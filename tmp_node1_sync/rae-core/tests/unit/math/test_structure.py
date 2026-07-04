import pytest

from rae_core.math.structure import DecayConfig, MemoryScoreResult, ScoringWeights


def test_scoring_weights_default():
    weights = ScoringWeights()
    assert weights.alpha == 0.5
    assert weights.beta == 0.3
    assert weights.gamma == 0.2
    assert abs((weights.alpha + weights.beta + weights.gamma) - 1.0) < 1e-9


def test_scoring_weights_validation():
    # Should warn if sum != 1.0
    with pytest.warns(UserWarning, match="ScoringWeights do not sum to 1.0"):
        ScoringWeights(alpha=0.1, beta=0.1, gamma=0.1)


def test_decay_config_defaults():
    config = DecayConfig()
    assert config.base_decay_rate == 0.001
    assert config.access_count_boost is True


def test_memory_score_result_serialization():
    result = MemoryScoreResult(
        final_score=0.8,
        relevance_score=0.9,
        importance_score=0.7,
        recency_score=0.6,
        memory_id="test-id",
        age_seconds=100.0,
        access_count=5,
        effective_decay_rate=0.001,
    )

    data = result.to_dict()
    assert data["final_score"] == 0.8
    assert data["memory_id"] == "test-id"
    assert data["age_seconds"] == 100.0
