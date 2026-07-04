"""
MathLayerController - Central controller for math level selection

This is the main entry point for deciding which mathematical level
to use for memory operations. It provides:
- Rule-based level selection (Iteration 1)
- Standardized decision format
- Comprehensive logging for future learning
- Integration with existing MathematicalDecisionEngine
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from ..decision_engine import MathematicalDecisionEngine
from .bandit import BanditConfig, BanditMonitor, MultiArmedBandit
from .config import MathControllerConfig
from .context import TaskContext
from .decision import DecisionWithOutcome, MathDecision
from .features import Features
from .features_v2 import FeaturesV2
from .policy_v2 import PolicyV2, PolicyV2Config
from .types import MathLevel, TaskType

logger = structlog.get_logger(__name__)


class FeatureExtractor:
    """
    Extracts features from TaskContext for decision making.

    Centralizes all feature extraction logic to ensure consistency
    between training and inference (important for Iteration 2+).
    """

    def __init__(self, decision_engine: Optional[MathematicalDecisionEngine] = None):
        """
        Initialize extractor.

        Args:
            decision_engine: Optional decision engine for metric calculations
        """
        self.decision_engine = decision_engine or MathematicalDecisionEngine()

    def extract(self, context: TaskContext) -> Features:
        """
        Extract features from task context.

        Args:
            context: Task context with memory state and metadata

        Returns:
            Features dataclass for decision making
        """
        features = Features(task_type=context.task_type)

        # Extract memory state features
        if context.memory_snapshot:
            features.memory_count = context.memory_snapshot.num_memories

            # Calculate graph density
            num_edges = len(context.memory_snapshot.graph_edges)
            max_edges = features.memory_count * (features.memory_count - 1) / 2
            features.graph_density = num_edges / max_edges if max_edges > 0 else 0.0

        # Extract session features
        features.session_length = context.turn_number

        # Extract budget constraints
        features.cost_budget = context.budget_constraints.get("max_cost_usd")
        features.latency_budget_ms = context.budget_constraints.get("max_latency_ms")

        # Calculate metrics if we have snapshots
        if context.memory_snapshot and len(context.memory_snapshot.graph_edges) > 0:
            # Use decision engine metrics
            from ..structure_metrics import (
                GraphConnectivityScore,
                GraphEntropyMetric,
                SemanticCoherenceScore,
            )

            entropy_metric = GraphEntropyMetric()
            gcs_metric = GraphConnectivityScore()
            scs_metric = SemanticCoherenceScore()

            features.memory_entropy = entropy_metric.calculate(
                num_nodes=context.memory_snapshot.num_memories,
                edges=context.memory_snapshot.graph_edges,
            )
            features.recent_gcs = gcs_metric.calculate(
                num_nodes=context.memory_snapshot.num_memories,
                edges=context.memory_snapshot.graph_edges,
            )
            features.recent_scs = scs_metric.calculate(context.memory_snapshot)

        # Calculate MRR from query results
        if context.query_results:
            from ..policy_metrics import OptimalRetrievalRatio

            orr_metric = OptimalRetrievalRatio()
            features.recent_mrr = orr_metric.calculate(context.query_results, k=5)

        return features


class SafeAdaptationGuard:
    """
    Guard mechanism for safe policy adaptation.

    Ensures that changes to decision rules (adaptations) are validated
    in a sandbox environment before being promoted to permanent rules.
    Prevents instability from rapid, unchecked adaptation.
    """

    def __init__(self):
        self.sandbox_adaptations: Dict[str, Any] = {}  # Temporary changes
        self.permanent_adaptations: Dict[str, Any] = {}  # Validated changes
        self.validation_counts: Dict[str, int] = {}  # Count of successful validations

    def propose_adaptation(self, rule_id: str, new_rule: Any) -> None:
        """
        Propose a new adaptation (add to sandbox).

        Args:
            rule_id: Identifier for the rule
            new_rule: The new rule value/object
        """
        self.sandbox_adaptations[rule_id] = new_rule
        self.validation_counts[rule_id] = 0  # Reset validation count for new proposal

    def validate_adaptation(self, rule_id: str, success: bool) -> bool:
        """
        Validate a proposed adaptation based on outcome.

        Args:
            rule_id: Identifier for the rule
            success: Whether the adaptation led to a successful outcome

        Returns:
            True if adaptation was promoted to permanent, False otherwise
        """
        if rule_id not in self.sandbox_adaptations:
            return False

        if success:
            self.validation_counts[rule_id] += 1
            # Promote if validated enough times (e.g. 3)
            if self.validation_counts[rule_id] >= 3:
                self.permanent_adaptations[rule_id] = self.sandbox_adaptations[rule_id]
                # Cleanup sandbox
                del self.sandbox_adaptations[rule_id]
                del self.validation_counts[rule_id]
                return True
        else:
            # Penalize or remove on failure
            # For now, aggressive pruning: one failure removes the proposal
            del self.sandbox_adaptations[rule_id]
            del self.validation_counts[rule_id]

        return False

    def get_active_rule(self, rule_id: str, default: Any = None) -> Any:
        """
        Get the currently active rule (permanent takes precedence, unless testing).

        Args:
            rule_id: Rule identifier
            default: Default value if no rule exists

        Returns:
            The active rule value
        """
        # In a real system, we might probabilisticly return sandbox rules for testing
        # Here we return permanent if exists, else sandbox (testing phase), else default
        if rule_id in self.permanent_adaptations:
            return self.permanent_adaptations[rule_id]
        elif rule_id in self.sandbox_adaptations:
            return self.sandbox_adaptations[rule_id]
        return default


class MathLayerController:
    """
    Central controller for math level selection in RAE.

    This controller is responsible for:
    1. Deciding which math level (L1, L2, L3) to use
    2. Selecting specific strategies within each level
    3. Configuring parameters for the selected strategy
    4. Logging decisions for future learning

    Iteration 1 Focus:
    - Clean, rule-based decision logic
    - Standardized MathDecision output
    - Comprehensive logging
    - Integration with existing systems

    Usage:
        controller = MathLayerController()

        context = TaskContext(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_snapshot=snapshot,
        )

        decision = controller.decide(context)

        print(f"Using {decision.selected_level} with {decision.strategy_id}")
        print(f"Reason: {decision.explanation}")
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[MathControllerConfig] = None,
    ):
        """
        Initialize the controller.

        Args:
            config_path: Path to YAML config file
            config: Config object (takes precedence over config_path)
        """
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            from .config import load_config

            self.config = load_config(config_path)
        else:
            self.config = MathControllerConfig()  # Default config

        # Initialize components
        self.decision_engine = MathematicalDecisionEngine(
            thresholds=self.config.thresholds
        )
        self.feature_extractor = FeatureExtractor(self.decision_engine)

        # Initialize Policy v2 (if configured)
        self.policy_version = getattr(self.config, "policy_version", 1)
        self.policy_v2 = None
        if self.policy_version >= 2:
            policy_v2_config = PolicyV2Config()
            # Transfer thresholds from main config
            policy_v2_config.l2_memory_threshold = int(
                self.config.thresholds.get("l2_memory_threshold", 30)
            )
            policy_v2_config.l2_entropy_threshold = self.config.thresholds.get(
                "l2_entropy_threshold", 0.7
            )
            policy_v2_config.l3_memory_threshold = int(
                self.config.thresholds.get("l3_memory_threshold", 500)
            )
            policy_v2_config.l3_session_threshold = int(
                self.config.thresholds.get("l3_session_threshold", 10)
            )
            self.policy_v2 = PolicyV2(policy_v2_config)

        # Initialize Bandit (if configured and policy v2 is active)
        self.bandit_enabled = getattr(self.config, "bandit_enabled", False)
        self.bandit: Optional[MultiArmedBandit] = None
        self.bandit_monitor: Optional[BanditMonitor] = None
        if self.bandit_enabled and self.policy_version >= 2:
            bandit_config = self._create_bandit_config()
            self.bandit = MultiArmedBandit(config=bandit_config)
            self.bandit_monitor = BanditMonitor(bandit=self.bandit)

        # Decision history (in-memory, for recent decisions)
        self.decision_history: List[MathDecision] = []
        self._max_history = 1000

        # Previous decision (for stability)
        self._previous_decision: Optional[MathDecision] = None

        logger.info(
            "math_layer_controller_initialized",
            profile=self.config.profile,
            default_level=self.config.default_level.value,
            policy_version=self.policy_version,
            bandit_enabled=self.bandit_enabled,
        )

    def decide(self, context: TaskContext) -> MathDecision:
        """
        Make a decision about which math level to use.

        This is the main entry point for the controller.

        Decision Flow with Bandit (if enabled):
        1. Extract features and convert to FeaturesV2
        2. Get baseline decision from Policy v2
        3. Check safety (degradation, exploration limits)
        4. If safe: use bandit to select arm (level, strategy)
        5. Monitor records the decision

        Args:
            context: Task context with all relevant information

        Returns:
            MathDecision with selected level, strategy, params, and explanation
        """
        # Extract features
        features = self.feature_extractor.extract(context)

        # Add history to features
        if self._previous_decision:
            features.previous_level = self._previous_decision.selected_level
            # Note: previous_level_success would be set after outcome is known

        # Convert to FeaturesV2 if needed (for bandit and policy v2)
        if isinstance(features, Features) and not isinstance(features, FeaturesV2):
            features_v2 = FeaturesV2.from_features(features)
            features_v2.consecutive_same_level = self._get_consecutive_same_level()
            features_v2.is_first_turn = features.session_length == 0
        else:
            features_v2 = features

        # Bandit decision flow (if enabled)
        if self.bandit and self.bandit_monitor:
            level, strategy, explanation = self._decide_with_bandit(features_v2)
        else:
            # Standard decision flow
            level = self.select_level(features)
            strategy = self.select_strategy(level, features)
            explanation = self._build_explanation(level, strategy, features)

        # Configure parameters
        params = self.configure_params(level, strategy, features)

        # Create decision
        decision = MathDecision(
            selected_level=level,
            strategy_id=strategy,
            params=params,
            explanation=explanation,
            telemetry_tags=self._build_telemetry_tags(
                level, strategy, features, context
            ),
            features_used=features_v2,
            confidence=self._calculate_confidence(level, features_v2),
        )

        # Log and store
        self.log_decision(decision)
        self._store_decision(decision)

        return decision

    def select_level(self, features: Features) -> MathLevel:
        """
        Select which math level to use based on features.

        Policy v1 (Rule-based):
        1. If budget-constrained -> L1 (cheapest)
        2. If latency-constrained -> L1 (fastest)
        3. If task prefers L2 AND conditions met -> L2
        4. If high-value scenario AND profile allows -> L3
        5. Default to configured default

        Policy v2 (Weighted scoring):
        - Computes scores for each level based on features
        - Applies task type priors and policy rules
        - Selects highest-scoring level

        Args:
            features: Extracted features from context

        Returns:
            Selected MathLevel
        """
        # Use Policy v2 if configured
        if self.policy_version >= 2 and self.policy_v2:
            # Convert to FeaturesV2 if needed
            if isinstance(features, Features) and not isinstance(features, FeaturesV2):
                features_v2 = FeaturesV2.from_features(features)
                # Enhance with historical data
                features_v2.consecutive_same_level = self._get_consecutive_same_level()
                features_v2.is_first_turn = features.session_length == 0
            else:
                features_v2 = features

            level = self.policy_v2.select_level(features_v2)
            logger.debug("level_selection_v2", level=level.value, policy="v2")
            return level

        # Fall back to Policy v1 (original logic)
        # Rule 1: Budget constraint forces L1
        if features.is_budget_constrained():
            logger.debug("level_selection_budget_constrained", level="L1")
            return MathLevel.L1

        # Rule 2: Latency constraint forces L1
        if features.is_latency_constrained():
            logger.debug("level_selection_latency_constrained", level="L1")
            return MathLevel.L1

        # Rule 3: Check if L3 is appropriate (high-value scenarios)
        if self._should_use_l3(features):
            logger.debug("level_selection_high_value", level="L3")
            return MathLevel.L3

        # Rule 4: Check if L2 is appropriate
        if self._should_use_l2(features):
            logger.debug("level_selection_l2_conditions_met", level="L2")
            return MathLevel.L2

        # Rule 5: Use task's preferred level
        preferred = features.task_type.preferred_level
        if self._is_level_allowed(preferred):
            logger.debug("level_selection_task_preferred", level=preferred.value)
            return preferred

        # Default
        return self.config.default_level

    def _get_consecutive_same_level(self) -> int:
        """Get count of consecutive decisions using same level"""
        if not self.decision_history:
            return 0

        count = 0
        last_level = self.decision_history[-1].selected_level

        for decision in reversed(self.decision_history):
            if decision.selected_level == last_level:
                count += 1
            else:
                break

        return count

    def _should_use_l3(self, features: Features) -> bool:
        """Check if L3 (adaptive/hybrid) should be used"""
        # L3 conditions (Iteration 1: conservative)
        if not self._is_level_allowed(MathLevel.L3):
            return False

        # Only use L3 for complex scenarios
        is_complex_task = features.task_type in [
            TaskType.REFLECTION_DEEP,
            TaskType.MEMORY_CONSOLIDATE,
        ]

        # Large memory count suggests need for sophisticated handling
        has_large_memory = features.memory_count > self.config.thresholds.get(
            "l3_memory_threshold", 500
        )

        # Long session suggests established context
        has_long_session = features.session_length > self.config.thresholds.get(
            "l3_session_threshold", 10
        )

        return is_complex_task and (has_large_memory or has_long_session)

    def _should_use_l2(self, features: Features) -> bool:
        """Check if L2 (information-theoretic) should be used"""
        if not self._is_level_allowed(MathLevel.L2):
            return False

        # L2 is good for tasks that benefit from entropy analysis
        l2_preferred_tasks = [
            TaskType.MEMORY_CONSOLIDATE,
            TaskType.REFLECTION_DEEP,
            TaskType.GRAPH_UPDATE,
            TaskType.CONTEXT_SELECT,
        ]

        if features.task_type in l2_preferred_tasks:
            # Use L2 if we have enough data to make it worthwhile
            has_sufficient_data = features.memory_count > self.config.thresholds.get(
                "l2_memory_threshold", 50
            )
            return has_sufficient_data

        # Also use L2 if entropy is high (disorganized memory)
        high_entropy = features.memory_entropy > self.config.thresholds.get(
            "l2_entropy_threshold", 0.7
        )

        return high_entropy and features.memory_count > 20

    def _is_level_allowed(self, level: MathLevel) -> bool:
        """Check if level is allowed in current config"""
        return level in self.config.allowed_levels

    def select_strategy(self, level: MathLevel, features: Features) -> str:
        """
        Select specific strategy within the chosen level.

        Args:
            level: Selected math level
            features: Extracted features

        Returns:
            Strategy identifier string
        """
        self.config.strategies.get(level, ["default"])

        if level == MathLevel.L1:
            # L1 strategies based on task type
            if features.task_type == TaskType.MEMORY_RETRIEVE:
                return "relevance_scoring"
            elif features.task_type == TaskType.MEMORY_STORE:
                return "importance_scoring"
            else:
                return "default"

        elif level == MathLevel.L2:
            # L2 strategies
            if features.memory_entropy > 0.6:
                return "entropy_minimization"
            elif features.task_type == TaskType.CONTEXT_SELECT:
                return "information_bottleneck"
            else:
                return "mutual_information"

        elif level == MathLevel.L3:
            # L3 strategies (Iteration 1: just default)
            return "hybrid_default"

        return "default"

    def configure_params(
        self,
        level: MathLevel,
        strategy: str,
        features: Features,
    ) -> Dict[str, Any]:
        """
        Configure parameters for the selected strategy.

        Args:
            level: Selected math level
            strategy: Selected strategy
            features: Extracted features

        Returns:
            Dictionary of parameters for the strategy
        """
        base_params = self.config.strategy_params.get(strategy, {}).copy()

        # Adjust based on features
        if level == MathLevel.L1:
            base_params.update(
                {
                    "use_recency": True,
                    "recency_weight": self._calculate_recency_weight(features),
                    "importance_threshold": self.config.thresholds.get(
                        "importance_threshold", 0.3
                    ),
                }
            )

        elif level == MathLevel.L2:
            base_params.update(
                {
                    "entropy_target": 0.5,
                    "ib_beta": self._calculate_ib_beta(features),
                    "max_iterations": 100,
                }
            )

        elif level == MathLevel.L3:
            base_params.update(
                {
                    "l1_weight": 0.5,
                    "l2_weight": 0.5,
                    "exploration_rate": (
                        0.1 if self.config.profile == "research" else 0.0
                    ),
                }
            )

        return base_params

    def _calculate_recency_weight(self, features: Features) -> float:
        """Calculate recency weight based on session length"""
        # Longer sessions should weight recency less
        if features.session_length < 5:
            return 0.3
        elif features.session_length < 20:
            return 0.2
        else:
            return 0.1

    def _calculate_ib_beta(self, features: Features) -> float:
        """Calculate Information Bottleneck beta parameter"""
        # Higher entropy -> lower beta (more compression)
        # Lower entropy -> higher beta (preserve more info)
        base_beta = 1.0
        entropy_factor = 1.0 - min(features.memory_entropy, 1.0)
        return base_beta * (0.5 + 0.5 * entropy_factor)

    def _build_explanation(
        self,
        level: MathLevel,
        strategy: str,
        features: Features,
    ) -> str:
        """Build human-readable explanation for the decision"""
        parts = []

        # Level explanation
        parts.append(f"Selected {level.value} ({level.description})")

        # Why this level
        if level == MathLevel.L1:
            if features.is_budget_constrained():
                parts.append("Reason: Budget constraints require lowest-cost approach")
            elif features.is_latency_constrained():
                parts.append("Reason: Latency constraints require fastest approach")
            else:
                parts.append(
                    f"Reason: Task type '{features.task_type.value}' works well with L1"
                )

        elif level == MathLevel.L2:
            if features.memory_entropy > 0.6:
                parts.append(
                    f"Reason: High memory entropy ({features.memory_entropy:.2f}) suggests need for information-theoretic optimization"
                )
            else:
                parts.append(
                    f"Reason: Task type '{features.task_type.value}' benefits from entropy analysis"
                )

        elif level == MathLevel.L3:
            parts.append(
                f"Reason: Complex scenario (memory_count={features.memory_count}, session_length={features.session_length}) benefits from adaptive approach"
            )

        # Strategy explanation
        parts.append(f"Strategy: {strategy}")

        return " | ".join(parts)

    def _build_telemetry_tags(
        self,
        level: MathLevel,
        strategy: str,
        features: Features,
        context: TaskContext,
    ) -> Dict[str, str]:
        """Build telemetry tags for observability"""
        return {
            "math.level": level.value,
            "math.strategy": strategy,
            "math.task_type": features.task_type.value,
            "math.profile": self.config.profile,
            "session.length": str(features.session_length),
            "memory.count": str(features.memory_count),
            "tenant.id": str(context.session_metadata.get("tenant_id", "unknown")),
        }

    def _calculate_confidence(self, level: MathLevel, features: Features) -> float:
        """
        Calculate confidence score for the decision.

        Higher confidence when:
        - Clear constraints force the decision
        - Lots of data supports the choice
        - Previous decisions were successful
        """
        confidence = 0.7  # Base confidence

        # Forced decisions have high confidence
        if features.is_budget_constrained() or features.is_latency_constrained():
            confidence = 0.95

        # More data -> higher confidence
        if features.memory_count > 100:
            confidence += 0.1

        # Previous success -> higher confidence
        if features.previous_level_success is True:
            confidence += 0.1

        return min(confidence, 1.0)

    def log_decision(self, decision: MathDecision) -> None:
        """
        Log decision for analysis and future learning.

        Logs to:
        1. Structured logger (for observability)
        2. Decision log file (for offline analysis)
        """
        # Structured logging
        logger.info(
            "math_decision_made",
            decision_id=decision.decision_id,
            level=decision.selected_level.value,
            strategy=decision.strategy_id,
            confidence=decision.confidence,
            explanation=decision.explanation,
            **decision.telemetry_tags,
        )

        # File logging (if configured)
        if self.config.logging.file_path:
            self._append_to_log_file(decision)

    def _append_to_log_file(self, decision: MathDecision) -> None:
        """Append decision to JSON Lines log file"""
        if not self.config.logging.file_path:
            return

        log_path = Path(self.config.logging.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "a") as f:
            f.write(decision.to_json() + "\n")

    def _store_decision(self, decision: MathDecision) -> None:
        """Store decision in history"""
        self.decision_history.append(decision)
        self._previous_decision = decision

        # Trim history if needed
        if len(self.decision_history) > self._max_history:
            self.decision_history = self.decision_history[-self._max_history :]

    def get_decision_history(self, limit: int = 100) -> List[MathDecision]:
        """Get recent decision history"""
        return self.decision_history[-limit:]

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        metrics: Dict[str, float],
    ) -> Optional[DecisionWithOutcome]:
        """
        Record the outcome of a decision for future learning.

        If bandit is enabled, this also provides reward feedback to update arm statistics.

        Args:
            decision_id: ID of the decision
            success: Whether the operation was successful
            metrics: Outcome metrics (e.g., mrr, latency_ms)

        Returns:
            DecisionWithOutcome if decision found, None otherwise
        """
        # Find decision
        decision = None
        for d in reversed(self.decision_history):
            if d.decision_id == decision_id:
                decision = d
                break

        if not decision:
            logger.warning("decision_not_found_for_outcome", decision_id=decision_id)
            return None

        # Create outcome-linked decision
        outcome = decision.with_outcome(success, metrics)

        # Log outcome
        logger.info(
            "math_decision_outcome_recorded",
            decision_id=decision_id,
            success=success,
            metrics=metrics,
        )

        # Provide reward feedback to bandit (if enabled)
        if (
            self.bandit
            and self.bandit_monitor
            and isinstance(decision.features_used, FeaturesV2)
        ):
            self._update_bandit_with_outcome(decision, outcome)

        # In Iteration 2+, this would be saved for training
        if self.config.logging.save_outcomes:
            self._save_outcome(outcome)

        return outcome

    def _save_outcome(self, outcome: DecisionWithOutcome) -> None:
        """Save outcome for future learning (Iteration 2+)"""
        if not self.config.logging.outcome_file_path:
            return

        outcome_path = Path(self.config.logging.outcome_file_path)
        outcome_path.parent.mkdir(parents=True, exist_ok=True)

        with open(outcome_path, "a") as f:
            f.write(json.dumps(outcome.to_training_example()) + "\n")

    def update_config(self, config: MathControllerConfig) -> None:
        """Update controller configuration at runtime"""
        self.config = config
        self.decision_engine.update_thresholds(config.thresholds)
        logger.info("math_controller_config_updated", profile=config.profile)

    def explain_decision(self, decision: MathDecision) -> str:
        """
        Generate detailed explanation of a decision.

        More verbose than the inline explanation for debugging.
        """
        lines = [
            f"Decision ID: {decision.decision_id}",
            f"Timestamp: {decision.timestamp.isoformat()}",
            "",
            f"Selected Level: {decision.selected_level.value}",
            f"  Description: {decision.selected_level.description}",
            f"  Cost Multiplier: {decision.selected_level.cost_multiplier}x",
            "",
            f"Strategy: {decision.strategy_id}",
            f"Parameters: {json.dumps(decision.params, indent=2)}",
            "",
            f"Explanation: {decision.explanation}",
            f"Confidence: {decision.confidence:.2f}",
            "",
            "Features Used:",
        ]

        if decision.features_used:
            for key, value in decision.features_used.to_dict().items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def _decide_with_bandit(self, features: FeaturesV2) -> tuple[MathLevel, str, str]:
        """
        Make decision using bandit (online learning).
        ...
        """
        assert self.policy_v2 is not None, "Policy v2 must be initialized for bandit"
        assert self.bandit is not None, "Bandit must be initialized"
        assert self.bandit_monitor is not None, "Bandit monitor must be initialized"

        # Get baseline decision from Policy v2
        baseline_level = self.policy_v2.select_level(features)
        baseline_strategy = self.select_strategy(baseline_level, features)

        # Check safety: degradation detection
        is_degraded, drop = self.bandit.check_degradation()
        if is_degraded:
            logger.warning(
                "bandit_degradation_detected", drop=drop, rolling_back_to_baseline=True
            )
            # Rollback to baseline
            return (
                baseline_level,
                baseline_strategy,
                f"Bandit degradation detected ({drop:.1%}), using baseline {baseline_level.value}",
            )

        # Run monitor health checks
        alerts = self.bandit_monitor.check_health()
        critical_alerts = [a for a in alerts if a.severity == "critical"]

        if critical_alerts:
            logger.warning(
                "bandit_critical_alerts",
                alert_count=len(critical_alerts),
                rolling_back_to_baseline=True,
            )
            # Rollback to baseline
            return (
                baseline_level,
                baseline_strategy,
                f"Bandit safety alerts, using baseline {baseline_level.value}",
            )

        # Safe to use bandit - select arm
        arm, was_exploration = self.bandit.select_arm(features)

        # Record decision in monitor
        self.bandit_monitor.record_decision(arm.arm_id)

        # Build explanation
        explanation_parts = [
            f"Bandit selected {arm.level.value} with {arm.strategy} strategy"
        ]
        if was_exploration:
            explanation_parts.append("(exploration)")
        else:
            explanation_parts.append(
                f"(exploitation, UCB score: {arm.ucb_score(self.bandit.total_pulls):.3f})"
            )

        explanation = " ".join(explanation_parts)

        logger.info(
            "bandit_decision",
            arm_id=arm.arm_id,
            level=arm.level.value,
            strategy=arm.strategy,
            was_exploration=was_exploration,
            arm_pulls=arm.pulls,
            arm_mean_reward=arm.mean_reward(),
        )

        return arm.level, arm.strategy, explanation

    def _create_bandit_config(self) -> BanditConfig:
        """
        Create BanditConfig from controller config.

        Reads bandit settings from config and creates BanditConfig.
        Uses safe defaults if not specified.

        Returns:
            BanditConfig
        """
        bandit_settings = getattr(self.config, "bandit", {})

        # Get exploration rate based on profile
        profile = self.config.profile
        if profile == "production":
            default_exploration = 0.0  # No exploration in production
        elif profile == "lab":
            default_exploration = 0.05  # 5% exploration in lab
        else:  # research
            default_exploration = 0.2  # 20% exploration in research

        exploration_rate = bandit_settings.get("exploration_rate", default_exploration)
        max_exploration_rate = bandit_settings.get("max_exploration_rate", 0.2)

        # Ensure exploration_rate <= max_exploration_rate
        exploration_rate = min(exploration_rate, max_exploration_rate)

        # Persistence path
        persistence_path = bandit_settings.get("persistence_path")
        if persistence_path:
            persistence_path = Path(persistence_path)

        return BanditConfig(
            c=bandit_settings.get("c", 1.0),
            context_bonus=bandit_settings.get("context_bonus", 0.1),
            exploration_rate=exploration_rate,
            max_exploration_rate=max_exploration_rate,
            degradation_threshold=bandit_settings.get("degradation_threshold", 0.15),
            min_pulls_for_confidence=bandit_settings.get(
                "min_pulls_for_confidence", 10
            ),
            save_frequency=bandit_settings.get("save_frequency", 50),
            persistence_path=persistence_path,
        )

    def _update_bandit_with_outcome(
        self, decision: MathDecision, outcome: DecisionWithOutcome
    ) -> None:
        """Update bandit statistics with reward feedback"""
        assert self.bandit is not None
        assert self.bandit_monitor is not None

        from .reward import RewardCalculator, RewardConfig

        # Calculate reward
        reward_config = RewardConfig()
        reward_calculator = RewardCalculator(reward_config)
        reward = reward_calculator.calculate(outcome)

        # Find the arm that was selected
        arm_key = (decision.selected_level, decision.strategy_id)
        if arm_key not in self.bandit.arm_map:
            logger.warning(
                "bandit_arm_not_found",
                level=decision.selected_level.value,
                strategy=decision.strategy_id,
            )
            return

        arm = self.bandit.arm_map[arm_key]

        # Update arm with reward
        from typing import cast

        from .features_v2 import FeaturesV2

        self.bandit.update(
            arm=arm,
            reward=reward,
            features=cast(FeaturesV2, decision.features_used),
        )

        # Record in monitor
        self.bandit_monitor.record_decision(arm.arm_id, reward=reward)

        logger.info(
            "bandit_updated_with_outcome",
            arm_id=arm.arm_id,
            reward=reward,
            arm_pulls=arm.pulls,
            arm_mean_reward=arm.mean_reward(),
        )
