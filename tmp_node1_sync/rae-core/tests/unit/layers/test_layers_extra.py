from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.layers.longterm import LongTermLayer
from rae_core.layers.sensory import SensoryLayer


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.get_memory = AsyncMock()
    return storage


@pytest.mark.asyncio
async def test_longterm_layer_extra(mock_storage):
    layer = LongTermLayer(mock_storage, "t1", "a1")

    # get_memory not found (101)
    mock_storage.get_memory.return_value = None
    assert await layer.get_memory(uuid4()) is None

    # upgrade_to_semantic not found (234)
    with pytest.raises(ValueError, match="not found"):
        await layer.upgrade_to_semantic(uuid4())


@pytest.mark.asyncio
async def test_sensory_layer_extra(mock_storage):
    layer = SensoryLayer(mock_storage, "t1", "a1")

    # get_memory not found (108)
    mock_storage.get_memory.return_value = None
    assert await layer.get_memory(uuid4()) is None

    # extend_ttl not found (180)
    assert await layer.extend_ttl(uuid4(), 10) is False
