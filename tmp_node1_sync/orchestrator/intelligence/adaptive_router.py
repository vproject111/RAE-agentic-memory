"""Adaptive model router that learns from historical performance.

Uses performance analytics to make intelligent routing decisions,
adapting based on past successes and failures.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from orchestrator.adapters.base import TaskComplexity, TaskRisk
from orchestrator.core.model_router_v2 import ModelRouterV2, RoutingDecision
from orchestrator.providers import ProviderRegistry

from .analytics import PerformanceAnalytics
from .performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Strategy for adaptive routing."""

    BASELINE = "baseline"  # Use standard routing rules
    PERFORMANCE = "performance"  # Optimize for success rate
    COST = "cost"  # Optimize for cost
    BALANCED = "balanced"  # Balance performance and cost
    LEARNING = "learning"  # Continuously learn and adapt


@dataclass
class LearningConfig:
    """Configuration for learning-based routing."""

    # Learning parameters
    min_samples: int = 5  # Minimum samples needed to trust historical data
    success_weight: float = 0.7  # Weight for success rate (0-1)
    cost_weight: float = 0.3  # Weight for cost optimization (0-1)

    # Exploration vs exploitation
    exploration_rate: float = 0.1  # Probability of trying non-optimal models

    # Confidence thresholds
    min_confidence: float = 0.6  # Minimum confidence to use historical data
    fallback_to_baseline: bool = True  # Fall back to baseline if confidence is low


class AdaptiveModelRouter(ModelRouterV2):
    """Intelligent router that learns from historical performance.

    Extends ModelRouterV2 with learning capabilities:
    - Uses performance analytics to inform decisions
    - Adapts routing based on past successes/failures
    - Balances exploration (trying new models) with exploitation (using best known models)
    - Supports multiple routing strategies
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        tracker: PerformanceTracker,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        config: Optional[LearningConfig] = None,
    ):
        """Initialize adaptive router.

        Args:
            registry: Provider registry
            tracker: Performance tracker with historical data
            strategy: Routing strategy to use
            config: Learning configuration
        """
        super().__init__(registry)

        self.tracker = tracker
        self.analytics = PerformanceAnalytics(tracker)
        self.strategy = strategy
        self.config = config or LearningConfig()

        logger.info(f"Initialized adaptive router with strategy: {strategy.value}")

    def _should_explore(self) -> bool:
        """Decide whether to explore (try new models) or exploit (use best known).

        Returns:
            True if should explore
        """
        import random

        return random.random() < self.config.exploration_rate

    def _get_historical_choice(
        self, task_area: str, task_risk: TaskRisk, role: str
    ) -> Optional[RoutingDecision]:
        """Get routing decision based on historical data.

        Args:
            task_area: Task area
            task_risk: Risk level
            role: Role ('planner' or 'implementer')

        Returns:
            Routing decision or None if insufficient data
        """
        risk_str = task_risk.value

        # Get task pattern analysis
        pattern = self.analytics.analyze_task_pattern(
            task_area, risk_str, min_samples=self.config.min_samples
        )

        if not pattern:
            logger.debug(
                f"Insufficient historical data for {task_area}/{risk_str}/{role} "
                f"- falling back to baseline"
            )
            return None

        # Get best performing model for this task type
        if role == "planner" and pattern.best_planner:
            model_id, success_rate = pattern.best_planner
        elif role == "implementer" and pattern.best_implementer:
            model_id, success_rate = pattern.best_implementer
        else:
            return None

        # Check confidence
        confidence = success_rate * (
            pattern.total_attempts / (pattern.total_attempts + 10)
        )

        if confidence < self.config.min_confidence:
            logger.debug(
                f"Low confidence ({confidence:.2f}) for {model_id} "
                f"- falling back to baseline"
            )
            return None

        # Get model info
        model_info = self.registry.get_model_info(model_id)
        if not model_info:
            logger.warning(f"Historical model {model_id} not found in registry")
            return None

        # Calculate estimated cost (use historical average)
        estimated_cost = pattern.avg_cost

        # Build rationale
        rationale = (
            f"Historical best for {task_area}/{risk_str} "
            f"({success_rate:.1%} success over {pattern.total_attempts} tasks)"
        )

        return RoutingDecision(
            model_id=model_id,
            provider=model_info.provider,
            model_info=model_info,
            rationale=rationale,
            estimated_cost=estimated_cost,
            confidence=confidence,
        )

    def _apply_strategy(
        self,
        baseline: RoutingDecision,
        historical: Optional[RoutingDecision],
        task_area: str,
        task_risk: TaskRisk,
    ) -> RoutingDecision:
        """Apply routing strategy to choose between baseline and historical.

        Args:
            baseline: Decision from baseline routing rules
            historical: Decision from historical data (may be None)
            task_area: Task area
            task_risk: Risk level

        Returns:
            Final routing decision
        """
        # Strategy: BASELINE - always use baseline
        if self.strategy == RoutingStrategy.BASELINE:
            return baseline

        # No historical data available
        if not historical:
            return baseline

        # Strategy: PERFORMANCE - always use historical best
        if self.strategy == RoutingStrategy.PERFORMANCE:
            return historical

        # Strategy: COST - use cheaper option
        if self.strategy == RoutingStrategy.COST:
            if historical.estimated_cost < baseline.estimated_cost:
                return historical
            return baseline

        # Strategy: BALANCED - weighted decision
        if self.strategy == RoutingStrategy.BALANCED:
            # Get historical performance metrics
            pattern = self.analytics.analyze_task_pattern(
                task_area, task_risk.value, min_samples=self.config.min_samples
            )

            if not pattern:
                return baseline

            # Calculate scores
            # Historical score: success_weight * success_rate - cost_weight * normalized_cost
            norm_cost_hist = historical.estimated_cost / max(pattern.max_cost, 0.001)
            hist_score = (
                self.config.success_weight * pattern.success_rate
                - self.config.cost_weight * norm_cost_hist
            )

            # Baseline score: assume 0.8 success rate (conservative)
            norm_cost_base = baseline.estimated_cost / max(pattern.max_cost, 0.001)
            base_score = (
                self.config.success_weight * 0.8
                - self.config.cost_weight * norm_cost_base
            )

            if hist_score > base_score:
                return historical
            return baseline

        # Strategy: LEARNING - explore/exploit
        if self.strategy == RoutingStrategy.LEARNING:
            if self._should_explore():
                logger.debug("Exploration: using baseline routing")
                return baseline
            else:
                logger.debug("Exploitation: using historical best")
                return historical

        # Default: return baseline
        return baseline

    def choose_planner(
        self,
        task_risk: TaskRisk,
        task_area: str,
        task_complexity: TaskComplexity,
    ) -> RoutingDecision:
        """Choose planner model with adaptive learning.

        Args:
            task_risk: Risk level
            task_area: Task area
            task_complexity: Complexity level

        Returns:
            Routing decision
        """
        # Get baseline decision
        baseline = super().choose_planner(task_risk, task_area, task_complexity)

        # Get historical recommendation
        historical = self._get_historical_choice(task_area, task_risk, role="planner")

        # Apply strategy
        decision = self._apply_strategy(baseline, historical, task_area, task_risk)

        logger.info(
            f"Planner routing: {decision.model_info.display_name} "
            f"(strategy={self.strategy.value}, confidence={decision.confidence:.2f})"
        )

        return decision

    def choose_implementer(
        self,
        step_risk: TaskRisk,
        step_complexity: TaskComplexity,
        step_type: str,
        step_area: str,
    ) -> RoutingDecision:
        """Choose implementer model with adaptive learning.

        Args:
            step_risk: Risk level
            step_complexity: Complexity level
            step_type: Step type
            step_area: Task area

        Returns:
            Routing decision
        """
        # Get baseline decision
        baseline = super().choose_implementer(
            step_risk, step_complexity, step_type, step_area
        )

        # Get historical recommendation
        historical = self._get_historical_choice(
            step_area, step_risk, role="implementer"
        )

        # Apply strategy
        decision = self._apply_strategy(baseline, historical, step_area, step_risk)

        logger.info(
            f"Implementer routing: {decision.model_info.display_name} "
            f"(strategy={self.strategy.value}, confidence={decision.confidence:.2f})"
        )

        return decision

    def get_learning_summary(self) -> dict:
        """Get summary of learning progress.

        Returns:
            Dictionary with learning statistics
        """
        stats = self.tracker.get_statistics()

        # Get provider comparison
        provider_comp = self.analytics.get_provider_comparison()

        # Get optimization opportunities
        opportunities = self.analytics.identify_optimization_opportunities()

        return {
            "strategy": self.strategy.value,
            "total_executions": stats["total_tasks"],
            "overall_success_rate": stats["success_rate"],
            "total_cost": stats["total_cost"],
            "provider_performance": provider_comp,
            "optimization_opportunities": len(opportunities),
            "top_opportunities": opportunities[:3] if opportunities else [],
        }

    def adapt_strategy(self):
        """Adapt routing strategy based on performance.

        Analyzes recent performance and adjusts strategy if needed.
        """
        # Get recent records (last 50)
        recent = self.tracker.get_recent_records(limit=50)

        if len(recent) < 20:
            logger.info("Insufficient data to adapt strategy")
            return

        # Calculate recent success rate
        successful = len([r for r in recent if r.outcome.value == "success"])
        recent_success_rate = successful / len(recent)

        logger.info(f"Recent performance: {recent_success_rate:.1%} success rate")

        # If performance is poor, increase exploration
        if recent_success_rate < 0.7 and self.strategy == RoutingStrategy.LEARNING:
            old_rate = self.config.exploration_rate
            self.config.exploration_rate = min(0.3, self.config.exploration_rate * 1.5)
            logger.info(
                f"Increasing exploration rate: {old_rate:.2f} → {self.config.exploration_rate:.2f}"
            )

        # If performance is good, decrease exploration
        elif recent_success_rate > 0.9 and self.strategy == RoutingStrategy.LEARNING:
            old_rate = self.config.exploration_rate
            self.config.exploration_rate = max(0.05, self.config.exploration_rate * 0.8)
            logger.info(
                f"Decreasing exploration rate: {old_rate:.2f} → {self.config.exploration_rate:.2f}"
            )
