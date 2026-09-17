"""Unit tests for EvidencePackage and search_evidence method (Iteration 2)."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from rae_core.models.envelope import CodeAttribution, ContextEnvelope
from rae_core.models.evidence_package import (
    EvidenceConflict,
    EvidenceItem,
    EvidencePackage,
)
from rae_core.search.engine import HybridSearchEngine
from rae_core.search.strategies import SearchStrategy

# ==============================================================================
# SCHEMA INTEGRITY TESTS
# ==============================================================================


def test_evidence_item_creation():
    uid = uuid4()
    content = "class HybridSearchEngine: pass"
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    item = EvidenceItem.from_memory_and_score(
        memory_id=uid,
        content=content,
        score=0.85,
        strategy="vector",
    )

    assert item.memory_id == uid
    assert item.content == content
    assert item.relevance_score == 0.85
    assert item.checksum_sha256 == expected_hash
    assert item.strategy_source == "vector"

    # Forbid extra fields
    with pytest.raises(ValidationError):
        EvidenceItem(
            memory_id=uid,
            content=content,
            relevance_score=0.5,
            illegal_field="bad",  # type: ignore[call-arg]
        )


def test_evidence_conflict_creation():
    id_a = uuid4()
    id_b = uuid4()

    conflict = EvidenceConflict(
        conflict_type="version_mismatch",
        item_a_id=id_a,
        item_b_id=id_b,
        description="Source A specifies timeout=5 while Source B specifies timeout=10",
    )
    assert conflict.item_a_id == id_a
    assert conflict.conflict_type == "version_mismatch"


def test_evidence_package_model():
    package = EvidencePackage(
        query="test query",
        tenant_id="tenant-123",
        strategies_used=["vector", "fulltext"],
        confidence_score=0.92,
    )
    assert package.query == "test query"
    assert package.tenant_id == "tenant-123"
    assert package.confidence_score == 0.92
    assert len(package.items) == 0


# ==============================================================================
# SEARCH_EVIDENCE INTEGRATION TESTS
# ==============================================================================


class MockStrategy(SearchStrategy):
    def __init__(self, name: str, return_candidates: list):
        self.name = name
        self.return_candidates = return_candidates

    async def search(self, *args, **kwargs):
        return self.return_candidates

    def get_strategy_name(self) -> str:
        return self.name

    def get_strategy_weight(self) -> float:
        return 1.0


@pytest.mark.asyncio
async def test_search_evidence_parity_and_assembly():
    uid1 = uuid4()
    uid2 = uuid4()

    strat1 = MockStrategy("vector", [(uid1, 0.9, 0.5), (uid2, 0.7, 0.5)])
    strategies: dict[str, SearchStrategy] = {"vector": strat1}

    mock_storage = AsyncMock()
    mock_storage.get_memories_batch.return_value = [
        {
            "id": uid1,
            "content": "First memory content",
            "importance": 0.9,
            "envelope": ContextEnvelope(
                source_type="code",
                project="rae_suite",
                attribution=CodeAttribution(
                    repository="RAE-Suite",
                    file_path="engine.py",
                    class_name="HybridSearchEngine",
                ),
            ),
        },
        {
            "id": uid2,
            "content": "Second memory content",
            "importance": 0.8,
            "envelope": None,
        },
    ]

    engine = HybridSearchEngine(
        strategies=strategies,
        memory_storage=mock_storage,
    )

    package = await engine.search_evidence(
        query="search test",
        tenant_id="tenant-abc",
        limit=10,
    )

    assert isinstance(package, EvidencePackage)
    assert package.query == "search test"
    assert package.tenant_id == "tenant-abc"
    assert len(package.items) == 2

    item1 = package.items[0]
    assert item1.memory_id == uid1
    assert item1.content == "First memory content"
    assert item1.envelope is not None
    assert item1.envelope.attribution is not None
    assert item1.envelope.attribution.class_name == "HybridSearchEngine"

    item2 = package.items[1]
    assert item2.memory_id == uid2
    assert item2.content == "Second memory content"
    assert item2.envelope is None

    # Confidence score is average of item scores
    assert package.confidence_score > 0.0


@pytest.mark.asyncio
async def test_search_evidence_empty():
    strat_empty = MockStrategy("vector", [])
    strategies: dict[str, SearchStrategy] = {"vector": strat_empty}
    engine = HybridSearchEngine(strategies=strategies)

    package = await engine.search_evidence(
        query="empty query",
        tenant_id="tenant-xyz",
    )

    assert isinstance(package, EvidencePackage)
    assert len(package.items) == 0
    assert package.confidence_score == 0.0
