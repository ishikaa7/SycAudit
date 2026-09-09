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


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score_id: uuid.UUID
    facet_scores: dict[str, float] = Field(default_factory=dict)
    ml_score: float | None = None
    rule_adjustment: float = 0.0
    final_score: float
    confidence: float | None = None
    created_at: datetime


class ResponseModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str | None = None
    model_name: str | None = None


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    response_id: uuid.UUID
    model_id: uuid.UUID
    model: ResponseModelRead | None = None
    response_text: str | None = None
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    token_usage: int | None = None
    created_at: datetime
    score: ScoreRead | None = None


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    variant_id: uuid.UUID
    variant_type: str
    variant_text: str
    generated_by_model_id: uuid.UUID | None = None
    created_at: datetime
    responses: list[ResponseRead] = Field(default_factory=list)


class SubmissionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    submission_id: uuid.UUID
    original_prompt: str
    status: str
    created_at: datetime
    updated_at: datetime


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    submission_id: uuid.UUID
    user_id: uuid.UUID
    original_prompt: str
    status: str
    created_at: datetime
    updated_at: datetime
    report: ReportRead | None = None
    variants: list[VariantRead] = Field(default_factory=list)