"""Semantic and hybrid search against Qdrant."""

from qdrant_client.models import Fusion, Prefetch

from clarke.api.schemas.retrieval import Provenance, RetrievedItem
from clarke.retrieval.qdrant.client import QdrantStore
from clarke.retrieval.qdrant.filters import build_search_filter
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def semantic_search(
    store: QdrantStore,
    query_embedding: list[float],
    tenant_id: str,
    project_id: str,
    top_k: int = 20,
    source_type: str | None = None,
    hybrid: bool = True,
    query_text: str | None = None,
) -> list[RetrievedItem]:
    """Search Qdrant with tenant-scoped filter. Supports hybrid (vector + BM25) search.

    When hybrid=True and query_text is provided, uses Qdrant's prefetch + RRF fusion
    to combine vector similarity with BM25 text matching.
    """
    query_filter = build_search_filter(tenant_id, project_id, source_type)

    if hybrid and query_text:
        # Hybrid search: vector prefetch + BM25 prefetch, fused with RRF
        try:
            results = await store.client.query_points(
                collection_name=store.collection_name,
                prefetch=[
                    Prefetch(query=query_embedding, limit=top_k * 2, filter=query_filter),
                    Prefetch(
                        query=query_text, using="content", limit=top_k * 2, filter=query_filter
                    ),
                ],
                query=Fusion.RRF,
                limit=top_k,
                with_payload=True,
            )
            logger.debug("hybrid_search_executed", vector_and_bm25=True)
        except Exception:
            # Fall back to vector-only if hybrid fails (e.g., text index not available)
            logger.debug("hybrid_search_fallback", reason="falling back to vector-only")
            results = await store.client.query_points(
                collection_name=store.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
    else:
        # Vector-only search
        results = await store.client.query_points(
            collection_name=store.collection_name,
            query=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

    return _results_to_items(results, tenant_id, project_id)


def _results_to_items(results, tenant_id: str, project_id: str) -> list[RetrievedItem]:
    """Convert Qdrant query results to RetrievedItem list."""
    items: list[RetrievedItem] = []
    for point in results.points:
        payload = point.payload or {}
        items.append(
            RetrievedItem(
                item_id=str(point.id),
                tenant_id=tenant_id,
                project_id=project_id,
                source=payload.get("source_type", "docs"),
                node_type=payload.get("node_type", "chunk"),
                score=point.score or 0.0,
                summary=payload.get("content", "")[:500],
                provenance=Provenance(
                    doc_id=payload.get("document_id"),
                    section=payload.get("section_heading"),
                ),
            )
        )
    return items
