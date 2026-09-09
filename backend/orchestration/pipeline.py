"""Background pipeline: turn a stored submission into persisted variants and responses.

Owns the ``submission -> processing -> variants -> responses -> completed/failed``
transition. The API only inserts the submission row and enqueues this task; every
later stage lives here so no request handler can hang behind live LLM calls.

Persistence mapping helpers (``build_variant_rows`` / ``build_response_rows``)
are pure and unit-testable without a database.
"""
from __future__ import annotations

import logging
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import LLMModel, PromptVariant, Response, Submission
from database.session import AsyncSessionLocal
from orchestration.generator import GenerationSpec, infer_provider
from orchestration.variants import Variant, VariantGenerationResult, generate_variants
from responders.gateway import ResponderSpec
from responders.respond import ResponderBatch, respond_all_variants

logger = logging.getLogger(__name__)


def build_variant_rows(
    submission: Submission,
    *,
    variants: Sequence[Variant],
    generated_by_model_id: uuid.UUID | None,
) -> list[PromptVariant]:
    """Map generated ``Variant`` dataclasses onto ORM rows for one submission."""
    return [
        PromptVariant(
            submission_id=submission.submission_id,
            variant_type=v.variant_type,
            variant_text=v.text,
            generated_by_model_id=generated_by_model_id,
        )
        for v in variants
    ]


def build_response_rows(
    variant_rows: Sequence[PromptVariant],
    *,
    batch: ResponderBatch,
    model_id_by_pair: dict[tuple[str, str], uuid.UUID],
) -> list[Response]:
    """Map a responder batch onto ORM rows, dropping unmapped uniqueness rows.

    Every (variant_type, provider/model) pair with a matching variant row and
    model id becomes one ``Response`` row; a failed/timeout slot still persists
    as a row so the UI sees the failure instead of a missing slot.
    """
    variant_by_type = {v.variant_type: v for v in variant_rows}
    rows: list[Response] = []
    for result in batch.results:
        variant = variant_by_type.get(result.variant_type)
        model_id = model_id_by_pair.get((result.provider, result.model))
        if variant is None or model_id is None:
            logger.warning(
                "dropping response for unknown variant=%r model=%r",
                result.variant_type,
                f"{result.provider}/{result.model}",
            )
            continue
        rows.append(
            Response(
                variant_id=variant.variant_id,
                model_id=model_id,
                response_text=result.response_text if result.ok else None,
                status=result.status,
                error_message=result.error_message,
                latency_ms=result.latency_ms,
                token_usage=result.total_tokens,
            )
        )
    return rows


async def _load_variant_framer_model_id(
    session: AsyncSession,
    generation: GenerationSpec,
) -> uuid.UUID | None:
    row = await session.scalar(
        select(LLMModel).where(
            LLMModel.provider == generation.provider,
            LLMModel.model_name == generation.model,
        )
    )
    return row.model_id if row is not None else None


async def _load_active_responders(
    session: AsyncSession,
) -> tuple[list[ResponderSpec], dict[tuple[str, str], uuid.UUID]]:
    rows = (
        await session.scalars(
            select(LLMModel).where(
                LLMModel.is_responder.is_(True),
                LLMModel.is_active.is_(True),
            )
        )
    ).all()
    specs = [
        ResponderSpec(
            provider=row.provider,
            model=row.model_name,
            temperature=row.temperature,
            max_tokens=row.max_tokens,
            rpm=row.rate_limit_rpm,
        )
        for row in rows
    ]
    model_id_by_pair = {(row.provider, row.model_name): row.model_id for row in rows}
    return specs, model_id_by_pair


async def _process_submission(session: AsyncSession, submission: Submission) -> None:
    submission.status = "processing"
    await session.commit()

    generation = GenerationSpec.for_provider(infer_provider())
    generation_result: VariantGenerationResult = await generate_variants(
        submission.original_prompt,
        generation=generation,
    )

    framer_model_id = await _load_variant_framer_model_id(session, generation)
    variant_rows = build_variant_rows(
        submission,
        variants=generation_result.variants,
        generated_by_model_id=framer_model_id,
    )
    session.add_all(variant_rows)
    await session.flush()

    specs, model_id_by_pair = await _load_active_responders(session)
    if not specs:
        raise RuntimeError("no active responder models are configured")

    batch = await respond_all_variants(generation_result.variants, specs)
    session.add_all(
        build_response_rows(
            variant_rows,
            batch=batch,
            model_id_by_pair=model_id_by_pair,
        )
    )
    success = batch.success_count
    total = len(batch.results)
    logger.info(
        "submission %s responded: %d/%d succeeded", submission.submission_id, success, total
    )
    submission.status = "completed"
    await session.commit()


async def run_submission_pipeline(submission_id: uuid.UUID) -> None:
    """Open an independent session (the request one is closed) and process."""
    async with AsyncSessionLocal() as session:
        submission = await session.get(Submission, submission_id)
        if submission is None:
            logger.warning("pipeline: submission %s not found", submission_id)
            return
        try:
            await _process_submission(session, submission)
        except Exception:  # noqa: BLE001 - a pipeline failure must never escape
            logger.exception("submission %s failed", submission_id)
            submission.status = "failed"
            await session.commit()