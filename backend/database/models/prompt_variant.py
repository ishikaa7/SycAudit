from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class PromptVariant(Base):
    __tablename__ = "prompt_variants"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.submission_id"), nullable=False, index=True
    )
    variant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    variant_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_models.model_id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped["Submission"] = relationship(back_populates="variants")
    responses: Mapped[list["Response"]] = relationship(back_populates="variant")

    __table_args__ = (
        CheckConstraint("variant_type IN ('original','third_person','question')", name="ck_variants_type"),
        UniqueConstraint("submission_id", "variant_type", name="uq_variants_submission_type"),
    )
