from rae_core.math.features import Features
from rae_core.types.enums import TaskType


def test_features_to_dict():
    f = Features(task_type=TaskType.SEARCH)
    d = f.to_dict()
    assert d["task_type"] == "search"
    assert "memory_count" in d


def test_is_budget_constrained():
    f = Features(task_type=TaskType.SEARCH)
    assert f.is_budget_constrained() is False

    f.cost_budget = 0.001
    assert f.is_budget_constrained() is True

    f.cost_budget = 0.1
    assert f.is_budget_constrained() is False


def test_is_latency_constrained():
    f = Features(task_type=TaskType.SEARCH)
    assert f.is_latency_constrained() is False

    f.latency_budget_ms = 50
    assert f.is_latency_constrained() is True

    f.latency_budget_ms = 500
    assert f.is_latency_constrained() is False
