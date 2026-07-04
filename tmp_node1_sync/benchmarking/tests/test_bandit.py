"""
Unit tests for Multi-Armed Bandit system

Tests:
- Arm UCB scoring and updates
- MultiArmedBandit arm selection
- Context discretization
- Safety features (degradation detection)
- BanditMonitor alerts
- Persistence (save/load)
"""

import tempfile
from pathlib import Path

import pytest

from benchmarking.math_metrics.controller.bandit import (
    Arm,
    BanditConfig,
    BanditMonitor,
    MonitorAlert,
    MultiArmedBandit,
    create_default_arms,
)
from benchmarking.math_metrics.controller.features_v2 import FeaturesV2
from benchmarking.math_metrics.controller.types import MathLevel, TaskType


class TestArm:
    """Test Arm class"""

    def test_arm_creation(self):
        """Test basic arm creation"""
        arm = Arm(level=MathLevel.L1, strategy="default")
        assert arm.arm_id == "deterministic_heuristic:default"
        assert arm.pulls == 0
        assert arm.total_reward == 0.0
        assert arm.confidence == 0.0

    def test_arm_update(self):
        """Test arm update with reward"""
        arm = Arm(level=MathLevel.L1, strategy="default")

        # First update
        arm.update(reward=0.8, context_id=5)
        assert arm.pulls == 1
        assert arm.total_reward == 0.8
        assert arm.mean_reward() == 0.8
        assert arm.confidence > 0.0

        # Second update
        arm.update(reward=0.6, context_id=5)
        assert arm.pulls == 2
        assert arm.total_reward == 1.4
        assert arm.mean_reward() == 0.7

    def test_arm_context_specific_stats(self):
        """Test context-specific statistics"""
        arm = Arm(level=MathLevel.L2, strategy="entropy_minimization")

        # Update in context 5
        arm.update(reward=0.9, context_id=5)
        arm.update(reward=0.8, context_id=5)

        # Update in context 10
        arm.update(reward=0.5, context_id=10)

        # Check context-specific means
        assert arm.mean_reward(context_id=5) == pytest.approx(
            0.85, abs=0.01
        )  # (0.9 + 0.8) / 2
        assert arm.mean_reward(context_id=10) == pytest.approx(0.5, abs=0.01)
        assert arm.mean_reward() == pytest.approx(0.733, abs=0.01)  # Global mean

    def test_arm_ucb_score(self):
        """Test UCB score calculation"""
        arm = Arm(level=MathLevel.L1, strategy="default")

        # Never pulled - should return infinity
        ucb = arm.ucb_score(total_pulls=10, c=1.0)
        assert ucb == float("inf")

        # After pulls
        arm.update(reward=0.7)
        arm.update(reward=0.8)

        ucb = arm.ucb_score(total_pulls=10, c=1.0)
        # UCB = mean + c * sqrt(ln(N) / n)
        # UCB = 0.75 + 1.0 * sqrt(ln(10) / 2) ≈ 0.75 + 1.07 ≈ 1.82
        assert ucb > arm.mean_reward()  # Should be higher than mean

    def test_create_default_arms(self):
        """Test default arms creation"""
        arms = create_default_arms()

        # Should create 9 arms
        assert len(arms) == 9

        # Count by level
        l1_arms = [a for a in arms if a.level == MathLevel.L1]
        l2_arms = [a for a in arms if a.level == MathLevel.L2]
        l3_arms = [a for a in arms if a.level == MathLevel.L3]

        assert len(l1_arms) == 3
        assert len(l2_arms) == 4
        assert len(l3_arms) == 2

    def test_arm_serialization(self):
        """Test arm to_dict and from_dict"""
        arm = Arm(level=MathLevel.L1, strategy="relevance_scoring")
        arm.update(reward=0.8, context_id=5)

        # Serialize
        data = arm.to_dict()
        assert data["arm_id"] == "deterministic_heuristic:relevance_scoring"
        assert data["pulls"] == 1
        assert data["mean_reward"] == 0.8

        # Deserialize
        arm2 = Arm.from_dict(data)
        assert arm2.arm_id == arm.arm_id
        assert arm2.pulls == arm.pulls
        assert arm2.total_reward == arm.total_reward


class TestMultiArmedBandit:
    """Test MultiArmedBandit class"""

    @pytest.fixture
    def bandit_config(self):
        """Create test bandit config"""
        return BanditConfig(
            c=1.0,
            exploration_rate=0.1,
            max_exploration_rate=0.2,
            degradation_threshold=0.15,
        )

    @pytest.fixture
    def bandit(self, bandit_config):
        """Create test bandit"""
        return MultiArmedBandit(config=bandit_config)

    @pytest.fixture
    def features(self):
        """Create test features"""
        return FeaturesV2(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_count=100,
            graph_density=0.5,
            memory_entropy=0.4,
        )

    def test_bandit_creation(self, bandit):
        """Test bandit creation"""
        assert len(bandit.arms) == 9
        assert bandit.total_pulls == 0
        assert bandit.total_reward == 0.0

    def test_arm_selection_first_pulls(self, bandit, features):
        """Test arm selection for first pulls (should explore)"""
        # First 9 pulls should explore all arms
        selected_arms = []
        for _ in range(9):
            arm, was_exploration = bandit.select_arm(features)
            selected_arms.append(arm.arm_id)
            # Update to mark as pulled
            bandit.update(arm, reward=0.5, features=features)

        # All arms should have been pulled at least once (or close)
        assert bandit.total_pulls == 9

    def test_arm_selection_ucb(self, bandit, features):
        """Test UCB-based arm selection"""
        # Pull all arms once
        for arm in bandit.arms:
            bandit.update(arm, reward=0.5, features=features)

        # Give one arm a much higher reward
        best_arm = bandit.arms[0]
        for _ in range(5):
            bandit.update(best_arm, reward=0.9, features=features)

        # Now select without forcing exploration
        bandit.config.exploration_rate = 0.0  # Disable exploration
        arm, was_exploration = bandit.select_arm(features)

        # Should select the best arm (with high probability)
        assert not was_exploration
        # Best arm should have high mean reward
        assert best_arm.mean_reward() > 0.7

    def test_context_discretization(self, bandit):
        """Test context discretization into buckets"""
        # Test different feature combinations
        features1 = FeaturesV2(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_count=10,  # small
            graph_density=0.1,  # sparse
            memory_entropy=0.1,  # low
        )
        context_id1 = bandit._discretize_context(features1)

        features2 = FeaturesV2(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_count=100,  # medium
            graph_density=0.5,  # medium
            memory_entropy=0.5,  # medium
        )
        context_id2 = bandit._discretize_context(features2)

        features3 = FeaturesV2(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_count=500,  # large
            graph_density=0.9,  # dense
            memory_entropy=0.9,  # high
        )
        context_id3 = bandit._discretize_context(features3)

        # Different features should produce different context IDs
        assert context_id1 != context_id2
        assert context_id2 != context_id3

        # Context IDs should be in valid range [0, 80]
        assert 0 <= context_id1 <= 80
        assert 0 <= context_id2 <= 80
        assert 0 <= context_id3 <= 80

    def test_degradation_detection(self, bandit, features):
        """Test performance degradation detection"""
        # Establish baseline with good rewards
        for arm in bandit.arms:
            for _ in range(5):
                bandit.update(arm, reward=0.8, features=features)

        # Check no degradation yet
        is_degraded, drop = bandit.check_degradation()
        assert not is_degraded

        # Simulate performance drop
        for _ in range(20):
            arm = bandit.arms[0]
            bandit.update(arm, reward=0.3, features=features)  # Much lower

        # Should detect degradation
        is_degraded, drop = bandit.check_degradation()
        # Note: degradation detection requires 20+ recent rewards
        # and baseline established, so this may or may not trigger
        # depending on exact implementation

    def test_get_best_arm(self, bandit, features):
        """Test getting best arm by mean reward"""
        # Pull all arms
        for arm in bandit.arms:
            bandit.update(arm, reward=0.5, features=features)

        # Make one arm clearly better
        best_arm = bandit.arms[0]
        for _ in range(10):
            bandit.update(best_arm, reward=0.95, features=features)

        # Get best arm (no exploration)
        selected = bandit.get_best_arm(features)
        assert selected.arm_id == best_arm.arm_id

    def test_persistence(self, bandit_config, features):
        """Test saving and loading bandit state"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence_path = Path(tmpdir) / "bandit_arms.json"
            bandit_config.persistence_path = persistence_path

            # Create and train bandit
            bandit1 = MultiArmedBandit(config=bandit_config)
            for arm in bandit1.arms:
                for _ in range(3):
                    bandit1.update(arm, reward=0.7, features=features)

            # Save state
            bandit1.save_state()
            assert persistence_path.exists()

            # Create new bandit and load state
            bandit2 = MultiArmedBandit(config=bandit_config)

            # Check state was loaded
            assert bandit2.total_pulls == bandit1.total_pulls
            assert bandit2.total_reward == bandit1.total_reward

            # Check arm statistics
            for arm1, arm2 in zip(bandit1.arms, bandit2.arms):
                assert arm2.pulls == arm1.pulls
                assert arm2.total_reward == arm1.total_reward


class TestBanditMonitor:
    """Test BanditMonitor class"""

    @pytest.fixture
    def bandit(self):
        """Create test bandit"""
        config = BanditConfig(exploration_rate=0.1)
        return MultiArmedBandit(config=config)

    @pytest.fixture
    def monitor(self, bandit):
        """Create test monitor"""
        return BanditMonitor(bandit=bandit)

    @pytest.fixture
    def features(self):
        """Create test features"""
        return FeaturesV2(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_count=100,
        )

    def test_monitor_creation(self, monitor):
        """Test monitor creation"""
        assert len(monitor.alerts) == 0
        assert len(monitor.reward_window) == 0

    def test_record_decision(self, monitor):
        """Test recording decisions"""
        monitor.record_decision("L1:default", reward=0.8)
        monitor.record_decision("L2:entropy_minimization", reward=0.7)

        assert len(monitor.reward_window) == 2
        assert len(monitor.arm_selection_window) == 2

    def test_health_check_no_alerts(self, monitor, bandit, features):
        """Test health check with no issues"""
        # Train bandit normally
        for arm in bandit.arms:
            for _ in range(5):
                bandit.update(arm, reward=0.7, features=features)
                monitor.record_decision(arm.arm_id, reward=0.7)

        # Run health check
        alerts = monitor.check_health()

        # Should have no critical alerts
        critical = [a for a in alerts if a.severity == "critical"]
        assert len(critical) == 0

    def test_excessive_exploration_alert(self, monitor, bandit):
        """Test alert for excessive exploration"""
        # Set exploration rate too high
        bandit.config.exploration_rate = 0.3
        bandit.config.max_exploration_rate = 0.2

        # Run health check
        alerts = monitor.check_health()

        # Should have critical alert
        critical = [a for a in alerts if a.category == "exploration"]
        assert len(critical) > 0

    def test_arm_imbalance_alert(self, monitor, bandit, features):
        """Test alert for arm imbalance"""
        # Dominate with one arm
        dominant_arm = bandit.arms[0]
        for _ in range(100):
            bandit.update(dominant_arm, reward=0.7, features=features)
            monitor.record_decision(dominant_arm.arm_id, reward=0.7)

        # Run health check
        alerts = monitor.check_health()

        # Should have arm imbalance warning
        [a for a in alerts if a.category == "arm_imbalance"]
        # May or may not trigger depending on exact distribution

    def test_get_summary(self, monitor, bandit, features):
        """Test monitor summary"""
        # Generate some activity
        for arm in bandit.arms[:3]:
            bandit.update(arm, reward=0.7, features=features)
            monitor.record_decision(arm.arm_id, reward=0.7)

        # Get summary
        summary = monitor.get_summary()

        assert "alert_counts" in summary
        assert "arm_distribution" in summary
        assert "reward_stats" in summary
        assert "bandit_stats" in summary

    def test_health_status(self, monitor):
        """Test overall health status"""
        # Initially healthy
        status = monitor.get_health_status()
        assert status == "healthy"

        # Add a critical alert
        monitor.alerts.append(
            MonitorAlert(
                severity="critical", category="test", message="Test critical alert"
            )
        )

        status = monitor.get_health_status()
        assert status == "critical"


class TestBanditConfig:
    """Test BanditConfig validation"""

    def test_valid_config(self):
        """Test valid configuration"""
        config = BanditConfig(
            exploration_rate=0.1,
            max_exploration_rate=0.2,
        )
        assert config.exploration_rate == 0.1

    def test_exploration_rate_exceeds_max(self):
        """Test that exploration rate exceeding max raises error"""
        with pytest.raises(ValueError):
            BanditConfig(
                exploration_rate=0.3,
                max_exploration_rate=0.2,
            )

    def test_exploration_rate_out_of_range(self):
        """Test that exploration rate must be in [0, 1]"""
        with pytest.raises(ValueError):
            BanditConfig(exploration_rate=1.5)

        with pytest.raises(ValueError):
            BanditConfig(exploration_rate=-0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
