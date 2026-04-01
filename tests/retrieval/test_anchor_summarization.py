"""Anchor summarization tests."""

from clarke.api.schemas.retrieval import Provenance, RetrievedItem
from clarke.retrieval.composer.anchors import summarize_anchors


def _make_graph_item(item_id: str, node_type: str, summary: str, score: float) -> RetrievedItem:
    return RetrievedItem(
        item_id=item_id,
        tenant_id="t1",
        project_id="p1",
        source="graph",
        node_type=node_type,
        score=score,
        summary=summary,
        provenance=Provenance(),
    )


def test_summarize_anchors_groups_by_type():
    items = [
        _make_graph_item("e1", "entity", "WebSocket protocol handler", 0.8),
        _make_graph_item("e2", "entity", "Session manager component", 0.7),
        _make_graph_item("c1", "concept", "Connection lifecycle", 0.9),
    ]
    anchors = summarize_anchors(items)
    assert len(anchors) >= 1
    assert all("title" in a and "summary" in a for a in anchors)


def test_summarize_anchors_empty():
    assert summarize_anchors([]) == []


def test_summarize_anchors_max_limit():
    items = [_make_graph_item(f"e{i}", f"type{i}", f"Item {i}", 0.5) for i in range(10)]
    anchors = summarize_anchors(items, max_anchors=2)
    assert len(anchors) <= 2


def test_summarize_anchors_highest_score_first():
    items = [
        _make_graph_item("low", "entity", "Low score", 0.3),
        _make_graph_item("high", "concept", "High score", 0.9),
    ]
    anchors = summarize_anchors(items)
    assert anchors[0]["top_score"] >= anchors[-1]["top_score"]
