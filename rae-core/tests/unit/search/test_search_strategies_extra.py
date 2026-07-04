from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from rae_core.search.strategies.fulltext import FullTextStrategy
from rae_core.search.strategies.sparse import SparseVectorStrategy


@pytest.fixture
def mock_storage():
    return MagicMock()


@pytest.mark.asyncio
async def test_fulltext_extra_coverage(mock_storage):
    strategy = FullTextStrategy(mock_storage)

    # Test memory_id as string
    mem_id_str = str(uuid4())
    mock_storage.list_memories = AsyncMock(
        return_value=[{"id": mem_id_str, "content": "test content", "tags": ["tag1"]}]
    )

    results = await strategy.search("test", "tenant")
    assert len(results) == 1
    assert isinstance(results[0][0], UUID)
    assert str(results[0][0]) == mem_id_str

    # Test score 0 filter
    mock_storage.list_memories = AsyncMock(
        return_value=[{"id": uuid4(), "content": "completely different", "tags": []}]
    )
    results = await strategy.search("xyz", "tenant")
    assert len(results) == 0

    # Test strategy name and weight
    assert strategy.get_strategy_name() == "fulltext"
    assert strategy.get_strategy_weight() == 0.2

    # Test empty memories
    mock_storage.list_memories = AsyncMock(return_value=[])
    results = await strategy.search("test", "tenant")
    assert results == []


@pytest.mark.asyncio
async def test_sparse_extra_coverage(mock_storage):
    strategy = SparseVectorStrategy(mock_storage)

    # Test memory_id as string
    mem_id_str = str(uuid4())
    mock_storage.list_memories = AsyncMock(
        return_value=[{"id": mem_id_str, "content": "test content"}]
    )

    results = await strategy.search("test", "tenant")
    assert len(results) == 1
    assert isinstance(results[0][0], UUID)

    # Test score 0 filter
    mock_storage.list_memories = AsyncMock(
        return_value=[{"id": uuid4(), "content": "completely different"}]
    )
    results = await strategy.search("xyz", "tenant")
    assert len(results) == 0

    # Test avg_doc_length for doc_count 0 (though search handles it earlier)
    # We can test _tokenize or other methods too
    assert strategy._tokenize("") == []

    # Test strategy name and weight
    assert strategy.get_strategy_name() == "sparse"
    assert strategy.get_strategy_weight() == 0.2

    # Test empty memories
    mock_storage.list_memories = AsyncMock(return_value=[])
    results = await strategy.search("test", "tenant")
    assert results == []
