"""Retry logic and error handling for orchestrator."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""

    IMMEDIATE = "immediate"  # Retry immediately
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Wait 2^attempt seconds
    FIXED_DELAY = "fixed_delay"  # Fixed delay between retries


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    timeout: Optional[float] = None  # per-attempt timeout


class RetryableError(Exception):
    """Error that can be retried."""

    pass


class NonRetryableError(Exception):
    """Error that should not be retried."""

    pass


class RetryHandler:
    """Handles retry logic with configurable strategies."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()

    async def execute_with_retry(
        self, func: Callable, *args, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            context: Context for logging (task_id, step_id, etc.)
            **kwargs: Keyword arguments

        Returns:
            Result from function

        Raises:
            Exception: If all retries exhausted
        """
        context = context or {}
        attempt = 1

        while attempt <= self.config.max_attempts:
            try:
                logger.info(
                    f"Executing {func.__name__} (attempt {attempt}/{self.config.max_attempts}) "
                    f"- {context}"
                )

                # Execute with timeout if configured
                if self.config.timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), timeout=self.config.timeout
                    )
                else:
                    result = await func(*args, **kwargs)

                logger.info(f"Success on attempt {attempt} - {context}")
                return result

            except NonRetryableError as e:
                logger.error(f"Non-retryable error: {e} - {context}")
                raise

            except asyncio.TimeoutError as e:
                logger.warning(
                    f"Timeout on attempt {attempt}/{self.config.max_attempts} - {context}"
                )
                if attempt >= self.config.max_attempts:
                    raise RetryableError(
                        f"Timeout after {self.config.max_attempts} attempts"
                    ) from e

            except Exception as e:
                logger.warning(
                    f"Error on attempt {attempt}/{self.config.max_attempts}: {e} - {context}"
                )

                if attempt >= self.config.max_attempts:
                    logger.error(f"All retries exhausted - {context}")
                    raise

                # Calculate delay based on strategy
                delay = self._calculate_delay(attempt)
                logger.info(f"Waiting {delay:.1f}s before retry - {context}")
                await asyncio.sleep(delay)

            attempt += 1

        # Should not reach here, but just in case
        raise RetryableError(f"Failed after {self.config.max_attempts} attempts")

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry.

        Args:
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0

        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # 2^attempt * base_delay, capped at max_delay
            delay = (2**attempt) * self.config.base_delay
            return min(delay, self.config.max_delay)

        elif self.config.strategy == RetryStrategy.FIXED_DELAY:
            return self.config.base_delay

        else:
            return 0.0


class ErrorClassifier:
    """Classifies errors as retryable or non-retryable."""

    # Error patterns that should not be retried
    NON_RETRYABLE_PATTERNS = [
        "authentication failed",
        "invalid api key",
        "permission denied",
        "not found",
        "bad request",
        "invalid input",
        "validation error",
    ]

    # Error patterns that can be retried
    RETRYABLE_PATTERNS = [
        "timeout",
        "connection error",
        "rate limit",
        "service unavailable",
        "internal server error",
        "temporary failure",
    ]

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """Check if error is retryable.

        Args:
            error: Exception to classify

        Returns:
            True if retryable
        """
        error_str = str(error).lower()

        # Check for non-retryable patterns
        for pattern in cls.NON_RETRYABLE_PATTERNS:
            if pattern in error_str:
                return False

        # Check for retryable patterns
        for pattern in cls.RETRYABLE_PATTERNS:
            if pattern in error_str:
                return True

        # Default: retryable (conservative approach)
        return True

    @classmethod
    def wrap_error(cls, error: Exception) -> Exception:
        """Wrap error as retryable or non-retryable.

        Args:
            error: Original exception

        Returns:
            Wrapped exception
        """
        if isinstance(error, (RetryableError, NonRetryableError)):
            return error

        if cls.is_retryable(error):
            raise RetryableError(str(error)) from error
        else:
            raise NonRetryableError(str(error)) from error


# Convenience decorators


def retry_on_failure(
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay: float = 1.0,
):
    """Decorator to add retry logic to async functions.

    Args:
        max_attempts: Maximum retry attempts
        strategy: Retry strategy
        base_delay: Base delay for backoff

    Returns:
        Decorated function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            handler = RetryHandler(
                RetryConfig(
                    max_attempts=max_attempts, strategy=strategy, base_delay=base_delay
                )
            )
            return await handler.execute_with_retry(func, *args, **kwargs)

        return wrapper

    return decorator
