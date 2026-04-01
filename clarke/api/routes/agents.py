"""Agent management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.agents.lifecycle import cancel_agent, check_expiry
from clarke.agents.results import ingest_result
from clarke.api.deps import get_session
from clarke.api.schemas.agents import (
    AgentStatusResponse,
    CancelAgentRequest,
    IngestResultRequest,
)
from clarke.storage.postgres.repositories.agent_repo import get_agent_instance

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> AgentStatusResponse:
    """Get agent instance status."""
    # Check expiry first
    await check_expiry(session, agent_id)
    await session.commit()

    instance = await get_agent_instance(session, agent_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found") from None

    return AgentStatusResponse(
        id=instance.id,
        tenant_id=instance.tenant_id,
        task_definition=instance.task_definition,
        depth=instance.depth,
        status=instance.status,
        created_at=instance.created_at.isoformat(),
        expires_at=instance.expires_at.isoformat() if instance.expires_at else None,
    )


@router.post("/{agent_id}/result", response_model=dict)
async def submit_agent_result(
    agent_id: str,
    request: IngestResultRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Submit a sub-agent result."""
    instance = await get_agent_instance(session, agent_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found") from None
    if instance.status != "active":
        raise HTTPException(
            status_code=400, detail=f"Agent is {instance.status}, not active"
        ) from None

    result = await ingest_result(
        session=session,
        agent_id=agent_id,
        tenant_id=instance.tenant_id,
        status=request.status,
        summary=request.summary,
        evidence_item_ids=request.evidence_item_ids,
        artifact_refs=request.artifact_refs,
        open_questions=request.open_questions,
    )
    await session.commit()
    return result


@router.post("/{agent_id}/cancel", response_model=dict)
async def cancel_agent_endpoint(
    agent_id: str,
    request: CancelAgentRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Cancel a sub-agent."""
    instance = await get_agent_instance(session, agent_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found") from None

    result = await cancel_agent(session, agent_id, request.reason)
    await session.commit()
    return result
