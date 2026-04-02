"""Row-Level Security policies for tenant isolation (spec §6.1).

Revision ID: 009
Revises: 008
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that carry tenant_id and should have RLS
_TENANT_TABLES = [
    "request_log",
    "retrieval_episodes",
    "documents",
    "chunks",
    "ingestion_jobs",
    "feedback_records",
    "answer_attributions",
    "source_weights",
    "decision_records",
    "policy_nodes",
    "policy_approvals",
    "proto_classes",
    "class_memberships",
    "rewrite_templates",
    "agent_instances",
    "agent_memory_links",
    "subagent_results",
    "blending_weights",
    "usage_quotas",
]


def upgrade() -> None:
    conn = op.get_bind()
    for table in _TENANT_TABLES:
        # Only apply RLS to tables that actually have a tenant_id column
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :tbl AND column_name = 'tenant_id'"
            ),
            {"tbl": table},
        )
        if not result.fetchone():
            continue
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            f"USING (tenant_id = current_setting('app.tenant_id', true))"
        )


def downgrade() -> None:
    for table in reversed(_TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
