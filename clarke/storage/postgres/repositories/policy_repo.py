"""Repository for policy_nodes and policy_approvals tables."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import PolicyApproval, PolicyNode
from clarke.utils.time import utc_now


async def create_policy_node(session: AsyncSession, data: dict) -> PolicyNode:
    record = PolicyNode(**data)
    session.add(record)
    await session.flush()
    return record


async def get_active_policies(session: AsyncSession, tenant_id: str) -> list[PolicyNode]:
    now = utc_now()
    result = await session.execute(
        select(PolicyNode).where(
            PolicyNode.tenant_id == tenant_id,
            PolicyNode.status == "active",
            (PolicyNode.effective_from.is_(None)) | (PolicyNode.effective_from <= now),
            (PolicyNode.effective_to.is_(None)) | (PolicyNode.effective_to >= now),
        )
    )
    return list(result.scalars().all())


async def get_policy_by_id(session: AsyncSession, policy_id: str) -> PolicyNode | None:
    result = await session.execute(select(PolicyNode).where(PolicyNode.id == policy_id))
    return result.scalar_one_or_none()


async def update_policy_status(
    session: AsyncSession, policy_id: str, status: str, **kwargs: str | None
) -> None:
    values: dict = {"status": status}
    values.update({k: v for k, v in kwargs.items() if v is not None})
    await session.execute(update(PolicyNode).where(PolicyNode.id == policy_id).values(**values))
    await session.flush()


async def create_policy_approval(session: AsyncSession, data: dict) -> PolicyApproval:
    record = PolicyApproval(**data)
    session.add(record)
    await session.flush()
    return record
