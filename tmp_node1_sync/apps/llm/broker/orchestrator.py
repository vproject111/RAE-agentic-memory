"""
LLM Orchestrator.

Decouples RAE Core from specific LLM models and providers.
Implements strategies (Single, Fallback) and handles configuration.
"""

import logging
import os
from typing import Any, Dict, Optional, cast

import yaml

from ..models import LLMRequest, LLMResponse
from .llm_router import LLMRouter

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """
    Orchestrator for LLM interactions.

    Decides WHICH model to use based on strategy/tags,
    and handles fallback logic.
    """

    def __init__(
        self,
        router: Optional[LLMRouter] = None,
        config_path: Optional[str] = None,
        task_repo: Any = None,
    ):
        """
        Initialize Orchestrator.

        Args:
            router: Initialized LLMRouter (if None, creates new one)
            config_path: Path to llm_config.yaml
            task_repo: Optional repository for delegating tasks
        """
        self.router = router or LLMRouter(task_repo=task_repo)
        self.config = self._load_config(config_path)

        # Override default model_name with environment variable if set
        env_model_name = os.getenv("LLM_MODEL_NAME")
        if env_model_name:
            for model_entry in self.config.get("models", []):
                if (
                    model_entry.get("id") == "openai_gpt4o"
                ):  # Targeting the default primary model
                    model_entry["model_name"] = env_model_name
                    logger.info(
                        f"Overriding openai_gpt4o model_name with LLM_MODEL_NAME from env: {env_model_name}"
                    )
                    break  # Assuming only one entry for openai_gpt4o

        self.models_config = {m["id"]: m for m in self.config.get("models", [])}
        self.strategies_config = self.config.get("strategies", {})
        self.default_strategy = self.config.get("default_strategy", "default")

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load orchestrator configuration."""
        if config_path is None:
            # Default to apps/llm/config/llm_config.yaml
            import pathlib

            config_path = str(
                pathlib.Path(__file__).parent.parent / "config" / "llm_config.yaml"
            )

        try:
            with open(config_path, "r") as f:
                return cast(Dict[str, Any], yaml.safe_load(f))
        except FileNotFoundError:
            logger.warning(
                f"Orchestrator config not found: {config_path}. Using defaults."
            )
            return {}

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using the appropriate strategy.

        Args:
            request: LLM request with optional strategy/tags

        Returns:
            LLMResponse
        """
        strategy_name = request.strategy or self.default_strategy
        strategy_config = self.strategies_config.get(strategy_name)

        if not strategy_config:
            logger.warning(
                f"Strategy '{strategy_name}' not found. Falling back to default strategy '{self.default_strategy}'."
            )
            strategy_name = self.default_strategy
            strategy_config = self.strategies_config.get(strategy_name)

        if not strategy_config:
            # Total fallback if configuration is broken
            logger.error("No valid strategy found. Using request model directly.")
            return await self.router.complete(request)

        mode = strategy_config.get("mode", "single")

        if mode == "single":
            return await self._execute_single(request, strategy_config)
        elif mode == "fallback":
            return await self._execute_fallback(request, strategy_config)
        else:
            logger.error(f"Unknown strategy mode: {mode}. Using single.")
            return await self._execute_single(request, strategy_config)

    async def _execute_single(
        self, request: LLMRequest, strategy_config: Dict[str, Any]
    ) -> LLMResponse:
        """Execute single model strategy."""
        model_id = strategy_config.get("primary")
        if not model_id:
            raise ValueError("Strategy 'single' requires 'primary' model_id")

        return await self._call_model(request, model_id)

    async def _execute_fallback(
        self, request: LLMRequest, strategy_config: Dict[str, Any]
    ) -> LLMResponse:
        """Execute fallback strategy."""
        primary_id = strategy_config.get("primary")
        fallback_id = strategy_config.get("fallback")

        if not primary_id:
            raise ValueError("Strategy 'fallback' requires 'primary' model_id")

        try:
            return await self._call_model(request, primary_id)
        except Exception as e:
            logger.warning(
                f"Primary model {primary_id} failed: {e}. Attempting fallback to {fallback_id}"
            )
            if not fallback_id:
                raise e

            return await self._call_model(request, fallback_id)

    async def _call_model(self, request: LLMRequest, model_id: str) -> LLMResponse:
        """Resolve model_id and call the provider."""
        model_conf = self.models_config.get(model_id)
        if not model_conf:
            # If model_id is not in config, assume it's a direct model name (legacy support)
            # Copy request to avoid mutating original
            import copy

            req_copy = copy.copy(request)
            req_copy.model = model_id
            return await self.router.complete(req_copy)

        if not model_conf.get("enabled", True):
            raise ValueError(f"Model {model_id} is disabled")

        provider_name = model_conf["provider"]
        real_model_name = model_conf["model_name"]

        # Get provider from router
        provider = self.router.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} not configured in Router")

        # Update request with real model name
        import copy

        req_copy = copy.copy(request)
        req_copy.model = real_model_name

        logger.info(
            f"Orchestrator calling {provider_name}/{real_model_name} (id={model_id})"
        )

        # Call provider directly (bypassing router's heuristic selection)
        return await provider.complete(req_copy)
