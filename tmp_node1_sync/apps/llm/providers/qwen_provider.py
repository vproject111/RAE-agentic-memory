"""
Qwen LLM Provider.

Implements the LLM provider interface for Qwen (Alibaba Cloud) models.
"""

from collections.abc import AsyncIterator
from typing import Any, Dict, cast

import httpx
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


class QwenProvider:
    """
    LLM provider for Qwen (Alibaba Cloud) models.

    Qwen API has some differences from OpenAI, particularly in message structure
    and tools handling.
    """

    def __init__(
        self, api_key: str, api_base: str = "https://dashscope.aliyuncs.com/api/v1"
    ):
        """
        Initialize the Qwen provider.

        Args:
            api_key: Qwen API key (DashScope API key)
            api_base: Qwen API base URL
        """
        self.name = "qwen"
        self.max_context_tokens = 32000  # Qwen-Max supports 32k context
        self.supports_streaming = True
        self.supports_tools = True

        self.api_key = api_key
        self.api_base = api_base
        self.client = httpx.AsyncClient(
            base_url=api_base,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    def _convert_messages(self, request: LLMRequest) -> list[dict]:
        """
        Convert LLMRequest messages to Qwen format.

        Qwen uses a similar structure to OpenAI but with some differences.
        """
        messages = []
        for msg in request.messages:
            message = {"role": msg.role, "content": msg.content}
            if msg.name:
                message["name"] = msg.name
            messages.append(message)
        return messages

    def _convert_tools(self, request: LLMRequest) -> dict | None:
        """
        Convert LLMRequest tools to Qwen format.

        Qwen tools are passed as part of the "parameters" field.
        """
        if not request.tools:
            return None

        return {
            "tools": [
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
        }

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a complete response from Qwen.

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
            tools_dict = self._convert_tools(request)

            payload: Dict[str, Any] = {
                "model": request.model,
                "input": {"messages": messages},
                "parameters": {
                    "temperature": request.temperature,
                },
            }

            parameters = cast(Dict[str, Any], payload["parameters"])

            if request.max_tokens:
                parameters["max_tokens"] = request.max_tokens

            if request.top_p is not None:
                parameters["top_p"] = request.top_p

            if request.stop_sequences:
                parameters["stop"] = request.stop_sequences

            # JSON mode in Qwen
            if request.json_mode:
                parameters["result_format"] = "json"

            # Add tools if present
            if tools_dict is not None:
                parameters.update(tools_dict)

            response = await self.client.post(
                "/services/aigc/text-generation/generation",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            # Qwen response structure
            if "output" not in result:
                raise LLMProviderError(
                    f"Unexpected Qwen response format: {result}",
                    provider="qwen",
                )

            output = result["output"]
            usage_data = result.get("usage", {})

            usage = TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Extract text and tool calls
            text = output.get("text", "")
            tool_calls = None

            if "tool_calls" in output and output["tool_calls"]:
                tool_calls = [
                    {
                        "id": tc.get("id"),
                        "name": tc.get("function", {}).get("name"),
                        "arguments": tc.get("function", {}).get("arguments"),
                    }
                    for tc in output["tool_calls"]
                ]

            return LLMResponse(
                text=text,
                usage=usage,
                finish_reason=output.get("finish_reason", "stop"),
                raw=result,
                model_name=request.model,
                tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_body = e.response.text

            if status_code == 429:
                raise LLMRateLimitError(
                    f"Qwen rate limit exceeded: {error_body}",
                    provider="qwen",
                    raw_error=e,
                ) from e
            elif status_code == 401 or status_code == 403:
                raise LLMAuthError(
                    f"Qwen authentication failed: {error_body}",
                    provider="qwen",
                    raw_error=e,
                ) from e
            elif status_code >= 500:
                raise LLMTransientError(
                    f"Qwen server error: {error_body}",
                    provider="qwen",
                    raw_error=e,
                ) from e
            else:
                raise LLMProviderError(
                    f"Qwen HTTP error {status_code}: {error_body}",
                    provider="qwen",
                    raw_error=e,
                ) from e

        except httpx.TimeoutException as e:
            raise LLMTransientError(
                f"Qwen request timed out: {str(e)}",
                provider="qwen",
                raw_error=e,
            ) from e
        except Exception as e:
            error_str = str(e).lower()
            if "context" in error_str or "too long" in error_str:
                raise LLMContextLengthError(
                    f"Qwen context length exceeded: {str(e)}",
                    provider="qwen",
                    raw_error=e,
                ) from e
            else:
                raise LLMProviderError(
                    f"Qwen error: {str(e)}",
                    provider="qwen",
                    raw_error=e,
                ) from e

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate a streaming response from Qwen.

        Args:
            request: Standardized LLM request

        Yields:
            Chunks of the response as they become available
        """
        try:
            messages = self._convert_messages(request)
            tools_dict = self._convert_tools(request)

            payload: Dict[str, Any] = {
                "model": request.model,
                "input": {"messages": messages},
                "parameters": {
                    "temperature": request.temperature,
                    "incremental_output": True,  # Enable streaming
                },
            }

            parameters = cast(Dict[str, Any], payload["parameters"])

            if request.max_tokens:
                parameters["max_tokens"] = request.max_tokens

            if request.json_mode:
                parameters["result_format"] = "json"

            if tools_dict is not None:
                parameters.update(tools_dict)

            async with self.client.stream(
                "POST",
                "/services/aigc/text-generation/generation",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        import json

                        data_str = line[5:].strip()  # Remove "data:" prefix
                        if data_str and data_str != "[DONE]":
                            chunk_data = json.loads(data_str)
                            if (
                                "output" in chunk_data
                                and "text" in chunk_data["output"]
                            ):
                                yield LLMChunk(
                                    text=chunk_data["output"]["text"],
                                    finish_reason=chunk_data["output"].get(
                                        "finish_reason"
                                    ),
                                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMRateLimitError(
                    f"Qwen rate limit exceeded: {e.response.text}",
                    provider="qwen",
                    raw_error=e,
                ) from e
            elif e.response.status_code in (401, 403):
                raise LLMAuthError(
                    f"Qwen authentication failed: {e.response.text}",
                    provider="qwen",
                    raw_error=e,
                ) from e
            else:
                raise LLMTransientError(
                    f"Qwen streaming error: {e.response.text}",
                    provider="qwen",
                    raw_error=e,
                ) from e
        except Exception as e:
            raise LLMTransientError(
                f"Qwen streaming error: {str(e)}",
                provider="qwen",
                raw_error=e,
            ) from e
