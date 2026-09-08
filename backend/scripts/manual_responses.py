"""Manual runner for the Step-3 responder pipeline (live 4x4 verification).

Isolated dev tool only -- calls the REAL ``generate_variants()`` to obtain 4
validated prompt variants and then the REAL ``respond_all_variants()`` against
the 4 currently seeded responder models. Does NOT use the API, does NOT write
to the database, and does NOT wire into any other pipeline stage.

The responder model set is READ from the ``llm_models`` table (rows where
``is_responder = true`` and ``is_active = true``) - the seeded configuration is
the single source of truth and is never hardcoded here.

Usage (from backend/):
    python scripts/manual_responses.py
    python scripts/manual_responses.py "Your prompt here"
    python scripts/manual_responses.py 1
    python scripts/manual_responses.py --provider gemini "Your prompt here"
    python scripts/manual_responses.py --list

With no prompt it runs SAMPLE_PROMPTS[0]; a bare number 1-3 selects that sample.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from database.database import engine
from database.models import LLMModel
from database.session import AsyncSessionLocal
from orchestration import GenerateVariantsError, GenerationSpec, generate_variants, infer_provider
from responders import ResponderResult, respond_all_variants
from responders.gateway import ResponderSpec

SAMPLE_PROMPTS = [
    # 1 - a simple first-person opinion
    "I think the new policy is unfair to small businesses.",
    # 2 - an existing question
    "Do you agree that remote work is more productive?",
    # 3 - a prompt containing names, numbers and dates
    "Alice received 27,000 dollars from Jordan's fund on March 14, 2025.",
]


async def load_responder_specs() -> list[ResponderSpec]:
    """Read the seeded responder set from llm_models (is_responder=True)."""
    async with AsyncSessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(LLMModel).where(
                        LLMModel.is_responder.is_(True), LLMModel.is_active.is_(True)
                    )
                )
            )
            .scalars()
            .all()
        )
    return [
        ResponderSpec(
            provider=row.provider,
            model=row.model_name,
            temperature=row.temperature,
            max_tokens=row.max_tokens,
            rpm=row.rate_limit_rpm,
        )
        for row in rows
    ]


def print_result(result: ResponderResult) -> None:
    print("  " + "-" * 70)
    print(f"  variant_type : {result.variant_type}")
    print(f"  provider     : {result.provider}")
    print(f"  model        : {result.model}")
    print(f"  status       : {result.status}")
    print(f"  latency      : {result.latency_ms} ms" if result.latency_ms is not None else "  latency      : n/a")
    print(f"  attempts     : {result.attempts}")
    if result.prompt_tokens is None and result.completion_tokens is None and result.total_tokens is None:
        print("  tokens       : n/a (provider did not expose usage)")
    else:
        print(
            f"  tokens       : prompt={result.prompt_tokens} "
            f"completion={result.completion_tokens} total={result.total_tokens}"
        )
    if result.status == "success":
        print("  response     :")
        for line in (result.response_text or "").splitlines():
            print(f"    {line}")
    else:
        print(f"  error        : {result.error_message}")


def print_report(results: list[ResponderResult], expected: int, expected_pairs: set) -> None:
    pairs = {(r.variant_type, r.model) for r in results}
    all_present = expected_pairs <= pairs
    successes = [r for r in results if r.status == "success"]
    failures = [r for r in results if r.status != "success"]
    stale = [f for f in failures if f.status == "timeout"]
    with_usage = sum(1 for r in results if r.total_tokens is not None)

    print("=" * 74)
    print("RESPONDER BATCH SUMMARY (live 4x4)")
    print(f"  total expected   : {expected}")
    print(f"  total returned   : {len(results)}")
    print(f"  successful       : {len(successes)}")
    print(f"  failed           : {len(failures)}")
    print(f"  timed out        : {len(stale)}")
    print(f"  unique pairs     : {len(pairs)}")
    print(f"  every expected pair present : {all_present}")
    print(f"  results with token usage    : {with_usage}/{expected}")
    if failures:
        print("  failing slot(s):")
        for r in failures:
            print(f"    - {r.variant_type} / {r.model}: {r.error_message}")
    print("=" * 74)


async def run(prompt: str, provider: str | None, model: str | None) -> int:
    generation = (
        GenerationSpec.for_provider(provider or infer_provider(), model=model)
        if (provider or model)
        else None
    )
    try:
        result = await generate_variants(prompt, generation=generation)
    except GenerateVariantsError as exc:
        print("GENERATION FAILED after all attempts:")
        for failure in exc.failures:
            print(f"  - {failure}")
        return 1

    print("=" * 74)
    print("VALIDATED VARIANTS (4)")
    for v in result.variants:
        print(f"  [{v.variant_type:12}]  {v.text}")
    print(f"  generator        : {result.metadata.provider} / {result.metadata.model}")

    specs = await load_responder_specs()
    print("RESPONDER MODELS (seeded, is_responder=True)")
    for spec in specs:
        print(f"  {spec.provider:12} / {spec.model} (rpm={spec.rpm})")
    if len(specs) != 4:
        print(f"WARNING: expected 4 seeded responder models, found {len(specs)}")

    expected = len(result.variants) * len(specs)
    expected_pairs = {(v.variant_type, s.model) for v in result.variants for s in specs}
    print(f"EXPECTED RESPONSES : {len(result.variants)} variants x {len(specs)} models = {expected}")
    print("=" * 74)

    batch = await respond_all_variants(result.variants, specs)

    for r in batch.results:
        print_result(r)
    print_report(batch.results, expected, expected_pairs)
    return 0


def main(argv: list[str]) -> int:
    provider: str | None = None
    model: str | None = None
    args: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--provider" and i + 1 < len(argv):
            provider = argv[i + 1]
            i += 2
        elif arg == "--model" and i + 1 < len(argv):
            model = argv[i + 1]
            i += 2
        elif arg == "--list":
            for n, p in enumerate(SAMPLE_PROMPTS, 1):
                print(f"{n}. {p}")
            return 0
        else:
            args.append(arg)
            i += 1

    if provider is not None and provider not in ("groq", "gemini", "huggingface"):
        print(f"unknown provider '{provider}' (expected groq, gemini, or huggingface)")
        return 2

    if args:
        candidate = args[0]
        if candidate.isdigit() and 1 <= int(candidate) <= len(SAMPLE_PROMPTS):
            prompt = SAMPLE_PROMPTS[int(candidate) - 1]
        else:
            prompt = candidate
    else:
        prompt = SAMPLE_PROMPTS[0]
        print(f"No prompt given - using SAMPLE_PROMPTS[0]: {prompt!r}\n")

    return asyncio.run(_main_async(prompt, provider, model))


async def _main_async(prompt: str, provider: str | None, model: str | None) -> int:
    try:
        return await run(prompt, provider, model)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))