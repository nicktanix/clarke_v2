"""Agent profiles and session context for Phase 7.

Revision ID: 010
Revises: 009
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=False),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=False),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("system_prompt_override", sa.Text()),
        sa.Column("behavioral_directives", JSONB()),
        sa.Column("capabilities", JSONB()),
        sa.Column("tool_access", JSONB()),
        sa.Column("budget_tokens", sa.Integer(), server_default=sa.text("8000")),
        sa.Column("allowed_sources", JSONB()),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'")),
        sa.Column("version", sa.Integer(), server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_agent_profiles_tenant_slug"),
    )
    op.create_index("ix_agent_profiles_tenant", "agent_profiles", ["tenant_id"])

    op.create_table(
        "agent_session_contexts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column(
            "agent_profile_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent_profiles.id"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("context_snapshot", JSONB()),
        sa.Column("skills_included", JSONB()),
        sa.Column("policies_included", JSONB()),
        sa.Column("token_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("degraded_mode", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("build_latency_ms", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_agent_session_contexts_profile",
        "agent_session_contexts",
        ["agent_profile_id"],
    )
    op.create_index(
        "ix_agent_session_contexts_session",
        "agent_session_contexts",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_table("agent_session_contexts")
    op.drop_table("agent_profiles")
