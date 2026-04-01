"""Answer attribution using token-level jaccard overlap."""

import re

from clarke.llm.token_counting import count_tokens

_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "it",
    "its",
    "this",
    "that",
    "and",
    "but",
    "or",
    "not",
    "no",
}


def _tokenize(text: str) -> set[str]:
    """Extract lowercased word tokens, filtering stopwords."""
    words = re.findall(r"\b\w+\b", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def compute_attributions(
    answer: str,
    injected_items: list[dict],
    threshold: float = 0.15,
    model: str = "",
) -> list[dict]:
    """Compute per-item attribution using jaccard overlap.

    Returns list of dicts: item_id, source, overlap_score, attributed, token_count.
    """
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return []

    attributions = []
    for item in injected_items:
        summary = item.get("summary", "")
        item_tokens = _tokenize(summary)

        if not item_tokens:
            overlap = 0.0
        else:
            intersection = answer_tokens & item_tokens
            union = answer_tokens | item_tokens
            overlap = len(intersection) / len(union) if union else 0.0

        token_count = count_tokens(summary, model)

        attributions.append(
            {
                "item_id": item.get("item_id", ""),
                "source": item.get("source", "unknown"),
                "overlap_score": round(overlap, 4),
                "attributed": overlap >= threshold,
                "token_count": token_count,
            }
        )

    return attributions


def useful_context_ratio(attributions: list[dict]) -> float:
    """Compute attributed_tokens / total_injected_tokens."""
    total = sum(a["token_count"] for a in attributions)
    if total == 0:
        return 0.0
    attributed = sum(a["token_count"] for a in attributions if a["attributed"])
    return round(attributed / total, 4)
