"""Unit tests for EvidenceConflictDetector (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.models.envelope import CodeAttribution, ContextEnvelope
from rae_core.models.evidence_package import EvidenceItem
from rae_core.search.conflict_detector import EvidenceConflictDetector
from rae_core.search.engine import HybridSearchEngine
from rae_core.search.strategies import SearchStrategy


def test_conflict_detector_empty_and_single_item():
    detector = EvidenceConflictDetector()
    assert detector.detect_conflicts([]) == []

    single_item = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="Single memory content",
        score=0.9,
    )
    assert detector.detect_conflicts([single_item]) == []


def test_conflict_detector_boolean_config_mismatch():
    detector = EvidenceConflictDetector()
    item1 = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="Configuration: feature_cache: enabled = true",
        score=0.9,
    )
    item2 = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="System settings: feature_cache: enabled = false",
        score=0.85,
    )

    conflicts = detector.detect_conflicts([item1, item2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "version_mismatch"
    assert "Contradictory configuration boolean values" in conflicts[0].description


def test_conflict_detector_deprecation_status_conflict():
    detector = EvidenceConflictDetector()
    attr1 = CodeAttribution(
        repository="rae-agentic-memory", file_path="services/auth.py"
    )
    attr2 = CodeAttribution(
        repository="rae-agentic-memory", file_path="services/auth.py"
    )

    item1 = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="This auth module is deprecated and obsolete. Do not use.",
        score=0.9,
        envelope=ContextEnvelope(project="rae_suite", attribution=attr1),
    )
    item2 = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="This auth module is active and is the single source of truth standard.",
        score=0.88,
        envelope=ContextEnvelope(project="rae_suite", attribution=attr2),
    )

    conflicts = detector.detect_conflicts([item1, item2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "temporal_drift"
    assert "Status discrepancy" in conflicts[0].description


def test_conflict_detector_temporal_drift_detection():
    detector = EvidenceConflictDetector()
    attr = CodeAttribution(
        repository="rae-agentic-memory", file_path="models/contract.py"
    )
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=90)

    item1 = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="Contract version 1.0 specifications",
        score=0.9,
        envelope=ContextEnvelope(project="rae_suite", attribution=attr),
    )
    item1.observed_at = old_time

    item2 = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="Contract version 2.0 restructured architecture",
        score=0.9,
        envelope=ContextEnvelope(project="rae_suite", attribution=attr),
    )
    item2.observed_at = now

    conflicts = detector.detect_conflicts([item1, item2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "temporal_drift"
    assert "Temporal drift of" in conflicts[0].description


@pytest.mark.asyncio
async def test_search_evidence_integrates_conflict_detector():
    uid1 = uuid4()
    uid2 = uuid4()
    mock_strat = MagicMock(spec=SearchStrategy)
    mock_strat.search = AsyncMock(return_value=[(uid1, 0.9, 0.0), (uid2, 0.8, 0.0)])
    mock_strat.get_strategy_weight.return_value = 0.5
    mock_strat.get_strategy_name.return_value = "vector"

    mock_storage = AsyncMock()
    mock_storage.get_memories_batch.return_value = [
        {
            "id": uid1,
            "content": "cache_mode: enabled = true",
            "importance": 0.9,
        },
        {
            "id": uid2,
            "content": "cache_mode: enabled = false",
            "importance": 0.9,
        },
    ]

    engine = HybridSearchEngine(
        strategies={"vector": mock_strat},
        memory_storage=mock_storage,
    )

    package = await engine.search_evidence(
        query="cache configuration",
        tenant_id="tenant-1",
    )

    assert len(package.conflicts) == 1
    assert package.conflicts[0].conflict_type == "version_mismatch"
    assert "sufficiency_assessment" in package.metadata
    assessment = package.metadata["sufficiency_assessment"]
    assert assessment["conflict_penalty"] > 0.0
