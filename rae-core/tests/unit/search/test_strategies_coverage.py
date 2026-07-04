"""Unit tests for search strategies to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.strategies.graph import GraphTraversalStrategy


class TestGraphTraversalStrategyCoverage:
    """Test suite for GraphTraversalStrategy coverage gaps."""

    @pytest.fixture
    def mock_deps(self):
        gs = MagicMock()
        gs.get_neighbors = AsyncMock()
        ms = MagicMock()
        return gs, ms

    @pytest.mark.asyncio
    async def test_search_with_seed_ids(self, mock_deps):
        gs, ms = mock_deps
        strat = GraphTraversalStrategy(graph_store=gs, memory_storage=ms)

        sid = uuid4()
        nid = uuid4()
        gs.get_neighbors.return_value = [nid]

        # Test with string seed_id
        res = await strat.search(
            "query",
            "t1",
            filters={"seed_ids": [str(sid)], "edge_type": "link", "max_depth": 1},
        )
        assert len(res) == 1
        assert res[0][0] == nid
        gs.get_neighbors.assert_called_once()
        args = gs.get_neighbors.call_args.kwargs
        assert args["edge_type"] == "link"

    @pytest.mark.asyncio
    async def test_search_no_seeds(self, mock_deps):
        gs, ms = mock_deps
        strat = GraphTraversalStrategy(graph_store=gs, memory_storage=ms)
        res = await strat.search("q", "t")
        assert res == []

    def test_getters(self, mock_deps):
        gs, ms = mock_deps
        strat = GraphTraversalStrategy(
            graph_store=gs, memory_storage=ms, default_weight=0.5
        )
        assert strat.get_strategy_name() == "graph"
        assert strat.get_strategy_weight() == 0.5
