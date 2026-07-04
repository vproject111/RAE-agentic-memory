from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.layers.working import WorkingLayer
from rae_core.models.memory import MemoryItem, MemoryLayer


@pytest.fixture
def mock_storage():
    storage = Mock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock()
    storage.get_memory = AsyncMock()
    storage.delete_memory = AsyncMock()
    storage.count_memories = AsyncMock(return_value=0)
    storage.delete_memories_below_importance = AsyncMock(return_value=0)
    storage.update_memory_access = AsyncMock(return_value=True)
    storage.list_memories = AsyncMock(return_value=[])
    storage.search_memories = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def working_layer(mock_storage):
    return WorkingLayer(
        storage=mock_storage,
        tenant_id="tenant_1",
        agent_id="agent_1",
        max_capacity=3,
        importance_threshold=0.5,
    )


@pytest.mark.asyncio
async def test_add_memory_within_capacity(working_layer, mock_storage):
    expected_id = uuid4()
    mock_storage.store_memory.return_value = expected_id
    mock_storage.count_memories.return_value = 2  # Current count

    mem_id = await working_layer.add_memory("test content", importance=0.6)

    assert mem_id == expected_id
    mock_storage.store_memory.assert_called_once()
    assert mock_storage.store_memory.call_args.kwargs["importance"] == 0.6
    mock_storage.delete_memory.assert_not_called()  # No eviction


@pytest.mark.asyncio
async def test_add_memory_exceeding_capacity_triggers_eviction(
    working_layer, mock_storage
):
    expected_id = uuid4()
    mock_storage.store_memory.return_value = expected_id
    # Simulate capacity exceeding max_capacity (e.g., 4 items where max is 3)
    mock_storage.count_memories.return_value = 4

    # Simulate existing memories, lowest importance first
    least_important_id = uuid4()
    mock_storage.list_memories.return_value = [
        {"id": least_important_id, "importance": 0.1}
    ]

    mem_id = await working_layer.add_memory("new content", importance=0.7)

    assert mem_id == expected_id
    mock_storage.store_memory.assert_called_once()
    mock_storage.list_memories.assert_called_once()  # Eviction triggered
    mock_storage.delete_memory.assert_called_once_with(
        memory_id=least_important_id, tenant_id="tenant_1"
    )


@pytest.mark.asyncio
async def test_get_memory_updates_access(working_layer, mock_storage):
    mem_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_storage.get_memory.return_value = {
        "id": mem_id,
        "content": "active",
        "layer": "working",
        "tenant_id": "t",
        "agent_id": "a",
        "created_at": now,
        "last_accessed_at": now,
    }

    item = await working_layer.get_memory(mem_id)

    assert item is not None
    mock_storage.update_memory_access.assert_called_once_with(
        memory_id=mem_id, tenant_id="tenant_1"
    )


@pytest.mark.asyncio
async def test_cleanup_removes_below_threshold(working_layer, mock_storage):
    mock_storage.delete_memories_below_importance.return_value = 5

    deleted_count = await working_layer.cleanup()

    assert deleted_count == 5
    mock_storage.delete_memories_below_importance.assert_called_once_with(
        tenant_id="tenant_1",
        agent_id="agent_1",
        layer="working",
        importance_threshold=0.5,
    )


@pytest.mark.asyncio
async def test_promote_to_working(working_layer, mock_storage):
    expected_id = uuid4()
    mock_storage.store_memory.return_value = expected_id

    sensory_mem = MemoryItem(
        id=uuid4(),
        content="sensory",
        layer=MemoryLayer.SENSORY,
        tenant_id="t",
        agent_id="a",
        importance=0.4,  # Below threshold
    )

    new_mem_id = await working_layer.promote_to_working(sensory_mem, new_importance=0.8)

    assert new_mem_id == expected_id
    mock_storage.store_memory.assert_called_once()
    assert mock_storage.store_memory.call_args.kwargs["importance"] == 0.8


@pytest.mark.asyncio
async def test_get_capacity_status(working_layer, mock_storage):
    mock_storage.count_memories.return_value = 2

    status = await working_layer.get_capacity_status()

    assert status["current_count"] == 2
    assert status["max_capacity"] == 3
    assert status["available_slots"] == 1
    assert status["is_full"] is False
    assert status["utilization_pct"] == (2 / 3) * 100
