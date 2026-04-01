"""Repository for retrieval_episodes table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import RetrievalEpisode


async def create_episode(session: AsyncSession, data: dict) -> RetrievalEpisode:
    record = RetrievalEpisode(**data)
    session.add(record)
    await session.flush()
    return record


async def get_episode_by_request_id(
    session: AsyncSession, request_id: str
) -> RetrievalEpisode | None:
    result = await session.execute(
        select(RetrievalEpisode).where(RetrievalEpisode.request_id == request_id)
    )
    return result.scalar_one_or_none()
