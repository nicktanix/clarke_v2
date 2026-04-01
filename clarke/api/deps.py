"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.broker.service import BrokerService
from clarke.settings import Settings, get_settings
from clarke.storage.postgres.database import get_db_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_app_settings() -> Settings:
    return get_settings()


def get_broker_service() -> BrokerService:
    return BrokerService()
