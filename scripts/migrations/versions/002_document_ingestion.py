"""Document ingestion tables for Phase 2.

Revision ID: 002
Revises: 001
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'")),
        sa.Column("metadata", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_tenant_project", "documents", ["tenant_id", "project_id"])

    op.create_table(
        "chunks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "document_id", UUID(as_uuid=False), sa.ForeignKey("documents.id"), nullable=False
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_tenant_id", "chunks", ["tenant_id"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column(
            "document_id", UUID(as_uuid=False), sa.ForeignKey("documents.id"), nullable=False
        ),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"])


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_table("chunks")
    op.drop_table("documents")
