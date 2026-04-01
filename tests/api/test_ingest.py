"""Ingest endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest

from clarke.api.schemas.ingest import DocumentStatusResponse, IngestDocumentResponse


@pytest.mark.asyncio
async def test_ingest_valid_request(client):
    mock_response = IngestDocumentResponse(
        document_id="doc_123",
        job_id="job_456",
        status="completed",
    )

    with patch("clarke.api.routes.ingest.IngestionService") as MockService:
        mock_service = AsyncMock()
        mock_service.ingest_document.return_value = mock_response
        MockService.return_value = mock_service

        response = await client.post(
            "/ingest",
            json={
                "tenant_id": "t_001",
                "project_id": "p_001",
                "filename": "test.md",
                "content_type": "text/markdown",
                "content": "# Test\n\nHello world.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "doc_123"
        assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_ingest_missing_content(client):
    response = await client.post(
        "/ingest",
        json={
            "tenant_id": "t_001",
            "project_id": "p_001",
            "filename": "test.md",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_document_status(client):
    mock_response = DocumentStatusResponse(
        document_id="doc_123",
        filename="test.md",
        content_type="text/markdown",
        status="ready",
        chunk_count=5,
        created_at="2026-04-01T00:00:00Z",
    )

    with patch("clarke.api.routes.ingest.IngestionService") as MockService:
        mock_service = AsyncMock()
        mock_service.get_document_status.return_value = mock_response
        MockService.return_value = mock_service

        response = await client.get("/documents/doc_123")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "doc_123"
        assert data["chunk_count"] == 5


@pytest.mark.asyncio
async def test_get_document_not_found(client):
    with patch("clarke.api.routes.ingest.IngestionService") as MockService:
        mock_service = AsyncMock()
        mock_service.get_document_status.side_effect = ValueError("Not found")
        MockService.return_value = mock_service

        response = await client.get("/documents/nonexistent")
        assert response.status_code == 404
