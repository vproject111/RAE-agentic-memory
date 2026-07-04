"""
Context Provenance Service - ISO/IEC 42001 Section 8 (Transparency & Explainability)

This service tracks the provenance of context used in AI decisions, enabling
full traceability from query → context → decision.

ISO/IEC 42001 compliance:
- Section 8.1: Transparency and explainability
- RISK-005 mitigation: Loss of context/knowledge lineage
- Enables auditability of AI decisions

Key features:
- Context lineage tracking
- Decision audit trail
- Memory source attribution
- Confidence scoring for context quality
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ContextSourceType(str, Enum):
    """Type of context source"""

    MEMORY = "memory"
    REFLECTION = "reflection"
    SEMANTIC_NODE = "semantic_node"
    EXTERNAL_API = "external_api"
    USER_INPUT = "user_input"
    SYSTEM_GENERATED = "system_generated"


class DecisionType(str, Enum):
    """Type of AI decision"""

    RESPONSE_GENERATION = "response_generation"
    ACTION_EXECUTION = "action_execution"
    MEMORY_STORAGE = "memory_storage"
    CONTEXT_SELECTION = "context_selection"
    REFLECTION_CREATION = "reflection_creation"


class ContextSource(BaseModel):
    """Individual source of context"""

    source_id: UUID
    source_type: ContextSourceType
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    trust_level: str  # From SourceTrustLevel
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    source_owner: Optional[str] = None
    verification_status: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DecisionContext(BaseModel):
    """Context used for an AI decision"""

    context_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    project_id: str

    # Query that triggered context retrieval
    query: str
    query_embedding: Optional[List[float]] = None

    # Context sources
    sources: List[ContextSource] = Field(default_factory=list)
    total_sources: int = 0

    # Context quality metrics
    avg_relevance: float = Field(0.0, ge=0.0, le=1.0)
    avg_trust: float = Field(0.0, ge=0.0, le=1.0)
    coverage_score: float = Field(0.0, ge=0.0, le=1.0)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    """Record of an AI decision with full provenance"""

    decision_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    project_id: str

    # Decision details
    decision_type: DecisionType
    decision_description: str

    # Context used
    context_id: UUID
    context_summary: str

    # Decision output
    output: str
    confidence: float = Field(ge=0.0, le=1.0)

    # Human involvement
    human_approved: bool = False
    approval_request_id: Optional[UUID] = None
    approved_by: Optional[str] = None

    # Model information
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    prompt_template: Optional[str] = None

    # Timestamps
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextProvenanceService:
    """Service for tracking context provenance and decision lineage"""

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings

    async def create_decision_context(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        sources: List[ContextSource],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionContext:
        """
        Create a decision context with full provenance.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query: Query that triggered context retrieval
            sources: List of context sources
            metadata: Additional metadata

        Returns:
            DecisionContext object with provenance tracking
        """
        # Calculate quality metrics
        avg_relevance = (
            sum(s.relevance_score for s in sources) / len(sources) if sources else 0.0
        )

        # Map trust levels to numeric scores
        trust_mapping = {"high": 1.0, "medium": 0.7, "low": 0.4, "unverified": 0.0}
        trust_scores = [trust_mapping.get(s.trust_level, 0.0) for s in sources]
        avg_trust = sum(trust_scores) / len(trust_scores) if trust_scores else 0.0

        # Simple coverage score (can be enhanced)
        coverage_score = min(len(sources) / 5.0, 1.0)  # Normalize to max 5 sources

        context = DecisionContext(
            tenant_id=tenant_id,
            project_id=project_id,
            query=query,
            sources=sources,
            total_sources=len(sources),
            avg_relevance=avg_relevance,
            avg_trust=avg_trust,
            coverage_score=coverage_score,
            metadata=metadata or {},
        )

        logger.info(
            "context_created",
            context_id=str(context.context_id),
            tenant_id=tenant_id,
            sources_count=len(sources),
            avg_relevance=avg_relevance,
            avg_trust=avg_trust,
        )

        # Store in database (placeholder)
        await self._store_context(context)

        return context

    async def record_decision(
        self,
        tenant_id: str,
        project_id: str,
        decision_type: DecisionType,
        decision_description: str,
        context_id: UUID,
        output: str,
        confidence: float,
        model_name: Optional[str] = None,
        human_approved: bool = False,
        approval_request_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionRecord:
        """
        Record an AI decision with full provenance.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            decision_type: Type of decision
            decision_description: Human-readable description
            context_id: ID of context used
            output: Decision output
            confidence: Confidence score
            model_name: AI model used
            human_approved: Whether human approved
            approval_request_id: ID of approval request if any
            metadata: Additional metadata

        Returns:
            DecisionRecord with full audit trail
        """
        # Fetch context to create summary
        context = await self._get_context(context_id)
        context_summary = (
            f"{len(context.sources)} sources (avg relevance: {context.avg_relevance:.2f})"
            if context
            else "Context not found"
        )

        decision = DecisionRecord(
            tenant_id=tenant_id,
            project_id=project_id,
            decision_type=decision_type,
            decision_description=decision_description,
            context_id=context_id,
            context_summary=context_summary,
            output=output,
            confidence=confidence,
            model_name=model_name,
            human_approved=human_approved,
            approval_request_id=approval_request_id,
            metadata=metadata or {},
        )

        logger.info(
            "decision_recorded",
            decision_id=str(decision.decision_id),
            tenant_id=tenant_id,
            decision_type=decision_type,
            confidence=confidence,
            human_approved=human_approved,
        )

        # Store in database (placeholder)
        await self._store_decision(decision)

        return decision

    async def get_decision_lineage(self, decision_id: UUID) -> Dict[str, Any]:
        """
        Get full lineage for a decision (query → context → decision).

        Args:
            decision_id: Decision ID

        Returns:
            Dict with full provenance chain
        """
        decision = await self._get_decision(decision_id)

        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        context = await self._get_context(decision.context_id)

        lineage = {
            "decision": decision.model_dump(),
            "context": context.model_dump() if context else None,
            "provenance_chain": {
                "query": context.query if context else None,
                "sources": [
                    {
                        "id": str(s.source_id),
                        "type": s.source_type,
                        "trust_level": s.trust_level,
                        "relevance": s.relevance_score,
                        "owner": s.source_owner,
                    }
                    for s in (context.sources if context else [])
                ],
                "decision_confidence": decision.confidence,
                "human_approved": decision.human_approved,
            },
        }

        return lineage

    async def audit_context_quality(self, context_id: UUID) -> Dict[str, Any]:
        """
        Audit the quality of context used.

        Args:
            context_id: Context ID

        Returns:
            Dict with quality metrics and recommendations
        """
        context = await self._get_context(context_id)

        if not context:
            raise ValueError(f"Context {context_id} not found")

        # Analyze quality
        issues = []
        recommendations = []

        if context.avg_trust < 0.7:
            issues.append("Low average trust level in sources")
            recommendations.append("Verify and update source trust levels")

        if context.avg_relevance < 0.6:
            issues.append("Low average relevance in retrieved context")
            recommendations.append("Review query formulation or search parameters")

        if context.total_sources < 2:
            issues.append("Insufficient context sources")
            recommendations.append("Expand context retrieval to include more sources")

        quality_score = (
            context.avg_trust * 0.4
            + context.avg_relevance * 0.4
            + context.coverage_score * 0.2
        )

        return {
            "context_id": str(context_id),
            "quality_score": quality_score,
            "metrics": {
                "avg_trust": context.avg_trust,
                "avg_relevance": context.avg_relevance,
                "coverage_score": context.coverage_score,
                "total_sources": context.total_sources,
            },
            "issues": issues,
            "recommendations": recommendations,
        }

    # ========================================================================
    # Private helper methods (database placeholders)
    # ========================================================================

    async def _store_context(self, context: DecisionContext):
        """Store context in database"""
        # Placeholder
        logger.debug("stored_context", context_id=str(context.context_id))

    async def _store_decision(self, decision: DecisionRecord):
        """Store decision in database"""
        # Placeholder
        logger.debug("stored_decision", decision_id=str(decision.decision_id))

    async def _get_context(self, context_id: UUID) -> Optional[DecisionContext]:
        """Fetch context from database"""
        # Placeholder
        logger.debug("fetched_context", context_id=str(context_id))
        return None

    async def _get_decision(self, decision_id: UUID) -> Optional[DecisionRecord]:
        """Fetch decision from database"""
        # Placeholder
        logger.debug("fetched_decision", decision_id=str(decision_id))
        return None
