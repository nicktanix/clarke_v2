"""Multi-agent support tables for Phase 6.

Revision ID: 006
Revises: 005
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_instances",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("root_agent_id", UUID(as_uuid=False)),
        sa.Column("parent_agent_id", UUID(as_uuid=False)),
        sa.Column("parent_request_id", sa.Text()),
        sa.Column("task_definition", sa.Text(), nullable=False),
        sa.Column("memory_scope_mode", sa.Text(), server_default=sa.text("'hybrid'")),
        sa.Column("allowed_sources", JSONB()),
        sa.Column("depth", sa.Integer(), server_default=sa.text("0")),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'")),
        sa.Column("budget_tokens", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancellation_reason", sa.Text()),
    )
    op.create_index("ix_agent_instances_tenant", "agent_instances", ["tenant_id"])
    op.create_index("ix_agent_instances_parent", "agent_instances", ["parent_agent_id"])

    op.create_table(
        "agent_memory_links",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column(
            "parent_agent_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent_instances.id"),
            nullable=False,
        ),
        sa.Column(
            "child_agent_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent_instances.id"),
            nullable=False,
        ),
        sa.Column("parent_episode_id", sa.Text()),
        sa.Column("child_episode_id", sa.Text()),
        sa.Column("handoff_type", sa.Text(), nullable=False),
        sa.Column("linked_item_ids", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_memory_links_parent", "agent_memory_links", ["parent_agent_id"])

    op.create_table(
        "subagent_results",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column(
            "agent_instance_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent_instances.id"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_item_ids", JSONB()),
        sa.Column("artifact_refs", JSONB()),
        sa.Column("open_questions", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_subagent_results_agent", "subagent_results", ["agent_instance_id"])


def downgrade() -> None:
    op.drop_table("subagent_results")
    op.drop_table("agent_memory_links")
    op.drop_table("agent_instances")
