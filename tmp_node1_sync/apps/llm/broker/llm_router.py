"""
LLM Router.

Central routing and orchestration for LLM requests.
Handles provider selection, fallbacks, cost validation, and telemetry.
"""

import logging
import os
from collections.abc import AsyncIterator
from typing import Any, Dict, Optional, cast

import yaml

from ..models import (
    LLMAuthError,
    LLMChunk,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMTransientError,
)
from ..providers import (
    AnthropicProvider,
    DeepSeekProvider,
    DelegatedLLMProvider,
    GeminiProvider,
    GrokProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    QwenProvider,
)

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Router for LLM requests.

    Responsibilities:
    - Load and manage provider configurations
    - Select appropriate provider based on model
    - Handle fallbacks when providers fail
    - Emit telemetry events
    - Validate cost constraints (future enhancement)
    """

    def __init__(self, config_path: Optional[str] = None, task_repo: Any = None):
        """
        Initialize the LLM router.

        Args:
            config_path: Path to providers.yaml configuration file
            task_repo: Optional repository for delegating tasks
        """
        self.providers: Dict[str, LLMProvider] = {}
        self.task_repo = task_repo
        self.config = self._load_config(config_path)
        self._initialize_providers()

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load provider configuration from YAML file."""
        if config_path is None:
            # Default to config file in same directory as this module
            import pathlib

            config_path = str(
                pathlib.Path(__file__).parent.parent / "config" / "providers.yaml"
            )

        try:
            with open(config_path, "r") as f:
                return cast(Dict[str, Any], yaml.safe_load(f))
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}. Using empty config.")
            return {"providers": {}}

    def _initialize_providers(self):
        """Initialize all configured providers."""
        provider_classes = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
            "ollama": OllamaProvider,
            "deepseek": DeepSeekProvider,
            "qwen": QwenProvider,
            "grok": GrokProvider,
            "delegated": DelegatedLLMProvider,
        }

        # Initialize delegated provider if repo is available
        if self.task_repo:
            self.providers["delegated"] = DelegatedLLMProvider(task_repo=self.task_repo)
            logger.info("Initialized provider: delegated")

        for provider_name, provider_config in self.config.get("providers", {}).items():
            try:
                provider_class = provider_classes.get(provider_name)
                if not provider_class:
                    logger.warning(f"Unknown provider: {provider_name}")
                    continue

                # Get API key from environment if specified
                api_key_env = provider_config.get("api_key_env")
                if api_key_env:
                    api_key = os.getenv(api_key_env)
                    if not api_key:
                        logger.warning(
                            f"API key not found for {provider_name} (env: {api_key_env})"
                        )
                        continue
                else:
                    api_key = None

                # Initialize provider
                endpoint = provider_config.get("endpoint")

                # Override endpoint from env for Ollama
                if provider_name == "ollama" and os.getenv("OLLAMA_API_URL"):
                    endpoint = os.getenv("OLLAMA_API_URL")

                if provider_name == "ollama":
                    self.providers[provider_name] = provider_class(api_url=endpoint)
                elif provider_name in ["openai", "deepseek", "grok"]:
                    self.providers[provider_name] = provider_class(
                        api_key=api_key, api_base=endpoint
                    )
                else:
                    self.providers[provider_name] = provider_class(api_key=api_key)

                logger.info(f"Initialized provider: {provider_name}")

            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_name}: {e}")

    def _get_provider_for_model(self, model: str) -> Optional[LLMProvider]:
        """
        Determine which provider to use for a given model.

        This uses simple heuristics based on model name prefixes.
        In production, this should be driven by configuration.
        """
        model_lower = model.lower()

        # Mapping of model prefixes to providers
        if "gpt" in model_lower or "o1" in model_lower:
            return self.providers.get("openai")
        elif "claude" in model_lower:
            return self.providers.get("anthropic")
        elif "gemini" in model_lower:
            return self.providers.get("gemini")
        elif (
            "llama" in model_lower
            or "mistral" in model_lower
            or "local_deepseek" in model_lower
            or "deepseek-r1" in model_lower
            or "phi" in model_lower
        ):
            return self.providers.get("ollama")
        elif "deepseek" in model_lower:
            return self.providers.get("deepseek")
        elif "qwen" in model_lower:
            return self.providers.get("qwen")
        elif "grok" in model_lower:
            return self.providers.get("grok")

        # Default to first available provider
        if self.providers:
            return next(iter(self.providers.values()))

        return None

    async def complete(self, request: LLMRequest, fallback: bool = True) -> LLMResponse:
        """
        Generate a complete response using the appropriate provider.

        Args:
            request: Standardized LLM request
            fallback: Whether to attempt fallback on failure

        Returns:
            Standardized LLM response

        Raises:
            LLMError: If all providers fail
        """
        provider = self._get_provider_for_model(request.model)

        if not provider:
            raise ValueError(f"No provider available for model: {request.model}")

        try:
            logger.info(
                f"llm.provider.start - provider={provider.name} model={request.model}"
            )

            response = await provider.complete(request)

            logger.info(
                f"llm.provider.ok - provider={provider.name} "
                f"tokens={response.usage.total_tokens} "
                f"finish_reason={response.finish_reason}"
            )

            return response

        except LLMAuthError:
            logger.error(f"llm.provider.error - provider={provider.name} error=auth")
            raise  # Don't retry auth errors

        except LLMRateLimitError:
            logger.warning(
                f"llm.provider.error - provider={provider.name} error=rate_limit"
            )
            if fallback:
                logger.info("llm.provider.fallback - attempting fallback")
                # In production, implement intelligent fallback logic
                # For now, just re-raise
            raise

        except LLMTransientError:
            logger.warning(
                f"llm.provider.error - provider={provider.name} error=transient"
            )
            if fallback:
                logger.info("llm.provider.retry - retrying request")
                # Provider already has retry logic via tenacity
            raise

        except Exception as e:
            logger.error(
                f"llm.provider.error - provider={provider.name} error=unknown: {e}"
            )
            raise

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate a streaming response using the appropriate provider.

        Args:
            request: Standardized LLM request

        Yields:
            Chunks of the response
        """
        provider = self._get_provider_for_model(request.model)

        if not provider:
            raise ValueError(f"No provider available for model: {request.model}")

        if not provider.supports_streaming:
            raise ValueError(f"Provider {provider.name} does not support streaming")

        try:
            logger.info(
                f"llm.provider.start - provider={provider.name} model={request.model} streaming=true"
            )

            async for chunk in provider.stream(request):
                yield chunk

            logger.info(
                f"llm.provider.ok - provider={provider.name} streaming=complete"
            )

        except Exception as e:
            logger.error(
                f"llm.provider.error - provider={provider.name} error=streaming: {e}"
            )
            raise
