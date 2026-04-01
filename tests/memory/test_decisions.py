"""Decision service tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clarke.memory.decisions import DecisionService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_record_decision(mock_session):
    mock_record = MagicMock()
    mock_record.id = "dec_123"
    mock_record.title = "Use PostgreSQL"
    mock_record.status = "active"

    with patch(
        "clarke.memory.decisions.create_decision", new_callable=AsyncMock, return_value=mock_record
    ):
        service = DecisionService()
        result = await service.record_decision(
            mock_session, "t1", "p1", "Use PostgreSQL", "Better ecosystem", "user1"
        )
        assert result["id"] == "dec_123"
        assert result["status"] == "active"


@pytest.mark.asyncio
async def test_get_relevant_decisions(mock_session):
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
        "clarke.memory.decisions.get_decisions_by_keywords",
        new_callable=AsyncMock,
        return_value=mock_decisions,
    ):
        service = DecisionService()
        result = await service.get_relevant_decisions(mock_session, "t1", "p1", ["websocket"])
        assert len(result) == 1
        assert result[0]["source"] == "decisions"
