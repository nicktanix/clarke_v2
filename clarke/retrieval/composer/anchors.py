"""Anchor summarization — group graph items for prompt-safe injection."""

from clarke.api.schemas.retrieval import RetrievedItem


def summarize_anchors(
    graph_items: list[RetrievedItem],
    max_anchors: int = 3,
) -> list[dict]:
    """Group high-score graph items by concept/node_type and generate anchor summaries.

    Anchors explain grouping without replacing evidence. No LLM call — heuristic only.
    """
    if not graph_items:
        return []

    # Group by node_type or provenance concept
    groups: dict[str, list[RetrievedItem]] = {}
    for item in graph_items:
        key = item.node_type or "entity"
        groups.setdefault(key, []).append(item)

    anchors = []
    for group_key, items in sorted(groups.items(), key=lambda x: -max(i.score for i in x[1])):
        if len(anchors) >= max_anchors:
            break

        # Best item's summary as title, concatenate others
        items.sort(key=lambda x: x.score, reverse=True)
        title = items[0].summary[:100] if items[0].summary else group_key
        summaries = [item.summary for item in items[:5] if item.summary]
        combined = ". ".join(summaries)[:500]

        anchors.append(
            {
                "title": f"{group_key.title()}: {title}",
                "summary": combined,
                "source": "graph",
                "item_count": len(items),
                "top_score": items[0].score,
            }
        )

    return anchors
