"""Repository for rewrite_templates table."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import RewriteTemplate


async def get_active_templates(
    session: AsyncSession, tenant_id: str, source: str | None = None
) -> list[RewriteTemplate]:
    query = select(RewriteTemplate).where(
        RewriteTemplate.tenant_id == tenant_id,
        RewriteTemplate.is_active.is_(True),
    )
    if source:
        query = query.where(RewriteTemplate.source == source)
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_template(session: AsyncSession, data: dict) -> RewriteTemplate:
    record = RewriteTemplate(**data)
    session.add(record)
    await session.flush()
    return record


async def increment_template_usage(session: AsyncSession, template_id: str) -> None:
    await session.execute(
        update(RewriteTemplate)
        .where(RewriteTemplate.id == template_id)
        .values(usage_count=RewriteTemplate.usage_count + 1)
    )
    await session.flush()
