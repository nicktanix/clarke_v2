"""Quota tracking tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from clarke.broker.quotas import check_quota


@pytest.mark.asyncio
async def test_check_quota_no_existing():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    allowed, count = await check_quota(session, "t1", "u1")
    assert allowed is True
    assert count == 0


@pytest.mark.asyncio
async def test_check_quota_under_limit():
    session = AsyncMock()
    mock_quota = MagicMock()
    mock_quota.query_count = 50
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_quota
    session.execute.return_value = mock_result

    allowed, count = await check_quota(session, "t1", "u1", max_queries_per_day=1000)
    assert allowed is True
    assert count == 50


@pytest.mark.asyncio
async def test_check_quota_exceeded():
    session = AsyncMock()
    mock_quota = MagicMock()
    mock_quota.query_count = 1000
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_quota
    session.execute.return_value = mock_result

    allowed, count = await check_quota(session, "t1", "u1", max_queries_per_day=1000)
    assert allowed is False
    assert count == 1000
