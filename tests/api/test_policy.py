"""Policy API tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_create_policy(client):
    with patch("clarke.api.routes.policy.PolicyService") as MockService:
        mock_service = AsyncMock()
        mock_service.create_policy.return_value = {"id": "pol_123", "status": "draft"}
        MockService.return_value = mock_service

        response = await client.post(
            "/policy",
            json={"tenant_id": "t1", "content": "No direct DB access", "owner_id": "u1"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == "pol_123"
        assert response.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_list_policies(client):
    with patch("clarke.api.routes.policy.PolicyService") as MockService:
        mock_service = AsyncMock()
        mock_service.get_active.return_value = [
            {"id": "p1", "content": "Policy one", "status": "active", "source": "policy"},
        ]
        MockService.return_value = mock_service

        response = await client.get("/policy?tenant_id=t1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
