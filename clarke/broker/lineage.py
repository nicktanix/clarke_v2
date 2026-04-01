"""Agent lineage tracking — PostgreSQL + Neo4j."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.storage.postgres.repositories.agent_repo import create_memory_link
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def record_lineage(
    session: AsyncSession,
    tenant_id: str,
    parent_agent_id: str,
    child_agent_id: str,
    handoff_type: str,
    linked_item_ids: list[str] | None = None,
    parent_episode_id: str | None = None,
) -> None:
    """Record parent-child lineage in PostgreSQL and Neo4j (best-effort)."""
    # PostgreSQL
    await create_memory_link(
        session,
        {
            "tenant_id": tenant_id,
            "parent_agent_id": parent_agent_id,
            "child_agent_id": child_agent_id,
            "handoff_type": handoff_type,
            "linked_item_ids": linked_item_ids,
            "parent_episode_id": parent_episode_id,
        },
    )

    # Neo4j (best-effort)
    try:
        from clarke.retrieval.neo4j.client import get_neo4j_store

        store = get_neo4j_store()
        await store.execute_write(
            """
            MERGE (p:AgentInstance {id: $parent_id, tenant_id: $tenant_id})
            MERGE (c:AgentInstance {id: $child_id, tenant_id: $tenant_id})
            MERGE (p)-[r:PARENT_OF]->(c)
            SET r.handoff_type = $handoff_type,
                r.tenant_id = $tenant_id,
                r.created_at = datetime()
            """,
            {
                "parent_id": parent_agent_id,
                "child_id": child_agent_id,
                "tenant_id": tenant_id,
                "handoff_type": handoff_type,
            },
        )
    except RuntimeError:
        logger.debug("lineage_neo4j_skipped", reason="neo4j not available")
    except Exception:
        logger.warning("lineage_neo4j_failed", exc_info=True)

    logger.info(
        "lineage_recorded",
        parent=parent_agent_id,
        child=child_agent_id,
        handoff=handoff_type,
    )
