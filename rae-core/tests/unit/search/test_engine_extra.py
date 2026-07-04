from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.engine import HybridSearchEngine, NoiseAwareSearchEngine


@pytest.fixture
def mock_strategy():
    strategy = MagicMock()
    strategy.search = AsyncMock(return_value=[(uuid4(), 0.9)])
    strategy.get_strategy_weight = MagicMock(return_value=0.5)
    return strategy


@pytest.mark.asyncio
async def test_search_single_strategy_variants(mock_strategy):
    engine = HybridSearchEngine(strategies={"s1": mock_strategy})

    # Unknown strategy (207)
    with pytest.raises(ValueError, match="Unknown strategy: nonexistent"):
        await engine.search_single_strategy("nonexistent", "q", "t")

    # Success without cache
    res = await engine.search_single_strategy("s1", "q", "t", use_cache=False)
    assert len(res) == 1

    # Success with cache (219, 238)
    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock(return_value=True)
    engine.cache = mock_cache

    # Hits 238 (set cache)
    await engine.search_single_strategy("s1", "q", "t", use_cache=True)
    assert mock_cache.set.called

    # Hits 219 (get from cache)
    mock_cache.get.return_value = [(uuid4(), 0.8)]
    res = await engine.search_single_strategy("s1", "q", "t", use_cache=True)
    assert len(res) == 1
    assert res[0][1] == 0.8


def test_get_available_strategies(mock_strategy):
    engine = HybridSearchEngine(strategies={"s1": mock_strategy})
    assert engine.get_available_strategies() == ["s1"]


@pytest.mark.asyncio
async def test_rerank_placeholder(mock_strategy):
    engine = HybridSearchEngine(strategies={})
    results = [(uuid4(), 0.9)]
    # Should return as-is
    reranked = await engine.rerank("q", results)
    assert reranked == results


def test_noise_aware_boost_low_noise():
    engine = NoiseAwareSearchEngine(strategies={}, noise_threshold=0.5)
    results = [(uuid4(), 0.9)]

    # Hits 295 (noise_level <= threshold)
    boosted = engine._apply_noise_aware_boost(results, {}, 0.3)
    assert boosted == results
