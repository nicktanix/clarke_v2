"""Repository for answer_attributions table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import AnswerAttribution


async def create_attributions(
    session: AsyncSession, attributions: list[dict]
) -> list[AnswerAttribution]:
    records = []
    for data in attributions:
        record = AnswerAttribution(**data)
        session.add(record)
        records.append(record)
    await session.flush()
    return records


async def get_attributions_by_episode(
    session: AsyncSession, episode_id: str
) -> list[AnswerAttribution]:
    result = await session.execute(
        select(AnswerAttribution).where(AnswerAttribution.episode_id == episode_id)
    )
    return list(result.scalars().all())
