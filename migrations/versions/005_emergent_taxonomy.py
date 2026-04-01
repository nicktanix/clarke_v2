"""Emergent taxonomy tables for Phase 5.

Revision ID: 005
Revises: 004
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proto_classes",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text()),
        sa.Column("centroid", JSONB()),
        sa.Column("retrieval_signature", JSONB()),
        sa.Column("member_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("stability_score", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("status", sa.Text(), server_default=sa.text("'embryonic'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_proto_classes_tenant_status", "proto_classes", ["tenant_id", "status"])

    op.create_table(
        "class_memberships",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "proto_class_id",
            UUID(as_uuid=False),
            sa.ForeignKey("proto_classes.id"),
            nullable=False,
        ),
        sa.Column("episode_id", sa.Text(), nullable=False),
        sa.Column("feature_vector", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_class_memberships_proto_class_id", "class_memberships", ["proto_class_id"])

    op.create_table(
        "rewrite_templates",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("success_rate", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("usage_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_rewrite_templates_tenant_source", "rewrite_templates", ["tenant_id", "source"]
    )


def downgrade() -> None:
    op.drop_table("rewrite_templates")
    op.drop_table("class_memberships")
    op.drop_table("proto_classes")
