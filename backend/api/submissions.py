import uuid

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

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

_RESPONSE_LOADS = (
    selectinload(Submission.variants)
    .selectinload(PromptVariant.responses)
    .selectinload(Response.score),
    selectinload(Submission.variants)
    .selectinload(PromptVariant.responses)
    .selectinload(Response.model),
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
    return list(result.scalars().all())


@router.get("/{submission_id}", response_model=SubmissionRead)
async def get_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Submission:
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
    return submission