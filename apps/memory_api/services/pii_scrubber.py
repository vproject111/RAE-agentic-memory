"""
PII Scrubber Service

Provides a unified interface for PII scrubbing, delegating to the
observability module's regex-based implementation.
"""

from apps.memory_api.observability.pii_scrubber import scrub_pii


def scrub_text(text: str | None) -> str:
    """
    Scrub PII from text using the observability scrubber.

    If Presidio is not available, returns the original text.

    Args:
        text: Input text

    Returns:
        Scrubbed text
    """
    if text is None:
        return ""
    return scrub_pii(text)
