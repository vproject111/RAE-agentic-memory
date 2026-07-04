"""Claude API adapter for orchestrator."""

import asyncio
import logging
import os
from typing import Optional

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

from .base import AgentContext, AgentResult, ModelAdapter, ModelType

logger = logging.getLogger(__name__)


class ClaudeAdapter(ModelAdapter):
    """Adapter for Claude API."""

    def __init__(
        self, model_type: ModelType, working_dir: str, api_key: Optional[str] = None
    ):
        """Initialize Claude adapter.

        Args:
            model_type: Claude model type (only SONNET supported)
            working_dir: Working directory for operations
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        if model_type != ModelType.CLAUDE_SONNET:
            raise ValueError(f"Invalid model type for Claude: {model_type}")

        super().__init__(model_type, working_dir)

        # Get API key and strip any whitespace (newlines, spaces, etc.)
        raw_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.api_key = raw_key.strip() if raw_key else None

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Set via environment or pass to constructor."
            )

        # Initialize client
        if AsyncAnthropic is None:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model_name = "claude-sonnet-4-5-20250929"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute task with Claude API.

        Args:
            context: Agent execution context

        Returns:
            Result of execution
        """
        try:
            # Build prompt from context
            prompt = self._build_prompt(context)

            logger.info(
                f"Claude API call: model={self.model_name}, prompt_len={len(prompt)}"
            )
            logger.debug(f"Prompt preview: {prompt[:200]}...")

            # Call Claude API
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=8192,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                timeout=300.0,  # 5 minutes
            )

            logger.info(
                f"Claude API success: input={response.usage.input_tokens}, output={response.usage.output_tokens}"
            )

            # Extract text from response
            output = ""
            for block in response.content:
                if hasattr(block, "text"):
                    output += block.text

            return AgentResult(
                success=True,
                output=output,
                metadata={
                    "model": self.model_name,
                    "task_type": context.task_type,
                    "complexity": context.complexity.value,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                },
            )

        except asyncio.TimeoutError:
            logger.error("Claude API timeout after 5 minutes")
            return AgentResult(
                success=False,
                output="",
                error="Claude API timed out after 5 minutes",
            )
        except Exception as e:
            logger.error(
                f"Claude API error: {type(e).__name__}: {str(e)}", exc_info=True
            )
            return AgentResult(
                success=False,
                output="",
                error=f"Claude API error: {str(e)}",
            )

    def _build_prompt(self, context: AgentContext) -> str:
        """Build prompt from context.

        Args:
            context: Agent execution context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Task: {context.task_description}",
            f"Type: {context.task_type}",
            f"Complexity: {context.complexity.value}",
            f"Risk: {context.risk.value}",
            f"Working Directory: {context.working_directory}",
        ]

        if context.files_to_read:
            prompt_parts.append(
                "\nFiles to consider:\n- " + "\n- ".join(context.files_to_read)
            )

        if context.additional_context:
            prompt_parts.append("\nAdditional Context:")
            for key, value in context.additional_context.items():
                prompt_parts.append(f"- {key}: {value}")

        return "\n\n".join(prompt_parts)

    async def is_available(self) -> bool:
        """Check if Claude API is available and configured.

        Returns:
            True if Claude API is ready to use
        """
        try:
            # Try a minimal API call
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
                timeout=10.0,
            )
            return response.id is not None
        except Exception:
            return False

    async def get_cost_per_1k_tokens(self) -> float:
        """Get cost per 1K tokens for this model.

        Returns:
            Cost in USD per 1K tokens (input + output average)
        """
        # Claude Sonnet 4.5 pricing (as of Dec 2024)
        # Input: $0.003/1K, Output: $0.015/1K
        # Average for mixed workload
        return 0.003  # Conservative estimate (mostly input)
