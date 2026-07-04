"""
Google Gemini LLM Provider.

Implements the LLM provider interface for Google Gemini models.
"""

from collections.abc import AsyncIterator
from typing import Any, Dict, cast

import google.generativeai as genai
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


class GeminiProvider:
    """
    LLM provider for Google Gemini models.
    """

    def __init__(self, api_key: str | None = None, credentials: Any = None):
        """
        Initialize the Gemini provider.

        Args:
            api_key: Google API key
            credentials: Optional OAuth2 credentials
        """
        self.name = "gemini"
        self.max_context_tokens = 1000000  # Gemini 1.5 Pro has 1M context
        self.supports_streaming = True
        self.supports_tools = True

        if api_key:
            genai.configure(api_key=api_key)
        elif credentials:
            genai.configure(credentials=credentials)
        else:
            # Try to load from ~/.gemini/oauth_creds.json (Gemini CLI token)
            import json
            import os

            from google.oauth2.credentials import Credentials

            oauth_path = os.path.expanduser("~/.gemini/oauth_creds.json")
            if os.path.exists(oauth_path):
                try:
                    with open(oauth_path, "r") as f:
                        creds_data = json.load(f)
                        # Gemini CLI Client ID
                        client_id = "681255809395-oo8ft2oprdnrp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
                        credentials = Credentials(
                            token=creds_data.get("access_token"),
                            refresh_token=creds_data.get("refresh_token"),
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=client_id,
                            scopes=creds_data.get("scope", "").split(" "),
                        )
                        genai.configure(credentials=credentials)
                        return
                except Exception:
                    # Ignore and try next fallback
                    pass

            # Fallback to Application Default Credentials (ADC)
            try:
                import google.auth

                adc_credentials, _ = google.auth.default()
                genai.configure(credentials=adc_credentials)
            except Exception:
                raise ValueError(
                    "Either api_key, credentials must be provided, or ADC/Token must be available"
                )

    def _convert_messages(self, request: LLMRequest) -> tuple[str, list[dict]]:
        """
        Convert LLMRequest messages to Gemini format.

        Returns:
            Tuple of (system_instruction, history)
        """
        system_instruction = ""
        history = []

        for msg in request.messages:
            if msg.role == "system":
                # Gemini uses system_instruction parameter
                system_instruction = msg.content
            else:
                # Gemini uses "user" and "model" roles instead of "assistant"
                role = "model" if msg.role == "assistant" else msg.role
                history.append({"role": role, "parts": [msg.content]})

        return system_instruction, history

    def _convert_tools(self, request: LLMRequest) -> list[dict] | None:
        """Convert LLMRequest tools to Gemini format."""
        if not request.tools:
            return None

        # Gemini uses function_declarations format
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
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
        Generate a complete response from Google Gemini.

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
            system_instruction, history = self._convert_messages(request)
            tools = self._convert_tools(request)

            generation_config: Dict[str, Any] = {
                "temperature": request.temperature,
            }

            if request.max_tokens:
                generation_config["max_output_tokens"] = request.max_tokens

            if request.top_p is not None:
                generation_config["top_p"] = request.top_p

            if request.stop_sequences:
                generation_config["stop_sequences"] = request.stop_sequences

            # JSON mode in Gemini uses response_mime_type
            if request.json_mode:
                generation_config["response_mime_type"] = "application/json"

            model_kwargs: Dict[str, Any] = {"model_name": request.model}

            if system_instruction:
                model_kwargs["system_instruction"] = system_instruction

            if tools:
                model_kwargs["tools"] = tools

            model = genai.GenerativeModel(**cast(Any, model_kwargs))

            # If we have history, we need to use a chat
            if len(history) > 1:
                # Extract the last user message
                last_message = history[-1]["parts"][0]
                chat_history = history[:-1]  # Everything except last message

                chat = model.start_chat(history=cast(Any, chat_history))
                response = await chat.send_message_async(
                    last_message, generation_config=cast(Any, generation_config)
                )
            else:
                # Single message, use generate_content
                prompt = history[0]["parts"][0] if history else ""
                response = await model.generate_content_async(
                    prompt, generation_config=cast(Any, generation_config)
                )

            usage = TokenUsage(
                prompt_tokens=response.usage_metadata.prompt_token_count,
                completion_tokens=response.usage_metadata.candidates_token_count,
                total_tokens=response.usage_metadata.total_token_count,
            )

            # Extract tool calls if any
            tool_calls = None
            if hasattr(response.candidates[0].content, "parts"):
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call"):
                        if tool_calls is None:
                            tool_calls = []
                        tool_calls.append(
                            {
                                "name": part.function_call.name,
                                "arguments": dict(part.function_call.args),
                            }
                        )

            return LLMResponse(
                text=response.text,
                usage=usage,
                finish_reason=str(response.candidates[0].finish_reason),
                raw={
                    "prompt_feedback": str(response.prompt_feedback),
                    "candidates": str(response.candidates),
                },
                model_name=request.model,
                tool_calls=tool_calls,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate" in error_str:
                raise LLMRateLimitError(
                    f"Gemini rate limit exceeded: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e
            elif "api key" in error_str or "authentication" in error_str:
                raise LLMAuthError(
                    f"Gemini authentication failed: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e
            elif "timeout" in error_str or "connection" in error_str:
                raise LLMTransientError(
                    f"Gemini transient error: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e
            elif "context" in error_str or "too long" in error_str:
                raise LLMContextLengthError(
                    f"Gemini context length exceeded: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e
            else:
                raise LLMProviderError(
                    f"Gemini error: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate a streaming response from Google Gemini.

        Args:
            request: Standardized LLM request

        Yields:
            Chunks of the response as they become available
        """
        try:
            system_instruction, history = self._convert_messages(request)
            tools = self._convert_tools(request)

            generation_config: Dict[str, Any] = {
                "temperature": request.temperature,
            }

            if request.max_tokens:
                generation_config["max_output_tokens"] = request.max_tokens

            if request.json_mode:
                generation_config["response_mime_type"] = "application/json"

            model_kwargs: Dict[str, Any] = {"model_name": request.model}

            if system_instruction:
                model_kwargs["system_instruction"] = system_instruction

            if tools:
                model_kwargs["tools"] = tools

            model = genai.GenerativeModel(**cast(Any, model_kwargs))

            if len(history) > 1:
                last_message = history[-1]["parts"][0]
                chat_history = history[:-1]
                chat = model.start_chat(history=cast(Any, chat_history))
                response_stream = await chat.send_message_async(
                    last_message,
                    generation_config=cast(Any, generation_config),
                    stream=True,
                )
            else:
                prompt = history[0]["parts"][0] if history else ""
                response_stream = await model.generate_content_async(
                    prompt, generation_config=cast(Any, generation_config), stream=True
                )

            async for chunk in response_stream:
                if chunk.text:
                    yield LLMChunk(text=chunk.text)

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate" in error_str:
                raise LLMRateLimitError(
                    f"Gemini rate limit exceeded: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e
            elif "api key" in error_str or "authentication" in error_str:
                raise LLMAuthError(
                    f"Gemini authentication failed: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e
            else:
                raise LLMTransientError(
                    f"Gemini streaming error: {str(e)}",
                    provider="gemini",
                    raw_error=e,
                ) from e
