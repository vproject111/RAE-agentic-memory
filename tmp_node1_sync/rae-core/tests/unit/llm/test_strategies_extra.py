from unittest.mock import AsyncMock, MagicMock

import pytest

from rae_core.llm.strategies import (
    FallbackStrategy,
    LLMStrategy,
    LoadBalancingStrategy,
    RoundRobinStrategy,
)


class DummyLLMStrategy(LLMStrategy):
    async def execute(self, providers, prompt, **kwargs):
        return "response", "dummy"


@pytest.mark.asyncio
async def test_abstract_llm_strategy():
    s = DummyLLMStrategy()
    res, p = await s.execute({}, "test")
    assert res == "response"


@pytest.mark.asyncio
async def test_fallback_strategy_errors():
    # No providers available
    s = FallbackStrategy([])
    with pytest.raises(ValueError, match="No providers available"):
        await s.execute({}, "test")

    # All providers fail
    p1 = MagicMock()
    p1.generate = AsyncMock(side_effect=Exception("Error"))
    s = FallbackStrategy(["p1"])
    with pytest.raises(RuntimeError, match="All providers failed"):
        await s.execute({"p1": p1}, "test")


@pytest.mark.asyncio
async def test_load_balancing_strategy_all_fail():
    p1 = MagicMock()
    p1.generate = AsyncMock(side_effect=Exception("Error"))
    s = LoadBalancingStrategy(["p1"])
    with pytest.raises(RuntimeError, match="All providers failed in load balancing"):
        await s.execute({"p1": p1}, "test")

    # No providers configured
    s = LoadBalancingStrategy([])
    with pytest.raises(ValueError, match="No providers configured for load balancing"):
        await s.execute({}, "test")


@pytest.mark.asyncio
async def test_round_robin_strategy():
    p1 = MagicMock()
    p1.generate = AsyncMock(return_value="r1")
    p2 = MagicMock()
    p2.generate = AsyncMock(return_value="r2")

    s = RoundRobinStrategy(["p1", "p2"])

    res1, pr1 = await s.execute({"p1": p1, "p2": p2}, "test")
    assert res1 == "r1"
    assert pr1 == "p1"

    res2, pr2 = await s.execute({"p1": p1, "p2": p2}, "test")
    assert res2 == "r2"
    assert pr2 == "p2"

    # Empty providers
    s = RoundRobinStrategy([])
    with pytest.raises(ValueError, match="No providers configured"):
        await s.execute({}, "test")

    # Provider not found
    s = RoundRobinStrategy(["p1"])
    with pytest.raises(ValueError, match="Provider 'p1' not found"):
        await s.execute({}, "test")
