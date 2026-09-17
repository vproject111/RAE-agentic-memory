"""Unit tests for StrategyRouter and HybridSearchEngine routing integration (Iteration 5)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_core.evaluation.golden_queries import QueryCategory
from rae_core.models.evidence_package import EvidencePackage
from rae_core.search.engine import HybridSearchEngine
from rae_core.search.router import RoutingPlan, StrategyRouter
from rae_core.search.strategies import SearchStrategy


class MockStrategy(SearchStrategy):
    def __init__(self, name: str, return_items: list):
        self.name = name
        self.return_items = return_items
        self.call_count = 0

    async def search(self, *args, **kwargs):
        self.call_count += 1
        return self.return_items

    def get_strategy_name(self) -> str:
        return self.name

    def get_strategy_weight(self) -> float:
        return 1.0


def test_strategy_router_exact_identifier():
    router = StrategyRouter()
    plan: RoutingPlan = router.route(
        query="CVE-2026-0001 vulnerability",
        available_strategies=["vector", "fulltext", "graph"],
    )

    assert plan.category == QueryCategory.EXACT_IDENTIFIER
    assert "fulltext" in plan.active_strategies
    assert plan.strategy_weights["fulltext"] >= 0.70
    assert "graph" in plan.pruned_strategies
    assert "graph" not in plan.active_strategies


def test_strategy_router_graph_relation():
    router = StrategyRouter()
    plan: RoutingPlan = router.route(
        query="who calls AdaptiveSearchEngine?",
        available_strategies=["vector", "fulltext", "graph"],
    )

    assert plan.category == QueryCategory.GRAPH_RELATION
    assert "graph" in plan.active_strategies
    assert plan.strategy_weights["graph"] >= 0.50


@pytest.mark.asyncio
async def test_hybrid_search_with_auto_routing_pruning():
    uid1 = uuid4()
    strat_fulltext = MockStrategy("fulltext", [(uid1, 0.9, 0.5)])
    strat_vector = MockStrategy("vector", [(uid1, 0.5, 0.5)])
    strat_graph = MockStrategy("graph", [(uid1, 0.4, 0.5)])

    strategies: dict[str, SearchStrategy] = {
        "fulltext": strat_fulltext,
        "vector": strat_vector,
        "graph": strat_graph,
    }

    mock_storage = AsyncMock()
    mock_storage.get_memories_batch.return_value = [
        {"id": uid1, "content": "CVE-2026-1234 fixed", "importance": 0.9}
    ]

    engine = HybridSearchEngine(
        strategies=strategies,
        memory_storage=mock_storage,
    )

    # Exact identifier query with auto_route=True
    package: EvidencePackage = await engine.search_evidence(
        query="CVE-2026-1234",
        tenant_id="tenant-1",
        auto_route=True,
    )

    assert isinstance(package, EvidencePackage)
    assert "routing_plan" in package.metadata
    assert package.metadata["routing_plan"]["category"] == "exact_identifier"

    # Fulltext and Vector should be executed, but Graph should be pruned (call_count == 0)
    assert strat_fulltext.call_count == 1
    assert strat_vector.call_count == 1
    assert (
        strat_graph.call_count == 0
    ), "Graph strategy should have been pruned to save latency"
