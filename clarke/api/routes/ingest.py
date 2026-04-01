"""Ingestion endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.deps import get_session
from clarke.api.schemas.ingest import (
    DocumentStatusResponse,
    IngestDocumentRequest,
    IngestDocumentResponse,
)
from clarke.ingestion.service import IngestionService
from clarke.settings import get_settings

router = APIRouter(tags=["ingestion"])


@router.post("/ingest", response_model=IngestDocumentResponse)
async def ingest_document(
    request: IngestDocumentRequest,
    session: AsyncSession = Depends(get_session),
) -> IngestDocumentResponse:
    service = IngestionService(get_settings())
    return await service.ingest_document(request, session)


@router.get("/documents/{document_id}", response_model=DocumentStatusResponse)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> DocumentStatusResponse:
    service = IngestionService(get_settings())
    try:
        return await service.get_document_status(document_id, session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
