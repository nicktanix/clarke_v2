"""Repository for skill_effectiveness table."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import SkillEffectiveness
from clarke.utils.time import utc_now


async def get_or_create(
    session: AsyncSession,
    agent_profile_id: str,
    tenant_id: str,
    skill_name: str,
    default_effectiveness: float = 0.5,
    default_epsilon: float = 0.10,
) -> SkillEffectiveness:
    result = await session.execute(
        select(SkillEffectiveness).where(
            SkillEffectiveness.agent_profile_id == agent_profile_id,
            SkillEffectiveness.skill_name == skill_name,
        )
    )
    record = result.scalar_one_or_none()
    if record:
        return record

    record = SkillEffectiveness(
        tenant_id=tenant_id,
        agent_profile_id=agent_profile_id,
        skill_name=skill_name,
        effectiveness=default_effectiveness,
        epsilon=default_epsilon,
    )
    session.add(record)
    await session.flush()
    return record


async def update_effectiveness(
    session: AsyncSession,
    record_id: str,
    new_effectiveness: float,
    new_epsilon: float,
) -> None:
    await session.execute(
        update(SkillEffectiveness)
        .where(SkillEffectiveness.id == record_id)
        .values(
            effectiveness=new_effectiveness,
            epsilon=new_epsilon,
            update_count=SkillEffectiveness.update_count + 1,
            updated_at=utc_now(),
        )
    )
    await session.flush()


async def get_all_for_agent(
    session: AsyncSession,
    agent_profile_id: str,
) -> list[SkillEffectiveness]:
    result = await session.execute(
        select(SkillEffectiveness).where(SkillEffectiveness.agent_profile_id == agent_profile_id)
    )
    return list(result.scalars().all())
