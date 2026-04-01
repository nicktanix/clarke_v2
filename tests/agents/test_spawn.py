"""Spawn validation tests."""

from unittest.mock import AsyncMock

import pytest

from clarke.agents.spawn import validate_spawn_request
from clarke.settings import BrokerSettings, LearningSettings


@pytest.fixture
def broker_settings():
    return BrokerSettings(max_subagent_depth=5, max_active_subagents_per_root=10)


@pytest.fixture
def learning_settings():
    return LearningSettings()


@pytest.mark.asyncio
async def test_validate_spawn_valid(broker_settings, learning_settings):
    session = AsyncMock()
    approved, reason = await validate_spawn_request(
        spawn_request={
            "task": "Analyze websocket reconnection tradeoffs separately",
            "max_depth": 3,
        },
        tenant_id="t1",
        project_id="p1",
        current_depth=0,
        root_agent_id=None,
        session=session,
        broker_settings=broker_settings,
        learning_settings=learning_settings,
    )
    assert approved is True
    assert reason == ""


@pytest.mark.asyncio
async def test_validate_spawn_depth_exceeded(broker_settings, learning_settings):
    session = AsyncMock()
    approved, reason = await validate_spawn_request(
        spawn_request={"task": "Some long enough task definition here"},
        tenant_id="t1",
        project_id="p1",
        current_depth=5,
        root_agent_id=None,
        session=session,
        broker_settings=broker_settings,
        learning_settings=learning_settings,
    )
    assert approved is False
    assert "Depth" in reason


@pytest.mark.asyncio
async def test_validate_spawn_task_too_short(broker_settings, learning_settings):
    session = AsyncMock()
    approved, reason = await validate_spawn_request(
        spawn_request={"task": "short"},
        tenant_id="t1",
        project_id="p1",
        current_depth=0,
        root_agent_id=None,
        session=session,
        broker_settings=broker_settings,
        learning_settings=learning_settings,
    )
    assert approved is False
    assert "short" in reason.lower() or "empty" in reason.lower()


@pytest.mark.asyncio
async def test_validate_spawn_bad_source(broker_settings, learning_settings):
    session = AsyncMock()
    approved, reason = await validate_spawn_request(
        spawn_request={
            "task": "Analyze something with unauthorized sources",
            "required_memory": ["forbidden_source"],
        },
        tenant_id="t1",
        project_id="p1",
        current_depth=0,
        root_agent_id=None,
        session=session,
        broker_settings=broker_settings,
        learning_settings=learning_settings,
    )
    assert approved is False
    assert "not allowed" in reason.lower() or "Source" in reason
