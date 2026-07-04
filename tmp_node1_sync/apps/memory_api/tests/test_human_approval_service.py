"""
Tests for HumanApprovalService - ISO/IEC 42001 Section 9 (Human Oversight)
"""

from datetime import timedelta
from uuid import uuid4

import pytest

from apps.memory_api.models import OperationRiskLevel
from apps.memory_api.services.human_approval_service import (
    ApprovalDecision,
    ApprovalDecisionRequest,
    ApprovalStatus,
    HumanApprovalService,
)
from apps.memory_api.utils.datetime_utils import utc_now

pytestmark = pytest.mark.iso42001


@pytest.fixture(autouse=True)
def mock_logger(mocker):
    """Mock logger to avoid structured logging issues"""
    mocker.patch("apps.memory_api.services.human_approval_service.logger")


@pytest.fixture
def mock_rae_service(mocker):
    """Mock RAECoreService"""
    service = mocker.MagicMock()
    service.postgres_pool = mocker.AsyncMock()
    return service


@pytest.fixture
def approval_service(mock_rae_service):
    """Create HumanApprovalService instance"""
    return HumanApprovalService(mock_rae_service)


class TestRequestApproval:
    """Tests for request_approval method"""

    @pytest.mark.asyncio
    async def test_auto_approve_low_risk(self, approval_service, mocker):
        """Low risk operations should be auto-approved"""
        mocker.patch.object(
            approval_service, "_store_approval_request", return_value=None
        )

        result = await approval_service.request_approval(
            tenant_id="test-tenant",
            project_id="test-project",
            operation_type="read_memory",
            operation_description="Read memory for display",
            risk_level=OperationRiskLevel.low,
            resource_type="memory",
            resource_id="mem-123",
            requested_by="user-1",
        )

        assert result.status == ApprovalStatus.AUTO_APPROVED
        assert result.approved_by == "system"
        assert result.approved_at is not None

    @pytest.mark.asyncio
    async def test_auto_approve_none_risk(self, approval_service, mocker):
        """None risk operations should be auto-approved"""
        mocker.patch.object(
            approval_service, "_store_approval_request", return_value=None
        )

        result = await approval_service.request_approval(
            tenant_id="test-tenant",
            project_id="test-project",
            operation_type="list_memories",
            operation_description="List memories",
            risk_level=OperationRiskLevel.none,
            resource_type="memory",
            resource_id="*",
            requested_by="user-1",
        )

        assert result.status == ApprovalStatus.AUTO_APPROVED

    @pytest.mark.asyncio
    async def test_pending_approval_high_risk(self, approval_service, mocker):
        """High risk operations should require approval"""
        mocker.patch.object(
            approval_service, "_store_approval_request", return_value=None
        )

        result = await approval_service.request_approval(
            tenant_id="test-tenant",
            project_id="test-project",
            operation_type="delete_memory",
            operation_description="Delete critical memory",
            risk_level=OperationRiskLevel.high,
            resource_type="memory",
            resource_id="mem-123",
            requested_by="user-1",
        )

        assert result.status == ApprovalStatus.PENDING
        assert result.approved_by is None
        assert result.expires_at is not None
        assert result.min_approvals == 1

    @pytest.mark.asyncio
    async def test_pending_approval_critical_risk(self, approval_service, mocker):
        """Critical risk operations should require 2 approvals"""
        mocker.patch.object(
            approval_service, "_store_approval_request", return_value=None
        )

        result = await approval_service.request_approval(
            tenant_id="test-tenant",
            project_id="test-project",
            operation_type="delete_all_memories",
            operation_description="Delete all tenant memories",
            risk_level=OperationRiskLevel.critical,
            resource_type="memory",
            resource_id="*",
            requested_by="user-1",
        )

        assert result.status == ApprovalStatus.PENDING
        assert result.min_approvals == 2
        assert result.expires_at is not None
        # Critical operations have 3 day timeout
        expected_timeout = utc_now() + timedelta(hours=72)
        assert abs((result.expires_at - expected_timeout).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_timeout_configuration(self, approval_service, mocker):
        """Test timeout configuration by risk level"""
        mocker.patch.object(
            approval_service, "_store_approval_request", return_value=None
        )

        # Test high risk timeout (48 hours)
        result_high = await approval_service.request_approval(
            tenant_id="test-tenant",
            project_id="test-project",
            operation_type="delete_memory",
            operation_description="Delete memory",
            risk_level=OperationRiskLevel.high,
            resource_type="memory",
            resource_id="mem-123",
            requested_by="user-1",
        )

        expected_high = utc_now() + timedelta(hours=48)
        assert abs((result_high.expires_at - expected_high).total_seconds()) < 5

        # Test medium risk timeout (24 hours)
        result_medium = await approval_service.request_approval(
            tenant_id="test-tenant",
            project_id="test-project",
            operation_type="update_memory",
            operation_description="Update memory",
            risk_level=OperationRiskLevel.medium,
            resource_type="memory",
            resource_id="mem-123",
            requested_by="user-1",
        )

        expected_medium = utc_now() + timedelta(hours=24)
        assert abs((result_medium.expires_at - expected_medium).total_seconds()) < 5


class TestProcessDecision:
    """Tests for process_decision method"""

    @pytest.mark.asyncio
    async def test_approve_single_approver(self, approval_service, mocker):
        """Test approval with single approver"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.PENDING
        mock_request.expires_at = utc_now() + timedelta(hours=24)
        mock_request.required_approvers = ["approver-1", "approver-2"]
        mock_request.approvers = []
        mock_request.min_approvals = 1

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )
        mocker.patch.object(
            approval_service, "_update_approval_request", return_value=None
        )

        decision = ApprovalDecisionRequest(
            request_id=request_id,
            approver_id="approver-1",
            decision=ApprovalDecision.APPROVE,
            reason="Approved after review",
        )

        result = await approval_service.process_decision(decision)

        assert result.status == ApprovalStatus.APPROVED
        assert "approver-1" in result.approvers
        assert result.approved_by == "approver-1"
        assert result.approved_at is not None

    @pytest.mark.asyncio
    async def test_approve_multi_approver(self, approval_service, mocker):
        """Test approval requiring multiple approvers"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.PENDING
        mock_request.expires_at = utc_now() + timedelta(hours=24)
        mock_request.required_approvers = ["approver-1", "approver-2"]
        mock_request.approvers = []
        mock_request.min_approvals = 2
        mock_request.version = 1

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )
        mocker.patch.object(
            approval_service, "_update_approval_request", return_value=None
        )

        # First approval
        decision1 = ApprovalDecisionRequest(
            request_id=request_id,
            approver_id="approver-1",
            decision=ApprovalDecision.APPROVE,
        )
        result1 = await approval_service.process_decision(decision1)
        assert result1.status == ApprovalStatus.PENDING
        assert len(result1.approvers) == 1

        # Second approval (should complete)
        mock_request.approvers = ["approver-1"]
        decision2 = ApprovalDecisionRequest(
            request_id=request_id,
            approver_id="approver-2",
            decision=ApprovalDecision.APPROVE,
        )
        result2 = await approval_service.process_decision(decision2)
        assert result2.status == ApprovalStatus.APPROVED
        assert len(result2.approvers) == 2

    @pytest.mark.asyncio
    async def test_reject_decision(self, approval_service, mocker):
        """Test rejection of approval request"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.PENDING
        mock_request.expires_at = utc_now() + timedelta(hours=24)
        mock_request.required_approvers = ["approver-1"]
        mock_request.approvers = []

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )
        mocker.patch.object(
            approval_service, "_update_approval_request", return_value=None
        )

        decision = ApprovalDecisionRequest(
            request_id=request_id,
            approver_id="approver-1",
            decision=ApprovalDecision.REJECT,
            reason="Security concerns",
        )

        result = await approval_service.process_decision(decision)

        assert result.status == ApprovalStatus.REJECTED
        assert result.rejection_reason == "Security concerns"

    @pytest.mark.asyncio
    async def test_expired_request(self, approval_service, mocker):
        """Test expired approval request"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.PENDING
        mock_request.expires_at = utc_now() - timedelta(hours=1)  # Expired

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )
        mocker.patch.object(
            approval_service, "_update_approval_request", return_value=None
        )

        decision = ApprovalDecisionRequest(
            request_id=request_id,
            approver_id="approver-1",
            decision=ApprovalDecision.APPROVE,
        )

        with pytest.raises(ValueError, match="expired"):
            await approval_service.process_decision(decision)

    @pytest.mark.asyncio
    async def test_unauthorized_approver(self, approval_service, mocker):
        """Test unauthorized approver"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.PENDING
        mock_request.expires_at = utc_now() + timedelta(hours=24)
        mock_request.required_approvers = ["approver-1", "approver-2"]
        mock_request.approvers = []

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )

        decision = ApprovalDecisionRequest(
            request_id=request_id,
            approver_id="unauthorized-user",
            decision=ApprovalDecision.APPROVE,
        )

        with pytest.raises(ValueError, match="not authorized"):
            await approval_service.process_decision(decision)

    @pytest.mark.asyncio
    async def test_already_decided(self, approval_service, mocker):
        """Test decision on already approved/rejected request"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.APPROVED

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )

        decision = ApprovalDecisionRequest(
            request_id=request_id,
            approver_id="approver-1",
            decision=ApprovalDecision.APPROVE,
        )

        with pytest.raises(ValueError, match="already"):
            await approval_service.process_decision(decision)


class TestCheckApprovalStatus:
    """Tests for check_approval_status method"""

    @pytest.mark.asyncio
    async def test_check_pending_status(self, approval_service, mocker):
        """Test checking pending approval status"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.PENDING
        mock_request.expires_at = utc_now() + timedelta(hours=24)

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )

        result = await approval_service.check_approval_status(request_id)
        assert result.status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_auto_expire_on_check(self, approval_service, mocker):
        """Test automatic expiration when checking status"""
        request_id = uuid4()
        mock_request = mocker.MagicMock()
        mock_request.request_id = request_id
        mock_request.status = ApprovalStatus.PENDING
        mock_request.expires_at = utc_now() - timedelta(hours=1)  # Expired

        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=mock_request
        )
        mocker.patch.object(
            approval_service, "_update_approval_request", return_value=None
        )

        result = await approval_service.check_approval_status(request_id)
        assert result.status == ApprovalStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_request_not_found(self, approval_service, mocker):
        """Test checking non-existent request"""
        request_id = uuid4()
        mocker.patch.object(
            approval_service, "_get_approval_request", return_value=None
        )

        with pytest.raises(ValueError, match="not found"):
            await approval_service.check_approval_status(request_id)


class TestRequiresApproval:
    """Tests for requires_approval helper method"""

    def test_requires_approval_critical(self, approval_service):
        """Critical operations require approval"""
        assert approval_service.requires_approval(OperationRiskLevel.critical) is True

    def test_requires_approval_high(self, approval_service):
        """High risk operations require approval"""
        assert approval_service.requires_approval(OperationRiskLevel.high) is True

    def test_requires_approval_medium(self, approval_service):
        """Medium risk operations require approval"""
        assert approval_service.requires_approval(OperationRiskLevel.medium) is True

    def test_no_approval_low(self, approval_service):
        """Low risk operations don't require approval"""
        assert approval_service.requires_approval(OperationRiskLevel.low) is False

    def test_no_approval_none(self, approval_service):
        """None risk operations don't require approval"""
        assert approval_service.requires_approval(OperationRiskLevel.none) is False
