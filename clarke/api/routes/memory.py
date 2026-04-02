"""Memory assessment endpoint — classify and store conversation turns."""

from uuid import uuid4

from fastapi import APIRouter

from clarke.api.schemas.memory import MemoryAssessRequest, MemoryAssessResponse
from clarke.memory.episodic import store_episodic_memory
from clarke.memory.significance import classify_significance
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["memory"])


@router.post("/memory/assess", response_model=MemoryAssessResponse)
async def assess_turn(request: MemoryAssessRequest) -> MemoryAssessResponse:
    """Classify a user/assistant turn and store as episodic memory if significant.

    Called by OpenClaw's afterTurn() hook to auto-persist important interactions.
    """
    sig = classify_significance(
        request.user_message,
        request.assistant_message,
    )

    if sig.should_store:
        request_id = f"r_{uuid4().hex[:24]}"
        try:
            await store_episodic_memory(
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                user_id=request.user_id,
                session_id=request.session_id,
                request_id=request_id,
                message=request.user_message,
                answer=request.assistant_message,
                agent_profile_id=None,
            )
        except Exception:
            logger.warning("memory_assess_store_failed", exc_info=True)

    return MemoryAssessResponse(
        stored=sig.should_store,
        memory_type=sig.memory_type,
        significance_score=sig.score,
        reason=sig.reason,
    )
