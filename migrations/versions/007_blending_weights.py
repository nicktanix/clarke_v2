"""Blending weights table for learned retrieval scoring.

Revision ID: 007
Revises: 006
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blending_weights",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("alpha_semantic", sa.Float(), server_default=sa.text("0.35")),
        sa.Column("beta_graph", sa.Float(), server_default=sa.text("0.15")),
        sa.Column("gamma_recency", sa.Float(), server_default=sa.text("0.10")),
        sa.Column("delta_trust", sa.Float(), server_default=sa.text("0.25")),
        sa.Column("epsilon_lexical", sa.Float(), server_default=sa.text("0.10")),
        sa.Column("zeta_cost_penalty", sa.Float(), server_default=sa.text("0.05")),
        sa.Column("update_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_blending_weights_tenant"),
    )


def downgrade() -> None:
    op.drop_table("blending_weights")
