"""Unit tests for search engine and cache to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.cache import SearchCache
from rae_core.search.engine import HybridSearchEngine


class TestSearchCoverage:
    """Test suite for search coverage gaps."""

    @pytest.mark.asyncio
    async def test_search_cache_deserialization_error(self):
        """Test SearchCache handling corrupted data."""
        mock_provider = AsyncMock()
        # Return invalid data format (missing fields)
        mock_provider.get.return_value = [{"bad": "data"}]

        cache = SearchCache(cache_provider=mock_provider)
        res = await cache.get("q", "t", "s")
        assert res is None

    @pytest.mark.asyncio
    async def test_search_cache_type_error(self):
        """Test SearchCache handling non-list data."""
        mock_provider = AsyncMock()
        mock_provider.get.return_value = "not a list"

        cache = SearchCache(cache_provider=mock_provider)
        res = await cache.get("q", "t", "s")
        assert res is None

    @pytest.mark.asyncio
    async def test_engine_search_unknown_strategy(self):
        """Test HybridSearchEngine with missing strategy."""
        engine = HybridSearchEngine(strategies={})
        res = await engine.search("q", "t", strategies=["unknown"])
        assert res == []

    @pytest.mark.asyncio
    async def test_engine_search_single_strategy_unknown(self):
        """Test search_single_strategy with unknown name."""
        engine = HybridSearchEngine(strategies={})
        with pytest.raises(ValueError, match="Unknown strategy"):
            await engine.search_single_strategy("unknown", "q", "t")

    @pytest.mark.asyncio
    async def test_engine_search_weight_resolution(self):
        """Test how engine resolves weights from strategies if not provided."""
        mock_strat = MagicMock()
        mock_strat.search = AsyncMock(return_value=[(uuid4(), 0.5)])
        mock_strat.get_strategy_weight.return_value = 5.0

        engine = HybridSearchEngine(strategies={"s1": mock_strat})
        # weights not provided in call
        results = await engine.search("q", "t")

        assert len(results) == 1
        # RRF score should use weight 5.0
        assert results[0][1] == 5.0 / (60 + 1)

    @pytest.mark.asyncio
    async def test_search_cache_set(self):
        """Test SearchCache.set serialization."""
        mock_provider = AsyncMock()
        cache = SearchCache(cache_provider=mock_provider)
        mid = uuid4()
        results = [(mid, 0.9)]

        await cache.set("q", "t", "s", results)

        # Verify provider.set called with serialized data
        mock_provider.set.assert_called_once()
        args = mock_provider.set.call_args[0]
        # args[1] is the value
        assert args[1][0]["id"] == str(mid)
        assert args[1][0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_search_cache_invalidate(self):
        """Test SearchCache.invalidate with pattern."""
        mock_provider = AsyncMock()
        cache = SearchCache(cache_provider=mock_provider)

        await cache.invalidate(tenant_id="t1", strategy="s1")
        # should call clear with search:s1:*
        mock_provider.clear.assert_called_once()
        assert "s1" in mock_provider.clear.call_args[0][0]

    @pytest.mark.asyncio
    async def test_engine_search_with_cache_hit_single(self, engine_with_cache):
        """Test search_single_strategy with cache hit."""
        engine, mock_cache, mock_strat = engine_with_cache
        mid = uuid4()
        mock_cache.get.return_value = [(mid, 0.9)]

        res = await engine.search_single_strategy("s1", "q", "t")
        assert res == [(mid, 0.9)]
        assert mock_strat.search.call_count == 0

    @pytest.fixture
    def engine_with_cache(self):
        mock_strat = MagicMock()
        mock_strat.search = AsyncMock()
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock()
        mock_cache.set = AsyncMock()
        engine = HybridSearchEngine(strategies={"s1": mock_strat}, cache=mock_cache)
        return engine, mock_cache, mock_strat
