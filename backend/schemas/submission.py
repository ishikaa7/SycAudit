from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubmissionCreate(BaseModel):
    original_prompt: str = Field(min_length=1)


class SubmissionCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    submission_id: uuid.UUID
    original_prompt: str
    status: str
    created_at: datetime


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: uuid.UUID
    wobble_score: float
    stability_label: str
    recommended_response_id: uuid.UUID | None = None
    created_at: datetime


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    submission_id: uuid.UUID
    user_id: uuid.UUID
    original_prompt: str
    status: str
    created_at: datetime
    updated_at: datetime
    report: ReportRead | None = None
