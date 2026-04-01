"""Sub-agent spawn validation and instance creation."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.agents.handles import AgentHandle, build_handle
from clarke.settings import BrokerSettings, LearningSettings
from clarke.storage.postgres.repositories.agent_repo import (
    count_active_agents_for_root,
    create_agent_instance,
)
from clarke.telemetry.logging import get_logger
from clarke.utils.time import utc_now

logger = get_logger(__name__)


async def validate_spawn_request(
    spawn_request: dict,
    tenant_id: str,
    project_id: str,
    current_depth: int,
    root_agent_id: str | None,
    session: AsyncSession,
    broker_settings: BrokerSettings,
    learning_settings: LearningSettings,
) -> tuple[bool, str]:
    """Validate a SUBAGENT_SPAWN request against broker policies.

    Returns (approved, rejection_reason).
    """
    # Check depth limit
    max_depth = spawn_request.get("max_depth", broker_settings.max_subagent_depth)
    if current_depth >= min(max_depth, broker_settings.max_subagent_depth):
        return (
            False,
            f"Depth limit reached: {current_depth} >= {broker_settings.max_subagent_depth}",
        )

    # Check task is defined
    task = spawn_request.get("task", "")
    if not task or len(task) < 10:
        return False, "Task definition too short or empty"

    # Check active agent quota
    if root_agent_id:
        active_count = await count_active_agents_for_root(session, root_agent_id)
        if active_count >= broker_settings.max_active_subagents_per_root:
            return (
                False,
                f"Active agent quota exceeded: {active_count} >= {broker_settings.max_active_subagents_per_root}",
            )

    # Check allowed sources
    required_memory = spawn_request.get("required_memory", [])
    allowed = set(learning_settings.allowed_context_request_sources)
    for source in required_memory:
        if source not in allowed:
            return False, f"Source not allowed: {source}"

    return True, ""


async def create_agent(
    session: AsyncSession,
    spawn_request: dict,
    tenant_id: str,
    project_id: str,
    parent_agent_id: str | None,
    root_agent_id: str | None,
    parent_request_id: str,
    current_depth: int,
) -> tuple[str, AgentHandle]:
    """Create an AgentInstance and return (agent_id, handle)."""
    timeout_minutes = spawn_request.get("timeout_minutes", 30)
    expires_at = utc_now() + timedelta(minutes=timeout_minutes)

    instance = await create_agent_instance(
        session,
        {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "root_agent_id": root_agent_id or parent_agent_id,
            "parent_agent_id": parent_agent_id,
            "parent_request_id": parent_request_id,
            "task_definition": spawn_request.get("task", ""),
            "memory_scope_mode": spawn_request.get("memory_scope_mode", "hybrid"),
            "allowed_sources": spawn_request.get("required_memory", []),
            "depth": current_depth + 1,
            "status": "active",
            "budget_tokens": spawn_request.get("budget_tokens"),
            "expires_at": expires_at,
        },
    )

    handle = build_handle(instance.id, timeout_minutes)
    logger.info(
        "subagent_created",
        agent_id=instance.id,
        parent=parent_agent_id,
        depth=current_depth + 1,
    )
    return instance.id, handle
