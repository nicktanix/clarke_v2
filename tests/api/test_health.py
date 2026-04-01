"""Health endpoint tests."""

import pytest

from clarke import __version__


@pytest.mark.asyncio
async def test_health_returns_200(client, mock_session):
    mock_session.execute.return_value = None
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_health_includes_version(client, mock_session):
    mock_session.execute.return_value = None
    response = await client.get("/health")
    assert response.json()["version"] == __version__


@pytest.mark.asyncio
async def test_ready_returns_200(client, mock_session):
    mock_session.execute.return_value = None
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True
