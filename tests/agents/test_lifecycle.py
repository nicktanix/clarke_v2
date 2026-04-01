"""Agent lifecycle tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clarke.agents.lifecycle import cancel_agent, check_expiry, complete_agent


@pytest.mark.asyncio
async def test_complete_agent():
    session = AsyncMock()
    with patch("clarke.agents.lifecycle.update_agent_status", new_callable=AsyncMock):
        result = await complete_agent(session, "agent_123")
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_cancel_agent():
    session = AsyncMock()
    with patch("clarke.agents.lifecycle.update_agent_status", new_callable=AsyncMock):
        result = await cancel_agent(session, "agent_123", "test reason")
        assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_check_expiry_not_expired():
    session = AsyncMock()
    from datetime import UTC, datetime, timedelta

    mock_instance = MagicMock()
    mock_instance.status = "active"
    mock_instance.expires_at = datetime.now(UTC) + timedelta(hours=1)

    with patch(
        "clarke.agents.lifecycle.get_agent_instance",
        new_callable=AsyncMock,
        return_value=mock_instance,
    ):
        expired = await check_expiry(session, "agent_123")
        assert expired is False


@pytest.mark.asyncio
async def test_check_expiry_expired():
    session = AsyncMock()
    from datetime import UTC, datetime, timedelta

    mock_instance = MagicMock()
    mock_instance.status = "active"
    mock_instance.expires_at = datetime.now(UTC) - timedelta(hours=1)

    with (
        patch(
            "clarke.agents.lifecycle.get_agent_instance",
            new_callable=AsyncMock,
            return_value=mock_instance,
        ),
        patch("clarke.agents.lifecycle.update_agent_status", new_callable=AsyncMock),
    ):
        expired = await check_expiry(session, "agent_123")
        assert expired is True
