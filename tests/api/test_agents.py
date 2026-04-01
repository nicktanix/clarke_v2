"""Agent API tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_agent_status(client, mock_session):
    from datetime import UTC, datetime, timedelta

    mock_instance = MagicMock()
    mock_instance.id = "agent_123"
    mock_instance.tenant_id = "t1"
    mock_instance.task_definition = "Analyze tradeoffs"
    mock_instance.depth = 1
    mock_instance.status = "active"
    mock_instance.created_at = datetime.now(UTC)
    mock_instance.expires_at = datetime.now(UTC) + timedelta(hours=1)

    with (
        patch("clarke.api.routes.agents.check_expiry", new_callable=AsyncMock, return_value=False),
        patch(
            "clarke.api.routes.agents.get_agent_instance",
            new_callable=AsyncMock,
            return_value=mock_instance,
        ),
    ):
        response = await client.get("/agents/agent_123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "agent_123"
        assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_agent_not_found(client, mock_session):
    with (
        patch("clarke.api.routes.agents.check_expiry", new_callable=AsyncMock, return_value=True),
        patch(
            "clarke.api.routes.agents.get_agent_instance",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        response = await client.get("/agents/nonexistent")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_agent(client, mock_session):
    mock_instance = MagicMock()
    mock_instance.id = "agent_123"

    with (
        patch(
            "clarke.api.routes.agents.get_agent_instance",
            new_callable=AsyncMock,
            return_value=mock_instance,
        ),
        patch(
            "clarke.api.routes.agents.cancel_agent",
            new_callable=AsyncMock,
            return_value={"id": "agent_123", "status": "cancelled"},
        ),
    ):
        response = await client.post(
            "/agents/agent_123/cancel",
            json={"reason": "no longer needed"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
