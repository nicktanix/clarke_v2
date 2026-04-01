"""Optional LLM-based reranker for design/tradeoff queries.

Runs a cheap LLM call to rerank top-N items by relevance for complex queries
where cross-encoder scores alone may not capture architectural reasoning.
"""

import json

from clarke.api.schemas.retrieval import RetrievedItem
from clarke.llm.gateway import LLMGateway
from clarke.settings import LLMSettings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def llm_rerank(
    query: str,
    items: list[RetrievedItem],
    top_k: int = 5,
    llm_settings: LLMSettings | None = None,
) -> list[RetrievedItem]:
    """Rerank items using an LLM judge for design/tradeoff queries.

    Returns top_k items reranked by LLM-judged relevance.
    Falls back to original ordering on failure.
    """
    if not items or len(items) <= 1:
        return items[:top_k]

    settings = llm_settings or LLMSettings()
    gateway = LLMGateway(settings)

    # Build prompt with numbered items
    item_descriptions = "\n".join(
        f"{i + 1}. [{item.source}] {item.summary[:200]}" for i, item in enumerate(items[:10])
    )

    prompt = f"""You are ranking search results by relevance to a design/architecture question.

Question: {query}

Search results:
{item_descriptions}

Rank the results from most to least relevant to answering the question.
Return ONLY a JSON array of the result numbers in order of relevance, e.g. [3, 1, 5, 2, 4]"""

    try:
        response = await gateway.call(
            messages=[{"role": "user", "content": prompt}],
            model=settings.default_answer_model,
            temperature=0.0,
        )

        # Parse ranking
        content = response.content.strip()
        ranking = json.loads(content)

        if not isinstance(ranking, list):
            return items[:top_k]

        # Reorder items by LLM ranking
        reranked = []
        for idx in ranking:
            if isinstance(idx, int) and 1 <= idx <= len(items):
                item = items[idx - 1]
                reranked.append(item.model_copy(update={"score": 1.0 - len(reranked) * 0.1}))

        # Add any items not in the ranking
        ranked_ids = {
            items[idx - 1].item_id
            for idx in ranking
            if isinstance(idx, int) and 1 <= idx <= len(items)
        }
        for item in items:
            if item.item_id not in ranked_ids:
                reranked.append(item)

        logger.debug("llm_rerank_complete", items_reranked=len(reranked))
        return reranked[:top_k]

    except Exception:
        logger.warning("llm_rerank_failed", exc_info=True)
        return items[:top_k]
