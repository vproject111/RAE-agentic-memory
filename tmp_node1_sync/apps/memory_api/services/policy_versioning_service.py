"""
Policy Versioning Service - ISO/IEC 42001 Section 6 (Risk Management)

Manages versioning and enforcement of AI governance policies.

ISO/IEC 42001 compliance:
- Section 6: Risk management policies
- RISK-003 further mitigation: Policy drift and inconsistency
- Ensures policy integrity and auditability

Key features:
- Policy versioning with change tracking
- Policy enforcement with compliance checking
- Rollback capabilities
- Audit trail for policy changes
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from apps.memory_api.utils.datetime_utils import utc_now

logger = structlog.get_logger(__name__)


class PolicyStatus(str, Enum):
    """Status of policy version"""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PolicyType(str, Enum):
    """Type of governance policy"""

    DATA_RETENTION = "data_retention"
    ACCESS_CONTROL = "access_control"
    APPROVAL_WORKFLOW = "approval_workflow"
    TRUST_SCORING = "trust_scoring"
    RISK_ASSESSMENT = "risk_assessment"
    HUMAN_OVERSIGHT = "human_oversight"


class PolicyVersion(BaseModel):
    """Versioned policy definition"""

    version_id: UUID = Field(default_factory=uuid4)
    policy_id: str  # Stable policy identifier (e.g., "retention_policy_v1")
    tenant_id: str

    # Version info
    version: int = 1
    status: PolicyStatus = PolicyStatus.DRAFT

    # Policy details
    policy_type: PolicyType
    policy_name: str
    policy_description: str

    # Policy rules (JSON schema or dict)
    rules: Dict[str, Any] = Field(default_factory=dict)

    # Change tracking
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    activated_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None

    # Changelog
    change_summary: Optional[str] = None
    previous_version_id: Optional[UUID] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyEnforcementResult(BaseModel):
    """Result of policy enforcement check"""

    policy_id: str
    version: int
    compliant: bool
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=utc_now)


class PolicyVersioningService:
    """Service for policy versioning and enforcement"""

    def __init__(self):
        # In-memory policy storage (would be database in production)
        self.policies: Dict[str, List[PolicyVersion]] = {}

    async def create_policy(
        self,
        tenant_id: str,
        policy_id: str,
        policy_type: PolicyType,
        policy_name: str,
        policy_description: str,
        rules: Dict[str, Any],
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyVersion:
        """
        Create new policy or new version of existing policy.

        Args:
            tenant_id: Tenant identifier
            policy_id: Stable policy identifier
            policy_type: Type of policy
            policy_name: Human-readable name
            policy_description: Description
            rules: Policy rules as dict
            created_by: Creator user ID
            metadata: Additional metadata

        Returns:
            PolicyVersion object
        """
        # Check if policy exists
        existing_versions = self.policies.get(policy_id, [])

        # Determine version number
        version = len(existing_versions) + 1

        # Get previous version ID if exists
        previous_version_id = (
            existing_versions[-1].version_id if existing_versions else None
        )

        policy = PolicyVersion(
            policy_id=policy_id,
            tenant_id=tenant_id,
            version=version,
            status=PolicyStatus.DRAFT,
            policy_type=policy_type,
            policy_name=policy_name,
            policy_description=policy_description,
            rules=rules,
            created_by=created_by,
            previous_version_id=previous_version_id,
            metadata=metadata or {},
        )

        # Store policy
        if policy_id not in self.policies:
            self.policies[policy_id] = []

        self.policies[policy_id].append(policy)

        logger.info(
            "policy_created",
            policy_id=policy_id,
            version=version,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        return policy

    async def activate_policy(self, policy_id: str, version_id: UUID) -> PolicyVersion:
        """
        Activate a policy version.

        Deactivates previous active version and activates specified version.

        Args:
            policy_id: Policy identifier
            version_id: Version to activate

        Returns:
            Activated PolicyVersion

        Raises:
            ValueError: If policy or version not found
        """
        versions = self.policies.get(policy_id, [])

        if not versions:
            raise ValueError(f"Policy {policy_id} not found")

        # Find version to activate
        target_version = None
        for v in versions:
            if v.version_id == version_id:
                target_version = v
                break

        if not target_version:
            raise ValueError(f"Version {version_id} not found for policy {policy_id}")

        # Deprecate current active version
        for v in versions:
            if v.status == PolicyStatus.ACTIVE:
                v.status = PolicyStatus.DEPRECATED
                v.deprecated_at = utc_now()

                logger.info(
                    "policy_deprecated",
                    policy_id=policy_id,
                    version=v.version,
                    message="Previous version deprecated",
                )

        # Activate target version
        target_version.status = PolicyStatus.ACTIVE
        target_version.activated_at = utc_now()

        logger.info(
            "policy_activated",
            policy_id=policy_id,
            version=target_version.version,
            version_id=str(version_id),
        )

        return target_version

    async def get_active_policy(self, policy_id: str) -> Optional[PolicyVersion]:
        """
        Get currently active version of a policy.

        Args:
            policy_id: Policy identifier

        Returns:
            Active PolicyVersion or None
        """
        versions = self.policies.get(policy_id, [])

        for v in versions:
            if v.status == PolicyStatus.ACTIVE:
                return v

        return None

    async def get_policy_history(self, policy_id: str) -> List[PolicyVersion]:
        """
        Get version history for a policy.

        Args:
            policy_id: Policy identifier

        Returns:
            List of PolicyVersion objects, ordered by version
        """
        return self.policies.get(policy_id, [])

    async def enforce_policy(
        self, policy_id: str, context: Dict[str, Any]
    ) -> PolicyEnforcementResult:
        """
        Enforce a policy against provided context.

        Args:
            policy_id: Policy identifier
            context: Context data to check against policy

        Returns:
            PolicyEnforcementResult with compliance status
        """
        policy = await self.get_active_policy(policy_id)

        if not policy:
            return PolicyEnforcementResult(
                policy_id=policy_id,
                version=0,
                compliant=False,
                violations=["No active policy version found"],
            )

        violations = []
        warnings = []

        # Simple rule enforcement (would be more sophisticated in production)
        for rule_key, rule_value in policy.rules.items():
            if rule_key in context:
                context_value = context[rule_key]

                # Example: numeric comparison
                if isinstance(rule_value, dict):
                    if "max" in rule_value and context_value > rule_value["max"]:
                        violations.append(
                            f"{rule_key} exceeds maximum: {context_value} > {rule_value['max']}"
                        )
                    if "min" in rule_value and context_value < rule_value["min"]:
                        violations.append(
                            f"{rule_key} below minimum: {context_value} < {rule_value['min']}"
                        )

                # Example: exact match
                elif context_value != rule_value:
                    warnings.append(
                        f"{rule_key} does not match policy: {context_value} != {rule_value}"
                    )
            else:
                warnings.append(f"Required field {rule_key} not found in context")

        compliant = len(violations) == 0

        result = PolicyEnforcementResult(
            policy_id=policy_id,
            version=policy.version,
            compliant=compliant,
            violations=violations,
            warnings=warnings,
        )

        logger.info(
            "policy_enforced",
            policy_id=policy_id,
            version=policy.version,
            compliant=compliant,
            violations_count=len(violations),
        )

        return result

    async def rollback_policy(self, policy_id: str) -> Optional[PolicyVersion]:
        """
        Rollback to previous active version of policy.

        Args:
            policy_id: Policy identifier

        Returns:
            Previous PolicyVersion now activated, or None

        Raises:
            ValueError: If no previous version exists
        """
        versions = self.policies.get(policy_id, [])

        if not versions:
            raise ValueError(f"Policy {policy_id} not found")

        # Find current active and previous version
        current_active = None
        previous_version = None

        for i, v in enumerate(versions):
            if v.status == PolicyStatus.ACTIVE:
                current_active = v
                if i > 0:
                    previous_version = versions[i - 1]
                break

        if not previous_version:
            raise ValueError(f"No previous version to rollback to for {policy_id}")

        # Rollback
        if current_active:
            current_active.status = PolicyStatus.DEPRECATED
            current_active.deprecated_at = utc_now()

        previous_version.status = PolicyStatus.ACTIVE
        previous_version.activated_at = utc_now()

        logger.warning(
            "policy_rolled_back",
            policy_id=policy_id,
            from_version=current_active.version if current_active else None,
            to_version=previous_version.version,
            message="Policy rolled back to previous version",
        )

        return previous_version


# Global policy service instance
policy_service = PolicyVersioningService()
