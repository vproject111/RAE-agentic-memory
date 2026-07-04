"""
Policy v2 - Data-driven level selection

Implements weighted feature scoring for intelligent level selection.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from .features_v2 import FeaturesV2
from .types import MathLevel, TaskType


@dataclass
class PolicyV2Config:
    """Configuration for Policy v2"""

    # Feature weights for scoring
    feature_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "task_type_score": 0.25,
            "session_length_score": 0.15,
            "memory_count_score": 0.20,
            "entropy_score": 0.18,
            "graph_density_score": 0.12,
            "recent_mrr_score": 0.15,
            "previous_success_score": 0.12,
            "stability_bonus": 0.10,
        }
    )

    # Level selection thresholds
    l2_memory_threshold: int = 30  # Min memories for L2
    l2_entropy_threshold: float = 0.5  # Min entropy for L2
    l3_memory_threshold: int = 200  # Min memories for L3
    l3_session_threshold: int = 10  # Min session length for L3

    # Safety settings
    max_exploration_rate: float = 0.2
    error_rate_threshold: float = 0.1
    consecutive_error_limit: int = 3

    # Quality thresholds
    quality_crisis_threshold: float = 0.2  # Upgrade if MRR < this
    quality_stable_threshold: float = 0.7  # Stay if MRR > this


class PolicyV2:
    """
    Policy v2 - Weighted scoring for level selection.

    Computes a score for each level based on features, then selects
    the highest-scoring level (subject to constraints).
    """

    def __init__(self, config: Optional[PolicyV2Config] = None):
        self.config = config or PolicyV2Config()

    def select_level(self, features: FeaturesV2) -> MathLevel:
        """
        Select the best mathematical level based on features.

        Returns:
            Selected level (L1, L2, or L3)
        """
        # 1. Check hard constraints (budget/latency)
        if features.is_budget_constrained() or features.is_latency_constrained():
            return MathLevel.L1

        # 2. Compute base scores for each level
        scores = self._compute_level_scores(features)

        # 3. Apply task type priors
        scores[MathLevel.L1] += features.get_task_affinity_l1() * 0.3
        scores[MathLevel.L2] += features.get_task_affinity_l2() * 0.3
        scores[MathLevel.L3] += features.get_task_affinity_l3() * 0.3

        # 4. Apply policy rules (modifies scores)
        scores = self._apply_policy_rules(features, scores)

        # 5. Apply safety overrides
        scores = self._apply_safety_overrides(features, scores)

        # 6. Select highest-scoring level
        selected_level = max(scores.items(), key=lambda x: x[1])[0]

        return selected_level

    def _compute_level_scores(self, features: FeaturesV2) -> Dict[MathLevel, float]:
        """
        Compute base scores for each level based on features.

        Each level starts with a base score and gets adjustments based on features.
        """
        derived = features.compute_derived_features()
        w = self.config.feature_weights

        # Initialize scores
        scores = {
            MathLevel.L1: 0.5,  # L1 gets moderate baseline (safe default)
            MathLevel.L2: 0.3,  # L2 starts lower
            MathLevel.L3: 0.1,  # L3 starts very low (high bar)
        }

        # Memory scale influences L2/L3
        memory_scale = derived["memory_scale"]
        scores[MathLevel.L2] += memory_scale * w["memory_count_score"] * 0.5
        scores[MathLevel.L3] += memory_scale * w["memory_count_score"] * 0.7

        # High entropy favors L2 (information theoretic methods)
        entropy_norm = derived["entropy_normalized"]
        if entropy_norm > 0.5:
            scores[MathLevel.L2] += entropy_norm * w["entropy_score"]

        # Long sessions favor L2/L3
        session_scale = derived["session_scale"]
        scores[MathLevel.L2] += session_scale * w["session_length_score"] * 0.6
        scores[MathLevel.L3] += session_scale * w["session_length_score"] * 0.8

        # Graph connectivity favors L2/L3
        if derived["has_graph"]:
            scores[MathLevel.L2] += (
                features.graph_connectivity * w["graph_density_score"]
            )
            scores[MathLevel.L3] += (
                features.graph_connectivity * w["graph_density_score"] * 0.8
            )

        # Recent quality influences scores
        if features.recent_mrr > 0.7:
            # High quality - can try more sophisticated methods
            scores[MathLevel.L2] += w["recent_mrr_score"] * 0.5
            scores[MathLevel.L3] += w["recent_mrr_score"] * 0.3
        elif features.recent_mrr < 0.3:
            # Low quality - stick to L1 or try L2 for improvement
            scores[MathLevel.L1] += w["recent_mrr_score"] * 0.4
            scores[MathLevel.L2] += w["recent_mrr_score"] * 0.6  # Try L2 to improve

        # Previous level success
        if features.previous_level and features.previous_level_success:
            # Bonus for sticking with what works
            if features.previous_level == MathLevel.L1.value:
                scores[MathLevel.L1] += w["stability_bonus"]
            elif features.previous_level == MathLevel.L2.value:
                scores[MathLevel.L2] += w["stability_bonus"]
            elif features.previous_level == MathLevel.L3.value:
                scores[MathLevel.L3] += w["stability_bonus"]

        return scores

    def _apply_policy_rules(
        self,
        features: FeaturesV2,
        scores: Dict[MathLevel, float],
    ) -> Dict[MathLevel, float]:
        """
        Apply policy rules that modify scores.

        Rules are prioritized and can significantly adjust scores.
        """
        derived = features.compute_derived_features()

        # Rule 1: First turn should be fast
        if derived["first_turn"]:
            scores[MathLevel.L1] += 0.5
            scores[MathLevel.L2] -= 0.2
            scores[MathLevel.L3] -= 0.4

        # Rule 2: Quality crisis - upgrade to try improving
        if features.recent_mrr < self.config.quality_crisis_threshold:
            scores[MathLevel.L2] += 0.4
            scores[MathLevel.L3] += 0.2

        # Rule 3: Quality improving - don't change
        if derived["quality_improving"] and derived["level_stable"]:
            # Strong stability bonus
            if features.previous_level == MathLevel.L1.value:
                scores[MathLevel.L1] += 0.6
            elif features.previous_level == MathLevel.L2.value:
                scores[MathLevel.L2] += 0.6
            elif features.previous_level == MathLevel.L3.value:
                scores[MathLevel.L3] += 0.6

        # Rule 4: High entropy needs information-theoretic methods
        if derived["entropy_normalized"] > 0.7:
            scores[MathLevel.L2] += 0.3
            scores[MathLevel.L1] -= 0.2

        # Rule 5: Deep reflection needs sophistication
        if features.task_type == TaskType.REFLECTION_DEEP:
            scores[MathLevel.L2] += 0.4
            scores[MathLevel.L3] += 0.5
            scores[MathLevel.L1] -= 0.3

        # Rule 6: Simple tasks stay simple
        if features.task_type in [TaskType.MEMORY_STORE, TaskType.CONTEXT_SELECT]:
            scores[MathLevel.L1] += 0.4
            scores[MathLevel.L2] -= 0.2
            scores[MathLevel.L3] -= 0.4

        # Rule 7: Needs reflection - might benefit from L3
        if derived["needs_reflection"]:
            scores[MathLevel.L3] += 0.3

        return scores

    def _apply_safety_overrides(
        self,
        features: FeaturesV2,
        scores: Dict[MathLevel, float],
    ) -> Dict[MathLevel, float]:
        """
        Apply safety overrides that can block levels.

        These are hard constraints that prevent unsafe selections.
        """
        # Override 1: L2 requires minimum memories
        if features.memory_count < self.config.l2_memory_threshold:
            scores[MathLevel.L2] = -1.0  # Block L2

        # Override 2: L3 requires significant memories
        if features.memory_count < self.config.l3_memory_threshold:
            scores[MathLevel.L3] = -1.0  # Block L3

        # Override 3: L3 requires session history
        if features.session_length < self.config.l3_session_threshold:
            scores[MathLevel.L3] = -1.0  # Block L3

        # Override 4: High error rate - downgrade
        if features.error_rate_recent > self.config.error_rate_threshold:
            scores[MathLevel.L2] -= 0.5
            scores[MathLevel.L3] -= 1.0

        # Override 5: Tight budgets - force L1
        derived = features.compute_derived_features()
        if derived["budget_tight"] or derived["latency_tight"]:
            scores[MathLevel.L1] += 1.0
            scores[MathLevel.L2] = -1.0
            scores[MathLevel.L3] = -1.0

        return scores

    def explain_decision(
        self,
        features: FeaturesV2,
        selected_level: MathLevel,
        scores: Dict[MathLevel, float],
    ) -> str:
        """
        Generate human-readable explanation for the decision.

        Args:
            features: Input features
            selected_level: Selected level
            scores: Computed scores

        Returns:
            Explanation string
        """
        explanation_parts = []

        # Header
        explanation_parts.append(
            f"Selected {selected_level.value} ({selected_level.description})"
        )

        # Scores
        scores_str = ", ".join(
            [f"{level.value}={score:.2f}" for level, score in scores.items()]
        )
        explanation_parts.append(f"Scores: [{scores_str}]")

        # Key factors
        factors = []

        if features.is_budget_constrained():
            factors.append("budget constrained")
        if features.is_latency_constrained():
            factors.append("latency constrained")

        if features.memory_count < 30:
            factors.append("few memories")
        elif features.memory_count > 200:
            factors.append("many memories")

        if features.recent_mrr < 0.3:
            factors.append("quality crisis")
        elif features.recent_mrr > 0.7:
            factors.append("high quality")

        if features.task_type == TaskType.REFLECTION_DEEP:
            factors.append("deep reflection")
        elif features.task_type in [TaskType.MEMORY_STORE, TaskType.MEMORY_RETRIEVE]:
            factors.append(f"{features.task_type.value}")

        if factors:
            explanation_parts.append(f"Factors: {', '.join(factors)}")

        return " | ".join(explanation_parts)
