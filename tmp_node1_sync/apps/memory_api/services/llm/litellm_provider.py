from typing import Type

import litellm
from pydantic import BaseModel

from ...config import settings
from .base import LLMProvider, LLMResult, LLMResultUsage


class LiteLLMProvider(LLMProvider):
    """
    A generic provider that uses litellm to call any supported model.
    The user is responsible for setting the correct environment variables for API keys.
    """

    def __init__(self, model_name: str | None = None):
        if model_name:
            self.model = model_name
        else:
            self.model = settings.RAE_LLM_MODEL_DEFAULT

    async def generate(
        self, *, system: str, prompt: str, model: str, **kwargs
    ) -> LLMResult:
        """
        Generates a response from the specified LLM model.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        # Call litellm
        response = await litellm.acompletion(model=model, messages=messages, **kwargs)

        usage = LLMResultUsage(
            prompt_tokens=response.usage.prompt_tokens,
            candidates_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )
        # Here we could do more processing, e.g., on usage stats
        # For now, just return the text
        return LLMResult(
            text=response.choices[0].message.content,
            usage=usage,
            model_name=model,
            finish_reason=response.choices[0].finish_reason,
        )

    async def generate_structured(
        self,
        *,
        system: str,
        prompt: str,
        model: str,
        response_model: Type[BaseModel],
        **kwargs,
    ) -> BaseModel:
        """
        Generates a structured response from the specified LLM model.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        # Call litellm
        response = await litellm.acompletion(model=model, messages=messages, **kwargs)

        content = response.choices[0].message.content
        return response_model.model_validate_json(content)
