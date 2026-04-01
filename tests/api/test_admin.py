"""Admin API tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_list_proto_classes(client):
    with patch("clarke.api.routes.admin.ProtoClassManager") as MockManager:
        mock_manager = AsyncMock()
        mock_manager.list_classes.return_value = [
            {
                "id": "pc_1",
                "label": "design_queries",
                "member_count": 45,
                "stability_score": 0.82,
                "status": "operational",
            }
        ]
        MockManager.return_value = mock_manager

        response = await client.get("/admin/proto-classes?tenant_id=t1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["label"] == "design_queries"


@pytest.mark.asyncio
async def test_promote_proto_class(client):
    with patch("clarke.api.routes.admin.ProtoClassManager") as MockManager:
        mock_manager = AsyncMock()
        mock_manager.promote_class.return_value = {"id": "pc_1", "status": "operational"}
        MockManager.return_value = mock_manager

        response = await client.post("/admin/proto-classes/pc_1/promote")
        assert response.status_code == 200
        assert response.json()["status"] == "operational"


@pytest.mark.asyncio
async def test_trigger_clustering(client, mock_session):
    from unittest.mock import MagicMock

    # scalars() is sync, .all() is sync — match SQLAlchemy Result behavior
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch("clarke.api.routes.admin.ProtoClassManager") as MockManager:
        mock_manager = AsyncMock()
        mock_manager.run_clustering.return_value = [
            {"id": "pc_1", "label": "cluster_0", "member_count": 10}
        ]
        MockManager.return_value = mock_manager

        response = await client.post(
            "/admin/cluster",
            json={"tenant_id": "t1"},
        )
        assert response.status_code == 200
