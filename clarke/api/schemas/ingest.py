"""Ingestion API schemas."""

from pydantic import BaseModel


class IngestDocumentRequest(BaseModel):
    tenant_id: str
    project_id: str
    filename: str
    content_type: str = "text/markdown"
    content: str
    source_url: str | None = None
    metadata: dict | None = None


class IngestDocumentResponse(BaseModel):
    document_id: str
    job_id: str
    status: str


class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    content_type: str
    status: str
    chunk_count: int
    created_at: str
    metadata: dict | None = None
