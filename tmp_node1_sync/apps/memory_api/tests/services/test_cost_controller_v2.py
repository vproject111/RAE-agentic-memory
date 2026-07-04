from unittest.mock import patch

import pytest

from apps.memory_api.services.cost_controller import (
    calculate_cache_savings,
    calculate_cost,
    estimate_cost,
    get_model_rates,
    is_model_known,
    validate_cost_calculation,
)


@pytest.fixture
def mock_cost_model():
    with patch("apps.memory_api.services.cost_controller.cost_model") as mock:
        yield mock


def test_calculate_cost_known_model(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = {"input": 5.0, "output": 15.0}

    # Execute
    result = calculate_cost("test-model", 1_000_000, 1_000_000)

    # Verify
    assert result["total_cost_usd"] == 20.0  # 5.0 + 15.0
    assert result["cost_known"] is True
    assert result["model_name"] == "test-model"


def test_calculate_cost_unknown_model(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = None

    # Execute
    result = calculate_cost("unknown-model", 1000, 1000)

    # Verify
    assert result["total_cost_usd"] == 0.0
    assert result["cost_known"] is False


def test_calculate_cost_cache_hit(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = {"input": 10.0, "output": 30.0}

    # Execute
    result = calculate_cost("test-model", 1_000_000, 0, cache_hit=True)

    # Verify
    assert result["total_cost_usd"] == 0.0
    assert result["cache_hit"] is True


def test_estimate_cost(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = {"input": 1.0, "output": 2.0}

    # Execute
    cost = estimate_cost("test-model", 1_000_000, 1_000_000)

    # Verify
    assert cost == 3.0


def test_get_model_rates_success(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = {"input": 0.5, "output": 1.5}

    # Execute
    rates = get_model_rates("test-model")

    # Verify
    assert rates is not None
    assert rates["input"] == 0.5
    assert rates["output"] == 1.5


def test_get_model_rates_not_found(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = None

    # Execute
    rates = get_model_rates("unknown")

    # Verify
    assert rates is None


def test_calculate_cache_savings(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = {"input": 10.0}

    # Execute
    savings = calculate_cache_savings("test-model", 1_000_000, "input")

    # Verify
    assert savings == 10.0


def test_is_model_known(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.side_effect = [{"cost": 1}, None]

    # Verify
    assert is_model_known("known") is True
    assert is_model_known("unknown") is False


def test_validate_cost_calculation_valid(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = {"input": 1.0, "output": 1.0}
    # Our cost for 1M + 1M = 2.0 USD

    # Execute
    is_valid = validate_cost_calculation("test", 1_000_000, 1_000_000, 2.00005)

    # Verify (within tolerance)
    assert is_valid is True


def test_validate_cost_calculation_invalid(mock_cost_model):
    # Setup
    mock_cost_model.get_model_cost.return_value = {"input": 1.0, "output": 1.0}
    # Our cost 2.0 USD

    # Execute
    is_valid = validate_cost_calculation("test", 1_000_000, 1_000_000, 5.0)

    # Verify
    assert is_valid is False
