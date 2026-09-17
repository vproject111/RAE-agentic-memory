"""Unit tests for GraphLiteStrategy (Iteration 6)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_core.search.strategies import SearchStrategy
from rae_core.search.strategies.graph_lite import GraphLiteStrategy


class MockSeedStrategy(SearchStrategy):
    def __init__(self, seed_candidates: list):
        self.seed_candidates = seed_candidates
        self.call_count = 0

    async def search(self, *args, **kwargs):
        self.call_count += 1
        return self.seed_candidates

    def get_strategy_name(self) -> str:
        return "vector_mock"

    def get_strategy_weight(self) -> float:
        return 1.0


@pytest.mark.asyncio
async def test_graph_lite_autonomous_seed_expansion():
    seed1 = uuid4()
    seed2 = uuid4()
    neighbor1_1 = uuid4()
    neighbor1_2 = uuid4()
    neighbor2_1 = uuid4()

    mock_seed_strat = MockSeedStrategy([(seed1, 0.9, 0.5), (seed2, 0.8, 0.5)])

    mock_graph_store = AsyncMock()

    async def get_neighbors_side_effect(node_id, tenant_id, edge_type=None):
        if node_id == seed1:
            return [neighbor1_1, neighbor1_2]
        if node_id == seed2:
            return [neighbor2_1, neighbor1_1]  # neighbor1_1 is shared (multi-path)
        return []

    mock_graph_store.get_neighbors.side_effect = get_neighbors_side_effect

    strategy = GraphLiteStrategy(
        graph_store=mock_graph_store,
        seed_strategy=mock_seed_strat,
        max_depth=2,
    )

    results = await strategy.search(
        query="test graph query",
        tenant_id="tenant-123",
        limit=10,
    )

    assert mock_seed_strat.call_count == 1
    assert len(results) >= 3

    # Check that neighbor1_1 has higher score due to multi-path accumulation
    res_dict = {r[0]: r[1] for r in results}
    assert neighbor1_1 in res_dict
    assert neighbor1_2 in res_dict
    assert neighbor2_1 in res_dict
    assert res_dict[neighbor1_1] > res_dict[neighbor1_2]


@pytest.mark.asyncio
async def test_graph_lite_explicit_seeds_override():
    explicit_seed = uuid4()
    neighbor = uuid4()

    mock_seed_strat = MockSeedStrategy([(uuid4(), 0.9, 0.5)])
    mock_graph_store = AsyncMock()
    mock_graph_store.get_neighbors.return_value = [neighbor]

    strategy = GraphLiteStrategy(
        graph_store=mock_graph_store,
        seed_strategy=mock_seed_strat,
    )

    results = await strategy.search(
        query="query",
        tenant_id="tenant-123",
        seed_ids=[explicit_seed],
    )

    # Seed strategy should NOT be called if explicit seeds provided
    assert mock_seed_strat.call_count == 0
    assert len(results) == 1
    assert results[0][0] == neighbor


@pytest.mark.asyncio
async def test_graph_lite_latency_budget():
    """DoD: Expansion must execute in under 40ms."""
    seed = uuid4()
    neighbors = [uuid4() for _ in range(10)]

    mock_seed_strat = MockSeedStrategy([(seed, 0.9, 0.5)])
    mock_graph_store = AsyncMock()
    mock_graph_store.get_neighbors.return_value = neighbors

    strategy = GraphLiteStrategy(
        graph_store=mock_graph_store,
        seed_strategy=mock_seed_strat,
        max_depth=2,
        max_nodes_per_seed=15,
    )

    start = time.perf_counter()
    results = await strategy.search(
        query="speed test",
        tenant_id="tenant-123",
    )
    duration_ms = (time.perf_counter() - start) * 1000

    assert len(results) > 0
    assert duration_ms < 40.0, f"Graph expansion too slow: {duration_ms:.2f}ms"
