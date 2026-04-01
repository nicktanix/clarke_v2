"""Shared test fixtures."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from clarke.api.app import create_app
from clarke.api.deps import get_broker_service, get_session
from clarke.broker.service import BrokerService


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_broker():
    """Mock broker service."""
    return AsyncMock(spec=BrokerService)


@pytest.fixture
def app(mock_session, mock_broker):
    """Create a test FastAPI application with dependency overrides."""
    application = create_app()

    async def override_session():
        yield mock_session

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_broker_service] = lambda: mock_broker

    return application


@pytest.fixture
async def client(app):
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
