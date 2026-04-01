"""Temporal workflows for cleanup — stale edge pruning and agent GC."""

from datetime import timedelta

from temporalio import activity, workflow

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


@activity.defn
async def prune_stale_edges_activity(tenant_id: str, max_age_days: int = 90) -> dict:
    """Prune Neo4j edges where last_retrieved_at is older than threshold."""
    try:
        from clarke.retrieval.neo4j.client import get_neo4j_store

        store = get_neo4j_store()
        result = await store.execute_write(
            """
            MATCH ()-[r]-()
            WHERE r.tenant_id = $tenant_id
              AND r.last_retrieved_at IS NOT NULL
              AND r.last_retrieved_at < datetime() - duration({days: $max_age_days})
            DELETE r
            RETURN count(r) as deleted_count
            """,
            {"tenant_id": tenant_id, "max_age_days": max_age_days},
        )
        deleted = result[0]["deleted_count"] if result else 0
        logger.info("stale_edges_pruned", tenant_id=tenant_id, deleted=deleted)
        return {"tenant_id": tenant_id, "deleted_edges": deleted}
    except RuntimeError:
        return {"tenant_id": tenant_id, "deleted_edges": 0, "skipped": "neo4j not available"}
    except Exception as e:
        logger.warning("stale_edge_pruning_failed", exc_info=True)
        return {"tenant_id": tenant_id, "error": str(e)}


@activity.defn
async def gc_expired_agents_activity(tenant_id: str) -> dict:
    """Garbage collect expired agent instances."""
    from sqlalchemy import select, update

    from clarke.storage.postgres.database import get_db_session
    from clarke.storage.postgres.models import AgentInstance
    from clarke.utils.time import utc_now

    now = utc_now()
    expired_count = 0

    async for session in get_db_session():
        result = await session.execute(
            select(AgentInstance).where(
                AgentInstance.tenant_id == tenant_id,
                AgentInstance.status == "active",
                AgentInstance.expires_at < now,
            )
        )
        expired = result.scalars().all()
        expired_count = len(expired)

        if expired:
            ids = [a.id for a in expired]
            await session.execute(
                update(AgentInstance).where(AgentInstance.id.in_(ids)).values(status="expired")
            )
            await session.commit()
        break

    logger.info("agents_gc_complete", tenant_id=tenant_id, expired=expired_count)
    return {"tenant_id": tenant_id, "expired_agents": expired_count}


@workflow.defn
class CleanupWorkflow:
    """Temporal workflow that runs cleanup tasks for a tenant."""

    @workflow.run
    async def run(self, tenant_id: str) -> dict:
        edge_result = await workflow.execute_activity(
            prune_stale_edges_activity,
            tenant_id,
            start_to_close_timeout=timedelta(minutes=5),
        )
        agent_result = await workflow.execute_activity(
            gc_expired_agents_activity,
            tenant_id,
            start_to_close_timeout=timedelta(minutes=5),
        )
        return {"edges": edge_result, "agents": agent_result}
