"""Repository for source_weights table."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import SourceWeight
from clarke.utils.time import utc_now


async def get_weights(session: AsyncSession, tenant_id: str) -> list[SourceWeight]:
    result = await session.execute(select(SourceWeight).where(SourceWeight.tenant_id == tenant_id))
    return list(result.scalars().all())


async def get_or_create_weight(
    session: AsyncSession,
    tenant_id: str,
    source: str,
    strategy: str,
    default_weight: float = 0.5,
    default_epsilon: float = 0.10,
) -> SourceWeight:
    result = await session.execute(
        select(SourceWeight).where(
            SourceWeight.tenant_id == tenant_id,
            SourceWeight.source == source,
            SourceWeight.strategy == strategy,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    record = SourceWeight(
        tenant_id=tenant_id,
        source=source,
        strategy=strategy,
        weight=default_weight,
        epsilon=default_epsilon,
    )
    session.add(record)
    await session.flush()
    return record


async def update_weight(
    session: AsyncSession,
    weight_id: str,
    new_weight: float,
    new_epsilon: float,
) -> None:
    await session.execute(
        update(SourceWeight)
        .where(SourceWeight.id == weight_id)
        .values(
            weight=new_weight,
            epsilon=new_epsilon,
            update_count=SourceWeight.update_count + 1,
            updated_at=utc_now(),
        )
    )
    await session.flush()
