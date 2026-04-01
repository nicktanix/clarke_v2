"""Combined node: fetch graph traversal, policies, and decisions concurrently."""

import asyncio

from clarke.graph.state import BrokerState
from clarke.memory.decisions import DecisionService
from clarke.memory.policy import PolicyService
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def _fetch_graph(state: BrokerState) -> list[dict]:
    """Run graph traversal against Neo4j."""
    try:
        from clarke.retrieval.neo4j.client import get_neo4j_store
        from clarke.retrieval.neo4j.converter import graph_results_to_retrieved_items
        from clarke.retrieval.neo4j.traversal import GraphTraversal
        from clarke.settings import get_settings

        store = get_neo4j_store()
        settings = get_settings()
        traversal = GraphTraversal(store)

        tenant_id = state["tenant_id"]
        project_id = state["project_id"]
        keywords = (state.get("query_features") or {}).get("keywords", [])

        items = []

        # Entity/concept traversal from keywords
        if keywords:
            results = await traversal.find_related_entities(
                tenant_id,
                project_id,
                keywords,
                max_hops=settings.graph.graph_traversal_max_hops,
                limit=settings.graph.graph_retrieval_top_k,
            )
            items.extend(graph_results_to_retrieved_items(results, tenant_id, project_id))

        # Convergence anchors from semantic results
        semantic_ids = [
            item.get("item_id") if isinstance(item, dict) else item.item_id
            for item in (state.get("retrieved_items") or [])
        ]
        if len(semantic_ids) >= 2:
            anchors = await traversal.find_convergence_anchors(
                tenant_id, project_id, semantic_ids[:10], limit=5
            )
            items.extend(
                graph_results_to_retrieved_items(anchors, tenant_id, project_id, source="graph")
            )

        return [item.model_dump() for item in items]
    except RuntimeError:
        return []
    except Exception:
        logger.warning("graph_retrieval_failed", exc_info=True)
        return []


async def _fetch_policies(state: BrokerState) -> list[dict]:
    """Load active policies from PostgreSQL."""
    try:
        from clarke.storage.postgres.database import get_db_session

        service = PolicyService()
        async for session in get_db_session():
            return await service.get_active(session, state["tenant_id"])
    except Exception:
        logger.warning("policy_fetch_failed", exc_info=True)
    return []


async def _fetch_decisions(state: BrokerState) -> list[dict]:
    """Load relevant decisions from PostgreSQL based on query keywords."""
    try:
        from clarke.storage.postgres.database import get_db_session

        keywords = (state.get("query_features") or {}).get("keywords", [])
        if not keywords:
            return []

        service = DecisionService()
        async for session in get_db_session():
            return await service.get_relevant_decisions(
                session, state["tenant_id"], state["project_id"], keywords
            )
    except Exception:
        logger.warning("decision_fetch_failed", exc_info=True)
    return []


async def fetch_graph_and_memory(state: BrokerState) -> dict:
    """Fetch graph traversal, policies, and decisions concurrently."""
    from clarke.settings import get_settings

    settings = get_settings()

    # Policy and decisions ALWAYS load from PostgreSQL regardless of graph_enabled.
    # Only Neo4j graph traversal is gated by graph_enabled.
    if settings.graph.graph_enabled:
        graph_result, policy_result, decision_result = await asyncio.gather(
            _fetch_graph(state),
            _fetch_policies(state),
            _fetch_decisions(state),
            return_exceptions=True,
        )
    else:
        graph_result: list[dict] = []
        policy_result, decision_result = await asyncio.gather(
            _fetch_policies(state),
            _fetch_decisions(state),
            return_exceptions=True,
        )

    graph_items = graph_result if isinstance(graph_result, list) else []
    policy_items = policy_result if isinstance(policy_result, list) else []
    decision_items = decision_result if isinstance(decision_result, list) else []

    graph_health = settings.graph.graph_enabled and isinstance(graph_result, list)

    return {
        "graph_retrieved_items": graph_items,
        "policy_items": policy_items,
        "decision_items": decision_items,
        "graph_health": graph_health,
    }
