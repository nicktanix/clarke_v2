"""Neo4j converter tests."""

from clarke.retrieval.neo4j.converter import graph_results_to_retrieved_items


def test_convert_results():
    results = [
        {
            "name": "WebSocket",
            "node_type": "Entity",
            "content": "WebSocket protocol",
            "id": "e1",
            "confidence": 0.8,
        },
        {"name": "Session", "node_type": "Concept", "content": None, "id": "c1", "confidence": 0.5},
    ]
    items = graph_results_to_retrieved_items(results, "t1", "p1")
    assert len(items) == 2
    assert items[0].item_id == "e1"
    assert items[0].source == "graph"
    assert items[0].score == 0.8
    assert items[0].summary == "WebSocket protocol"
    assert items[1].summary == "Session"  # falls back to name


def test_convert_empty():
    assert graph_results_to_retrieved_items([], "t1", "p1") == []


def test_score_capped_at_1():
    results = [{"name": "X", "node_type": "Entity", "id": "x1", "confidence": 1.5}]
    items = graph_results_to_retrieved_items(results, "t1", "p1")
    assert items[0].score == 1.0


def test_default_confidence():
    results = [{"name": "Y", "node_type": "Entity", "id": "y1"}]
    items = graph_results_to_retrieved_items(results, "t1", "p1")
    assert items[0].score == 0.5
