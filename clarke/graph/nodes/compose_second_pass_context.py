"""Compose merged context pack for second-pass LLM call."""

from clarke.api.schemas.retrieval import RetrievedItem
from clarke.graph.state import BrokerState
from clarke.retrieval.composer.renderer import render_context_pack
from clarke.settings import get_settings


def compose_second_pass_context(state: BrokerState) -> dict:
    """Merge first-pass and second-pass items into a combined context pack.

    Second-pass budget is limited to a fraction of first-pass budget.
    """
    settings = get_settings()

    first_pack = state.get("context_pack") or {}
    first_tokens = first_pack.get("budget", {}).get("input_tokens", 0)
    second_budget = (
        int(first_tokens * settings.learning.second_pass_budget_fraction) if first_tokens else 2000
    )

    second_items_raw = state.get("second_pass_retrieved_items") or []
    second_items = [
        RetrievedItem(**item) if isinstance(item, dict) else item for item in second_items_raw
    ]

    budget = {
        "anchors": second_budget // 3,
        "evidence": second_budget * 2 // 3,
    }

    second_pack = render_context_pack(
        evidence_items=second_items,
        budget=budget,
        model=settings.llm.default_answer_model,
    )

    # Merge: keep first-pass context, append second-pass items
    merged = {
        "policy": first_pack.get("policy", []),
        "anchors": first_pack.get("anchors", []) + second_pack.anchors,
        "evidence": first_pack.get("evidence", []) + second_pack.evidence,
        "recent_state": first_pack.get("recent_state", []),
        "budget": {
            "input_tokens": first_tokens + second_pack.budget.input_tokens,
            "actual_tokenizer": second_pack.budget.actual_tokenizer,
        },
    }

    return {
        "second_pass_context_pack": merged,
        "second_pass_injected_items": [item.model_dump() for item in second_items],
    }
