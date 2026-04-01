"""Neo4j client wrapper with singleton lifecycle."""

from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from clarke.settings import GraphSettings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


class Neo4jStore:
    def __init__(self, settings: GraphSettings) -> None:
        self._settings = settings
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            self._settings.neo4j_uri,
            auth=(self._settings.neo4j_user, self._settings.neo4j_password),
        )
        await self._driver.verify_connectivity()
        logger.info("neo4j_connected", uri=self._settings.neo4j_uri)

    async def health_check(self) -> bool:
        if not self._driver:
            return False
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def execute_read(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict]:
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        async with self._driver.session(database=self._settings.neo4j_database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict]:
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        async with self._driver.session(database=self._settings.neo4j_database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        return self._driver


# Module-level singleton
_store: Neo4jStore | None = None


async def init_neo4j(settings: GraphSettings) -> None:
    global _store
    _store = Neo4jStore(settings)
    try:
        await _store.connect()
    except Exception:
        logger.warning("neo4j_connection_failed", exc_info=True)
        _store = None


async def dispose_neo4j() -> None:
    global _store
    if _store:
        await _store.close()
        _store = None


def get_neo4j_store() -> Neo4jStore:
    if _store is None:
        raise RuntimeError("Neo4j not initialized. Call init_neo4j() first.")
    return _store
