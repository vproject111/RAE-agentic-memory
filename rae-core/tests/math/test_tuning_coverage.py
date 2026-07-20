import pytest

from rae_core.math.tuning import BayesianPolicyTuner, TuningResult


class TestBayesianPolicyTuner:
    def test_init(self):
        tuner = BayesianPolicyTuner(baseline_alpha=10.0)
        assert tuner.baseline_alpha == 10.0

    def test_compute_posterior_basic(self):
        tuner = BayesianPolicyTuner(baseline_alpha=5.0)
        current_weights = {"alpha": 0.5, "beta": 0.3, "gamma": 0.2}
        feedback_loop = [
            {"score": 0.8, "weights": {"alpha": 0.6, "beta": 0.2, "gamma": 0.2}},
            {"score": -0.5, "weights": {"alpha": 0.4, "beta": 0.4, "gamma": 0.2}},
        ]

        result = tuner.compute_posterior(
            current_weights, feedback_loop, learning_rate=1.0
        )

        assert isinstance(result, TuningResult)
        assert "alpha" in result.new_weights
        assert "beta" in result.new_weights
        assert "gamma" in result.new_weights
        assert 0.0 <= result.confidence <= 1.0
        assert result.entropy > 0.0
        # Check normalization
        assert pytest.approx(sum(result.new_weights.values()), rel=1e-5) == 1.0

    def test_compute_posterior_no_significant_feedback(self):
        tuner = BayesianPolicyTuner(baseline_alpha=5.0)
        current_weights = {"alpha": 0.5, "beta": 0.3, "gamma": 0.2}
        feedback_loop = [
            {
                "score": 0.05,
                "weights": {"alpha": 0.6, "beta": 0.2, "gamma": 0.2},
            },  # Should be ignored
        ]

        result = tuner.compute_posterior(current_weights, feedback_loop)

        # Should stay close to prior/clamped values
        assert pytest.approx(result.new_weights["alpha"], abs=0.1) == 0.5
        assert pytest.approx(result.new_weights["beta"], abs=0.1) == 0.3
        assert pytest.approx(result.new_weights["gamma"], abs=0.1) == 0.2

    def test_compute_posterior_negative_feedback_floor(self):
        tuner = BayesianPolicyTuner(baseline_alpha=1.0)
        current_weights = {"alpha": 0.5, "beta": 0.3, "gamma": 0.2}
        feedback_loop = [
            {"score": -10.0, "weights": {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}},
        ]

        result = tuner.compute_posterior(current_weights, feedback_loop)

        # Alphas should be clamped to 0.5 minimum
        # The result weights are then normalized and clamped to [0.05, 0.85]
        assert result.new_weights["alpha"] >= 0.05
        assert result.new_weights["beta"] >= 0.05
        assert result.new_weights["gamma"] >= 0.05

    def test_calculate_intent_adjustment(self):
        tuner = BayesianPolicyTuner()

        # Vague query
        adj_vague = tuner.calculate_intent_adjustment("hi")
        assert adj_vague["beta"] == 0.1
        assert adj_vague["alpha"] == -0.05

        # Complex query
        adj_complex = tuner.calculate_intent_adjustment(
            "What is the meaning of life, the universe and everything?"
        )
        assert adj_complex["alpha"] == 0.1
        assert adj_complex["beta"] == -0.05

        # Normal query
        adj_normal = tuner.calculate_intent_adjustment("Hello world test")
        assert adj_normal["alpha"] == 0.0
        assert adj_normal["beta"] == 0.0
        assert adj_normal["gamma"] == 0.0

    def test_compute_posterior_default_weights(self):
        tuner = BayesianPolicyTuner()
        # Test with missing keys in current_weights and feedback
        result = tuner.compute_posterior({}, [{"score": 1.0, "weights": {}}])
        assert "alpha" in result.new_weights
        assert "beta" in result.new_weights
        assert "gamma" in result.new_weights
