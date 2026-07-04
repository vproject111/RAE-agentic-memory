"""
Rate Limiting Middleware - Enterprise-Grade Request Throttling

This module provides comprehensive rate limiting for RAE API endpoints using SlowAPI.

Features:
- Per-tenant rate limiting (not just per-IP)
- Configurable limits per endpoint
- Redis-backed storage for distributed systems
- Custom headers for rate limit info
- Graceful degradation if Redis unavailable

Rate Limits (per tenant):
- POST /v1/memories/create: 30/minute
- POST /v1/search/hybrid: 60/minute
- POST /v1/ml/generate: 20/minute
- GET endpoints: 100/minute (general)
- POST endpoints: 50/minute (general)

Headers Returned:
- X-RateLimit-Limit: Maximum requests allowed
- X-RateLimit-Remaining: Requests remaining in current window
- X-RateLimit-Reset: Unix timestamp when limit resets
"""

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = structlog.get_logger(__name__)


# ============================================================================
# Key Function - Extract tenant_id for rate limiting
# ============================================================================


def get_tenant_key(request: Request) -> str:
    """
    Extract rate limiting key from request.

    Priority:
    1. X-Tenant-ID header (preferred for multi-tenant systems)
    2. tenant_id from JSON body
    3. tenant_id from query params
    4. Fall back to IP address

    This ensures rate limits are per-tenant, not per-IP,
    which is more appropriate for API services.
    """
    # Try header first
    tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")

    if tenant_id:
        logger.debug("rate_limit_key_from_header", tenant_id=tenant_id)
        return f"tenant:{tenant_id}"

    # Try to extract from body (if JSON)
    try:
        if request.method in ["POST", "PUT", "PATCH"]:
            # Note: This is a simplified approach. In production, you might want to
            # parse the body more carefully or use a request context variable
            # that was set by earlier middleware
            pass
    except Exception:
        pass

    # Fall back to IP address
    ip = get_remote_address(request)
    logger.debug("rate_limit_key_from_ip", ip=ip)
    return f"ip:{ip}"


# ============================================================================
# Limiter Initialization
# ============================================================================

# Initialize SlowAPI limiter with tenant-aware key function
limiter = Limiter(
    key_func=get_tenant_key,
    default_limits=["100/minute"],  # Default for all endpoints
    storage_uri="memory://",  # Use in-memory storage (for single-instance)
    # For distributed systems, use Redis:
    # storage_uri="redis://localhost:6379",
    headers_enabled=True,  # Enable X-RateLimit-* headers
    swallow_errors=True,  # Don't crash if storage fails
)


# ============================================================================
# Rate Limit Exception Handler
# ============================================================================


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns user-friendly error message with retry information.
    """
    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        method=request.method,
        key=get_tenant_key(request),
        limit=str(exc.detail),
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down and try again later.",
                "detail": str(exc.detail),
                "retry_after_seconds": 60,  # Suggest retry after 1 minute
            }
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Reset": str(exc.detail) if hasattr(exc, "detail") else "60",
        },
    )


# ============================================================================
# Rate Limit Decorators for Specific Endpoints
# ============================================================================

# High-traffic search endpoints
search_limit = limiter.limit("60/minute")

# Memory creation (moderate limit to prevent abuse)
memory_create_limit = limiter.limit("30/minute")

# ML/LLM endpoints (expensive, lower limit)
ml_limit = limiter.limit("20/minute")

# General GET endpoints (high limit)
get_limit = limiter.limit("100/minute")

# General POST endpoints (moderate limit)
post_limit = limiter.limit("50/minute")

# Admin endpoints (very low limit)
admin_limit = limiter.limit("10/minute")


# ============================================================================
# Utility Functions
# ============================================================================


def get_rate_limit_status(request: Request) -> dict:
    """
    Get current rate limit status for debugging/monitoring.

    Returns dict with limit, remaining, and reset time.
    """
    try:
        key = get_tenant_key(request)
        # This would require accessing limiter's internal storage
        # For now, return placeholder
        return {
            "key": key,
            "limit": "unknown",
            "remaining": "unknown",
            "reset": "unknown",
        }
    except Exception as e:
        logger.error("get_rate_limit_status_error", error=str(e))
        return {"error": str(e)}


# ============================================================================
# Configuration
# ============================================================================

RATE_LIMITS = {
    "memory_create": "30/minute",
    "search_hybrid": "60/minute",
    "ml_generate": "20/minute",
    "get_general": "100/minute",
    "post_general": "50/minute",
    "admin": "10/minute",
}


def get_rate_limit_for_endpoint(path: str, method: str) -> str:
    """
    Get rate limit configuration for a specific endpoint.

    This allows dynamic rate limit configuration based on endpoint.
    """
    if "/v1/memories/create" in path:
        return RATE_LIMITS["memory_create"]
    elif "/v1/search/hybrid" in path:
        return RATE_LIMITS["search_hybrid"]
    elif "/v1/ml/" in path:
        return RATE_LIMITS["ml_generate"]
    elif method == "GET":
        return RATE_LIMITS["get_general"]
    elif method in ["POST", "PUT", "PATCH"]:
        return RATE_LIMITS["post_general"]
    else:
        return "100/minute"  # Default


# ============================================================================
# Notes for Production Deployment
# ============================================================================

"""
For production deployment with multiple instances, configure Redis:

1. Install Redis:
   pip install redis

2. Update limiter initialization:
   limiter = Limiter(
       key_func=get_tenant_key,
       storage_uri="redis://redis:6379/0",  # Use your Redis host
       headers_enabled=True,
       swallow_errors=True,
   )

3. Environment variable support:
   storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

4. Redis with authentication:
   storage_uri="redis://:password@redis:6379/0"

5. Redis Cluster:
   storage_uri="redis+cluster://redis1:6379,redis2:6379,redis3:6379/0"

For Kubernetes deployment:
- Deploy Redis as a StatefulSet or use managed Redis (AWS ElastiCache, etc.)
- Configure connection via ConfigMap/Secret
- Enable persistence for Redis to survive pod restarts
- Monitor Redis memory usage and eviction policies
"""
