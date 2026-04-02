"""Self-improvement loop tables for Phase 7b.

Revision ID: 011
Revises: 010
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skill_effectiveness",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column(
            "agent_profile_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent_profiles.id"),
            nullable=False,
        ),
        sa.Column("skill_name", sa.Text(), nullable=False),
        sa.Column("effectiveness", sa.Float(), server_default=sa.text("0.5")),
        sa.Column("update_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("epsilon", sa.Float(), server_default=sa.text("0.10")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "agent_profile_id", "skill_name", name="uq_skill_effectiveness_agent_skill"
        ),
    )
    op.create_index(
        "ix_skill_effectiveness_agent",
        "skill_effectiveness",
        ["agent_profile_id"],
    )

    op.create_table(
        "directive_proposals",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column(
            "agent_profile_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent_profiles.id"),
            nullable=False,
        ),
        sa.Column("proposed_directive", sa.Text(), nullable=False),
        sa.Column("source_memory_ids", JSONB()),
        sa.Column("cluster_size", sa.Integer(), server_default=sa.text("0")),
        sa.Column("similarity_score", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending_approval'")),
        sa.Column("proposed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_by", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_comment", sa.Text()),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("applied_version", sa.Integer()),
    )
    op.create_index(
        "ix_directive_proposals_agent_status",
        "directive_proposals",
        ["agent_profile_id", "status"],
    )

    op.create_table(
        "tenant_signals",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=False),
        sa.Column("source_memory_ids", JSONB()),
        sa.Column("agent_profile_ids", JSONB()),
        sa.Column("agent_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("cluster_size", sa.Integer(), server_default=sa.text("0")),
        sa.Column("similarity_score", sa.Float(), server_default=sa.text("0.0")),
        sa.Column(
            "policy_node_id",
            UUID(as_uuid=False),
            sa.ForeignKey("policy_nodes.id"),
        ),
        sa.Column("status", sa.Text(), server_default=sa.text("'detected'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_tenant_signals_tenant_status",
        "tenant_signals",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("tenant_signals")
    op.drop_table("directive_proposals")
    op.drop_table("skill_effectiveness")
