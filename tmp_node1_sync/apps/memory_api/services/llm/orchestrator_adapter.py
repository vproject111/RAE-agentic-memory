"""
LLM Orchestrator Adapter.

Adapts the new LLM Orchestrator (apps.llm) to the old LLMProvider interface
used by the memory API (apps.memory_api).
"""

from typing import Type

import structlog
from pydantic import BaseModel

from apps.llm.broker.orchestrator import LLMOrchestrator
from apps.llm.models import LLMMessage, LLMRequest
from apps.memory_api.services.llm.base import LLMProvider, LLMResult, LLMResultUsage

logger = structlog.get_logger(__name__)


class OrchestratorAdapter(LLMProvider):
    """
    Adapts LLMOrchestrator to the LLMProvider protocol.
    """

    def __init__(self, orchestrator: LLMOrchestrator):
        """
        Initialize adapter.

        Args:
            orchestrator: The LLM Orchestrator instance
        """
        self.orchestrator = orchestrator

    async def generate(self, *, system: str, prompt: str, model: str) -> LLMResult:
        """
        Generate content using the orchestrator.
        """
        request = self._create_request(system, prompt, model)

        # Determine strategy from model name if it looks like a strategy
        # In Iteration 1, we might pass strategy via model param or rely on default
        # If 'model' matches a known strategy, use it. Otherwise, treat as model.
        if model in self.orchestrator.strategies_config:
            request.strategy = model
            # We don't clear request.model because orchestrator might fallback to it
            # but actually orchestrator ignores request.model if strategy is found
            # except if strategy fails.
            # Ideally request.model should be just a placeholder if strategy is used.

        response = await self.orchestrator.generate(request)

        return LLMResult(
            text=response.text,
            usage=LLMResultUsage(
                prompt_tokens=response.usage.prompt_tokens,
                candidates_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ),
            model_name=response.model_name or model,
            finish_reason=response.finish_reason,
        )

    async def generate_structured(
        self, *, system: str, prompt: str, model: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Generate structured content using the orchestrator.
        """
        request = self._create_request(system, prompt, model)

        # Enable JSON mode
        request.json_mode = True

        # Append instruction for JSON
        # (Many models need explicit instruction to output JSON)
        # We append it to the system message or prompt.
        json_instruction = f"\nRespond strictly with valid JSON matching this schema: {response_model.model_json_schema()}"

        # Find system message and append
        if request.messages and request.messages[0].role == "system":
            request.messages[0].content += json_instruction
        else:
            # Insert system message
            request.messages.insert(
                0, LLMMessage(role="system", content=json_instruction)
            )

        if model in self.orchestrator.strategies_config:
            request.strategy = model

        response = await self.orchestrator.generate(request)

        try:
            return response_model.model_validate_json(response.text)
        except Exception as e:
            logger.error(
                f"Failed to parse structured response: {e}",
                response_text=response.text,
            )
            raise ValueError(
                f"Failed to parse LLM response as {response_model.__name__}: {e}"
            )

    def _create_request(self, system: str, prompt: str, model: str) -> LLMRequest:
        """Create LLMRequest from components."""
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))

        return LLMRequest(
            model=model,
            messages=messages,
            temperature=0.0,  # Default to deterministic for structured/code
        )
