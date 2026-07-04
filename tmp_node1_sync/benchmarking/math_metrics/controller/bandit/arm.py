"""
Arm representation for Multi-Armed Bandit

An arm represents a specific (level, strategy) combination that the bandit can choose.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..types import MathLevel


@dataclass
class Arm:
    """
    Represents a single arm in the multi-armed bandit.

    An arm is a (level, strategy) pair that can be pulled (selected).
    Each arm maintains statistics about its performance across different contexts.

    Attributes:
        level: Math level (L1, L2, or L3)
        strategy: Strategy within that level
        arm_id: Unique identifier (auto-generated)

        # Global statistics (all contexts)
        pulls: Total number of times this arm was selected
        total_reward: Cumulative reward from all pulls

        # Context-specific statistics (81 context buckets)
        context_pulls: Dict mapping context_id -> pull count
        context_rewards: Dict mapping context_id -> cumulative reward

        # Metadata
        last_pulled: Timestamp of last pull
        confidence: Confidence in this arm's estimates [0, 1]
    """

    level: MathLevel
    strategy: str
    arm_id: str = field(default="")

    # Global statistics
    pulls: int = 0
    total_reward: float = 0.0

    # Context-specific statistics
    context_pulls: Dict[int, int] = field(default_factory=dict)
    context_rewards: Dict[int, float] = field(default_factory=dict)

    # Metadata
    last_pulled: Optional[float] = None
    confidence: float = 0.0

    def __post_init__(self):
        """Generate arm_id if not provided"""
        if not self.arm_id:
            self.arm_id = f"{self.level.value}:{self.strategy}"

    def mean_reward(self, context_id: Optional[int] = None) -> float:
        """
        Calculate mean reward for this arm.

        Args:
            context_id: If provided, return context-specific mean

        Returns:
            Mean reward (0.0 if never pulled)
        """
        if context_id is not None:
            # Context-specific mean
            pulls = self.context_pulls.get(context_id, 0)
            if pulls == 0:
                return 0.0
            total = self.context_rewards.get(context_id, 0.0)
            return total / pulls
        else:
            # Global mean
            if self.pulls == 0:
                return 0.0
            return self.total_reward / self.pulls

    def ucb_score(
        self,
        total_pulls: int,
        c: float = 1.0,
        context_id: Optional[int] = None,
        context_bonus: float = 0.0,
    ) -> float:
        """
        Calculate UCB (Upper Confidence Bound) score for this arm.

        UCB formula: mean_reward + c * sqrt(ln(N) / n) + context_bonus

        Args:
            total_pulls: Total pulls across all arms (N)
            c: Confidence parameter (higher = more exploration)
            context_id: Context for context-specific UCB
            context_bonus: Additional bonus for context match

        Returns:
            UCB score (higher = should be selected)
        """
        import math

        # Get arm-specific pulls
        if context_id is not None:
            arm_pulls = self.context_pulls.get(context_id, 0)
        else:
            arm_pulls = self.pulls

        # If never pulled, return infinity (explore first)
        if arm_pulls == 0:
            return float("inf")

        # Calculate UCB
        mean = self.mean_reward(context_id)
        exploration_bonus = c * math.sqrt(math.log(max(total_pulls, 1)) / arm_pulls)

        return mean + exploration_bonus + context_bonus

    def update(
        self,
        reward: float,
        context_id: Optional[int] = None,
        timestamp: Optional[float] = None,
    ):
        """
        Update arm statistics with a new reward observation.

        Args:
            reward: Reward received from pulling this arm
            context_id: Context in which arm was pulled
            timestamp: When the arm was pulled
        """
        # Update global statistics
        self.pulls += 1
        self.total_reward += reward

        # Update context-specific statistics
        if context_id is not None:
            self.context_pulls[context_id] = self.context_pulls.get(context_id, 0) + 1
            self.context_rewards[context_id] = (
                self.context_rewards.get(context_id, 0.0) + reward
            )

        # Update metadata
        if timestamp is not None:
            self.last_pulled = timestamp

        # Update confidence (more pulls = higher confidence)
        # Asymptotic confidence: 1 - 1/(1 + pulls)
        self.confidence = 1.0 - 1.0 / (1.0 + self.pulls)

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "arm_id": self.arm_id,
            "level": self.level.value,
            "strategy": self.strategy,
            "pulls": self.pulls,
            "total_reward": self.total_reward,
            "mean_reward": self.mean_reward(),
            "context_pulls": self.context_pulls,
            "context_rewards": self.context_rewards,
            "last_pulled": self.last_pulled,
            "confidence": self.confidence,
        }

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> "Arm":
        """Deserialize from dictionary"""
        level = MathLevel(data["level"])
        return cls(
            level=level,
            strategy=data["strategy"],
            arm_id=data.get("arm_id", ""),
            pulls=data.get("pulls", 0),
            total_reward=data.get("total_reward", 0.0),
            context_pulls=data.get("context_pulls", {}),
            context_rewards=data.get("context_rewards", {}),
            last_pulled=data.get("last_pulled"),
            confidence=data.get("confidence", 0.0),
        )


def create_default_arms() -> List[Arm]:
    """
    Create the default set of arms for the bandit.

    Returns 9 arms:
    - L1: default, relevance_scoring, importance_scoring
    - L2: default, entropy_minimization, information_bottleneck, mutual_information
    - L3: hybrid_default, weighted_combination

    Returns:
        List of Arm objects
    """
    arms = []

    # L1 arms (3)
    arms.append(Arm(level=MathLevel.L1, strategy="default"))
    arms.append(Arm(level=MathLevel.L1, strategy="relevance_scoring"))
    arms.append(Arm(level=MathLevel.L1, strategy="importance_scoring"))

    # L2 arms (4)
    arms.append(Arm(level=MathLevel.L2, strategy="default"))
    arms.append(Arm(level=MathLevel.L2, strategy="entropy_minimization"))
    arms.append(Arm(level=MathLevel.L2, strategy="information_bottleneck"))
    arms.append(Arm(level=MathLevel.L2, strategy="mutual_information"))

    # L3 arms (2)
    arms.append(Arm(level=MathLevel.L3, strategy="hybrid_default"))
    arms.append(Arm(level=MathLevel.L3, strategy="weighted_combination"))

    return arms
