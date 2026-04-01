"""Context composer tests — budgeter, dedupe, renderer."""

from clarke.api.schemas.retrieval import Provenance, RetrievedItem
from clarke.retrieval.composer.budgeter import allocate_budget, enforce_budget
from clarke.retrieval.composer.dedupe import deduplicate_items
from clarke.retrieval.composer.renderer import render_context_pack


def _make_item(item_id: str, score: float = 0.5, summary: str = "test") -> RetrievedItem:
    return RetrievedItem(
        item_id=item_id,
        tenant_id="t1",
        project_id="p1",
        source="docs",
        node_type="chunk",
        score=score,
        summary=summary,
        provenance=Provenance(),
    )


def test_allocate_budget_default():
    budget = allocate_budget()
    assert budget["policy"] == 600  # 15% of 4000
    assert budget["evidence"] == 1800  # 45% of 4000


def test_allocate_budget_design_oriented():
    budget = allocate_budget({"is_design_oriented": 0.9})
    assert budget["anchors"] > 800  # default 20% + 10%


def test_enforce_budget_selects_items():
    # Each item is ~5 tokens (char estimate: 20 chars / 4 = 5)
    items = [_make_item(f"i{i}", summary=f"Item number {i} text") for i in range(10)]
    selected = enforce_budget(items, max_tokens=25)  # fits ~5 items
    assert len(selected) < 10
    assert len(selected) > 0


def test_enforce_budget_empty():
    assert enforce_budget([], max_tokens=100) == []


def test_deduplicate_items_removes_similar():
    items = [
        _make_item("a", score=0.9),
        _make_item("b", score=0.8),
    ]
    # Same embedding = similar
    embeddings = {
        "a": [1.0, 0.0, 0.0],
        "b": [1.0, 0.0, 0.0],
    }
    result = deduplicate_items(items, embeddings, similarity_threshold=0.9)
    assert len(result) == 1
    assert result[0].item_id == "a"  # higher score kept


def test_deduplicate_items_keeps_different():
    items = [_make_item("a"), _make_item("b")]
    embeddings = {
        "a": [1.0, 0.0, 0.0],
        "b": [0.0, 1.0, 0.0],
    }
    result = deduplicate_items(items, embeddings)
    assert len(result) == 2


def test_render_context_pack():
    items = [
        _make_item("high", score=0.9, summary="High score item"),
        _make_item("low", score=0.5, summary="Low score item"),
    ]
    budget = {"anchors": 1000, "evidence": 1000}
    pack = render_context_pack(items, budget)
    assert len(pack.anchors) == 1  # score >= 0.8
    assert len(pack.evidence) == 1  # score < 0.8
    assert pack.budget.input_tokens > 0
