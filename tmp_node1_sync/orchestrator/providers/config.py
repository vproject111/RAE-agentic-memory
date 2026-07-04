"""Provider configuration system.

Loads provider configuration from YAML file and initializes the provider registry.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .base import ProviderConfig
from .claude import ClaudeProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)


DEFAULT_CONFIG_PATH = ".orchestrator/providers.yaml"


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load provider configuration from YAML file.

    Args:
        config_path: Path to configuration file (defaults to .orchestrator/providers.yaml)

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config_file = Path(config_path)

    if not config_file.exists():
        logger.warning(f"Provider config not found: {config_path}")
        return {}

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    if not config:
        logger.warning(f"Empty provider config: {config_path}")
        return {}

    return config


def expand_env_vars(value: Any) -> Any:
    """Expand environment variables in configuration values.

    Supports ${VAR_NAME} syntax.

    Args:
        value: Configuration value (string, dict, list, or other)

    Returns:
        Value with expanded environment variables
    """
    if isinstance(value, str):
        # Simple ${VAR} expansion
        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            return os.environ.get(var_name, "")
        return value
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


def create_provider_from_config(
    provider_name: str, provider_config: Dict[str, Any]
) -> Optional[Any]:
    """Create provider instance from configuration.

    Args:
        provider_name: Provider name ('claude', 'gemini', 'ollama')
        provider_config: Provider configuration dictionary

    Returns:
        Provider instance or None if provider is disabled or fails to initialize
    """
    # Check if enabled
    if not provider_config.get("enabled", True):
        logger.info(f"Provider '{provider_name}' is disabled in config")
        return None

    # Expand environment variables in settings
    settings = expand_env_vars(provider_config.get("settings", {}))

    try:
        if provider_name == "claude":
            api_key = settings.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
            return ClaudeProvider(api_key=api_key)

        elif provider_name == "gemini":
            cli_path = settings.get("cli_path", "gemini")
            rate_limit_delay = settings.get("rate_limit_delay", True)
            min_delay = settings.get("min_delay", 1.0)
            max_delay = settings.get("max_delay", 10.0)
            return GeminiProvider(
                cli_path=cli_path,
                rate_limit_delay=rate_limit_delay,
                min_delay=min_delay,
                max_delay=max_delay,
            )

        elif provider_name == "ollama":
            endpoint = settings.get("endpoint", "http://localhost:11434")
            return OllamaProvider(endpoint=endpoint)

        else:
            logger.warning(f"Unknown provider: {provider_name}")
            return None

    except Exception as e:
        logger.error(f"Failed to create provider '{provider_name}': {e}")
        return None


def init_registry_from_config(
    config_path: Optional[str] = None, registry: Optional[ProviderRegistry] = None
) -> ProviderRegistry:
    """Initialize provider registry from configuration file.

    Args:
        config_path: Path to configuration file (defaults to .orchestrator/providers.yaml)
        registry: Existing registry to populate (creates new if None)

    Returns:
        Initialized provider registry
    """
    if registry is None:
        registry = ProviderRegistry()

    # Load config
    try:
        config = load_config(config_path)
    except Exception as e:
        logger.error(f"Failed to load provider config: {e}")
        return registry

    # Get providers section
    providers_config = config.get("providers", {})

    if not providers_config:
        logger.warning("No providers configured")
        return registry

    # Register each provider
    for provider_name, provider_config in providers_config.items():
        # Create provider instance
        provider = create_provider_from_config(provider_name, provider_config)

        if provider is None:
            continue

        # Create ProviderConfig
        provider_cfg = ProviderConfig(
            name=provider_name,
            enabled=provider_config.get("enabled", True),
            default_model=provider_config.get("default_model"),
            settings=provider_config.get("settings", {}),
        )

        # Register
        try:
            registry.register(provider, provider_cfg)
            logger.info(f"Registered provider: {provider_name}")
        except Exception as e:
            logger.error(f"Failed to register provider '{provider_name}': {e}")

    return registry


def create_default_config_file(config_path: Optional[str] = None):
    """Create default provider configuration file.

    Args:
        config_path: Path for configuration file (defaults to .orchestrator/providers.yaml)
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config_file = Path(config_path)

    # Don't overwrite existing config
    if config_file.exists():
        logger.info(f"Provider config already exists: {config_path}")
        return

    # Create directory if needed
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Default configuration
    default_config = {
        "providers": {
            "claude": {
                "enabled": True,
                "default_model": "claude-sonnet-4-5-20250929",
                "settings": {"api_key": "${ANTHROPIC_API_KEY}"},
            },
            "gemini": {
                "enabled": True,
                "default_model": "gemini-2.5-flash",
                "settings": {
                    "cli_path": "gemini",
                    "rate_limit_delay": True,
                    "min_delay": 1.0,
                    "max_delay": 10.0,
                },
            },
            "ollama": {
                "enabled": False,
                "default_model": "llama3:70b",
                "settings": {"endpoint": "http://localhost:11434"},
            },
        },
        "routing": {
            "prefer_local": False,
            "max_cost_per_task": 1.0,
            "fallback_provider": "claude",
        },
    }

    # Write to file
    with open(config_file, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Created default provider config: {config_path}")


# Convenience function
def get_configured_registry(config_path: Optional[str] = None) -> ProviderRegistry:
    """Get provider registry initialized from configuration.

    If config file doesn't exist, creates default config and initializes registry
    with default settings (Claude and Gemini enabled).

    Args:
        config_path: Path to configuration file

    Returns:
        Configured provider registry
    """
    # Create default config if it doesn't exist
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    if not Path(config_path).exists():
        logger.info("Creating default provider configuration")
        create_default_config_file(config_path)

    # Initialize registry from config
    return init_registry_from_config(config_path)
