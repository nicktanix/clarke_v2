"""Attribution tests."""

from clarke.learning.attribution import compute_attributions, useful_context_ratio


def test_compute_attributions_with_overlap():
    answer = "The websocket connection handles reconnection through the session manager."
    items = [
        {
            "item_id": "i1",
            "source": "docs",
            "summary": "The websocket connection manager handles session lifecycle and reconnection logic.",
        },
        {
            "item_id": "i2",
            "source": "docs",
            "summary": "Database migration scripts for PostgreSQL tables.",
        },
    ]
    attrs = compute_attributions(answer, items, threshold=0.1)
    assert len(attrs) == 2
    assert attrs[0]["attributed"] is True  # high overlap
    assert attrs[1]["attributed"] is False  # low overlap
    assert attrs[0]["overlap_score"] > attrs[1]["overlap_score"]


def test_compute_attributions_no_overlap():
    answer = "The sky is blue."
    items = [
        {
            "item_id": "i1",
            "source": "docs",
            "summary": "Database migration scripts for PostgreSQL tables.",
        },
    ]
    attrs = compute_attributions(answer, items, threshold=0.15)
    assert len(attrs) == 1
    assert attrs[0]["attributed"] is False


def test_compute_attributions_empty():
    assert compute_attributions("answer", []) == []
    assert compute_attributions("", [{"item_id": "i1", "source": "docs", "summary": "test"}]) == []


def test_useful_context_ratio_all_attributed():
    attrs = [
        {"item_id": "i1", "attributed": True, "token_count": 100},
        {"item_id": "i2", "attributed": True, "token_count": 50},
    ]
    assert useful_context_ratio(attrs) == 1.0


def test_useful_context_ratio_none_attributed():
    attrs = [
        {"item_id": "i1", "attributed": False, "token_count": 100},
    ]
    assert useful_context_ratio(attrs) == 0.0


def test_useful_context_ratio_partial():
    attrs = [
        {"item_id": "i1", "attributed": True, "token_count": 100},
        {"item_id": "i2", "attributed": False, "token_count": 100},
    ]
    assert useful_context_ratio(attrs) == 0.5


def test_useful_context_ratio_empty():
    assert useful_context_ratio([]) == 0.0
