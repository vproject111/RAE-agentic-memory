from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from rae_core.search.strategies.fulltext import FullTextStrategy


@pytest.mark.asyncio
async def test_fulltext_wildcard_search():
    # Setup
    mock_storage = AsyncMock()
    mock_storage.list_memories.return_value = [
        {"id": str(UUID(int=1)), "content": "Memory 1", "tags": []},
        {"id": str(UUID(int=2)), "content": "Memory 2", "tags": []},
        {"id": str(UUID(int=3)), "content": "Memory 3", "tags": []},
    ]

    strategy = FullTextStrategy(memory_storage=mock_storage)

    # Execute wildcard search
    results = await strategy.search(query="*", tenant_id="tenant-123")

    # Verify
    assert len(results) == 3
    assert results[0][1] == 1.0
    assert results[1][1] == 1.0
    assert results[2][1] == 1.0

    # Verify storage was called correctly
    mock_storage.list_memories.assert_called_once()


@pytest.mark.asyncio
async def test_fulltext_normal_search():
    # Setup
    mock_storage = AsyncMock()
    mock_storage.list_memories.return_value = [
        {"id": str(UUID(int=1)), "content": "Target memory", "tags": []},
        {"id": str(UUID(int=2)), "content": "Other memory", "tags": []},
    ]

    strategy = FullTextStrategy(memory_storage=mock_storage)

    # Execute normal search
    results = await strategy.search(query="Target", tenant_id="tenant-123")

    # Verify
    assert len(results) == 1
    assert results[0][0] == UUID(int=1)
    assert results[0][1] > 0.0
