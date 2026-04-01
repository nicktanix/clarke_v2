"""Agent lifecycle management — complete, cancel, expire."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.repositories.agent_repo import get_agent_instance, update_agent_status
from clarke.telemetry.logging import get_logger
from clarke.utils.time import utc_now

logger = get_logger(__name__)


async def complete_agent(session: AsyncSession, agent_id: str) -> dict:
    """Mark an agent as completed."""
    await update_agent_status(session, agent_id, "completed")
    return {"id": agent_id, "status": "completed"}


async def cancel_agent(
    session: AsyncSession, agent_id: str, reason: str = "cancelled by parent"
) -> dict:
    """Cancel an agent."""
    await update_agent_status(session, agent_id, "cancelled", cancellation_reason=reason)
    return {"id": agent_id, "status": "cancelled"}


async def check_expiry(session: AsyncSession, agent_id: str) -> bool:
    """Check if an agent has expired. If so, mark it expired. Returns True if expired."""
    instance = await get_agent_instance(session, agent_id)
    if not instance:
        return True

    if instance.status != "active":
        return instance.status in ("expired", "cancelled")

    if instance.expires_at and instance.expires_at < utc_now():
        await update_agent_status(session, agent_id, "expired")
        logger.info("agent_expired", agent_id=agent_id)
        return True

    return False
