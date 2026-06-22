"""
Compliance API v2 - powered by RAE-Core.
ISO/IEC 42001 AI Management System.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from apps.memory_api.dependencies import get_db_pool
from apps.memory_api.models import OperationRiskLevel
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import require_admin, verify_tenant_access
from apps.memory_api.services.human_approval_service import (
    ApprovalStatus,
    HumanApprovalService,
)
from apps.memory_api.utils.circuit_breaker import rae_circuit_breakers

router = APIRouter(
    prefix="/v2/compliance",
    tags=["Compliance v2 (RAE-Core)"],
    dependencies=[Depends(auth.verify_token)],
)
logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)

# Request/Response models (re-using logic from V1 but updating paths)


class ApprovalRequestV2(BaseModel):
    tenant_id: UUID
    project: str
    operation_type: str
    operation_description: str
    risk_level: OperationRiskLevel
    resource_type: str
    resource_id: str
    requested_by: str
    required_approvers: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class ApprovalResponseV2(BaseModel):
    request_id: UUID
    status: ApprovalStatus
    risk_level: OperationRiskLevel
    expires_at: Optional[datetime] = None
    min_approvals: int
    current_approvals: int = 0
    approvers: List[str] = Field(default_factory=list)


# --- Approval Endpoints ---


@router.post("/approvals", response_model=ApprovalResponseV2)
async def request_approval(
    request: ApprovalRequestV2,
    req: Request,
    pool=Depends(get_db_pool),
):
    with tracer.start_as_current_span("rae.api.v2.compliance.request_approval"):
        await auth.check_tenant_access(req, request.tenant_id)
        service = HumanApprovalService(pool)
        result = await service.request_approval(
            tenant_id=str(request.tenant_id),
            project=request.project,
            operation_type=request.operation_type,
            operation_description=request.operation_description,
            risk_level=request.risk_level,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            requested_by=request.requested_by,
            required_approvers=request.required_approvers,
            metadata=request.metadata,
        )
        return ApprovalResponseV2(
            request_id=result.request_id,
            status=result.status,
            risk_level=result.risk_level,
            expires_at=result.expires_at,
            min_approvals=result.min_approvals,
            current_approvals=len(result.approvers),
            approvers=result.approvers,
        )


@router.get("/approvals/{request_id}", response_model=ApprovalResponseV2)
async def check_approval_status(request_id: UUID, pool=Depends(get_db_pool)):
    service = HumanApprovalService(pool)
    result = await service.check_approval_status(request_id)
    return ApprovalResponseV2(
        request_id=result.request_id,
        status=result.status,
        risk_level=result.risk_level,
        expires_at=result.expires_at,
        min_approvals=result.min_approvals,
        current_approvals=len(result.approvers),
        approvers=result.approvers,
    )


# --- Circuit Breaker Endpoints ---


@router.get("/circuit-breakers")
async def get_all_circuit_breakers(admin_access: bool = Depends(require_admin)):
    states = []
    for _name, breaker in rae_circuit_breakers.items():
        state = breaker.get_state()
        states.append(
            {
                "name": state["name"],
                "state": state["state"].value,
                "metrics": state["metrics"],
            }
        )
    return states


# TODO: Add remaining provenance and policy endpoints if needed by tests
