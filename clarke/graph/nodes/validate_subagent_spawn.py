"""Validate a SUBAGENT_SPAWN request against broker policies."""

from clarke.agents.spawn import validate_spawn_request
from clarke.graph.state import BrokerState
from clarke.settings import get_settings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def validate_subagent_spawn(state: BrokerState) -> dict:
    """Validate spawn request — depth, quota, budget, sources, task scope."""
    settings = get_settings()
    spawn_req = state.get("spawn_request")

    if not spawn_req:
        return {"subagent_spawn_approved": False}

    # Spec: spawn disabled in CANONICAL_ONLY mode
    execution_mode = state.get("execution_mode", "full")
    if execution_mode == "canonical_only":
        logger.info("spawn_rejected_canonical_only")
        return {"subagent_spawn_approved": False, "subagent_spawn_requested": False}

    try:
        from clarke.storage.postgres.database import get_db_session

        async for session in get_db_session():
            approved, reason = await validate_spawn_request(
                spawn_request=spawn_req,
                tenant_id=state["tenant_id"],
                project_id=state["project_id"],
                current_depth=state.get("agent_depth", 0),
                root_agent_id=state.get("root_agent_id"),
                session=session,
                broker_settings=settings.broker,
                learning_settings=settings.learning,
            )
            break
    except Exception:
        logger.exception("spawn_validation_failed")
        return {"subagent_spawn_approved": False}

    if not approved:
        logger.info("spawn_rejected", reason=reason)
        return {"subagent_spawn_approved": False, "subagent_spawn_requested": False}

    logger.info("spawn_approved", task=spawn_req.get("task", "")[:50])
    return {"subagent_spawn_approved": True}
