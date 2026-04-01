"""Repository for agent_instances, agent_memory_links, subagent_results tables."""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import AgentInstance, AgentMemoryLink, SubagentResultRecord
from clarke.utils.time import utc_now


async def create_agent_instance(session: AsyncSession, data: dict) -> AgentInstance:
    record = AgentInstance(**data)
    session.add(record)
    await session.flush()
    return record


async def get_agent_instance(session: AsyncSession, agent_id: str) -> AgentInstance | None:
    result = await session.execute(select(AgentInstance).where(AgentInstance.id == agent_id))
    return result.scalar_one_or_none()


async def update_agent_status(
    session: AsyncSession, agent_id: str, status: str, **kwargs: str | None
) -> None:
    values: dict = {"status": status, "last_activity_at": utc_now()}
    if status == "completed":
        values["completed_at"] = utc_now()
    elif status == "cancelled":
        values["cancelled_at"] = utc_now()
    values.update({k: v for k, v in kwargs.items() if v is not None})
    await session.execute(
        update(AgentInstance).where(AgentInstance.id == agent_id).values(**values)
    )
    await session.flush()


async def count_active_agents_for_root(session: AsyncSession, root_agent_id: str) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(AgentInstance)
        .where(
            AgentInstance.root_agent_id == root_agent_id,
            AgentInstance.status == "active",
        )
    )
    return result.scalar_one()


async def create_memory_link(session: AsyncSession, data: dict) -> AgentMemoryLink:
    record = AgentMemoryLink(**data)
    session.add(record)
    await session.flush()
    return record


async def create_subagent_result(session: AsyncSession, data: dict) -> SubagentResultRecord:
    record = SubagentResultRecord(**data)
    session.add(record)
    await session.flush()
    return record


async def get_subagent_result(
    session: AsyncSession, agent_instance_id: str
) -> SubagentResultRecord | None:
    result = await session.execute(
        select(SubagentResultRecord).where(
            SubagentResultRecord.agent_instance_id == agent_instance_id
        )
    )
    return result.scalar_one_or_none()
