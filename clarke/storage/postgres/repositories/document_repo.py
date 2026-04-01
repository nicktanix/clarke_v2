"""Repository for documents, chunks, and ingestion_jobs tables."""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import Chunk, Document, IngestionJob
from clarke.utils.time import utc_now


async def create_document(session: AsyncSession, data: dict) -> Document:
    record = Document(**data)
    session.add(record)
    await session.flush()
    return record


async def update_document_status(session: AsyncSession, document_id: str, status: str) -> None:
    await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(status=status, updated_at=utc_now())
    )
    await session.flush()


async def get_document(session: AsyncSession, document_id: str) -> Document | None:
    result = await session.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def create_chunks(session: AsyncSession, chunks: list[dict]) -> None:
    for chunk_data in chunks:
        session.add(Chunk(**chunk_data))
    await session.flush()


async def get_chunk_count(session: AsyncSession, document_id: str) -> int:
    result = await session.execute(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    )
    return result.scalar_one()


async def create_ingestion_job(session: AsyncSession, data: dict) -> IngestionJob:
    record = IngestionJob(**data)
    session.add(record)
    await session.flush()
    return record


async def update_ingestion_job(
    session: AsyncSession, job_id: str, status: str, error: str | None = None
) -> None:
    values: dict = {"status": status}
    if status == "running":
        values["started_at"] = utc_now()
    elif status in ("completed", "failed"):
        values["completed_at"] = utc_now()
    if error:
        values["error_message"] = error
    await session.execute(update(IngestionJob).where(IngestionJob.id == job_id).values(**values))
    await session.flush()
