"""Context pack renderer — builds ContextPack from categorized items."""

from clarke.api.schemas.retrieval import ContextBudget, ContextPack, RetrievedItem
from clarke.llm.token_counting import count_tokens


def render_context_pack(
    evidence_items: list[RetrievedItem],
    budget: dict[str, int],
    model: str = "",
) -> ContextPack:
    """Build a ContextPack from retrieved items with exact token counts.

    Items with score >= 0.8 become anchors; rest are evidence.
    Policy section is static. Recent state empty for Phase 2.
    """
    anchors: list[dict] = []
    evidence: list[dict] = []

    for item in evidence_items:
        entry = {
            "source": item.source,
            "summary": item.summary,
            "score": item.score,
            "item_id": item.item_id,
            "provenance": item.provenance.model_dump() if item.provenance else {},
        }
        if item.score >= 0.8:
            anchors.append(entry)
        else:
            evidence.append(entry)

    # Enforce budgets
    anchor_budget = budget.get("anchors", 800)
    evidence_budget = budget.get("evidence", 1800)

    anchors = _truncate_entries(anchors, anchor_budget, model)
    evidence = _truncate_entries(evidence, evidence_budget, model)

    total_tokens = sum(count_tokens(e.get("summary", ""), model) for e in anchors + evidence)

    return ContextPack(
        policy=[],
        anchors=anchors,
        evidence=evidence,
        recent_state=[],
        budget=ContextBudget(input_tokens=total_tokens, actual_tokenizer=model or "estimated"),
    )


def _truncate_entries(entries: list[dict], max_tokens: int, model: str) -> list[dict]:
    """Greedily select entries that fit within token budget."""
    selected: list[dict] = []
    used = 0
    for entry in entries:
        tokens = count_tokens(entry.get("summary", ""), model)
        if used + tokens > max_tokens:
            break
        selected.append(entry)
        used += tokens
    return selected
