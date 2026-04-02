"""Agent management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.agents.lifecycle import cancel_agent, check_expiry
from clarke.agents.results import ingest_result
from clarke.agents.session_context import (
    SessionContextBuilder,
    render_session_context_markdown,
)
from clarke.api.deps import get_session
from clarke.api.schemas.agents import (
    AgentStatusResponse,
    CancelAgentRequest,
    IngestResultRequest,
)
from clarke.api.schemas.ingest import IngestDocumentRequest
from clarke.api.schemas.session_context import (
    AgentProfileResponse,
    BuildSessionContextRequest,
    CreateAgentProfileRequest,
    IngestSkillRequest,
    UpdateAgentProfileRequest,
)
from clarke.storage.postgres.repositories.agent_profile_repo import (
    archive_agent_profile,
    create_agent_profile,
    get_agent_profile,
    list_agent_profiles,
    update_agent_profile,
)
from clarke.storage.postgres.repositories.agent_repo import get_agent_instance

router = APIRouter(prefix="/agents", tags=["agents"])


# --- Phase 7: Agent Profiles & Session Context ---
# These specific-path routes MUST be defined before the /{agent_id} catch-all.


@router.post("/profiles", response_model=AgentProfileResponse, status_code=201)
async def create_profile(
    request: CreateAgentProfileRequest,
    session: AsyncSession = Depends(get_session),
) -> AgentProfileResponse:
    """Create an agent profile."""
    profile = await create_agent_profile(session, request.model_dump())
    await session.commit()
    return AgentProfileResponse(
        id=profile.id,
        tenant_id=profile.tenant_id,
        project_id=profile.project_id,
        name=profile.name,
        slug=profile.slug,
        model_id=profile.model_id,
        capabilities=profile.capabilities or [],
        tool_access=profile.tool_access or [],
        budget_tokens=profile.budget_tokens,
        status=profile.status,
        version=profile.version,
    )


@router.get("/profiles/{profile_id}", response_model=AgentProfileResponse)
async def get_profile(
    profile_id: str,
    session: AsyncSession = Depends(get_session),
) -> AgentProfileResponse:
    """Get an agent profile by ID."""
    profile = await get_agent_profile(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found") from None
    return AgentProfileResponse(
        id=profile.id,
        tenant_id=profile.tenant_id,
        project_id=profile.project_id,
        name=profile.name,
        slug=profile.slug,
        model_id=profile.model_id,
        capabilities=profile.capabilities or [],
        tool_access=profile.tool_access or [],
        budget_tokens=profile.budget_tokens,
        status=profile.status,
        version=profile.version,
    )


@router.get("/profiles", response_model=list[AgentProfileResponse])
async def list_profiles(
    tenant_id: str,
    status: str | None = "active",
    session: AsyncSession = Depends(get_session),
) -> list[AgentProfileResponse]:
    """List agent profiles for a tenant."""
    profiles = await list_agent_profiles(session, tenant_id, status)
    return [
        AgentProfileResponse(
            id=p.id,
            tenant_id=p.tenant_id,
            project_id=p.project_id,
            name=p.name,
            slug=p.slug,
            model_id=p.model_id,
            capabilities=p.capabilities or [],
            tool_access=p.tool_access or [],
            budget_tokens=p.budget_tokens,
            status=p.status,
            version=p.version,
        )
        for p in profiles
    ]


@router.put("/profiles/{profile_id}", response_model=AgentProfileResponse)
async def update_profile(
    profile_id: str,
    request: UpdateAgentProfileRequest,
    session: AsyncSession = Depends(get_session),
) -> AgentProfileResponse:
    """Update an agent profile. Bumps the version."""
    profile = await get_agent_profile(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found") from None

    update_data = request.model_dump(exclude_none=True)
    update_data["version"] = profile.version + 1
    await update_agent_profile(session, profile_id, update_data)
    await session.commit()

    profile = await get_agent_profile(session, profile_id)
    return AgentProfileResponse(
        id=profile.id,
        tenant_id=profile.tenant_id,
        project_id=profile.project_id,
        name=profile.name,
        slug=profile.slug,
        model_id=profile.model_id,
        capabilities=profile.capabilities or [],
        tool_access=profile.tool_access or [],
        budget_tokens=profile.budget_tokens,
        status=profile.status,
        version=profile.version,
    )


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Archive (soft delete) an agent profile."""
    profile = await get_agent_profile(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found") from None
    await archive_agent_profile(session, profile_id)
    await session.commit()


@router.post("/session-context")
async def build_session_context(
    request: BuildSessionContextRequest,
    session: AsyncSession = Depends(get_session),
):
    """Build dynamic session context for an agent."""
    if not request.agent_profile_id and not request.agent_slug:
        raise HTTPException(
            status_code=400,
            detail="Either agent_profile_id or agent_slug is required",
        ) from None

    builder = SessionContextBuilder()
    try:
        pack = await builder.build(request, session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if request.format == "markdown":
        return PlainTextResponse(
            content=render_session_context_markdown(pack),
            media_type="text/markdown",
        )
    return pack


@router.post("/skills", status_code=201)
async def ingest_skill(
    request: IngestSkillRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Ingest a skill document into CLARKE."""
    from clarke.ingestion.service import IngestionService
    from clarke.settings import get_settings

    ingest_request = IngestDocumentRequest(
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        filename=f"skill_{request.skill_name}.md",
        content_type="text/markdown",
        content=request.content,
        metadata={
            "doc_type": "skill",
            "skill_name": request.skill_name,
            "trigger_conditions": request.trigger_conditions,
            "tool_access": request.tool_access,
            "agent_capabilities": request.agent_capabilities,
            "priority": request.priority,
        },
    )

    service = IngestionService(get_settings())
    result = await service.ingest_document(ingest_request, session)
    return {
        "document_id": result.document_id,
        "skill_name": request.skill_name,
        "status": result.status,
    }


# --- Agent Instance endpoints (Phase 6) ---
# These use /{agent_id} catch-all and MUST come after specific-path routes.


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
