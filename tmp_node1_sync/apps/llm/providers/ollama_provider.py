"""
Ollama LLM Provider.

Implements the LLM provider interface for local Ollama models.
"""

import json
from collections.abc import AsyncIterator
from typing import Any, Dict, cast

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import (
    LLMChunk,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMTransientError,
    TokenUsage,
)


class OllamaProvider:
    """
    LLM provider for local Ollama models.
    """

    def __init__(self, api_url: str = "http://localhost:11434"):
        """
        Initialize the Ollama provider.

        Args:
            api_url: Base URL of the Ollama server
        """
        self.name = "ollama"
        self.max_context_tokens = 8192  # Default, varies by model
        self.supports_streaming = True
        self.supports_tools = False  # Ollama has limited tool support

        self.api_url = api_url
        self.client = httpx.AsyncClient(base_url=api_url, timeout=120.0)

    def _convert_messages(self, request: LLMRequest) -> tuple[str, str]:
        """
        Convert LLMRequest messages to Ollama format.

        Returns:
            Tuple of (system, prompt)
        """
        system = ""
        prompt = ""

        for msg in request.messages:
            if msg.role == "system":
                system = msg.content
            elif msg.role == "user":
                prompt += msg.content + "\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n"

        return system, prompt.strip()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=5),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a complete response from Ollama.

        Args:
            request: Standardized LLM request

        Returns:
            Standardized LLM response

        Raises:
            LLMTransientError: For connection or timeout errors
            LLMProviderError: For other provider errors
        """
        try:
            system, prompt = self._convert_messages(request)

            payload: Dict[str, Any] = {
                "model": request.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                },
            }

            options = cast(Dict[str, Any], payload["options"])

            if system:
                payload["system"] = system

            if request.max_tokens:
                options["num_predict"] = request.max_tokens

            if request.json_mode:
                payload["format"] = "json"

            if request.stop_sequences:
                options["stop"] = request.stop_sequences

            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            result_data = response.json()

            usage = TokenUsage(
                prompt_tokens=result_data.get("prompt_eval_count", 0),
                completion_tokens=result_data.get("eval_count", 0),
                total_tokens=result_data.get("prompt_eval_count", 0)
                + result_data.get("eval_count", 0),
            )

            return LLMResponse(
                text=result_data.get("response", "").strip(),
                usage=usage,
                finish_reason=result_data.get("done_reason", "stop"),
                raw=result_data,
                model_name=request.model,
            )

        except httpx.ConnectError as e:
            raise LLMTransientError(
                f"Could not connect to Ollama server at {self.api_url}: {str(e)}",
                provider="ollama",
                raw_error=e,
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTransientError(
                f"Ollama request timed out: {str(e)}",
                provider="ollama",
                raw_error=e,
            ) from e
        except Exception as e:
            raise LLMProviderError(
                f"Ollama error: {str(e)}",
                provider="ollama",
                raw_error=e,
            ) from e

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate a streaming response from Ollama.

        Args:
            request: Standardized LLM request

        Yields:
            Chunks of the response as they become available
        """
        try:
            system, prompt = self._convert_messages(request)

            payload: Dict[str, Any] = {
                "model": request.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": request.temperature,
                },
            }

            options = cast(Dict[str, Any], payload["options"])

            if system:
                payload["system"] = system

            if request.max_tokens:
                options["num_predict"] = request.max_tokens

            if request.json_mode:
                payload["format"] = "json"

            if request.stop_sequences:
                options["stop"] = request.stop_sequences

            async with self.client.stream(
                "POST", "/api/generate", json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        chunk_data = json.loads(line)
                        if chunk_data.get("response"):
                            yield LLMChunk(
                                text=chunk_data["response"],
                                finish_reason=(
                                    chunk_data.get("done_reason")
                                    if chunk_data.get("done")
                                    else None
                                ),
                            )

        except httpx.ConnectError as e:
            raise LLMTransientError(
                f"Could not connect to Ollama server at {self.api_url}: {str(e)}",
                provider="ollama",
                raw_error=e,
            ) from e
        except Exception as e:
            raise LLMTransientError(
                f"Ollama streaming error: {str(e)}",
                provider="ollama",
                raw_error=e,
            ) from e
