"""Conflict detection — identify contradicting items in the context pack.

When two items from different trust tiers cover the same topic but provide
different information, flag the conflict so the LLM can surface it.
"""

import re

from clarke.api.schemas.retrieval import RetrievedItem
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

# Trust tier names for labeling conflicts
_TRUST_LABELS = {
    "policy": "canonical policy",
    "decisions": "structured decision",
    "docs": "authoritative document",
    "memory": "episodic memory",
    "graph": "graph neighbor",
}


def _extract_terms(text: str) -> set[str]:
    """Extract significant terms for topic overlap detection."""
    return set(re.findall(r"\b\w{4,}\b", text.lower()))


def detect_conflicts(
    items: list[RetrievedItem],
    topic_overlap_threshold: float = 0.4,
) -> list[dict]:
    """Detect potential conflicts between retrieved items.

    Two items conflict when they cover the same topic (high term overlap)
    but come from different trust tiers. The higher-trust source should take
    precedence, and the conflict should be surfaced in the context.

    Returns list of conflict dicts: {higher_item, lower_item, overlap, note}
    """
    if len(items) < 2:
        return []

    conflicts: list[dict] = []

    for i, item_a in enumerate(items):
        terms_a = _extract_terms(item_a.summary)
        if not terms_a:
            continue

        for j in range(i + 1, len(items)):
            item_b = items[j]

            # Only flag conflicts between different source types
            if item_a.source == item_b.source:
                continue

            terms_b = _extract_terms(item_b.summary)
            if not terms_b:
                continue

            # Topic overlap via jaccard
            intersection = terms_a & terms_b
            union = terms_a | terms_b
            overlap = len(intersection) / len(union) if union else 0.0

            if overlap >= topic_overlap_threshold:
                # Determine which has higher trust
                trust_order = ["policy", "decisions", "docs", "memory", "graph"]
                rank_a = trust_order.index(item_a.source) if item_a.source in trust_order else 99
                rank_b = trust_order.index(item_b.source) if item_b.source in trust_order else 99

                higher = item_a if rank_a <= rank_b else item_b
                lower = item_b if rank_a <= rank_b else item_a

                higher_label = _TRUST_LABELS.get(higher.source, higher.source)
                lower_label = _TRUST_LABELS.get(lower.source, lower.source)

                conflict = {
                    "higher_item_id": higher.item_id,
                    "lower_item_id": lower.item_id,
                    "higher_source": higher.source,
                    "lower_source": lower.source,
                    "overlap": round(overlap, 3),
                    "note": (
                        f"Potential conflict: {higher_label} and {lower_label} "
                        f"cover overlapping topics. Following {higher_label} per trust ordering."
                    ),
                }
                conflicts.append(conflict)

    if conflicts:
        logger.info("conflicts_detected", count=len(conflicts))

    return conflicts
