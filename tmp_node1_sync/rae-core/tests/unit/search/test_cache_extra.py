from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.cache import SearchCache


@pytest.fixture
def mock_cache_provider():
    return MagicMock()


@pytest.mark.asyncio
async def test_search_cache_get_success(mock_cache_provider):
    cache = SearchCache(mock_cache_provider)
    id1 = uuid4()
    mock_cache_provider.get = AsyncMock(return_value=[{"id": str(id1), "score": 0.9}])

    results = await cache.get("q", "t", "s")
    assert results is not None
    assert len(results) == 1
    assert results[0] == (id1, 0.9)


@pytest.mark.asyncio
async def test_search_cache_get_none(mock_cache_provider):
    cache = SearchCache(mock_cache_provider)
    mock_cache_provider.get = AsyncMock(return_value=None)

    assert await cache.get("q", "t", "s") is None


@pytest.mark.asyncio
async def test_search_cache_get_invalid_data(mock_cache_provider):
    cache = SearchCache(mock_cache_provider)

    # Missing 'id' key
    mock_cache_provider.get = AsyncMock(return_value=[{"score": 0.9}])
    assert await cache.get("q", "t", "s") is None

    # Invalid UUID
    mock_cache_provider.get = AsyncMock(return_value=[{"id": "invalid", "score": 0.9}])
    assert await cache.get("q", "t", "s") is None


@pytest.mark.asyncio
async def test_search_cache_invalidate_all(mock_cache_provider):
    cache = SearchCache(mock_cache_provider)
    mock_cache_provider.clear = AsyncMock(return_value=5)

    # Invalidate without strategy (line 153)
    count = await cache.invalidate("t1")
    assert count == 5
    mock_cache_provider.clear.assert_called_with("search:*")
