from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.layers.reflective import ReflectiveLayer
from rae_core.models.reflection import Reflection, ReflectionPriority, ReflectionType


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.store_memory = AsyncMock(return_value=uuid4())
    storage.get_memory = AsyncMock()
    storage.update_memory_access = AsyncMock()
    storage.search_memories = AsyncMock()
    storage.list_memories = AsyncMock()
    storage.delete_memories_with_metadata_filter = AsyncMock()
    return storage


@pytest.mark.asyncio
async def test_reflective_layer_add_memory_default_importance(mock_storage):
    layer = ReflectiveLayer(mock_storage, "t1", "a1")
    await layer.add_memory("test")

    call_args = mock_storage.store_memory.call_args
    assert call_args.kwargs["importance"] == 0.8


@pytest.mark.asyncio
async def test_reflective_layer_get_memory_not_found(mock_storage):
    layer = ReflectiveLayer(mock_storage, "t1", "a1")
    mock_storage.get_memory.return_value = None
    assert await layer.get_memory(uuid4()) is None


@pytest.mark.asyncio
async def test_reflective_layer_get_reflection_not_found(mock_storage):
    layer = ReflectiveLayer(mock_storage, "t1", "a1")
    # Mock get_memory internally
    mock_storage.get_memory.return_value = None
    assert await layer.get_reflection(uuid4()) is None


@pytest.mark.asyncio
async def test_reflective_layer_search_memories(mock_storage):
    layer = ReflectiveLayer(mock_storage, "t1", "a1")
    mock_storage.search_memories.return_value = [
        {
            "memory": {
                "id": uuid4(),
                "content": "c1",
                "layer": "reflective",
                "tenant_id": "t1",
                "agent_id": "a1",
                "importance": 0.9,
                "created_at": datetime.now().isoformat(),
            },
            "score": 0.9,
        }
    ]

    results = await layer.search_memories(
        "query", reflection_type=ReflectionType.INSIGHT
    )
    assert len(results) == 1
    assert mock_storage.search_memories.called


@pytest.mark.asyncio
async def test_reflective_layer_find_methods(mock_storage):
    layer = ReflectiveLayer(mock_storage, "t1", "a1")
    mock_storage.list_memories.return_value = []

    await layer.find_contradictions()
    assert mock_storage.list_memories.called

    await layer.find_patterns()
    assert mock_storage.list_memories.call_count == 2


@pytest.mark.asyncio
async def test_reflective_layer_add_reflection_low_source_count(mock_storage):
    layer = ReflectiveLayer(mock_storage, "t1", "a1", min_source_memories=3)
    reflection = Reflection(
        content="test",
        reflection_type=ReflectionType.INSIGHT,
        priority=ReflectionPriority.MEDIUM,
        source_memory_ids=[uuid4()],  # Only 1
        tenant_id="t1",
        agent_id="a1",
    )

    with pytest.raises(ValueError, match="at least 3 source memories"):
        await layer.add_reflection(reflection)
