"""BrokerService tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clarke.api.schemas.query import BrokerQueryRequest
from clarke.broker.service import BrokerService
from clarke.llm.contracts import LLMResponse, TokenUsage


@pytest.mark.asyncio
async def test_broker_service_handle_query():
    mock_llm_response = LLMResponse(
        content="CLARKE is a context engine.",
        model="gpt-4o-mini",
        usage=TokenUsage(input_tokens=100, output_tokens=20),
        latency_ms=150,
    )

    request = BrokerQueryRequest(
        tenant_id="t_001",
        project_id="p_001",
        user_id="u_001",
        session_id="s_001",
        message="What is CLARKE?",
    )

    mock_session = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    mock_store = AsyncMock()
    mock_store.health_check = AsyncMock(return_value=True)

    import clarke.retrieval.qdrant.client as qdrant_module

    original_store = qdrant_module._store

    with (
        patch("clarke.graph.nodes.call_answer_model.LLMGateway") as MockGateway,
        patch(
            "clarke.broker.service.get_request_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "clarke.graph.nodes.run_semantic_retrieval.embed_single",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ),
        patch(
            "clarke.graph.nodes.run_semantic_retrieval.semantic_search",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        mock_gateway = AsyncMock()
        mock_gateway.call = AsyncMock(return_value=mock_llm_response)
        MockGateway.return_value = mock_gateway

        qdrant_module._store = mock_store
        try:
            service = BrokerService()
            response = await service.handle_query(request, mock_session)
        finally:
            qdrant_module._store = original_store

        assert response.answer == "CLARKE is a context engine."
        assert response.degraded_mode is False
        assert response.request_id.startswith("r_")
