"""Decision API tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_create_decision(client):
    with patch("clarke.api.routes.decisions.DecisionService") as MockService:
        mock_service = AsyncMock()
        mock_service.record_decision.return_value = {
            "id": "dec_123",
            "title": "Use PostgreSQL",
            "status": "active",
        }
        MockService.return_value = mock_service

        response = await client.post(
            "/decisions",
            json={
                "tenant_id": "t1",
                "project_id": "p1",
                "title": "Use PostgreSQL",
                "rationale": "Better ecosystem",
                "decided_by": "u1",
            },
        )
        assert response.status_code == 200
        assert response.json()["id"] == "dec_123"


@pytest.mark.asyncio
async def test_list_decisions(client):
    from datetime import UTC, datetime

    mock_decisions = [
        MagicMock(
            id="d1",
            title="Use WebSockets",
            rationale="Real-time needed",
            status="active",
            decided_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    ]

    with patch(
        "clarke.storage.postgres.repositories.decision_repo.get_decisions_by_project",
        new_callable=AsyncMock,
        return_value=mock_decisions,
    ):
        response = await client.get("/decisions?tenant_id=t1&project_id=p1")
        assert response.status_code == 200
        assert len(response.json()) == 1
