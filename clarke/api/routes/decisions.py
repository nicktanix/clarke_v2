"""Decision management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.deps import get_session
from clarke.api.schemas.decisions import (
    CreateDecisionRequest,
    DecisionListItem,
    DecisionResponse,
)
from clarke.memory.decisions import DecisionService
from clarke.storage.postgres.repositories.audit_repo import create_audit_event

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("", response_model=DecisionResponse)
async def create_decision(
    request: CreateDecisionRequest,
    session: AsyncSession = Depends(get_session),
) -> DecisionResponse:
    service = DecisionService()
    result = await service.record_decision(
        session,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        title=request.title,
        rationale=request.rationale,
        decided_by=request.decided_by,
        alternatives=request.alternatives,
    )
    await create_audit_event(
        session,
        tenant_id=request.tenant_id,
        actor_id=request.decided_by,
        action="decision_recorded",
        target_type="decision",
        target_id=result["id"],
        metadata={"title": request.title},
    )
    await session.commit()
    return DecisionResponse(**result)


@router.get("", response_model=list[DecisionListItem])
async def list_decisions(
    tenant_id: str,
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[DecisionListItem]:
    from clarke.storage.postgres.repositories.decision_repo import get_decisions_by_project

    decisions = await get_decisions_by_project(session, tenant_id, project_id)
    return [
        DecisionListItem(
            id=d.id,
            title=d.title,
            rationale=d.rationale,
            status=d.status,
            decided_at=d.decided_at.isoformat(),
        )
        for d in decisions
    ]
