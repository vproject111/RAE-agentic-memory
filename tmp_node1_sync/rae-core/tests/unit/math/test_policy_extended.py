"""Extended coverage tests for RAE math policy."""

from rae_core.math.policy import (
    compute_coherence_reward,
    compute_reasoning_score_with_coherence,
    compute_score_with_custom_weights,
)


def test_compute_score_with_custom_weights():
    """Test custom weights computation."""
    score = compute_score_with_custom_weights(
        similarity=1.0,
        importance=0.5,
        recency=0.0,
        alpha=0.5,
        beta=0.5,
        gamma=0.0,
    )
    # 0.5*1 + 0.5*0.5 + 0 = 0.75
    assert score == 0.75

    # Test clamping
    score = compute_score_with_custom_weights(
        similarity=1.0, importance=1.0, recency=1.0, alpha=1.0, beta=1.0, gamma=1.0
    )
    assert score == 1.0


def test_compute_coherence_reward_basic():
    """Test coherence reward with matching memories."""
    path_steps = ["User login", "Dashboard access"]

    # Let's use simpler strings
    episodic = [{"content": "User login"}]
    semantic = [{"content": "Dashboard"}]

    reward = compute_coherence_reward(path_steps, episodic, semantic)
    # Supports: 1 episodic + 1 semantic = 2
    # Length: 2
    # Reward = 2 / (2 + 1) = 0.666...
    assert 0.66 < reward < 0.67

    # Test with empty content (should be skipped)
    episodic_empty = [{"content": ""}, {"content": "User login"}]
    semantic_empty = [{"content": ""}, {"content": "Dashboard"}]
    reward_empty = compute_coherence_reward(path_steps, episodic_empty, semantic_empty)
    # Should be same as above because empty one is skipped
    assert 0.66 < reward_empty < 0.67


def test_compute_coherence_reward_empty_path():
    """Test coherence reward with empty path."""
    assert compute_coherence_reward([], [], []) == 0.0


def test_compute_coherence_reward_no_matches():
    """Test coherence reward with no matches."""
    path = ["step1"]
    memories = [{"content": "irrelevant"}]
    reward = compute_coherence_reward(path, memories, [])
    assert reward == 0.0


def test_compute_reasoning_score_with_coherence():
    """Test combining reasoning score with coherence."""
    base = 1.0
    coherence = 0.0
    weight = 0.5

    # (1 - 0.5) * 1.0 + 0.5 * 0.0 = 0.5
    score = compute_reasoning_score_with_coherence(base, coherence, weight)
    assert score == 0.5

    # Default weight 0.3
    # (0.7 * 1.0) + (0.3 * 0.0) = 0.7
    score = compute_reasoning_score_with_coherence(1.0, 0.0)
    assert score == 0.7
