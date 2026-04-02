"""Directive surfacing — detect recurring corrections and propose behavioral directives."""

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.settings import SelfImprovementSettings, get_settings
from clarke.storage.postgres.repositories.directive_proposal_repo import (
    create_proposal,
    find_similar_proposals,
)
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def detect_directive_candidates(
    tenant_id: str,
    agent_profile_id: str,
    session: AsyncSession,
    settings: SelfImprovementSettings | None = None,
) -> list[dict]:
    """Detect recurring correction/preference patterns and create directive proposals.

    Steps:
    1. Query Qdrant for correction/preference memories for this agent
    2. Cluster by semantic similarity
    3. For clusters >= min_size, synthesize a directive via LLM
    4. Deduplicate against existing proposals
    5. Create DirectiveProposal records
    """
    if not settings:
        settings = get_settings().self_improvement

    # 1. Query episodic memories from Qdrant
    memories = await _fetch_correction_memories(tenant_id, agent_profile_id)
    if len(memories) < settings.directive_min_cluster_size:
        logger.debug(
            "directive_detection_skipped",
            reason="too few memories",
            count=len(memories),
        )
        return []

    # 2. Cluster by similarity
    clusters = _cluster_memories(
        memories,
        similarity_threshold=settings.directive_similarity_threshold,
        min_cluster_size=settings.directive_min_cluster_size,
    )

    if not clusters:
        return []

    # 3. Deduplicate against existing proposals
    existing = await find_similar_proposals(session, agent_profile_id)
    existing_texts = {p.proposed_directive.lower() for p in existing}

    # 4. Synthesize directives and create proposals
    proposals = []
    for cluster in clusters:
        directive = await _synthesize_directive(cluster["texts"])
        if not directive:
            continue

        # Simple dedup: skip if directive is very similar to an existing one
        if directive.lower() in existing_texts:
            continue

        proposal = await create_proposal(
            session,
            {
                "tenant_id": tenant_id,
                "agent_profile_id": agent_profile_id,
                "proposed_directive": directive,
                "source_memory_ids": cluster["point_ids"],
                "cluster_size": cluster["size"],
                "similarity_score": cluster["avg_similarity"],
                "status": "pending_approval",
            },
        )
        proposals.append({"id": proposal.id, "directive": directive})

    logger.info(
        "directive_candidates_detected",
        agent_profile_id=agent_profile_id,
        clusters_found=len(clusters),
        proposals_created=len(proposals),
    )

    return proposals


async def _fetch_correction_memories(
    tenant_id: str,
    agent_profile_id: str,
) -> list[dict]:
    """Fetch correction/preference memories from Qdrant for a specific agent."""
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

        from clarke.retrieval.qdrant.client import get_qdrant_store

        store = get_qdrant_store()

        memory_filter = Filter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                FieldCondition(key="source_type", match=MatchValue(value="memory")),
                FieldCondition(
                    key="memory_type",
                    match=MatchAny(any=["correction", "preference"]),
                ),
                FieldCondition(
                    key="agent_profile_id",
                    match=MatchValue(value=agent_profile_id),
                ),
            ]
        )

        results = await store.client.scroll(
            collection_name=store.collection_name,
            scroll_filter=memory_filter,
            limit=100,
            with_payload=True,
            with_vectors=True,
        )

        memories = []
        for point in results[0]:
            memories.append(
                {
                    "point_id": str(point.id),
                    "text": (point.payload or {}).get("content", ""),
                    "vector": point.vector,
                    "memory_type": (point.payload or {}).get("memory_type", ""),
                    "significance_score": (point.payload or {}).get("significance_score", 0.0),
                }
            )
        return memories
    except Exception:
        logger.warning("correction_memory_fetch_failed", exc_info=True)
        return []


def _cluster_memories(
    memories: list[dict],
    similarity_threshold: float = 0.80,
    min_cluster_size: int = 3,
) -> list[dict]:
    """Cluster memories by cosine similarity using agglomerative clustering."""
    if len(memories) < min_cluster_size:
        return []

    vectors = [m["vector"] for m in memories if m.get("vector")]
    if len(vectors) < min_cluster_size:
        return []

    from sklearn.cluster import AgglomerativeClustering

    # Convert to numpy array
    X = np.array(vectors)

    # Normalize for cosine distance
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_norm = X / norms

    # Agglomerative clustering with cosine distance
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - similarity_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(X_norm)

    # Group by cluster label
    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        cluster_map.setdefault(label, []).append(idx)

    # Build cluster results
    clusters = []
    for _label, indices in cluster_map.items():
        if len(indices) < min_cluster_size:
            continue

        cluster_vectors = X_norm[indices]
        # Average pairwise similarity
        if len(indices) > 1:
            sims = []
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    sims.append(float(np.dot(cluster_vectors[i], cluster_vectors[j])))
            avg_sim = sum(sims) / len(sims) if sims else 0.0
        else:
            avg_sim = 1.0

        clusters.append(
            {
                "texts": [memories[i]["text"] for i in indices],
                "point_ids": [memories[i]["point_id"] for i in indices],
                "size": len(indices),
                "avg_similarity": round(avg_sim, 4),
            }
        )

    return clusters


async def _synthesize_directive(texts: list[str]) -> str | None:
    """Use LLM to synthesize a behavioral directive from a cluster of corrections."""
    try:
        from clarke.llm.gateway import LLMGateway
        from clarke.settings import get_settings

        settings = get_settings()
        gateway = LLMGateway(settings.llm)

        corrections_text = "\n---\n".join(texts[:10])  # Cap at 10 examples
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a directive synthesis engine. Given a set of similar user "
                    "corrections or preferences, synthesize a single, clear behavioral "
                    "directive that captures the common instruction. The directive should "
                    "be concise (1-2 sentences), actionable, and written as an instruction "
                    "to an AI agent. Return ONLY the directive text, nothing else."
                ),
            },
            {
                "role": "user",
                "content": f"Synthesize a directive from these corrections:\n\n{corrections_text}",
            },
        ]

        response = await gateway.call(messages)
        directive = response.content.strip()
        return directive if directive else None
    except Exception:
        logger.warning("directive_synthesis_failed", exc_info=True)
        return None


async def schedule_detection(tenant_id: str, agent_profile_id: str) -> None:
    """Schedule directive detection for an agent profile.

    For MVP, runs detection inline. Future: delegate to Temporal workflow.
    """
    try:
        from clarke.storage.postgres.database import get_db_session

        settings = get_settings()
        if not settings.self_improvement.self_improvement_enabled:
            return

        async for session in get_db_session():
            await detect_directive_candidates(
                tenant_id,
                agent_profile_id,
                session,
                settings.self_improvement,
            )
            await session.commit()
    except Exception:
        logger.debug("directive_detection_schedule_failed", exc_info=True)
