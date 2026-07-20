from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import uuid4

from rae_core.governance.context import Clock, ResolutionContext, SystemClock
from rae_core.models.evidence import (
    ConflictSeverity,
    ConflictType,
    EvidenceBundle,
    EvidenceItem,
    KnowledgeConflict,
    ResolutionStatus,
)
from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType
from rae_core.governance.adapter_broker import AdapterBroker
from rae_core.interfaces.adapter import RetrievalContext
from rae_core.governance.hashing import calculate_audit_hash, calculate_content_hash

logger = logging.getLogger(__name__)

AUTHORITY_WEIGHT = {
    "canonical": 1.00,
    "approved": 0.85,
    "observed": 0.60,
    "inferred": 0.35,
    "untrusted": 0.05,
}


class KnowledgeResolutionEngine(ABC):
    @abstractmethod
    async def resolve(
        self,
        query: str,
        *,
        context: ResolutionContext,
        previous_audit_hash: str | None = None,
    ) -> EvidenceBundle:
        raise NotImplementedError


class DefaultKnowledgeResolutionEngine(KnowledgeResolutionEngine):
    def __init__(self, broker: AdapterBroker, clock: Clock | None = None) -> None:
        self.broker = broker
        self.clock = clock or SystemClock()

    async def resolve(
        self,
        query: str,
        *,
        context: ResolutionContext,
        previous_audit_hash: str | None = None,
    ) -> EvidenceBundle:
        if not query.strip():
            raise ValueError("Zapytanie nie może być puste")

        # 1. RETRIEVE CANDIDATES FROM ADAPTERS
        retrieval_ctx = RetrievalContext(
            tenant_id=context.tenant_id,
            request_id=context.request_id,
            actor_id=context.actor_id,
            scope=context.scope,
            timeout_seconds=5.0,
            allow_network=True,
        )

        candidates = await self.broker.retrieve(query, context=retrieval_ctx)

        # 2. MAP CANDIDATES TO EVIDENCE ITEMS
        evidence_items: list[EvidenceItem] = []
        now = self.clock.now()

        for candidate in candidates:
            # Calculate freshness based on observed age
            age_seconds = max(0.0, (now - candidate.observed_at).total_seconds())
            # Half-life of 30 days (2,592,000 seconds) for exponential decay
            freshness = round(0.5 ** (age_seconds / 2592000.0), 6)

            # Check if scope matches context scope
            scope_match = 1.0
            if context.scope:
                item_scope = candidate.metadata.get("scope", [])
                if item_scope:
                    matches = set(item_scope).intersection(set(context.scope))
                    scope_match = round(len(matches) / len(item_scope), 6)
                else:
                    scope_match = 0.0

            # Relevance defaults to candidate score
            relevance = round(candidate.score, 6)

            evidence_items.append(
                EvidenceItem(
                    evidence_id=candidate.evidence_id,
                    knowledge_id=candidate.knowledge_id,
                    source_ref=candidate.source_ref,
                    source_type=candidate.source_type,
                    authority_level=candidate.authority_level,
                    relevance=relevance,
                    freshness=freshness,
                    scope_match=scope_match,
                    checksum=candidate.checksum,
                    observed_at=candidate.observed_at,
                    content_excerpt=candidate.content[:200] if candidate.content else None,
                    metadata=candidate.metadata,
                )
            )

        # 3. CONFLICT DETECTION
        conflicts: list[KnowledgeConflict] = []
        resolved_evidence: list[EvidenceItem] = []
        resolution_status = ResolutionStatus.RESOLVED

        # Group items by source reference or knowledge id
        by_key: dict[str, list[EvidenceItem]] = {}
        for item in evidence_items:
            key = item.knowledge_id if (item.knowledge_id is not None and item.knowledge_id.strip() != "") else item.source_ref
            by_key.setdefault(key, []).append(item)

        for key, items in by_key.items():
            if len(items) <= 1:
                resolved_evidence.extend(items)
                continue

            # Verify if checksums are identical
            first_checksum = items[0].checksum
            if all(item.checksum == first_checksum for item in items):
                # No conflict, just duplicate entries
                resolved_evidence.append(items[0])
                continue

            # Checksums differ! We have a conflict!
            # Sort items by authority weight descending, then by observed_at descending
            sorted_items = sorted(
                items,
                key=lambda x: (
                    AUTHORITY_WEIGHT.get(x.authority_level.value, 0.05),
                    x.observed_at,
                ),
                reverse=True,
            )

            winner = sorted_items[0]
            loser = sorted_items[1]

            conflict = KnowledgeConflict(
                conflict_id=str(uuid4()),
                subject=key,
                source_a=winner.source_ref,
                source_b=loser.source_ref,
                conflict_type=ConflictType.VERSION,
                severity=ConflictSeverity.WARNING,
                preferred_source=winner.source_ref,
                resolution_rule="higher_authority_then_newer_timestamp",
                rationale=f"Winner has authority {winner.authority_level} and date {winner.observed_at} versus loser authority {loser.authority_level} and date {loser.observed_at}.",
            )
            conflicts.append(conflict)
            resolved_evidence.append(winner)
            resolution_status = ResolutionStatus.RESOLVED_WITH_WARNING

        # 4. CONSTRUCT EVIDENCE BUNDLE
        avg_relevance = sum(item.relevance for item in resolved_evidence) / len(resolved_evidence) if resolved_evidence else 1.0
        confidence = round(avg_relevance, 6)

        bundle = EvidenceBundle(
            bundle_id=uuid4(),
            tenant_id=context.tenant_id,
            request_id=context.request_id,
            query=query,
            generated_at=now,
            policy_version=context.policy_version,
            evidence=resolved_evidence,
            conflicts=conflicts,
            confidence=confidence,
            resolution_status=resolution_status,
        )

        # 5. GENERATE HASHES
        bundle.content_hash = calculate_content_hash(bundle)
        bundle.audit_hash = calculate_audit_hash(bundle, previous_audit_hash=previous_audit_hash)

        return bundle
