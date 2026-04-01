"""Compose the context pack from all retrieval sources with trust-precedence blending."""

from clarke.api.schemas.retrieval import RetrievedItem
from clarke.graph.state import BrokerState
from clarke.llm.prompts import CONTEXT_TEMPLATE_VERSION_ID, PROMPT_VERSION_ID
from clarke.retrieval.composer.anchors import summarize_anchors
from clarke.retrieval.composer.budgeter import allocate_budget
from clarke.retrieval.composer.conflicts import detect_conflicts
from clarke.retrieval.composer.dedupe import deduplicate_by_text_overlap
from clarke.retrieval.composer.renderer import render_context_pack
from clarke.settings import get_settings


def _harmonize_scores(
    items: list[RetrievedItem],
    blending: dict | None = None,
) -> list[RetrievedItem]:
    """Apply blending formula with learned or default weights.

    Uses spec 11.4 formula: final = a*semantic + b*graph + d*trust_boost.
    """
    alpha = blending.get("alpha_semantic", 0.35) if blending else 0.35
    delta = blending.get("delta_trust", 0.25) if blending else 0.25
    beta = blending.get("beta_graph", 0.15) if blending else 0.15

    trust_boosts = {
        "policy": 0.3,
        "decisions": 0.2,
        "graph": 0.1,
        "docs": 0.0,
        "memory": -0.05,
    }

    boosted = []
    for item in items:
        base = item.score * alpha
        trust = trust_boosts.get(item.source, 0.0) * delta
        graph_boost = beta if item.source == "graph" else 0.0
        new_score = min(base + trust + graph_boost + item.score * (1 - alpha), 1.0)
        boosted.append(item.model_copy(update={"score": max(0.0, new_score)}))
    return boosted


def compose_context_pack(state: BrokerState) -> dict:
    """Build the context pack blending semantic + graph + policy + decisions."""
    features = state.get("query_features")
    settings = get_settings()
    model = settings.llm.default_answer_model

    # Collect items from all sources
    all_raw: list[dict] = []

    # Semantic items (already reranked)
    for item in state.get("retrieved_items") or []:
        if isinstance(item, dict):
            item.setdefault("source", "docs")
        all_raw.append(item)

    # Graph items
    for item in state.get("graph_retrieved_items") or []:
        if isinstance(item, dict):
            item.setdefault("source", "graph")
        all_raw.append(item)

    # Decision items → convert to RetrievedItem format
    for d in state.get("decision_items") or []:
        all_raw.append(
            {
                "item_id": d.get("id", ""),
                "tenant_id": state.get("tenant_id", ""),
                "project_id": state.get("project_id", ""),
                "source": "decisions",
                "node_type": "decision",
                "score": 0.6,
                "summary": f"{d.get('title', '')}: {d.get('rationale', '')}",
                "provenance": {},
            }
        )

    # Deduplicate by item_id
    seen: set[str] = set()
    unique: list[dict] = []
    for item in all_raw:
        item_id = item.get("item_id", "")
        if item_id and item_id not in seen:
            seen.add(item_id)
            unique.append(item)

    items = [RetrievedItem(**item) if isinstance(item, dict) else item for item in unique]

    # Deduplicate near-identical items by text overlap
    items = deduplicate_by_text_overlap(items)

    # Detect conflicts between items from different trust tiers
    conflicts = detect_conflicts(items)

    # Apply blending formula (uses defaults; learned weights loaded via BlendingWeight table when available)
    items = _harmonize_scores(items)
    items.sort(key=lambda x: x.score, reverse=True)

    # Extract policy for the policy section
    policy_strings = [
        p.get("content", "") for p in (state.get("policy_items") or []) if p.get("content")
    ]

    # Add conflict notes to policy section so LLM sees them
    for conflict in conflicts:
        policy_strings.append(f"CONFLICT NOTE: {conflict['note']}")

    # Summarize graph items as anchors (prompt-safe)
    graph_items = [i for i in items if i.source == "graph"]
    anchor_summaries = summarize_anchors(graph_items) if graph_items else []

    budget = allocate_budget(query_features=features)
    context_pack = render_context_pack(evidence_items=items, budget=budget, model=model)

    # Inject policy strings and graph anchors
    context_pack_dict = context_pack.model_dump()
    context_pack_dict["policy"] = policy_strings
    if anchor_summaries:
        context_pack_dict["anchors"] = anchor_summaries + context_pack_dict.get("anchors", [])

    return {
        "context_pack": context_pack_dict,
        "injected_items": [item.model_dump() for item in items],
        "prompt_version_id": PROMPT_VERSION_ID,
        "context_template_version_id": CONTEXT_TEMPLATE_VERSION_ID,
    }
