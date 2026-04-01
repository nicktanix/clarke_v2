"""Feedback endpoint with real persistence."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from clarke.api.deps import get_session
from clarke.api.schemas.feedback import FeedbackRequest
from clarke.learning.usefulness import compute_usefulness_score
from clarke.learning.weights import apply_weight_updates
from clarke.settings import get_settings
from clarke.storage.postgres.repositories.episode_repo import get_episode_by_request_id
from clarke.storage.postgres.repositories.feedback_repo import create_feedback
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["feedback"])


@router.post("/feedback", status_code=202)
async def feedback(
    request: FeedbackRequest,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Persist feedback, compute usefulness, trigger weight updates."""
    # Persist feedback record
    await create_feedback(
        session,
        {
            # Let the model default (uuid4) generate the ID
            "request_id": request.request_id,
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "accepted": request.accepted,
            "score": request.score,
            "retrieved_item_ids": request.retrieved_item_ids,
            "notes": request.notes,
        },
    )

    # Look up episode and compute usefulness
    episode = await get_episode_by_request_id(session, request.request_id)
    if episode:
        ucr = episode.usefulness_score or 0.0
        usefulness = compute_usefulness_score(
            feedback_accepted=request.accepted,
            feedback_score=request.score,
            ucr=ucr,
        )

        # Build source usefulness map from retrieval plan
        plan = episode.retrieval_plan or []
        source_usefulness: dict[str, float] = {}
        for req in plan:
            key = f"{req.get('source', 'docs')}:{req.get('strategy', 'direct')}"
            source_usefulness[key] = usefulness

        if source_usefulness:
            settings = get_settings()
            await apply_weight_updates(
                session,
                tenant_id=request.tenant_id,
                source_usefulness=source_usefulness,
                settings=settings.learning,
            )

    # Audit
    from clarke.storage.postgres.repositories.audit_repo import create_audit_event

    await create_audit_event(
        session,
        tenant_id=request.tenant_id,
        actor_id=request.user_id,
        action="feedback_submitted",
        target_type="request",
        target_id=request.request_id,
        metadata={"accepted": request.accepted, "score": request.score},
    )

    await session.commit()

    logger.info("feedback_persisted", request_id=request.request_id)

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "request_id": request.request_id},
    )
