"""
Decision data structures for Math Layer Controller

MathDecision: Standardized decision format
DecisionWithOutcome: Decision paired with its outcome for learning
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .features import Features
from .types import MathLevel


@dataclass
class MathDecision:
    """
    Standardized decision structure from the MathLayerController.

    This dataclass captures everything needed for:
    1. Executing the decision (level, strategy, params)
    2. Explaining the decision (explanation)
    3. Logging and analysis (telemetry_tags, features_used)
    4. Future learning (confidence, outcome linkage via decision_id)

    Attributes:
        decision_id: Unique identifier for correlating with outcomes
        timestamp: When the decision was made
        selected_level: Which math level to use (L1, L2, or L3)
        strategy_id: Specific strategy within the level
        params: Configuration parameters for the strategy
        explanation: Human-readable explanation of why this decision
        telemetry_tags: Tags for filtering in observability systems
        features_used: The features that informed this decision
        confidence: Confidence score (0.0-1.0), higher = more certain
    """

    # Identity
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Decision
    selected_level: MathLevel = MathLevel.L1
    strategy_id: str = "default"
    params: Dict[str, Any] = field(default_factory=dict)

    # Explanation
    explanation: str = ""

    # Observability
    telemetry_tags: Dict[str, str] = field(default_factory=dict)

    # Context (for learning)
    features_used: Optional[Features] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging and storage"""
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat(),
            "selected_level": self.selected_level.value,
            "strategy_id": self.strategy_id,
            "params": self.params,
            "explanation": self.explanation,
            "telemetry_tags": self.telemetry_tags,
            "features": self.features_used.to_dict() if self.features_used else None,
            "confidence": self.confidence,
        }

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MathDecision":
        """Deserialize from dictionary"""
        return cls(
            decision_id=data.get("decision_id", str(uuid.uuid4())[:8]),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else datetime.now(timezone.utc)
            ),
            selected_level=MathLevel(
                data.get("selected_level", "deterministic_heuristic")
            ),
            strategy_id=data.get("strategy_id", "default"),
            params=data.get("params", {}),
            explanation=data.get("explanation", ""),
            telemetry_tags=data.get("telemetry_tags", {}),
            features_used=None,  # Features need separate deserialization
            confidence=data.get("confidence", 1.0),
        )

    def with_outcome(
        self, success: bool, metrics: Dict[str, float]
    ) -> "DecisionWithOutcome":
        """Create outcome-linked version for learning"""
        return DecisionWithOutcome(
            decision=self,
            success=success,
            outcome_metrics=metrics,
            outcome_timestamp=datetime.now(timezone.utc),
        )


@dataclass
class DecisionWithOutcome:
    """
    Decision paired with its outcome for learning.

    This is used in Iteration 2+ for data-driven policy learning.
    """

    decision: MathDecision
    success: bool
    outcome_metrics: Dict[str, float]  # e.g., {"mrr": 0.85, "latency_ms": 45}
    outcome_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_training_example(self) -> Dict[str, Any]:
        """Convert to format suitable for policy training"""
        return {
            "features": (
                self.decision.features_used.to_dict()
                if self.decision.features_used
                else {}
            ),
            "action": {
                "level": self.decision.selected_level.value,
                "strategy": self.decision.strategy_id,
            },
            "reward": self._calculate_reward(),
        }

    def _calculate_reward(self) -> float:
        """Calculate reward for RL (Iteration 3)"""
        # Simple reward: success + quality bonus - cost penalty
        base_reward = 1.0 if self.success else 0.0
        quality_bonus = self.outcome_metrics.get("mrr", 0.0) * 0.5
        cost_penalty = self.decision.selected_level.cost_multiplier * 0.1
        return base_reward + quality_bonus - cost_penalty
