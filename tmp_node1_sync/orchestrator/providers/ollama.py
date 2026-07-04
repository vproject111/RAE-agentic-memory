"""Ollama LLM Provider implementation.

Example provider showing how to integrate local models. Ollama runs models locally
via HTTP API (default: http://localhost:11434).
"""

import logging
from typing import List, Optional

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .base import GenerationResult, LLMProvider, ModelInfo, ModelTier, Usage

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM inference.

    Requires Ollama running locally (https://ollama.ai/).
    Install: curl https://ollama.ai/install.sh | sh
    Run: ollama serve
    """

    def __init__(self, endpoint: str = "http://localhost:11434"):
        """Initialize Ollama provider.

        Args:
            endpoint: Ollama API endpoint
        """
        self.endpoint = endpoint.rstrip("/")

        if not AIOHTTP_AVAILABLE:
            logger.warning(
                "aiohttp not installed - Ollama provider will be unavailable"
            )

    @property
    def name(self) -> str:
        """Get provider name.

        Returns:
            Provider name 'ollama'
        """
        return "ollama"

    @property
    def available_models(self) -> List[ModelInfo]:
        """Get list of common Ollama models.

        Note: Actual availability depends on which models are pulled locally.
        Use 'ollama pull <model>' to download models.

        Returns:
            List of common Ollama model metadata
        """
        return [
            ModelInfo(
                provider="ollama",
                model_id="llama3:70b",
                display_name="Llama 3 70B",
                capabilities=["code", "analysis", "planning", "complex_reasoning"],
                context_window=8192,
                cost_per_1k_input=0.0,  # Local, free
                cost_per_1k_output=0.0,
                tier=ModelTier.STANDARD,
            ),
            ModelInfo(
                provider="ollama",
                model_id="llama3:8b",
                display_name="Llama 3 8B",
                capabilities=["code", "analysis", "simple_tasks"],
                context_window=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tier=ModelTier.FAST,
            ),
            ModelInfo(
                provider="ollama",
                model_id="codellama:34b",
                display_name="CodeLlama 34B",
                capabilities=["code", "analysis"],
                context_window=16384,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tier=ModelTier.STANDARD,
            ),
            ModelInfo(
                provider="ollama",
                model_id="codellama:13b",
                display_name="CodeLlama 13B",
                capabilities=["code"],
                context_window=16384,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tier=ModelTier.FAST,
            ),
            ModelInfo(
                provider="ollama",
                model_id="mistral:7b",
                display_name="Mistral 7B",
                capabilities=["code", "analysis", "simple_tasks"],
                context_window=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tier=ModelTier.FAST,
            ),
            ModelInfo(
                provider="ollama",
                model_id="mixtral:8x7b",
                display_name="Mixtral 8x7B",
                capabilities=["code", "analysis", "planning"],
                context_window=32768,
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
        """Generate completion using Ollama API.

        Args:
            model: Model identifier (e.g., 'llama3:70b')
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional Ollama API arguments

        Returns:
            Generation result with content and usage

        Raises:
            RuntimeError: If aiohttp is not installed
            Exception: If API call fails
        """
        if not AIOHTTP_AVAILABLE:
            return GenerationResult(
                content="", error="aiohttp not installed - run: pip install aiohttp"
            )

        try:
            # Build request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt

            # Add any additional options
            if kwargs:
                payload["options"].update(kwargs)

            logger.debug(f"Calling Ollama API: model={model}, endpoint={self.endpoint}")

            # Call API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300.0),  # 5 minute timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"Ollama API error: {response.status} - {error_text}"
                        )
                        return GenerationResult(
                            content="",
                            error=f"Ollama API error {response.status}: {error_text}",
                        )

                    result = await response.json()

            # Extract content
            content = result.get("response", "")

            # Extract usage (Ollama provides token counts)
            usage = None
            if "prompt_eval_count" in result or "eval_count" in result:
                usage = Usage(
                    input_tokens=result.get("prompt_eval_count", 0),
                    output_tokens=result.get("eval_count", 0),
                )

            # Build metadata
            metadata = {
                "model": result.get("model"),
                "done": result.get("done"),
                "total_duration": result.get("total_duration"),
                "load_duration": result.get("load_duration"),
                "prompt_eval_duration": result.get("prompt_eval_duration"),
                "eval_duration": result.get("eval_duration"),
            }

            logger.info(
                f"Ollama API call successful: model={model}, "
                f"input_tokens={usage.input_tokens if usage else 0}, "
                f"output_tokens={usage.output_tokens if usage else 0}"
            )

            return GenerationResult(
                content=content,
                usage=usage,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            return GenerationResult(content="", error=f"Ollama API error: {str(e)}")

    async def is_available(self) -> bool:
        """Check if Ollama is running and available.

        Returns:
            True if Ollama server is accessible
        """
        if not AIOHTTP_AVAILABLE:
            return False

        try:
            # Check health endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5.0),
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.warning(f"Ollama availability check failed: {e}")
            return False


# Backward compatibility - create default instance
_default_provider: Optional[OllamaProvider] = None


def get_ollama_provider() -> OllamaProvider:
    """Get default Ollama provider instance.

    Returns:
        Singleton Ollama provider instance
    """
    global _default_provider
    if _default_provider is None:
        _default_provider = OllamaProvider()
    return _default_provider
