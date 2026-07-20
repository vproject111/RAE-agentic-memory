from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional, List
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from rae_core.models.cost import CostVector
from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType
from rae_core.types.branded import (
    ChecksumSha256Value,
    RequestIdValue,
    TenantIdValue,
)


class ActionRecord(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    department: str
    role: str
    action_type: str
    goal: str
    tools_used: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str


class DecisionEvidenceRecord(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_summary: str
    reasoning_summary: str
    policy_basis: str | None = None
    input_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    cost: float | None = None
    cost_vector: CostVector | None = None


class OutcomeRecord(BaseModel):
    outcome_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str
    result: str  # success | failure | partial
    quality_result: str | None = None
    latency_ms: int | None = None
    cost: float | None = None
    observed_effect: str | None = None
    cost_vector: CostVector | None = None


class ConflictType(StrEnum):
    VERSION = "version"
    SEMANTIC = "semantic"
    SCOPE = "scope"
    RUNTIME_DRIFT = "runtime_drift"
    POLICY_VIOLATION = "policy_violation"


class ConflictSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    RESOLVED_WITH_WARNING = "resolved_with_warning"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(default_factory=lambda: str(uuid4()), max_length=255)
    knowledge_id: str | None = Field(default=None, max_length=255)
    source_ref: str = Field(min_length=1, max_length=2048)
    source_type: KnowledgeSourceType
    authority_level: AuthorityLevel
    relevance: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    scope_match: float = Field(ge=0.0, le=1.0)
    checksum: ChecksumSha256Value
    observed_at: datetime
    content_excerpt: str | None = Field(default=None, max_length=4000)
    content_ref: str | None = Field(default=None, max_length=2048)
    supports: list[str] = Field(default_factory=list, max_length=100)
    contradicts: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict = Field(default_factory=dict)


class KnowledgeConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(default_factory=lambda: str(uuid4()), max_length=255)
    subject: str = Field(min_length=1, max_length=2048)
    source_a: str = Field(min_length=1, max_length=2048)
    source_b: str = Field(min_length=1, max_length=2048)
    conflict_type: ConflictType
    severity: ConflictSeverity
    preferred_source: str | None = Field(default=None, max_length=2048)
    resolution_rule: str | None = Field(default=None, max_length=1000)
    rationale: str | None = Field(default=None, max_length=4000)


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: UUID = Field(default_factory=uuid4)
    tenant_id: TenantIdValue
    request_id: RequestIdValue
    query: str = Field(min_length=1, max_length=20_000)
    generated_at: datetime
    policy_version: str = Field(min_length=1, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=1000)
    conflicts: list[KnowledgeConflict] = Field(default_factory=list, max_length=500)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)
    resolution_status: ResolutionStatus
    content_hash: ChecksumSha256Value | None = None
    audit_hash: ChecksumSha256Value | None = None
    previous_audit_hash: ChecksumSha256Value | None = None
