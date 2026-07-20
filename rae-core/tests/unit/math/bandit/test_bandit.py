from unittest.mock import patch

import pytest

from rae_core.math.bandit.arm import Arm
from rae_core.math.bandit.bandit import BanditConfig, MultiArmedBandit
from rae_core.math.features_v2 import FeaturesV2
from rae_core.math.types import MathLevel, TaskType


def test_bandit_config_validation():
    # Valid config
    config = BanditConfig(exploration_rate=0.1, max_exploration_rate=0.2)
    assert config.exploration_rate == 0.1

    # Invalid: exceeds max
    with pytest.raises(ValueError, match="exceeds max_exploration_rate"):
        BanditConfig(exploration_rate=0.3, max_exploration_rate=0.2)

    # Invalid: out of [0, 1]
    with pytest.raises(ValueError, match=r"must be in \[0, 1\]"):
        BanditConfig(exploration_rate=-0.1)

    # None handling
    config_none = BanditConfig(exploration_rate=None)
    assert config_none.exploration_rate == 0.1


def test_bandit_init():
    config = BanditConfig()
    bandit = MultiArmedBandit(config)
    assert len(bandit.arms) > 0
    assert (MathLevel.L1, "default") in bandit.arm_map
    assert bandit.total_pulls == 0


def test_discretize_context_industrial():
    bandit = MultiArmedBandit(BanditConfig())

    # Industrial, not quantitative, low density
    features = FeaturesV2(
        task_type=TaskType.MEMORY_RETRIEVE, is_industrial=True, term_density=0.5
    )
    assert bandit._discretize_context(features) == 100

    # Industrial, not quantitative, high density
    features.term_density = 0.9
    assert bandit._discretize_context(features) == 101

    # Industrial, quantitative, low density
    features.is_quantitative = True
    features.term_density = 0.5
    assert bandit._discretize_context(features) == 150

    # Industrial, quantitative, high density
    features.term_density = 0.9
    assert bandit._discretize_context(features) == 151


def test_discretize_context_general():
    bandit = MultiArmedBandit(BanditConfig())

    # memory_bin=0 (<30), density_bin=0 (<0.3), entropy_bin=0 (<0.3), affinity_bin=0 (TaskType.MEMORY_RETRIEVE -> L3 affinity=0.3 -> bin 1? No, < 0.3 is 0, >= 0.3 and < 0.7 is 1)
    # L3 affinity for MEMORY_RETRIEVE is 0.3. So bin 1.
    features = FeaturesV2(
        task_type=TaskType.MEMORY_RETRIEVE,
        memory_count=10,
        graph_density=0.1,
        memory_entropy=0.1,
    )
    # memory_bin=0, density_bin=0, entropy_bin=0, affinity_bin=1
    # bucket_id = 0*27 + 0*9 + 0*3 + 1 = 1
    assert bandit._discretize_context(features) == 1

    # memory_count=201 (bin 2), graph_density=0.8 (bin 2), memory_entropy=0.8 (bin 2), TaskType.REFLECTION_DEEP (L3 affinity=1.0 -> bin 2)
    features_complex = FeaturesV2(
        task_type=TaskType.REFLECTION_DEEP,
        memory_count=201,
        graph_density=0.8,
        memory_entropy=0.8,
    )
    # bucket_id = 2*27 + 2*9 + 2*3 + 2 = 54 + 18 + 6 + 2 = 80
    assert bandit._discretize_context(features_complex) == 80


def test_select_arm():
    config = BanditConfig(exploration_rate=0.0)  # No random exploration
    bandit = MultiArmedBandit(config)
    features = FeaturesV2(task_type=TaskType.MEMORY_RETRIEVE)

    # All arms never pulled, UCB should be inf. max() returns the first one usually.
    arm, is_exp = bandit.select_arm(features)
    assert isinstance(arm, Arm)
    assert is_exp == False

    # Force exploration
    arm_exp, is_exp2 = bandit.select_arm(features, force_exploration=True)
    # Since exploration_rate is 0.0, it SHOULD NOT explore randomly even if forced?
    # Wait, look at code:
    # should_explore = force_exploration or (random.random() < self.config.exploration_rate)
    # if should_explore and self.config.exploration_rate > 0:
    # Ah, if exploration_rate is 0, it doesn't explore even if forced.
    assert is_exp2 == False

    bandit.config.exploration_rate = 0.1
    with patch("random.random", return_value=0.05):  # Less than 0.1
        arm_exp, is_exp3 = bandit.select_arm(features)
        assert is_exp3 == True


def test_update_and_drift():
    config = BanditConfig(degradation_threshold=0.1, min_pulls_for_confidence=2)
    bandit = MultiArmedBandit(config)
    features = FeaturesV2(task_type=TaskType.MEMORY_RETRIEVE)
    arm = bandit.arms[0]

    # Update many times to establish baseline
    for _ in range(20):
        bandit.update(arm, 1.0, features)

    assert bandit.baseline_mean_reward == 1.0
    assert bandit.total_pulls == 20

    # Now introduce a drop
    # Simulate drop slowly to find the exact moment of drift
    drift_detected = False
    for i in range(20):
        bandit.update(arm, 0.5, features)
        if bandit.baseline_mean_reward == 0.0:
            drift_detected = True
            break

    assert drift_detected is True
    assert len(bandit.last_100_rewards) == 0

    # Next update will re-establish a NEW baseline (based on all-time average, currently)
    bandit.update(arm, 0.5, features)
    assert bandit.baseline_mean_reward > 0 and bandit.baseline_mean_reward < 1.0


def test_get_best_arm():
    config = BanditConfig(min_pulls_for_confidence=5)
    bandit = MultiArmedBandit(config)
    features = FeaturesV2(task_type=TaskType.MEMORY_RETRIEVE)

    # No arms have 5 pulls yet
    best = bandit.get_best_arm(features)
    assert best.strategy == "default"
    assert best.level == MathLevel.L1

    # Make one arm confident and good
    good_arm = bandit.arms[5]
    for _ in range(5):
        bandit.update(good_arm, 0.9, features)

    best = bandit.get_best_arm(features)
    assert best == good_arm


def test_persistence(tmp_path):
    path = tmp_path / "bandit.json"
    config = BanditConfig(persistence_path=path)
    bandit = MultiArmedBandit(config)
    features = FeaturesV2(task_type=TaskType.MEMORY_RETRIEVE)

    arm = bandit.arms[0]
    bandit.update(arm, 0.8, features)
    bandit.save_state()

    assert path.exists()

    # Load in new bandit
    bandit2 = MultiArmedBandit(config)
    assert bandit2.total_pulls == 1
    assert bandit2.total_reward == 0.8
    # Check if arm state was restored
    assert bandit2.arms[0].pulls == 1
    assert bandit2.arms[0].context_pulls[bandit._discretize_context(features)] == 1


def test_get_statistics():
    bandit = MultiArmedBandit(BanditConfig())
    stats = bandit.get_statistics()
    assert "total_pulls" in stats
    assert "arms" in stats
    assert len(stats["arms"]) == len(bandit.arms)


def test_to_dict():
    bandit = MultiArmedBandit(BanditConfig())
    d = bandit.to_dict()
    assert "config" in d
    assert "statistics" in d
