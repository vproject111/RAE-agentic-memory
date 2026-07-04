from unittest.mock import AsyncMock, Mock

import pytest

from rae_core.interfaces.cache import ICacheProvider
from rae_core.interfaces.llm import ILLMProvider
from rae_core.llm.config import LLMConfig
from rae_core.llm.orchestrator import LLMOrchestrator


@pytest.fixture
def mock_provider():
    provider = Mock(spec=ILLMProvider)
    provider.generate = AsyncMock(return_value="Provider Response")
    provider.generate_with_context = AsyncMock(return_value="Context Response")
    return provider


@pytest.fixture
def mock_cache():
    cache = Mock(spec=ICacheProvider)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def orchestrator(mock_provider, mock_cache):
    config = LLMConfig(
        default_provider="main",
        providers={"main": {"provider_type": "openai", "model": "gpt-4"}},
        enable_fallback=True,
        cache_responses=True,
    )
    orch = LLMOrchestrator(
        config=config, providers={"main": mock_provider}, cache=mock_cache
    )
    return orch


@pytest.mark.asyncio
async def test_generate_uses_default_provider(orchestrator, mock_provider):
    response, provider_name = await orchestrator.generate("prompt")

    assert response == "Provider Response"
    assert provider_name == "main"
    mock_provider.generate.assert_called_once()


@pytest.mark.asyncio
async def test_generate_uses_cache(orchestrator, mock_provider, mock_cache):
    # Setup cache hit
    mock_cache.get.return_value = {
        "response": "Cached Response",
        "provider": "cached_provider",
    }

    response, provider_name = await orchestrator.generate("prompt", use_cache=True)

    assert response == "Cached Response"
    assert provider_name == "cached_provider"
    mock_provider.generate.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_on_error(orchestrator, mock_provider):
    # Setup main provider failure
    mock_provider.generate.side_effect = Exception("API Error")

    # Ensure fallback is registered (it is by default in fixture)
    assert "fallback" in orchestrator.providers

    response, provider_name = await orchestrator.generate("prompt")

    # Should use fallback (which returns truncated prompt in NoLLMFallback)
    assert "prompt..." in response
    assert provider_name == "fallback"


@pytest.mark.asyncio
async def test_generate_with_context(orchestrator, mock_provider):
    messages = [{"role": "user", "content": "hello"}]
    response, provider_name = await orchestrator.generate_with_context(messages)

    assert response == "Context Response"
    assert provider_name == "main"
    mock_provider.generate_with_context.assert_called_once()
