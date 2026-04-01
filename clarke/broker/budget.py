"""Token budget allocation."""

from pydantic import BaseModel


class TokenBudget(BaseModel):
    """Budget allocation by context section (percentages)."""

    policy_pct: float = 0.15
    anchors_pct: float = 0.20
    evidence_pct: float = 0.45
    recent_state_pct: float = 0.20
    total_tokens: int = 4000


def calculate_budget(query_features: dict | None = None) -> TokenBudget:
    """Calculate token budget with dynamic multipliers based on query features.

    Phase 1: returns default split. Phase 2+ applies feature-based adjustments.
    """
    budget = TokenBudget()

    if not query_features:
        return budget

    if query_features.get("is_design_oriented", 0) > 0.5:
        budget.anchors_pct += 0.10
        budget.evidence_pct -= 0.10

    if query_features.get("doc_dependency", 0) > 0.5:
        budget.evidence_pct += 0.10
        budget.recent_state_pct -= 0.10

    if query_features.get("recent_history_dependency", 0) > 0.5:
        budget.recent_state_pct += 0.10
        budget.anchors_pct -= 0.10

    return budget
