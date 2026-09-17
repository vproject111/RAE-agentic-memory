"""Unit tests for RetrievalOptimizer in rae-core (Iteration 9)."""

from __future__ import annotations

import pytest

from rae_core.search.optimizer import (
    MaturityMode,
    OptimizationRecommendation,
    RetrievalOptimizer,
)


def test_maturity_mode_enum():
    assert MaturityMode.SHADOW == "shadow"
    assert MaturityMode.ADVISORY == "advisory"
    assert MaturityMode.ACTIVE == "active"


def test_optimization_recommendation_model():
    rec = OptimizationRecommendation(
        mode=MaturityMode.ADVISORY,
        strategy_weights={"vector": 0.55, "fulltext": 0.45},
        predicted_reward=0.72,
        observed_rewards_count=10,
        rationale="Test rationale",
    )
    assert rec.mode == MaturityMode.ADVISORY
    assert rec.strategy_weights["vector"] == 0.55
    assert rec.predicted_reward == 0.72
    assert rec.observed_rewards_count == 10
    assert rec.rationale == "Test rationale"


def test_retrieval_optimizer_init_defaults_and_custom():
    # Defaults
    opt_default = RetrievalOptimizer()
    assert opt_default.mode == MaturityMode.ACTIVE
    assert opt_default.damping_factor == 0.05
    assert opt_default.max_deviation == 0.15
    assert "vector" in opt_default.current_weights
    assert "fulltext" in opt_default.current_weights

    # Custom
    custom_baseline = {"custom_strat": 0.6}
    opt_custom = RetrievalOptimizer(
        mode=MaturityMode.SHADOW,
        damping_factor=0.1,
        max_deviation=0.2,
        baseline_weights=custom_baseline,
    )
    assert opt_custom.mode == MaturityMode.SHADOW
    assert opt_custom.damping_factor == 0.1
    assert opt_custom.max_deviation == 0.2
    assert opt_custom.current_weights == {"custom_strat": 0.6}


def test_compute_reward_variations():
    optimizer = RetrievalOptimizer()

    # Ideal retrieval
    r_ideal = optimizer.compute_reward(
        quality=1.0,
        latency_ms=50.0,
        token_cost=0.0,
        is_failed=False,
    )
    # 0.65 * 1.0 - 0.10 * 0.1 = 0.64
    assert r_ideal == pytest.approx(0.64, abs=0.02)

    # Failed retrieval
    r_failed = optimizer.compute_reward(
        quality=0.0,
        latency_ms=500.0,
        token_cost=0.5,
        is_failed=True,
    )
    # 0 - 0.1 - 0.05 - 0.15 = -0.30
    assert r_failed < 0.0

    # Bounds: reward cannot exceed 1.0 or go below -1.0
    r_max = optimizer.compute_reward(quality=2.0, latency_ms=-10.0)
    assert r_max <= 1.0

    r_min = optimizer.compute_reward(
        quality=-1.0, latency_ms=10000.0, token_cost=10.0, is_failed=True
    )
    assert r_min >= -1.0


def test_step_active_mode_positive_and_negative():
    optimizer = RetrievalOptimizer(
        mode=MaturityMode.ACTIVE,
        damping_factor=0.05,
        max_deviation=0.15,
        baseline_weights={"vector": 0.50},
    )

    # High quality feedback (> 0.4) -> weight increases
    rec1 = optimizer.step(
        strategy_name="vector",
        quality=0.95,
        latency_ms=50.0,
    )
    assert rec1.mode == MaturityMode.ACTIVE
    assert optimizer.current_weights["vector"] > 0.50
    assert "Observed reward" in rec1.rationale

    # Push repeatedly to test upper clamping [0.5 * 1.15 = 0.575]
    for _ in range(30):
        optimizer.step(
            strategy_name="vector",
            quality=1.0,
            latency_ms=10.0,
        )
    assert optimizer.current_weights["vector"] <= 0.575

    # Low quality feedback (< 0.4) -> weight decreases
    for _ in range(50):
        optimizer.step(
            strategy_name="vector",
            quality=0.0,
            latency_ms=450.0,
            is_failed=True,
        )
    # Lower bound is 0.5 * 0.85 = 0.425
    assert optimizer.current_weights["vector"] >= 0.425
    assert optimizer.current_weights["vector"] < 0.50


def test_step_shadow_and_advisory_modes():
    opt_shadow = RetrievalOptimizer(mode=MaturityMode.SHADOW)
    initial_w = dict(opt_shadow.current_weights)
    rec_s = opt_shadow.step(strategy_name="vector", quality=1.0, latency_ms=20.0)
    assert rec_s.mode == MaturityMode.SHADOW
    assert opt_shadow.current_weights == initial_w

    opt_advisory = RetrievalOptimizer(mode=MaturityMode.ADVISORY)
    rec_a = opt_advisory.step(strategy_name="vector", quality=1.0, latency_ms=20.0)
    assert rec_a.mode == MaturityMode.ADVISORY
    assert opt_advisory.current_weights == initial_w


def test_get_average_reward():
    optimizer = RetrievalOptimizer()
    assert optimizer.get_average_reward() == 0.0

    optimizer.step("vector", quality=0.8, latency_ms=100.0)
    optimizer.step("vector", quality=0.4, latency_ms=200.0)
    optimizer.step("vector", quality=0.9, latency_ms=50.0)

    avg_all = optimizer.get_average_reward()
    assert avg_all > 0.0

    avg_last_1 = optimizer.get_average_reward(last_n=1)
    last_reward = optimizer.history[-1]["reward"]
    assert avg_last_1 == pytest.approx(last_reward)
