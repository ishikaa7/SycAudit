"""Execute the frozen ``budget-v1`` dataset against the responder set.

The calibration goal is to measure how many completion tokens each active
responder model naturally needs before answers are *finished* (``stop``) versus
cut off (``max_tokens``/``length``). To make truncation observable instead of a
raised error, every spec is re-cloned with ``keep_truncated=True`` regardless of
how the caller built it - production callers never trigger this path because
they never set that flag themselves.

Nothing here touches the database: results come back as plain dataclasses so the
script can print a report and future stages can persist or analyse them.
"""
from __future__ import annotations

import asyncio
import dataclasses
import math
import statistics
from dataclasses import dataclass
from typing import Callable, Sequence

from orchestration.generator import _TRUNCATED_FINISH_REASONS

from responders.benchmarks.prompts import (
    BENCHMARK_PROMPTS,
    BenchmarkPrompt,
)
from responders.gateway import (
    ChatGateway,
    RateLimiter,
    RateLimitedGateway,
    ResponderSpec,
    build_responder_gateway,
)
from responders.respond import (
    CALL_TIMEOUT_SECONDS,
    MAX_RESPONDER_ATTEMPTS,
    SleepFn,
    Status,
    respond,
)

TRUNCATED_FINISH_REASONS: frozenset[str] = frozenset(_TRUNCATED_FINISH_REASONS)


@dataclass(frozen=True)
class BenchmarkResult:
    """One ``budget-v1`` call: a single frozen prompt to a single spec.

    ``truncated`` is derived from ``finish_reason`` only - the provider told us
    the output hit its ceiling. A ``success`` result with a ``None``
    ``finish_reason`` means the provider simply did not report it.
    """

    prompt_id: int
    category: str
    expected_complexity: str
    provider: str
    model: str
    status: Status
    latency_ms: int | None
    attempts: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None
    response_text: str | None = None
    error_message: str | None = None
    thoughts_tokens: int | None = None

    @property
    def ok(self) -> bool:
        return self.status == "success"

    @property
    def truncated(self) -> bool:
        return (self.finish_reason or "").lower() in TRUNCATED_FINISH_REASONS


@dataclass(frozen=True)
class ModelSummary:
    """Aggregate ``budget-v1`` calibration statistics for one responder model."""

    provider: str
    model: str
    total: int
    succeeded: int
    failed: int
    timed_out: int
    completion_tokens_mean: float | None
    completion_tokens_median: int | None
    completion_tokens_p90: int | None
    completion_tokens_max: int | None
    truncated: int
    not_reported: int
    latency_ms_median: int | None

    @property
    def truncation_rate(self) -> float | None:
        if self.succeeded == 0:
            return None
        return self.truncated / self.succeeded

    def prompt_key(self) -> tuple[str, str]:
        return (self.provider, self.model)


@dataclass(frozen=True)
class BenchmarkSummary:
    version: str
    results: tuple[BenchmarkResult, ...]
    models: tuple[ModelSummary, ...]

    def by_model(self, provider: str, model: str) -> ModelSummary | None:
        for summary in self.models:
            if summary.provider == provider and summary.model == model:
                return summary
        return None


def _percentile(sorted_values: Sequence[int], q: float) -> int:
    if not sorted_values:
        raise ValueError("percentile of empty sequence")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * q
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[lower]
    fraction = rank - lower
    return round(sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction)


async def run_benchmark(
    prompts: Sequence[BenchmarkPrompt] = BENCHMARK_PROMPTS,
    specs: Sequence[ResponderSpec] = (),
    *,
    gateway_builder: Callable[[ResponderSpec], ChatGateway] = build_responder_gateway,
    max_attempts: int = MAX_RESPONDER_ATTEMPTS,
    timeout_seconds: float = CALL_TIMEOUT_SECONDS,
    sleep: SleepFn = asyncio.sleep,
    max_tokens: int | None = None,
) -> tuple[BenchmarkResult, ...]:
    """Send every frozen prompt to every spec, losing no measurement slot.

    Specs are cloned with ``keep_truncated=True`` so a hit output ceiling is
    recorded as a ``truncated`` result with its real tokens and finish reason,
    instead of raising. ``max_tokens`` is a BENCHMARK-ONLY ceiling override: it
    replaces the spec's ``max_tokens`` for this calibration only and never
    touches production ``ResponderSpec`` defaults or the frozen responder
    snapshot. Leave it ``None`` to run at the snapshot's configured ceiling.
    Rate limiting and per-call retry behaviour match the live responder stage
    (``respond_all_variants``).
    """
    if not prompts:
        raise ValueError("benchmark needs at least one prompt")
    if not specs:
        raise ValueError("benchmark needs at least one responder spec")
    if max_tokens is not None and max_tokens <= 0:
        raise ValueError("benchmark max_tokens must be positive")

    measured_specs: list[ResponderSpec] = []
    for spec in specs:
        overrides = {"keep_truncated": True}
        if max_tokens is not None:
            overrides["max_tokens"] = max_tokens
        measured_specs.append(dataclasses.replace(spec, **overrides))
    gateways = [
        RateLimitedGateway(gateway_builder(spec), RateLimiter(spec.rpm, sleep=sleep))
        for spec in measured_specs
    ]

    async def one(
        prompt: BenchmarkPrompt, spec: ResponderSpec, gateway: ChatGateway
    ) -> BenchmarkResult:
        result = await respond(
            prompt.text,
            gateway=gateway,
            spec=spec,
            max_attempts=max_attempts,
            timeout_seconds=timeout_seconds,
            sleep=sleep,
            variant_type="benchmark",
        )
        return BenchmarkResult(
            prompt_id=prompt.prompt_id,
            category=prompt.category,
            expected_complexity=prompt.expected_complexity,
            provider=result.provider,
            model=result.model,
            status=result.status,
            latency_ms=result.latency_ms,
            attempts=result.attempts,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            finish_reason=result.finish_reason,
            response_text=result.response_text,
            error_message=result.error_message,
            thoughts_tokens=result.thoughts_tokens,
        )

    tasks = [
        one(prompt, spec, gateway)
        for prompt in prompts
        for spec, gateway in zip(measured_specs, gateways)
    ]
    raw = await asyncio.gather(*tasks)
    return tuple(raw)


def summarize(results: Sequence[BenchmarkResult], version: str = "unknown") -> BenchmarkSummary:
    """Aggregate per-model statistics from a completed run.

    Length statistics (mean/median/p90/max) use only successful results whose
    provider reported completion tokens. ``truncated`` counts every success the
    provider flagged as hitting its ceiling; ``not_reported`` counts successes
    with no finish reason at all.
    """
    order: list[tuple[str, str]] = []
    grouped: dict[tuple[str, str], list[BenchmarkResult]] = {}
    for result in results:
        key = (result.provider, result.model)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(result)

    model_summaries = [summarize_model(model_results) for model_results in grouped.values()]
    return BenchmarkSummary(
        version=version,
        results=tuple(results),
        models=tuple(model_summaries),
    )


def summarize_model(results: Sequence[BenchmarkResult]) -> ModelSummary:
    lengths = sorted(
        r.completion_tokens for r in results if r.ok and r.completion_tokens is not None
    )
    latencies = sorted(r.latency_ms for r in results if r.latency_ms is not None)
    succeeded = sum(1 for r in results if r.ok)
    return ModelSummary(
        provider=results[0].provider,
        model=results[0].model,
        total=len(results),
        succeeded=succeeded,
        failed=sum(1 for r in results if r.status == "failed"),
        timed_out=sum(1 for r in results if r.status == "timeout"),
        completion_tokens_mean=statistics.mean(lengths) if lengths else None,
        completion_tokens_median=_percentile(lengths, 0.5) if lengths else None,
        completion_tokens_p90=_percentile(lengths, 0.9) if lengths else None,
        completion_tokens_max=lengths[-1] if lengths else None,
        truncated=sum(1 for r in results if r.ok and r.truncated),
        not_reported=sum(1 for r in results if r.ok and r.finish_reason is None),
        latency_ms_median=_percentile(latencies, 0.5) if latencies else None,
    )


def format_report(summary: BenchmarkSummary) -> str:
    """Render a compact calibration report suitable for a CLI script."""
    lines = [
        f"budget-v1 responder calibration ({summary.version})",
        f"results : {len(summary.results)}  prompts x models",
        "",
        f"{'model':<40} {'ok':>3} {'trunc':>5} {'rate':>7} {'p50':>6} {'p90':>6} {'max':>6} {'med_ms':>7}",
    ]
    for m in summary.models:
        rate = f"{m.truncation_rate:.0%}" if m.truncation_rate is not None else "n/a"
        lines.append(
            f"{m.prompt_key()[0] + '/' + m.prompt_key()[1]:<40} "
            f"{m.succeeded:>3} {m.truncated:>5} {rate:>7} "
            f"{m.completion_tokens_median if m.completion_tokens_median is not None else '-':>6} "
            f"{m.completion_tokens_p90 if m.completion_tokens_p90 is not None else '-':>6} "
            f"{m.completion_tokens_max if m.completion_tokens_max is not None else '-':>6} "
            f"{m.latency_ms_median if m.latency_ms_median is not None else '-':>7}"
        )
    return "\n".join(lines)