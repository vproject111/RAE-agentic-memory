"""
RAE API Client - Enhanced Client with Resilience Patterns

This module provides an enhanced API client for the RAE Memory API with:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Request/response caching
- Connection pooling
- Timeout handling
- Error classification
- Rate limiting
"""

import asyncio
import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, cast

import httpx
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Enums and Constants
# ============================================================================


class CircuitState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class ErrorCategory(str, Enum):
    """Error categories for classification"""

    NETWORK = "network"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"


# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF_MS = 100
DEFAULT_MAX_BACKOFF_MS = 10000
DEFAULT_BACKOFF_MULTIPLIER = 2.0

# Circuit breaker configuration
DEFAULT_FAILURE_THRESHOLD = 5
DEFAULT_SUCCESS_THRESHOLD = 2
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_HALF_OPEN_TIMEOUT_SECONDS = 60

# Cache configuration
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes


# ============================================================================
# Error Classification
# ============================================================================


class RAEClientError(Exception):
    """Base exception for RAE client errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        original_error: Optional[Exception] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.original_error = original_error
        self.status_code = status_code


def classify_error(
    error: Exception, status_code: Optional[int] = None
) -> ErrorCategory:
    """
    Classify error into category.

    Args:
        error: Exception to classify
        status_code: HTTP status code if available

    Returns:
        ErrorCategory
    """
    if isinstance(error, httpx.NetworkError):
        return ErrorCategory.NETWORK

    if isinstance(error, httpx.TimeoutException):
        return ErrorCategory.TIMEOUT

    if status_code:
        if status_code == 429:
            return ErrorCategory.RATE_LIMIT
        elif status_code == 401 or status_code == 403:
            return ErrorCategory.AUTHENTICATION
        elif 400 <= status_code < 500:
            return ErrorCategory.CLIENT_ERROR
        elif 500 <= status_code < 600:
            return ErrorCategory.SERVER_ERROR

    return ErrorCategory.UNKNOWN


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """
    Circuit breaker implementation.

    Prevents cascading failures by stopping requests when error rate is high.
    """

    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        success_threshold: int = DEFAULT_SUCCESS_THRESHOLD,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        half_open_timeout_seconds: int = DEFAULT_HALF_OPEN_TIMEOUT_SECONDS,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes before closing circuit (from half-open)
            timeout_seconds: Seconds to wait before trying again (open → half-open)
            half_open_timeout_seconds: Timeout for requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_timeout_seconds = half_open_timeout_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None

        logger.info(
            "circuit_breaker_initialized",
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
        )

    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RAEClientError: If circuit is open
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self.last_failure_time:
                time_since_failure = (
                    datetime.now(timezone.utc) - self.last_failure_time
                ).total_seconds()
                if time_since_failure >= self.timeout_seconds:
                    logger.info("circuit_breaker_half_open")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise RAEClientError(
                        f"Circuit breaker is OPEN (failing fast). Retry in {self.timeout_seconds - time_since_failure:.1f}s",
                        category=ErrorCategory.SERVER_ERROR,
                    )

        try:
            # Execute function
            if self.state == CircuitState.HALF_OPEN:
                # Apply stricter timeout in half-open state
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=self.half_open_timeout_seconds
                )
            else:
                result = await func(*args, **kwargs)

            # Success
            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure(e)
            raise

    async def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                "circuit_breaker_success_in_half_open",
                success_count=self.success_count,
                threshold=self.success_threshold,
            )

            if self.success_count >= self.success_threshold:
                logger.info("circuit_breaker_closed")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    async def _on_failure(self, error: Exception):
        """Handle failed call."""
        self.last_failure_time = datetime.now(timezone.utc)

        if self.state == CircuitState.HALF_OPEN:
            # Immediately open on failure in half-open
            logger.warning("circuit_breaker_opened_from_half_open")
            self.state = CircuitState.OPEN
            self.failure_count = self.failure_threshold

        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            logger.warning(
                "circuit_breaker_failure",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )

            if self.failure_count >= self.failure_threshold:
                logger.error("circuit_breaker_opened")
                self.state = CircuitState.OPEN

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
        }


# ============================================================================
# Response Cache
# ============================================================================


class ResponseCache:
    """
    Simple in-memory response cache with TTL.
    """

    def __init__(self, default_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        """
        Initialize response cache.

        Args:
            default_ttl_seconds: Default TTL for cached entries
        """
        self.default_ttl_seconds = default_ttl_seconds
        self._cache: Dict[str, tuple[Any, datetime]] = {}

        logger.info("response_cache_initialized", ttl_seconds=default_ttl_seconds)

    def _generate_key(
        self, method: str, url: str, params: Optional[Dict] = None
    ) -> str:
        """Generate cache key from request details."""
        key_parts = [method.upper(), url]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))

        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(
        self, method: str, url: str, params: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        Get cached response.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters

        Returns:
            Cached response or None if not found/expired
        """
        key = self._generate_key(method, url, params)

        if key in self._cache:
            response, expires_at = self._cache[key]

            # Check if expired
            if datetime.now(timezone.utc) < expires_at:
                logger.debug("cache_hit", key=key)
                return response
            else:
                # Remove expired entry
                logger.debug("cache_expired", key=key)
                del self._cache[key]

        logger.debug("cache_miss", key=key)
        return None

    def set(
        self,
        method: str,
        url: str,
        response: Any,
        params: Optional[Dict] = None,
        ttl_seconds: Optional[int] = None,
    ):
        """
        Cache response.

        Args:
            method: HTTP method
            url: Request URL
            response: Response to cache
            params: Query parameters
            ttl_seconds: TTL override
        """
        key = self._generate_key(method, url, params)
        ttl = ttl_seconds or self.default_ttl_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        self._cache[key] = (response, expires_at)
        logger.debug("cache_set", key=key, ttl_seconds=ttl)

    def invalidate(self, method: str, url: str, params: Optional[Dict] = None):
        """Invalidate cached response."""
        key = self._generate_key(method, url, params)
        if key in self._cache:
            del self._cache[key]
            logger.debug("cache_invalidated", key=key)

    def clear(self):
        """Clear all cached responses."""
        count = len(self._cache)
        self._cache.clear()
        logger.info("cache_cleared", entries_removed=count)

    def cleanup_expired(self):
        """Remove expired entries."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items() if now >= expires_at
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info("cache_cleanup", entries_removed=len(expired_keys))


# ============================================================================
# RAE API Client
# ============================================================================


class RAEClient:
    """
    Enhanced RAE API Client with resilience patterns.

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker for fault tolerance
    - Response caching
    - Connection pooling
    - Comprehensive error handling
    """

    circuit_breaker: Optional[CircuitBreaker]
    cache: Optional[ResponseCache]

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        # Retry configuration
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_backoff_ms: int = DEFAULT_INITIAL_BACKOFF_MS,
        max_backoff_ms: int = DEFAULT_MAX_BACKOFF_MS,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        # Circuit breaker configuration
        enable_circuit_breaker: bool = True,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        success_threshold: int = DEFAULT_SUCCESS_THRESHOLD,
        # Cache configuration
        enable_cache: bool = True,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        # Connection configuration
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ):
        """
        Initialize RAE client.

        Args:
            base_url: Base URL for RAE API
            api_key: API key for authentication
            tenant_id: Default tenant ID
            project_id: Default project ID
            max_retries: Maximum number of retries
            initial_backoff_ms: Initial backoff in milliseconds
            max_backoff_ms: Maximum backoff in milliseconds
            backoff_multiplier: Backoff multiplier
            enable_circuit_breaker: Enable circuit breaker
            failure_threshold: Circuit breaker failure threshold
            success_threshold: Circuit breaker success threshold
            enable_cache: Enable response caching
            cache_ttl_seconds: Default cache TTL
            timeout: Request timeout in seconds
            max_connections: Maximum number of connections
            max_keepalive_connections: Maximum keepalive connections
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.project_id = project_id

        # Retry configuration
        self.max_retries = max_retries
        self.initial_backoff_ms = initial_backoff_ms
        self.max_backoff_ms = max_backoff_ms
        self.backoff_multiplier = backoff_multiplier

        # Initialize circuit breaker
        self.enable_circuit_breaker = enable_circuit_breaker
        if enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=failure_threshold, success_threshold=success_threshold
            )
        else:
            self.circuit_breaker = None

        # Initialize cache
        self.enable_cache = enable_cache
        if enable_cache:
            self.cache = ResponseCache(default_ttl_seconds=cache_ttl_seconds)
        else:
            self.cache = None

        # Initialize HTTP client with connection pooling
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
        )

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retried_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        logger.info(
            "rae_client_initialized",
            base_url=base_url,
            max_retries=max_retries,
            circuit_breaker_enabled=enable_circuit_breaker,
            cache_enabled=enable_cache,
        )

    async def close(self):
        """Close client and cleanup resources."""
        await self.client.aclose()
        logger.info("rae_client_closed")

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    # ========================================================================
    # Core Request Methods
    # ========================================================================

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        retry_on_errors: Optional[List[ErrorCategory]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry and circuit breaker.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            params: Query parameters
            json_data: JSON request body
            headers: Additional headers
            use_cache: Use cache for GET requests
            cache_ttl: Cache TTL override
            retry_on_errors: Error categories to retry on

        Returns:
            Response JSON

        Raises:
            RAEClientError: On request failure
        """
        self.stats["total_requests"] += 1

        # Build full URL
        url = path if path.startswith("http") else f"{self.base_url}{path}"

        # Check cache for GET requests
        if method.upper() == "GET" and use_cache and self.cache:
            cached_response = self.cache.get(method, url, params)
            if cached_response is not None:
                self.stats["cache_hits"] += 1
                return cast(Dict[str, Any], cached_response)
            self.stats["cache_misses"] += 1

        # Prepare headers
        request_headers = self._prepare_headers(headers)

        # Define retry-able error categories
        if retry_on_errors is None:
            retry_on_errors = [
                ErrorCategory.NETWORK,
                ErrorCategory.TIMEOUT,
                ErrorCategory.SERVER_ERROR,
            ]

        # Execute with retry and circuit breaker
        try:
            if self.circuit_breaker:
                response = await self.circuit_breaker.call(
                    self._request_with_retry,
                    method,
                    url,
                    params,
                    json_data,
                    request_headers,
                    retry_on_errors,
                )
            else:
                response = await self._request_with_retry(
                    method, url, params, json_data, request_headers, retry_on_errors
                )

            # Cache successful GET responses
            if method.upper() == "GET" and use_cache and self.cache:
                self.cache.set(method, url, response, params, cache_ttl)

            self.stats["successful_requests"] += 1
            return cast(Dict[str, Any], response)

        except Exception as e:
            self.stats["failed_requests"] += 1
            if isinstance(e, RAEClientError):
                raise
            raise RAEClientError(
                f"Request failed: {str(e)}",
                category=classify_error(e),
                original_error=e,
            ) from e

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        params: Optional[Dict],
        json_data: Optional[Dict],
        headers: Dict,
        retry_on_errors: List[ErrorCategory],
    ) -> Dict[str, Any]:
        """Execute request with exponential backoff retry."""
        last_error: Optional[Exception] = None
        backoff_ms = self.initial_backoff_ms

        for attempt in range(self.max_retries + 1):
            try:
                # Make request
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

                # Check for success
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_error = e

                # Get status code if available
                status_code = None
                if isinstance(e, httpx.HTTPStatusError):
                    status_code = e.response.status_code

                # Classify error
                error_category = classify_error(e, status_code)

                # Log error
                logger.warning(
                    "request_failed",
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                    error=str(e),
                    category=error_category.value,
                    status_code=status_code,
                )

                # Check if should retry
                if attempt < self.max_retries and error_category in retry_on_errors:
                    # Calculate backoff
                    await asyncio.sleep(backoff_ms / 1000.0)

                    # Increase backoff
                    backoff_ms = min(
                        int(backoff_ms * self.backoff_multiplier), self.max_backoff_ms
                    )

                    self.stats["retried_requests"] += 1

                    logger.info(
                        "retrying_request", attempt=attempt + 1, backoff_ms=backoff_ms
                    )
                else:
                    # Don't retry
                    break

        # All retries exhausted
        if isinstance(last_error, httpx.HTTPStatusError):
            status_code = last_error.response.status_code
            error_category = classify_error(last_error, status_code)

            raise RAEClientError(
                f"Request failed with status {status_code}: {last_error.response.text}",
                category=error_category,
                original_error=last_error,
                status_code=status_code,
            )
        else:
            raise RAEClientError(
                f"Request failed after {self.max_retries + 1} attempts: {str(last_error)}",
                category=classify_error(cast(Exception, last_error)),
                original_error=cast(Exception, last_error),
            )

    def _prepare_headers(self, additional_headers: Optional[Dict] = None) -> Dict:
        """Prepare request headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "RAE-Python-Client/1.0",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id

        if self.project_id:
            headers["X-Project-ID"] = self.project_id

        if additional_headers:
            headers.update(additional_headers)

        return headers

    # ========================================================================
    # Convenience Methods
    # ========================================================================

    async def get(
        self, path: str, params: Optional[Dict] = None, **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", path, params=params, **kwargs)

    async def post(
        self, path: str, json_data: Optional[Dict] = None, **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self.request(
            "POST", path, json_data=json_data, use_cache=False, **kwargs
        )

    async def put(
        self, path: str, json_data: Optional[Dict] = None, **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.request(
            "PUT", path, json_data=json_data, use_cache=False, **kwargs
        )

    async def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", path, use_cache=False, **kwargs)

    # ========================================================================
    # Statistics and Monitoring
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = self.stats.copy()

        # Add circuit breaker stats
        if self.circuit_breaker:
            stats["circuit_breaker"] = self.circuit_breaker.get_state()

        # Calculate derived metrics
        if stats["total_requests"] > 0:
            stats["success_rate"] = (
                stats["successful_requests"] / stats["total_requests"]
            )
            stats["failure_rate"] = stats["failed_requests"] / stats["total_requests"]
            stats["retry_rate"] = stats["retried_requests"] / stats["total_requests"]

        if (stats["cache_hits"] + stats["cache_misses"]) > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / (
                stats["cache_hits"] + stats["cache_misses"]
            )

        return stats

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retried_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        logger.info("stats_reset")

    def invalidate_cache(
        self, method: Optional[str] = None, path: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            method: HTTP method to invalidate (None = all)
            path: Path to invalidate (None = all)
        """
        if not self.cache:
            return

        if method is None and path is None:
            self.cache.clear()
        elif method and path:
            self.cache.invalidate(method, path)
