"""Unit tests for EvidenceSufficiencyGate (Iteration 3)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from rae_core.models.envelope import CodeAttribution, ContextEnvelope
from rae_core.models.evidence_package import (
    EvidenceConflict,
    EvidenceItem,
    EvidencePackage,
)
from rae_core.search.sufficiency_gate import (
    EvidenceSufficiencyGate,
    GateDecision,
    SufficiencyAssessment,
)

# ==============================================================================
# SCHEMA INTEGRITY TESTS
# ==============================================================================


def test_sufficiency_assessment_schema():
    assessment = SufficiencyAssessment(
        decision=GateDecision.SUFFICIENT,
        composite_score=0.85,
        relevance_component=0.9,
        coverage_component=0.8,
        diversity_component=0.7,
        trust_component=1.0,
        temporal_component=0.9,
        conflict_penalty=0.0,
        missing_aspects=[],
        rationale="All requirements satisfied",
    )
    assert assessment.decision == GateDecision.SUFFICIENT
    assert assessment.composite_score == 0.85

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        SufficiencyAssessment(
            decision=GateDecision.SUFFICIENT,
            composite_score=0.85,
            relevance_component=0.9,
            coverage_component=0.8,
            diversity_component=0.7,
            trust_component=1.0,
            temporal_component=0.9,
            conflict_penalty=0.0,
            rationale="error",
            illegal_key="fail",  # type: ignore[call-arg]
        )


# ==============================================================================
# GATE EVALUATION TESTS
# ==============================================================================


def test_gate_empty_package():
    gate = EvidenceSufficiencyGate()
    pkg = EvidencePackage(query="where is engine?", tenant_id="t1")

    assessment = gate.evaluate(pkg)
    assert assessment.decision == GateDecision.INSUFFICIENT
    assert assessment.composite_score == 0.0
    assert len(assessment.missing_aspects) > 0


def test_gate_high_relevance_sufficient():
    gate = EvidenceSufficiencyGate(threshold=0.68)
    items = [
        EvidenceItem.from_memory_and_score(
            memory_id=uuid4(),
            content="class HybridSearchEngine implements hybrid retrieval for queries",
            score=0.95,
            trust_score=1.0,
            envelope=ContextEnvelope(
                source_type="code",
                project="rae",
                attribution=CodeAttribution(
                    repository="RAE-Suite",
                    file_path="engine.py",
                    class_name="HybridSearchEngine",
                ),
            ),
        ),
        EvidenceItem.from_memory_and_score(
            memory_id=uuid4(),
            content="HybridSearchEngine combines vector and fulltext strategies",
            score=0.90,
            trust_score=1.0,
            envelope=ContextEnvelope(
                source_type="code",
                project="rae",
                attribution=CodeAttribution(
                    repository="RAE-Suite",
                    file_path="service.py",
                    class_name="RAECoreService",
                ),
            ),
        ),
    ]

    pkg = EvidencePackage(
        query="HybridSearchEngine hybrid retrieval",
        tenant_id="t1",
        items=items,
    )

    assessment = gate.evaluate(pkg)
    assert assessment.decision == GateDecision.SUFFICIENT
    assert assessment.composite_score >= 0.68
    assert assessment.conflict_penalty == 0.0


def test_gate_conflict_penalty():
    gate = EvidenceSufficiencyGate(threshold=0.68)
    id1 = uuid4()
    id2 = uuid4()

    items = [
        EvidenceItem.from_memory_and_score(
            memory_id=id1,
            content="timeout is set to 5 seconds by default",
            score=0.85,
        ),
        EvidenceItem.from_memory_and_score(
            memory_id=id2,
            content="timeout is set to 60 seconds by default",
            score=0.80,
        ),
    ]

    # Package without conflicts
    pkg_clean = EvidencePackage(query="default timeout", tenant_id="t1", items=items)
    assessment_clean = gate.evaluate(pkg_clean)

    # Package with conflict
    pkg_conflict = EvidencePackage(
        query="default timeout",
        tenant_id="t1",
        items=items,
        conflicts=[
            EvidenceConflict(
                conflict_type="factual",
                item_a_id=id1,
                item_b_id=id2,
                description="Contradicting default timeout values (5s vs 60s)",
            )
        ],
    )
    assessment_conflict = gate.evaluate(pkg_conflict)

    assert assessment_conflict.conflict_penalty > 0.0
    assert assessment_conflict.composite_score < assessment_clean.composite_score


def test_gate_ambiguous_decision():
    gate = EvidenceSufficiencyGate(threshold=0.70)
    # Marginal relevance and partial keyword coverage
    items = [
        EvidenceItem.from_memory_and_score(
            memory_id=uuid4(),
            content="some partial text mentioning only one keyword",
            score=0.60,
            trust_score=0.7,
        )
    ]

    pkg = EvidencePackage(
        query="keyword target concept details", tenant_id="t1", items=items
    )
    assessment = gate.evaluate(pkg)

    # Should fall into AMBIGUOUS or INSUFFICIENT
    assert assessment.decision in (GateDecision.AMBIGUOUS, GateDecision.INSUFFICIENT)
    assert assessment.composite_score < 0.70
