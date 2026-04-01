"""Graph memory tables for Phase 4.

Revision ID: 004
Revises: 003
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_records",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'")),
        sa.Column("alternatives", JSONB()),
        sa.Column("decided_by", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_decision_records_tenant_project", "decision_records", ["tenant_id", "project_id"]
    )

    op.create_table(
        "policy_nodes",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'")),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("approver_id", sa.Text()),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_policy_nodes_tenant_status", "policy_nodes", ["tenant_id", "status"])

    op.create_table(
        "policy_approvals",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "policy_node_id", UUID(as_uuid=False), sa.ForeignKey("policy_nodes.id"), nullable=False
        ),
        sa.Column("approver_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_policy_approvals_policy_node_id", "policy_approvals", ["policy_node_id"])


def downgrade() -> None:
    op.drop_table("policy_approvals")
    op.drop_table("policy_nodes")
    op.drop_table("decision_records")
