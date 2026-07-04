from datetime import datetime, timezone
from typing import Any, cast

import pytest

from rae_core.math.policy import (
    compute_batch_scores,
    compute_memory_score,
    rank_memories_by_score,
)


def test_compute_memory_score_balanced():
    # Weights: 0.5, 0.3, 0.2
    # Inputs: 1.0, 1.0, 1.0 (recency at t=0)
    now = datetime.now(timezone.utc)

    result = compute_memory_score(
        similarity=1.0,
        importance=1.0,
        last_accessed_at=now,
        created_at=now,
        access_count=0,
        now=now,
    )

    # 0.5*1 + 0.3*1 + 0.2*1 = 1.0
    assert result.final_score == 1.0
    assert result.relevance_score == 1.0
    assert result.importance_score == 1.0
    assert result.recency_score == 1.0


def test_compute_memory_score_zero():
    # Weights: 0.5, 0.3, 0.2
    # Inputs: 0.0, 0.0, very old (recency ~0)
    now = datetime.now(timezone.utc)
    old = datetime(2000, 1, 1, tzinfo=timezone.utc)

    result = compute_memory_score(
        similarity=0.0,
        importance=0.0,
        last_accessed_at=old,
        created_at=old,
        access_count=0,
        now=now,
    )

    assert result.final_score < 0.01  # Should be close to 0


def test_batch_scoring_and_ranking():
    now = datetime.now(timezone.utc)
    memories = [
        {"id": "A", "importance": 0.9, "created_at": now},  # High importance
        {"id": "B", "importance": 0.1, "created_at": now},  # Low importance
    ]
    similarities = [0.9, 0.9]  # Same relevance

    results = compute_batch_scores(memories, similarities, now=now)
    ranked = rank_memories_by_score(memories, results)

    assert len(ranked) == 2
    assert ranked[0]["id"] == "A"  # A should be first due to higher importance
    assert ranked[0]["final_score"] > ranked[1]["final_score"]


def test_mismatched_lengths():
    with pytest.raises(ValueError):
        compute_batch_scores([{}], [0.1, 0.2])

    with pytest.raises(ValueError):
        rank_memories_by_score([{}], [cast(Any, {}), cast(Any, {})])
