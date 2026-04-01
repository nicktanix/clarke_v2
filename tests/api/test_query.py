"""Query endpoint tests."""

import pytest

from clarke.api.schemas.query import BrokerQueryResponse


@pytest.mark.asyncio
async def test_query_missing_tenant_id(client):
    response = await client.post(
        "/query",
        json={
            "project_id": "p_001",
            "user_id": "u_001",
            "message": "test",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_missing_message(client):
    response = await client.post(
        "/query",
        json={
            "tenant_id": "t_001",
            "project_id": "p_001",
            "user_id": "u_001",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_valid_request(client, mock_broker):
    mock_response = BrokerQueryResponse(
        request_id="r_test123",
        answer="Test answer",
        degraded_mode=False,
    )
    mock_broker.handle_query.return_value = mock_response

    response = await client.post(
        "/query",
        json={
            "tenant_id": "t_001",
            "project_id": "p_001",
            "user_id": "u_001",
            "session_id": "s_001",
            "message": "What is CLARKE?",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Test answer"
    assert data["request_id"] == "r_test123"
    assert data["degraded_mode"] is False


@pytest.mark.asyncio
async def test_query_request_id_in_response_headers(client, mock_broker):
    mock_response = BrokerQueryResponse(
        request_id="r_header_test",
        answer="Test",
    )
    mock_broker.handle_query.return_value = mock_response

    response = await client.post(
        "/query",
        json={
            "tenant_id": "t_001",
            "project_id": "p_001",
            "user_id": "u_001",
            "message": "test",
        },
    )

    assert "x-request-id" in response.headers
