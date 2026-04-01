"""Per-user and per-tenant daily quota tracking (spec §6.4)."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import UsageQuota
from clarke.telemetry.logging import get_logger
from clarke.utils.time import utc_now

logger = get_logger(__name__)


async def check_quota(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    max_queries_per_day: int = 1000,
) -> tuple[bool, int]:
    """Check if user has remaining quota. Returns (allowed, current_count)."""
    today = utc_now().strftime("%Y-%m-%d")

    result = await session.execute(
        select(UsageQuota).where(
            UsageQuota.tenant_id == tenant_id,
            UsageQuota.user_id == user_id,
            UsageQuota.date == today,
        )
    )
    quota = result.scalar_one_or_none()

    if not quota:
        return True, 0

    return quota.query_count < max_queries_per_day, quota.query_count


async def increment_quota(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    token_count: int = 0,
) -> None:
    """Increment the daily query count for a user."""
    today = utc_now().strftime("%Y-%m-%d")

    result = await session.execute(
        select(UsageQuota).where(
            UsageQuota.tenant_id == tenant_id,
            UsageQuota.user_id == user_id,
            UsageQuota.date == today,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await session.execute(
            update(UsageQuota)
            .where(UsageQuota.id == existing.id)
            .values(
                query_count=UsageQuota.query_count + 1,
                token_count=UsageQuota.token_count + token_count,
            )
        )
    else:
        session.add(
            UsageQuota(
                tenant_id=tenant_id,
                user_id=user_id,
                date=today,
                query_count=1,
                token_count=token_count,
            )
        )
    await session.flush()
