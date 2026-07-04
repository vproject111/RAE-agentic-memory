"""
Tests for PolicyVersioningService - ISO/IEC 42001 Section 6 (Risk Management)
"""

from uuid import uuid4

import pytest

from apps.memory_api.services.policy_versioning_service import (
    PolicyStatus,
    PolicyType,
    PolicyVersioningService,
)

pytestmark = pytest.mark.iso42001


@pytest.fixture(autouse=True)
def mock_logger(mocker):
    """Mock logger to avoid structured logging issues"""
    mocker.patch("apps.memory_api.services.policy_versioning_service.logger")


@pytest.fixture
def policy_service():
    """Create PolicyVersioningService instance"""
    return PolicyVersioningService()


class TestCreatePolicy:
    """Tests for create_policy method"""

    @pytest.mark.asyncio
    async def test_create_first_policy_version(self, policy_service):
        """Test creating the first version of a policy"""
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="retention_policy_v1",
            policy_type=PolicyType.DATA_RETENTION,
            policy_name="Data Retention Policy",
            policy_description="Defines data retention rules",
            rules={"max_retention_days": 365, "min_retention_days": 30},
            created_by="admin@example.com",
        )

        assert policy.policy_id == "retention_policy_v1"
        assert policy.tenant_id == "test-tenant"
        assert policy.version == 1
        assert policy.status == PolicyStatus.DRAFT
        assert policy.policy_type == PolicyType.DATA_RETENTION
        assert policy.rules["max_retention_days"] == 365
        assert policy.previous_version_id is None

    @pytest.mark.asyncio
    async def test_create_second_policy_version(self, policy_service):
        """Test creating a second version of an existing policy"""
        # Create first version
        policy_v1 = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="access_control_policy",
            policy_type=PolicyType.ACCESS_CONTROL,
            policy_name="Access Control Policy",
            policy_description="Defines access control rules",
            rules={"require_2fa": True},
            created_by="admin@example.com",
        )

        # Create second version
        policy_v2 = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="access_control_policy",
            policy_type=PolicyType.ACCESS_CONTROL,
            policy_name="Access Control Policy",
            policy_description="Updated access control rules",
            rules={"require_2fa": True, "require_biometric": True},
            created_by="admin@example.com",
        )

        assert policy_v2.version == 2
        assert policy_v2.previous_version_id == policy_v1.version_id
        assert policy_v2.status == PolicyStatus.DRAFT

    @pytest.mark.asyncio
    async def test_create_policy_with_metadata(self, policy_service):
        """Test creating policy with additional metadata"""
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.TRUST_SCORING,
            policy_name="Trust Scoring Policy",
            policy_description="Defines trust scoring rules",
            rules={"min_trust_score": 0.7},
            created_by="admin@example.com",
            metadata={"compliance_standard": "ISO 42001", "review_period": "quarterly"},
        )

        assert policy.metadata["compliance_standard"] == "ISO 42001"
        assert policy.metadata["review_period"] == "quarterly"


class TestActivatePolicy:
    """Tests for activate_policy method"""

    @pytest.mark.asyncio
    async def test_activate_draft_policy(self, policy_service):
        """Test activating a draft policy"""
        # Create a draft policy
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.APPROVAL_WORKFLOW,
            policy_name="Approval Workflow Policy",
            policy_description="Test policy",
            rules={"require_approval": True},
            created_by="admin@example.com",
        )

        assert policy.status == PolicyStatus.DRAFT

        # Activate it
        activated = await policy_service.activate_policy(
            policy_id="test_policy", version_id=policy.version_id
        )

        assert activated.status == PolicyStatus.ACTIVE
        assert activated.activated_at is not None

    @pytest.mark.asyncio
    async def test_activate_deprecates_previous(self, policy_service):
        """Test that activating new version deprecates previous active version"""
        # Create and activate first version
        policy_v1 = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.RISK_ASSESSMENT,
            policy_name="Risk Assessment Policy",
            policy_description="Version 1",
            rules={"max_risk_score": 0.5},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy_v1.version_id)

        # Create and activate second version
        policy_v2 = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.RISK_ASSESSMENT,
            policy_name="Risk Assessment Policy",
            policy_description="Version 2",
            rules={"max_risk_score": 0.7},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy_v2.version_id)

        # Check that v1 is deprecated
        assert policy_v1.status == PolicyStatus.DEPRECATED
        assert policy_v1.deprecated_at is not None
        assert policy_v2.status == PolicyStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_nonexistent_policy(self, policy_service):
        """Test activating non-existent policy raises error"""
        with pytest.raises(ValueError, match="not found"):
            await policy_service.activate_policy("nonexistent", uuid4())

    @pytest.mark.asyncio
    async def test_activate_nonexistent_version(self, policy_service):
        """Test activating non-existent version raises error"""
        await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.HUMAN_OVERSIGHT,
            policy_name="Test Policy",
            policy_description="Test",
            rules={},
            created_by="admin@example.com",
        )

        with pytest.raises(ValueError, match="Version .* not found"):
            await policy_service.activate_policy("test_policy", uuid4())


class TestGetActivePolicy:
    """Tests for get_active_policy method"""

    @pytest.mark.asyncio
    async def test_get_active_policy(self, policy_service):
        """Test retrieving active policy version"""
        # Create and activate policy
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.DATA_RETENTION,
            policy_name="Test Policy",
            policy_description="Test",
            rules={"retention_days": 90},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy.version_id)

        # Retrieve active policy
        active = await policy_service.get_active_policy("test_policy")

        assert active is not None
        assert active.status == PolicyStatus.ACTIVE
        assert active.policy_id == "test_policy"

    @pytest.mark.asyncio
    async def test_get_active_policy_no_active(self, policy_service):
        """Test retrieving active policy when none is active"""
        # Create draft policy but don't activate
        await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.ACCESS_CONTROL,
            policy_name="Test Policy",
            policy_description="Test",
            rules={},
            created_by="admin@example.com",
        )

        # Should return None
        active = await policy_service.get_active_policy("test_policy")
        assert active is None

    @pytest.mark.asyncio
    async def test_get_active_policy_nonexistent(self, policy_service):
        """Test retrieving non-existent policy returns None"""
        active = await policy_service.get_active_policy("nonexistent")
        assert active is None


class TestGetPolicyHistory:
    """Tests for get_policy_history method"""

    @pytest.mark.asyncio
    async def test_get_policy_history(self, policy_service):
        """Test retrieving policy version history"""
        # Create multiple versions
        for i in range(3):
            await policy_service.create_policy(
                tenant_id="test-tenant",
                policy_id="test_policy",
                policy_type=PolicyType.TRUST_SCORING,
                policy_name=f"Test Policy v{i + 1}",
                policy_description=f"Version {i + 1}",
                rules={"version": i + 1},
                created_by="admin@example.com",
            )

        # Get history
        history = await policy_service.get_policy_history("test_policy")

        assert len(history) == 3
        assert history[0].version == 1
        assert history[1].version == 2
        assert history[2].version == 3

    @pytest.mark.asyncio
    async def test_get_policy_history_nonexistent(self, policy_service):
        """Test retrieving history for non-existent policy"""
        history = await policy_service.get_policy_history("nonexistent")
        assert history == []


class TestEnforcePolicy:
    """Tests for enforce_policy method"""

    @pytest.mark.asyncio
    async def test_enforce_policy_compliant(self, policy_service):
        """Test policy enforcement for compliant context"""
        # Create and activate policy
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.RISK_ASSESSMENT,
            policy_name="Risk Policy",
            policy_description="Test policy",
            rules={"risk_score": {"max": 0.8, "min": 0.0}},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy.version_id)

        # Enforce with compliant context
        result = await policy_service.enforce_policy(
            policy_id="test_policy", context={"risk_score": 0.5}
        )

        assert result.compliant is True
        assert len(result.violations) == 0
        assert result.policy_id == "test_policy"
        assert result.version == 1

    @pytest.mark.asyncio
    async def test_enforce_policy_max_violation(self, policy_service):
        """Test policy enforcement for max value violation"""
        # Create and activate policy
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.RISK_ASSESSMENT,
            policy_name="Risk Policy",
            policy_description="Test policy",
            rules={"risk_score": {"max": 0.8}},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy.version_id)

        # Enforce with non-compliant context (exceeds max)
        result = await policy_service.enforce_policy(
            policy_id="test_policy", context={"risk_score": 0.9}
        )

        assert result.compliant is False
        assert len(result.violations) == 1
        assert "exceeds maximum" in result.violations[0]

    @pytest.mark.asyncio
    async def test_enforce_policy_min_violation(self, policy_service):
        """Test policy enforcement for min value violation"""
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.TRUST_SCORING,
            policy_name="Trust Policy",
            policy_description="Test policy",
            rules={"trust_score": {"min": 0.5}},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy.version_id)

        # Enforce with non-compliant context (below min)
        result = await policy_service.enforce_policy(
            policy_id="test_policy", context={"trust_score": 0.3}
        )

        assert result.compliant is False
        assert len(result.violations) == 1
        assert "below minimum" in result.violations[0]

    @pytest.mark.asyncio
    async def test_enforce_policy_exact_match_warning(self, policy_service):
        """Test policy enforcement for exact match with warning"""
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.ACCESS_CONTROL,
            policy_name="Access Policy",
            policy_description="Test policy",
            rules={"access_level": "admin"},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy.version_id)

        # Enforce with mismatched value (generates warning, not violation)
        result = await policy_service.enforce_policy(
            policy_id="test_policy", context={"access_level": "user"}
        )

        assert result.compliant is True  # No violations, only warnings
        assert len(result.warnings) == 1
        assert "does not match policy" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_enforce_policy_missing_field_warning(self, policy_service):
        """Test policy enforcement for missing field"""
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.DATA_RETENTION,
            policy_name="Retention Policy",
            policy_description="Test policy",
            rules={"retention_days": 90},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy.version_id)

        # Enforce without required field
        result = await policy_service.enforce_policy(
            policy_id="test_policy", context={}
        )

        assert result.compliant is True  # No violations
        assert len(result.warnings) == 1
        assert "not found in context" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_enforce_policy_no_active_version(self, policy_service):
        """Test enforcing policy with no active version"""
        # Create draft policy but don't activate
        await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.HUMAN_OVERSIGHT,
            policy_name="Test Policy",
            policy_description="Test",
            rules={},
            created_by="admin@example.com",
        )

        result = await policy_service.enforce_policy(
            policy_id="test_policy", context={}
        )

        assert result.compliant is False
        assert "No active policy version found" in result.violations


class TestRollbackPolicy:
    """Tests for rollback_policy method"""

    @pytest.mark.asyncio
    async def test_rollback_to_previous_version(self, policy_service):
        """Test rolling back to previous policy version"""
        # Create and activate v1
        policy_v1 = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.APPROVAL_WORKFLOW,
            policy_name="Test Policy",
            policy_description="Version 1",
            rules={"approval_required": True},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy_v1.version_id)

        # Create and activate v2
        policy_v2 = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.APPROVAL_WORKFLOW,
            policy_name="Test Policy",
            policy_description="Version 2",
            rules={"approval_required": False},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy_v2.version_id)

        # Rollback
        rolled_back = await policy_service.rollback_policy("test_policy")

        assert rolled_back.version == 1
        assert rolled_back.status == PolicyStatus.ACTIVE
        assert policy_v2.status == PolicyStatus.DEPRECATED
        assert rolled_back.activated_at is not None

    @pytest.mark.asyncio
    async def test_rollback_no_previous_version(self, policy_service):
        """Test rollback when there is no previous version"""
        # Create and activate only one version
        policy = await policy_service.create_policy(
            tenant_id="test-tenant",
            policy_id="test_policy",
            policy_type=PolicyType.RISK_ASSESSMENT,
            policy_name="Test Policy",
            policy_description="Version 1",
            rules={},
            created_by="admin@example.com",
        )
        await policy_service.activate_policy("test_policy", policy.version_id)

        # Try to rollback
        with pytest.raises(ValueError, match="No previous version"):
            await policy_service.rollback_policy("test_policy")

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_policy(self, policy_service):
        """Test rollback of non-existent policy"""
        with pytest.raises(ValueError, match="not found"):
            await policy_service.rollback_policy("nonexistent")


class TestPolicyTypes:
    """Tests for different policy types"""

    @pytest.mark.asyncio
    async def test_all_policy_types(self, policy_service):
        """Test that all policy types can be created"""
        policy_types = [
            PolicyType.DATA_RETENTION,
            PolicyType.ACCESS_CONTROL,
            PolicyType.APPROVAL_WORKFLOW,
            PolicyType.TRUST_SCORING,
            PolicyType.RISK_ASSESSMENT,
            PolicyType.HUMAN_OVERSIGHT,
        ]

        for policy_type in policy_types:
            policy = await policy_service.create_policy(
                tenant_id="test-tenant",
                policy_id=f"policy_{policy_type.value}",
                policy_type=policy_type,
                policy_name=f"{policy_type.value} Policy",
                policy_description=f"Test {policy_type.value} policy",
                rules={"test": True},
                created_by="admin@example.com",
            )

            assert policy.policy_type == policy_type
