"""Directive proposal endpoints for agent self-improvement."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.deps import get_session
from clarke.api.schemas.directives import (
    ApproveDirectiveRequest,
    DirectiveProposalResponse,
    RejectDirectiveRequest,
)
from clarke.learning.directive_service import DirectiveService

router = APIRouter(prefix="/agents/profiles", tags=["directives"])


@router.get(
    "/{profile_id}/directives/proposals",
    response_model=list[DirectiveProposalResponse],
)
async def list_directive_proposals(
    profile_id: str,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[DirectiveProposalResponse]:
    """List directive proposals for an agent profile."""
    service = DirectiveService()
    proposals = await service.get_proposals(session, profile_id, status)
    return [DirectiveProposalResponse(**p) for p in proposals]


@router.post(
    "/{profile_id}/directives/proposals/{proposal_id}/approve",
    response_model=dict,
)
async def approve_directive(
    profile_id: str,
    proposal_id: str,
    request: ApproveDirectiveRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Approve and apply a directive proposal."""
    service = DirectiveService()
    try:
        result = await service.approve_proposal(
            session, proposal_id, request.approver_id, request.comment
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/{profile_id}/directives/proposals/{proposal_id}/reject",
    response_model=dict,
)
async def reject_directive(
    profile_id: str,
    proposal_id: str,
    request: RejectDirectiveRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Reject a directive proposal."""
    service = DirectiveService()
    try:
        result = await service.reject_proposal(
            session, proposal_id, request.approver_id, request.comment
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{profile_id}/directives/detect", response_model=list[dict])
async def trigger_directive_detection(
    profile_id: str,
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Manually trigger directive detection for an agent profile."""
    from clarke.learning.directive_surfacing import detect_directive_candidates
    from clarke.settings import get_settings

    settings = get_settings()
    proposals = await detect_directive_candidates(
        tenant_id,
        profile_id,
        session,
        settings.self_improvement,
    )
    await session.commit()
    return proposals
