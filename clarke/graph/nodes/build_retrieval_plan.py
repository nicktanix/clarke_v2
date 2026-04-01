"""Build candidate retrieval plan with learned weights and exploration."""

from clarke.graph.state import BrokerState
from clarke.retrieval.planner.exploration import select_exploration_strategy, should_explore
from clarke.settings import get_settings
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

# Available strategies for exploration
_AVAILABLE_STRATEGIES = [
    {"source": "docs", "strategy": "direct"},
    {"source": "docs", "strategy": "leaf_first"},
    {"source": "memory", "strategy": "direct"},
    {"source": "decisions", "strategy": "direct"},
    {"source": "recent_history", "strategy": "direct"},
]


async def build_retrieval_plan(state: BrokerState) -> dict:
    """Generate retrieval requests with learned weights and exploration.

    Execution modes:
    - FULL: normal retrieval plan
    - REDUCED: skip semantic retrieval (Qdrant down), but policy+decisions still fetched by fetch_graph_and_memory
    - CANONICAL_ONLY: skip all retrieval — policy+decisions fetched directly
    """
    execution_mode = state.get("execution_mode", "full")
    if execution_mode == "canonical_only":
        return {"retrieval_plan": [], "retrieved_items": []}
    if execution_mode == "reduced":
        # Qdrant is down — no semantic retrieval, but we still return an empty plan
        # so the graph proceeds. Policy + decisions are fetched by fetch_graph_and_memory.
        return {"retrieval_plan": [], "retrieved_items": []}

    settings = get_settings()
    message = state.get("message", "")
    features = state.get("query_features") or {}
    tenant_id = state.get("tenant_id", "")

    # Load learned weights if available
    weight_map: dict[str, float] = {}
    avg_epsilon = settings.learning.epsilon_initial
    try:
        from clarke.storage.postgres.database import get_db_session

        async for session in get_db_session():
            from clarke.storage.postgres.repositories.weight_repo import get_weights

            weights = await get_weights(session, tenant_id)
            for w in weights:
                weight_map[f"{w.source}:{w.strategy}"] = w.weight
            if weights:
                avg_epsilon = sum(w.epsilon for w in weights) / len(weights)
            break
    except Exception:
        logger.debug("weight_loading_skipped", reason="db not available")

    requests = []

    # Primary semantic search
    primary_weight = weight_map.get("docs:direct", 0.85)
    requests.append(
        {
            "source": "docs",
            "strategy": "direct",
            "query": message,
            "weight": primary_weight,
            "constraints": {"max_items": 20, "timeout_ms": 800},
        }
    )

    # Keyword-focused secondary if enough keywords
    keywords = features.get("keywords", [])
    if len(keywords) >= 3:
        keyword_query = " ".join(keywords[:10])
        if keyword_query != message:
            kw_weight = weight_map.get("docs:direct", 0.65)
            requests.append(
                {
                    "source": "docs",
                    "strategy": "direct",
                    "query": keyword_query,
                    "weight": kw_weight * 0.75,
                    "constraints": {"max_items": 10, "timeout_ms": 800},
                }
            )

    # Episodic memory retrieval if query references history
    if features.get("recent_history_dependency", 0) > 0.3:
        memory_weight = weight_map.get("memory:direct", 0.5)
        requests.append(
            {
                "source": "memory",
                "strategy": "direct",
                "query": message,
                "weight": memory_weight,
                "constraints": {"max_items": 5, "timeout_ms": 800},
            }
        )

    # Rewrite templates: generate query variants for the primary source
    from clarke.retrieval.planner.templates import apply_template, select_templates

    templates = select_templates("docs", "direct", features, max_templates=1)
    for tmpl in templates:
        rewritten = apply_template(tmpl["template"], message)
        if rewritten != message:
            requests.append(
                {
                    "source": tmpl["source"],
                    "strategy": tmpl["strategy"],
                    "query": rewritten,
                    "weight": primary_weight * 0.7,
                    "constraints": {"max_items": 10, "timeout_ms": 800},
                    "template": tmpl["description"],
                }
            )

    # Exploration: with probability epsilon, add one low-weight strategy
    excluded = {f"{r['source']}:{r['strategy']}" for r in requests}
    if should_explore(avg_epsilon):
        exploration_req = select_exploration_strategy(_AVAILABLE_STRATEGIES, weight_map, excluded)
        if exploration_req:
            exploration_req["query"] = message
            requests.append(exploration_req)
            logger.info(
                "exploration_strategy_added",
                source=exploration_req["source"],
                strategy=exploration_req["strategy"],
            )

    return {
        "retrieval_plan": requests,
        "retrieved_items": [],
    }
