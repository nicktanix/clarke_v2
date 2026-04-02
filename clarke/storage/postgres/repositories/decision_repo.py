"""Repository for decision_records table."""

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import DecisionRecord


async def create_decision(session: AsyncSession, data: dict) -> DecisionRecord:
    record = DecisionRecord(**data)
    session.add(record)
    await session.flush()
    return record


async def get_decisions_by_project(
    session: AsyncSession,
    tenant_id: str,
    project_id: str,
    status: str = "active",
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DecisionRecord], int]:
    base = select(DecisionRecord).where(
        DecisionRecord.tenant_id == tenant_id,
        DecisionRecord.project_id == project_id,
        DecisionRecord.status == status,
    )
    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                DecisionRecord.title.ilike(pattern),
                DecisionRecord.rationale.ilike(pattern),
            )
        )

    count_result = await session.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    result = await session.execute(base.offset(offset).limit(limit))
    return list(result.scalars().all()), total


async def get_decisions_by_keywords(
    session: AsyncSession,
    tenant_id: str,
    project_id: str,
    keywords: list[str],
    limit: int = 5,
) -> list[DecisionRecord]:
    if not keywords:
        return []

    conditions = []
    for kw in keywords:
        pattern = f"%{kw}%"
        conditions.append(DecisionRecord.title.ilike(pattern))
        conditions.append(DecisionRecord.rationale.ilike(pattern))

    result = await session.execute(
        select(DecisionRecord)
        .where(
            DecisionRecord.tenant_id == tenant_id,
            DecisionRecord.project_id == project_id,
            DecisionRecord.status == "active",
            or_(*conditions),
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_decision_status(session: AsyncSession, decision_id: str, status: str) -> None:
    await session.execute(
        update(DecisionRecord).where(DecisionRecord.id == decision_id).values(status=status)
    )
    await session.flush()
