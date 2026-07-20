"""Extended tests for HybridSearchEngine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.engine import HybridSearchEngine


class TestHybridSearchEngineExtended:
    @pytest.fixture
    def mock_strategy(self):
        strategy = MagicMock()
        strategy.search = AsyncMock(return_value=[])
        strategy.get_strategy_weight.return_value = 1.0
        strategy.get_strategy_name.return_value = "s1"
        return strategy

    @pytest.fixture
    def engine(self, mock_strategy):
        # We need more mocks for the modern HybridSearchEngine
        mock_embedding = MagicMock()
        mock_storage = MagicMock()
        return HybridSearchEngine(
            strategies={"s1": mock_strategy},
            embedding_provider=mock_embedding,
            memory_storage=mock_storage,
        )

    @pytest.mark.asyncio
    async def test_search_single_strategy(self, engine, mock_strategy):
        mem_id = uuid4()
        mock_strategy.search.return_value = [(mem_id, 0.5)]

        # Mocking the storage content fetch
        engine._fetch_contents = AsyncMock(return_value={mem_id: "content"})

        results = await engine.search("q", "t1", strategies=["s1"])
        assert len(results) > 0
        assert results[0][0] == mem_id
