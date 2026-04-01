"""Temporal workflow for HDBSCAN clustering of retrieval episodes."""

from datetime import timedelta

from temporalio import activity, workflow

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


@activity.defn
async def run_clustering_activity(tenant_id: str) -> dict:
    """Load episodes, run HDBSCAN, create proto-classes."""
    from sqlalchemy import select

    from clarke.learning.proto_classes import ProtoClassManager
    from clarke.settings import get_settings
    from clarke.storage.postgres.database import get_db_session
    from clarke.storage.postgres.models import RetrievalEpisode

    settings = get_settings()
    manager = ProtoClassManager(settings.taxonomy)

    async for session in get_db_session():
        result = await session.execute(
            select(RetrievalEpisode)
            .where(RetrievalEpisode.tenant_id == tenant_id)
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

        classes = await manager.run_clustering(session, tenant_id, episodes)
        await session.commit()
        break

    return {"tenant_id": tenant_id, "clusters_created": len(classes)}


@workflow.defn
class ClusteringWorkflow:
    """Temporal workflow that runs episode clustering for a tenant."""

    @workflow.run
    async def run(self, tenant_id: str) -> dict:
        return await workflow.execute_activity(
            run_clustering_activity,
            tenant_id,
            start_to_close_timeout=timedelta(minutes=10),
        )
