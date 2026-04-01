"""Memory inheritance — build child context from parent context pack."""

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


def build_inherited_context(
    parent_context_pack: dict,
    handoff_mode: str = "hybrid",
    handoff_evidence: list[str] | None = None,
) -> dict:
    """Assemble child context from parent context pack using handoff mode.

    Modes:
    - copy_in: snapshot of all parent evidence + policy
    - hybrid (default): copy high-score items + policy, reference rest
    - reference_link: not implemented in Phase 6
    """
    if not parent_context_pack:
        return {"policy": [], "anchors": [], "evidence": [], "recent_state": [], "budget": {}}

    # Policy always inherited
    policy = parent_context_pack.get("policy", [])

    if handoff_mode == "copy_in":
        # Full snapshot of parent context
        return {
            "policy": policy,
            "anchors": parent_context_pack.get("anchors", []),
            "evidence": parent_context_pack.get("evidence", []),
            "recent_state": [],
            "budget": parent_context_pack.get("budget", {}),
        }

    # hybrid mode: copy specific evidence + all policy
    evidence = parent_context_pack.get("evidence", [])
    anchors = parent_context_pack.get("anchors", [])

    if handoff_evidence:
        # Filter to only requested items
        evidence_ids = set(handoff_evidence)
        evidence = [e for e in evidence if e.get("item_id") in evidence_ids]

    # Include high-score anchors
    inherited_anchors = [a for a in anchors if a.get("top_score", a.get("score", 0)) >= 0.7]

    return {
        "policy": policy,
        "anchors": inherited_anchors,
        "evidence": evidence,
        "recent_state": [],
        "budget": parent_context_pack.get("budget", {}),
    }
