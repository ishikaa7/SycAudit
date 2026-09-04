"""Public interface for the isolated prompt-variation pipeline.

Holds the domain types plus the orchestration loop (generate -> validate ->
retry). The generator (LLM) and the validator (deterministic Python) live in
their own modules; this module only wires them together.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from orchestration.generator import (
    MAX_ATTEMPTS,
    ChatGateway,
    GenerationSpec,
    MalformedOutputError,
    build_gateway,
    generate_raw_variants,
    infer_provider,
)
from orchestration.validator import ValidationResult, validate_variants

VARIANT_TYPES = ("original", "third_person", "question", "hedged")


@dataclass(frozen=True)
class Variant:
    variant_type: str
    text: str


@dataclass(frozen=True)
class GenerationMetadata:
    model: str
    provider: str
    temperature: float
    max_tokens: int
    prompt_version: str
    attempts: int
    generation_spec: dict


@dataclass(frozen=True)
class VariantGenerationResult:
    variants: tuple[Variant, ...]
    analysis: str
    validation: ValidationResult
    metadata: GenerationMetadata


class GenerateVariantsError(Exception):
    """Raised when all three attempts fail to produce valid variants."""

    def __init__(self, message: str, attempts: int, failures: list[str]):
        super().__init__(message)
        self.attempts = attempts
        self.failures = failures


async def generate_variants(
    prompt: str,
    *,
    gateway: ChatGateway | None = None,
    generation: GenerationSpec | None = None,
) -> VariantGenerationResult:
    """Generate and validate the four prompt variants.

    - ``gateway``: injected chat gateway (tests pass a mock).
    - ``generation``: model/provider/parameters for traceability.

    Implements the approved retry policy: one initial attempt plus at most two
    regeneration attempts. Never falls back to the original prompt.
    """
    spec = generation or GenerationSpec.for_provider(infer_provider())
    gw = gateway if gateway is not None else build_gateway(spec)

    failures: list[str] = []
    last_validation: ValidationResult | None = None
    last_analysis = ""
    last_variants: tuple[Variant, ...] = ()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = await generate_raw_variants(
                prompt,
                gateway=gw,
                generation=spec,
                attempt=attempt,
                max_attempts=MAX_ATTEMPTS,
            )
        except MalformedOutputError as exc:
            failures.append(f"attempt {attempt}: malformed generator output: {exc}")
            continue

        candidates = tuple(Variant(v.variant_type, v.text) for v in raw.variants)
        result = validate_variants(prompt, candidates)
        if result.valid:
            ordered = tuple(
                next(v for v in candidates if v.variant_type == t) for t in VARIANT_TYPES
            )
            metadata = GenerationMetadata(
                model=spec.model,
                provider=spec.provider,
                temperature=spec.temperature,
                max_tokens=spec.max_tokens,
                prompt_version=spec.prompt_version,
                attempts=attempt,
                generation_spec=asdict(spec),
            )
            return VariantGenerationResult(
                variants=ordered,
                analysis=raw.analysis,
                validation=result,
                metadata=metadata,
            )

        last_validation = result
        last_analysis = raw.analysis
        last_variants = candidates
        failures.append(f"attempt {attempt}: validation failed — {result.summary}")

    raise GenerateVariantsError(
        "variation generation failed after three consecutive failed attempts",
        attempts=MAX_ATTEMPTS,
        failures=failures,
    )