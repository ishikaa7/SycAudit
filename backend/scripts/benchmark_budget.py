"""Run the ``budget-v1`` responder calibration benchmark against live models.

Isolated dev tool only -- calls the REAL responder gateways against the frozen
20-prompt calibration dataset. It does NOT require (or write to) PostgreSQL: the
responder set comes from the frozen ``BENCHMARK_RESPONDERS`` snapshot, which
mirrors the active seeded configuration, so a broken or absent DATABASE_URL can
never block calibration.

Truncation is opt-in here by design: specs are re-cloned with
``keep_truncated=True`` so an answer cut off by the token ceiling is reported
(and counted) instead of failing the calibration run. ``--max-tokens`` is a
benchmark-only ceiling override for calibration (production ``max_tokens`` is
never touched).

Raw results are saved as JSON under ``responders/benchmarks/results/`` for later
analysis.

Usage (from backend/):
    python scripts/benchmark_budget.py
    python scripts/benchmark_budget.py --provider gemini
    python scripts/benchmark_budget.py --model openai/gpt-oss-20b
    python scripts/benchmark_budget.py --model openai/gpt-oss-20b --max-tokens 4096
    python scripts/benchmark_budget.py --provider groq --model openai/gpt-oss-20b
    python scripts/benchmark_budget.py --per-prompt

``--provider`` and ``--model`` both narrow the responder snapshot; supplied
together they select the intersection (that exact model on that provider).
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from responders.benchmarks import (
    BENCHMARK_PROMPTS,
    BENCHMARK_RESPONDERS,
    BENCHMARK_VERSION,
    format_report,
    run_benchmark,
    summarize,
)
from responders.benchmarks.runner import BenchmarkResult
from responders.gateway import ResponderSpec

RESULTS_DIR = Path(__file__).resolve().parents[1] / "responders" / "benchmarks" / "results"


def select_responder_specs(
    specs: tuple[ResponderSpec, ...],
    provider: str | None = None,
    model: str | None = None,
) -> tuple[ResponderSpec, ...]:
    """Pure CLI selector: keep only specs matching an exact provider and/or model.

    ``provider`` filters on the spec's provider; ``model`` filters on the exact
    model name. With both given the selection is the intersection. ``None``
    leaves that dimension open, and original order is preserved.
    """
    selected = []
    for spec in specs:
        if provider is not None and spec.provider != provider:
            continue
        if model is not None and spec.model != model:
            continue
        selected.append(spec)
    return tuple(selected)


def load_responder_specs(
    provider: str | None = None,
    model: str | None = None,
    *,
    specs: tuple[ResponderSpec, ...] = BENCHMARK_RESPONDERS,
) -> tuple[ResponderSpec, ...]:
    """Return the responder snapshot filtered by ``provider`` and/or ``model``."""
    return select_responder_specs(specs, provider=provider, model=model)


def _sanitize_model_name(model: str) -> str:
    return model.replace("/", "__").replace(" ", "_")


def results_path(
    *,
    provider: str | None,
    model: str | None,
    now: datetime | None = None,
    results_dir: Path = RESULTS_DIR,
) -> Path:
    """Deterministic target path for one run's raw JSON.

    A single-model run is named for that model; a run over several models is
    named ``budget-v1_all``. Timestamps are UTC, second precision.
    """
    when = (now or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")
    if model is not None:
        scope = _sanitize_model_name(model)
    elif provider is not None:
        scope = provider
    else:
        scope = "all"
    return results_dir / f"budget-v1_{scope}_{when}.json"


def serialize_result(result: BenchmarkResult) -> dict:
    data = dataclasses.asdict(result)
    data["truncated"] = result.truncated
    return data


def write_results_json(
    results,
    *,
    provider: str | None,
    model: str | None,
    path: Path | None = None,
    max_tokens: int | None = None,
) -> Path:
    """Write raw calibration results to ``results/`` and return the file path."""
    target = path or results_path(provider=provider, model=model)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": BENCHMARK_VERSION,
        "scope": {"provider": provider, "model": model, "max_tokens": max_tokens},
        "run_at": datetime.now(timezone.utc).isoformat(),
        "results": [serialize_result(r) for r in results],
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return target


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="budget-v1 responder calibration")
    parser.add_argument(
        "--provider",
        choices=["groq", "gemini", "huggingface"],
        help="restrict the run to one provider (default: all seeded responders)",
    )
    parser.add_argument(
        "--model",
        help="restrict the run to one exact responder model "
        "(e.g. openai/gpt-oss-20b); combined with --provider selects the intersection",
    )
    parser.add_argument(
        "--per-prompt",
        action="store_true",
        help="also print per-prompt results for each model",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="benchmark-only output ceiling in tokens (e.g. 4096); does not "
        "touch production max_tokens - defaults to the configured ceiling",
    )
    return parser


async def main() -> int:
    args = build_argument_parser().parse_args()

    specs = load_responder_specs(args.provider, args.model)
    if not specs:
        print(
            "no responder matches the filters "
            f"(provider={args.provider!r}, model={args.model!r}) - "
            "check responders/benchmarks/specs.py"
        )
        return 1

    print(
        f"budget-v1 calibration start: {len(specs)} model(s), "
        f"{len(BENCHMARK_PROMPTS)} prompts each, "
        f"ceiling={args.max_tokens or 'configured'} tokens"
    )
    results = await run_benchmark(specs=specs, max_tokens=args.max_tokens)

    summary = summarize(results, version=BENCHMARK_VERSION)
    print()
    print(format_report(summary))

    json_path = write_results_json(
        results, provider=args.provider, model=args.model, max_tokens=args.max_tokens
    )
    print(f"raw results written to: {json_path}")

    if args.per_prompt:
        for m in summary.models:
            print()
            print(f"per-prompt: {m.provider}/{m.model}")
            for r in summary.results:
                if r.provider != m.provider or r.model != m.model:
                    continue
                status = f"{r.status:8}"
                reason = r.finish_reason or "n/a"
                tokens = f"{r.completion_tokens if r.completion_tokens is not None else 'n/a':>5}"
                print(
                    f"  #{r.prompt_id:>2} {r.category:<18} {status} "
                    f"tokens={tokens} finish={reason}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))