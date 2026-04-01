"""Memory inheritance tests."""

from clarke.memory.inheritance import build_inherited_context


def test_copy_in_mode():
    parent = {
        "policy": ["Policy 1"],
        "anchors": [{"title": "A"}],
        "evidence": [{"item_id": "e1", "summary": "Evidence 1"}],
        "recent_state": [{"state": "recent"}],
        "budget": {"input_tokens": 500},
    }
    child = build_inherited_context(parent, handoff_mode="copy_in")
    assert child["policy"] == ["Policy 1"]
    assert len(child["anchors"]) == 1
    assert len(child["evidence"]) == 1
    assert child["recent_state"] == []  # recent state not inherited


def test_hybrid_mode_with_handoff_evidence():
    parent = {
        "policy": ["Policy 1"],
        "anchors": [{"title": "A", "top_score": 0.9}],
        "evidence": [
            {"item_id": "e1", "summary": "Evidence 1"},
            {"item_id": "e2", "summary": "Evidence 2"},
        ],
        "budget": {"input_tokens": 500},
    }
    child = build_inherited_context(parent, handoff_mode="hybrid", handoff_evidence=["e1"])
    assert child["policy"] == ["Policy 1"]
    assert len(child["evidence"]) == 1
    assert child["evidence"][0]["item_id"] == "e1"


def test_hybrid_mode_no_handoff():
    parent = {
        "policy": ["Policy 1"],
        "anchors": [{"title": "A", "top_score": 0.9}, {"title": "B", "top_score": 0.3}],
        "evidence": [{"item_id": "e1"}],
        "budget": {},
    }
    child = build_inherited_context(parent, handoff_mode="hybrid")
    assert child["policy"] == ["Policy 1"]
    assert len(child["anchors"]) == 1  # only high-score anchor


def test_empty_parent():
    child = build_inherited_context({})
    assert child["policy"] == []
    assert child["evidence"] == []
