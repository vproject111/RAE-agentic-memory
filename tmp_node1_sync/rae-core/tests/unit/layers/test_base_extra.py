from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.layers.base import MemoryLayerBase


class DummyLayer(MemoryLayerBase):
    async def add_memory(
        self, content, tags=None, metadata=None, embedding=None, importance=None
    ):
        return uuid4()

    async def get_memory(self, memory_id):
        return None

    async def search_memories(self, query, limit=10, filters=None):
        return []

    async def cleanup(self):
        return 0


@pytest.mark.asyncio
async def test_memory_layer_base_abstract_calls():
    mock_storage = MagicMock()
    layer = DummyLayer(mock_storage, "test", "tenant", "agent")
    mem_id = uuid4()

    await layer.add_memory("test")
    await layer.get_memory(mem_id)
    await layer.search_memories("test")
    await layer.cleanup()

    mock_storage.count_memories = AsyncMock(return_value=5)
    await layer.count_memories()

    mock_storage.delete_memory = AsyncMock(return_value=True)
    await layer.delete_memory(mem_id)
