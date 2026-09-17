"""End-to-end closed-loop integration test for RAE-Suite Adaptive Retrieval (Iteration 10)."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_core.evaluation.golden_queries import QueryCategory
from rae_core.ingestion.context_enricher import ContextEnricher
from rae_core.math.policy import compute_retrieval_reward
from rae_core.models.envelope import CodeAttribution, ContextEnvelope
from rae_core.models.evidence_package import EvidencePackage
from rae_core.models.memory import MemoryItem
from rae_core.search.adaptive_engine import AdaptiveSearchEngine
from rae_core.search.classifier import QueryClassifier
from rae_core.search.router import StrategyRouter
from rae_core.search.strategies import SearchStrategy
from rae_core.types.enums import MemoryLayer, MemoryType


class MockRetrievalStrategy(SearchStrategy):
    def __init__(self, name: str, items_by_pass: list[list]):
        self.name = name
        self.items_by_pass = items_by_pass
        self.call_count = 0

    async def search(self, *args, **kwargs):
        idx = min(self.call_count, len(self.items_by_pass) - 1)
        res = self.items_by_pass[idx]
        self.call_count += 1
        return res

    def get_strategy_name(self) -> str:
        return self.name

    def get_strategy_weight(self) -> float:
        return 1.0


@pytest.mark.asyncio
async def test_full_closed_loop_retrieval_pipeline():
    # =========================================================================
    # STEP 1: CONTEXTUAL INGESTION (Iteration 1)
    # =========================================================================
    import textwrap

    code_content = textwrap.dedent("""
    class AdaptiveSearchEngine(HybridSearchEngine):
        def search_adaptive_evidence(self, query: str):
            pass
    """).strip()
    enricher = ContextEnricher()
    cls_name, fn_name, start_l, end_l, doc = enricher.extract_python_symbols(
        code_content
    )
    assert cls_name == "AdaptiveSearchEngine"
    assert fn_name == "search_adaptive_evidence"

    mem_id = uuid4()
    envelope = ContextEnvelope(
        source_type="code",
        project="rae_suite",
        attribution=CodeAttribution(
            repository="RAE-Suite",
            file_path="search/adaptive_engine.py",
            class_name="AdaptiveSearchEngine",
        ),
        scope_tags=["search", "adaptive"],
    )

    memory_item = MemoryItem(
        id=mem_id,
        content=code_content,
        layer=MemoryLayer.SEMANTIC,
        memory_type=MemoryType.CODE,
        tenant_id="tenant-alpha",
        agent_id="coding_agent",
        project="rae_suite",
        envelope=envelope,
    )
    assert memory_item.envelope is not None

    # =========================================================================
    # STEP 2: DETERMINISTIC QUERY CLASSIFICATION & ROUTING (Iteration 5)
    # =========================================================================
    query = "Implementation of AdaptiveSearchEngine class"
    classifier = QueryClassifier()
    classification = classifier.classify(query)
    assert classification.category == QueryCategory.CODE_SYMBOL

    router = StrategyRouter(classifier=classifier)
    routing_plan = router.route(
        query, available_strategies=["fulltext", "vector", "graph"]
    )
    assert "fulltext" in routing_plan.active_strategies
    assert "vector" in routing_plan.active_strategies
    assert routing_plan.strategy_weights["fulltext"] >= 0.50

    # =========================================================================
    # STEP 3: ADAPTIVE 2-PASS SEARCH & EVIDENCE ASSEMBLY (Iterations 2, 3, 4)
    # =========================================================================
    # Pass 1: returns low relevance / incomplete info (triggers Pass 2)
    # Pass 2: returns exact relevant match
    mem_id_pass2 = uuid4()
    strat_fulltext = MockRetrievalStrategy(
        "fulltext",
        [
            [(mem_id, 0.25, 0.2)],
            [(mem_id_pass2, 0.95, 0.9)],
        ],
    )
    strat_vector = MockRetrievalStrategy(
        "vector",
        [
            [(mem_id, 0.20, 0.2)],
            [(mem_id_pass2, 0.90, 0.9)],
        ],
    )

    strategies = {
        "fulltext": strat_fulltext,
        "vector": strat_vector,
    }

    mock_storage = AsyncMock()

    def get_batch(ids, tenant_id):
        res = []
        for i in ids:
            if i == mem_id:
                res.append(
                    {
                        "id": mem_id,
                        "content": "Unrelated log buffer item",
                        "envelope": None,
                        "importance": 0.2,
                    }
                )
            elif i == mem_id_pass2:
                res.append(
                    {
                        "id": mem_id_pass2,
                        "content": "Exact implementation of AdaptiveSearchEngine class with max_passes=2",
                        "envelope": envelope,
                        "importance": 0.95,
                    }
                )
        return res

    mock_storage.get_memories_batch.side_effect = get_batch

    engine = AdaptiveSearchEngine(
        strategies=strategies,
        memory_storage=mock_storage,
        router=router,
    )

    package: EvidencePackage = await engine.search_adaptive_evidence(
        query=query,
        tenant_id="tenant-alpha",
        force_2pass=True,
    )

    assert isinstance(package, EvidencePackage)
    assert package.metadata.get("pass_count") == 2
    assert len(package.items) >= 2

    # Verify SHA-256 checksum integrity on evidence items (ISO 42001)
    for item in package.items:
        expected_sha = hashlib.sha256(item.content.encode("utf-8")).hexdigest()
        assert item.checksum_sha256 == expected_sha

    # =========================================================================
    # STEP 4: MULTI-OBJECTIVE REWARD & OPTIMIZATION (Iteration 9)
    # =========================================================================
    latency_ms = 110.0
    quality = package.confidence_score
    reward = compute_retrieval_reward(
        quality=quality,
        latency_ms=latency_ms,
        token_cost=0.01,
        is_failed=False,
    )
    assert reward > 0.35

    # =========================================================================
    # STEP 5: ISO 42001 / ISO 27001 AUDIT RECEIPT SIGNING
    # =========================================================================
    audit_payload = {
        "package_id": str(package.package_id),
        "query": package.query,
        "items_count": len(package.items),
        "confidence_score": package.confidence_score,
        "reward": reward,
    }
    audit_receipt = hashlib.sha256(
        json.dumps(audit_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert len(audit_receipt) == 64
    target_item = next(item for item in package.items if item.memory_id == mem_id_pass2)
    assert target_item.envelope is not None
    assert target_item.envelope.attribution is not None
    assert target_item.envelope.attribution.class_name == "AdaptiveSearchEngine"
