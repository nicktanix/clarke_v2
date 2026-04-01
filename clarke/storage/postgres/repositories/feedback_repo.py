"""Repository for feedback_records table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import FeedbackRecord


async def create_feedback(session: AsyncSession, data: dict) -> FeedbackRecord:
    record = FeedbackRecord(**data)
    session.add(record)
    await session.flush()
    return record


async def get_feedback_by_request_id(
    session: AsyncSession, request_id: str
) -> list[FeedbackRecord]:
    result = await session.execute(
        select(FeedbackRecord).where(FeedbackRecord.request_id == request_id)
    )
    return list(result.scalars().all())
