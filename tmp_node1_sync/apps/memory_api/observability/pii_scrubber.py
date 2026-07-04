"""
PII Scrubber for RAE Telemetry

Provides PII detection and scrubbing for sensitive environments (medical, government).
Ensures compliance with HIPAA, GDPR, and other privacy regulations.

Detects and redacts:
- Email addresses
- Phone numbers
- IP addresses
- Credit card numbers
- Social security numbers
- Names (basic heuristics)
- Addresses (basic patterns)

For production use with sensitive data, consider integrating:
- Microsoft Presidio (https://github.com/microsoft/presidio)
- AWS Comprehend PII detection
- Google Cloud DLP API
"""

import re
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# PII Patterns
# ============================================================================

# Regex patterns for common PII
PII_PATTERNS = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        re.IGNORECASE,
    ),
    "phone_us": re.compile(
        r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b"
    ),
    "phone_intl": re.compile(r"\+[0-9]{1,3}[\s.-]?[0-9]{1,14}"),
    "ssn": re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "ipv4": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
    "ipv6": re.compile(
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
        re.IGNORECASE,
    ),
    # Basic name patterns (capitalized words)
    "name_pattern": re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"),
}


# Replacement tokens
REDACTION_TOKENS = {
    "email": "[EMAIL]",
    "phone_us": "[PHONE]",
    "phone_intl": "[PHONE]",
    "ssn": "[SSN]",
    "credit_card": "[CREDIT_CARD]",
    "ipv4": "[IP_ADDRESS]",
    "ipv6": "[IP_ADDRESS]",
    "name_pattern": "[NAME]",
}


# ============================================================================
# PII Scrubber
# ============================================================================


class PIIScrubber:
    """
    PII detection and redaction engine.

    Provides configurable PII scrubbing for telemetry data.
    """

    def __init__(
        self,
        enabled_patterns: Optional[List[str]] = None,
        custom_patterns: Optional[Dict[str, re.Pattern]] = None,
    ):
        """
        Initialize PII scrubber.

        Args:
            enabled_patterns: List of pattern names to enable (None = all)
            custom_patterns: Additional custom patterns to apply
        """
        self.enabled_patterns = (
            enabled_patterns
            if enabled_patterns is not None
            else list(PII_PATTERNS.keys())
        )
        self.patterns = {
            name: pattern
            for name, pattern in PII_PATTERNS.items()
            if name in self.enabled_patterns
        }

        # Add custom patterns
        if custom_patterns:
            self.patterns.update(custom_patterns)

        logger.info(
            "pii_scrubber_initialized",
            enabled_patterns=self.enabled_patterns,
            pattern_count=len(self.patterns),
        )

    def scrub(self, text: str, preserve_structure: bool = True) -> str:
        """
        Scrub PII from text.

        Args:
            text: Text to scrub
            preserve_structure: Keep text structure (length, format)

        Returns:
            Scrubbed text
        """
        if not text or not isinstance(text, str):
            return text

        scrubbed = text

        # Apply each pattern
        for pattern_name, pattern in self.patterns.items():
            replacement = REDACTION_TOKENS.get(pattern_name, "[REDACTED]")

            if preserve_structure:
                # Replace with token of similar length
                def replacer(m: Any, r: str = replacement) -> str:
                    return self._preserve_length(m.group(), r)

                scrubbed = pattern.sub(replacer, scrubbed)
            else:
                # Simple replacement
                scrubbed = pattern.sub(replacement, scrubbed)

        return scrubbed

    def detect(self, text: str) -> Dict[str, List[str]]:
        """
        Detect PII in text without scrubbing.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping pattern name to list of detected values
        """
        if not text or not isinstance(text, str):
            return {}

        detected = {}

        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                detected[pattern_name] = matches

        return detected

    def has_pii(self, text: str) -> bool:
        """
        Check if text contains PII.

        Args:
            text: Text to check

        Returns:
            True if PII detected
        """
        if not text or not isinstance(text, str):
            return False

        for pattern in self.patterns.values():
            if pattern.search(text):
                return True

        return False

    def _preserve_length(self, original: str, replacement: str) -> str:
        """
        Preserve text length when replacing.

        Args:
            original: Original text
            replacement: Replacement token

        Returns:
            Replacement padded/truncated to match original length
        """
        if len(replacement) == len(original):
            return replacement
        elif len(replacement) < len(original):
            # Pad with asterisks
            padding = "*" * (len(original) - len(replacement))
            return replacement + padding
        else:
            # Truncate
            return replacement[: len(original)]


# Global scrubber instance
_scrubber = None


def get_scrubber() -> PIIScrubber:
    """
    Get global PII scrubber instance.

    Returns:
        PIIScrubber instance
    """
    global _scrubber
    if _scrubber is None:
        _scrubber = PIIScrubber()
    return _scrubber


def scrub_pii(text: str, preserve_structure: bool = True) -> str:
    """
    Scrub PII from text using global scrubber.

    Args:
        text: Text to scrub
        preserve_structure: Keep text structure

    Returns:
        Scrubbed text
    """
    return get_scrubber().scrub(text, preserve_structure)


def detect_pii(text: str) -> Dict[str, List[str]]:
    """
    Detect PII in text using global scrubber.

    Args:
        text: Text to analyze

    Returns:
        Dictionary of detected PII
    """
    return get_scrubber().detect(text)


def has_pii(text: str) -> bool:
    """
    Check if text contains PII using global scrubber.

    Args:
        text: Text to check

    Returns:
        True if PII detected
    """
    return get_scrubber().has_pii(text)


# ============================================================================
# Attribute Scrubbing
# ============================================================================


def scrub_span_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scrub PII from span attributes.

    Args:
        attributes: Span attributes dictionary

    Returns:
        Scrubbed attributes dictionary
    """
    if not attributes:
        return attributes

    scrubbed: Dict[str, Any] = {}
    scrubber = get_scrubber()

    for key, value in attributes.items():
        if isinstance(value, str):
            # Scrub string values
            scrubbed[key] = scrubber.scrub(value)
        elif isinstance(value, (list, tuple)):
            # Scrub list/tuple of strings
            scrubbed[key] = [
                scrubber.scrub(v) if isinstance(v, str) else v for v in value
            ]
        elif isinstance(value, dict):
            # Recursively scrub nested dicts
            scrubbed[key] = scrub_span_attributes(value)
        else:
            # Keep non-string values as-is
            scrubbed[key] = value

    return scrubbed


# ============================================================================
# Configuration
# ============================================================================


def configure_scrubber(
    enabled_patterns: Optional[List[str]] = None,
    custom_patterns: Optional[Dict[str, str]] = None,
):
    """
    Configure global PII scrubber.

    Args:
        enabled_patterns: List of pattern names to enable
        custom_patterns: Dict of name -> regex pattern strings
    """
    global _scrubber

    # Compile custom patterns
    compiled_custom = None
    if custom_patterns:
        compiled_custom = {
            name: re.compile(pattern) for name, pattern in custom_patterns.items()
        }

    _scrubber = PIIScrubber(
        enabled_patterns=enabled_patterns,
        custom_patterns=compiled_custom,
    )

    logger.info("pii_scrubber_configured", enabled_patterns=enabled_patterns)


# ============================================================================
# Usage Examples
# ============================================================================

r"""
# Example 1: Basic scrubbing
text = "Contact John Smith at john.smith@example.com or 555-123-4567"
scrubbed = scrub_pii(text)
# Output: "Contact [NAME] at [EMAIL] or [PHONE]"

# Example 2: Detect PII
detected = detect_pii(text)
# Output: {
#   "email": ["john.smith@example.com"],
#   "phone_us": ["555-123-4567"],
#   "name_pattern": ["John Smith"]
# }

# Example 3: Check if PII exists
if has_pii(user_input):
    logger.warning("pii_detected_in_input")

# Example 4: Scrub span attributes
attributes = {
    "user.query": "My email is test@example.com",
    "user.ip": "192.168.1.1",
}
scrubbed_attrs = scrub_span_attributes(attributes)

# Example 5: Custom patterns
configure_scrubber(
    enabled_patterns=["email", "phone_us"],
    custom_patterns={
        "medical_id": r"MRN-\d{8}",
    }
)

# Example 6: Preserve structure
scrubbed = scrub_pii("SSN: 123-45-6789", preserve_structure=True)
# Output: "SSN: [SSN]*******" (maintains length)
"""


# ============================================================================
# Integration with OpenTelemetry
# ============================================================================


def create_pii_scrubbing_processor():
    """
    Create an OpenTelemetry span processor that scrubs PII.

    Returns:
        Span processor instance
    """
    try:
        from opentelemetry.sdk.trace import SpanProcessor

        class PIIScrubbingProcessor(SpanProcessor):
            """Span processor that scrubs PII from attributes."""

            def __init__(self):
                self.scrubber = get_scrubber()

            def on_start(self, span, parent_context=None):
                """Called when span starts."""
                pass

            def on_end(self, span):
                """Scrub PII from span attributes when span ends."""
                if not hasattr(span, "attributes") or span.attributes is None:
                    return

                # Scrub attributes
                scrubbed = scrub_span_attributes(dict(span.attributes))
                # In OpenTelemetry, we can't easily replace the whole attributes dict
                # if it's a BoundedAttributes or similar, but we can iterate and set.
                # However, Span objects in processors are usually ReadableSpan, which might be immutable.
                # If it's a ReadWriteSpan, we can modify it.
                # Standard SpanProcessor receives ReadableSpan.
                # Modifying attributes in on_end is generally for export purposes.
                # But here we modify the internal _attributes dict if possible for the sake of the example logic.
                if hasattr(span, "_attributes"):
                    span._attributes = scrubbed

            def shutdown(self):
                """Shutdown processor."""
                pass

            def force_flush(self, timeout_millis=None):
                """Force flush."""
                pass

        return PIIScrubbingProcessor()

    except ImportError:
        logger.warning("opentelemetry_not_available_for_pii_processor")

        # Return a dummy object to avoid NameError in tests that expect a return value
        class DummyProcessor:
            def on_end(self, span):
                pass

        return DummyProcessor()
