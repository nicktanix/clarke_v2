"""Usage quotas table for per-user/tenant daily budgets.

Revision ID: 008
Revises: 007
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_quotas",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("date", sa.Text(), nullable=False),
        sa.Column("query_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("token_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "user_id", "date", name="uq_usage_quotas"),
    )
    op.create_index("ix_usage_quotas_tenant_date", "usage_quotas", ["tenant_id", "date"])


def downgrade() -> None:
    op.drop_table("usage_quotas")
