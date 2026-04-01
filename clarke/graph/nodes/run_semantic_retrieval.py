"""Execute semantic retrieval against Qdrant."""

import asyncio

from clarke.graph.state import BrokerState
from clarke.ingestion.embeddings import embed_single
from clarke.retrieval.qdrant.search import semantic_search
from clarke.settings import get_settings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def run_semantic_retrieval(state: BrokerState) -> dict:
    """Embed the query and search Qdrant for relevant chunks."""
    plan = state.get("retrieval_plan") or []
    if not plan or state.get("degraded_mode"):
        return {"retrieved_items": []}

    settings = get_settings()

    # Try to get the Qdrant store
    try:
        from clarke.retrieval.qdrant.client import get_qdrant_store

        store = get_qdrant_store()
    except RuntimeError:
        logger.warning("qdrant_not_available", reason="store not initialized")
        return {"retrieved_items": [], "degraded_mode": True}

    all_items = []
    seen_ids: set[str] = set()

    for request in plan:
        query = request.get("query", state.get("message", ""))
        top_k = request.get("constraints", {}).get("max_items", settings.retrieval.search_top_k)
        timeout_ms = request.get("constraints", {}).get("timeout_ms", 800)
        source_type = request.get("source")  # docs, memory, decisions, etc.

        try:
            query_embedding = await embed_single(
                query,
                model=settings.embedding.embedding_model,
                dimensions=settings.embedding.embedding_dimensions,
            )
            # Enforce wall-clock timeout per subsystem (spec §6.3)
            items = await asyncio.wait_for(
                semantic_search(
                    store=store,
                    query_embedding=query_embedding,
                    tenant_id=state["tenant_id"],
                    project_id=state["project_id"],
                    top_k=top_k,
                    source_type=source_type,
                    hybrid=True,
                    query_text=query,
                ),
                timeout=timeout_ms / 1000,
            )
            for item in items:
                if item.item_id not in seen_ids:
                    all_items.append(item)
                    seen_ids.add(item.item_id)
        except TimeoutError:
            logger.warning("semantic_retrieval_timeout", timeout_ms=timeout_ms)
        except Exception:
            logger.exception("semantic_retrieval_failed")
            return {"retrieved_items": [], "degraded_mode": True}

    return {
        "retrieved_items": [item.model_dump() for item in all_items],
    }
