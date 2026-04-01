"""LangGraph workflow definition for the broker execution graph."""

from langgraph.graph import END, StateGraph

from clarke.graph.nodes.build_retrieval_plan import build_retrieval_plan
from clarke.graph.nodes.call_answer_model import call_answer_model
from clarke.graph.nodes.call_second_pass_model import call_second_pass_model
from clarke.graph.nodes.check_dependency_health import check_health
from clarke.graph.nodes.compose_context_pack import compose_context_pack
from clarke.graph.nodes.compose_second_pass_context import compose_second_pass_context
from clarke.graph.nodes.create_subagent_instance import create_subagent_instance
from clarke.graph.nodes.extract_features import extract_features
from clarke.graph.nodes.fetch_graph_and_memory import fetch_graph_and_memory
from clarke.graph.nodes.inspect_response import inspect_response
from clarke.graph.nodes.persist_episode import persist_episode
from clarke.graph.nodes.rerank_candidates import rerank_candidates
from clarke.graph.nodes.run_second_pass_retrieval import run_second_pass_retrieval
from clarke.graph.nodes.run_semantic_retrieval import run_semantic_retrieval
from clarke.graph.nodes.validate_context_request import validate_context_request
from clarke.graph.nodes.validate_request import validate_request
from clarke.graph.nodes.validate_subagent_spawn import validate_subagent_spawn
from clarke.graph.state import BrokerState


def _route_after_inspect(state: BrokerState) -> str:
    """3-way routing: CONTEXT_REQUEST, SUBAGENT_SPAWN, or persist."""
    if state.get("context_request_detected") and state.get("retrieval_loop_count", 0) < 1:
        return "validate_context_request"
    if state.get("subagent_spawn_requested"):
        return "validate_subagent_spawn"
    return "persist_episode"


def build_graph() -> StateGraph:
    """Build the Phase 6 broker execution graph with multi-agent support."""
    graph = StateGraph(BrokerState)

    # First-pass nodes
    graph.add_node("validate_request", validate_request)
    graph.add_node("check_health", check_health)
    graph.add_node("extract_features", extract_features)
    graph.add_node("build_retrieval_plan", build_retrieval_plan)
    graph.add_node("run_semantic_retrieval", run_semantic_retrieval)
    graph.add_node("rerank_candidates", rerank_candidates)
    graph.add_node("fetch_graph_and_memory", fetch_graph_and_memory)
    graph.add_node("compose_context_pack", compose_context_pack)
    graph.add_node("call_answer_model", call_answer_model)
    graph.add_node("inspect_response", inspect_response)

    # CONTEXT_REQUEST second-pass nodes
    graph.add_node("validate_context_request", validate_context_request)
    graph.add_node("run_second_pass_retrieval", run_second_pass_retrieval)
    graph.add_node("compose_second_pass_context", compose_second_pass_context)
    graph.add_node("call_second_pass_model", call_second_pass_model)

    # SUBAGENT_SPAWN nodes
    graph.add_node("validate_subagent_spawn", validate_subagent_spawn)
    graph.add_node("create_subagent_instance", create_subagent_instance)

    # Terminal
    graph.add_node("persist_episode", persist_episode)

    graph.set_entry_point("validate_request")

    # First-pass edges
    graph.add_edge("validate_request", "check_health")
    graph.add_edge("check_health", "extract_features")
    graph.add_edge("extract_features", "build_retrieval_plan")
    graph.add_edge("build_retrieval_plan", "run_semantic_retrieval")
    graph.add_edge("run_semantic_retrieval", "rerank_candidates")
    graph.add_edge("rerank_candidates", "fetch_graph_and_memory")
    graph.add_edge("fetch_graph_and_memory", "compose_context_pack")
    graph.add_edge("compose_context_pack", "call_answer_model")
    graph.add_edge("call_answer_model", "inspect_response")

    # 3-way conditional routing after inspect_response
    graph.add_conditional_edges(
        "inspect_response",
        _route_after_inspect,
        {
            "validate_context_request": "validate_context_request",
            "validate_subagent_spawn": "validate_subagent_spawn",
            "persist_episode": "persist_episode",
        },
    )

    # CONTEXT_REQUEST chain
    graph.add_edge("validate_context_request", "run_second_pass_retrieval")
    graph.add_edge("run_second_pass_retrieval", "compose_second_pass_context")
    graph.add_edge("compose_second_pass_context", "call_second_pass_model")
    graph.add_edge("call_second_pass_model", "persist_episode")

    # SUBAGENT_SPAWN chain
    graph.add_edge("validate_subagent_spawn", "create_subagent_instance")
    graph.add_edge("create_subagent_instance", "persist_episode")

    graph.add_edge("persist_episode", END)

    return graph
