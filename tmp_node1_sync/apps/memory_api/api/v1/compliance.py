"""
ISO/IEC 42001 Compliance API - AI Management System

This module provides comprehensive compliance endpoints for:
- Human-in-the-loop approval workflows
- Context provenance and decision lineage
- Circuit breaker status and resilience monitoring
- Policy versioning and enforcement

Endpoints:
- POST /v1/compliance/approvals - Request approval for high-risk operations
- GET /v1/compliance/approvals/{request_id} - Check approval status
- POST /v1/compliance/approvals/{request_id}/decide - Approve or reject
- POST /v1/compliance/provenance/context - Create decision context
- POST /v1/compliance/provenance/decision - Record decision
- GET /v1/compliance/provenance/lineage/{decision_id} - Get decision lineage
- GET /v1/compliance/circuit-breakers - Get all circuit breaker states
- GET /v1/compliance/circuit-breakers/{name} - Get specific breaker state
- POST /v1/compliance/circuit-breakers/{name}/reset - Reset circuit breaker
- GET /v1/compliance/policies - List policies
- POST /v1/compliance/policies - Create policy
- POST /v1/compliance/policies/{policy_id}/activate - Activate policy
- POST /v1/compliance/policies/{policy_id}/enforce - Enforce policy
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from apps.memory_api.dependencies import get_db_pool
from apps.memory_api.models import OperationRiskLevel
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import require_admin, verify_tenant_access
from apps.memory_api.services.context_provenance_service import (
    ContextProvenanceService,
    ContextSource,
    ContextSourceType,
    DecisionType,
)
from apps.memory_api.services.human_approval_service import (
    ApprovalDecision,
    ApprovalDecisionRequest,
    ApprovalStatus,
    HumanApprovalService,
)
from apps.memory_api.services.policy_versioning_service import (
    PolicyType,
    PolicyVersioningService,
)
from apps.memory_api.utils.circuit_breaker import rae_circuit_breakers

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)
router = APIRouter(
    prefix="/v1/compliance",
    tags=["ISO/IEC 42001 Compliance"],
    dependencies=[Depends(auth.verify_token)],  # All endpoints require auth
)


# ============================================================================
# Request/Response Models
# ============================================================================


class ApprovalRequest(BaseModel):
    """Request for approval of high-risk operation"""

    tenant_id: UUID
    project_id: str
    operation_type: str
    operation_description: str
    risk_level: OperationRiskLevel
    resource_type: str
    resource_id: str
    requested_by: str
    required_approvers: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class ApprovalResponse(BaseModel):
    """Approval request response"""

    request_id: UUID
    status: ApprovalStatus
    risk_level: OperationRiskLevel
    expires_at: Optional[datetime] = None
    min_approvals: int
    current_approvals: int = 0
    approvers: List[str] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    """Approval decision"""

    approver_id: str
    decision: ApprovalDecision
    reason: Optional[str] = None


class ContextCreationRequest(BaseModel):
    """Create decision context"""

    tenant_id: UUID
    project_id: str
    query: str
    sources: List[Dict]


class DecisionRecordRequest(BaseModel):
    """Record a decision"""

    tenant_id: UUID
    project_id: str
    decision_type: DecisionType
    decision_description: str
    context_id: UUID
    output: str
    confidence: float
    model_name: Optional[str] = None
    human_approved: bool = False
    approval_request_id: Optional[UUID] = None
    metadata: Optional[Dict] = None


class CircuitBreakerState(BaseModel):
    """Circuit breaker state"""

    name: str
    state: str
    failure_threshold: int
    recovery_timeout: int
    metrics: Dict


class PolicyRequest(BaseModel):
    """Create policy request"""

    tenant_id: UUID
    policy_id: str
    policy_type: PolicyType
    policy_name: str
    policy_description: str
    rules: Dict
    created_by: str
    metadata: Optional[Dict] = None


class PolicyEnforceRequest(BaseModel):
    """Enforce policy request"""

    context: Dict


# ============================================================================
# Human Approval Endpoints
# ============================================================================


@router.post("/approvals", response_model=ApprovalResponse)
async def request_approval(
    request: ApprovalRequest,
    pool=Depends(get_db_pool),
    tenant_access: bool = Depends(verify_tenant_access),
):
    """
    Request approval for a high-risk operation.

    Based on the risk level, operations may be:
    - Auto-approved (low/none risk)
    - Require single approval (medium/high risk)
    - Require multiple approvals (critical risk)

    **Risk Levels:**
    - none, low: Auto-approved
    - medium: 24h timeout, 1 approval
    - high: 48h timeout, 1 approval
    - critical: 72h timeout, 2 approvals

    **Permissions:** Tenant owner or authorized user
    """
    with tracer.start_as_current_span("rae.api.compliance.request_approval") as span:
        span.set_attribute("rae.tenant_id", request.tenant_id)
        span.set_attribute("rae.project_id", request.project_id)
        span.set_attribute("rae.compliance.operation_type", request.operation_type)
        span.set_attribute("rae.compliance.risk_level", request.risk_level.value)
        span.set_attribute("rae.compliance.resource_type", request.resource_type)

        try:
            service = HumanApprovalService(pool)
            result = await service.request_approval(
                tenant_id=str(request.tenant_id),
                project_id=request.project_id,
                operation_type=request.operation_type,
                operation_description=request.operation_description,
                risk_level=request.risk_level,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                requested_by=request.requested_by,
                required_approvers=request.required_approvers,
                metadata=request.metadata,
            )

            span.set_attribute("rae.compliance.request_id", str(result.request_id))
            span.set_attribute("rae.compliance.approval_status", result.status.value)
            span.set_attribute("rae.compliance.min_approvals", result.min_approvals)
            span.set_attribute("rae.outcome.label", "success")

            return ApprovalResponse(
                request_id=result.request_id,
                status=result.status,
                risk_level=result.risk_level,
                expires_at=result.expires_at,
                min_approvals=result.min_approvals,
                current_approvals=len(result.approvers),
                approvers=result.approvers,
            )

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("approval_request_error", error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to request approval: {str(e)}"
            ) from e


@router.get("/approvals/{request_id}", response_model=ApprovalResponse)
async def check_approval_status(
    request_id: UUID,
    pool=Depends(get_db_pool),
    token_verified: bool = Depends(auth.verify_token),
):
    """
    Check the status of an approval request.

    Returns current status, approvers, and expiration time.
    """
    with tracer.start_as_current_span(
        "rae.api.compliance.check_approval_status"
    ) as span:
        span.set_attribute("rae.compliance.request_id", str(request_id))

        try:
            service = HumanApprovalService(pool)
            result = await service.check_approval_status(request_id)

            span.set_attribute("rae.compliance.approval_status", result.status.value)
            span.set_attribute("rae.compliance.risk_level", result.risk_level.value)
            span.set_attribute(
                "rae.compliance.current_approvals", len(result.approvers)
            )
            span.set_attribute("rae.compliance.min_approvals", result.min_approvals)
            span.set_attribute("rae.outcome.label", "success")

            return ApprovalResponse(
                request_id=result.request_id,
                status=result.status,
                risk_level=result.risk_level,
                expires_at=result.expires_at,
                min_approvals=result.min_approvals,
                current_approvals=len(result.approvers),
                approvers=result.approvers,
            )

        except ValueError as e:
            span.set_attribute("rae.outcome.label", "not_found")
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error(
                "approval_status_error", request_id=str(request_id), error=str(e)
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to check approval status: {str(e)}"
            ) from e


@router.post("/approvals/{request_id}/decide", response_model=ApprovalResponse)
async def process_approval_decision(
    request_id: UUID,
    decision: DecisionRequest,
    pool=Depends(get_db_pool),
    token_verified: bool = Depends(auth.verify_token),
):
    """
    Approve or reject an approval request.

    Only authorized approvers can make decisions.
    For critical operations, multiple approvals may be required.
    """
    with tracer.start_as_current_span(
        "rae.api.compliance.process_approval_decision"
    ) as span:
        span.set_attribute("rae.compliance.request_id", str(request_id))
        span.set_attribute("rae.compliance.decision", decision.decision.value)
        span.set_attribute("rae.compliance.approver_id", decision.approver_id)

        try:
            service = HumanApprovalService(pool)

            decision_request = ApprovalDecisionRequest(
                request_id=request_id,
                approver_id=decision.approver_id,
                decision=decision.decision,
                reason=decision.reason,
            )

            result = await service.process_decision(decision_request)

            span.set_attribute("rae.compliance.approval_status", result.status.value)
            span.set_attribute(
                "rae.compliance.current_approvals", len(result.approvers)
            )
            span.set_attribute("rae.outcome.label", "success")

            return ApprovalResponse(
                request_id=result.request_id,
                status=result.status,
                risk_level=result.risk_level,
                expires_at=result.expires_at,
                min_approvals=result.min_approvals,
                current_approvals=len(result.approvers),
                approvers=result.approvers,
            )

        except ValueError as e:
            span.set_attribute("rae.outcome.label", "invalid_request")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error(
                "approval_decision_error", request_id=str(request_id), error=str(e)
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to process decision: {str(e)}"
            ) from e


# ============================================================================
# Context Provenance Endpoints
# ============================================================================


@router.post("/provenance/context")
async def create_decision_context(
    request: ContextCreationRequest,
    tenant_access: bool = Depends(verify_tenant_access),
):
    """
    Create a decision context for provenance tracking.

    Records the query and source context used for decision-making.
    Calculates quality metrics (relevance, trust, coverage).
    """
    with tracer.start_as_current_span(
        "rae.api.compliance.create_decision_context"
    ) as span:
        span.set_attribute("rae.tenant_id", request.tenant_id)
        span.set_attribute("rae.project_id", request.project_id)
        span.set_attribute("rae.compliance.query_length", len(request.query))
        span.set_attribute("rae.compliance.sources_count", len(request.sources))

        try:
            service = ContextProvenanceService()

            # Convert dict sources to ContextSource objects
            sources = [
                ContextSource(
                    source_id=UUID(s["source_id"]),
                    source_type=ContextSourceType(s["source_type"]),
                    content=s["content"],
                    relevance_score=s["relevance_score"],
                    trust_level=s.get("trust_level", "medium"),
                    source_owner=s.get("source_owner"),
                    metadata=s.get("metadata"),
                )
                for s in request.sources
            ]

            result = await service.create_decision_context(
                tenant_id=str(request.tenant_id),
                project_id=request.project_id,
                query=request.query,
                sources=sources,
            )

            span.set_attribute("rae.compliance.context_id", str(result.context_id))
            span.set_attribute("rae.compliance.avg_relevance", result.avg_relevance)
            span.set_attribute("rae.compliance.avg_trust", result.avg_trust)
            span.set_attribute("rae.compliance.coverage_score", result.coverage_score)
            span.set_attribute("rae.outcome.label", "success")

            return {
                "context_id": str(result.context_id),
                "query": result.query,
                "total_sources": result.total_sources,
                "avg_relevance": result.avg_relevance,
                "avg_trust": result.avg_trust,
                "coverage_score": result.coverage_score,
            }

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("context_creation_error", error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to create context: {str(e)}"
            ) from e


@router.post("/provenance/decision")
async def record_decision(
    request: DecisionRecordRequest,
    tenant_access: bool = Depends(verify_tenant_access),
):
    """
    Record a decision for provenance tracking.

    Links decisions to their context and approval workflows.
    """
    with tracer.start_as_current_span("rae.api.compliance.record_decision") as span:
        span.set_attribute("rae.tenant_id", request.tenant_id)
        span.set_attribute("rae.project_id", request.project_id)
        span.set_attribute("rae.compliance.decision_type", request.decision_type.value)
        span.set_attribute("rae.compliance.context_id", str(request.context_id))
        span.set_attribute("rae.compliance.confidence", request.confidence)
        span.set_attribute("rae.compliance.human_approved", request.human_approved)

        try:
            service = ContextProvenanceService()

            result = await service.record_decision(
                tenant_id=str(request.tenant_id),
                project_id=request.project_id,
                decision_type=request.decision_type,
                decision_description=request.decision_description,
                context_id=request.context_id,
                output=request.output,
                confidence=request.confidence,
                model_name=request.model_name,
                human_approved=request.human_approved,
                approval_request_id=request.approval_request_id,
                metadata=request.metadata,
            )

            span.set_attribute("rae.compliance.decision_id", str(result.decision_id))
            if request.model_name:
                span.set_attribute("rae.compliance.model_name", request.model_name)
            span.set_attribute("rae.outcome.label", "success")

            return {
                "decision_id": str(result.decision_id),
                "context_id": str(result.context_id),
                "confidence": result.confidence,
                "human_approved": result.human_approved,
                "context_summary": result.context_summary,
            }

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("decision_recording_error", error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to record decision: {str(e)}"
            ) from e


@router.get("/provenance/lineage/{decision_id}")
async def get_decision_lineage(
    decision_id: UUID,
    token_verified: bool = Depends(auth.verify_token),
):
    """
    Get the full provenance lineage for a decision.

    Returns the complete chain: query → context → decision
    """
    with tracer.start_as_current_span(
        "rae.api.compliance.get_decision_lineage"
    ) as span:
        span.set_attribute("rae.compliance.decision_id", str(decision_id))

        try:
            service = ContextProvenanceService()
            result = await service.get_decision_lineage(decision_id)

            span.set_attribute("rae.outcome.label", "success")
            return result

        except ValueError as e:
            span.set_attribute("rae.outcome.label", "not_found")
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error(
                "lineage_retrieval_error", decision_id=str(decision_id), error=str(e)
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to get lineage: {str(e)}"
            ) from e


# ============================================================================
# Circuit Breaker Endpoints
# ============================================================================


@router.get("/circuit-breakers", response_model=List[CircuitBreakerState])
async def get_all_circuit_breakers(
    admin_access: bool = Depends(require_admin),
):
    """
    Get the state of all circuit breakers.

    Shows resilience status for database, vector store, and LLM service.

    **Permissions:** Admin only
    """
    with tracer.start_as_current_span(
        "rae.api.compliance.get_all_circuit_breakers"
    ) as span:
        try:
            states = []
            for _name, breaker in rae_circuit_breakers.items():
                state = breaker.get_state()
                states.append(
                    CircuitBreakerState(
                        name=state["name"],
                        state=state["state"].value,
                        failure_threshold=state["failure_threshold"],
                        recovery_timeout=state["recovery_timeout"],
                        metrics=state["metrics"],
                    )
                )

            span.set_attribute("rae.compliance.circuit_breakers_count", len(states))
            span.set_attribute("rae.outcome.label", "success")

            return states

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("circuit_breaker_list_error", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get circuit breaker states: {str(e)}",
            ) from e


@router.get("/circuit-breakers/{name}", response_model=CircuitBreakerState)
async def get_circuit_breaker_state(
    name: str,
    admin_access: bool = Depends(require_admin),
):
    """
    Get the state of a specific circuit breaker.

    **Available breakers:** database, vector_store, llm_service
    **Permissions:** Admin only
    """
    with tracer.start_as_current_span(
        "rae.api.compliance.get_circuit_breaker_state"
    ) as span:
        span.set_attribute("rae.compliance.circuit_breaker_name", name)

        try:
            if name not in rae_circuit_breakers:
                span.set_attribute("rae.outcome.label", "not_found")
                raise HTTPException(
                    status_code=404, detail=f"Circuit breaker '{name}' not found"
                )

            breaker = rae_circuit_breakers[name]
            state = breaker.get_state()

            span.set_attribute(
                "rae.compliance.circuit_breaker_state", state["state"].value
            )
            span.set_attribute(
                "rae.compliance.failure_count", state["metrics"].get("failure_count", 0)
            )
            span.set_attribute("rae.outcome.label", "success")

            return CircuitBreakerState(
                name=state["name"],
                state=state["state"].value,
                failure_threshold=state["failure_threshold"],
                recovery_timeout=state["recovery_timeout"],
                metrics=state["metrics"],
            )

        except HTTPException:
            raise
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("circuit_breaker_state_error", name=name, error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to get circuit breaker state: {str(e)}"
            ) from e


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(
    name: str,
    admin_access: bool = Depends(require_admin),
):
    """
    Reset a circuit breaker to CLOSED state.

    Clears all failure counts and reopens the circuit.

    **Permissions:** Admin only
    """
    with tracer.start_as_current_span(
        "rae.api.compliance.reset_circuit_breaker"
    ) as span:
        span.set_attribute("rae.compliance.circuit_breaker_name", name)

        try:
            if name not in rae_circuit_breakers:
                span.set_attribute("rae.outcome.label", "not_found")
                raise HTTPException(
                    status_code=404, detail=f"Circuit breaker '{name}' not found"
                )

            breaker = rae_circuit_breakers[name]
            breaker.reset()

            span.set_attribute("rae.compliance.circuit_breaker_state", "CLOSED")
            span.set_attribute("rae.outcome.label", "success")

            return {
                "message": f"Circuit breaker '{name}' has been reset",
                "state": "CLOSED",
            }

        except HTTPException:
            raise
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("circuit_breaker_reset_error", name=name, error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to reset circuit breaker: {str(e)}"
            ) from e


# ============================================================================
# Policy Versioning Endpoints
# ============================================================================


@router.get("/policies")
async def list_policies(
    tenant_id: Optional[UUID] = Query(None),
    policy_type: Optional[PolicyType] = Query(None),
    token_verified: bool = Depends(auth.verify_token),
):
    """
    List all policies, optionally filtered by tenant and type.

    **Policy Types:**
    - data_retention
    - access_control
    - approval_workflow
    - trust_scoring
    - risk_assessment
    - human_oversight
    """
    with tracer.start_as_current_span("rae.api.compliance.list_policies") as span:
        if tenant_id:
            span.set_attribute("rae.tenant_id", tenant_id)
        if policy_type:
            span.set_attribute("rae.compliance.policy_type", policy_type.value)

        try:
            # This is a simplified implementation
            # In production, you would query the database for policies
            span.set_attribute("rae.outcome.label", "success")

            return {
                "message": "Policy listing endpoint",
                "filters": {
                    "tenant_id": tenant_id,
                    "policy_type": policy_type.value if policy_type else None,
                },
            }

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("policy_list_error", error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to list policies: {str(e)}"
            ) from e


@router.post("/policies")
async def create_policy(
    request: PolicyRequest,
    tenant_access: bool = Depends(verify_tenant_access),
):
    """
    Create a new policy version.

    If a policy with the same ID exists, creates a new version.
    New policies start in DRAFT status.
    """
    with tracer.start_as_current_span("rae.api.compliance.create_policy") as span:
        span.set_attribute("rae.tenant_id", request.tenant_id)
        span.set_attribute("rae.compliance.policy_id", request.policy_id)
        span.set_attribute("rae.compliance.policy_type", request.policy_type.value)
        span.set_attribute("rae.compliance.created_by", request.created_by)

        try:
            service = PolicyVersioningService()

            result = await service.create_policy(
                tenant_id=str(request.tenant_id),
                policy_id=request.policy_id,
                policy_type=request.policy_type,
                policy_name=request.policy_name,
                policy_description=request.policy_description,
                rules=request.rules,
                created_by=request.created_by,
                metadata=request.metadata,
            )

            span.set_attribute("rae.compliance.version_id", str(result.version_id))
            span.set_attribute("rae.compliance.version", result.version)
            span.set_attribute("rae.compliance.policy_status", result.status.value)
            span.set_attribute("rae.outcome.label", "success")

            return {
                "version_id": str(result.version_id),
                "policy_id": result.policy_id,
                "version": result.version,
                "status": result.status.value,
                "created_at": result.created_at.isoformat(),
            }

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("policy_creation_error", error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to create policy: {str(e)}"
            ) from e


@router.post("/policies/{policy_id}/activate")
async def activate_policy(
    policy_id: str,
    version_id: UUID,
    admin_access: bool = Depends(require_admin),
):
    """
    Activate a policy version.

    Only one version of a policy can be active at a time.
    Previous active version is automatically deprecated.

    **Permissions:** Admin only
    """
    with tracer.start_as_current_span("rae.api.compliance.activate_policy") as span:
        span.set_attribute("rae.compliance.policy_id", policy_id)
        span.set_attribute("rae.compliance.version_id", str(version_id))

        try:
            service = PolicyVersioningService()
            result = await service.activate_policy(policy_id, version_id)

            span.set_attribute("rae.compliance.version", result.version)
            span.set_attribute("rae.compliance.policy_status", result.status.value)
            span.set_attribute("rae.outcome.label", "success")

            return {
                "version_id": str(result.version_id),
                "policy_id": result.policy_id,
                "version": result.version,
                "status": result.status.value,
                "activated_at": (
                    result.activated_at.isoformat() if result.activated_at else None
                ),
            }

        except ValueError as e:
            span.set_attribute("rae.outcome.label", "not_found")
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("policy_activation_error", policy_id=policy_id, error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to activate policy: {str(e)}"
            ) from e


@router.post("/policies/{policy_id}/enforce")
async def enforce_policy(
    policy_id: str,
    request: PolicyEnforceRequest,
    token_verified: bool = Depends(auth.verify_token),
):
    """
    Enforce a policy against a context.

    Returns compliance status, violations, and warnings.
    """
    with tracer.start_as_current_span("rae.api.compliance.enforce_policy") as span:
        span.set_attribute("rae.compliance.policy_id", policy_id)

        try:
            service = PolicyVersioningService()
            result = await service.enforce_policy(policy_id, request.context)

            span.set_attribute("rae.compliance.version", result.version)
            span.set_attribute("rae.compliance.compliant", result.compliant)
            span.set_attribute(
                "rae.compliance.violations_count", len(result.violations)
            )
            span.set_attribute("rae.compliance.warnings_count", len(result.warnings))
            span.set_attribute("rae.outcome.label", "success")

            return {
                "policy_id": result.policy_id,
                "version": result.version,
                "compliant": result.compliant,
                "violations": result.violations,
                "warnings": result.warnings,
                "checked_at": result.checked_at.isoformat(),
            }

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("policy_enforcement_error", policy_id=policy_id, error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to enforce policy: {str(e)}"
            ) from e
