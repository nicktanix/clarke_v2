"""Learning loop tables for Phase 3.

Revision ID: 003
Revises: 002
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_records",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("request_id", sa.Text(), sa.ForeignKey("request_log.request_id"), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("retrieved_item_ids", JSONB()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_feedback_records_request_id", "feedback_records", ["request_id"])

    op.create_table(
        "answer_attributions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("episode_id", sa.Text(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("overlap_score", sa.Float(), nullable=False),
        sa.Column("attributed", sa.Boolean(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_answer_attributions_episode_id", "answer_attributions", ["episode_id"])

    op.create_table(
        "source_weights",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("update_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("epsilon", sa.Float(), server_default=sa.text("0.10")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "source", "strategy", name="uq_source_weights"),
    )

    # Add columns to retrieval_episodes
    op.add_column("retrieval_episodes", sa.Column("episode_id", sa.Text()))
    op.add_column(
        "retrieval_episodes",
        sa.Column("context_request_used", sa.Boolean(), server_default=sa.text("false")),
    )
    op.add_column("retrieval_episodes", sa.Column("second_pass_retrieved_items", JSONB()))
    op.add_column("retrieval_episodes", sa.Column("second_pass_injected_items", JSONB()))
    op.add_column("retrieval_episodes", sa.Column("useful_context_ratio", sa.Float()))


def downgrade() -> None:
    op.drop_column("retrieval_episodes", "useful_context_ratio")
    op.drop_column("retrieval_episodes", "second_pass_injected_items")
    op.drop_column("retrieval_episodes", "second_pass_retrieved_items")
    op.drop_column("retrieval_episodes", "context_request_used")
    op.drop_column("retrieval_episodes", "episode_id")
    op.drop_table("source_weights")
    op.drop_table("answer_attributions")
    op.drop_table("feedback_records")
