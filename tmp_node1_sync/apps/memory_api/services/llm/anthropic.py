from typing import Any, Optional, Type, cast

import instructor
from anthropic import AsyncAnthropic
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from apps.memory_api.config import settings
from apps.memory_api.services.llm.base import LLMProvider, LLMResult, LLMResultUsage


class AnthropicProvider(LLMProvider):
    """
    An LLM provider that uses the Anthropic API (for Claude models).
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.ANTHROPIC_API_KEY
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        self.client = instructor.from_anthropic(AsyncAnthropic(api_key=key))

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3)
    )
    async def generate(self, *, system: str, prompt: str, model: str) -> LLMResult:
        """
        Generates content using an Anthropic Claude model.
        """
        try:
            response = await cast(Any, self.client).messages.create(
                model=model,
                system=system,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,  # Anthropic requires max_tokens
            )

            usage = LLMResultUsage(
                prompt_tokens=response.usage.input_tokens,
                candidates_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return LLMResult(
                text=response.content[0].text,
                usage=usage,
                model_name=model,
                finish_reason=response.stop_reason,
            )
        except Exception as e:
            print(f"Anthropic API call failed: {e}")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3)
    )
    async def generate_structured(
        self, *, system: str, prompt: str, model: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Generates structured content using an Anthropic Claude model.
        """
        try:
            response = await self.client.messages.create(
                model=model,
                system=system,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,  # Anthropic requires max_tokens
                response_model=response_model,
            )
            return cast(BaseModel, response)
        except Exception as e:
            print(f"Anthropic API call failed: {e}")
            raise
