import json
from pathlib import Path
from unittest.mock import patch

from rae_core.math.bandit.bandit import BanditConfig, MultiArmedBandit
from rae_core.math.features_v2 import FeaturesV2
from rae_core.math.types import MathLevel, TaskType


def test_bandit_config_string_path():
    # Line 47: persistence_path is a string
    config = BanditConfig(persistence_path="/tmp/bandit.json")
    assert isinstance(config.persistence_path, Path)


def test_last_100_rewards_pop():
    # Line 186: pop(0) if len > 100
    config = BanditConfig()
    bandit = MultiArmedBandit(config)
    features = FeaturesV2(task_type=TaskType.MEMORY_RETRIEVE)
    arm = bandit.arms[0]

    for _ in range(105):
        bandit.update(arm, 1.0, features)

    assert len(bandit.last_100_rewards) == 100


def test_save_state_triggered_by_frequency():
    # Lines 200-201: save_state and reset decisions_since_save
    with patch("rae_core.math.bandit.bandit.MultiArmedBandit.save_state") as mock_save:
        config = BanditConfig(save_frequency=5)
        bandit = MultiArmedBandit(config)
        features = FeaturesV2(task_type=TaskType.MEMORY_RETRIEVE)
        arm = bandit.arms[0]

        for _ in range(4):
            bandit.update(arm, 1.0, features)
            assert bandit.decisions_since_save == _ + 1
            mock_save.assert_not_called()

        bandit.update(arm, 1.0, features)
        assert bandit.decisions_since_save == 0
        mock_save.assert_called_once()


def test_check_degradation_early_return():
    # Line 215: baseline_mean_reward == 0
    config = BanditConfig()
    bandit = MultiArmedBandit(config)
    # total_pulls < 20
    is_deg, drop = bandit.check_degradation()
    assert is_deg is False
    assert drop == 0.0

    # Let's set pulls to 20 but reward to 0
    bandit.total_pulls = 20
    bandit.last_100_rewards = [1.0] * 20
    # but baseline_mean_reward is still 0
    is_deg, drop = bandit.check_degradation()
    assert is_deg is False
    assert drop == 0.0


def test_discretize_context_bins():
    # Lines 292, 300, 308, 315, 319
    bandit = MultiArmedBandit(BanditConfig())

    # memory_bin=1 (30 <= 100 < 200)
    # density_bin=1 (0.3 <= 0.5 < 0.7)
    # entropy_bin=1 (0.3 <= 0.5 < 0.7)
    # affinity_bin=2 (TaskType.REFLECTION_DEEP -> L3 affinity=1.0 -> bin 2)
    features = FeaturesV2(
        task_type=TaskType.REFLECTION_DEEP,
        memory_count=100,
        graph_density=0.5,
        memory_entropy=0.5,
    )
    # bucket_id = 1*27 + 1*9 + 1*3 + 2 = 27 + 9 + 3 + 2 = 41
    assert bandit._discretize_context(features) == 41

    # memory_bin=2 (201 >= 200)
    # density_bin=2 (0.8 >= 0.7)
    # entropy_bin=2 (0.8 >= 0.7)
    # affinity_bin=0 (TaskType.MEMORY_STORE -> L3 affinity=0.1 -> bin 0)
    features_low = FeaturesV2(
        task_type=TaskType.MEMORY_STORE,
        memory_count=201,
        graph_density=0.8,
        memory_entropy=0.8,
    )
    # bucket_id = 2*27 + 2*9 + 2*3 + 0 = 54 + 18 + 6 = 78
    assert bandit._discretize_context(features_low) == 78


def test_save_state_no_path():
    # Line 330
    config = BanditConfig(persistence_path=None)
    bandit = MultiArmedBandit(config)
    # Should not crash
    bandit.save_state()


def test_load_state_no_path_or_file():
    # Line 350
    config = BanditConfig(persistence_path=Path("/tmp/non_existent_bandit.json"))
    bandit = MultiArmedBandit(config)
    # Should not crash and should return early
    bandit.load_state()
    assert bandit.total_pulls == 0


def test_load_state_success(tmp_path):
    path = tmp_path / "bandit.json"
    state = {
        "total_pulls": 10,
        "total_reward": 5.0,
        "baseline_mean_reward": 0.5,
        "arms": [
            {
                "arm_id": "deterministic_heuristic:default",
                "pulls": 5,
                "total_reward": 2.5,
                "context_pulls": {"1": 2},
                "context_rewards": {"1": 1.0},
                "confidence": 0.8,
            }
        ],
    }
    with open(path, "w") as f:
        json.dump(state, f)

    config = BanditConfig(persistence_path=path)
    bandit = MultiArmedBandit(config)
    # bandit init calls load_state
    assert bandit.total_pulls == 10
    assert bandit.total_reward == 5.0

    # Check if arm state was restored
    # "deterministic_heuristic:default" is one of the default arms
    arm = bandit.arm_map[(MathLevel.L1, "default")]
    assert arm.pulls == 5
    assert arm.total_reward == 2.5
    assert arm.context_pulls[1] == 2
    assert arm.context_rewards[1] == 1.0
