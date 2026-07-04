"""Gemini LLM Provider implementation."""

import asyncio
import json
import logging
import os
import random
import shutil
import tempfile
from typing import List, Optional

from .base import GenerationResult, LLMProvider, ModelInfo, ModelTier, Usage

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini provider using Google Gemini CLI.

    Uses the official 'gemini' CLI tool which requires browser-based authentication
    (gemini auth login). Supports non-interactive mode via --output-format json.
    """

    def __init__(
        self,
        cli_path: str = "gemini",
        rate_limit_delay: bool = True,
        min_delay: float = 1.0,
        max_delay: float = 10.0,
    ):
        """Initialize Gemini provider.

        Args:
            cli_path: Path to gemini CLI executable (defaults to 'gemini' in PATH)
            rate_limit_delay: Whether to add random delays to avoid rate limits
            min_delay: Minimum delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 10.0)
        """
        self.cli_path = cli_path
        self.rate_limit_delay = rate_limit_delay
        self.min_delay = min_delay
        self.max_delay = max_delay

    @property
    def name(self) -> str:
        """Get provider name.

        Returns:
            Provider name 'gemini'
        """
        return "gemini"

    @property
    def available_models(self) -> List[ModelInfo]:
        """Get list of available Gemini models.

        Note: Gemini CLI (free, no API key) has rate limits. Use rate_limit_delay=True
        to add random delays (1-10s) between requests.

        Returns:
            List of Gemini model metadata
        """
        return [
            # GEMINI 3.0 - Newest (Preview)
            ModelInfo(
                provider="gemini",
                model_id="gemini-3-pro-preview",
                display_name="Gemini 3.0 Pro (Preview)",
                capabilities=[
                    "code",
                    "analysis",
                    "planning",
                    "complex_reasoning",
                    "review",
                    "research",
                    "architecture",
                ],
                context_window=200000,
                cost_per_1k_input=0.0,  # Free via CLI
                cost_per_1k_output=0.0,
                tier=ModelTier.ADVANCED,
            ),
            # GEMINI 2.5 - Latest stable
            ModelInfo(
                provider="gemini",
                model_id="gemini-2.5-pro",
                display_name="Gemini 2.5 Pro",
                capabilities=[
                    "code",
                    "analysis",
                    "planning",
                    "complex_reasoning",
                    "review",
                ],
                context_window=128000,
                cost_per_1k_input=0.0,  # Free via CLI
                cost_per_1k_output=0.0,
                tier=ModelTier.STANDARD,
            ),
            ModelInfo(
                provider="gemini",
                model_id="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash",
                capabilities=[
                    "code",
                    "analysis",
                    "simple_tasks",
                    "docs",
                    "refactoring",
                ],
                context_window=64000,
                cost_per_1k_input=0.0,  # Free via CLI
                cost_per_1k_output=0.0,
                tier=ModelTier.FAST,
            ),
            ModelInfo(
                provider="gemini",
                model_id="gemini-2.5-flash-lite",
                display_name="Gemini 2.5 Flash Lite",
                capabilities=[
                    "simple_tasks",
                    "docs",
                    "linting",
                    "formatting",
                    "simple_edits",
                ],
                context_window=32000,
                cost_per_1k_input=0.0,  # Free via CLI
                cost_per_1k_output=0.0,
                tier=ModelTier.FAST,
            ),
            # GEMINI 2.0 - Legacy (kept for compatibility)
            ModelInfo(
                provider="gemini",
                model_id="gemini-2.0-flash",
                display_name="Gemini 2.0 Flash (Legacy)",
                capabilities=["code", "analysis", "simple_tasks", "docs"],
                context_window=32000,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tier=ModelTier.FAST,
            ),
            ModelInfo(
                provider="gemini",
                model_id="gemini-2.0-pro",
                display_name="Gemini 2.0 Pro (Legacy)",
                capabilities=["code", "analysis", "planning", "review"],
                context_window=128000,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tier=ModelTier.STANDARD,
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
        """Generate completion using Gemini CLI.

        Args:
            model: Model identifier (e.g., 'gemini-2.0-flash')
            prompt: User prompt
            system_prompt: Optional system prompt (prepended to prompt)
            max_tokens: Maximum tokens to generate (not enforced by CLI)
            temperature: Sampling temperature (0.0-1.0, not exposed by CLI)
            **kwargs: Additional arguments (ignored for CLI)

        Returns:
            Generation result with content and usage

        Raises:
            Exception: If CLI call fails
        """
        # Check CLI availability
        if not await self.is_available():
            return GenerationResult(
                content="",
                error="Gemini CLI not available - install with: pip install google-genai",
            )

        # Rate limiting: Add random delay to avoid hitting rate limits
        # (Gemini CLI without API key has strict per-second and per-day limits)
        if self.rate_limit_delay:
            delay = random.uniform(self.min_delay, self.max_delay)
            logger.debug(f"Rate limit delay: {delay:.1f}s before Gemini CLI call")
            await asyncio.sleep(delay)

        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # IMPORTANT: Write prompt to temp file to avoid CLI parsing issues
            # Long prompts with newlines/special chars break when passed via -p flag
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(full_prompt)
                prompt_file = f.name

            try:
                # Build CLI command - read prompt from stdin
                cmd = [
                    self.cli_path,
                    "-m",
                    model,
                    "--output-format",
                    "json",
                ]

                logger.debug(
                    f"Calling Gemini CLI: model={model}, prompt_file={prompt_file}"
                )

                # Execute CLI with prompt from stdin
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Read prompt from file and send to stdin
                with open(prompt_file, "r") as pf:
                    prompt_content = pf.read()

                # Wait for completion (5 minute timeout)
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(input=prompt_content.encode("utf-8")),
                        timeout=300.0,
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    logger.error(f"Gemini CLI timeout for model {model}")
                    return GenerationResult(
                        content="", error="Gemini CLI timeout after 5 minutes"
                    )
            finally:
                # Clean up temp file
                try:
                    os.unlink(prompt_file)
                except Exception:
                    pass

            # Check return code
            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                logger.error(f"Gemini CLI failed: {error_msg}")
                return GenerationResult(
                    content="", error=f"Gemini CLI error: {error_msg}"
                )

            # Parse JSON output
            try:
                output_text = stdout.decode("utf-8")
                output_json = json.loads(output_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini CLI output: {e}")
                # Try to extract raw text
                content = stdout.decode("utf-8") if stdout else ""
                return GenerationResult(
                    content=content, error=f"JSON parse error: {str(e)}"
                )

            # Extract content and metadata from JSON
            content = ""
            usage = None
            metadata = {}

            # Gemini CLI JSON format may vary - handle different structures
            if isinstance(output_json, dict):
                # Try common fields
                content = output_json.get("text", "")
                if not content:
                    content = output_json.get("content", "")
                if not content:
                    content = output_json.get("response", "")

                # Try to extract usage if available
                if "usage" in output_json:
                    usage_data = output_json["usage"]
                    usage = Usage(
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                    )

                # Store other metadata
                metadata = {
                    k: v
                    for k, v in output_json.items()
                    if k not in ["text", "content", "response", "usage"]
                }

            elif isinstance(output_json, str):
                content = output_json

            logger.info(
                f"Gemini CLI call successful: model={model}, "
                f"content_length={len(content)}"
            )

            return GenerationResult(
                content=content,
                usage=usage,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Gemini CLI call failed: {e}")
            return GenerationResult(content="", error=f"Gemini CLI error: {str(e)}")

    async def is_available(self) -> bool:
        """Check if Gemini CLI is available.

        Returns:
            True if CLI is installed and authenticated
        """
        # Check if CLI exists
        if not shutil.which(self.cli_path):
            logger.warning(f"Gemini CLI not found at: {self.cli_path}")
            return False

        # Try a minimal CLI call to verify authentication
        try:
            proc = await asyncio.create_subprocess_exec(
                self.cli_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if proc.returncode != 0:
                logger.warning(f"Gemini CLI check failed: {stderr.decode('utf-8')}")
                return False

            # CLI exists, but we can't easily test auth without making an API call
            # Assume it's available if --version works
            return True

        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Gemini CLI availability check failed: {e}")
            return False


# Backward compatibility - create default instance
_default_provider: Optional[GeminiProvider] = None


def get_gemini_provider() -> GeminiProvider:
    """Get default Gemini provider instance.

    Returns:
        Singleton Gemini provider instance
    """
    global _default_provider
    if _default_provider is None:
        _default_provider = GeminiProvider()
    return _default_provider
