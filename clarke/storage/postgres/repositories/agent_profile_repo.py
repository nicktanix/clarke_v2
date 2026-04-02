"""Repository for agent_profiles and agent_session_contexts tables."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import AgentProfile, AgentSessionContext
from clarke.utils.time import utc_now


async def create_agent_profile(session: AsyncSession, data: dict) -> AgentProfile:
    record = AgentProfile(**data)
    session.add(record)
    await session.flush()
    return record


async def get_agent_profile(session: AsyncSession, profile_id: str) -> AgentProfile | None:
    result = await session.execute(select(AgentProfile).where(AgentProfile.id == profile_id))
    return result.scalar_one_or_none()


async def get_agent_profile_by_slug(
    session: AsyncSession, tenant_id: str, slug: str
) -> AgentProfile | None:
    result = await session.execute(
        select(AgentProfile).where(
            AgentProfile.tenant_id == tenant_id,
            AgentProfile.slug == slug,
        )
    )
    return result.scalar_one_or_none()


async def list_agent_profiles(
    session: AsyncSession,
    tenant_id: str,
    status: str | None = "active",
) -> list[AgentProfile]:
    stmt = select(AgentProfile).where(AgentProfile.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(AgentProfile.status == status)
    stmt = stmt.order_by(AgentProfile.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_agent_profile(session: AsyncSession, profile_id: str, data: dict) -> None:
    data["updated_at"] = utc_now()
    await session.execute(update(AgentProfile).where(AgentProfile.id == profile_id).values(**data))
    await session.flush()


async def archive_agent_profile(session: AsyncSession, profile_id: str) -> None:
    await update_agent_profile(session, profile_id, {"status": "archived"})


async def create_session_context(session: AsyncSession, data: dict) -> AgentSessionContext:
    record = AgentSessionContext(**data)
    session.add(record)
    await session.flush()
    return record


async def get_session_context_by_session(
    session: AsyncSession, session_id: str
) -> AgentSessionContext | None:
    result = await session.execute(
        select(AgentSessionContext)
        .where(AgentSessionContext.session_id == session_id)
        .order_by(AgentSessionContext.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
