import os
from unittest.mock import MagicMock, patch

import pytest

from apps.llm.broker.llm_router import LLMRouter
from apps.llm.models import (
    LLMAuthError,
    LLMChunk,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMTransientError,
)


@pytest.fixture
def mock_provider_classes():
    """Fixture to mock all LLMProvider classes."""
    with (
        patch("apps.llm.broker.llm_router.OpenAIProvider") as MockOpenAIProvider,
        patch("apps.llm.broker.llm_router.AnthropicProvider") as MockAnthropicProvider,
        patch("apps.llm.broker.llm_router.GeminiProvider") as MockGeminiProvider,
        patch("apps.llm.broker.llm_router.OllamaProvider") as MockOllamaProvider,
        patch("apps.llm.broker.llm_router.DeepSeekProvider") as MockDeepSeekProvider,
        patch("apps.llm.broker.llm_router.QwenProvider") as MockQwenProvider,
        patch("apps.llm.broker.llm_router.GrokProvider") as MockGrokProvider,
    ):
        # Configure mock instances if needed, e.g., to return a specific name
        MockOpenAIProvider.return_value.name = "openai"
        MockAnthropicProvider.return_value.name = "anthropic"
        MockGeminiProvider.return_value.name = "gemini"
        MockOllamaProvider.return_value.name = "ollama"
        MockDeepSeekProvider.return_value.name = "deepseek"
        MockQwenProvider.return_value.name = "qwen"
        MockGrokProvider.return_value.name = "grok"

        yield {
            "openai": MockOpenAIProvider,
            "anthropic": MockAnthropicProvider,
            "gemini": MockGeminiProvider,
            "ollama": MockOllamaProvider,
            "deepseek": MockDeepSeekProvider,
            "qwen": MockQwenProvider,
            "grok": MockGrokProvider,
        }


@pytest.fixture
def mock_llm_request():
    from apps.llm.models.llm_request import LLMMessage

    return LLMRequest(
        model="gpt-4", messages=[LLMMessage(role="user", content="Hello")]
    )


@pytest.fixture
def mock_llm_response():
    return LLMResponse(
        text="Hello world",
        usage=MagicMock(),
        finish_reason="stop",
        raw={},
        model_name="gpt-4",
    )


@pytest.fixture
def mock_llm_chunk():
    return LLMChunk(text="chunk", finish_reason=None)


@pytest.fixture
def llm_router_with_mocked_config(mock_provider_classes):
    with patch("apps.llm.broker.llm_router.LLMRouter._load_config") as mock_load_config:
        mock_load_config.return_value = {
            "providers": {
                "openai": {
                    "api_key_env": "OPENAI_API_KEY",
                    "endpoint": "https://api.openai.com",
                },
                "anthropic": {"api_key_env": "ANTHROPIC_API_KEY"},
                "gemini": {"api_key_env": "GEMINI_API_KEY"},
                "ollama": {"endpoint": "http://localhost:11434"},
            }
        }
        # Set environment variables for the mocked API keys
        os.environ["OPENAI_API_KEY"] = "mock_openai_key"
        os.environ["ANTHROPIC_API_KEY"] = "mock_anthropic_key"
        os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
        router = LLMRouter()
        yield router
        # Clean up environment variables
        del os.environ["OPENAI_API_KEY"]
        del os.environ["ANTHROPIC_API_KEY"]
        del os.environ["GEMINI_API_KEY"]


@pytest.fixture
def llm_router_empty_config():
    with patch("apps.llm.broker.llm_router.LLMRouter._load_config") as mock_load_config:
        mock_load_config.return_value = {"providers": {}}
        router = LLMRouter()
        yield router


@pytest.fixture
def llm_router_no_api_key():
    with patch("apps.llm.broker.llm_router.LLMRouter._load_config") as mock_load_config:
        mock_load_config.return_value = {
            "providers": {
                "openai": {
                    "api_key_env": "NON_EXISTENT_KEY",
                    "endpoint": "https://api.openai.com",
                },
            }
        }
        # Ensure the env var is not set
        if "NON_EXISTENT_KEY" in os.environ:
            del os.environ["NON_EXISTENT_KEY"]
        router = LLMRouter()
        yield router


@pytest.fixture
def llm_router_unknown_provider():
    with patch("apps.llm.broker.llm_router.LLMRouter._load_config") as mock_load_config:
        mock_load_config.return_value = {
            "providers": {
                "unknown_provider": {"api_key_env": "SOME_KEY"},
            }
        }
        router = LLMRouter()
        yield router


@pytest.mark.asyncio
async def test_init_loads_config_and_initializes_providers(
    llm_router_with_mocked_config, mock_provider_classes
):
    router = llm_router_with_mocked_config
    assert "openai" in router.providers
    assert "anthropic" in router.providers
    assert isinstance(router.providers["openai"], MagicMock)  # It's a mock instance
    mock_provider_classes["openai"].assert_called_once_with(
        api_key="mock_openai_key", api_base="https://api.openai.com"
    )
    mock_provider_classes["anthropic"].assert_called_once_with(
        api_key="mock_anthropic_key"
    )


@pytest.mark.asyncio
async def test_init_handles_empty_config(llm_router_empty_config):
    router = llm_router_empty_config
    assert not router.providers


@pytest.mark.asyncio
async def test_init_handles_missing_api_key(llm_router_no_api_key):
    router = llm_router_no_api_key
    assert (
        "openai" not in router.providers
    )  # Should not be initialized due to missing API key


@pytest.mark.asyncio
async def test_init_handles_unknown_provider(llm_router_unknown_provider):
    router = llm_router_unknown_provider
    assert "unknown_provider" not in router.providers  # Should not be initialized


@pytest.mark.parametrize(
    "model_name, expected_provider_name",
    [
        ("gpt-3.5-turbo", "openai"),
        ("claude-2", "anthropic"),
        ("gemini-pro", "gemini"),
        ("llama2", "ollama"),
        ("mistral", "ollama"),
        ("deepseek-coder", "deepseek"),
        ("qwen-turbo", "qwen"),
        ("grok-1", "grok"),
        ("unknown-model", "openai"),  # Fallback to first available in mocked config
    ],
)
@pytest.mark.asyncio
async def test_get_provider_for_model(
    llm_router_with_mocked_config, model_name, expected_provider_name
):
    router = llm_router_with_mocked_config
    provider = router._get_provider_for_model(model_name)
    assert provider is not None
    assert provider.name == expected_provider_name


@pytest.mark.asyncio
async def test_get_provider_for_model_no_providers(llm_router_empty_config):
    router = llm_router_empty_config
    provider = router._get_provider_for_model("any-model")
    assert provider is None


@pytest.mark.asyncio
async def test_complete_success(
    llm_router_with_mocked_config, mock_llm_request, mock_llm_response
):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.complete.return_value = mock_llm_response

    response = await router.complete(mock_llm_request)
    assert response == mock_llm_response
    mock_openai_provider.complete.assert_awaited_once_with(mock_llm_request)


@pytest.mark.asyncio
async def test_complete_no_provider(llm_router_empty_config, mock_llm_request):
    router = llm_router_empty_config
    with pytest.raises(ValueError, match="No provider available for model"):
        await router.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_complete_auth_error(llm_router_with_mocked_config, mock_llm_request):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.complete.side_effect = LLMAuthError("Invalid key")

    with pytest.raises(LLMAuthError, match="Invalid key"):
        await router.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_complete_rate_limit_error(
    llm_router_with_mocked_config, mock_llm_request
):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.complete.side_effect = LLMRateLimitError("Too fast")

    with pytest.raises(LLMRateLimitError, match="Too fast"):
        await router.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_complete_transient_error(
    llm_router_with_mocked_config, mock_llm_request
):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.complete.side_effect = LLMTransientError("Temp issue")

    with pytest.raises(LLMTransientError, match="Temp issue"):
        await router.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_complete_generic_exception(
    llm_router_with_mocked_config, mock_llm_request
):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.complete.side_effect = Exception("Generic error")

    with pytest.raises(Exception, match="Generic error"):
        await router.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_stream_success(
    llm_router_with_mocked_config, mock_llm_request, mock_llm_chunk
):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.supports_streaming = True
    mock_openai_provider.stream.return_value = [
        mock_llm_chunk,
        mock_llm_chunk,
    ]  # AsyncMock iterable

    chunks = [chunk async for chunk in router.stream(mock_llm_request)]
    assert len(chunks) == 2
    assert chunks[0] == mock_llm_chunk
    mock_openai_provider.stream.assert_awaited_once_with(mock_llm_request)


@pytest.mark.asyncio
async def test_stream_no_provider(llm_router_empty_config, mock_llm_request):
    router = llm_router_empty_config
    with pytest.raises(ValueError, match="No provider available for model"):
        await router.stream(mock_llm_request)


@pytest.mark.asyncio
async def test_stream_provider_does_not_support_streaming(
    llm_router_with_mocked_config, mock_llm_request
):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.supports_streaming = False  # Does not support streaming

    with pytest.raises(ValueError, match="Provider openai does not support streaming"):
        await router.stream(mock_llm_request)


@pytest.mark.asyncio
async def test_stream_generic_exception(
    llm_router_with_mocked_config, mock_llm_request
):
    router = llm_router_with_mocked_config
    mock_openai_provider = router.providers["openai"]
    mock_openai_provider.supports_streaming = True
    mock_openai_provider.stream.side_effect = Exception("Streaming error")

    with pytest.raises(Exception, match="Streaming error"):
        async for _ in router.stream(mock_llm_request):
            pass
