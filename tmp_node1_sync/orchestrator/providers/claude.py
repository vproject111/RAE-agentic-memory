"""Claude LLM Provider implementation."""

import logging
import os
from typing import List, Optional

from anthropic import AsyncAnthropic
from anthropic.types import Message

from .base import GenerationResult, LLMProvider, ModelInfo, ModelTier, Usage

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Claude provider using Anthropic API.

    Supports Claude Sonnet, Opus, and Haiku models via official Anthropic SDK.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        # Get API key and strip any whitespace (newlines, spaces, etc.)
        raw_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.api_key = raw_key.strip() if raw_key else None

        if not self.api_key:
            logger.warning(
                "No Anthropic API key provided - provider will be unavailable"
            )
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)

    @property
    def name(self) -> str:
        """Get provider name.

        Returns:
            Provider name 'claude'
        """
        return "claude"

    @property
    def available_models(self) -> List[ModelInfo]:
        """Get list of available Claude models.

        Note: Claude API uses full model identifiers, but you can also use
        simplified aliases: 'haiku', 'sonnet', 'opus' which map to latest versions.

        Returns:
            List of Claude model metadata
        """
        return [
            # SONNET - Default, balanced (most used)
            ModelInfo(
                provider="claude",
                model_id="claude-sonnet-4-5-20250929",
                display_name="Claude Sonnet 4.5",
                capabilities=[
                    "code",
                    "analysis",
                    "planning",
                    "complex_reasoning",
                    "review",
                    "refactoring",
                    "debugging",
                ],
                context_window=200000,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                tier=ModelTier.ADVANCED,
            ),
            # OPUS - Most powerful, most expensive
            ModelInfo(
                provider="claude",
                model_id="claude-opus-4-20250514",
                display_name="Claude Opus 4",
                capabilities=[
                    "code",
                    "analysis",
                    "planning",
                    "complex_reasoning",
                    "review",
                    "research",
                    "architecture",
                    "difficult_bugs",
                ],
                context_window=200000,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
                tier=ModelTier.ADVANCED,
            ),
            # HAIKU - Fast and cheap
            ModelInfo(
                provider="claude",
                model_id="claude-haiku-3-5-20241022",
                display_name="Claude Haiku 3.5",
                capabilities=[
                    "code",
                    "analysis",
                    "simple_tasks",
                    "docs",
                    "linting",
                    "formatting",
                    "simple_edits",
                ],
                context_window=200000,
                cost_per_1k_input=0.0008,
                cost_per_1k_output=0.004,
                tier=ModelTier.FAST,
            ),
            # Legacy (kept for compatibility)
            ModelInfo(
                provider="claude",
                model_id="claude-sonnet-3-5-20241022",
                display_name="Claude Sonnet 3.5 (Legacy)",
                capabilities=["code", "analysis", "planning", "complex_reasoning"],
                context_window=200000,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                tier=ModelTier.ADVANCED,
            ),
        ]

    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate completion using Claude API.

        Args:
            model: Model identifier (e.g., 'claude-sonnet-4-5-20250929')
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional Anthropic API arguments

        Returns:
            Generation result with content and usage

        Raises:
            RuntimeError: If provider is not configured
            Exception: If API call fails
        """
        if not self.client:
            return GenerationResult(
                content="", error="Claude provider not configured - missing API key"
            )

        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Build API call kwargs
            api_kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            # Add system prompt if provided
            if system_prompt:
                api_kwargs["system"] = system_prompt

            # Add any additional kwargs
            api_kwargs.update(kwargs)

            # Call API
            logger.debug(f"Calling Claude API: model={model}, max_tokens={max_tokens}")
            response: Message = await self.client.messages.create(**api_kwargs)

            # Extract content
            content = ""
            if response.content:
                # Handle text blocks
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            # Extract usage
            usage = None
            if response.usage:
                usage = Usage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )

            # Build metadata
            metadata = {
                "model": response.model,
                "stop_reason": response.stop_reason,
                "role": response.role,
            }

            logger.info(
                f"Claude API call successful: model={model}, "
                f"input_tokens={usage.input_tokens if usage else 0}, "
                f"output_tokens={usage.output_tokens if usage else 0}"
            )

            return GenerationResult(
                content=content,
                usage=usage,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return GenerationResult(content="", error=f"Claude API error: {str(e)}")

    async def is_available(self) -> bool:
        """Check if Claude provider is available.

        Returns:
            True if API key is configured
        """
        if not self.client:
            return False

        # Try a minimal API call to verify connectivity
        try:
            # Very cheap test call
            response = await self.client.messages.create(
                model="claude-haiku-3-5-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return response is not None
        except Exception as e:
            logger.warning(f"Claude availability check failed: {e}")
            return False


# Backward compatibility - create default instance
_default_provider: Optional[ClaudeProvider] = None


def get_claude_provider() -> ClaudeProvider:
    """Get default Claude provider instance.

    Returns:
        Singleton Claude provider instance
    """
    global _default_provider
    if _default_provider is None:
        _default_provider = ClaudeProvider()
    return _default_provider
