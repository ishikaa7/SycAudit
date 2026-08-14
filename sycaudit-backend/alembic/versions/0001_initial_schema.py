"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('user','reviewer','admin')", name="ck_users_role"),
    )

    op.create_table(
        "llm_models",
        sa.Column("model_id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50)),
        sa.Column("temperature", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="1024"),
        sa.Column("rate_limit_rpm", sa.Integer),
        sa.Column("is_responder", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_framer", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_grader", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("provider IN ('groq','gemini','huggingface')", name="ck_llm_models_provider"),
        sa.UniqueConstraint("provider", "model_name", "version", name="uq_llm_models_identity"),
    )

    op.create_table(
        "submissions",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("original_prompt", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending','processing','completed','failed')", name="ck_submissions_status"),
    )
    op.create_index("idx_submissions_user_id", "submissions", ["user_id"])

    op.create_table(
        "prompt_variants",
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.submission_id"), nullable=False),
        sa.Column("variant_type", sa.String(20), nullable=False),
        sa.Column("variant_text", sa.Text, nullable=False),
        sa.Column("generated_by_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_models.model_id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("variant_type IN ('original','third_person','question')", name="ck_variants_type"),
        sa.UniqueConstraint("submission_id", "variant_type", name="uq_variants_submission_type"),
    )
    op.create_index("idx_variants_submission_id", "prompt_variants", ["submission_id"])

    op.create_table(
        "responses",
        sa.Column("response_id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_variants.variant_id"), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_models.model_id"), nullable=False),
        sa.Column("response_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("token_usage", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending','success','failed','timeout')", name="ck_responses_status"),
    )
    op.create_index("idx_responses_variant_id", "responses", ["variant_id"])
    op.create_index("idx_responses_model_id", "responses", ["model_id"])

    op.create_table(
        "response_scores",
        sa.Column("score_id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("response_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("responses.response_id"),
                   nullable=False, unique=True),
        sa.Column("grader_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_models.model_id"), nullable=False),
        sa.Column("facet_scores", postgresql.JSONB, nullable=False),
        sa.Column("ml_score", sa.Float),
        sa.Column("rule_adjustment", sa.Float, nullable=False, server_default="0"),
        sa.Column("final_score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reports",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.submission_id"),
                   nullable=False, unique=True),
        sa.Column("recommended_response_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("responses.response_id"),
                   nullable=False),
        sa.Column("wobble_score", sa.Float, nullable=False),
        sa.Column("stability_label", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("stability_label IN ('low','moderate','high')", name="ck_reports_stability_label"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("response_scores")
    op.drop_index("idx_responses_model_id", table_name="responses")
    op.drop_index("idx_responses_variant_id", table_name="responses")
    op.drop_table("responses")
    op.drop_index("idx_variants_submission_id", table_name="prompt_variants")
    op.drop_table("prompt_variants")
    op.drop_index("idx_submissions_user_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("llm_models")
    op.drop_table("users")
