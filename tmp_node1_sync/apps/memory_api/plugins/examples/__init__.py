"""
Example Plugins for RAE Memory API

This package contains example plugins demonstrating the plugin system.
"""

from apps.memory_api.plugins.examples.analytics_tracker import AnalyticsTrackerPlugin
from apps.memory_api.plugins.examples.memory_validator import MemoryValidatorPlugin
from apps.memory_api.plugins.examples.slack_notifier import SlackNotifierPlugin

__all__ = ["SlackNotifierPlugin", "MemoryValidatorPlugin", "AnalyticsTrackerPlugin"]
