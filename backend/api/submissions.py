import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Submission, User
from database.session import get_db
from schemas.submission import SubmissionCreate, SubmissionCreated, SubmissionRead

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

DEV_USER_EMAIL = "local@sycaudit.dev"


async def _get_or_create_dev_user(db: AsyncSession) -> User:
    user = await db.scalar(select(User).where(User.email == DEV_USER_EMAIL))
    if user is not None:
        return user
    user = User(name="Local User", email=DEV_USER_EMAIL, password_hash="")
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        user = await db.scalar(select(User).where(User.email == DEV_USER_EMAIL))
    await db.refresh(user)
    return user


@router.post("", response_model=SubmissionCreated, status_code=201)
async def create_submission(
    payload: SubmissionCreate, db: AsyncSession = Depends(get_db)
) -> Submission:
    user = await _get_or_create_dev_user(db)
    submission = Submission(user_id=user.user_id, original_prompt=payload.original_prompt)
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/{submission_id}", response_model=SubmissionRead)
async def get_submission(
    submission_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Submission:
    submission = await db.scalar(
        select(Submission)
        .options(selectinload(Submission.report))
        .where(Submission.submission_id == submission_id)
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission
