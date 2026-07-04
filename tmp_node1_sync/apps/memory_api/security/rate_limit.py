"""
Rate Limiting Module

Provides rate limiting functionality using Redis.
"""

import time
from typing import Optional

import structlog
from fastapi import HTTPException, Request, status
from redis import Redis

from apps.memory_api.config import settings

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Rate limiter using Redis sliding window algorithm.
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance (optional, will create if not provided)
        """
        self.redis_client = redis_client
        self.enabled = settings.ENABLE_RATE_LIMITING

    def get_redis_client(self) -> Optional[Redis]:
        """Get or create Redis client."""
        if not self.enabled:
            return None

        if self.redis_client is None:
            try:
                self.redis_client = Redis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
            except Exception as e:
                logger.error("redis_connection_failed", error=str(e))
                return None

        return self.redis_client

    def get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Uses API key if available, otherwise uses IP address.

        Args:
            request: FastAPI request object

        Returns:
            Unique identifier string
        """
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return (
                f"api_key:{api_key[:20]}"  # Use first 20 chars to avoid very long keys
            )

        # Try to get user ID from auth
        if hasattr(request.state, "user"):
            user = request.state.user
            if user_id := user.get("user_id"):
                return f"user:{user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def check_rate_limit(
        self,
        request: Request,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> dict:
        """
        Check if request is within rate limit.

        Args:
            request: FastAPI request object
            max_requests: Maximum requests allowed (defaults to config)
            window_seconds: Time window in seconds (defaults to config)

        Returns:
            Dictionary with rate limit info

        Raises:
            HTTPException: If rate limit exceeded
        """
        if not self.enabled:
            return {"allowed": True, "remaining": -1, "reset_at": -1}

        redis_client = self.get_redis_client()
        if not redis_client:
            # If Redis is unavailable, allow request but log warning
            logger.warning("rate_limit_check_skipped_redis_unavailable")
            return {"allowed": True, "remaining": -1, "reset_at": -1}

        # Use provided limits or defaults from settings
        max_requests = max_requests or settings.RATE_LIMIT_REQUESTS
        window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW

        identifier = self.get_identifier(request)
        key = f"rate_limit:{identifier}"

        current_time = int(time.time())
        window_start = current_time - window_seconds

        try:
            # Remove old entries outside the window
            redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = redis_client.zcard(key)

            # Check if limit exceeded
            if request_count >= max_requests:
                # Get oldest request time to calculate reset time
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                reset_at = (
                    int(oldest[0][1]) + window_seconds
                    if oldest
                    else current_time + window_seconds
                )

                logger.warning(
                    "rate_limit_exceeded",
                    identifier=identifier,
                    count=request_count,
                    limit=max_requests,
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": max_requests,
                        "window": window_seconds,
                        "reset_at": reset_at,
                    },
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                        "Retry-After": str(reset_at - current_time),
                    },
                )

            # Add current request
            redis_client.zadd(key, {str(current_time): current_time})

            # Set expiry on key (cleanup)
            redis_client.expire(key, window_seconds + 60)

            remaining = max_requests - request_count - 1
            reset_at = current_time + window_seconds

            return {
                "allowed": True,
                "remaining": remaining,
                "limit": max_requests,
                "reset_at": reset_at,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("rate_limit_check_failed", error=str(e))
            # On error, allow request but log
            return {"allowed": True, "remaining": -1, "reset_at": -1}


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.

    Checks rate limits before processing request.

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in chain

    Returns:
        Response object
    """
    # Skip rate limiting for health check and metrics
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)

    limiter = get_rate_limiter()

    # Check rate limit
    rate_info = await limiter.check_rate_limit(request)

    # Process request
    response = await call_next(request)

    # Add rate limit headers to response
    if rate_info.get("allowed"):
        response.headers["X-RateLimit-Limit"] = str(rate_info.get("limit", -1))
        response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", -1))
        response.headers["X-RateLimit-Reset"] = str(rate_info.get("reset_at", -1))

    return response
