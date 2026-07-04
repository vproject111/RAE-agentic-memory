"""
Circuit Breaker Pattern - ISO/IEC 42001 Graceful Degradation

Implements circuit breaker pattern to handle RAE failures gracefully and
prevent cascading failures in AI agent systems.

ISO/IEC 42001 compliance:
- RISK-004 mitigation: RAE unavailability causing agent failures
- Ensures system resilience and availability
- Enables degraded operation mode

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failure threshold exceeded, requests fail fast
- HALF_OPEN: Testing if service recovered
"""

import time
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Type, Union

import structlog

from apps.memory_api.utils.datetime_utils import utc_now

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failure threshold exceeded
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for graceful degradation.

    Tracks failures and opens circuit when threshold is exceeded,
    preventing further requests until recovery period.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Union[
            Type[BaseException], Tuple[Type[BaseException], ...]
        ] = Exception,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
            success_threshold: Successful calls needed to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold

        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.opened_at: Optional[datetime] = None

        # Metrics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function raises exception
        """
        self.total_calls += 1

        # Check if we should attempt call
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(
                    "circuit_breaker_half_open",
                    name=self.name,
                    message="Attempting recovery",
                )
            else:
                logger.warning(
                    "circuit_breaker_open",
                    name=self.name,
                    failure_count=self.failure_count,
                    message="Circuit open, failing fast",
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                )

        try:
            # Execute function
            result = await func(*args, **kwargs)

            # Record success
            self._on_success()

            return result

        except self.expected_exception as e:
            # Record failure
            self._on_failure()

            logger.error(
                "circuit_breaker_failure",
                name=self.name,
                state=self.state,
                failure_count=self.failure_count,
                error=str(e),
            )

            raise

    def _on_success(self):
        """Handle successful call"""
        self.total_successes += 1
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1

            if self.success_count >= self.success_threshold:
                self._close()

    def _on_failure(self):
        """Handle failed call"""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Immediately reopen on failure during recovery
            self._open()

        elif self.failure_count >= self.failure_threshold:
            self._open()

    def _open(self):
        """Open the circuit"""
        self.state = CircuitState.OPEN
        self.opened_at = utc_now()

        logger.error(
            "circuit_breaker_opened",
            name=self.name,
            failure_count=self.failure_count,
            threshold=self.failure_threshold,
            message=f"Circuit opened due to {self.failure_count} failures",
        )

    def _close(self):
        """Close the circuit"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None

        logger.info(
            "circuit_breaker_closed",
            name=self.name,
            message="Circuit closed, service recovered",
        )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return False

        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            Dict with state information
        """
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "metrics": {
                "total_calls": self.total_calls,
                "total_successes": self.total_successes,
                "total_failures": self.total_failures,
                "success_rate": (
                    self.total_successes / self.total_calls
                    if self.total_calls > 0
                    else 0.0
                ),
            },
        }

    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

        logger.info("circuit_breaker_reset", name=self.name, message="Manually reset")


class DegradedModeService:
    """
    Service for managing degraded mode operations.

    Provides fallback capabilities when RAE is unavailable.
    """

    def __init__(self):
        self.degraded_mode = False
        self.entered_at: Optional[datetime] = None
        self.reason: Optional[str] = None

    def enter_degraded_mode(self, reason: str):
        """
        Enter degraded operation mode.

        Args:
            reason: Reason for entering degraded mode
        """
        self.degraded_mode = True
        self.entered_at = utc_now()
        self.reason = reason

        logger.warning(
            "entered_degraded_mode",
            reason=reason,
            entered_at=self.entered_at.isoformat(),
            message="System operating in degraded mode",
        )

    def exit_degraded_mode(self):
        """Exit degraded mode and return to normal operation"""
        if self.degraded_mode:
            duration = (
                (utc_now() - self.entered_at).total_seconds() if self.entered_at else 0
            )

            logger.info(
                "exited_degraded_mode",
                duration_seconds=duration,
                message="Returned to normal operation",
            )

        self.degraded_mode = False
        self.entered_at = None
        self.reason = None

    def is_degraded(self) -> bool:
        """Check if system is in degraded mode"""
        return self.degraded_mode

    def get_status(self) -> Dict[str, Any]:
        """Get degraded mode status"""
        return {
            "degraded": self.degraded_mode,
            "entered_at": self.entered_at.isoformat() if self.entered_at else None,
            "reason": self.reason,
            "duration_seconds": (
                (utc_now() - self.entered_at).total_seconds() if self.entered_at else 0
            ),
        }


# Global circuit breakers for RAE components
rae_circuit_breakers = {
    "database": CircuitBreaker(
        name="rae_database",
        failure_threshold=5,
        recovery_timeout=30,
    ),
    "vector_store": CircuitBreaker(
        name="rae_vector_store",
        failure_threshold=3,
        recovery_timeout=60,
    ),
    "llm_service": CircuitBreaker(
        name="rae_llm_service",
        failure_threshold=5,
        recovery_timeout=120,
    ),
}

# Global degraded mode service
degraded_mode_service = DegradedModeService()
