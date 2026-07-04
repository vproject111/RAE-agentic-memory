"""Unit tests for MultiVectorSearchStrategy."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.strategies.multi_vector import MultiVectorSearchStrategy


class TestMultiVectorStrategy:
    """Test suite for MultiVectorSearchStrategy."""

    @pytest.mark.asyncio
    async def test_search_fusion(self):
        # Setup mocks
        store1 = MagicMock()
        provider1 = MagicMock()
        store2 = MagicMock()
        provider2 = MagicMock()

        id1, id2 = uuid4(), uuid4()

        provider1.embed_text = AsyncMock(return_value=[0.1] * 384)
        store1.search_similar = AsyncMock(return_value=[(id1, 0.9)])

        provider2.embed_text = AsyncMock(return_value=[0.2] * 768)
        store2.search_similar = AsyncMock(return_value=[(id2, 0.8)])

        strategy = MultiVectorSearchStrategy(
            [(store1, provider1, "layer1"), (store2, provider2, "layer2")]
        )

        results = await strategy.search("query", "tenant")

        assert len(results) == 2
        assert strategy.get_strategy_name() == "multi_vector_fusion"
        assert strategy.get_strategy_weight() == 0.5

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        store = MagicMock()
        provider = MagicMock()
        provider.embed_text = AsyncMock(side_effect=Exception("API Error"))

        strategy = MultiVectorSearchStrategy([(store, provider, "layer")])
        results = await strategy.search("query", "tenant")

        assert results == []
