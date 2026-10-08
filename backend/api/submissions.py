import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import get_current_user
from database.models import PromptVariant, Response, Submission, User
from database.session import get_db
from orchestration.pipeline import run_submission_pipeline
from schemas.submission import (
    SubmissionCreate,
    SubmissionCreated,
    SubmissionListItem,
    SubmissionRead,
)

logger = logging.getLogger(__name__)

# Requests served before this instant read responses generated in an EARLIER
# server run - those runs are surfaced as stored/demo evaluations.
_SERVER_START = datetime.now(timezone.utc)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

_RESPONSE_LOADS = (
    selectinload(Submission.variants)
    .selectinload(PromptVariant.responses)
    .selectinload(Response.score),
    selectinload(Submission.variants)
    .selectinload(PromptVariant.responses)
    .selectinload(Response.model),
)


def _annotate_analysis(submission: Submission) -> None:
    """Attach read-only display metadata (not persisted columns)."""
    submission.analysis_source = "existing_ml_model"
    created = submission.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    submission.response_origin = (
        "live" if created is not None and created >= _SERVER_START else "stored"
    )


@router.post("", response_model=SubmissionCreated, status_code=201)
async def create_submission(
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Submission:
    submission = Submission(
        user_id=current_user.user_id,
        original_prompt=payload.original_prompt,
        status="processing",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    background_tasks.add_task(run_submission_pipeline, submission.submission_id)
    return submission


@router.get("", response_model=list[SubmissionListItem])
async def list_submissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Submission]:
    result = await db.execute(
        select(Submission)
        .where(Submission.user_id == current_user.user_id)
        .order_by(Submission.created_at.desc())
    )
    items = list(result.scalars().all())
    for item in items:
        _annotate_analysis(item)
    return items


@router.get("/{submission_id}", response_model=SubmissionRead)
async def get_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Submission:
    exists = await db.scalar(
        select(Submission).where(
            Submission.submission_id == submission_id,
            Submission.user_id == current_user.user_id,
        )
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Heal path: runs completed before grading was wired (stored/demo records)
    # are scored here with the same existing ML model, once.
    if exists.status == "completed":
        from scoring.service import heal_scored

        await heal_scored(submission_id)

    submission = await db.scalar(
        select(Submission)
        .options(selectinload(Submission.report), *_RESPONSE_LOADS)
        .where(
            Submission.submission_id == submission_id,
            Submission.user_id == current_user.user_id,
        )
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _annotate_analysis(submission)
    return submission