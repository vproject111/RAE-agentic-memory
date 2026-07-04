from datetime import datetime, timedelta, timezone

import pytest

from apps.memory_api.services.memory_scoring_v2 import (
    DecayConfig,
    MemoryScoreResult,
    ScoringWeights,
    compute_batch_scores,
    compute_memory_score,
    rank_memories_by_score,
)


@pytest.fixture
def now():
    return datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def created_at():
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_scoring_weights_validation():
    """Test that non-normalized weights raise a warning"""
    # Changed: Now uses Python warnings.warn() instead of structlog logging
    # since rae_core is pure and shouldn't depend on structlog
    with pytest.warns(UserWarning, match="do not sum to 1.0"):
        ScoringWeights(alpha=0.5, beta=0.5, gamma=0.5)  # Sum = 1.5


def test_compute_memory_score_basic(now, created_at):
    """Test basic score computation"""
    result = compute_memory_score(
        similarity=0.9,
        importance=0.8,
        last_accessed_at=created_at,
        created_at=created_at,
        access_count=1,
        now=now,
        memory_id="mem1",
    )

    assert isinstance(result, MemoryScoreResult)
    assert 0.0 <= result.final_score <= 1.0
    assert result.memory_id == "mem1"
    assert result.age_seconds > 0


def test_recency_decay(now, created_at):
    """Test that older memories have lower recency score"""
    # Recent memory
    recent = compute_memory_score(
        similarity=0.5,
        importance=0.5,
        last_accessed_at=now - timedelta(days=1),
        created_at=created_at,
        now=now,
    )

    # Old memory
    old = compute_memory_score(
        similarity=0.5,
        importance=0.5,
        last_accessed_at=now - timedelta(days=100),
        created_at=created_at,
        now=now,
    )

    assert recent.recency_score > old.recency_score


def test_access_count_boost(now, created_at):
    """Test that frequent access slows down decay"""
    # Low access count
    low_access = compute_memory_score(
        similarity=0.5,
        importance=0.5,
        last_accessed_at=created_at,
        created_at=created_at,
        access_count=1,
        now=now,
    )

    # High access count
    high_access = compute_memory_score(
        similarity=0.5,
        importance=0.5,
        last_accessed_at=created_at,
        created_at=created_at,
        access_count=100,
        now=now,
    )

    # Higher access count should result in higher recency score (slower decay)
    # given same time delta
    assert high_access.recency_score > low_access.recency_score
    assert high_access.effective_decay_rate < low_access.effective_decay_rate


def test_future_timestamp(now):
    """Test handling of future timestamps"""
    future = now + timedelta(days=1)

    # Changed: Now uses Python warnings.warn() instead of structlog logging
    # since rae_core is pure and shouldn't depend on structlog
    with pytest.warns(UserWarning, match="Future timestamp detected"):
        result = compute_memory_score(
            similarity=0.5,
            importance=0.5,
            last_accessed_at=future,
            created_at=future,
            now=now,
        )

        assert result.recency_score == 1.0  # Default for invalid/future


def test_batch_scoring(now, created_at):
    """Test batch scoring function"""
    memories = [
        {"id": "m1", "created_at": created_at, "importance": 0.8},
        {"id": "m2", "created_at": created_at, "importance": 0.4},
    ]
    similarities = [0.9, 0.2]

    results = compute_batch_scores(
        memories=memories, similarity_scores=similarities, now=now
    )

    assert len(results) == 2
    assert results[0].memory_id == "m1"
    assert results[1].memory_id == "m2"
    # m1 should have higher score (higher sim and imp)
    assert results[0].final_score > results[1].final_score


def test_batch_scoring_mismatch():
    """Test error when lists have different lengths"""
    memories = [{"id": "m1"}]
    similarities = [0.9, 0.8]

    # Updated: Error message changed to "Length mismatch" in rae_core.math
    with pytest.raises(ValueError, match="Length mismatch"):
        compute_batch_scores(memories, similarities)


def test_rank_memories(now, created_at):
    """Test ranking logic"""
    memories = [
        {"id": "m1", "created_at": created_at},
        {"id": "m2", "created_at": created_at},
    ]

    # Create mock results
    r1 = MemoryScoreResult(0.9, 0, 0, 0, "m1", 0, 0, 0)
    r2 = MemoryScoreResult(0.1, 0, 0, 0, "m2", 0, 0, 0)

    ranked = rank_memories_by_score(memories, [r1, r2])

    assert ranked[0]["id"] == "m1"
    assert ranked[0]["final_score"] == 0.9

    # Inverted inputs - m1 gets r2 (score 0.1), m2 gets r1 (score 0.9)
    ranked_inv = rank_memories_by_score(memories, [r2, r1])

    # Should be sorted descending by score, so m2 (score 0.9) should be first
    assert ranked_inv[0]["id"] == "m2"
    assert ranked_inv[0]["final_score"] == 0.9


def test_decay_config_limits(now, created_at):
    """Test that effective decay rate respects min/max limits"""
    # Super high access count -> very low calculated decay -> clamped to min
    config = DecayConfig(min_decay_rate=0.05)

    result = compute_memory_score(
        similarity=0.5,
        importance=0.5,
        last_accessed_at=created_at,
        created_at=created_at,
        access_count=1000000,
        now=now,
        decay_config=config,
    )

    assert result.effective_decay_rate == 0.05  # Clamped to min
