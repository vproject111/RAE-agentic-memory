from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.layers.longterm import LongTermLayer
from rae_core.models.memory import MemoryItem, MemoryLayer


@pytest.fixture
def mock_storage():
    storage = Mock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock()
    storage.get_memory = AsyncMock()
    storage.list_memories = AsyncMock(return_value=[])
    storage.search_memories = AsyncMock(return_value=[])
    storage.delete_memories_below_importance = AsyncMock(return_value=0)
    storage.update_memory_access = AsyncMock(return_value=True)
    storage.count_memories = AsyncMock(return_value=0)
    return storage


@pytest.fixture
def longterm_layer(mock_storage):
    return LongTermLayer(
        storage=mock_storage,
        tenant_id="tenant_1",
        agent_id="agent_1",
    )


@pytest.mark.asyncio
async def test_add_episodic_memory(longterm_layer, mock_storage):
    expected_id = uuid4()
    mock_storage.store_memory.return_value = expected_id

    mem_id = await longterm_layer.add_memory("episodic content")

    assert mem_id == expected_id
    mock_storage.store_memory.assert_called_once()
    call_kwargs = mock_storage.store_memory.call_args.kwargs
    assert call_kwargs["layer"] == MemoryLayer.EPISODIC.value
    assert call_kwargs["metadata"]["memory_subtype"] == "episodic"
    assert call_kwargs["importance"] == 0.5


@pytest.mark.asyncio
async def test_add_semantic_memory(longterm_layer, mock_storage):
    expected_id = uuid4()
    mock_storage.store_memory.return_value = expected_id

    mem_id = await longterm_layer.add_memory(
        "semantic content", is_semantic=True, importance=0.9
    )

    assert mem_id == expected_id
    mock_storage.store_memory.assert_called_once()
    call_kwargs = mock_storage.store_memory.call_args.kwargs
    assert call_kwargs["layer"] == MemoryLayer.SEMANTIC.value
    assert call_kwargs["metadata"]["memory_subtype"] == "semantic"
    assert call_kwargs["importance"] == 0.9


@pytest.mark.asyncio
async def test_get_memory_updates_access(longterm_layer, mock_storage):
    mem_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_storage.get_memory.return_value = {
        "id": mem_id,
        "content": "test",
        "layer": "episodic",
        "tenant_id": "t",
        "agent_id": "a",
        "created_at": now,
        "last_accessed_at": now,
    }

    item = await longterm_layer.get_memory(mem_id)

    assert item is not None
    mock_storage.update_memory_access.assert_called_once_with(
        memory_id=mem_id, tenant_id="tenant_1"
    )


@pytest.mark.asyncio
async def test_search_memories_filters(longterm_layer, mock_storage):
    # Mock search_memories to return some data
    mock_storage.search_memories.return_value = [
        {
            "memory": {
                "id": uuid4(),
                "content": "c",
                "layer": "episodic",
                "tenant_id": "t",
                "agent_id": "a",
                "created_at": datetime.now(timezone.utc),
            },
            "score": 0.8,
        }
    ]

    await longterm_layer.search_memories("query", semantic_only=True)

    # Semantic search call
    semantic_call_kwargs = mock_storage.search_memories.call_args.kwargs
    assert semantic_call_kwargs["layer"] == MemoryLayer.SEMANTIC.value

    mock_storage.search_memories.reset_mock()  # Reset for next test

    await longterm_layer.search_memories("query", episodic_only=True)
    episodic_call_kwargs = mock_storage.search_memories.call_args.kwargs
    assert episodic_call_kwargs["layer"] == MemoryLayer.EPISODIC.value


@pytest.mark.asyncio
async def test_cleanup(longterm_layer, mock_storage):
    mock_storage.delete_memories_below_importance.side_effect = [
        5,
        3,
    ]  # Episodic, Semantic

    deleted_count = await longterm_layer.cleanup()

    assert deleted_count == 8
    assert mock_storage.delete_memories_below_importance.call_count == 2

    # Check calls for both layers
    call_args_list = mock_storage.delete_memories_below_importance.call_args_list
    assert call_args_list[0].kwargs["layer"] == MemoryLayer.EPISODIC.value
    assert call_args_list[1].kwargs["layer"] == MemoryLayer.SEMANTIC.value


@pytest.mark.asyncio
async def test_consolidate_from_working(longterm_layer, mock_storage):
    expected_id = uuid4()
    mock_storage.store_memory.return_value = expected_id

    working_mem = MemoryItem(
        id=uuid4(),
        content="working content",
        layer=MemoryLayer.WORKING,
        tenant_id="t",
        agent_id="a",
        importance=0.6,
    )

    new_mem_id = await longterm_layer.consolidate_from_working(
        working_mem, as_semantic=True
    )

    assert new_mem_id == expected_id
    call_kwargs = mock_storage.store_memory.call_args.kwargs
    assert call_kwargs["layer"] == MemoryLayer.SEMANTIC.value
    assert call_kwargs["importance"] == min(working_mem.importance + 0.2, 1.0)


@pytest.mark.asyncio
async def test_upgrade_to_semantic(longterm_layer, mock_storage):
    episodic_id = uuid4()
    semantic_id = uuid4()
    now = datetime.now(timezone.utc)

    mock_storage.get_memory.return_value = {
        "id": episodic_id,
        "content": "original",
        "layer": "episodic",
        "tenant_id": "t",
        "agent_id": "a",
        "created_at": now,
        "last_accessed_at": now,
        "importance": 0.5,
        "metadata": {},
    }
    mock_storage.store_memory.return_value = semantic_id

    upgraded_id = await longterm_layer.upgrade_to_semantic(
        episodic_id, "generalized content"
    )

    assert upgraded_id == semantic_id
    call_kwargs = mock_storage.store_memory.call_args.kwargs
    assert call_kwargs["content"] == "generalized content"
    assert call_kwargs["layer"] == MemoryLayer.SEMANTIC.value
    assert call_kwargs["importance"] == 0.6  # 0.5 + 0.1
    assert "derived_from_episodic" in call_kwargs["metadata"]


@pytest.mark.asyncio
async def test_count_memories(longterm_layer, mock_storage):
    mock_storage.count_memories.side_effect = [10, 5]  # episodic, semantic

    episodic_count = await longterm_layer.count_episodic()
    semantic_count = await longterm_layer.count_semantic()

    assert episodic_count == 10
    assert semantic_count == 5
    assert mock_storage.count_memories.call_count == 2
