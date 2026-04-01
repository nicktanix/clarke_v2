"""Repository for proto_classes and class_memberships tables."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import ClassMembership, ProtoClass
from clarke.utils.time import utc_now


async def create_proto_class(session: AsyncSession, data: dict) -> ProtoClass:
    record = ProtoClass(**data)
    session.add(record)
    await session.flush()
    return record


async def get_proto_classes(
    session: AsyncSession, tenant_id: str, status: str | None = None
) -> list[ProtoClass]:
    query = select(ProtoClass).where(ProtoClass.tenant_id == tenant_id)
    if status:
        query = query.where(ProtoClass.status == status)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_proto_class_by_id(session: AsyncSession, class_id: str) -> ProtoClass | None:
    result = await session.execute(select(ProtoClass).where(ProtoClass.id == class_id))
    return result.scalar_one_or_none()


async def update_proto_class(session: AsyncSession, class_id: str, updates: dict) -> None:
    updates["updated_at"] = utc_now()
    await session.execute(update(ProtoClass).where(ProtoClass.id == class_id).values(**updates))
    await session.flush()


async def create_class_membership(session: AsyncSession, data: dict) -> ClassMembership:
    record = ClassMembership(**data)
    session.add(record)
    await session.flush()
    return record
