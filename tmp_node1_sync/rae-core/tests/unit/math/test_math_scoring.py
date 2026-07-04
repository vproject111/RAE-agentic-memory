"""Unit tests for MathLayerController and ImportanceDecay."""

from datetime import datetime, timedelta, timezone

import pytest

from rae_core.math.controller import MathLayerController
from rae_core.models.scoring import DecayConfig
from rae_core.scoring.decay import ImportanceDecay


class TestMathLayerController:
    @pytest.fixture
    def controller(self):
        return MathLayerController()

    def test_score_memory(self, controller, golden_snapshot):
        now = datetime.now(timezone.utc)
        memory = {
            "importance": 0.8,
            "last_accessed_at": now,
            "created_at": now,
            "access_count": 5,
        }
        score = controller.score_memory(memory, query_similarity=0.9)

        # Record golden snapshot
        golden_snapshot(
            test_name="math_score_memory_standard",
            inputs={"memory": memory, "query_similarity": 0.9},
            output=score,
            metadata={"component": "MathLayerController"},
        )

        assert 0.0 <= score <= 1.0

    def test_compute_similarity(self, controller, golden_snapshot):
        v1 = [1.0, 0.0]
        v2 = [1.0, 0.0]
        v3 = [0.0, 1.0]

        res1 = controller.compute_similarity(v1, v2)
        res2 = controller.compute_similarity(v1, v3)

        # Record golden snapshot
        golden_snapshot(
            test_name="math_cosine_similarity",
            inputs={"v1": v1, "v2": v2, "v3": v3},
            output={"v1_v2": res1, "v1_v3": res2},
            metadata={"component": "MathLayerController"},
        )

        assert res1 == pytest.approx(1.0)
        assert res2 == pytest.approx(0.0)

    def test_apply_decay(self, controller):
        # 24 hours age
        score = controller.apply_decay(age_hours=24.0, usage_count=1)
        assert 0.0 <= score <= 1.0


class TestImportanceDecay:
    @pytest.fixture
    def decay(self):
        config = DecayConfig(
            decay_rate=0.1,
            decay_period=timedelta(days=1),
            min_importance=0.01,
            layer_rates={"test_layer": 0.1},
        )
        return ImportanceDecay(config=config)

    def test_exponential_decay(self, decay):
        # 1 period (1 day) -> factor e^-0.1
        res = decay.exponential_decay(1.0, timedelta(days=1), layer="test_layer")
        assert res.decayed_importance < 1.0
        assert res.decay_amount > 0

    def test_linear_decay(self, decay):
        # 1 period -> subtract (decay_rate * periods) = 0.1 * 1 = 0.1
        res = decay.linear_decay(1.0, timedelta(days=1), layer="test_layer")
        assert res.decayed_importance == pytest.approx(0.9)

    def test_logarithmic_decay(self, decay):
        res = decay.logarithmic_decay(1.0, timedelta(days=1), layer="test_layer")
        assert res.decayed_importance < 1.0

    def test_step_decay(self, decay):
        # periods = 1, decay_rate=0.1, step=0.1 (default) -> amount 0.01
        res = decay.step_decay(
            1.0, timedelta(days=1), layer="test_layer", step_size=0.1
        )
        assert res.decayed_importance == pytest.approx(0.99)

    def test_clamping(self, decay):
        # config min is 0.01
        res = decay.linear_decay(0.05, timedelta(days=10), layer="test_layer")
        assert res.decayed_importance == pytest.approx(0.01)


def test_decay_utils():
    from rae_core.scoring.decay import calculate_half_life, time_to_threshold

    # Half life for rate 0.1 should be ln(2)/0.1 periods
    hl = calculate_half_life(0.1)
    assert hl.days > 0

    # Zero/negative rate
    assert calculate_half_life(0).days == 36500

    # Time to threshold
    # From 1.0 to 0.5 with rate 0.1
    tt = time_to_threshold(1.0, 0.5, 0.1)
    assert tt.days > 0

    # Already below
    assert time_to_threshold(0.4, 0.5, 0.1) == timedelta(0)


@pytest.fixture
def controller():
    return MathLayerController()


def test_math_controller_similarity_fallback(controller):
    # Test with invalid inputs to trigger exception handling if needed,
    # but here we test the logic of the fallback itself
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    # compute_similarity already has a try-except, let's just ensure it works
    assert controller.compute_similarity(v1, v2) == 0.0
