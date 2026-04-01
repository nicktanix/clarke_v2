"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from clarke.settings import DatabaseSettings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: DatabaseSettings) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.postgres_url,
        pool_size=settings.pool_size,
        echo=settings.echo,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def dispose_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        yield session
