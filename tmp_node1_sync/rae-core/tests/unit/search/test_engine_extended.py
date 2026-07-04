"""Extended tests for HybridSearchEngine and NoiseAwareSearchEngine."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.engine import HybridSearchEngine, NoiseAwareSearchEngine


class TestHybridSearchEngineExtended:
    @pytest.fixture
    def mock_strategy(self):
        strategy = MagicMock()
        strategy.search = AsyncMock(return_value=[])
        strategy.get_strategy_weight.return_value = 1.0
        return strategy

    @pytest.fixture
    def engine(self, mock_strategy):
        return HybridSearchEngine(strategies={"s1": mock_strategy})

    @pytest.mark.asyncio
    async def test_rrf_fusion_logic(self, engine):
        id1 = uuid4()
        id2 = uuid4()

        # Strategy 1 results: id1 at rank 1, id2 at rank 2
        # Strategy 2 results: id2 at rank 1, id1 at rank 2
        strategy_results = {
            "s1": [(id1, 0.9), (id2, 0.8)],
            "s2": [(id2, 0.9), (id1, 0.8)],
        }
        weights = {"s1": 1.0, "s2": 1.0}

        fused = engine._reciprocal_rank_fusion(strategy_results, weights)

        # In RRF with equal weights and symmetrical ranks, scores should be equal
        assert len(fused) == 2
        assert fused[0][1] == fused[1][1]
        assert fused[0][1] == (1.0 / (60 + 1)) + (1.0 / (60 + 2))

    @pytest.mark.asyncio
    async def test_search_with_cache(self, mock_strategy):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        engine = HybridSearchEngine(strategies={"s1": mock_strategy}, cache=mock_cache)

        # First call - cache miss
        await engine.search("query", "t1")
        assert mock_strategy.search.call_count == 1
        assert mock_cache.set.call_count == 1

        # Second call - cache hit
        mock_cache.get.return_value = [(uuid4(), 1.0)]
        mock_strategy.search.reset_mock()

        results = await engine.search("query", "t1")
        assert len(results) == 1
        assert mock_strategy.search.call_count == 0

    @pytest.mark.asyncio
    async def test_search_single_strategy(self, engine, mock_strategy):
        mem_id = uuid4()
        mock_strategy.search.return_value = [(mem_id, 0.5)]

        results = await engine.search_single_strategy("s1", "q", "t1")
        assert len(results) == 1
        assert results[0][0] == mem_id


class TestNoiseAwareSearchEngine:
    @pytest.fixture
    def mock_strategy(self):
        s = MagicMock()
        s.search = AsyncMock()
        s.get_strategy_weight.return_value = 1.0
        return s

    @pytest.fixture
    def engine(self, mock_strategy):
        return NoiseAwareSearchEngine(
            strategies={"s1": mock_strategy}, noise_threshold=0.5
        )

    def test_apply_noise_aware_boost(self, engine):
        id_recent = uuid4()
        id_old = uuid4()
        now = datetime.now(timezone.utc)

        results = [(id_recent, 0.5), (id_old, 0.5)]
        metadata = {
            id_recent: {"created_at": now, "confidence_score": 1.0},
            id_old: {"created_at": now - timedelta(days=30), "confidence_score": 0.5},
        }

        # High noise (0.8 > 0.5 threshold)
        boosted = engine._apply_noise_aware_boost(results, metadata, noise_level=0.8)

        assert boosted[0][0] == id_recent
        assert boosted[0][1] > boosted[1][1]

    @pytest.mark.asyncio
    async def test_search_noise_aware(self, engine, mock_strategy):
        mem_id = uuid4()
        mock_strategy.search.return_value = [(mem_id, 0.5)]
        metadata = {mem_id: {"created_at": datetime.now(timezone.utc)}}

        # Baseline (no noise)
        results_clean = await engine.search(
            "q", "t1", noise_level=0.0, memory_metadata=metadata
        )
        score_clean = results_clean[0][1]

        # With noise (0.8 > 0.5 threshold)
        results_noisy = await engine.search(
            "q", "t1", noise_level=0.8, memory_metadata=metadata
        )
        score_noisy = results_noisy[0][1]

        assert score_noisy > score_clean
