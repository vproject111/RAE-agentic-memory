from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.layers.working import WorkingLayer
from rae_core.models.memory import MemoryItem


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.store_memory = AsyncMock(return_value=uuid4())
    storage.count_memories = AsyncMock(return_value=1)
    storage.get_memory = AsyncMock()
    storage.update_memory_access = AsyncMock()
    storage.search_memories = AsyncMock()
    storage.delete_memories_below_importance = AsyncMock()
    storage.list_memories = AsyncMock()
    storage.delete_memory = AsyncMock()
    return storage


@pytest.mark.asyncio
async def test_working_layer_add_memory_low_importance(mock_storage):
    layer = WorkingLayer(mock_storage, "t1", "a1", importance_threshold=0.5)

    # Test importance < threshold
    await layer.add_memory("test", importance=0.1)

    # Verify importance was boosted to threshold
    call_args = mock_storage.store_memory.call_args
    assert call_args.kwargs["importance"] == 0.5


@pytest.mark.asyncio
async def test_working_layer_get_memory_not_found(mock_storage):
    layer = WorkingLayer(mock_storage, "t1", "a1")
    mock_storage.get_memory.return_value = None

    assert await layer.get_memory(uuid4()) is None


@pytest.mark.asyncio
async def test_working_layer_search_memories(mock_storage):
    layer = WorkingLayer(mock_storage, "t1", "a1")

    # Mock search results in the format expected by the adapter
    mock_storage.search_memories.return_value = [
        {
            "memory": {
                "id": uuid4(),
                "content": "c1",
                "layer": "working",
                "tenant_id": "t1",
                "agent_id": "a1",
                "importance": 0.8,
                "created_at": "2025-01-01",
            },
            "score": 0.95,
        }
    ]

    results = await layer.search_memories("query")
    assert len(results) == 1
    assert results[0].score == 0.95
    assert results[0].memory.content == "c1"


@pytest.mark.asyncio
async def test_working_layer_eviction(mock_storage):
    # Set capacity to 1
    layer = WorkingLayer(mock_storage, "t1", "a1", max_capacity=1)

    # First memory
    mock_storage.count_memories.return_value = 1
    await layer.add_memory("c1")
    assert mock_storage.delete_memory.call_count == 0

    # Second memory (trigger eviction)
    mock_storage.count_memories.return_value = 2
    mock_storage.list_memories.return_value = [{"id": uuid4()}]
    await layer.add_memory("c2")

    assert mock_storage.delete_memory.call_count == 1


@pytest.mark.asyncio
async def test_working_layer_promote(mock_storage):
    layer = WorkingLayer(mock_storage, "t1", "a1")
    memory = MemoryItem(
        id=uuid4(),
        content="promoted",
        layer="sensory",
        tenant_id="t1",
        agent_id="a1",
        importance=0.3,
    )

    await layer.promote_to_working(memory)
    # Importance should be max(0.3, 0.5) = 0.5
    call_args = mock_storage.store_memory.call_args
    assert call_args.kwargs["importance"] == 0.5


@pytest.mark.asyncio
async def test_working_layer_capacity_status(mock_storage):
    layer = WorkingLayer(mock_storage, "t1", "a1", max_capacity=10)
    mock_storage.count_memories.return_value = 5

    status = await layer.get_capacity_status()
    assert status["current_count"] == 5
    assert status["available_slots"] == 5
    assert status["utilization_pct"] == 50.0
