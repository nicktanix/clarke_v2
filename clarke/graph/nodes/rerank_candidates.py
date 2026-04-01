"""Rerank retrieved items using cross-encoder + optional LLM reranker for design queries."""

from clarke.api.schemas.retrieval import RetrievedItem
from clarke.graph.state import BrokerState
from clarke.retrieval.rerank.cross_encoder import CrossEncoderReranker
from clarke.settings import get_settings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

_reranker: CrossEncoderReranker | None = None


def _get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        settings = get_settings()
        _reranker = CrossEncoderReranker(model_name=settings.retrieval.rerank_model)
    return _reranker


async def rerank_candidates(state: BrokerState) -> dict:
    """Rerank retrieved_items using cross-encoder, then optional LLM reranker for design queries."""
    raw_items = state.get("retrieved_items") or []
    if not raw_items:
        return {"retrieved_items": []}

    settings = get_settings()
    if not settings.retrieval.rerank_enabled:
        return {"retrieved_items": raw_items[: settings.retrieval.rerank_top_k]}

    items = [RetrievedItem(**item) if isinstance(item, dict) else item for item in raw_items]

    # Stage 1: Cross-encoder reranking
    reranker = _get_reranker()
    reranked = reranker.rerank(
        query=state.get("message", ""),
        items=items,
        top_k=settings.retrieval.rerank_top_k,
    )

    # Stage 2: Optional LLM reranker for design/tradeoff queries
    features = state.get("query_features") or {}
    is_design = features.get("is_design_oriented", 0) > 0.7
    question_type = features.get("question_type", "")

    if is_design or question_type == "comparison":
        try:
            from clarke.retrieval.rerank.llm_reranker import llm_rerank

            reranked = await llm_rerank(
                query=state.get("message", ""),
                items=reranked,
                top_k=settings.retrieval.rerank_top_k,
                llm_settings=settings.llm,
            )
            logger.info("llm_reranker_applied", query_type=question_type or "design")
        except Exception:
            logger.debug("llm_reranker_skipped", exc_info=True)

    return {"retrieved_items": [item.model_dump() for item in reranked]}
