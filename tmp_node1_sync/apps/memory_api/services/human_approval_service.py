"""
Human Approval Workflow Service - ISO/IEC 42001 Section 9 (Human Oversight)

This service manages human-in-the-loop approval workflows for high-risk AI operations.

ISO/IEC 42001 compliance:
- Section 9: Human oversight of AI systems
- RISK-010 mitigation: High-risk decisions without human oversight
- Defense in depth: Prevents autonomous execution of critical operations

Key features:
- Risk-based approval routing
- Timeout management
- Approval audit trail
- Multi-approver support for critical operations
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from apps.memory_api.models import OperationRiskLevel
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.utils.datetime_utils import utc_now

logger = structlog.get_logger(__name__)


class ApprovalStatus(str, Enum):
    """Status of approval request"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"  # For low-risk operations


class ApprovalDecision(str, Enum):
    """Approver's decision"""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_MORE_INFO = "request_more_info"


class ApprovalRequest(BaseModel):
    """Human approval request model"""

    request_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    project_id: str

    # Operation details
    operation_type: str = Field(
        ..., description="Type of operation (delete_memory, execute_action, etc.)"
    )
    operation_description: str
    risk_level: OperationRiskLevel

    # Resource details
    resource_type: str
    resource_id: str
    resource_details: Dict[str, Any] = Field(default_factory=dict)

    # Approval workflow
    required_approvers: List[str] = Field(
        default_factory=list, description="User IDs who can approve"
    )
    approvers: List[str] = Field(
        default_factory=list, description="User IDs who have approved"
    )
    min_approvals: int = Field(
        1, description="Minimum approvals required (2 for critical)"
    )

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str
    requested_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None

    # Decision
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    """Request to make approval decision"""

    request_id: UUID
    approver_id: str
    decision: ApprovalDecision
    reason: Optional[str] = None
    notes: Optional[str] = None


class HumanApprovalService:
    """Service for managing human approval workflows"""

    # Timeout configuration by risk level
    APPROVAL_TIMEOUTS = {
        OperationRiskLevel.critical: timedelta(hours=72),  # 3 days
        OperationRiskLevel.high: timedelta(hours=48),  # 2 days
        OperationRiskLevel.medium: timedelta(hours=24),  # 1 day
        OperationRiskLevel.low: timedelta(hours=1),  # 1 hour
        OperationRiskLevel.none: timedelta(seconds=0),  # Immediate
    }

    # Minimum approvers by risk level
    MIN_APPROVERS = {
        OperationRiskLevel.critical: 2,  # Requires 2 approvals
        OperationRiskLevel.high: 1,
        OperationRiskLevel.medium: 1,
        OperationRiskLevel.low: 1,
        OperationRiskLevel.none: 0,
    }

    def __init__(self, rae_service: RAECoreService):
        self.rae_service = rae_service

    async def request_approval(
        self,
        tenant_id: str,
        project_id: str,
        operation_type: str,
        operation_description: str,
        risk_level: OperationRiskLevel,
        resource_type: str,
        resource_id: str,
        requested_by: str,
        required_approvers: Optional[List[str]] = None,
        resource_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Request human approval for an operation.

        For low/none risk operations, auto-approves immediately.
        For medium/high/critical, creates pending approval request.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            operation_type: Type of operation
            operation_description: Human-readable description
            risk_level: Risk level of operation
            resource_type: Type of resource being operated on
            resource_id: ID of resource
            requested_by: User requesting the operation
            required_approvers: List of user IDs who can approve (optional)
            resource_details: Additional details about resource
            metadata: Additional metadata

        Returns:
            ApprovalRequest object

        Raises:
            ValueError: If invalid parameters
        """
        logger.info(
            "approval_requested",
            tenant_id=tenant_id,
            operation_type=operation_type,
            risk_level=risk_level,
            requested_by=requested_by,
        )

        # Auto-approve low-risk operations
        if risk_level in [OperationRiskLevel.low, OperationRiskLevel.none]:
            logger.info(
                "auto_approved_low_risk",
                tenant_id=tenant_id,
                operation_type=operation_type,
                risk_level=risk_level,
            )

            request = ApprovalRequest(
                tenant_id=tenant_id,
                project_id=project_id,
                operation_type=operation_type,
                operation_description=operation_description,
                risk_level=risk_level,
                resource_type=resource_type,
                resource_id=resource_id,
                requested_by=requested_by,
                status=ApprovalStatus.AUTO_APPROVED,
                approved_by="system",
                approved_at=utc_now(),
                resource_details=resource_details or {},
                metadata=metadata or {},
            )

            # Store in database
            await self._store_approval_request(request)

            return request

        # For higher risk, create pending approval request
        timeout = self.APPROVAL_TIMEOUTS.get(risk_level, timedelta(hours=24))
        expires_at = utc_now() + timeout

        min_approvals = self.MIN_APPROVERS.get(risk_level, 1)

        request = ApprovalRequest(
            tenant_id=tenant_id,
            project_id=project_id,
            operation_type=operation_type,
            operation_description=operation_description,
            risk_level=risk_level,
            resource_type=resource_type,
            resource_id=resource_id,
            requested_by=requested_by,
            required_approvers=required_approvers or [],
            min_approvals=min_approvals,
            status=ApprovalStatus.PENDING,
            expires_at=expires_at,
            resource_details=resource_details or {},
            metadata=metadata or {},
        )

        # Store in database
        await self._store_approval_request(request)

        logger.info(
            "approval_pending",
            request_id=str(request.request_id),
            tenant_id=tenant_id,
            operation_type=operation_type,
            risk_level=risk_level,
            expires_at=expires_at.isoformat(),
            min_approvals=min_approvals,
        )

        return request

    async def process_decision(
        self, decision_request: ApprovalDecisionRequest
    ) -> ApprovalRequest:
        """
        Process an approval decision from a human approver.

        Args:
            decision_request: Decision request with approver and decision

        Returns:
            Updated ApprovalRequest

        Raises:
            ValueError: If request not found or invalid state
        """
        # Fetch current request
        request = await self._get_approval_request(decision_request.request_id)

        if not request:
            raise ValueError(
                f"Approval request {decision_request.request_id} not found"
            )

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request already {request.status}, cannot process decision"
            )

        # Check if expired
        if request.expires_at and utc_now() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            await self._update_approval_request(request)
            raise ValueError("Approval request has expired")

        # Check if approver is authorized
        if (
            request.required_approvers
            and decision_request.approver_id not in request.required_approvers
        ):
            logger.warning(
                "unauthorized_approver",
                request_id=str(request.request_id),
                approver_id=decision_request.approver_id,
                authorized=request.required_approvers,
            )
            raise ValueError("Approver not authorized for this request")

        # Process decision
        if decision_request.decision == ApprovalDecision.REJECT:
            request.status = ApprovalStatus.REJECTED
            request.rejection_reason = decision_request.reason
            logger.info(
                "approval_rejected",
                request_id=str(request.request_id),
                approver=decision_request.approver_id,
                reason=decision_request.reason,
            )

        elif decision_request.decision == ApprovalDecision.APPROVE:
            # Add approver
            if decision_request.approver_id not in request.approvers:
                request.approvers.append(decision_request.approver_id)

            # Check if we have enough approvals
            if len(request.approvers) >= request.min_approvals:
                request.status = ApprovalStatus.APPROVED
                request.approved_by = decision_request.approver_id
                request.approved_at = utc_now()

                logger.info(
                    "approval_granted",
                    request_id=str(request.request_id),
                    approver=decision_request.approver_id,
                    total_approvers=len(request.approvers),
                )
            else:
                logger.info(
                    "approval_partial",
                    request_id=str(request.request_id),
                    approver=decision_request.approver_id,
                    approvals=len(request.approvers),
                    required=request.min_approvals,
                )

        # Update request in database
        await self._update_approval_request(request)

        return request

    async def check_approval_status(self, request_id: UUID) -> ApprovalRequest:
        """
        Check status of approval request.

        Args:
            request_id: Approval request ID

        Returns:
            ApprovalRequest with current status

        Raises:
            ValueError: If request not found
        """
        request = await self._get_approval_request(request_id)

        if not request:
            raise ValueError(f"Approval request {request_id} not found")

        # Check if expired
        if (
            request.status == ApprovalStatus.PENDING
            and request.expires_at
            and utc_now() > request.expires_at
        ):
            request.status = ApprovalStatus.EXPIRED
            await self._update_approval_request(request)

        return request

    async def list_pending_approvals(
        self,
        tenant_id: str,
        approver_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ApprovalRequest]:
        """
        List pending approval requests.

        Args:
            tenant_id: Tenant identifier
            approver_id: Optional filter for specific approver
            limit: Maximum number of requests to return

        Returns:
            List of pending ApprovalRequest objects
        """
        # This would query the database
        # Placeholder for now
        return []

    # ========================================================================
    # Private helper methods
    # ========================================================================

    async def _store_approval_request(self, request: ApprovalRequest):
        """Store approval request in database"""
        # Placeholder - would insert into approval_requests table
        logger.debug("stored_approval_request", request_id=str(request.request_id))

    async def _update_approval_request(self, request: ApprovalRequest):
        """Update approval request in database"""
        # Placeholder - would update approval_requests table
        logger.debug(
            "updated_approval_request",
            request_id=str(request.request_id),
            status=request.status,
        )

    async def _get_approval_request(
        self, request_id: UUID
    ) -> Optional[ApprovalRequest]:
        """Fetch approval request from database"""
        # Placeholder - would query approval_requests table
        logger.debug("fetched_approval_request", request_id=str(request_id))
        return None

    def requires_approval(self, risk_level: OperationRiskLevel) -> bool:
        """
        Check if operation requires human approval.

        Args:
            risk_level: Risk level of operation

        Returns:
            True if approval required, False otherwise
        """
        return risk_level not in [OperationRiskLevel.low, OperationRiskLevel.none]
