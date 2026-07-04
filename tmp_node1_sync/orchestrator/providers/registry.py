"""Provider registry for managing LLM providers."""

import logging
from typing import Any, Dict, List, Optional

from .base import LLMProvider, ModelInfo, ModelTier, ProviderConfig

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Central registry for LLM providers.

    Manages provider registration, model discovery, and routing decisions.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._providers: Dict[str, LLMProvider] = {}
        self._models: Dict[str, ModelInfo] = {}  # model_id -> ModelInfo
        self._configs: Dict[str, ProviderConfig] = {}

    def register(self, provider: LLMProvider, config: Optional[ProviderConfig] = None):
        """Register a provider.

        Args:
            provider: Provider instance
            config: Optional provider configuration
        """
        provider_name = provider.name

        # Store provider
        self._providers[provider_name] = provider

        # Store config
        if config:
            self._configs[provider_name] = config
        elif provider_name not in self._configs:
            # Default config
            self._configs[provider_name] = ProviderConfig(
                name=provider_name, enabled=True
            )

        # Index all models
        for model_info in provider.available_models:
            self._models[model_info.model_id] = model_info

        logger.info(
            f"Registered provider '{provider_name}' with "
            f"{len(provider.available_models)} models"
        )

    def unregister(self, provider_name: str):
        """Unregister a provider.

        Args:
            provider_name: Name of provider to unregister
        """
        if provider_name in self._providers:
            provider = self._providers[provider_name]

            # Remove models
            for model_info in provider.available_models:
                if model_info.model_id in self._models:
                    del self._models[model_info.model_id]

            # Remove provider
            del self._providers[provider_name]

            # Remove config
            if provider_name in self._configs:
                del self._configs[provider_name]

            logger.info(f"Unregistered provider '{provider_name}'")

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None
        """
        return self._providers.get(name)

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get model metadata.

        Args:
            model_id: Model identifier

        Returns:
            Model information or None
        """
        return self._models.get(model_id)

    def list_providers(self, enabled_only: bool = True) -> List[str]:
        """List registered providers.

        Args:
            enabled_only: Only return enabled providers

        Returns:
            List of provider names
        """
        if enabled_only:
            return [name for name, config in self._configs.items() if config.enabled]
        return list(self._providers.keys())

    def list_models(
        self,
        provider: Optional[str] = None,
        capability: Optional[str] = None,
        tier: Optional[ModelTier] = None,
        max_cost: Optional[float] = None,
        enabled_providers_only: bool = True,
    ) -> List[ModelInfo]:
        """List models matching criteria.

        Args:
            provider: Filter by provider name
            capability: Required capability (e.g., 'code')
            tier: Required tier
            max_cost: Maximum cost per 1K input tokens
            enabled_providers_only: Only include models from enabled providers

        Returns:
            List of matching models
        """
        models = list(self._models.values())

        # Filter by provider
        if provider:
            models = [m for m in models if m.provider == provider]

        # Filter by enabled providers
        if enabled_providers_only:
            enabled = self.list_providers(enabled_only=True)
            models = [m for m in models if m.provider in enabled]

        # Filter by capability
        if capability:
            models = [m for m in models if m.supports(capability)]

        # Filter by tier
        if tier:
            models = [m for m in models if m.tier == tier]

        # Filter by cost
        if max_cost is not None:
            models = [m for m in models if m.cost_per_1k_input <= max_cost]

        return models

    def find_cheapest_model(
        self, capability: Optional[str] = None, tier: Optional[ModelTier] = None
    ) -> Optional[ModelInfo]:
        """Find cheapest model matching criteria.

        Args:
            capability: Required capability
            tier: Required tier

        Returns:
            Cheapest matching model or None
        """
        models = self.list_models(capability=capability, tier=tier)

        if not models:
            return None

        return min(models, key=lambda m: m.cost_per_1k_input)

    def find_best_model(
        self,
        capability: Optional[str] = None,
        prefer_local: bool = False,
        max_cost: Optional[float] = None,
    ) -> Optional[ModelInfo]:
        """Find best model matching criteria.

        Args:
            capability: Required capability
            prefer_local: Prefer local models (Ollama)
            max_cost: Maximum cost constraint

        Returns:
            Best matching model or None
        """
        models = self.list_models(capability=capability, max_cost=max_cost)

        if not models:
            return None

        # Prefer local if requested
        if prefer_local:
            local_models = [m for m in models if m.cost_per_1k_input == 0.0]
            if local_models:
                # Choose highest tier local model
                return max(local_models, key=lambda m: m.tier.value)

        # Otherwise choose based on tier (higher is better), then cost (lower is better)
        tier_priority = {
            ModelTier.ADVANCED: 3,
            ModelTier.STANDARD: 2,
            ModelTier.FAST: 1,
        }

        models.sort(key=lambda m: (-tier_priority[m.tier], m.cost_per_1k_input))
        return models[0]

    async def check_availability(self) -> Dict[str, bool]:
        """Check availability of all providers.

        Returns:
            Dictionary mapping provider names to availability status
        """
        availability = {}

        for name, provider in self._providers.items():
            config = self._configs.get(name)
            if config and not config.enabled:
                availability[name] = False
                continue

            try:
                is_available = await provider.is_available()
                availability[name] = is_available
            except Exception as e:
                logger.warning(f"Provider '{name}' availability check failed: {e}")
                availability[name] = False

        return availability

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary.

        Returns:
            Summary dictionary
        """
        return {
            "total_providers": len(self._providers),
            "enabled_providers": len(self.list_providers(enabled_only=True)),
            "total_models": len(self._models),
            "providers": {
                name: {
                    "enabled": self._configs[name].enabled,
                    "models": len(provider.available_models),
                    "default_model": self._configs[name].default_model,
                }
                for name, provider in self._providers.items()
            },
        }


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get global provider registry.

    Returns:
        Provider registry instance
    """
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def init_registry() -> ProviderRegistry:
    """Initialize fresh global registry.

    Returns:
        New provider registry instance
    """
    global _registry
    _registry = ProviderRegistry()
    return _registry
