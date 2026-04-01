"""Repository for request_log table."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import RequestLog


async def create_request_log(session: AsyncSession, data: dict) -> RequestLog:
    record = RequestLog(**data)
    session.add(record)
    await session.flush()
    return record


async def get_request_by_id(session: AsyncSession, request_id: str) -> RequestLog | None:
    result = await session.execute(select(RequestLog).where(RequestLog.request_id == request_id))
    return result.scalar_one_or_none()


async def update_request_log(session: AsyncSession, request_id: str, updates: dict) -> None:
    await session.execute(
        update(RequestLog).where(RequestLog.request_id == request_id).values(**updates)
    )
    await session.flush()
