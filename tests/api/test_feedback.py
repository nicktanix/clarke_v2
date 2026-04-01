"""Feedback endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_feedback_returns_202(client):
    with (
        patch("clarke.api.routes.feedback.create_feedback", new_callable=AsyncMock) as mock_create,
        patch(
            "clarke.api.routes.feedback.get_episode_by_request_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        mock_create.return_value = AsyncMock()

        response = await client.post(
            "/feedback",
            json={
                "request_id": "r_test",
                "tenant_id": "t_001",
                "user_id": "u_001",
                "accepted": True,
            },
        )
        assert response.status_code == 202
        assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_feedback_persists_record(client):
    with (
        patch("clarke.api.routes.feedback.create_feedback", new_callable=AsyncMock) as mock_create,
        patch(
            "clarke.api.routes.feedback.get_episode_by_request_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        mock_create.return_value = AsyncMock()

        await client.post(
            "/feedback",
            json={
                "request_id": "r_test",
                "tenant_id": "t_001",
                "user_id": "u_001",
                "accepted": True,
                "score": 0.9,
                "retrieved_item_ids": ["i1", "i2"],
            },
        )
        mock_create.assert_called_once()
        call_data = mock_create.call_args[0][1]
        assert call_data["request_id"] == "r_test"
        assert call_data["accepted"] is True
        assert call_data["score"] == 0.9
