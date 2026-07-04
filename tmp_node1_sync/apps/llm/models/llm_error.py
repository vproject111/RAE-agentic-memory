"""
LLM Error types.
Unified error handling for all LLM providers.
"""

from typing import Optional


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        raw_error: Optional[Exception] = None,
    ):
        self.message = message
        self.provider = provider
        self.raw_error = raw_error
        super().__init__(message)


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    pass


class LLMAuthError(LLMError):
    """Raised when authentication fails."""

    pass


class LLMTransientError(LLMError):
    """Raised for transient errors that can be retried (timeouts, network issues)."""

    pass


class LLMProviderError(LLMError):
    """Raised for provider-specific errors."""

    pass


class LLMValidationError(LLMError):
    """Raised when request validation fails."""

    pass


class LLMContextLengthError(LLMError):
    """Raised when context length exceeds model limits."""

    pass
