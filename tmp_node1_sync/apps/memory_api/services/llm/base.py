from typing import NamedTuple, Protocol, Type

from pydantic import BaseModel


class LLMResultUsage(BaseModel):
    """
    Represents the token usage metadata from an LLM call.
    """

    prompt_tokens: int
    candidates_tokens: int
    total_tokens: int


class LLMResult(NamedTuple):
    """
    Represents the result of an LLM generation call.
    """

    text: str
    usage: LLMResultUsage
    model_name: str
    finish_reason: str = "stop"


class LLMProvider(Protocol):
    """
    A protocol defining the interface for a Large Language Model provider.
    """

    async def generate(self, *, system: str, prompt: str, model: str) -> LLMResult:
        """
        Generates content using the specified model and inputs.

        Args:
            system: The system instruction or context.
            prompt: The user prompt.
            model: The name of the model to use.

        Returns:
            An LLMResult containing the generated text and usage metadata.
        """
        ...

    async def generate_structured(
        self, *, system: str, prompt: str, model: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Generates structured content using the specified model and inputs.

        Args:
            system: The system instruction or context.
            prompt: The user prompt.
            model: The name of the model to use.
            response_model: The Pydantic model to parse the response into.

        Returns:
            An instance of the response_model.
        """
        ...
