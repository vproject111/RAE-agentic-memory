from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.layers.reflective import ReflectiveLayer
from rae_core.models.memory import MemoryLayer
from rae_core.models.reflection import Reflection, ReflectionPriority, ReflectionType


@pytest.fixture
def mock_storage():
    storage = Mock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock()
    storage.get_memory = AsyncMock()
    storage.list_memories = AsyncMock(return_value=[])
    storage.search_memories = AsyncMock(return_value=[])
    storage.delete_memories_with_metadata_filter = AsyncMock(return_value=0)
    storage.update_memory_access = AsyncMock(return_value=True)
    return storage


@pytest.fixture
def reflective_layer(mock_storage):
    return ReflectiveLayer(
        storage=mock_storage,
        tenant_id="tenant_1",
        agent_id="agent_1",
        min_source_memories=2,
    )


@pytest.mark.asyncio
async def test_add_reflection_success(reflective_layer, mock_storage):
    expected_id = uuid4()
    mock_storage.store_memory.return_value = expected_id

    reflection = Reflection(
        content="insight",
        reflection_type=ReflectionType.INSIGHT,
        source_memory_ids=[uuid4(), uuid4()],
        tenant_id="tenant_1",
        agent_id="agent_1",
        priority=ReflectionPriority.HIGH,
    )

    mem_id = await reflective_layer.add_reflection(reflection)

    assert mem_id == expected_id
    mock_storage.store_memory.assert_called_once()
    call_kwargs = mock_storage.store_memory.call_args.kwargs
    assert call_kwargs["layer"] == MemoryLayer.REFLECTIVE.value
    assert call_kwargs["importance"] == 0.85  # High priority
    assert call_kwargs["metadata"]["reflection_type"] == "insight"


@pytest.mark.asyncio
async def test_add_reflection_insufficient_source_memories(
    reflective_layer, mock_storage
):
    reflection = Reflection(
        content="insight",
        reflection_type=ReflectionType.INSIGHT,
        source_memory_ids=[uuid4()],  # Only 1 source memory
        tenant_id="tenant_1",
        agent_id="agent_1",
    )

    with pytest.raises(
        ValueError, match="Reflection requires at least 2 source memories"
    ):
        await reflective_layer.add_reflection(reflection)


@pytest.mark.asyncio
async def test_get_reflection(reflective_layer, mock_storage):
    mem_id = uuid4()
    reflection_id = uuid4()
    now = datetime.now(timezone.utc)

    mock_storage.get_memory.return_value = {
        "id": mem_id,
        "content": "pattern",
        "layer": "reflective",
        "tenant_id": "t",
        "agent_id": "a",
        "created_at": now,
        "last_accessed_at": now,
        "metadata": {
            "reflection_id": str(reflection_id),
            "reflection_type": "pattern",
            "priority": "medium",
            "source_memory_ids": [str(uuid4())],
            "confidence": 0.7,
        },
    }

    reflection_obj = await reflective_layer.get_reflection(mem_id)

    assert reflection_obj is not None
    assert reflection_obj.id == reflection_id
    assert reflection_obj.reflection_type == ReflectionType.PATTERN
    assert reflection_obj.confidence == 0.7


@pytest.mark.asyncio
async def test_cleanup_removes_low_confidence(reflective_layer, mock_storage):
    mock_storage.delete_memories_with_metadata_filter.return_value = 3

    deleted_count = await reflective_layer.cleanup()

    assert deleted_count == 3
    mock_storage.delete_memories_with_metadata_filter.assert_called_once_with(
        tenant_id="tenant_1",
        agent_id="agent_1",
        layer="reflective",
        metadata_filter={"confidence__lt": 0.3},
    )


@pytest.mark.asyncio
async def test_get_reflections_by_type(reflective_layer, mock_storage):
    mem_id_1 = uuid4()
    mem_id_2 = uuid4()
    now = datetime.now(timezone.utc)

    mock_storage.list_memories.return_value = [
        {
            "id": mem_id_1,
            "content": "pattern 1",
            "layer": "reflective",
            "tenant_id": "t",
            "agent_id": "a",
            "created_at": now,
            "last_accessed_at": now,
            "metadata": {
                "reflection_type": "pattern",
                "priority": "high",
                "source_memory_ids": [],
            },
        },
        {
            "id": mem_id_2,
            "content": "pattern 2",
            "layer": "reflective",
            "tenant_id": "t",
            "agent_id": "a",
            "created_at": now,
            "last_accessed_at": now,
            "metadata": {
                "reflection_type": "pattern",
                "priority": "medium",
                "source_memory_ids": [],
            },
        },
    ]

    patterns = await reflective_layer.get_reflections_by_type(ReflectionType.PATTERN)

    assert len(patterns) == 2
    assert patterns[0].reflection_type == ReflectionType.PATTERN
    mock_storage.list_memories.assert_called_once()
