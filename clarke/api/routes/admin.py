"""Admin endpoints for proto-class management."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.deps import get_session
from clarke.api.schemas.admin import (
    ClusterRequest,
    ClusterResponse,
    ProtoClassAction,
    ProtoClassListItem,
    SetupRequest,
    SetupResponse,
)
from clarke.learning.proto_classes import ProtoClassManager
from clarke.settings import get_settings
from clarke.storage.postgres.models import Project, RetrievalEpisode, Tenant

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/setup", response_model=SetupResponse)
async def setup_tenant_project(
    request: SetupRequest,
    session: AsyncSession = Depends(get_session),
) -> SetupResponse:
    """Create a tenant and project for a new CLARKE installation.

    Idempotent: if a tenant with the same name exists, returns the existing IDs.
    """
    from sqlalchemy import select

    # Check for existing tenant by name
    result = await session.execute(select(Tenant).where(Tenant.name == request.tenant_name))
    tenant = result.scalar_one_or_none()
    created = False

    if not tenant:
        tenant = Tenant(name=request.tenant_name)
        session.add(tenant)
        await session.flush()
        created = True

    # Check for existing project
    result = await session.execute(
        select(Project).where(
            Project.tenant_id == tenant.id,
            Project.name == request.project_name,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        project = Project(tenant_id=tenant.id, name=request.project_name)
        session.add(project)
        await session.flush()
        created = True

    await session.commit()

    return SetupResponse(tenant_id=tenant.id, project_id=project.id, created=created)


@router.get("/proto-classes", response_model=list[ProtoClassListItem])
async def list_proto_classes(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[ProtoClassListItem]:
    settings = get_settings()
    manager = ProtoClassManager(settings.taxonomy)
    classes = await manager.list_classes(session, tenant_id)
    return [ProtoClassListItem(**c) for c in classes]


@router.post("/proto-classes/{class_id}/promote", response_model=dict)
async def promote_proto_class(
    class_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    manager = ProtoClassManager(settings.taxonomy)
    result = await manager.promote_class(session, class_id)
    await session.commit()
    return result


@router.post("/proto-classes/{class_id}/merge", response_model=dict)
async def merge_proto_classes(
    class_id: str,
    action: ProtoClassAction,
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    manager = ProtoClassManager(settings.taxonomy)
    result = await manager.merge_classes(session, class_id, action.target_id or "")
    await session.commit()
    return result


@router.post("/proto-classes/{class_id}/split", response_model=dict)
async def split_proto_class(
    class_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    manager = ProtoClassManager(settings.taxonomy)
    result = await manager.split_class(session, class_id)
    await session.commit()
    return result


@router.post("/cluster", response_model=ClusterResponse)
async def trigger_clustering(
    request: ClusterRequest,
    session: AsyncSession = Depends(get_session),
) -> ClusterResponse:
    """Trigger HDBSCAN clustering of retrieval episodes."""
    settings = get_settings()

    # Load episodes
    result = await session.execute(
        select(RetrievalEpisode)
        .where(RetrievalEpisode.tenant_id == request.tenant_id)
        .order_by(RetrievalEpisode.created_at.desc())
        .limit(1000)
    )
    episodes = [
        {
            "id": ep.id,
            "query_features": ep.query_features,
            "retrieval_plan": ep.retrieval_plan,
            "retrieved_items": ep.retrieved_items,
            "usefulness_score": ep.usefulness_score,
        }
        for ep in result.scalars().all()
    ]

    manager = ProtoClassManager(settings.taxonomy)
    classes = await manager.run_clustering(session, request.tenant_id, episodes)
    await session.commit()

    return ClusterResponse(clusters_created=len(classes), classes=classes)


@router.post("/replay", response_model=dict)
async def run_replay(
    tenant_id: str,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Run replay analysis on recent episodes for a tenant."""
    from clarke.evals.replay import ReplayHarness

    harness = ReplayHarness()
    episodes = await harness.load_episodes(session, tenant_id, limit=limit)
    stats = harness.compare_plans(episodes)
    return {"tenant_id": tenant_id, "episodes_analyzed": len(episodes), **stats}


@router.get("/episodes/{request_id}", response_model=dict)
async def get_episode(
    request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get episode detail by request_id for eval scoring."""
    from clarke.storage.postgres.repositories.episode_repo import get_episode_by_request_id

    episode = await get_episode_by_request_id(session, request_id)
    if not episode:
        return {"found": False}
    return {
        "found": True,
        "retrieved_items": episode.retrieved_items or [],
        "injected_items": episode.injected_items or [],
        "retrieval_plan": episode.retrieval_plan or [],
        "query_features": episode.query_features or {},
        "usefulness_score": episode.usefulness_score,
        "degraded_mode": episode.degraded_mode,
    }


@router.get("/trace/{request_id}", response_model=dict)
async def get_trace(
    request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get full trace data for a request (spec §7.1).

    Returns request log, episode, and attributions in a single response.
    """
    from clarke.storage.postgres.repositories.attribution_repo import get_attributions_by_episode
    from clarke.storage.postgres.repositories.episode_repo import get_episode_by_request_id
    from clarke.storage.postgres.repositories.request_repo import get_request_by_id

    request_log = await get_request_by_id(session, request_id)
    if not request_log:
        return {"found": False, "request_id": request_id}

    episode = await get_episode_by_request_id(session, request_id)
    attributions = []
    if episode:
        attr_records = await get_attributions_by_episode(session, episode.id)
        attributions = [
            {
                "item_id": a.item_id,
                "source": a.source,
                "overlap_score": a.overlap_score,
                "attributed": a.attributed,
                "token_count": a.token_count,
            }
            for a in attr_records
        ]

    return {
        "found": True,
        "request_id": request_id,
        "request": {
            "tenant_id": request_log.tenant_id,
            "project_id": request_log.project_id,
            "user_id": request_log.user_id,
            "message": request_log.message,
            "status": request_log.status,
            "degraded_mode": request_log.degraded_mode,
            "prompt_version_id": request_log.prompt_version_id,
            "model_used": request_log.model_used,
            "answer_summary": request_log.answer_summary,
            "latency_ms": request_log.latency_ms,
            "created_at": request_log.created_at.isoformat() if request_log.created_at else None,
        },
        "episode": {
            "query_features": episode.query_features if episode else None,
            "retrieval_plan": episode.retrieval_plan if episode else None,
            "retrieved_items": episode.retrieved_items if episode else [],
            "injected_items": episode.injected_items if episode else [],
            "usefulness_score": episode.usefulness_score if episode else None,
        },
        "attributions": attributions,
    }
