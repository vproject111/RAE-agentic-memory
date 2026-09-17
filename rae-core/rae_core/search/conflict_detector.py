"""Deterministic conflict detector for retrieved evidence items (<1ms)."""

from __future__ import annotations

import re
from typing import Sequence
from uuid import uuid4

import structlog

from rae_core.models.evidence_package import EvidenceConflict, EvidenceItem

logger = structlog.get_logger(__name__)

DEPRECATION_PATTERN = re.compile(
    r"\b(deprecated|usunięto|zastąpiono przez|obsolete|legacy|nie używać|do not use|superseded)\b",
    re.IGNORECASE,
)
ACTIVE_PATTERN = re.compile(
    r"\b(active|standard|aktualne|włączone|enabled|recommended|single source of truth)\b",
    re.IGNORECASE,
)
BOOLEAN_TRUE_PATTERN = re.compile(
    r"\b(enabled\s*[:=]\s*true|flag\s*=\s*true)\b", re.IGNORECASE
)
BOOLEAN_FALSE_PATTERN = re.compile(
    r"\b(enabled\s*[:=]\s*false|flag\s*=\s*false)\b", re.IGNORECASE
)


class EvidenceConflictDetector:
    """
    Deterministic rules-first conflict detector.
    Analyzes pairs of EvidenceItems to identify contradictions, temporal drift,
    and version/status mismatches without external LLM calls.
    """

    def detect_conflicts(self, items: Sequence[EvidenceItem]) -> list[EvidenceConflict]:
        """Detect pairwise conflicts across retrieved evidence items."""
        if len(items) < 2:
            return []

        conflicts: list[EvidenceConflict] = []

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_a = items[i]
                item_b = items[j]

                conflict = self._check_pair(item_a, item_b)
                if conflict:
                    conflicts.append(conflict)

        if conflicts:
            logger.info("evidence_conflicts_detected", count=len(conflicts))

        return conflicts

    def _check_pair(
        self, item_a: EvidenceItem, item_b: EvidenceItem
    ) -> EvidenceConflict | None:
        content_a = item_a.content.lower()
        content_b = item_b.content.lower()

        # 1. Check boolean config flag contradiction
        has_true_a = bool(BOOLEAN_TRUE_PATTERN.search(content_a))
        has_false_a = bool(BOOLEAN_FALSE_PATTERN.search(content_a))
        has_true_b = bool(BOOLEAN_TRUE_PATTERN.search(content_b))
        has_false_b = bool(BOOLEAN_FALSE_PATTERN.search(content_b))

        if (has_true_a and has_false_b) or (has_false_a and has_true_b):
            return EvidenceConflict(
                conflict_id=uuid4(),
                conflict_type="version_mismatch",
                item_a_id=item_a.evidence_id,
                item_b_id=item_b.evidence_id,
                description="Contradictory configuration boolean values detected between evidence items.",
            )

        # 2. Check active vs deprecated status contradiction
        is_depr_a = bool(DEPRECATION_PATTERN.search(content_a))
        is_active_a = bool(ACTIVE_PATTERN.search(content_a))
        is_depr_b = bool(DEPRECATION_PATTERN.search(content_b))
        is_active_b = bool(ACTIVE_PATTERN.search(content_b))

        if (is_depr_a and is_active_b) or (is_active_a and is_depr_b):
            same_source = False
            file_ref = ""
            if (
                item_a.envelope
                and item_b.envelope
                and item_a.envelope.attribution
                and item_b.envelope.attribution
                and item_a.envelope.attribution.file_path
                and item_a.envelope.attribution.file_path
                == item_b.envelope.attribution.file_path
            ):
                same_source = True
                file_ref = f" for {item_a.envelope.attribution.file_path}"

            return EvidenceConflict(
                conflict_id=uuid4(),
                conflict_type="temporal_drift" if same_source else "version_mismatch",
                item_a_id=item_a.evidence_id,
                item_b_id=item_b.evidence_id,
                description=(
                    f"Status discrepancy: one item indicates deprecated/obsolete while the other "
                    f"indicates active/standard{file_ref}."
                ),
            )

        # 3. Check temporal drift across same file with >60 days gap and different content
        if (
            item_a.envelope
            and item_b.envelope
            and item_a.envelope.attribution
            and item_b.envelope.attribution
            and item_a.envelope.attribution.file_path
            and item_a.envelope.attribution.file_path
            == item_b.envelope.attribution.file_path
            and item_a.observed_at
            and item_b.observed_at
        ):
            delta_days = abs((item_a.observed_at - item_b.observed_at).days)
            if delta_days > 60 and item_a.checksum_sha256 != item_b.checksum_sha256:
                return EvidenceConflict(
                    conflict_id=uuid4(),
                    conflict_type="temporal_drift",
                    item_a_id=item_a.evidence_id,
                    item_b_id=item_b.evidence_id,
                    description=(
                        f"Temporal drift of {delta_days} days detected for source "
                        f"'{item_a.envelope.attribution.file_path}' with different contents."
                    ),
                )

        return None
