"""Policy service tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from clarke.memory.policy import PolicyService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_create_policy(mock_session):
    from unittest.mock import patch

    mock_record = MagicMock()
    mock_record.id = "pol_123"
    mock_record.status = "draft"

    with patch(
        "clarke.memory.policy.create_policy_node", new_callable=AsyncMock, return_value=mock_record
    ):
        service = PolicyService()
        result = await service.create_policy(mock_session, "t1", "No direct DB access", "user1")
        assert result["id"] == "pol_123"
        assert result["status"] == "draft"


@pytest.mark.asyncio
async def test_get_active_policies(mock_session):
    from unittest.mock import patch

    mock_policies = [
        MagicMock(id="p1", content="Policy one", status="active"),
        MagicMock(id="p2", content="Policy two", status="active"),
    ]

    with patch(
        "clarke.memory.policy.get_active_policies",
        new_callable=AsyncMock,
        return_value=mock_policies,
    ):
        service = PolicyService()
        result = await service.get_active(mock_session, "t1")
        assert len(result) == 2
        assert result[0]["source"] == "policy"
