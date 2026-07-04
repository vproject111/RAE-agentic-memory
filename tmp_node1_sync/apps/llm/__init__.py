"""
RAE LLM Integration Module.

Unified multi-model LLM integration with support for:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude)
- Google (Gemini)
- Ollama (local models)
- DeepSeek
- Qwen (Alibaba Cloud)
- Grok (xAI)

Usage:
    from apps.llm import LLMRouter, LLMRequest, LLMMessage

    router = LLMRouter()
    request = LLMRequest(
        model="gpt-4",
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant"),
            LLMMessage(role="user", content="Hello!"),
        ],
    )
    response = await router.complete(request)
    print(response.text)
"""

from .broker import LLMRouter
from .models import (
    LLMAuthError,
    LLMChunk,
    LLMContextLengthError,
    LLMError,
    LLMMessage,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMTool,
    LLMTransientError,
    LLMValidationError,
    TokenUsage,
)
from .providers import (
    AnthropicProvider,
    DeepSeekProvider,
    GeminiProvider,
    GrokProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    QwenProvider,
)

__all__ = [
    # Router
    "LLMRouter",
    # Providers
    "LLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "DeepSeekProvider",
    "QwenProvider",
    "GrokProvider",
    # Models
    "LLMRequest",
    "LLMResponse",
    "LLMMessage",
    "LLMTool",
    "LLMChunk",
    "TokenUsage",
    # Errors
    "LLMError",
    "LLMRateLimitError",
    "LLMAuthError",
    "LLMTransientError",
    "LLMProviderError",
    "LLMValidationError",
    "LLMContextLengthError",
]
