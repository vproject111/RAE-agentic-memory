"""
Base LLM Provider interface.

This module defines the contract that all LLM providers must implement.
"""

from collections.abc import AsyncIterator
from typing import Protocol

from ..models import LLMChunk, LLMRequest, LLMResponse


class LLMProvider(Protocol):
    """
    Protocol defining the interface for a Large Language Model provider.

    All providers must implement this interface to ensure consistent behavior
    across different LLM vendors.

    Attributes:
        name: The provider name (e.g., "openai", "anthropic", "gemini")
        max_context_tokens: Maximum context length supported by the provider
        supports_streaming: Whether the provider supports streaming responses
        supports_tools: Whether the provider supports tool/function calling
    """

    name: str
    max_context_tokens: int
    supports_streaming: bool
    supports_tools: bool

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a complete response from the LLM.

        Args:
            request: Standardized request containing messages, model, and parameters

        Returns:
            Standardized response containing text, usage, and metadata

        Raises:
            LLMRateLimitError: When rate limit is exceeded
            LLMAuthError: When authentication fails
            LLMTransientError: For transient errors (timeouts, network)
            LLMProviderError: For provider-specific errors
            LLMValidationError: When request validation fails
            LLMContextLengthError: When context exceeds model limits
        """
        ...

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate a streaming response from the LLM.

        Args:
            request: Standardized request containing messages, model, and parameters

        Yields:
            Chunks of the response as they become available

        Raises:
            Same exceptions as complete()
        """
        ...
