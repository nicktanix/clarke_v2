"""LangGraph workflow tests."""

import pytest

from clarke.graph.nodes.build_retrieval_plan import build_retrieval_plan
from clarke.graph.nodes.compose_context_pack import compose_context_pack
from clarke.graph.nodes.extract_features import extract_features
from clarke.graph.nodes.inspect_response import inspect_response
from clarke.graph.nodes.rerank_candidates import rerank_candidates
from clarke.graph.nodes.validate_request import validate_request


def test_validate_request_generates_request_id():
    state = {
        "tenant_id": "t_001",
        "project_id": "p_001",
        "user_id": "u_001",
        "message": "test",
    }
    result = validate_request(state)
    assert result["request_id"].startswith("r_")


def test_validate_request_preserves_existing_id():
    state = {
        "request_id": "r_existing",
        "tenant_id": "t_001",
        "project_id": "p_001",
        "user_id": "u_001",
        "message": "test",
    }
    result = validate_request(state)
    assert result["request_id"] == "r_existing"


def test_validate_request_missing_fields():
    state = {"message": "test"}
    result = validate_request(state)
    assert "error" in result
    assert "tenant_id" in result["error"]


def test_extract_features_returns_features():
    state = {"message": "What is the architecture design pattern?"}
    result = extract_features(state)
    features = result["query_features"]
    assert "is_design_oriented" in features
    assert features["is_design_oriented"] > 0
    assert "keywords" in features
    assert len(features["keywords"]) > 0


def test_extract_features_doc_dependency():
    state = {"message": "What does the specification document say?"}
    result = extract_features(state)
    assert result["query_features"]["doc_dependency"] > 0


@pytest.mark.asyncio
async def test_build_retrieval_plan_generates_requests():
    state = {
        "message": "How does authentication work?",
        "query_features": {"keywords": ["authentication", "work"]},
        "degraded_mode": False,
        "tenant_id": "t_001",
    }
    result = await build_retrieval_plan(state)
    assert len(result["retrieval_plan"]) >= 1
    assert result["retrieval_plan"][0]["source"] == "docs"


@pytest.mark.asyncio
async def test_build_retrieval_plan_skips_in_canonical_only():
    state = {"message": "test", "execution_mode": "canonical_only"}
    result = await build_retrieval_plan(state)
    assert result["retrieval_plan"] == []


@pytest.mark.asyncio
async def test_build_retrieval_plan_skips_in_reduced():
    state = {"message": "test", "execution_mode": "reduced"}
    result = await build_retrieval_plan(state)
    assert result["retrieval_plan"] == []


@pytest.mark.asyncio
async def test_rerank_candidates_empty_input():
    state = {"retrieved_items": [], "message": "test"}
    result = await rerank_candidates(state)
    assert result["retrieved_items"] == []


def test_compose_context_pack_with_items():
    state = {
        "retrieved_items": [
            {
                "item_id": "i1",
                "tenant_id": "t1",
                "project_id": "p1",
                "source": "docs",
                "node_type": "chunk",
                "score": 0.9,
                "summary": "High relevance content",
                "provenance": {},
            },
            {
                "item_id": "i2",
                "tenant_id": "t1",
                "project_id": "p1",
                "source": "docs",
                "node_type": "chunk",
                "score": 0.5,
                "summary": "Lower relevance",
                "provenance": {},
            },
        ],
        "query_features": {},
    }
    result = compose_context_pack(state)
    pack = result["context_pack"]
    assert len(pack["anchors"]) == 1  # score >= 0.8
    assert len(pack["evidence"]) == 1  # score < 0.8


def test_compose_context_pack_empty():
    state = {"retrieved_items": [], "query_features": {}}
    result = compose_context_pack(state)
    assert result["context_pack"]["anchors"] == []
    assert result["context_pack"]["evidence"] == []


def test_inspect_response_no_escalation():
    result = inspect_response({"model_response": "A plain answer."})
    assert result["context_request_detected"] is False
    assert result["subagent_spawn_requested"] is False


def test_inspect_response_detects_context_request():
    response = '{"type": "CONTEXT_REQUEST", "requests": []}'
    result = inspect_response({"model_response": response})
    assert result["context_request_detected"] is True


def test_inspect_response_detects_subagent_spawn():
    response = '{"type": "SUBAGENT_SPAWN", "task": "test"}'
    result = inspect_response({"model_response": response})
    assert result["subagent_spawn_requested"] is True
