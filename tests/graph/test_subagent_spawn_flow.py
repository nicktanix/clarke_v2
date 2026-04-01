"""Sub-agent spawn workflow routing tests."""

from clarke.graph.nodes.inspect_response import inspect_response
from clarke.graph.workflow import _route_after_inspect


def test_inspect_detects_subagent_spawn():
    response = '{"type": "SUBAGENT_SPAWN", "task": "Analyze tradeoffs"}'
    result = inspect_response({"model_response": response})
    assert result["subagent_spawn_requested"] is True
    assert result["spawn_request"] is not None
    assert result["spawn_request"]["task"] == "Analyze tradeoffs"


def test_inspect_no_spawn():
    result = inspect_response({"model_response": "Plain answer."})
    assert result["subagent_spawn_requested"] is False
    assert result["spawn_request"] is None


def test_route_spawn_detected():
    state = {
        "context_request_detected": False,
        "subagent_spawn_requested": True,
        "retrieval_loop_count": 0,
    }
    assert _route_after_inspect(state) == "validate_subagent_spawn"


def test_route_cr_takes_priority_over_spawn():
    state = {
        "context_request_detected": True,
        "subagent_spawn_requested": True,
        "retrieval_loop_count": 0,
    }
    assert _route_after_inspect(state) == "validate_context_request"


def test_route_neither():
    state = {
        "context_request_detected": False,
        "subagent_spawn_requested": False,
        "retrieval_loop_count": 0,
    }
    assert _route_after_inspect(state) == "persist_episode"
