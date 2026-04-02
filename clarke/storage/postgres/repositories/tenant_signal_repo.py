"""Repository for tenant_signals table."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import TenantSignal
from clarke.utils.time import utc_now


async def create_signal(session: AsyncSession, data: dict) -> TenantSignal:
    record = TenantSignal(**data)
    session.add(record)
    await session.flush()
    return record


async def list_signals(
    session: AsyncSession,
    tenant_id: str,
    status: str | None = None,
) -> list[TenantSignal]:
    stmt = select(TenantSignal).where(TenantSignal.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(TenantSignal.status == status)
    stmt = stmt.order_by(TenantSignal.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_signal_status(
    session: AsyncSession,
    signal_id: str,
    status: str,
    policy_node_id: str | None = None,
) -> None:
    values: dict = {"status": status, "updated_at": utc_now()}
    if policy_node_id:
        values["policy_node_id"] = policy_node_id
    await session.execute(update(TenantSignal).where(TenantSignal.id == signal_id).values(**values))
    await session.flush()
