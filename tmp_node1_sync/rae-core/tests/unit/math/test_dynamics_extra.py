from datetime import datetime, timedelta, timezone

import pytest

from rae_core.math.dynamics import (
    calculate_decay_rate_from_half_life,
    calculate_half_life,
    calculate_recency_score,
    ensure_utc,
)


def test_calculate_recency_score_future_timestamp():
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=1)

    with pytest.warns(UserWarning, match="Future timestamp detected"):
        score, age, decay = calculate_recency_score(
            last_accessed_at=None, created_at=future, access_count=0, now=now
        )
        assert score == 1.0
        assert age == 0.0


def test_ensure_utc_naive():
    naive_dt = datetime.now()
    result = ensure_utc(naive_dt)
    assert result.tzinfo == timezone.utc
    assert result.hour == naive_dt.hour


def test_ensure_utc_already_aware():
    aware_dt = datetime.now(timezone.utc)
    result = ensure_utc(aware_dt)
    assert result is aware_dt


def test_calculate_half_life_invalid():
    with pytest.raises(ValueError, match="Decay rate must be positive"):
        calculate_half_life(0)
    with pytest.raises(ValueError, match="Decay rate must be positive"):
        calculate_half_life(-1)


def test_calculate_decay_rate_from_half_life_invalid():
    with pytest.raises(ValueError, match="Half-life must be positive"):
        calculate_decay_rate_from_half_life(0)
    with pytest.raises(ValueError, match="Half-life must be positive"):
        calculate_decay_rate_from_half_life(-1)
