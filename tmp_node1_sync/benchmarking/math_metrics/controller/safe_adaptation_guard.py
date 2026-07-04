"""Safe Adaptation Guard for MPEB benchmark.

Prevents catastrophic forgetting by distinguishing temporary vs permanent
adaptations. Uses a sandbox-to-permanent promotion strategy with validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set


@dataclass
class AdaptationCandidate:
    """Candidate adaptation awaiting validation."""

    rule_id: str
    new_value: Any
    proposed_at: datetime
    validation_count: int = 0
    last_validated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SafeAdaptationGuard:
    """Guard against catastrophic forgetting in policy adaptation.

    Strategy:
    1. All rule changes go to sandbox first
    2. After N successful validations → promote to permanent
    3. Critical rules require more validations
    4. Failed validations reset counter

    This prevents:
    - Accidental overwrite of critical rules
    - Rapid oscillation between conflicting adaptations
    - Catastrophic forgetting of core knowledge

    Example:
        >>> guard = SafeAdaptationGuard()
        >>> guard.propose_adaptation("reward_threshold", 0.85)
        >>> guard.validate_adaptation("reward_threshold")
        >>> guard.validate_adaptation("reward_threshold")
        >>> guard.validate_adaptation("reward_threshold")
        >>> if guard.is_ready_for_promotion("reward_threshold"):
        ...     perm_value = guard.promote_to_permanent("reward_threshold")
    """

    def __init__(
        self,
        default_validation_threshold: int = 3,
        critical_validation_threshold: int = 5,
    ):
        """Initialize safe adaptation guard.

        Args:
            default_validation_threshold: Validations needed for normal rules
            critical_validation_threshold: Validations needed for critical rules
        """
        self.default_validation_threshold = default_validation_threshold
        self.critical_validation_threshold = critical_validation_threshold

        # Storage
        self.sandbox_adaptations: Dict[str, AdaptationCandidate] = {}
        self.permanent_adaptations: Dict[str, Any] = {}
        self.critical_rules: Set[str] = set()

        # Statistics
        self.stats = {
            "total_proposals": 0,
            "total_validations": 0,
            "total_promotions": 0,
            "total_rejections": 0,
            "total_rollbacks": 0,
        }

    def mark_as_critical(self, rule_id: str):
        """Mark a rule as critical (requires more validations).

        Args:
            rule_id: Rule identifier
        """
        self.critical_rules.add(rule_id)

    def is_critical(self, rule_id: str) -> bool:
        """Check if rule is marked as critical.

        Args:
            rule_id: Rule identifier

        Returns:
            True if rule is critical
        """
        return rule_id in self.critical_rules

    def propose_adaptation(
        self, rule_id: str, new_value: Any, metadata: Optional[Dict[str, Any]] = None
    ):
        """Propose a new adaptation (add to sandbox).

        Args:
            rule_id: Unique rule identifier
            new_value: Proposed new value for the rule
            metadata: Optional metadata about the proposal
        """
        self.stats["total_proposals"] += 1

        candidate = AdaptationCandidate(
            rule_id=rule_id,
            new_value=new_value,
            proposed_at=datetime.now(timezone.utc),
            validation_count=0,
            metadata=metadata or {},
        )

        self.sandbox_adaptations[rule_id] = candidate

    def validate_adaptation(self, rule_id: str, success: bool = True):
        """Record validation result for a sandboxed adaptation.

        Args:
            rule_id: Rule identifier
            success: Whether validation passed (True) or failed (False)

        Raises:
            KeyError: If rule_id not in sandbox
        """
        if rule_id not in self.sandbox_adaptations:
            raise KeyError(f"Rule {rule_id} not in sandbox")

        self.stats["total_validations"] += 1
        candidate = self.sandbox_adaptations[rule_id]

        if success:
            candidate.validation_count += 1
            candidate.last_validated_at = datetime.now(timezone.utc)
        else:
            # Failed validation → reset counter
            self.stats["total_rejections"] += 1
            candidate.validation_count = 0

    def is_ready_for_promotion(self, rule_id: str) -> bool:
        """Check if adaptation has enough validations for promotion.

        Args:
            rule_id: Rule identifier

        Returns:
            True if ready for promotion to permanent
        """
        if rule_id not in self.sandbox_adaptations:
            return False

        candidate = self.sandbox_adaptations[rule_id]
        threshold = (
            self.critical_validation_threshold
            if self.is_critical(rule_id)
            else self.default_validation_threshold
        )

        return candidate.validation_count >= threshold

    def promote_to_permanent(self, rule_id: str) -> Any:
        """Promote a validated adaptation to permanent storage.

        Args:
            rule_id: Rule identifier

        Returns:
            The promoted value

        Raises:
            ValueError: If not ready for promotion
        """
        if not self.is_ready_for_promotion(rule_id):
            candidate = self.sandbox_adaptations.get(rule_id)
            if candidate:
                threshold = (
                    self.critical_validation_threshold
                    if self.is_critical(rule_id)
                    else self.default_validation_threshold
                )
                raise ValueError(
                    f"Rule {rule_id} not ready for promotion "
                    f"({candidate.validation_count}/{threshold} validations)"
                )
            else:
                raise ValueError(f"Rule {rule_id} not in sandbox")

        self.stats["total_promotions"] += 1

        candidate = self.sandbox_adaptations.pop(rule_id)
        self.permanent_adaptations[rule_id] = candidate.new_value

        return candidate.new_value

    def get_sandbox_value(self, rule_id: str) -> Optional[Any]:
        """Get value from sandbox (if exists).

        Args:
            rule_id: Rule identifier

        Returns:
            Sandboxed value or None
        """
        candidate = self.sandbox_adaptations.get(rule_id)
        return candidate.new_value if candidate else None

    def get_permanent_value(self, rule_id: str) -> Optional[Any]:
        """Get value from permanent storage (if exists).

        Args:
            rule_id: Rule identifier

        Returns:
            Permanent value or None
        """
        return self.permanent_adaptations.get(rule_id)

    def get_value(self, rule_id: str, prefer_sandbox: bool = True) -> Optional[Any]:
        """Get value with preference for sandbox or permanent.

        Args:
            rule_id: Rule identifier
            prefer_sandbox: If True, return sandbox value if exists

        Returns:
            Value from sandbox (if prefer_sandbox and exists) or permanent
        """
        if prefer_sandbox:
            sandbox_value = self.get_sandbox_value(rule_id)
            if sandbox_value is not None:
                return sandbox_value

        return self.get_permanent_value(rule_id)

    def rollback_sandbox_adaptation(self, rule_id: str):
        """Remove an adaptation from sandbox (rollback).

        Args:
            rule_id: Rule identifier

        Raises:
            KeyError: If rule_id not in sandbox
        """
        if rule_id not in self.sandbox_adaptations:
            raise KeyError(f"Rule {rule_id} not in sandbox")

        self.stats["total_rollbacks"] += 1
        del self.sandbox_adaptations[rule_id]

    def get_sandbox_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all sandboxed adaptations.

        Returns:
            Dict mapping rule_id to status info
        """
        status = {}
        for rule_id, candidate in self.sandbox_adaptations.items():
            threshold = (
                self.critical_validation_threshold
                if self.is_critical(rule_id)
                else self.default_validation_threshold
            )

            status[rule_id] = {
                "validation_count": candidate.validation_count,
                "validation_threshold": threshold,
                "ready_for_promotion": candidate.validation_count >= threshold,
                "is_critical": self.is_critical(rule_id),
                "proposed_at": candidate.proposed_at.isoformat(),
                "last_validated_at": (
                    candidate.last_validated_at.isoformat()
                    if candidate.last_validated_at
                    else None
                ),
            }

        return status

    def get_stats(self) -> Dict[str, int]:
        """Get guard statistics.

        Returns:
            Dict with stat counters
        """
        return self.stats.copy()

    def clear_sandbox(self):
        """Clear all sandboxed adaptations (useful for testing)."""
        self.sandbox_adaptations.clear()

    def clear_permanent(self):
        """Clear all permanent adaptations (useful for testing)."""
        self.permanent_adaptations.clear()

    def reset(self):
        """Reset guard to initial state."""
        self.sandbox_adaptations.clear()
        self.permanent_adaptations.clear()
        self.critical_rules.clear()
        for key in self.stats:
            self.stats[key] = 0
