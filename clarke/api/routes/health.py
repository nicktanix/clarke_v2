"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clarke import __version__
from clarke.api.deps import get_session
from clarke.api.schemas.common import HealthCheck, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    checks = []

    try:
        await session.execute(text("SELECT 1"))
        checks.append(HealthCheck(name="postgres", status="ok"))
    except Exception:
        checks.append(HealthCheck(name="postgres", status="error"))

    overall = "ok" if all(c.status == "ok" for c in checks) else "degraded"
    return HealthResponse(status=overall, version=__version__, checks=checks)


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("SELECT 1"))
    return {"ready": True}
