"""
Reward calculation for Policy v2

Multi-objective reward function balancing quality, cost, and stability.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .decision import DecisionWithOutcome, MathDecision
from .types import MathLevel


@dataclass
class RewardConfig:
    """Configuration for reward calculation"""

    # Component weights
    w_quality: float = 1.0  # Quality is most important
    w_cost: float = 0.3  # Moderate cost penalty
    w_stability: float = 0.2  # Light stability preference

    # Quality sub-weights
    quality_weights: Optional[Dict[str, float]] = None

    # Stability sub-weights
    stability_weights: Optional[Dict[str, float]] = None

    # Catastrophic penalties
    penalties: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if self.quality_weights is None:
            self.quality_weights = {
                "mrr": 0.35,
                "hit_rate": 0.30,
                "precision": 0.15,
                "orr": 0.20,
            }

        if self.stability_weights is None:
            self.stability_weights = {
                "memory_drift": 0.4,
                "structural_drift": 0.3,
                "level_churn": 0.3,
            }

        if self.penalties is None:
            self.penalties = {
                "zero_mrr": 2.0,
                "error": 3.0,
                "budget_violation": 5.0,
                "quality_collapse": 1.5,
                "timeout": 2.5,
            }


class RewardCalculator:
    """
    Calculates rewards for decision-outcome pairs.

    Reward range: approximately -10.0 to +1.0
    - Positive: Good decision
    - Negative: Bad decision (penalties applied)
    - Near 0: Neutral (cost offset quality)
    """

    def __init__(self, config: Optional[RewardConfig] = None):
        self.config = config or RewardConfig()

    def calculate(
        self,
        decision_with_outcome: DecisionWithOutcome,
        baseline_mrr: float = 0.5,
    ) -> float:
        """
        Calculate reward for a decision-outcome pair.

        Args:
            decision_with_outcome: Decision with outcome metrics
            baseline_mrr: Baseline MRR for quality collapse detection

        Returns:
            Reward score
        """
        # Quality component (0.0 to 1.0)
        quality = self._calculate_quality(decision_with_outcome.outcome_metrics)

        # Cost component (0.0 to ~2.0 typically)
        cost = self._calculate_cost(
            decision_with_outcome.decision, decision_with_outcome.outcome_metrics
        )

        # Stability component (0.0 to 1.0)
        stability = self._calculate_stability(decision_with_outcome.outcome_metrics)

        # Catastrophic penalties (0.0 to ~10.0)
        penalty = self._calculate_penalty(decision_with_outcome, baseline_mrr)

        # Weighted combination
        reward = (
            self.config.w_quality * quality
            - self.config.w_cost * cost
            - self.config.w_stability * stability
            - penalty
        )

        return reward

    def _calculate_quality(self, metrics: Dict) -> float:
        """Calculate quality component from outcome metrics"""
        assert self.config.quality_weights is not None
        w = self.config.quality_weights

        # Extract metrics with defaults
        mrr = metrics.get("mrr", 0.0)
        hit_rate = metrics.get("hit_rate_5", metrics.get("hit_rate", {}).get("@5", 0.0))
        precision = metrics.get(
            "precision_5", metrics.get("precision", {}).get("@5", 0.0)
        )
        orr = metrics.get("orr", metrics.get("optimal_retrieval_ratio", 0.0))

        quality = (
            w["mrr"] * mrr
            + w["hit_rate"] * hit_rate
            + w["precision"] * precision
            + w["orr"] * orr
        )

        return float(quality)

    def _calculate_cost(self, decision: MathDecision, metrics: Dict) -> float:
        """Calculate cost component"""
        # Base cost from level multiplier
        level_multipliers = {
            MathLevel.L1: 1.0,
            MathLevel.L2: 2.5,
            MathLevel.L3: 4.0,
        }
        base_cost = level_multipliers.get(decision.selected_level, 1.0) * 0.1

        # Latency penalty
        latency_penalty = 0.0
        if decision.features_used and decision.features_used.latency_budget_ms:
            actual_latency = metrics.get("latency_ms", 0)
            budget = decision.features_used.latency_budget_ms

            if actual_latency > budget:
                # Exponential penalty for exceeding budget
                ratio = actual_latency / budget
                latency_penalty = (ratio - 1.0) ** 2

        return base_cost + latency_penalty

    def _calculate_stability(self, metrics: Dict) -> float:
        """Calculate stability penalty"""
        assert self.config.stability_weights is not None
        w = self.config.stability_weights

        # Memory drift (0.0 = stable, 1.0 = high drift)
        memory_drift = metrics.get("memory_drift_index", 0.0)

        # Structural drift (0.0 = stable, 1.0 = high drift)
        structural_drift = metrics.get("structural_drift", 0.0)

        # Level churn is calculated separately from history
        level_churn = 0.0  # TODO: Calculate from decision history

        stability_penalty = (
            w["memory_drift"] * memory_drift
            + w["structural_drift"] * structural_drift
            + w["level_churn"] * level_churn
        )

        return float(stability_penalty)

    def _calculate_penalty(
        self, decision_with_outcome: DecisionWithOutcome, baseline_mrr: float
    ) -> float:
        """Calculate catastrophic failure penalties"""
        assert self.config.penalties is not None
        penalty = 0.0
        p = self.config.penalties

        # Zero MRR = complete failure
        if decision_with_outcome.outcome_metrics.get("mrr", 0.0) == 0.0:
            penalty += p["zero_mrr"]

        # System error or timeout
        if not decision_with_outcome.success:
            penalty += p["error"]

        # Budget violation (if tracked)
        budget_exceeded = decision_with_outcome.outcome_metrics.get(
            "budget_exceeded", False
        )
        if budget_exceeded:
            penalty += p["budget_violation"]

        # Quality collapse (MRR dropped > 50% from baseline)
        mrr = decision_with_outcome.outcome_metrics.get("mrr", 0.0)
        if baseline_mrr > 0 and mrr < baseline_mrr * 0.5:
            penalty += p["quality_collapse"]

        # Timeout (if tracked)
        timed_out = decision_with_outcome.outcome_metrics.get("timed_out", False)
        if timed_out:
            penalty += p["timeout"]

        return penalty

    def calculate_batch(
        self,
        decisions_with_outcomes: List[DecisionWithOutcome],
    ) -> List[float]:
        """Calculate rewards for a batch of decisions"""
        # Calculate baseline MRR from successful outcomes
        successful_mrrs = [
            d.outcome_metrics.get("mrr", 0.0)
            for d in decisions_with_outcomes
            if d.success
        ]
        baseline_mrr = (
            sum(successful_mrrs) / len(successful_mrrs) if successful_mrrs else 0.5
        )

        return [self.calculate(d, baseline_mrr) for d in decisions_with_outcomes]
