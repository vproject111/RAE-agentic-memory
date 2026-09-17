"""Unit tests for AdaptiveSearchEngine and QueryRewriter (Iteration 4)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_core.models.evidence_package import EvidencePackage
from rae_core.search.adaptive_engine import AdaptiveSearchEngine
from rae_core.search.rewriter import QueryRewriter, RewritePlan
from rae_core.search.strategies import SearchStrategy
from rae_core.search.sufficiency_gate import (
    EvidenceSufficiencyGate,
    GateDecision,
    SufficiencyAssessment,
)

# ==============================================================================
# QUERY REWRITER TESTS
# ==============================================================================


def test_query_rewriter_missing_symbol():
    rewriter = QueryRewriter(default_boost=1.5)
    assessment = SufficiencyAssessment(
        decision=GateDecision.INSUFFICIENT,
        composite_score=0.45,
        relevance_component=0.4,
        coverage_component=0.3,
        diversity_component=0.5,
        trust_component=1.0,
        temporal_component=1.0,
        conflict_penalty=0.0,
        missing_aspects=["HybridSearchEngine", "search_evidence"],
        rationale="Missing technical identifiers",
    )

    plan = rewriter.create_rewrite_plan(
        query="search implementation", assessment=assessment
    )

    assert isinstance(plan, RewritePlan)
    assert plan.original_query == "search implementation"
    assert "HybridSearchEngine" in plan.missing_aspects
    # Strategy adjustments should boost fulltext and anchor for code symbols
    assert plan.strategy_weight_adjustments.get("fulltext") == 1.5
    assert plan.strategy_weight_adjustments.get("anchor") == 1.5
    assert plan.strategy_weight_adjustments.get("vector") == 0.7
    assert len(plan.refined_queries) > 0
    assert "HybridSearchEngine" in plan.refined_queries[0]


def test_query_rewriter_missing_semantic_aspect():
    rewriter = QueryRewriter(default_boost=1.4)
    assessment = SufficiencyAssessment(
        decision=GateDecision.INSUFFICIENT,
        composite_score=0.5,
        relevance_component=0.5,
        coverage_component=0.4,
        diversity_component=0.5,
        trust_component=1.0,
        temporal_component=1.0,
        conflict_penalty=0.0,
        missing_aspects=["architecture overview", "rationale"],
        rationale="Missing semantic context",
    )

    plan = rewriter.create_rewrite_plan(
        query="explain system design", assessment=assessment
    )

    assert plan.strategy_weight_adjustments.get("vector") == 1.4
    assert plan.strategy_weight_adjustments.get("graph") == 1.4
    assert plan.strategy_weight_adjustments.get("fulltext") == 0.8


def test_query_rewriter_no_assessment():
    rewriter = QueryRewriter()
    plan = rewriter.create_rewrite_plan(query="clean search")
    assert plan.missing_aspects == []
    assert plan.refined_queries == ["clean search"]


# ==============================================================================
# ADAPTIVE ENGINE TESTS
# ==============================================================================


class MockSearchStrategy(SearchStrategy):
    def __init__(self, name: str, candidate_sequences: list[list]):
        self.name = name
        self.candidate_sequences = candidate_sequences
        self.call_count = 0

    async def search(self, *args, **kwargs):
        idx = min(self.call_count, len(self.candidate_sequences) - 1)
        res = self.candidate_sequences[idx]
        self.call_count += 1
        return res

    def get_strategy_name(self) -> str:
        return self.name

    def get_strategy_weight(self) -> float:
        return 1.0


@pytest.mark.asyncio
async def test_adaptive_engine_single_pass_when_disabled():
    uid1 = uuid4()
    strat = MockSearchStrategy("vector", [[(uid1, 0.5, 0.5)]])
    strategies = {"vector": strat}

    mock_storage = AsyncMock()
    mock_storage.get_memories_batch.return_value = [
        {"id": uid1, "content": "Memory 1", "importance": 0.8}
    ]

    engine = AdaptiveSearchEngine(
        strategies=strategies,
        memory_storage=mock_storage,
    )

    package = await engine.search_adaptive_evidence(
        query="test query",
        tenant_id="tenant-1",
        force_2pass=False,
    )

    assert isinstance(package, EvidencePackage)
    assert package.metadata.get("pass_count") == 1
    assert strat.call_count == 1


@pytest.mark.asyncio
async def test_adaptive_engine_2pass_execution_and_fusion():
    uid1 = uuid4()
    uid2 = uuid4()

    # Pass 1 returns uid1 with low relevance; Pass 2 returns uid2 with high relevance
    strat = MockSearchStrategy(
        "vector",
        [
            [(uid1, 0.4, 0.5)],
            [(uid2, 0.95, 0.9)],
        ],
    )
    strategies = {"vector": strat}

    mock_storage = AsyncMock()

    def get_memories_batch_side_effect(ids, tenant_id):
        result = []
        for mid in ids:
            if mid == uid1:
                result.append(
                    {"id": uid1, "content": "Initial partial match", "importance": 0.5}
                )
            elif mid == uid2:
                result.append(
                    {"id": uid2, "content": "Exact relevant match", "importance": 0.95}
                )
        return result

    mock_storage.get_memories_batch.side_effect = get_memories_batch_side_effect

    engine = AdaptiveSearchEngine(
        strategies=strategies,
        memory_storage=mock_storage,
    )

    package = await engine.search_adaptive_evidence(
        query="missing information query",
        tenant_id="tenant-1",
        force_2pass=True,
    )

    assert isinstance(package, EvidencePackage)
    assert package.metadata.get("pass_count") == 2
    assert "rewrite_plan" in package.metadata
    assert strat.call_count == 2

    # Verify results fusion: both items should be present
    item_ids = [item.memory_id for item in package.items]
    assert uid1 in item_ids
    assert uid2 in item_ids


@pytest.mark.asyncio
async def test_adaptive_engine_hard_max_passes_cap():
    engine = AdaptiveSearchEngine(
        strategies={},
        max_passes=5,  # Attempts to configure 5 passes
    )
    assert engine.max_passes == 2  # Hard limit capped at 2


@pytest.mark.asyncio
async def test_adaptive_engine_boost_and_focus_filters():
    from unittest.mock import MagicMock

    uid_shared = uuid4()
    uid_other = uuid4()
    strat = MockSearchStrategy(
        "vector",
        [
            [(uid_shared, 0.3, 0.3), (uid_other, 0.9, 0.9)],
            [(uid_shared, 0.5, 0.5)],
        ],
    )
    strategies = {"vector": strat}
    mock_storage = AsyncMock()

    def get_memories(ids, tenant_id):
        res = []
        for i in ids:
            if i == uid_shared:
                res.append(
                    {"id": uid_shared, "content": "Shared content", "importance": 0.5}
                )
            elif i == uid_other:
                res.append(
                    {"id": uid_other, "content": "Other content", "importance": 0.9}
                )
        return res

    mock_storage.get_memories_batch.side_effect = get_memories

    mock_rewriter = MagicMock(spec=QueryRewriter)
    mock_rewriter.create_rewrite_plan.return_value = RewritePlan(
        original_query="test",
        refined_queries=["refined test"],
        strategy_weight_adjustments={"vector": 1.2},
        focus_filters={"layer": "semantic"},
    )

    mock_gate = MagicMock(spec=EvidenceSufficiencyGate)
    mock_gate.evaluate.return_value = SufficiencyAssessment(
        decision=GateDecision.INSUFFICIENT,
        composite_score=0.3,
        relevance_component=0.3,
        coverage_component=0.2,
        diversity_component=0.3,
        trust_component=0.5,
        temporal_component=0.5,
        conflict_penalty=0.0,
        missing_aspects=["semantic"],
        rationale="Insufficient evidence",
    )

    engine = AdaptiveSearchEngine(
        strategies=strategies,
        memory_storage=mock_storage,
        rewriter=mock_rewriter,
        sufficiency_gate=mock_gate,
    )

    package = await engine.search_adaptive_evidence(
        query="test",
        tenant_id="tenant-1",
        filters={"project": "proj-a"},
        force_2pass=True,
    )

    assert package.metadata.get("pass_count") == 2
    assert len(package.items) == 2
    shared_item = next(it for it in package.items if it.memory_id == uid_shared)
    assert shared_item.relevance_score > 0.0
