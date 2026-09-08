"""Manual runner for the Step-2 prompt-variation pipeline.

Isolated dev tool only -- calls the REAL ``generate_variants()`` with the REAL
configured LLM client (no mocks, no fake gateway). Does NOT touch the API, the
database, or any other pipeline stage.

Usage (from backend/):
    python scripts/manual_variations.py
    python scripts/manual_variations.py "Your prompt here"
    python scripts/manual_variations.py --provider gemini "Your prompt here"
    python scripts/manual_variations.py --provider groq --model openai/gpt-oss-20b "Your prompt here"
    python scripts/manual_variations.py --list

With no argument it runs SAMPLE_PROMPTS[0]; a bare number 1-5 selects that
sample. Default provider is whatever ``infer_provider()`` finds configured
(first available of groq/gemini/huggingface in backend/.env).
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

from orchestration import (
    GenerateVariantsError,
    GenerationSpec,
    generate_variants,
    infer_provider,
)

SAMPLE_PROMPTS = [
    # 1 - a simple first-person opinion
    "I think the new policy is unfair to small businesses.",
    # 2 - an existing question
    "Do you agree that remote work is more productive?",
    # 3 - a prompt containing names, numbers and dates
    "Alice received 27,000 dollars from Jordan's fund on March 14, 2025.",
    # 4 - an already-hedged opinion
    "I'm not sure the company's new logo is a good idea.",
    # 5 - a complex multi-sentence prompt
    (
        "After Mr. Fernandez reviewed the Q3 report, he noticed revenue grew by 12% "
        "since October 1, 2025. Now he wants to know if that growth is sustainable "
        "without cutting costs further."
    ),
]


def print_result(prompt: str, result) -> None:
    print("=" * 74)
    print("ORIGINAL PROMPT")
    print(f"  {prompt}")
    print("GENERATOR (LLM) ANALYSIS")
    print(f"  {result.analysis}")
    print("FOUR VARIANTS")
    for v in result.variants:
        print(f"  [{v.variant_type:12}]  {v.text}")
    print("VALIDATION")
    print(f"  result : {result.validation.summary}")
    for issue in result.validation.issues:
        print(
            f"  {issue.severity:7}  {issue.code:22} [{issue.variant_type}]  {issue.message}"
        )
    print("METADATA")
    print(f"  model            : {result.metadata.model}")
    print(f"  provider         : {result.metadata.provider}")
    print(f"  temperature      : {result.metadata.temperature}")
    print(f"  max_tokens       : {result.metadata.max_tokens}")
    print(f"  prompt_version   : {result.metadata.prompt_version}")
    print(f"  attempts          : {result.metadata.attempts}")
    print("=" * 74)


def print_failure(exc: GenerateVariantsError) -> None:
    print("GENERATION FAILED after all attempts:")
    for failure in exc.failures:
        print(f"  - {failure}")
    print("=" * 74)


async def run(prompt: str, provider: str | None, model: str | None) -> int:
    generation = GenerationSpec.for_provider(provider or infer_provider(), model=model) if (provider or model) else None
    try:
        result = await generate_variants(prompt, generation=generation)
    except GenerateVariantsError as exc:
        print_failure(exc)
        return 1
    print_result(prompt, result)
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

    return asyncio.run(run(prompt, provider, model))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))