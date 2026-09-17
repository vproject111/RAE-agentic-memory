"""EvidencePackage DTO models for unified agentic retrieval in RAE."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from rae_core.models.envelope import ContextEnvelope


class EvidenceItem(BaseModel):
    """An individual piece of retrieved evidence with full provenance."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID = Field(
        default_factory=uuid4, description="Unique evidence instance ID"
    )
    memory_id: UUID = Field(description="Underlying memory ID in storage")
    content: str = Field(description="Exact memory content text")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Normalized relevance score [0.0, 1.0]"
    )
    trust_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Source reliability score"
    )
    strategy_source: str = Field(
        default="hybrid_fused",
        description="Search strategy yielding this evidence: vector | fulltext | graph | hybrid_fused",
    )
    envelope: ContextEnvelope | None = Field(
        default=None,
        description="Contextual envelope with file, class, repo attribution",
    )
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of retrieval",
    )
    checksum_sha256: str | None = Field(
        default=None, description="SHA-256 hash of evidence content"
    )

    @classmethod
    def from_memory_and_score(
        cls,
        memory_id: UUID,
        content: str,
        score: float,
        strategy: str = "hybrid_fused",
        trust_score: float = 1.0,
        envelope: ContextEnvelope | None = None,
    ) -> EvidenceItem:
        """Helper to construct EvidenceItem with automatic checksum computation."""
        c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        normalized_score = max(0.0, min(1.0, float(score)))
        return cls(
            memory_id=memory_id,
            content=content,
            relevance_score=normalized_score,
            trust_score=trust_score,
            strategy_source=strategy,
            envelope=envelope,
            checksum_sha256=c_hash,
        )


class EvidenceConflict(BaseModel):
    """A detected conflict between two pieces of retrieved evidence."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: UUID = Field(default_factory=uuid4)
    conflict_type: str = Field(
        description="factual | version_mismatch | temporal_drift | authority"
    )
    item_a_id: UUID = Field(description="First conflicting evidence ID")
    item_b_id: UUID = Field(description="Second conflicting evidence ID")
    description: str = Field(description="Detailed explanation of the discrepancy")


class EvidencePackage(BaseModel):
    """
    Self-contained, auditable evidence package assembled by search engine for agent reasoning.
    Separates retrieval mechanics from cognitive consumption.
    """

    model_config = ConfigDict(extra="forbid")

    package_id: UUID = Field(
        default_factory=uuid4, description="Unique package instance identifier"
    )
    query: str = Field(description="Original search query")
    tenant_id: str = Field(description="Tenant ID")
    items: list[EvidenceItem] = Field(
        default_factory=list, description="Ranked evidence items"
    )
    strategies_used: list[str] = Field(
        default_factory=list, description="Strategies executed"
    )
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Overall package confidence score"
    )
    conflicts: list[EvidenceConflict] = Field(
        default_factory=list, description="Contradictions or conflicts identified"
    )
    missing_aspects: list[str] = Field(
        default_factory=list,
        description="Sub-queries or entities not covered in results",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
