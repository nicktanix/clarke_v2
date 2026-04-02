"""Initial schema for Phase 1.

Revision ID: 001
Revises:
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("external_id", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "request_log",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=False, unique=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text()),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text()),
        sa.Column("degraded_mode", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("prompt_version_id", sa.Text()),
        sa.Column("context_template_version_id", sa.Text()),
        sa.Column("model_used", sa.Text()),
        sa.Column("answer_summary", sa.Text()),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'")),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "retrieval_episodes",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "request_id",
            sa.Text(),
            sa.ForeignKey("request_log.request_id"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("query_features", JSONB()),
        sa.Column("retrieval_plan", JSONB()),
        sa.Column("retrieved_items", JSONB()),
        sa.Column("injected_items", JSONB()),
        sa.Column("degraded_mode", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("usefulness_score", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("metadata", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("prompt_versions")
    op.drop_table("retrieval_episodes")
    op.drop_table("request_log")
    op.drop_table("projects")
    op.drop_table("users")
    op.drop_table("tenants")
