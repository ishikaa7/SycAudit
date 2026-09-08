"""Responder stage: every validated variant to every responder model.

Maps the "4 x 4 = 16 responses" step from ``orchestration/variation_rules.md``:
for each variant and each responder model, collect one free-form LLM response.
Individual call failures are recorded, never raised - callers get a complete
batch with per-(variant, model) status so the next (API/DB) stage can persist
it without losing any slot.

No live LLM calls happen in unit tests; a fake gateway is injected via
``gateway_builder``. ``respond`` is the independently callable single-prompt
entry point; ``respond_all_variants`` fans out the full cross product.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Literal, Sequence

from orchestration.generator import ProviderError, build_provider_error

from responders.gateway import (
    RESPONDER_SYSTEM_PROMPT,
    ChatCompletion,
    ChatGateway,
    RateLimiter,
    RateLimitedGateway,
    ResponderSpec,
    build_responder_gateway,
)

MAX_RESPONDER_ATTEMPTS = 3
CALL_TIMEOUT_SECONDS = 120.0

Status = Literal["success", "failed", "timeout"]
SleepFn = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class ResponderResult:
    variant_type: str
    provider: str
    model: str
    status: Status
    response_text: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None
    attempts: int = 1
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    @property
    def ok(self) -> bool:
        return self.status == "success"


@dataclass
class ResponderBatch:
    results: list[ResponderResult] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def failure_count(self) -> int:
        return len(self.results) - self.success_count

    @property
    def total_attempts(self) -> int:
        return sum(r.attempts for r in self.results)

    def by_variant(self) -> dict[str, list[ResponderResult]]:
        grouped: dict[str, list[ResponderResult]] = defaultdict(list)
        for r in self.results:
            grouped[r.variant_type].append(r)
        return dict(grouped)

    def by_model(self) -> dict[str, list[ResponderResult]]:
        grouped: dict[str, list[ResponderResult]] = defaultdict(list)
        for r in self.results:
            grouped[r.model].append(r)
        return dict(grouped)


def _sanitize_error_message(provider: str, model: str, exc: Exception) -> str:
    return str(build_provider_error(provider, model, exc))


async def respond(
    prompt: str,
    *,
    gateway: ChatGateway,
    spec: ResponderSpec,
    max_attempts: int = MAX_RESPONDER_ATTEMPTS,
    timeout_seconds: float = CALL_TIMEOUT_SECONDS,
    sleep: SleepFn = asyncio.sleep,
    system_prompt: str = RESPONDER_SYSTEM_PROMPT,
    variant_type: str = "prompt",
) -> ResponderResult:
    """Call one responder model for ``prompt``, retrying on provider failures.

    Never raises for expected provider behaviour: a :class:`ResponderResult` is
    always returned with ``status`` in ``success`` / ``failed`` / ``timeout``
    and a scrubbed ``error_message`` when it did not succeed.
    """
    if not prompt.strip():
        raise ValueError("refusing to send an empty prompt to a responder model")

    failures: list[str] = []
    timed_out = False
    started = time.monotonic()

    for attempt in range(1, max_attempts + 1):
        attempt_started = time.monotonic()
        try:
            completion: ChatCompletion = await asyncio.wait_for(
                gateway.complete(system_prompt, prompt), timeout=timeout_seconds
            )
        except TimeoutError:
            timed_out = True
            failures.append(f"attempt {attempt}: timed out after {timeout_seconds}s")
        except ProviderError as exc:
            failures.append(
                f"attempt {attempt}: provider error ({exc.provider} / {exc.model}): {exc}"
            )
        except Exception as exc:  # noqa: BLE001 - normalized into a failed result
            failures.append(
                f"attempt {attempt}: {_sanitize_error_message(spec.provider, spec.model, exc)}"
            )
        else:
            return ResponderResult(
                variant_type=variant_type,
                provider=spec.provider,
                model=spec.model,
                status="success",
                response_text=completion.text,
                latency_ms=int((time.monotonic() - attempt_started) * 1000),
                attempts=attempt,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                total_tokens=completion.total_tokens,
            )
        if attempt < max_attempts:
            await sleep(0.25 * attempt)

    return ResponderResult(
        variant_type=variant_type,
        provider=spec.provider,
        model=spec.model,
        status="timeout" if timed_out else "failed",
        error_message="; ".join(failures)[-2000:],
        latency_ms=int((time.monotonic() - started) * 1000),
        attempts=max_attempts,
    )


async def respond_all_variants(
    variants: Sequence[object],
    specs: Sequence[ResponderSpec],
    *,
    gateway_builder: Callable[[ResponderSpec], ChatGateway] = build_responder_gateway,
    max_attempts: int = MAX_RESPONDER_ATTEMPTS,
    timeout_seconds: float = CALL_TIMEOUT_SECONDS,
    sleep: SleepFn = asyncio.sleep,
) -> ResponderBatch:
    """Promise every ``variant`` to every ``spec`` and collect one result each.

    ``variants`` are any objects exposing ``variant_type`` and ``text`` (the
    same duck-typing the validator uses). Calls run concurrently; calls to the
    same model are serialized by a per-spec :class:`RateLimiter`. A builder is
    called once per spec and reuse across retries.
    """
    if not variants:
        raise ValueError("responder stage needs at least one variant")
    if not specs:
        raise ValueError("responder stage needs at least one responder spec")

    gateways = [
        RateLimitedGateway(gateway_builder(spec), RateLimiter(spec.rpm, sleep=sleep))
        for spec in specs
    ]

    async def one(
        variant: object, spec: ResponderSpec, gateway: ChatGateway
    ) -> ResponderResult:
        return await respond(
            getattr(variant, "text"),
            gateway=gateway,
            spec=spec,
            max_attempts=max_attempts,
            timeout_seconds=timeout_seconds,
            sleep=sleep,
            variant_type=getattr(variant, "variant_type"),
        )

    tasks = [
        one(variant, spec, gateway)
        for variant in variants
        for spec, gateway in zip(specs, gateways)
    ]
    results = await asyncio.gather(*tasks)
    return ResponderBatch(results=list(results))