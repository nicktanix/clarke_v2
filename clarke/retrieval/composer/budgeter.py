"""Token budget allocation and enforcement."""

from clarke.api.schemas.retrieval import RetrievedItem
from clarke.broker.budget import calculate_budget
from clarke.llm.token_counting import count_tokens


def allocate_budget(
    query_features: dict | None = None,
    total_tokens: int = 4000,
) -> dict[str, int]:
    """Calculate absolute token limits per section from percentage-based budget."""
    budget = calculate_budget(query_features)
    return {
        "policy": int(total_tokens * budget.policy_pct),
        "anchors": int(total_tokens * budget.anchors_pct),
        "evidence": int(total_tokens * budget.evidence_pct),
        "recent_state": int(total_tokens * budget.recent_state_pct),
    }


def enforce_budget(
    items: list[RetrievedItem],
    max_tokens: int,
    model: str = "",
) -> list[RetrievedItem]:
    """Greedily select items that fit within the token budget.

    Items are assumed to be pre-sorted by relevance (reranked).
    """
    selected: list[RetrievedItem] = []
    used_tokens = 0

    for item in items:
        item_tokens = count_tokens(item.summary, model)
        if used_tokens + item_tokens > max_tokens:
            break
        selected.append(item)
        used_tokens += item_tokens

    return selected
