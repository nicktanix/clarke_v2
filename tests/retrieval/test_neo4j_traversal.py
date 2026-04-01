"""Neo4j traversal tests."""

from unittest.mock import AsyncMock

import pytest

from clarke.retrieval.neo4j.traversal import GraphTraversal


@pytest.fixture
def mock_store():
    store = AsyncMock()
    store.execute_read = AsyncMock(return_value=[])
    return store


@pytest.mark.asyncio
async def test_find_related_entities_empty_names(mock_store):
    traversal = GraphTraversal(mock_store)
    result = await traversal.find_related_entities("t1", "p1", [])
    assert result == []
    mock_store.execute_read.assert_not_called()


@pytest.mark.asyncio
async def test_find_related_entities_calls_cypher(mock_store):
    mock_store.execute_read.return_value = [
        {"name": "Entity1", "node_type": "Entity", "content": "test", "id": "e1", "confidence": 0.8}
    ]
    traversal = GraphTraversal(mock_store)
    result = await traversal.find_related_entities("t1", "p1", ["websocket"])
    assert len(result) == 1
    mock_store.execute_read.assert_called_once()
    call_args = mock_store.execute_read.call_args
    assert "tenant_id" in call_args[0][0] or "$tenant_id" in call_args[0][0]


@pytest.mark.asyncio
async def test_find_convergence_anchors_needs_2_ids(mock_store):
    traversal = GraphTraversal(mock_store)
    result = await traversal.find_convergence_anchors("t1", "p1", ["id1"])
    assert result == []
    mock_store.execute_read.assert_not_called()


@pytest.mark.asyncio
async def test_find_convergence_anchors_with_ids(mock_store):
    mock_store.execute_read.return_value = [
        {
            "name": "Shared Concept",
            "node_type": "Concept",
            "id": "c1",
            "shared_count": 2,
            "confidence": 0.7,
        }
    ]
    traversal = GraphTraversal(mock_store)
    result = await traversal.find_convergence_anchors("t1", "p1", ["id1", "id2"])
    assert len(result) == 1


@pytest.mark.asyncio
async def test_find_decision_lineage_empty_keywords(mock_store):
    traversal = GraphTraversal(mock_store)
    result = await traversal.find_decision_lineage("t1", "p1", [])
    assert result == []
