"""
DeepSeek LLM Provider.

Implements the LLM provider interface for DeepSeek models.
DeepSeek API is very similar to OpenAI's API.
"""

from collections.abc import AsyncIterator
from typing import Any, cast

from openai import AsyncOpenAI, RateLimitError
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


class DeepSeekProvider:
    """
    LLM provider for DeepSeek models.

    DeepSeek uses an OpenAI-compatible API, so we leverage the OpenAI client.
    """

    def __init__(self, api_key: str, api_base: str = "https://api.deepseek.com/v1"):
        """
        Initialize the DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            api_base: DeepSeek API base URL (default: https://api.deepseek.com/v1)
        """
        self.name = "deepseek"
        self.max_context_tokens = 64000  # DeepSeek supports up to 64k tokens
        self.supports_streaming = True
        self.supports_tools = True

        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)

    def _convert_messages(self, request: LLMRequest) -> list[dict]:
        """Convert LLMRequest messages to DeepSeek format."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
            }
            for msg in request.messages
        ]

    def _convert_tools(self, request: LLMRequest) -> list[dict] | None:
        """Convert LLMRequest tools to DeepSeek format."""
        if not request.tools:
            return None

        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
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
        Generate a complete response from DeepSeek.

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
            messages = self._convert_messages(request)
            tools = self._convert_tools(request)

            params = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
            }

            if request.max_tokens:
                params["max_tokens"] = request.max_tokens

            if request.json_mode:
                params["response_format"] = {"type": "json_object"}

            if tools:
                params["tools"] = tools

            if request.top_p is not None:
                params["top_p"] = request.top_p

            if request.frequency_penalty is not None:
                params["frequency_penalty"] = request.frequency_penalty

            if request.presence_penalty is not None:
                params["presence_penalty"] = request.presence_penalty

            if request.stop_sequences:
                params["stop"] = request.stop_sequences

            response = await self.client.chat.completions.create(**cast(Any, params))

            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

            tool_calls = None
            if response.choices[0].message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in response.choices[0].message.tool_calls
                ]

            return LLMResponse(
                text=response.choices[0].message.content or "",
                usage=usage,
                finish_reason=response.choices[0].finish_reason,
                raw=response.model_dump(),
                model_name=response.model,
                tool_calls=tool_calls,
            )

        except RateLimitError as e:
            raise LLMRateLimitError(
                f"DeepSeek rate limit exceeded: {str(e)}",
                provider="deepseek",
                raw_error=e,
            ) from e
        except Exception as e:
            error_str = str(e).lower()
            if (
                "authentication" in error_str
                or "api key" in error_str
                or "401" in error_str
            ):
                raise LLMAuthError(
                    f"DeepSeek authentication failed: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e
            elif "timeout" in error_str or "connection" in error_str:
                raise LLMTransientError(
                    f"DeepSeek transient error: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e
            elif (
                "context_length_exceeded" in error_str or "maximum context" in error_str
            ):
                raise LLMContextLengthError(
                    f"DeepSeek context length exceeded: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e
            elif "500" in error_str or "502" in error_str or "503" in error_str:
                raise LLMTransientError(
                    f"DeepSeek server error: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e
            else:
                raise LLMProviderError(
                    f"DeepSeek error: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate a streaming response from DeepSeek.

        Args:
            request: Standardized LLM request

        Yields:
            Chunks of the response as they become available
        """
        try:
            messages = self._convert_messages(request)
            tools = self._convert_tools(request)

            params = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
                "stream": True,
            }

            if request.max_tokens:
                params["max_tokens"] = request.max_tokens

            if request.json_mode:
                params["response_format"] = {"type": "json_object"}

            if tools:
                params["tools"] = tools

            stream = await self.client.chat.completions.create(**cast(Any, params))

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LLMChunk(
                        text=chunk.choices[0].delta.content,
                        finish_reason=chunk.choices[0].finish_reason,
                    )

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str and "limit" in error_str:
                raise LLMRateLimitError(
                    f"DeepSeek rate limit exceeded: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e
            elif "authentication" in error_str or "api key" in error_str:
                raise LLMAuthError(
                    f"DeepSeek authentication failed: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e
            else:
                raise LLMTransientError(
                    f"DeepSeek streaming error: {str(e)}",
                    provider="deepseek",
                    raw_error=e,
                ) from e
