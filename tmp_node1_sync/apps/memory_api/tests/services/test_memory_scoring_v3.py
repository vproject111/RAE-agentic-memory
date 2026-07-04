from datetime import datetime, timezone

import pytest

from apps.memory_api.services.memory_scoring_v3 import (
    MemoryScoreResultV3,
    ScoringWeightsV3,
    compute_batch_scores_v3,
)


@pytest.mark.unit
def test_scoring_weights_v3_default():
    weights = ScoringWeightsV3()
    assert weights.w1_relevance == 0.40
    assert weights.w2_importance == 0.20
    assert weights.w3_recency == 0.10
    assert weights.w4_centrality == 0.10
    assert weights.w5_diversity == 0.10
    assert weights.w6_density == 0.10

    total = sum(
        [
            weights.w1_relevance,
            weights.w2_importance,
            weights.w3_recency,
            weights.w4_centrality,
            weights.w5_diversity,
            weights.w6_density,
        ]
    )
    assert abs(total - 1.0) < 1e-5


@pytest.mark.unit
def test_compute_batch_scores_v3_basic():
    now = datetime.now(timezone.utc)
    memories = [
        {
            "id": "mem1",
            "content": "Short content",
            "created_at": now,
            "importance": 0.8,
            "metadata": {"token_count": 100, "graph_centrality": 0.9},
        }
    ]
    similarities = [0.9]

    results = compute_batch_scores_v3(memories, similarities, now=now)

    assert len(results) == 1
    res = results[0]
    assert isinstance(res, MemoryScoreResultV3)
    assert res.memory_id == "mem1"
    assert res.score_relevance == 0.9
    assert res.score_importance == 0.8
    assert res.score_recency == 1.0  # Created just now
    assert res.score_centrality == 0.9
    assert res.score_diversity == 1.0  # Single item = max diversity
    assert res.score_density == 0.2  # 100 / 500


@pytest.mark.unit
def test_compute_batch_scores_v3_fallback_diversity():
    # Test without embeddings -> diversity should be 1.0
    now = datetime.now(timezone.utc)
    memories = [{"id": "1", "created_at": now}, {"id": "2", "created_at": now}]
    similarities = [0.5, 0.5]

    results = compute_batch_scores_v3(memories, similarities, embeddings=None, now=now)

    assert results[0].score_diversity == 1.0
    assert results[1].score_diversity == 1.0


@pytest.mark.unit
def test_density_calculation():
    now = datetime.now(timezone.utc)
    # Case 1: token_count present
    m1 = {"id": "1", "created_at": now, "metadata": {"token_count": 250}}
    # Case 2: no token_count, use content length
    m2 = {"id": "2", "created_at": now, "content": "a" * 1000}  # 1000 chars

    results = compute_batch_scores_v3([m1, m2], [0, 0], now=now)

    assert results[0].score_density == 0.5  # 250/500
    assert results[1].score_density == 0.5  # 1000/2000
