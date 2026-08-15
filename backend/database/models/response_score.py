from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class ResponseScore(Base):
    __tablename__ = "response_scores"

    score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responses.response_id"), nullable=False, unique=True
    )
    grader_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_models.model_id"), nullable=False
    )
    facet_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ml_score: Mapped[float | None] = mapped_column(Float)  # populated once the classifier ships
    rule_adjustment: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped["Response"] = relationship(back_populates="score")
