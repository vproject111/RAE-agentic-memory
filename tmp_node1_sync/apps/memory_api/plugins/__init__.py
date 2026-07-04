"""
Plugin System for RAE Memory API

Allows extending RAE with custom functionality.
"""

from apps.memory_api.plugins.base import (
    Plugin,
    PluginHook,
    PluginMetadata,
    PluginRegistry,
)

__all__ = ["Plugin", "PluginMetadata", "PluginHook", "PluginRegistry"]
