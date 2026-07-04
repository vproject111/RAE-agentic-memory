"""Tests for Bayesian Policy Tuner."""
import pytest
import numpy as np
from rae_core.math.tuning import BayesianPolicyTuner

def test_bayesian_update_sum_to_one():
    tuner = BayesianPolicyTuner()
    current_weights = {"alpha": 0.5, "beta": 0.3, "gamma": 0.2}
    feedback = [
        {"score": 1.0, "weights": {"alpha": 0.3, "beta": 0.3, "gamma": 0.4}},
        {"score": -1.0, "weights": {"alpha": 0.8, "beta": 0.1, "gamma": 0.1}}
    ]
    
    result = tuner.compute_posterior(current_weights, feedback)
    
    # Check sum
    total = sum(result.new_weights.values())
    assert pytest.approx(total) == 1.0
    
    # Check guardrails
    for w in result.new_weights.values():
        assert w >= 0.05
        assert w <= 0.85

def test_bayesian_learning_direction():
    tuner = BayesianPolicyTuner(baseline_alpha=1.0)
    current_weights = {"alpha": 0.5, "beta": 0.3, "gamma": 0.2}
    
    # User rewards recency (gamma)
    feedback = [{"score": 1.0, "weights": {"alpha": 0.1, "beta": 0.1, "gamma": 0.8}}]
    
    result = tuner.compute_posterior(current_weights, feedback, learning_rate=2.0)
    
    # Gamma should increase
    assert result.new_weights["gamma"] > current_weights["gamma"]
    # Alpha and Beta should decrease
    assert result.new_weights["alpha"] < current_weights["alpha"]
