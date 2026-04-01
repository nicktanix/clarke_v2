"""CONTEXT_REQUEST loop tests."""

from clarke.graph.nodes.inspect_response import inspect_response
from clarke.graph.nodes.validate_context_request import validate_context_request
from clarke.graph.workflow import _route_after_inspect


def test_inspect_response_parses_context_request():
    response = '{"type": "CONTEXT_REQUEST", "requests": [{"source": "docs", "query": "test", "why": "need more", "max_items": 3}]}'
    result = inspect_response({"model_response": response})
    assert result["context_request_detected"] is True
    assert result["context_request"] is not None
    assert result["context_request"]["type"] == "CONTEXT_REQUEST"


def test_inspect_response_no_context_request():
    result = inspect_response({"model_response": "Plain answer."})
    assert result["context_request_detected"] is False
    assert result["context_request"] is None


def test_validate_context_request_valid():
    state = {
        "context_request": {
            "type": "CONTEXT_REQUEST",
            "requests": [
                {
                    "source": "docs",
                    "query": "more details",
                    "why": "insufficient context",
                    "max_items": 3,
                }
            ],
        },
        "retrieval_loop_count": 0,
    }
    result = validate_context_request(state)
    assert result.get("retrieval_loop_count") == 1
    assert result.get("context_request_detected") is None  # not set = passes


def test_validate_context_request_bad_source():
    state = {
        "context_request": {
            "type": "CONTEXT_REQUEST",
            "requests": [
                {"source": "invalid_source", "query": "test", "why": "reason", "max_items": 3}
            ],
        },
        "retrieval_loop_count": 0,
    }
    result = validate_context_request(state)
    assert result["context_request_detected"] is False


def test_validate_context_request_empty_why():
    state = {
        "context_request": {
            "type": "CONTEXT_REQUEST",
            "requests": [{"source": "docs", "query": "test", "why": "", "max_items": 3}],
        },
        "retrieval_loop_count": 0,
    }
    result = validate_context_request(state)
    assert result["context_request_detected"] is False


def test_validate_context_request_at_max_loops():
    state = {
        "context_request": {
            "type": "CONTEXT_REQUEST",
            "requests": [{"source": "docs", "query": "test", "why": "reason", "max_items": 3}],
        },
        "retrieval_loop_count": 1,
    }
    result = validate_context_request(state)
    assert result["context_request_detected"] is False


def test_route_after_inspect_with_context_request():
    state = {"context_request_detected": True, "retrieval_loop_count": 0}
    assert _route_after_inspect(state) == "validate_context_request"


def test_route_after_inspect_without_context_request():
    state = {"context_request_detected": False, "retrieval_loop_count": 0}
    assert _route_after_inspect(state) == "persist_episode"


def test_route_after_inspect_at_max_loops():
    state = {"context_request_detected": True, "retrieval_loop_count": 1}
    assert _route_after_inspect(state) == "persist_episode"
