"""Unit tests for LLMOrchestrator and strategies to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rae_core.llm.orchestrator import LLMConfig, LLMOrchestrator
from rae_core.llm.strategies import (
    FallbackStrategy,
    LoadBalancingStrategy,
    RoundRobinStrategy,
)


class TestOrchestratorCoverage:
    @pytest.fixture
    def config(self):
        return LLMConfig(default_provider="p1", enable_fallback=True)

    @pytest.fixture
    def mock_p1(self):
        p = MagicMock()
        p.generate = AsyncMock(return_value="r1")
        p.extract_entities = AsyncMock(return_value=[{"e": 1}])
        p.summarize = AsyncMock(return_value="s1")
        return p

    @pytest.mark.asyncio
    async def test_register_and_get_provider(self, config):
        orch = LLMOrchestrator(config)
        p = MagicMock()
        orch.register_provider("new_p", p)
        assert orch.get_provider("new_p") == p
        assert "new_p" in orch.list_providers()

    @pytest.mark.asyncio
    async def test_generate_no_provider_configured(self):
        config = LLMConfig(default_provider=None)
        orch = LLMOrchestrator(config)
        with pytest.raises(ValueError, match="No provider specified"):
            await orch.generate("p")

    @pytest.mark.asyncio
    async def test_generate_provider_not_found(self):
        # Disable fallback so 'fallback' key isn't added
        config = LLMConfig(default_provider="p1", enable_fallback=False)
        orch = LLMOrchestrator(config)
        with pytest.raises(ValueError, match="Provider 'p1' not found"):
            await orch.generate("p")

    @pytest.mark.asyncio
    async def test_summarize_fallback(self, config):
        orch = LLMOrchestrator(config)
        res = await orch.summarize("text")
        # NoLLMFallback.summarize returns text + "."
        assert res == "text."

    @pytest.mark.asyncio
    async def test_fallback_strategy_success(self, mock_p1):
        providers = {"p1": mock_p1}
        strat = FallbackStrategy(["missing", "p1"])
        res, name = await strat.execute(providers, "q")
        assert res == "r1"
        assert name == "p1"

    @pytest.mark.asyncio
    async def test_fallback_strategy_all_fail(self):
        from typing import cast

        from rae_core.interfaces.llm import ILLMProvider

        p_fail = MagicMock()
        p_fail.generate = AsyncMock(side_effect=Exception("Err"))
        providers = {"p1": p_fail}
        strat = FallbackStrategy(["p1"])
        with pytest.raises(RuntimeError, match="All providers failed"):
            await strat.execute(cast(dict[str, ILLMProvider], providers), "q")

    @pytest.mark.asyncio
    async def test_load_balancing_strategy(self, mock_p1):
        providers = {"p1": mock_p1}
        strat = LoadBalancingStrategy(["p1"])
        res, name = await strat.execute(providers, "q")
        assert res == "r1"
        assert name == "p1"

        # Test skip missing
        strat = LoadBalancingStrategy(["missing", "p1"])
        res, name = await strat.execute(providers, "q")
        assert name == "p1"

    @pytest.mark.asyncio
    async def test_round_robin_strategy(self, mock_p1):
        providers = {"p1": mock_p1}
        strat = RoundRobinStrategy(["p1"])
        res, name = await strat.execute(providers, "q")
        assert res == "r1"

        with pytest.raises(ValueError, match="No providers configured"):
            await RoundRobinStrategy([]).execute(providers, "q")

        with pytest.raises(ValueError, match="Provider 'missing' not found"):
            await RoundRobinStrategy(["missing"]).execute(providers, "q")
