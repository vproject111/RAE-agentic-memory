"""Provider-agnostic LLM provider system.

This module provides a flexible, extensible architecture for working with multiple
LLM providers (Claude, Gemini, Ollama, OpenAI, etc.) through a common interface.

Key Components:
    - LLMProvider: Abstract base class for all providers
    - ProviderRegistry: Central registry for provider discovery and routing
    - ModelInfo: Metadata about model capabilities, costs, and tiers
    - ClaudeProvider, GeminiProvider, OllamaProvider: Concrete implementations

Usage:
    >>> from orchestrator.providers import ProviderRegistry, ClaudeProvider, GeminiProvider
    >>>
    >>> # Initialize registry
    >>> registry = ProviderRegistry()
    >>>
    >>> # Register providers
    >>> registry.register(ClaudeProvider())
    >>> registry.register(GeminiProvider())
    >>>
    >>> # Find models by criteria
    >>> models = registry.list_models(capability="code", tier=ModelTier.ADVANCED)
    >>>
    >>> # Get cheapest suitable model
    >>> best_model = registry.find_cheapest_model(capability="code")
    >>>
    >>> # Use provider
    >>> provider = registry.get_provider(best_model.provider)
    >>> result = await provider.generate(model=best_model.model_id, prompt="...")
"""

from .base import (
    GenerationResult,
    LLMProvider,
    ModelInfo,
    ModelTier,
    ProviderConfig,
    Usage,
)
from .claude import ClaudeProvider, get_claude_provider
from .config import (
    create_default_config_file,
    get_configured_registry,
    init_registry_from_config,
    load_config,
)
from .gemini import GeminiProvider, get_gemini_provider
from .ollama import OllamaProvider, get_ollama_provider
from .registry import ProviderRegistry, get_registry, init_registry

__all__ = [
    # Base types
    "LLMProvider",
    "ModelInfo",
    "ModelTier",
    "GenerationResult",
    "Usage",
    "ProviderConfig",
    # Registry
    "ProviderRegistry",
    "get_registry",
    "init_registry",
    # Providers
    "ClaudeProvider",
    "GeminiProvider",
    "OllamaProvider",
    # Convenience functions
    "get_claude_provider",
    "get_gemini_provider",
    "get_ollama_provider",
    # Configuration
    "load_config",
    "init_registry_from_config",
    "get_configured_registry",
    "create_default_config_file",
]
