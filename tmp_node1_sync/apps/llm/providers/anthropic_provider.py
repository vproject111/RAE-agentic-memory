"""
Anthropic LLM Provider.

Implements the LLM provider interface for Anthropic Claude models.
"""

from collections.abc import AsyncIterator
from typing import Any, cast

from anthropic import APIError, AsyncAnthropic, AuthenticationError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import (
    LLMAuthError,
    LLMChunk,
    LLMContextLengthError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMTransientError,
    TokenUsage,
)


class AnthropicProvider:
    """
    LLM provider for Anthropic Claude models.
    """

    def __init__(self, api_key: str):
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key
        """
        self.name = "anthropic"
        self.max_context_tokens = 200000  # Claude 3 supports 200k tokens
        self.supports_streaming = True
        self.supports_tools = True

        self.client = AsyncAnthropic(api_key=api_key)

    def _convert_messages(self, request: LLMRequest) -> tuple[str, list[dict]]:
        """
        Convert LLMRequest messages to Anthropic format.

        Returns:
            Tuple of (system_message, messages_list)
        """
        system_message = ""
        messages = []

        for msg in request.messages:
            if msg.role == "system":
                # Anthropic uses separate system parameter
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        return system_message, messages

    def _convert_tools(self, request: LLMRequest) -> list[dict] | None:
        """Convert LLMRequest tools to Anthropic format."""
        if not request.tools:
            return None

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in request.tools
        ]

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a complete response from Anthropic Claude.

        Args:
            request: Standardized LLM request

        Returns:
            Standardized LLM response

        Raises:
            LLMRateLimitError: When rate limit is exceeded
            LLMAuthError: When authentication fails
            LLMTransientError: For transient errors
            LLMProviderError: For other provider errors
        """
        try:
            system_message, messages = self._convert_messages(request)
            tools = self._convert_tools(request)

            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,  # Claude requires max_tokens
                "temperature": request.temperature,
            }

            if system_message:
                params["system"] = system_message

            if tools:
                params["tools"] = tools

            if request.stop_sequences:
                params["stop_sequences"] = request.stop_sequences

            response = await self.client.messages.create(**cast(Any, params))

            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            # Extract text from content blocks
            text = ""
            tool_calls = None

            if response.content:
                for block in response.content:
                    if block.type == "text":
                        text += block.text
                    elif block.type == "tool_use":
                        if tool_calls is None:
                            tool_calls = []
                        tool_calls.append(
                            {
                                "id": block.id,
                                "name": block.name,
                                "arguments": block.input,
                            }
                        )

            return LLMResponse(
                text=text,
                usage=usage,
                finish_reason=response.stop_reason,
                raw={
                    "id": response.id,
                    "model": response.model,
                    "content": str(response.content),
                },
                model_name=response.model,
                tool_calls=tool_calls,
            )

        except RateLimitError as e:
            raise LLMRateLimitError(
                f"Anthropic rate limit exceeded: {str(e)}",
                provider="anthropic",
                raw_error=e,
            ) from e
        except AuthenticationError as e:
            raise LLMAuthError(
                f"Anthropic authentication failed: {str(e)}",
                provider="anthropic",
                raw_error=e,
            ) from e
        except APIError as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "connection" in error_str:
                raise LLMTransientError(
                    f"Anthropic transient error: {str(e)}",
                    provider="anthropic",
                    raw_error=e,
                ) from e
            elif "maximum context length" in error_str:
                raise LLMContextLengthError(
                    f"Anthropic context length exceeded: {str(e)}",
                    provider="anthropic",
                    raw_error=e,
                ) from e
            else:
                raise LLMProviderError(
                    f"Anthropic error: {str(e)}",
                    provider="anthropic",
                    raw_error=e,
                ) from e
        except Exception as e:
            raise LLMProviderError(
                f"Anthropic unexpected error: {str(e)}",
                provider="anthropic",
                raw_error=e,
            ) from e

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate a streaming response from Anthropic Claude.

        Args:
            request: Standardized LLM request

        Yields:
            Chunks of the response as they become available
        """
        try:
            system_message, messages = self._convert_messages(request)
            tools = self._convert_tools(request)

            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
                "stream": True,
            }

            if system_message:
                params["system"] = system_message

            if tools:
                params["tools"] = tools

            async with self.client.messages.stream(**cast(Any, params)) as stream:
                async for text in stream.text_stream:
                    yield LLMChunk(text=text)

        except RateLimitError as e:
            raise LLMRateLimitError(
                f"Anthropic rate limit exceeded: {str(e)}",
                provider="anthropic",
                raw_error=e,
            ) from e
        except AuthenticationError as e:
            raise LLMAuthError(
                f"Anthropic authentication failed: {str(e)}",
                provider="anthropic",
                raw_error=e,
            ) from e
        except Exception as e:
            raise LLMTransientError(
                f"Anthropic streaming error: {str(e)}",
                provider="anthropic",
                raw_error=e,
            ) from e
