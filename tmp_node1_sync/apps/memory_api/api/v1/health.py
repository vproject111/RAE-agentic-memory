"""
Health Check and Monitoring Endpoints

Provides comprehensive health checks for all system components.
"""

from datetime import datetime, timezone
from typing import Any, Dict, cast

import asyncpg
import httpx
import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel
from redis import Redis

from apps.memory_api.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health"])


class ComponentHealth(BaseModel):
    """Health status of a single component."""

    status: str  # healthy, degraded, unhealthy
    response_time_ms: float | None = None
    message: str | None = None
    details: Dict[str, Any] | None = None


class HealthCheckResponse(BaseModel):
    """Overall health check response."""

    status: str  # healthy, degraded, unhealthy
    timestamp: str
    version: str
    components: Dict[str, ComponentHealth]


class MetricsResponse(BaseModel):
    """System metrics response."""

    timestamp: str
    uptime_seconds: float
    memory_usage_mb: float
    database: Dict[str, Any]
    redis: Dict[str, Any]
    vector_store: Dict[str, Any]


# Application start time for uptime calculation
_start_time = datetime.now(timezone.utc)


async def check_database() -> ComponentHealth:
    """Check PostgreSQL database health."""
    try:
        start_time = datetime.now(timezone.utc)

        # Create a temporary connection
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            timeout=3.0,
        )

        # Run a simple query
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        if result == 1:
            return ComponentHealth(
                status="healthy",
                response_time_ms=response_time,
                message="Database connection successful",
            )
        else:
            return ComponentHealth(
                status="unhealthy",
                response_time_ms=response_time,
                message="Unexpected query result",
            )

    except asyncpg.exceptions.PostgresError as e:
        logger.error("database_health_check_failed", error=str(e))
        return ComponentHealth(status="unhealthy", message=f"Database error: {str(e)}")
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return ComponentHealth(
            status="unhealthy", message=f"Connection failed: {str(e)}"
        )


async def check_redis() -> ComponentHealth:
    """Check Redis cache health."""
    try:
        start_time = datetime.now(timezone.utc)

        redis_client = Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=3, decode_responses=True
        )

        # Ping Redis
        redis_client.ping()

        # Get some stats
        info = redis_client.info()
        redis_client.close()

        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        return ComponentHealth(
            status="healthy",
            response_time_ms=response_time,
            message="Redis connection successful",
            details={
                "version": info.get("redis_version"),
                "used_memory_mb": (
                    float(info["used_memory"]) / 1024 / 1024
                    if info.get("used_memory") is not None
                    else None
                ),
                "connected_clients": info.get("connected_clients"),
            },
        )

    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return ComponentHealth(
            status="unhealthy", message=f"Redis connection failed: {str(e)}"
        )


async def check_vector_store() -> ComponentHealth:
    """Check vector store (Qdrant) health."""
    try:
        start_time = datetime.now(timezone.utc)

        # Check Qdrant health endpoint
        qdrant_url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/"

        async with httpx.AsyncClient() as client:
            response = await client.get(qdrant_url, timeout=3.0)

        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        if response.status_code == 200:
            data = response.json()
            return ComponentHealth(
                status="healthy",
                response_time_ms=response_time,
                message="Vector store connection successful",
                details={"version": data.get("version"), "title": data.get("title")},
            )
        else:
            return ComponentHealth(
                status="unhealthy",
                response_time_ms=response_time,
                message=f"Unexpected status code: {response.status_code}",
            )

    except httpx.TimeoutException:
        return ComponentHealth(
            status="unhealthy", message="Vector store connection timeout"
        )
    except Exception as e:
        logger.error("vector_store_health_check_failed", error=str(e))
        return ComponentHealth(
            status="unhealthy", message=f"Vector store connection failed: {str(e)}"
        )


def determine_overall_status(components: Dict[str, ComponentHealth]) -> str:
    """
    Determine overall system status based on component health.

    Args:
        components: Dictionary of component health statuses

    Returns:
        Overall status: healthy, degraded, or unhealthy
    """
    statuses = [comp.status for comp in components.values()]

    if all(s == "healthy" for s in statuses):
        return "healthy"
    elif any(s == "unhealthy" for s in statuses):
        # If critical components are unhealthy, system is unhealthy
        critical_components = ["database", "redis"]
        if any(
            components[comp].status == "unhealthy"
            for comp in critical_components
            if comp in components
        ):
            return "unhealthy"
        return "degraded"
    else:
        return "degraded"


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health of all system components including database, cache, and vector store.",
)
async def health_check() -> HealthCheckResponse:
    """
    Comprehensive health check endpoint.

    Returns health status of all system components:
    - PostgreSQL database
    - Redis cache
    - Qdrant vector store

    Status can be:
    - healthy: All components working normally
    - degraded: Some non-critical components have issues
    - unhealthy: Critical components are failing
    """
    logger.info("health_check_requested")

    # Check all components in parallel
    import asyncio

    db_health, redis_health, vector_health = await asyncio.gather(
        check_database(), check_redis(), check_vector_store(), return_exceptions=True
    )

    # Handle exceptions from health checks
    if isinstance(db_health, Exception):
        db_health = ComponentHealth(status="unhealthy", message=str(db_health))
    if isinstance(redis_health, Exception):
        redis_health = ComponentHealth(status="unhealthy", message=str(redis_health))
    if isinstance(vector_health, Exception):
        vector_health = ComponentHealth(status="unhealthy", message=str(vector_health))

    components: Dict[str, ComponentHealth] = {
        "database": cast(ComponentHealth, db_health),
        "redis": cast(ComponentHealth, redis_health),
        "vector_store": cast(ComponentHealth, vector_health),
    }

    overall_status = determine_overall_status(components)

    response = HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        version="1.0.0",
        components=components,
    )

    if overall_status != "healthy":
        logger.warning(
            "health_check_degraded", status=overall_status, components=components
        )

    return response


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Check if the service is ready to accept requests (for Kubernetes readiness probes).",
)
async def readiness_check() -> Dict[str, str]:
    """
    Readiness probe endpoint.

    Returns 200 if service is ready to accept traffic.
    Used by Kubernetes readiness probes.
    """
    # Check critical components only
    db_health = await check_database()

    if db_health.status == "healthy":
        return {"status": "ready"}
    else:
        return {"status": "not_ready", "reason": db_health.message or "unknown"}


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Check if the service is alive (for Kubernetes liveness probes).",
)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness probe endpoint.

    Always returns 200 if the service is running.
    Used by Kubernetes liveness probes.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="System Metrics",
    description="Get system metrics including uptime, memory usage, and component statistics.",
    operation_id="get_system_metrics",
)
async def get_system_metrics() -> MetricsResponse:
    """
    System metrics endpoint.

    Returns operational metrics for monitoring and observability.
    """
    import psutil

    # Calculate uptime
    uptime = (datetime.now(timezone.utc) - _start_time).total_seconds()

    # Get memory usage
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024

    # Get component stats
    db_stats: Dict[str, Any] = {}
    redis_stats: Dict[str, Any] = {}
    vector_stats: Dict[str, Any] = {}

    try:
        redis_client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        info = redis_client.info()
        used_mem = info.get("used_memory")
        redis_stats = {
            "used_memory_mb": (
                float(used_mem) / 1024 / 1024 if used_mem is not None else 0.0
            ),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands": info.get("total_commands_processed", 0),
        }
        redis_client.close()
    except Exception:
        pass

    return MetricsResponse(
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        uptime_seconds=uptime,
        memory_usage_mb=memory_mb,
        database=db_stats,
        redis=redis_stats,
        vector_store=vector_stats,
    )
