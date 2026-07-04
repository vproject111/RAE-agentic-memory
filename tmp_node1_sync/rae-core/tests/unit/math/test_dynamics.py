import math
from datetime import datetime, timedelta, timezone

from rae_core.math.dynamics import (
    calculate_decay_rate_from_half_life,
    calculate_half_life,
    calculate_recency_score,
)
from rae_core.math.structure import DecayConfig


def test_recency_at_time_zero():
    now = datetime.now(timezone.utc)
    # Created now, accessed now
    score, age, decay = calculate_recency_score(
        last_accessed_at=now, created_at=now, access_count=0, now=now
    )
    assert score == 1.0
    assert age == 0.0


def test_recency_decay():
    now = datetime.now(timezone.utc)
    past = now - timedelta(seconds=1000)

    # Standard decay: exp(-0.001 * 1000) = exp(-1) ≈ 0.368
    config = DecayConfig(base_decay_rate=0.001, access_count_boost=False)

    score, age, decay = calculate_recency_score(
        last_accessed_at=None,
        created_at=past,
        access_count=0,
        now=now,
        decay_config=config,
    )

    assert math.isclose(score, math.exp(-1), rel_tol=1e-3)
    assert age == 1000.0


def test_access_count_boost():
    now = datetime.now(timezone.utc)
    past = now - timedelta(seconds=1000)
    config = DecayConfig(base_decay_rate=0.001, access_count_boost=True)

    # Case 1: No access
    score_0, _, decay_0 = calculate_recency_score(
        last_accessed_at=None,
        created_at=past,
        access_count=0,
        now=now,
        decay_config=config,
    )

    # Case 2: High access (should decay slower -> higher score)
    score_10, _, decay_10 = calculate_recency_score(
        last_accessed_at=None,
        created_at=past,
        access_count=10,
        now=now,
        decay_config=config,
    )

    assert score_10 > score_0
    assert decay_10 < decay_0  # Decay rate should be lower


def test_half_life_calculations():
    # t_1/2 = ln(2) / lambda
    # For lambda = ln(2), half life should be 1
    decay_rate = math.log(2)
    half_life = calculate_half_life(decay_rate)
    assert math.isclose(half_life, 1.0)

    # Inverse check
    calculated_decay = calculate_decay_rate_from_half_life(1.0)
    assert math.isclose(calculated_decay, decay_rate)
