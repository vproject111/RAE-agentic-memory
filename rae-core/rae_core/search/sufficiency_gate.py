"""Evidence sufficiency gate for evaluating retrieval completeness and confidence."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from enum import StrEnum

import structlog
from pydantic import BaseModel, ConfigDict, Field

from rae_core.models.evidence_package import EvidencePackage

logger = structlog.get_logger(__name__)


class GateDecision(StrEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    AMBIGUOUS = "ambiguous"


class SufficiencyAssessment(BaseModel):
    """Evaluation result from EvidenceSufficiencyGate."""

    model_config = ConfigDict(extra="forbid")

    decision: GateDecision = Field(
        description="Sufficiency verdict: sufficient | insufficient | ambiguous"
    )
    composite_score: float = Field(
        ge=0.0, le=1.0, description="Overall weighted confidence score [0.0, 1.0]"
    )
    relevance_component: float = Field(ge=0.0, le=1.0)
    coverage_component: float = Field(ge=0.0, le=1.0)
    diversity_component: float = Field(ge=0.0, le=1.0)
    trust_component: float = Field(ge=0.0, le=1.0)
    temporal_component: float = Field(ge=0.0, le=1.0)
    conflict_penalty: float = Field(ge=0.0, le=1.0)
    missing_aspects: list[str] = Field(default_factory=list)
    rationale: str = Field(description="Explanation of sufficiency gate verdict")


class EvidenceSufficiencyGate:
    """
    Evaluates whether an EvidencePackage contains sufficient, consistent,
    and reliable material for downstream agent decision-making.
    """

    def __init__(
        self,
        threshold: float = 0.68,
        mode: str | None = None,
    ):
        """
        Initialize the gate.

        Args:
            threshold: Minimum composite score required for SUFFICIENT verdict.
            mode: 'shadow' | 'active' | 'disabled'. If None, reads RAE_EVIDENCE_GATE_MODE env var.
        """
        self.threshold = threshold
        self._mode = mode

    @property
    def mode(self) -> str:
        if self._mode:
            return self._mode.lower()
        return os.getenv("RAE_EVIDENCE_GATE_MODE", "shadow").lower()

    def evaluate(self, package: EvidencePackage) -> SufficiencyAssessment:
        """
        Evaluate an EvidencePackage deterministically without invoking external LLMs.
        Runtime SLA < 2ms.
        """
        if not package.items:
            assessment = SufficiencyAssessment(
                decision=GateDecision.INSUFFICIENT,
                composite_score=0.0,
                relevance_component=0.0,
                coverage_component=0.0,
                diversity_component=0.0,
                trust_component=0.0,
                temporal_component=0.0,
                conflict_penalty=0.0,
                missing_aspects=["No evidence retrieved"],
                rationale="Empty evidence package. Retrieval yielded 0 candidates.",
            )
            self._log_telemetry(package, assessment)
            return assessment

        # 1. Relevance component (top 3 average)
        top_scores = [item.relevance_score for item in package.items[:3]]
        r_rel = float(sum(top_scores) / len(top_scores)) if top_scores else 0.0

        # 2. Coverage component (query token presence in retrieved text)
        q_tokens = set(re_clean(package.query).lower().split())
        all_text = " ".join(item.content.lower() for item in package.items)
        if q_tokens:
            matched_tokens = sum(1 for t in q_tokens if t in all_text)
            c_cov = min(1.0, float(matched_tokens) / float(len(q_tokens)))
        else:
            c_cov = 1.0

        missing_aspects: list[str] = []
        if q_tokens:
            for t in q_tokens:
                if len(t) > 3 and t not in all_text:
                    missing_aspects.append(t)

        # 3. Source diversity component (distinct file paths or distinct items)
        distinct_sources = set()
        for item in package.items:
            if (
                item.envelope
                and item.envelope.attribution
                and item.envelope.attribution.file_path
            ):
                distinct_sources.add(item.envelope.attribution.file_path)
            else:
                distinct_sources.add(str(item.memory_id))
        d_div = min(
            1.0, float(len(distinct_sources)) / min(3.0, float(len(package.items)))
        )

        # 4. Trust component (average trust_score)
        t_trust = float(
            sum(item.trust_score for item in package.items) / len(package.items)
        )

        # 5. Temporal consistency component
        now = datetime.now(timezone.utc)
        temporal_scores = []
        for item in package.items:
            age_days = (now - item.observed_at).days
            temp_s = 1.0 / (1.0 + max(0.0, float(age_days)) / 30.0)
            temporal_scores.append(temp_s)
        k_temp = float(sum(temporal_scores) / len(temporal_scores))

        # 6. Conflict penalty
        conflict_penalty = min(0.5, 0.25 * float(len(package.conflicts)))

        # 7. Composite score calculation (Pillar weights)
        raw_score = (
            0.30 * r_rel
            + 0.25 * c_cov
            + 0.15 * d_div
            + 0.15 * t_trust
            + 0.15 * k_temp
            - conflict_penalty
        )
        composite_score = max(0.0, min(1.0, raw_score))

        # Verdict
        if composite_score >= self.threshold:
            decision = GateDecision.SUFFICIENT
            rationale = (
                f"Evidence package is sufficient (score={composite_score:.3f} >= threshold={self.threshold:.2f}). "
                f"Rel={r_rel:.2f}, Cov={c_cov:.2f}, Div={d_div:.2f}."
            )
        elif composite_score >= (self.threshold - 0.15):
            decision = GateDecision.AMBIGUOUS
            rationale = (
                f"Evidence package is ambiguous (score={composite_score:.3f} near threshold={self.threshold:.2f}). "
                f"Missing terms: {missing_aspects[:3]}."
            )
        else:
            decision = GateDecision.INSUFFICIENT
            rationale = (
                f"Evidence package is insufficient (score={composite_score:.3f} < threshold={self.threshold:.2f}). "
                f"Rel={r_rel:.2f}, Cov={c_cov:.2f}. Missing aspects: {missing_aspects[:3]}."
            )

        assessment = SufficiencyAssessment(
            decision=decision,
            composite_score=composite_score,
            relevance_component=r_rel,
            coverage_component=c_cov,
            diversity_component=d_div,
            trust_component=t_trust,
            temporal_component=k_temp,
            conflict_penalty=conflict_penalty,
            missing_aspects=missing_aspects[:5],
            rationale=rationale,
        )

        self._log_telemetry(package, assessment)
        return assessment

    def _log_telemetry(
        self, package: EvidencePackage, assessment: SufficiencyAssessment
    ) -> None:
        """Log structured telemetry without side-effects."""
        logger.info(
            "evidence_sufficiency_gate_evaluated",
            package_id=str(package.package_id),
            decision=assessment.decision.value,
            composite_score=round(assessment.composite_score, 4),
            gate_mode=self.mode,
            items_count=len(package.items),
        )


def re_clean(text: str) -> str:
    """Helper to clean text for token matching."""
    import re

    return re.sub(r"[^\w\s]", " ", text)
