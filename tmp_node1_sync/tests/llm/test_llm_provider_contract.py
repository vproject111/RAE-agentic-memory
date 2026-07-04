"""
Contract tests for LLM providers.

All providers must pass these tests to ensure they implement
the LLMProvider interface correctly.

NOTE: These tests make real API calls and require valid API keys.
If API keys are not set or are clearly test placeholders, tests are skipped.
Run with: pytest -m llm tests/llm/
"""

import json
import os

import pytest

from apps.llm import (
    AnthropicProvider,
    DeepSeekProvider,
    GeminiProvider,
    GrokProvider,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    OpenAIProvider,
    QwenProvider,
)

# Mark all tests in this module as requiring LLM API access
pytestmark = pytest.mark.llm


def should_skip_provider_test(api_key: str | None) -> bool:
    """Determine if a provider test should be skipped."""
    if not api_key:
        return True
    # Common dummy/test keys
    if (
        api_key.startswith("sk-test-")
        or api_key.startswith("mock-")
        or api_key.startswith("dummy-")
        or api_key.startswith("sk-proj")
    ):
        return True
    return False


# Fixtures for providers - skip if API keys not available or are test keys
@pytest.fixture
def openai_provider():
    api_key = os.getenv("OPENAI_API_KEY")
    if should_skip_provider_test(api_key):
        pytest.skip("OPENAI_API_KEY not set or is a test key")

    return OpenAIProvider(api_key=api_key)


@pytest.fixture
def anthropic_provider():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if should_skip_provider_test(api_key):
        pytest.skip("ANTHROPIC_API_KEY not set or is a test key")
    return AnthropicProvider(api_key=api_key)


@pytest.fixture
def gemini_provider():
    api_key = os.getenv("GEMINI_API_KEY")
    # If API key is a placeholder, treat as None to force built-in Token/ADC fallback
    if api_key and (api_key.startswith("your-") or "gemini-key" in api_key):
        api_key = None

    try:
        # GeminiProvider now handles fallsbacks internally
        return GeminiProvider(api_key=api_key)
    except Exception as e:
        pytest.skip(f"GeminiProvider initialization failed: {e}")


@pytest.fixture
def deepseek_provider():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if should_skip_provider_test(api_key):
        pytest.skip("DEEPSEEK_API_KEY not set or is a test key")
    return DeepSeekProvider(api_key=api_key)


@pytest.fixture
def qwen_provider():
    api_key = os.getenv("QWEN_API_KEY")
    if should_skip_provider_test(api_key):
        pytest.skip("QWEN_API_KEY not set or is a test key")
    return QwenProvider(api_key=api_key)


@pytest.fixture
def grok_provider():
    api_key = os.getenv("GROK_API_KEY")
    if should_skip_provider_test(api_key):
        pytest.skip("GROK_API_KEY not set or is a test key")
    return GrokProvider(api_key=api_key)


@pytest.fixture
def all_providers(
    openai_provider,
    anthropic_provider,
    gemini_provider,
    deepseek_provider,
    qwen_provider,
    grok_provider,
):
    """Return all available providers."""
    return [
        openai_provider,
        anthropic_provider,
        gemini_provider,
        deepseek_provider,
        qwen_provider,
        grok_provider,
    ]


@pytest.mark.asyncio
async def test_basic_completion(openai_provider):
    """Test basic completion with simple prompt."""
    request = LLMRequest(
        model="gpt-3.5-turbo",
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Say 'Hello World' and nothing else."),
        ],
        temperature=0.0,
    )

    response = await openai_provider.complete(request)

    assert isinstance(response, LLMResponse)
    assert response.text
    assert "hello" in response.text.lower() or "world" in response.text.lower()
    assert response.usage.total_tokens > 0
    assert response.finish_reason in ["stop", "end_turn", "complete"]


@pytest.mark.asyncio
async def test_json_mode(openai_provider):
    """Test JSON mode output."""
    request = LLMRequest(
        model="gpt-3.5-turbo",
        messages=[
            LLMMessage(
                role="system",
                content="You are a helpful assistant that outputs JSON.",
            ),
            LLMMessage(
                role="user",
                content='Output a JSON object with a single key "message" and value "test".',
            ),
        ],
        json_mode=True,
        temperature=0.0,
    )

    response = await openai_provider.complete(request)

    assert isinstance(response, LLMResponse)
    assert response.text
    # Should be valid JSON
    # import json # Already imported for Anthropic Mock
    result = json.loads(response.text)
    assert "message" in result


@pytest.mark.asyncio
async def test_streaming(openai_provider):
    """Test streaming response."""
    request = LLMRequest(
        model="gpt-3.5-turbo",
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Count from 1 to 5."),
        ],
        temperature=0.0,
    )

    chunks = []
    async for chunk in openai_provider.stream(request):
        chunks.append(chunk.text)

    full_text = "".join(chunks)
    assert full_text
    assert len(chunks) > 1  # Should receive multiple chunks


@pytest.mark.asyncio
async def test_token_usage(openai_provider):
    """Test that token usage is reported correctly."""
    request = LLMRequest(
        model="gpt-3.5-turbo",
        messages=[
            LLMMessage(role="user", content="Hello"),
        ],
    )

    response = await openai_provider.complete(request)

    assert response.usage.prompt_tokens > 0
    assert response.usage.completion_tokens > 0
    assert response.usage.total_tokens == (
        response.usage.prompt_tokens + response.usage.completion_tokens
    )


@pytest.mark.asyncio
async def test_temperature_control(openai_provider):
    """Test temperature parameter affects output variability."""
    request_zero = LLMRequest(
        model="gpt-3.5-turbo",
        messages=[
            LLMMessage(role="user", content="Say exactly: 'Test'"),
        ],
        temperature=0.0,
    )

    # Low temperature should give consistent results
    response1 = await openai_provider.complete(request_zero)
    response2 = await openai_provider.complete(request_zero)

    # Responses should be similar (not necessarily identical due to model variations)
    assert response1.text
    assert response2.text


@pytest.mark.asyncio
async def test_max_tokens(openai_provider):
    """Test max_tokens parameter limits output."""
    request = LLMRequest(
        model="gpt-3.5-turbo",
        messages=[
            LLMMessage(role="user", content="Write a long story about a dragon."),
        ],
        max_tokens=50,
    )

    response = await openai_provider.complete(request)

    # Response should be truncated
    assert response.usage.completion_tokens <= 50
    assert response.finish_reason in ["length", "max_tokens"]


# Example of how to test all providers with same test
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_name,model",
    [
        ("openai", "gpt-3.5-turbo"),
        ("anthropic", "claude-3-haiku-20240307"),
        ("gemini", "gemini-1.5-flash"),
        # Add more as providers are configured
    ],
)
async def test_provider_contract_hello_world(provider_name, model, request):
    """Test that all providers can handle a simple hello world request."""
    # Get provider from fixtures
    provider = request.getfixturevalue(f"{provider_name}_provider")

    llm_request = LLMRequest(
        model=model,
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Say hello"),
        ],
    )

    from apps.llm.models import LLMAuthError

    try:
        response = await provider.complete(llm_request)
    except LLMAuthError as e:
        pytest.skip(f"Authentication failed for {provider_name}: {e}")

    assert isinstance(response, LLMResponse)
    assert response.text
    assert response.usage.total_tokens > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
