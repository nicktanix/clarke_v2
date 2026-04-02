"""Tenant signal detection — surface cross-agent patterns as policy candidates."""

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.memory.policy import PolicyService
from clarke.settings import SelfImprovementSettings, get_settings
from clarke.storage.postgres.repositories.tenant_signal_repo import create_signal
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def detect_tenant_signals(
    tenant_id: str,
    session: AsyncSession,
    settings: SelfImprovementSettings | None = None,
) -> list[dict]:
    """Detect correction patterns that span multiple agents and create policy proposals.

    When similar corrections appear across M+ distinct agents in a tenant,
    synthesize a policy candidate and submit it through the existing policy
    approval workflow.
    """
    if not settings:
        settings = get_settings().self_improvement

    # 1. Fetch all correction/preference memories across agents in this tenant
    memories = await _fetch_tenant_correction_memories(tenant_id)
    if len(memories) < settings.tenant_signal_min_cluster_size:
        return []

    # 2. Cluster by similarity
    clusters = _cluster_memories(
        memories,
        similarity_threshold=settings.tenant_signal_similarity_threshold,
        min_cluster_size=settings.tenant_signal_min_cluster_size,
    )

    signals = []
    policy_service = PolicyService()

    for cluster in clusters:
        # 3. Count distinct agents in this cluster
        agent_ids = {m["agent_profile_id"] for m in cluster["members"] if m.get("agent_profile_id")}
        if len(agent_ids) < settings.tenant_signal_min_agent_count:
            continue

        # 4. Synthesize a policy statement
        policy_text = await _synthesize_policy(cluster["texts"])
        if not policy_text:
            continue

        # 5. Create policy via existing workflow
        try:
            policy_node = await policy_service.create_policy(
                session,
                tenant_id=tenant_id,
                content=policy_text,
                owner_id="system:self_improvement",
            )
            await policy_service.submit_for_approval(session, policy_node["id"])
        except Exception:
            logger.warning("tenant_signal_policy_creation_failed", exc_info=True)
            continue

        # 6. Record the signal
        signal = await create_signal(
            session,
            {
                "tenant_id": tenant_id,
                "signal_type": "correction_pattern",
                "content_summary": policy_text,
                "source_memory_ids": cluster["point_ids"],
                "agent_profile_ids": list(agent_ids),
                "agent_count": len(agent_ids),
                "cluster_size": cluster["size"],
                "similarity_score": cluster["avg_similarity"],
                "policy_node_id": policy_node["id"],
                "status": "policy_created",
            },
        )
        signals.append({"id": signal.id, "policy_text": policy_text, "agent_count": len(agent_ids)})

    logger.info(
        "tenant_signals_detected",
        tenant_id=tenant_id,
        signals_created=len(signals),
    )

    return signals


async def _fetch_tenant_correction_memories(tenant_id: str) -> list[dict]:
    """Fetch correction/preference memories across all agents in a tenant."""
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
            ]
        )

        results = await store.client.scroll(
            collection_name=store.collection_name,
            scroll_filter=memory_filter,
            limit=200,
            with_payload=True,
            with_vectors=True,
        )

        memories = []
        for point in results[0]:
            payload = point.payload or {}
            memories.append(
                {
                    "point_id": str(point.id),
                    "text": payload.get("content", ""),
                    "vector": point.vector,
                    "agent_profile_id": payload.get("agent_profile_id"),
                    "memory_type": payload.get("memory_type", ""),
                }
            )
        return memories
    except Exception:
        logger.warning("tenant_correction_fetch_failed", exc_info=True)
        return []


def _cluster_memories(
    memories: list[dict],
    similarity_threshold: float = 0.80,
    min_cluster_size: int = 5,
) -> list[dict]:
    """Cluster memories by cosine similarity, preserving member metadata."""
    vectors = [m["vector"] for m in memories if m.get("vector")]
    if len(vectors) < min_cluster_size:
        return []

    from sklearn.cluster import AgglomerativeClustering

    X = np.array(vectors)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_norm = X / norms

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - similarity_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(X_norm)

    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        cluster_map.setdefault(label, []).append(idx)

    clusters = []
    for _label, indices in cluster_map.items():
        if len(indices) < min_cluster_size:
            continue

        cluster_vectors = X_norm[indices]
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
                "members": [memories[i] for i in indices],
                "size": len(indices),
                "avg_similarity": round(avg_sim, 4),
            }
        )

    return clusters


async def _synthesize_policy(texts: list[str]) -> str | None:
    """Use LLM to synthesize a tenant-wide policy from cross-agent corrections."""
    try:
        from clarke.llm.gateway import LLMGateway
        from clarke.settings import get_settings

        settings = get_settings()
        gateway = LLMGateway(settings.llm)

        corrections_text = "\n---\n".join(texts[:10])
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a policy synthesis engine. Given a set of similar user "
                    "corrections that appeared across multiple AI agents, synthesize a "
                    "single, clear organizational policy statement. The policy should "
                    "be concise (1-2 sentences), authoritative, and apply to all agents "
                    "in the organization. Return ONLY the policy text, nothing else."
                ),
            },
            {
                "role": "user",
                "content": f"Synthesize a policy from these cross-agent corrections:\n\n{corrections_text}",
            },
        ]

        response = await gateway.call(messages)
        policy = response.content.strip()
        return policy if policy else None
    except Exception:
        logger.warning("policy_synthesis_failed", exc_info=True)
        return None
