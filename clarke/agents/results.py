"""Sub-agent result ingestion."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.repositories.agent_repo import (
    create_subagent_result,
    update_agent_status,
)
from clarke.storage.postgres.repositories.audit_repo import create_audit_event
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def ingest_result(
    session: AsyncSession,
    agent_id: str,
    tenant_id: str,
    status: str,
    summary: str,
    evidence_item_ids: list[str] | None = None,
    artifact_refs: list[dict] | None = None,
    open_questions: list[str] | None = None,
) -> dict:
    """Validate and store a sub-agent result, mark agent as completed."""
    result = await create_subagent_result(
        session,
        {
            "tenant_id": tenant_id,
            "agent_instance_id": agent_id,
            "status": status,
            "summary": summary,
            "evidence_item_ids": evidence_item_ids,
            "artifact_refs": artifact_refs,
            "open_questions": open_questions,
        },
    )

    await update_agent_status(session, agent_id, "completed")

    await create_audit_event(
        session,
        tenant_id=tenant_id,
        actor_id="system",
        action="subagent_result_ingested",
        target_type="agent",
        target_id=agent_id,
        metadata={"status": status},
    )

    logger.info("subagent_result_ingested", agent_id=agent_id, status=status)
    return {"id": result.id, "agent_id": agent_id, "status": status}
