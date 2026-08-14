import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")

    __table_args__ = (CheckConstraint("role IN ('user','reviewer','admin')", name="ck_users_role"),)


class LLMModel(Base):
    __tablename__ = "llm_models"

    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50))
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    rate_limit_rpm: Mapped[int | None] = mapped_column(Integer)
    is_responder: Mapped[bool] = mapped_column(default=True)
    is_framer: Mapped[bool] = mapped_column(default=False)
    is_grader: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("provider IN ('groq','gemini','huggingface')", name="ck_llm_models_provider"),
        UniqueConstraint("provider", "model_name", "version", name="uq_llm_models_identity"),
    )


class Submission(Base):
    __tablename__ = "submissions"

    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    original_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="submissions")
    variants: Mapped[list["PromptVariant"]] = relationship(back_populates="submission")
    report: Mapped["Report | None"] = relationship(back_populates="submission", uselist=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending','processing','completed','failed')", name="ck_submissions_status"),
    )


class PromptVariant(Base):
    __tablename__ = "prompt_variants"

    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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


class Response(Base):
    __tablename__ = "responses"

    response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_variants.variant_id"), nullable=False, index=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_models.model_id"), nullable=False, index=True
    )
    response_text: Mapped[str | None] = mapped_column(Text)  # null if the call failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    variant: Mapped["PromptVariant"] = relationship(back_populates="responses")
    score: Mapped["ResponseScore | None"] = relationship(back_populates="response", uselist=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending','success','failed','timeout')", name="ck_responses_status"),
    )


class ResponseScore(Base):
    __tablename__ = "response_scores"

    score_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responses.response_id"), nullable=False, unique=True
    )
    grader_model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("llm_models.model_id"), nullable=False)
    facet_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ml_score: Mapped[float | None] = mapped_column(Float)          # populated once the classifier ships
    rule_adjustment: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped["Response"] = relationship(back_populates="score")


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.submission_id"), nullable=False, unique=True
    )
    recommended_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responses.response_id"), nullable=False
    )
    wobble_score: Mapped[float] = mapped_column(Float, nullable=False)
    stability_label: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped["Submission"] = relationship(back_populates="report")

    __table_args__ = (
        CheckConstraint("stability_label IN ('low','moderate','high')", name="ck_reports_stability_label"),
    )
