from typing import Any, Optional, Type, cast

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from ...config import settings
from .base import LLMProvider, LLMResult, LLMResultUsage


class OpenAIProvider(LLMProvider):
    """
    An LLM provider that uses the OpenAI API.
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.OPENAI_API_KEY
        if not key:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.client = instructor.patch(AsyncOpenAI(api_key=key))

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3)
    )
    async def generate(self, *, system: str, prompt: str, model: str) -> LLMResult:
        """
        Generates content using the OpenAI model.
        """
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )

            usage_data = cast(Any, response.usage)
            usage = LLMResultUsage(
                prompt_tokens=usage_data.prompt_tokens if usage_data else 0,
                candidates_tokens=usage_data.completion_tokens if usage_data else 0,
                total_tokens=usage_data.total_tokens if usage_data else 0,
            )

            return LLMResult(
                text=response.choices[0].message.content or "",
                usage=usage,
                model_name=model,
                finish_reason=response.choices[0].finish_reason or "stop",
            )
        except Exception as e:
            print(f"OpenAI API call failed: {e}")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3)
    )
    async def generate_structured(
        self, *, system: str, prompt: str, model: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Generates structured content using the OpenAI model.
        """
        try:
            response = await cast(Any, self.client).chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_model=response_model,
            )
            return cast(BaseModel, response)
        except Exception as e:
            print(f"OpenAI API call failed: {e}")
            raise
