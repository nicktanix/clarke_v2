"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from clarke import __version__
from clarke.api.middleware import RequestIdMiddleware
from clarke.api.routes import (
    admin,
    agents,
    decisions,
    directives,
    feedback,
    health,
    ingest,
    memory,
    policy,
    query,
)
from clarke.retrieval.neo4j.client import dispose_neo4j, init_neo4j
from clarke.retrieval.qdrant.client import dispose_qdrant, init_qdrant
from clarke.settings import get_settings
from clarke.storage.postgres.database import dispose_db, init_db
from clarke.telemetry.logging import configure_logging
from clarke.telemetry.tracing import init_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.telemetry.log_level)
    init_tracing(settings.telemetry)
    init_db(settings.db)
    await init_qdrant(settings.retrieval, settings.embedding)
    if settings.graph.graph_enabled:
        await init_neo4j(settings.graph)
    yield
    await dispose_neo4j()
    await dispose_qdrant()
    await dispose_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CLARKE Broker API",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    app.include_router(query.router)
    app.include_router(feedback.router)
    app.include_router(ingest.router)
    app.include_router(policy.router)
    app.include_router(decisions.router)
    app.include_router(agents.router)
    app.include_router(memory.router)
    app.include_router(directives.router)
    app.include_router(admin.router)

    return app
