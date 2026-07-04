from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APIError, AuthenticationError
from anthropic import RateLimitError as AnthropicRateLimitError
from openai import APIStatusError as OpenAIAPIError
from openai import AuthenticationError as OpenAIAuthError
from openai import RateLimitError as OpenAIRateLimitError

from apps.llm.models import (
    LLMAuthError,
    LLMContextLengthError,
    LLMMessage,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMTool,
    LLMTransientError,
)
from apps.llm.providers.anthropic_provider import AnthropicProvider
from apps.llm.providers.openai_provider import OpenAIProvider


@pytest.fixture
def mock_llm_request():
    return LLMRequest(
        model="test-model",
        messages=[LLMMessage(role="user", content="Hello")],
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def mock_tool_llm_request():
    return LLMRequest(
        model="test-model",
        messages=[LLMMessage(role="user", content="Use tool")],
        temperature=0.7,
        max_tokens=100,
        tools=[
            LLMTool(
                name="test_tool",
                description="A tool for testing",
                parameters={"type": "object", "properties": {}},
            )
        ],
    )


# --- Anthropic Mocks and Tests ---


@pytest.fixture
def mock_anthropic_client():
    with patch("apps.llm.providers.anthropic_provider.AsyncAnthropic") as mock_class:
        instance = mock_class.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock()
        instance.messages.stream = MagicMock()
        instance.messages.stream.return_value.__aenter__.return_value = AsyncMock()
        yield instance


@pytest.fixture
def anthropic_provider(mock_anthropic_client):
    return AnthropicProvider(api_key="mock-key")


@pytest.mark.asyncio
async def test_anthropic_complete_success(
    anthropic_provider, mock_anthropic_client, mock_llm_request
):
    # Mock Anthropic's response structure
    # Mock Anthropic's response structure
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 20
    # Ensure name and input return actual values, not MagicMock objects
    mock_tool_use_block = MagicMock(type="tool_use")
    mock_tool_use_block.id = "tool_0"
    mock_tool_use_block.name = "test_tool"
    mock_tool_use_block.input = {"param": "value"}
    mock_response.content = [mock_tool_use_block]
    mock_response.stop_reason = "tool_use"
    mock_response.id = "msg_123"
    mock_response.model = "claude-3-opus-20240229"

    mock_anthropic_client.messages.create.return_value = mock_response

    response = await anthropic_provider.complete(mock_llm_request)

    assert isinstance(response, LLMResponse)
    assert response.tool_calls is not None
    assert response.tool_calls[0]["name"] == "test_tool"


@pytest.mark.asyncio
async def test_anthropic_stream_success(
    anthropic_provider, mock_anthropic_client, mock_llm_request
):
    async def mock_text_stream():
        yield "chunk1"
        yield "chunk2"

    mock_stream_obj = AsyncMock()
    mock_stream_obj.text_stream = mock_text_stream()
    mock_anthropic_client.messages.stream.return_value.__aenter__.return_value = (
        mock_stream_obj
    )

    chunks = [chunk async for chunk in anthropic_provider.stream(mock_llm_request)]

    assert len(chunks) == 2
    assert chunks[0].text == "chunk1"
    assert chunks[1].text == "chunk2"


@pytest.mark.asyncio
async def test_anthropic_rate_limit_error(
    anthropic_provider, mock_anthropic_client, mock_llm_request
):
    mock_anthropic_client.messages.create.side_effect = AnthropicRateLimitError(
        "test", response=MagicMock(), body={}
    )
    with pytest.raises(LLMRateLimitError):
        await anthropic_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_anthropic_authentication_error(
    anthropic_provider, mock_anthropic_client, mock_llm_request
):
    mock_anthropic_client.messages.create.side_effect = AuthenticationError(
        "test", response=MagicMock(), body={}
    )
    with pytest.raises(LLMAuthError):
        await anthropic_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_anthropic_api_error_transient(
    anthropic_provider, mock_anthropic_client, mock_llm_request
):
    # APIError constructor accepts response and body
    mock_anthropic_client.messages.create.side_effect = APIError(
        message="Connection timed out", request=MagicMock(), body={}
    )
    with pytest.raises(LLMTransientError):
        await anthropic_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_anthropic_api_error_context_length(
    anthropic_provider, mock_anthropic_client, mock_llm_request
):
    mock_anthropic_client.messages.create.side_effect = APIError(
        message="maximum context length", request=MagicMock(), body={}
    )
    with pytest.raises(LLMContextLengthError):
        await anthropic_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_anthropic_api_error_general(
    anthropic_provider, mock_anthropic_client, mock_llm_request
):
    mock_anthropic_client.messages.create.side_effect = APIError(
        message="Unknown error", request=MagicMock(), body={}
    )
    with pytest.raises(LLMProviderError):
        await anthropic_provider.complete(mock_llm_request)


# --- OpenAI Mocks and Tests ---


@pytest.fixture
def mock_openai_client():
    with patch("apps.llm.providers.openai_provider.AsyncOpenAI") as mock_class:
        instance = mock_class.return_value
        instance.chat = MagicMock()
        instance.chat.completions = MagicMock()
        instance.chat.completions.create = AsyncMock()
        yield instance


@pytest.fixture
def openai_provider(mock_openai_client):
    return OpenAIProvider(api_key="mock-key")


@pytest.mark.asyncio
async def test_openai_complete_success(
    openai_provider, mock_openai_client, mock_llm_request
):
    mock_response_choice = MagicMock()
    mock_response_choice.message.content = "Mocked OpenAI response"
    mock_response_choice.message.tool_calls = None
    mock_response_choice.finish_reason = "stop"

    mock_response_usage = MagicMock()
    mock_response_usage.prompt_tokens = 10
    mock_response_usage.completion_tokens = 20
    mock_response_usage.total_tokens = 30

    mock_response = MagicMock()
    mock_response.choices = [mock_response_choice]
    mock_response.usage = mock_response_usage
    mock_response.model = "gpt-4-turbo"
    mock_response.model_dump.return_value = {}  # For raw field

    mock_openai_client.chat.completions.create.return_value = mock_response

    response = await openai_provider.complete(mock_llm_request)

    assert isinstance(response, LLMResponse)
    assert response.text == "Mocked OpenAI response"
    assert response.usage.total_tokens == 30
    mock_openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_complete_with_tool_call(
    openai_provider, mock_openai_client, mock_tool_llm_request
):
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = '{"param": "value"}'

    mock_response_choice = MagicMock()
    mock_response_choice.message.content = None
    mock_response_choice.message.tool_calls = [mock_tool_call]
    mock_response_choice.finish_reason = "tool_calls"

    mock_response_usage = MagicMock()
    mock_response_usage.prompt_tokens = 10
    mock_response_usage.completion_tokens = 20
    mock_response_usage.total_tokens = 30

    mock_response = MagicMock()
    mock_response.choices = [mock_response_choice]
    mock_response.usage = mock_response_usage
    mock_response.model = "gpt-4-turbo"
    mock_response.model_dump.return_value = {}

    mock_openai_client.chat.completions.create.return_value = mock_response

    response = await openai_provider.complete(mock_tool_llm_request)

    assert isinstance(response, LLMResponse)
    assert response.tool_calls is not None
    assert response.tool_calls[0]["name"] == "test_tool"


@pytest.mark.asyncio
async def test_openai_stream_success(
    openai_provider, mock_openai_client, mock_llm_request
):
    async def mock_stream_chunks():
        chunk1 = MagicMock()
        chunk1.choices = [
            MagicMock(delta=MagicMock(content="chunk1"), finish_reason=None)
        ]
        yield chunk1

        chunk2 = MagicMock()
        chunk2.choices = [
            MagicMock(delta=MagicMock(content="chunk2"), finish_reason="stop")
        ]
        yield chunk2

    mock_openai_client.chat.completions.create.return_value = mock_stream_chunks()

    chunks = [chunk async for chunk in openai_provider.stream(mock_llm_request)]

    assert len(chunks) == 2
    assert chunks[0].text == "chunk1"
    assert chunks[1].text == "chunk2"


@pytest.mark.asyncio
async def test_openai_rate_limit_error(
    openai_provider, mock_openai_client, mock_llm_request
):
    mock_openai_client.chat.completions.create.side_effect = OpenAIRateLimitError(
        "test", response=MagicMock(), body={}
    )
    with pytest.raises(LLMRateLimitError):
        await openai_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_openai_authentication_error(
    openai_provider, mock_openai_client, mock_llm_request
):
    mock_openai_client.chat.completions.create.side_effect = OpenAIAuthError(
        "authentication failed", response=MagicMock(), body={}
    )
    with pytest.raises(LLMAuthError):
        await openai_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_openai_api_error_transient(
    openai_provider, mock_openai_client, mock_llm_request
):
    mock_openai_client.chat.completions.create.side_effect = OpenAIAPIError(
        "connection reset", response=MagicMock(), body={}
    )
    with pytest.raises(LLMTransientError):
        await openai_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_openai_api_error_context_length(
    openai_provider, mock_openai_client, mock_llm_request
):
    mock_openai_client.chat.completions.create.side_effect = OpenAIAPIError(
        "context_length_exceeded", response=MagicMock(), body={}
    )
    with pytest.raises(LLMContextLengthError):
        await openai_provider.complete(mock_llm_request)


@pytest.mark.asyncio
async def test_openai_api_error_general(
    openai_provider, mock_openai_client, mock_llm_request
):
    mock_openai_client.chat.completions.create.side_effect = OpenAIAPIError(
        "unknown error", response=MagicMock(), body={}
    )
    with pytest.raises(LLMProviderError):
        await openai_provider.complete(mock_llm_request)
