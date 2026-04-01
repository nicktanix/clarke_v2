"""Proto-class management — create, promote, merge, split."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.learning.clustering import build_episode_vector, cluster_episodes, compute_centroid
from clarke.settings import TaxonomySettings
from clarke.storage.postgres.repositories.proto_class_repo import (
    create_class_membership,
    create_proto_class,
    get_proto_classes,
    update_proto_class,
)
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


class ProtoClassManager:
    def __init__(self, settings: TaxonomySettings) -> None:
        self.settings = settings

    async def run_clustering(
        self,
        session: AsyncSession,
        tenant_id: str,
        episodes: list[dict],
    ) -> list[dict]:
        """Cluster episodes and create/update proto-classes."""
        clusters = cluster_episodes(episodes, self.settings.min_cluster_size)
        if not clusters:
            return []

        created = []
        for label, indices in clusters.items():
            members = [episodes[i] for i in indices]
            vectors = [build_episode_vector(ep) for ep in members]
            centroid = compute_centroid(vectors)

            # Compute retrieval signature (most common source/strategy)
            source_counts: dict[str, int] = {}
            for ep in members:
                for item in ep.get("retrieved_items") or []:
                    src = item.get("source", "docs") if isinstance(item, dict) else "docs"
                    source_counts[src] = source_counts.get(src, 0) + 1

            avg_usefulness = sum(ep.get("usefulness_score", 0) or 0 for ep in members) / max(
                len(members), 1
            )

            proto = await create_proto_class(
                session,
                {
                    "tenant_id": tenant_id,
                    "label": f"cluster_{label}",
                    "centroid": centroid,
                    "retrieval_signature": {
                        "source_distribution": source_counts,
                        "avg_usefulness": round(avg_usefulness, 4),
                    },
                    "member_count": len(members),
                    "stability_score": 0.0,
                    "status": "embryonic",
                },
            )

            # Create memberships
            for i, idx in enumerate(indices):
                ep = episodes[idx]
                await create_class_membership(
                    session,
                    {
                        "proto_class_id": proto.id,
                        "episode_id": ep.get("id", f"ep_{idx}"),
                        "feature_vector": vectors[i],
                    },
                )

            created.append(
                {
                    "id": proto.id,
                    "label": proto.label,
                    "member_count": len(members),
                }
            )

        return created

    def check_promotion(self, proto_class: dict) -> bool:
        """Check if a proto-class meets promotion criteria."""
        return (
            proto_class.get("member_count", 0) >= self.settings.min_members_for_promotion
            and proto_class.get("stability_score", 0) >= self.settings.min_stability_score
        )

    async def promote_class(self, session: AsyncSession, class_id: str) -> dict:
        """Promote a proto-class to operational status."""
        await update_proto_class(session, class_id, {"status": "operational"})
        return {"id": class_id, "status": "operational"}

    async def merge_classes(self, session: AsyncSession, class_id_a: str, class_id_b: str) -> dict:
        """Merge class B into class A. Mark B as merged."""
        await update_proto_class(session, class_id_b, {"status": "merged"})
        return {"merged_into": class_id_a, "merged_from": class_id_b}

    async def split_class(self, session: AsyncSession, class_id: str) -> dict:
        """Mark a class for re-clustering on next run."""
        await update_proto_class(session, class_id, {"status": "split_pending"})
        return {"id": class_id, "status": "split_pending"}

    async def list_classes(self, session: AsyncSession, tenant_id: str) -> list[dict]:
        """List proto-classes for a tenant."""
        classes = await get_proto_classes(session, tenant_id)
        return [
            {
                "id": c.id,
                "label": c.label,
                "member_count": c.member_count,
                "stability_score": c.stability_score,
                "status": c.status,
            }
            for c in classes
        ]
