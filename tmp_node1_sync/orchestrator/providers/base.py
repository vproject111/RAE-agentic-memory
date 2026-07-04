"""Base interfaces for LLM providers - provider-agnostic architecture."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ModelTier(Enum):
    """Model capability tiers for routing."""

    FAST = "fast"  # Fast, cheap models (e.g., Gemini Flash, local small models)
    STANDARD = "standard"  # Standard models (e.g., Gemini Pro, GPT-3.5)
    ADVANCED = "advanced"  # Advanced models (e.g., Claude Sonnet, GPT-4)


@dataclass
class Usage:
    """Token usage information."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class GenerationResult:
    """Result from LLM generation."""

    content: str
    usage: Optional[Usage] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if generation was successful."""
        return self.error is None


@dataclass
class ModelInfo:
    """Metadata about an LLM model."""

    provider: str  # Provider name (e.g., 'claude', 'gemini', 'ollama')
    model_id: str  # Model identifier (e.g., 'claude-sonnet-4-5')
    display_name: str  # Human-readable name
    capabilities: List[str]  # Capabilities (e.g., ['code', 'analysis', 'planning'])
    context_window: int  # Max context tokens
    cost_per_1k_input: float  # USD per 1K input tokens
    cost_per_1k_output: float  # USD per 1K output tokens
    tier: ModelTier  # Capability tier

    def supports(self, capability: str) -> bool:
        """Check if model supports a capability.

        Args:
            capability: Capability to check (e.g., 'code', 'planning')

        Returns:
            True if model supports capability
        """
        return capability.lower() in [c.lower() for c in self.capabilities]

    def estimated_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers (Claude, Gemini, Ollama, OpenAI, etc.) must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get provider name (e.g., 'claude', 'gemini', 'ollama').

        Returns:
            Provider name
        """
        pass

    @property
    @abstractmethod
    def available_models(self) -> List[ModelInfo]:
        """Get list of available models from this provider.

        Returns:
            List of model metadata
        """
        pass

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate completion from model.

        Args:
            model: Model identifier
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Provider-specific arguments

        Returns:
            Generation result with content and usage

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is configured and available.

        Returns:
            True if provider is ready to use
        """
        pass

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about specific model.

        Args:
            model_id: Model identifier

        Returns:
            Model information or None if not found
        """
        for model in self.available_models:
            if model.model_id == model_id:
                return model
        return None

    def list_models(
        self,
        capability: Optional[str] = None,
        tier: Optional[ModelTier] = None,
        max_cost: Optional[float] = None,
    ) -> List[ModelInfo]:
        """List models matching criteria.

        Args:
            capability: Required capability (e.g., 'code')
            tier: Required tier
            max_cost: Maximum cost per 1K input tokens

        Returns:
            List of matching models
        """
        models = self.available_models

        if capability:
            models = [m for m in models if m.supports(capability)]
        if tier:
            models = [m for m in models if m.tier == tier]
        if max_cost is not None:
            models = [m for m in models if m.cost_per_1k_input <= max_cost]

        return models


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    name: str
    enabled: bool = True
    default_model: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfig":
        """Create from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Provider configuration
        """
        return cls(
            name=data["name"],
            enabled=data.get("enabled", True),
            default_model=data.get("default_model"),
            settings=data.get("settings", {}),
        )
