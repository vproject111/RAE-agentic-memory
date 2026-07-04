"""
Unit tests for Policy v2

Tests cover:
- FeaturesV2 derived features
- Reward calculation
- Weighted level selection
- Policy rules application
"""

import pytest

from benchmarking.math_metrics.controller import (
    FeaturesV2,
    MathControllerConfig,
    MathDecision,
    MathLayerController,
    MathLevel,
    PolicyV2,
    RewardCalculator,
    RewardConfig,
    TaskContext,
    TaskType,
)


class TestFeaturesV2:
    """Test FeaturesV2 dataclass"""

    def test_derived_features(self):
        """Test derived feature computation"""
        features = FeaturesV2(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_count=100,
            session_length=10,
            memory_entropy=2.0,
            consecutive_same_level=6,
            time_since_reflection=150,
        )

        derived = features.compute_derived_features()

        assert "memory_scale" in derived
        assert "session_scale" in derived
        assert "entropy_normalized" in derived
        assert "level_stable" in derived
        assert "needs_reflection" in derived

        # Check specific values
        assert derived["memory_scale"] == pytest.approx(0.1)  # 100/1000
        assert derived["session_scale"] == pytest.approx(0.2)  # 10/50
        assert derived["level_stable"] == 1.0  # consecutive >= 5
        assert derived["needs_reflection"] == 1.0  # > 100 operations

    def test_task_affinities(self):
        """Test task type affinity scores"""
        features = FeaturesV2(task_type=TaskType.REFLECTION_DEEP)

        l1_affinity = features.get_task_affinity_l1()
        l2_affinity = features.get_task_affinity_l2()
        l3_affinity = features.get_task_affinity_l3()

        # Deep reflection should prefer L3
        assert l3_affinity > l2_affinity
        assert l3_affinity > l1_affinity

    def test_from_features_upgrade(self):
        """Test upgrading from Features to FeaturesV2"""
        from benchmarking.math_metrics.controller import Features

        base_features = Features(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_count=50,
            session_length=5,
        )

        features_v2 = FeaturesV2.from_features(base_features, is_first_turn=True)

        assert features_v2.task_type == TaskType.MEMORY_RETRIEVE
        assert features_v2.memory_count == 50
        assert features_v2.is_first_turn is True


class TestRewardCalculator:
    """Test reward calculation"""

    def test_quality_calculation(self):
        """Test quality component"""
        config = RewardConfig()
        calculator = RewardCalculator(config)

        decision = MathDecision(
            selected_level=MathLevel.L1,
            strategy_id="test",
        )

        outcome = decision.with_outcome(
            success=True,
            metrics={
                "mrr": 1.0,
                "hit_rate_5": 1.0,
                "precision_5": 1.0,
                "orr": 1.0,
            },
        )

        reward = calculator.calculate(outcome)

        # Perfect quality should give positive reward
        assert reward > 0

    def test_zero_mrr_penalty(self):
        """Test catastrophic failure penalty"""
        config = RewardConfig()
        calculator = RewardCalculator(config)

        decision = MathDecision(
            selected_level=MathLevel.L1,
            strategy_id="test",
        )

        outcome = decision.with_outcome(success=True, metrics={"mrr": 0.0})

        reward = calculator.calculate(outcome)

        # Zero MRR should give negative reward (penalty kicks in)
        assert reward < 0


class TestPolicyV2:
    """Test Policy v2"""

    @pytest.fixture
    def policy(self):
        """Create Policy v2 instance"""
        return PolicyV2()

    def test_budget_constrained_forces_l1(self, policy):
        """Test budget constraint forces L1"""
        features = FeaturesV2(
            task_type=TaskType.REFLECTION_DEEP,
            cost_budget=0.001,  # Very tight budget
            memory_count=100,
        )

        level = policy.select_level(features)
        assert level == MathLevel.L1

    def test_simple_task_prefers_l1(self, policy):
        """Test simple tasks prefer L1"""
        features = FeaturesV2(
            task_type=TaskType.MEMORY_STORE,
            memory_count=100,
            session_length=5,
        )

        level = policy.select_level(features)
        assert level == MathLevel.L1

    def test_deep_reflection_prefers_l2_or_l3(self, policy):
        """Test deep reflection prefers L2/L3"""
        features = FeaturesV2(
            task_type=TaskType.REFLECTION_DEEP,
            memory_count=100,
            session_length=15,
            memory_entropy=1.5,
        )

        level = policy.select_level(features)
        assert level in [MathLevel.L2, MathLevel.L3]

    def test_l2_memory_threshold(self, policy):
        """Test L2 requires minimum memories"""
        # Too few memories for L2
        features = FeaturesV2(
            task_type=TaskType.MEMORY_CONSOLIDATE,
            memory_count=10,  # Below threshold
            memory_entropy=1.0,
        )

        level = policy.select_level(features)
        assert level == MathLevel.L1  # Should fall back to L1

    def test_l3_blocked_under_threshold(self, policy):
        """Test L3 blocked if memory count too low"""
        features = FeaturesV2(
            task_type=TaskType.REFLECTION_DEEP,
            memory_count=50,  # Below L3 threshold (200)
            session_length=15,
        )

        level = policy.select_level(features)
        assert level != MathLevel.L3  # L3 should be blocked


class TestMathLayerControllerV2:
    """Test controller with Policy v2"""

    def test_controller_v2_initialization(self):
        """Test controller initializes with v2"""
        config = MathControllerConfig(profile="research")
        config.policy_version = 2

        controller = MathLayerController(config=config)

        assert controller.policy_version == 2
        assert controller.policy_v2 is not None

    def test_controller_v2_decision(self):
        """Test v2 makes decisions"""
        config = MathControllerConfig(profile="research")
        config.policy_version = 2

        controller = MathLayerController(config=config)

        context = TaskContext(task_type=TaskType.MEMORY_RETRIEVE)
        decision = controller.decide(context)

        assert isinstance(decision, MathDecision)
        assert decision.selected_level in MathLevel

    def test_controller_v1_fallback(self):
        """Test falls back to v1 when v2 not configured"""
        config = MathControllerConfig(profile="research")
        config.policy_version = 1  # Explicitly v1

        controller = MathLayerController(config=config)

        assert controller.policy_version == 1
        assert controller.policy_v2 is None

        # Should still work
        context = TaskContext(task_type=TaskType.MEMORY_RETRIEVE)
        decision = controller.decide(context)

        assert isinstance(decision, MathDecision)
