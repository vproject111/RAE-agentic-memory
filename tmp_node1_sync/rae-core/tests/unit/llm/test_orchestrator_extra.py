from unittest.mock import AsyncMock, MagicMock

import pytest

from rae_core.llm.config import LLMConfig
from rae_core.llm.orchestrator import LLMOrchestrator


@pytest.fixture
def orchestrator():
    config = LLMConfig(default_provider="test")
    provider = MagicMock()
    provider.generate_with_context = AsyncMock(return_value="context response")
    provider.extract_entities = AsyncMock(return_value=[])
    provider.summarize = AsyncMock(return_value="summary")

    return LLMOrchestrator(config, providers={"test": provider})


@pytest.mark.asyncio
async def test_generate_with_context_errors(orchestrator):
    # No target provider (no default, no arg)
    orchestrator.config.default_provider = None
    with pytest.raises(
        ValueError, match="No provider specified and no default configured"
    ):
        await orchestrator.generate_with_context([])

    # Provider not found
    with pytest.raises(ValueError, match="Provider 'nonexistent' not found"):
        await orchestrator.generate_with_context([], provider_name="nonexistent")


@pytest.mark.asyncio
async def test_extract_entities_fallback(orchestrator):
    # Case where provider is not found, should use fallback
    res = await orchestrator.extract_entities("some text", provider_name="nonexistent")
    # NoLLMFallback should be used
    assert isinstance(res, list)


@pytest.mark.asyncio
async def test_summarize_coverage(orchestrator):
    res = await orchestrator.summarize("text to summarize")
    assert res == "summary"

    # Test with non-existent provider (uses fallback)
    res = await orchestrator.summarize("text", provider_name="nonexistent")
    assert "text" in res.lower() or res == ""  # Fallback behavior


def test_register_and_get_provider(orchestrator):
    p2 = MagicMock()
    orchestrator.register_provider("p2", p2)
    assert orchestrator.get_provider("p2") == p2
    assert "p2" in orchestrator.list_providers()
