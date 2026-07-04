"""
RAE Telemetry Profiles

Provides profile-based telemetry configuration for different environments:
- Development: Full data, detailed events, low sampling
- Research: Full data for scientific analysis, no PII scrubbing
- Production: Sampling, filtered attributes, performance optimized
- Government: PII scrubbing, compliance, audit trails

Profile selection via environment variable: RAE_TELEMETRY_PROFILE

Based on improvements plan:
"W praktyce: kod RAE jest jeden, różnią się tylko profile"
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set, cast

import structlog

logger = structlog.get_logger(__name__)


class TelemetryProfile(str, Enum):
    """Telemetry profile types."""

    DEVELOPMENT = "dev"
    RESEARCH = "research"
    PRODUCTION = "prod"
    GOVERNMENT = "gov"


@dataclass
class ProfileConfig:
    """
    Configuration for a telemetry profile.

    Attributes:
        name: Profile name
        sampling_rate: Span sampling rate (0.0-1.0)
        include_sensitive: Include sensitive attributes (prompts, responses)
        enable_pii_scrubbing: Enable PII scrubbing
        retention_days: Data retention in days
        max_attribute_length: Max length for string attributes
        excluded_attributes: Attributes to exclude from spans
        export_format: Export format (otlp, json, parquet)
        enable_metrics: Enable metrics collection
        enable_logging: Enable logging instrumentation
    """

    name: str
    sampling_rate: float
    include_sensitive: bool
    enable_pii_scrubbing: bool
    retention_days: int
    max_attribute_length: int
    excluded_attributes: Set[str]
    export_format: str
    enable_metrics: bool
    enable_logging: bool


# ============================================================================
# Profile Definitions
# ============================================================================

PROFILE_CONFIGS = {
    TelemetryProfile.DEVELOPMENT: ProfileConfig(
        name="Development",
        sampling_rate=1.0,  # Trace everything
        include_sensitive=True,  # Include prompts, responses
        enable_pii_scrubbing=False,  # No scrubbing in dev
        retention_days=7,  # Short retention
        max_attribute_length=10000,  # Long attributes for debugging
        excluded_attributes=set(),  # Include all attributes
        export_format="otlp",  # Standard OTLP
        enable_metrics=True,
        enable_logging=True,
    ),
    TelemetryProfile.RESEARCH: ProfileConfig(
        name="Research",
        sampling_rate=1.0,  # Trace everything for analysis
        include_sensitive=True,  # Full data for research
        enable_pii_scrubbing=True,  # Anonymize PII
        retention_days=90,  # Longer retention for analysis
        max_attribute_length=5000,
        excluded_attributes=set(),  # Include all attributes
        export_format="otlp",  # Can also export to ClickHouse/Parquet
        enable_metrics=True,
        enable_logging=True,
    ),
    TelemetryProfile.PRODUCTION: ProfileConfig(
        name="Production",
        sampling_rate=0.1,  # Sample 10% of spans
        include_sensitive=False,  # Exclude prompts/responses
        enable_pii_scrubbing=True,  # Always scrub PII
        retention_days=30,  # Standard retention
        max_attribute_length=1000,  # Shorter attributes
        excluded_attributes={
            "llm.prompt",
            "llm.response",
            "memory.content",
            "user.email",
            "user.name",
        },
        export_format="otlp",
        enable_metrics=True,
        enable_logging=False,  # Reduce overhead
    ),
    TelemetryProfile.GOVERNMENT: ProfileConfig(
        name="Government/Medical",
        sampling_rate=1.0,  # Trace everything for compliance
        include_sensitive=False,  # Never include sensitive data
        enable_pii_scrubbing=True,  # Always scrub PII
        retention_days=365,  # Long retention for compliance
        max_attribute_length=500,  # Short attributes
        excluded_attributes={
            "llm.prompt",
            "llm.response",
            "memory.content",
            "user.email",
            "user.name",
            "user.phone",
            "user.address",
        },
        export_format="otlp",  # Export to SIEM/audit systems
        enable_metrics=True,
        enable_logging=True,  # Full logging for audit
    ),
}


# ============================================================================
# Profile Manager
# ============================================================================


class TelemetryProfileManager:
    """
    Manages telemetry profiles and applies profile-specific configurations.

    Singleton pattern ensures consistent profile across the application.
    """

    _instance = None
    _current_profile: Optional[ProfileConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize profile from environment."""
        profile_name = os.getenv("RAE_TELEMETRY_PROFILE", "dev").lower()

        # Map profile name to enum
        profile_map = {
            "dev": TelemetryProfile.DEVELOPMENT,
            "development": TelemetryProfile.DEVELOPMENT,
            "research": TelemetryProfile.RESEARCH,
            "prod": TelemetryProfile.PRODUCTION,
            "production": TelemetryProfile.PRODUCTION,
            "gov": TelemetryProfile.GOVERNMENT,
            "government": TelemetryProfile.GOVERNMENT,
        }

        profile_enum = profile_map.get(profile_name, TelemetryProfile.DEVELOPMENT)
        self._current_profile = PROFILE_CONFIGS[profile_enum]

        logger.info(
            "telemetry_profile_initialized",
            profile=self._current_profile.name,
            sampling_rate=self._current_profile.sampling_rate,
            pii_scrubbing=self._current_profile.enable_pii_scrubbing,
        )

    @property
    def profile(self) -> ProfileConfig:
        """Get current profile configuration."""
        return cast(ProfileConfig, self._current_profile)

    def should_sample_span(self, span_name: str) -> bool:
        """
        Determine if a span should be sampled based on profile.

        Args:
            span_name: Name of the span

        Returns:
            True if span should be sampled
        """
        import random

        # Always sample critical operations
        critical_operations = ["safety", "compliance", "human.approval"]
        if any(op in span_name for op in critical_operations):
            return True

        # Sample based on profile rate
        return random.random() < self.profile.sampling_rate

    def should_include_attribute(self, attribute_name: str) -> bool:
        """
        Check if attribute should be included based on profile.

        Args:
            attribute_name: Name of the attribute

        Returns:
            True if attribute should be included
        """
        return attribute_name not in self.profile.excluded_attributes

    def filter_attribute_value(self, value: str) -> str:
        """
        Filter attribute value based on profile (truncate, scrub).

        Args:
            value: Attribute value

        Returns:
            Filtered value
        """
        if not isinstance(value, str):
            return value

        # Truncate to max length
        max_len = self.profile.max_attribute_length
        if len(value) > max_len:
            return value[:max_len] + "... [truncated]"

        # Apply PII scrubbing if enabled
        if self.profile.enable_pii_scrubbing:
            # Import here to avoid circular dependency
            from .pii_scrubber import scrub_pii

            return scrub_pii(value)

        return value

    def get_exporter_config(self) -> dict:
        """
        Get exporter configuration based on profile.

        Returns:
            Dictionary with exporter configuration
        """
        return {
            "format": self.profile.export_format,
            "sampling_rate": self.profile.sampling_rate,
            "retention_days": self.profile.retention_days,
            "enable_metrics": self.profile.enable_metrics,
            "enable_logging": self.profile.enable_logging,
        }


# Global profile manager instance
_profile_manager = None


def get_profile_manager() -> TelemetryProfileManager:
    """
    Get global profile manager instance.

    Returns:
        TelemetryProfileManager instance
    """
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = TelemetryProfileManager()
    return _profile_manager


def get_current_profile() -> ProfileConfig:
    """
    Get current active profile configuration.

    Returns:
        ProfileConfig instance
    """
    return get_profile_manager().profile


# ============================================================================
# Profile-Aware Span Processor
# ============================================================================


class ProfileAwareSpanProcessor:
    """
    Span processor that applies profile-specific filtering.

    This processor should be added to the TracerProvider to automatically
    apply profile rules to all spans.
    """

    def __init__(self):
        """Initialize processor with current profile."""
        self.profile_manager = get_profile_manager()

    def on_start(self, span, parent_context=None):
        """
        Called when span starts.

        Args:
            span: The span being started
            parent_context: Parent context if any
        """
        # Check if span should be sampled
        if not self.profile_manager.should_sample_span(span.name):
            # Mark span as not sampled
            span._sampled = False

    def on_end(self, span):
        """
        Called when span ends. Filter attributes based on profile.

        Args:
            span: The span being ended
        """
        if not hasattr(span, "attributes") or span.attributes is None:
            return

        # Filter attributes
        filtered_attrs = {}
        for key, value in span.attributes.items():
            # Check if attribute should be included
            if not self.profile_manager.should_include_attribute(key):
                continue

            # Filter value if string
            if isinstance(value, str):
                filtered_attrs[key] = self.profile_manager.filter_attribute_value(value)
            else:
                filtered_attrs[key] = value

        # Update span attributes
        span._attributes = filtered_attrs

    def shutdown(self):
        """Shutdown processor."""
        pass

    def force_flush(self, timeout_millis=None):
        """Force flush processor."""
        pass


# ============================================================================
# Usage Example
# ============================================================================

"""
# Set profile via environment variable
export RAE_TELEMETRY_PROFILE=research

# In application code
from apps.memory_api.observability.telemetry_profiles import (
    get_current_profile,
    get_profile_manager,
)

# Get current profile
profile = get_current_profile()
print(f"Sampling rate: {profile.sampling_rate}")
print(f"PII scrubbing: {profile.enable_pii_scrubbing}")

# Check if should sample
manager = get_profile_manager()
if manager.should_sample_span("memory.search"):
    # Create span
    pass

# Filter attribute
filtered_value = manager.filter_attribute_value(sensitive_data)
"""
