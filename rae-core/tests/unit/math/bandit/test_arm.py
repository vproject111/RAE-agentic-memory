import json

from rae_core.math.bandit.arm import Arm, create_default_arms
from rae_core.math.types import MathLevel


def test_arm_init():
    arm = Arm(level=MathLevel.L1, strategy="test_strategy")
    assert arm.arm_id == f"{MathLevel.L1.value}:test_strategy"
    assert arm.level == MathLevel.L1
    assert arm.strategy == "test_strategy"
    assert arm.pulls == 0
    assert arm.total_reward == 0.0
    assert arm.history == []


def test_arm_mean_reward_global():
    arm = Arm(level=MathLevel.L1, strategy="test")
    assert arm.mean_reward() == 0.0

    arm.update(1.0)
    assert arm.mean_reward() == 1.0

    arm.update(0.0)
    assert arm.mean_reward() == 0.5

    # Test window size
    arm.window_size = 2
    arm.update(2.0)
    # history should be [0.0, 2.0]
    assert arm.mean_reward() == 1.0


def test_arm_mean_reward_context():
    arm = Arm(level=MathLevel.L1, strategy="test")
    context_id = 1
    assert arm.mean_reward(context_id=context_id) == 0.0

    arm.update(1.0, context_id=context_id)
    assert arm.mean_reward(context_id=context_id) == 1.0

    arm.update(0.5, context_id=context_id)
    assert arm.mean_reward(context_id=context_id) == 0.75

    # Different context
    assert arm.mean_reward(context_id=2) == 0.0


def test_arm_ucb_score():
    arm = Arm(level=MathLevel.L1, strategy="test")
    # Never pulled
    assert arm.ucb_score(total_pulls=10) == float("inf")

    arm.update(0.8)  # history: [0.8], pulls: 1
    # total_pulls=10, c=1.0, arm_pulls=1
    # mean = 0.8
    # exploration_bonus = 1.0 * sqrt(ln(10) / 1) = sqrt(2.3025) = 1.5174
    # expected = 0.8 + 1.5174 = 2.3174
    score = arm.ucb_score(total_pulls=10)
    assert 2.317 < score < 2.318

    # Context-specific UCB
    context_id = 5
    assert arm.ucb_score(total_pulls=10, context_id=context_id) == float("inf")
    arm.update(1.0, context_id=context_id)  # context_pulls[5]=1, context_rewards[5]=1.0
    # arm_pulls for context 5 is 1
    # mean for context 5 is 1.0
    # exploration_bonus = 1.0 * sqrt(ln(10) / 1) = 1.5174
    # expected = 1.0 + 1.5174 = 2.5174
    score_ctx = arm.ucb_score(total_pulls=10, context_id=context_id)
    assert 2.517 < score_ctx < 2.518


def test_arm_update_metadata():
    arm = Arm(level=MathLevel.L2, strategy="test")
    timestamp = 123456789.0
    arm.update(reward=0.5, timestamp=timestamp)
    assert arm.last_pulled == timestamp
    assert arm.pulls == 1
    assert arm.confidence == 1.0 - 1.0 / (1.0 + 1.0) == 0.5


def test_arm_reset_window():
    arm = Arm(level=MathLevel.L1, strategy="test")
    arm.update(1.0)
    arm.update(0.5)
    assert len(arm.history) == 2
    arm.reset_window()
    assert len(arm.history) == 0
    assert arm.mean_reward() == 0.0


def test_arm_serialization():
    arm = Arm(level=MathLevel.L3, strategy="test_strat", config={"foo": "bar"})
    arm.update(0.9, context_id=1, timestamp=100.0)

    d = arm.to_dict()
    assert d["arm_id"] == arm.arm_id
    assert d["level"] == MathLevel.L3.value
    assert d["strategy"] == "test_strat"
    assert d["config"] == {"foo": "bar"}
    assert d["pulls"] == 1
    assert d["total_reward"] == 0.9
    assert d["mean_reward"] == 0.9
    assert d["context_pulls"] == {1: 1}

    # Check JSON
    j = arm.to_json()
    loaded_j = json.loads(j)
    assert loaded_j["arm_id"] == arm.arm_id
    assert loaded_j["context_pulls"] == {"1": 1}  # JSON converts int keys to strings

    # Check from_dict
    arm2 = Arm.from_dict(d)
    assert arm2.arm_id == arm.arm_id
    assert arm2.level == arm.level
    assert arm2.strategy == arm.strategy
    assert arm2.pulls == arm.pulls
    assert arm2.total_reward == arm.total_reward
    assert arm2.context_pulls == arm.context_pulls
    assert arm2.last_pulled == arm.last_pulled
    assert arm2.confidence == arm.confidence


def test_create_default_arms():
    arms = create_default_arms()
    assert len(arms) > 20
    # Check if some specific arms exist
    arm_ids = [a.arm_id for a in arms]
    assert f"{MathLevel.L1.value}:default" in arm_ids
    assert f"{MathLevel.L2.value}:entropy_minimization" in arm_ids
    assert f"{MathLevel.L3.value}:hybrid_default" in arm_ids
    # Check one of the ratio arms
    assert f"{MathLevel.L1.value}:w_txt10p0_vec1p0" in arm_ids
