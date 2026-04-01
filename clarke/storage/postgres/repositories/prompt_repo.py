"""Repository for prompt_versions table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import PromptVersion


async def get_active_prompt(session: AsyncSession, prompt_type: str) -> PromptVersion | None:
    result = await session.execute(
        select(PromptVersion).where(
            PromptVersion.type == prompt_type,
            PromptVersion.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def create_prompt_version(session: AsyncSession, data: dict) -> PromptVersion:
    record = PromptVersion(**data)
    session.add(record)
    await session.flush()
    return record
