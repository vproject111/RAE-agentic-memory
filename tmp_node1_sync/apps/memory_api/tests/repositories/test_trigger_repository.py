from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from apps.memory_api.repositories.trigger_repository import TriggerRepository


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    # Connection mock
    conn = AsyncMock()

    # Context Manager Mock
    # This needs to be an object that supports __aenter__ and __aexit__
    cm = AsyncMock()
    cm.__aenter__.return_value = conn
    cm.__aexit__.return_value = None

    # pool.acquire() should return the context manager
    # We use MagicMock here so calling pool.acquire() doesn't require 'await' itself,
    # but the result (cm) can be used in 'async with' because it has __aenter__
    # However, asyncpg.Pool.acquire IS an async method usually?
    # Checking asyncpg docs: pool.acquire() IS async context manager, but invoked as:
    # async with pool.acquire() as conn:
    # This means pool.acquire() returns an object that has __aenter__.

    # If pool.acquire is an AsyncMock, calling it returns a coroutine.
    # That coroutine, when awaited, must return the context manager?
    # NO. asyncpg usage is: `async with pool.acquire() as conn`.
    # This implies pool.acquire() returns an AsyncContextManager.

    # Let's try strictly configuring the return value of the call.
    pool.acquire.return_value = cm

    # If the code is `async with self.pool.acquire() as conn`, Python calls `pool.acquire()` first.
    # If pool.acquire is AsyncMock, it returns a Coroutine.
    # `async with` expects an object with `__aenter__` (or `__enter__`).
    # Coroutines don't have `__aenter__`.

    # Therefore pool.acquire MUST be a MagicMock (not AsyncMock) or configured to NOT be a coroutine.
    pool.acquire = MagicMock(return_value=cm)

    return pool


@pytest.fixture
def trigger_repo(mock_pool):
    return TriggerRepository(mock_pool)


@pytest.fixture
def sample_trigger_data():
    return {
        "tenant_id": "t-1",
        "project_id": "p-1",
        "rule_name": "Test Rule",
        "event_types": ["memory_created"],
        "conditions": [{"field": "importance", "operator": "gt", "value": 5}],
        "actions": [{"type": "notify", "channel": "slack"}],
        "created_by": "admin",
        "description": "A test rule",
    }


@pytest.mark.asyncio
async def test_create_trigger(trigger_repo, mock_pool, sample_trigger_data):
    # Setup
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetchrow.return_value = {
        "id": uuid4(),
        **sample_trigger_data,
        "status": "active",
    }

    # Execute
    result = await trigger_repo.create_trigger(**sample_trigger_data)

    # Verify
    assert result["rule_name"] == "Test Rule"
    conn.fetchrow.assert_called_once()
    args = conn.fetchrow.call_args[0]
    # Check if JSON fields are serialized
    assert isinstance(args[6], str)  # conditions -> json
    assert isinstance(args[8], str)  # actions -> json


@pytest.mark.asyncio
async def test_get_active_triggers_for_event(trigger_repo, mock_pool):
    # Setup
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch.return_value = [
        {"id": uuid4(), "rule_name": "Rule 1", "priority": 10},
        {"id": uuid4(), "rule_name": "Rule 2", "priority": 5},
    ]

    # Execute
    results = await trigger_repo.get_active_triggers_for_event(
        "memory_created", "t-1", "p-1"
    )

    # Verify
    assert len(results) == 2
    assert results[0]["rule_name"] == "Rule 1"
    conn.fetch.assert_called_once()
    query = conn.fetch.call_args[0][0]
    assert "status = 'active'" in query
    assert "ANY(event_types)" in query


@pytest.mark.asyncio
async def test_update_trigger_dynamic_query(trigger_repo, mock_pool):
    # Setup
    trigger_id = uuid4()
    updates = {
        "rule_name": "Updated Name",
        "priority": 100,
        "invalid_field": "should be ignored",
    }
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetchrow.return_value = {
        "id": trigger_id,
        "rule_name": "Updated Name",
        "priority": 100,
    }

    # Execute
    result = await trigger_repo.update_trigger(trigger_id, "t-1", updates)

    # Verify
    assert result["rule_name"] == "Updated Name"
    conn.fetchrow.assert_called_once()
    query = conn.fetchrow.call_args[0][0]

    # Check query construction
    assert "rule_name = $3" in query
    assert "priority = $4" in query
    assert "invalid_field" not in query

    # Check args
    call_args = conn.fetchrow.call_args[0]
    assert call_args[1] == trigger_id
    assert call_args[2] == "t-1"
    assert "Updated Name" in call_args
    assert 100 in call_args


@pytest.mark.asyncio
async def test_update_trigger_no_valid_updates(trigger_repo, mock_pool):
    # Setup
    trigger_id = uuid4()
    updates = {"invalid_field": "value"}

    # Mock get_trigger call which happens if no updates
    # We need to mock the separate connection context for get_trigger
    # Since mock_pool.acquire returns the same mock, we need to handle the nested call behavior or simpler:
    # The code calls self.get_trigger if filtered_updates is empty.

    # Let's mock get_trigger directly to verify the fallback
    trigger_repo.get_trigger = AsyncMock(
        return_value={"id": trigger_id, "name": "Original"}
    )

    # Execute
    result = await trigger_repo.update_trigger(trigger_id, "t-1", updates)

    # Verify
    trigger_repo.get_trigger.assert_called_once_with(trigger_id, "t-1")
    assert result["name"] == "Original"


@pytest.mark.asyncio
async def test_delete_trigger(trigger_repo, mock_pool):
    # Setup
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.execute.return_value = "DELETE 1"

    # Execute
    result = await trigger_repo.delete_trigger(uuid4(), "t-1")

    # Verify
    assert result is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_trigger_not_found(trigger_repo, mock_pool):
    # Setup
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.execute.return_value = "DELETE 0"

    # Execute
    result = await trigger_repo.delete_trigger(uuid4(), "t-1")

    # Verify
    assert result is False
