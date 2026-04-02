"""Repository for directive_proposals table."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.models import DirectiveProposal
from clarke.utils.time import utc_now


async def create_proposal(session: AsyncSession, data: dict) -> DirectiveProposal:
    record = DirectiveProposal(**data)
    session.add(record)
    await session.flush()
    return record


async def get_proposal(session: AsyncSession, proposal_id: str) -> DirectiveProposal | None:
    result = await session.execute(
        select(DirectiveProposal).where(DirectiveProposal.id == proposal_id)
    )
    return result.scalar_one_or_none()


async def list_proposals(
    session: AsyncSession,
    agent_profile_id: str,
    status: str | None = None,
) -> list[DirectiveProposal]:
    stmt = select(DirectiveProposal).where(DirectiveProposal.agent_profile_id == agent_profile_id)
    if status:
        stmt = stmt.where(DirectiveProposal.status == status)
    stmt = stmt.order_by(DirectiveProposal.proposed_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_proposal_status(
    session: AsyncSession,
    proposal_id: str,
    status: str,
    reviewed_by: str | None = None,
    review_comment: str | None = None,
    applied_version: int | None = None,
) -> None:
    values: dict = {"status": status}
    if reviewed_by:
        values["reviewed_by"] = reviewed_by
        values["reviewed_at"] = utc_now()
    if review_comment is not None:
        values["review_comment"] = review_comment
    if status == "applied":
        values["applied_at"] = utc_now()
    if applied_version is not None:
        values["applied_version"] = applied_version
    await session.execute(
        update(DirectiveProposal).where(DirectiveProposal.id == proposal_id).values(**values)
    )
    await session.flush()


async def find_similar_proposals(
    session: AsyncSession,
    agent_profile_id: str,
) -> list[DirectiveProposal]:
    """Get non-rejected proposals for deduplication."""
    result = await session.execute(
        select(DirectiveProposal).where(
            DirectiveProposal.agent_profile_id == agent_profile_id,
            DirectiveProposal.status.notin_(["rejected"]),
        )
    )
    return list(result.scalars().all())
