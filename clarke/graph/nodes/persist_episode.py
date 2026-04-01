"""Persist request log and retrieval episode to PostgreSQL."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.graph.state import BrokerState
from clarke.learning.attribution import compute_attributions, useful_context_ratio
from clarke.storage.postgres.repositories.episode_repo import create_episode
from clarke.storage.postgres.repositories.request_repo import create_request_log
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def _persist(state: BrokerState, session: AsyncSession) -> None:
    request_data = {
        "request_id": state["request_id"],
        "tenant_id": state["tenant_id"],
        "project_id": state["project_id"],
        "user_id": state["user_id"],
        "session_id": state.get("session_id"),
        "message": state["message"],
        "agent_id": state.get("agent_id"),
        "degraded_mode": state.get("degraded_mode", False),
        "prompt_version_id": state.get("prompt_version_id"),
        "context_template_version_id": state.get("context_template_version_id"),
        "answer_summary": (state.get("answer") or "")[:500],
        "status": "error" if state.get("error") else "completed",
        "latency_ms": state.get("latency_ms"),
    }
    await create_request_log(session, request_data)

    # Compute attributions
    answer = state.get("answer") or ""
    injected = state.get("injected_items") or []
    attributions = compute_attributions(answer, injected)
    ucr = useful_context_ratio(attributions) if attributions else None

    episode_data = {
        "request_id": state["request_id"],
        "tenant_id": state["tenant_id"],
        "query_features": state.get("query_features"),
        "retrieval_plan": state.get("retrieval_plan"),
        "retrieved_items": state.get("retrieved_items"),
        "injected_items": injected,
        "degraded_mode": state.get("degraded_mode", False),
        "usefulness_score": ucr,
    }
    await create_episode(session, episode_data)
    await session.commit()


def persist_episode(state: BrokerState) -> dict:
    """Placeholder node — actual persistence handled by BrokerService."""
    return {}
