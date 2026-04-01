"""Second-pass retrieval based on validated CONTEXT_REQUEST."""

from clarke.graph.state import BrokerState
from clarke.ingestion.embeddings import embed_single
from clarke.retrieval.qdrant.search import semantic_search
from clarke.settings import get_settings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def run_second_pass_retrieval(state: BrokerState) -> dict:
    """Execute second-pass retrieval from CONTEXT_REQUEST queries."""
    cr = state.get("context_request")
    if not cr or not cr.get("requests"):
        return {"second_pass_retrieved_items": []}

    settings = get_settings()

    try:
        from clarke.retrieval.qdrant.client import get_qdrant_store

        store = get_qdrant_store()
    except RuntimeError:
        logger.warning("qdrant_not_available_for_second_pass")
        return {"second_pass_retrieved_items": []}

    # Collect first-pass item IDs for deduplication
    first_pass_ids = {
        item.get("item_id") if isinstance(item, dict) else item.item_id
        for item in (state.get("retrieved_items") or [])
    }

    all_items = []

    for req in cr["requests"]:
        query = req.get("query", "")
        max_items = req.get("max_items", 3)

        try:
            query_embedding = await embed_single(
                query,
                model=settings.embedding.embedding_model,
                dimensions=settings.embedding.embedding_dimensions,
            )
            items = await semantic_search(
                store=store,
                query_embedding=query_embedding,
                tenant_id=state["tenant_id"],
                project_id=state["project_id"],
                top_k=max_items,
            )
            for item in items:
                if item.item_id not in first_pass_ids:
                    all_items.append(item)
                    first_pass_ids.add(item.item_id)
        except Exception:
            logger.exception("second_pass_retrieval_failed")

    logger.info("second_pass_retrieval_complete", items=len(all_items))
    return {"second_pass_retrieved_items": [item.model_dump() for item in all_items]}
