"""Tests for the combined fetch_graph_and_memory node."""

from unittest.mock import AsyncMock, patch

import pytest

from clarke.graph.nodes.fetch_graph_and_memory import fetch_graph_and_memory


@pytest.mark.asyncio
async def test_fetch_graph_and_memory_disabled():
    with patch("clarke.settings.get_settings") as mock_settings:
        mock_settings.return_value.graph.graph_enabled = False
        state = {"tenant_id": "t1", "project_id": "p1", "query_features": {}, "retrieved_items": []}
        result = await fetch_graph_and_memory(state)
        assert result["graph_retrieved_items"] == []
        assert result["policy_items"] == []
        assert result["decision_items"] == []
        assert result["graph_health"] is False


@pytest.mark.asyncio
async def test_fetch_graph_and_memory_all_succeed():
    with (
        patch("clarke.settings.get_settings") as mock_settings,
        patch(
            "clarke.graph.nodes.fetch_graph_and_memory._fetch_graph",
            new_callable=AsyncMock,
        ) as mock_graph,
        patch(
            "clarke.graph.nodes.fetch_graph_and_memory._fetch_policies",
            new_callable=AsyncMock,
        ) as mock_pol,
        patch(
            "clarke.graph.nodes.fetch_graph_and_memory._fetch_decisions",
            new_callable=AsyncMock,
        ) as mock_dec,
    ):
        mock_settings.return_value.graph.graph_enabled = True
        mock_graph.return_value = [{"item_id": "g1", "source": "graph"}]
        mock_pol.return_value = [{"id": "p1", "content": "Policy 1"}]
        mock_dec.return_value = [{"id": "d1", "title": "Decision 1"}]

        state = {"tenant_id": "t1", "project_id": "p1", "query_features": {}, "retrieved_items": []}
        result = await fetch_graph_and_memory(state)

        assert len(result["graph_retrieved_items"]) == 1
        assert len(result["policy_items"]) == 1
        assert len(result["decision_items"]) == 1


@pytest.mark.asyncio
async def test_fetch_graph_and_memory_partial_failure():
    with (
        patch("clarke.settings.get_settings") as mock_settings,
        patch(
            "clarke.graph.nodes.fetch_graph_and_memory._fetch_graph",
            new_callable=AsyncMock,
        ) as mock_graph,
        patch(
            "clarke.graph.nodes.fetch_graph_and_memory._fetch_policies",
            new_callable=AsyncMock,
        ) as mock_pol,
        patch(
            "clarke.graph.nodes.fetch_graph_and_memory._fetch_decisions",
            new_callable=AsyncMock,
        ) as mock_dec,
    ):
        mock_settings.return_value.graph.graph_enabled = True
        mock_graph.side_effect = RuntimeError("Neo4j down")
        mock_pol.return_value = [{"id": "p1", "content": "Policy 1"}]
        mock_dec.return_value = []

        state = {"tenant_id": "t1", "project_id": "p1", "query_features": {}, "retrieved_items": []}
        result = await fetch_graph_and_memory(state)

        assert result["graph_retrieved_items"] == []
        assert len(result["policy_items"]) == 1
