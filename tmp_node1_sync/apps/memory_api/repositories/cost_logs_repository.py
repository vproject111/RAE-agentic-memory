"""
Cost Logs Repository - Enterprise-Grade LLM Call Audit Trail

This repository provides comprehensive logging and querying capabilities for LLM API calls,
enabling detailed cost tracking, token usage analysis, and governance reporting.

Features:
- Log all LLM API calls with full metadata (model, provider, tokens, costs)
- Aggregate cost and token statistics by time period
- Calculate cache savings and cost avoidance
- Per-model cost breakdown for optimization analysis
- Multi-tenant isolation via tenant_id filtering
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg
import structlog
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class LLMCallLog(BaseModel):
    """Complete LLM API call log entry"""

    id: str
    tenant_id: str
    project_id: str

    # LLM Metadata
    model: str
    provider: str  # 'openai', 'anthropic', 'google', 'ollama'
    operation: str  # 'query', 'reflection', 'embedding', 'entity_extraction', etc.

    # Token Tracking
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Cost Tracking
    input_cost_per_million: float
    output_cost_per_million: float
    total_cost_usd: float

    # Cache Tracking
    cache_hit: bool = False
    cache_tokens_saved: int = 0

    # Request Context
    request_id: Optional[str] = None
    user_id: Optional[str] = None

    # Performance
    latency_ms: Optional[int] = None
    error: bool = False
    error_message: Optional[str] = None

    # Timestamp
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class LogLLMCallParams(BaseModel):
    """Parameters for logging an LLM API call"""

    tenant_id: str
    project_id: str
    model: str
    provider: str
    operation: str

    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)

    input_cost_per_million: float = Field(..., ge=0)
    output_cost_per_million: float = Field(..., ge=0)
    total_cost_usd: float = Field(..., ge=0)

    cache_hit: bool = False
    cache_tokens_saved: int = Field(0, ge=0)

    request_id: Optional[str] = None
    user_id: Optional[str] = None
    latency_ms: Optional[int] = None
    error: bool = False
    error_message: Optional[str] = None


class CostStatistics(BaseModel):
    """Aggregated cost statistics for a time period"""

    tenant_id: str
    project_id: str

    # Call counts
    total_calls: int
    successful_calls: int
    failed_calls: int

    # Token usage
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int

    # Costs
    total_cost_usd: float
    avg_cost_per_call: float

    # Cache efficiency
    cache_hits: int
    cache_hit_rate: float  # Percentage
    total_tokens_saved: int
    estimated_cost_saved_usd: float

    # Performance
    avg_latency_ms: Optional[float] = None

    # Time period
    period_start: datetime
    period_end: datetime


class ModelBreakdown(BaseModel):
    """Cost breakdown by model"""

    model: str
    provider: str
    total_calls: int
    total_tokens: int
    total_cost_usd: float
    avg_cost_per_call: float
    avg_latency_ms: Optional[float] = None


# ============================================================================
# Repository Functions
# ============================================================================


async def log_llm_call(pool: asyncpg.Pool, params: LogLLMCallParams) -> str:
    """
    Logs a single LLM API call to the cost_logs table.

    This is the primary audit trail function called after every LLM API interaction.

    Args:
        pool: Database connection pool
        params: LLM call parameters with tokens, costs, and metadata

    Returns:
        UUID of the created log entry

    Example:
        log_id = await log_llm_call(pool, LogLLMCallParams(
            tenant_id="tenant-123",
            project_id="project-456",
            model="gpt-4o-mini",
            provider="openai",
            operation="query",
            input_tokens=1500,
            output_tokens=500,
            input_cost_per_million=0.15,
            output_cost_per_million=0.60,
            total_cost_usd=0.000525,
            cache_hit=False
        ))
    """
    logger.info(
        "log_llm_call",
        tenant_id=params.tenant_id,
        project_id=params.project_id,
        model=params.model,
        operation=params.operation,
        input_tokens=params.input_tokens,
        output_tokens=params.output_tokens,
        total_cost_usd=params.total_cost_usd,
        cache_hit=params.cache_hit,
    )

    try:
        record = await pool.fetchrow(
            """
            INSERT INTO cost_logs (
                tenant_id,
                project_id,
                model,
                provider,
                operation,
                input_tokens,
                output_tokens,
                input_cost_per_million,
                output_cost_per_million,
                total_cost_usd,
                cache_hit,
                cache_tokens_saved,
                request_id,
                user_id,
                latency_ms,
                error,
                error_message
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING id
            """,
            params.tenant_id,
            params.project_id,
            params.model,
            params.provider,
            params.operation,
            params.input_tokens,
            params.output_tokens,
            params.input_cost_per_million,
            params.output_cost_per_million,
            params.total_cost_usd,
            params.cache_hit,
            params.cache_tokens_saved,
            params.request_id,
            params.user_id,
            params.latency_ms,
            params.error,
            params.error_message,
        )

        log_id = str(record["id"])
        logger.info("llm_call_logged", log_id=log_id, tenant_id=params.tenant_id)
        return log_id

    except Exception as e:
        logger.error(
            "log_llm_call_failed",
            error=str(e),
            tenant_id=params.tenant_id,
            model=params.model,
        )
        raise


async def get_cost_statistics(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    period_start: datetime,
    period_end: datetime,
) -> CostStatistics:
    """
    Retrieves aggregated cost statistics for a tenant/project over a time period.

    Used by GovernanceService and dashboard analytics.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        period_start: Start of period (inclusive)
        period_end: End of period (inclusive)

    Returns:
        CostStatistics with all aggregated metrics

    Example:
        # Get last 24 hours
        stats = await get_cost_statistics(
            pool,
            "tenant-123",
            "project-456",
            datetime.now() - timedelta(days=1),
            datetime.now()
        )
        print(f"Total cost: ${stats.total_cost_usd:.4f}")
        print(f"Cache hit rate: {stats.cache_hit_rate:.1f}%")
    """
    logger.info(
        "get_cost_statistics",
        tenant_id=tenant_id,
        project_id=project_id,
        period_start=period_start,
        period_end=period_end,
    )

    record = await pool.fetchrow(
        """
        SELECT
            COUNT(*) as total_calls,
            SUM(CASE WHEN error = FALSE THEN 1 ELSE 0 END) as successful_calls,
            SUM(CASE WHEN error = TRUE THEN 1 ELSE 0 END) as failed_calls,

            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            SUM(total_tokens) as total_tokens,

            SUM(total_cost_usd) as total_cost_usd,
            AVG(total_cost_usd) as avg_cost_per_call,

            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
            SUM(CASE WHEN cache_hit THEN cache_tokens_saved ELSE 0 END) as total_tokens_saved,

            AVG(latency_ms) as avg_latency_ms
        FROM cost_logs
        WHERE tenant_id = $1
          AND project_id = $2
          AND timestamp >= $3
          AND timestamp <= $4
        """,
        tenant_id,
        project_id,
        period_start,
        period_end,
    )

    # Calculate derived metrics
    total_calls = record["total_calls"] or 0
    cache_hits = record["cache_hits"] or 0
    cache_hit_rate = (cache_hits / total_calls * 100) if total_calls > 0 else 0.0

    # Estimate cost saved from cache (rough approximation)
    total_tokens_saved = record["total_tokens_saved"] or 0
    avg_cost_per_token = (record["total_cost_usd"] or 0) / (record["total_tokens"] or 1)
    estimated_cost_saved = total_tokens_saved * avg_cost_per_token

    stats = CostStatistics(
        tenant_id=tenant_id,
        project_id=project_id,
        total_calls=total_calls,
        successful_calls=record["successful_calls"] or 0,
        failed_calls=record["failed_calls"] or 0,
        total_input_tokens=record["total_input_tokens"] or 0,
        total_output_tokens=record["total_output_tokens"] or 0,
        total_tokens=record["total_tokens"] or 0,
        total_cost_usd=float(record["total_cost_usd"] or 0),
        avg_cost_per_call=float(record["avg_cost_per_call"] or 0),
        cache_hits=cache_hits,
        cache_hit_rate=cache_hit_rate,
        total_tokens_saved=total_tokens_saved,
        estimated_cost_saved_usd=float(estimated_cost_saved),
        avg_latency_ms=(
            float(record["avg_latency_ms"]) if record["avg_latency_ms"] else None
        ),
        period_start=period_start,
        period_end=period_end,
    )

    logger.info(
        "cost_statistics_retrieved",
        tenant_id=tenant_id,
        total_calls=stats.total_calls,
        total_cost_usd=stats.total_cost_usd,
        cache_hit_rate=stats.cache_hit_rate,
    )

    return stats


async def get_daily_cost(pool: asyncpg.Pool, tenant_id: str, project_id: str) -> float:
    """
    Gets total cost for current day (UTC).

    Convenience function for dashboard "Today's Cost" displays.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier

    Returns:
        Total cost in USD for today
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_end = datetime.now(timezone.utc)

    stats = await get_cost_statistics(
        pool, tenant_id, project_id, today_start, today_end
    )
    return stats.total_cost_usd


async def get_monthly_cost(
    pool: asyncpg.Pool, tenant_id: str, project_id: str
) -> float:
    """
    Gets total cost for current month (UTC).

    Convenience function for dashboard "This Month's Cost" displays.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier

    Returns:
        Total cost in USD for current month
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = now

    stats = await get_cost_statistics(
        pool, tenant_id, project_id, month_start, month_end
    )
    return stats.total_cost_usd


async def get_daily_tokens(pool: asyncpg.Pool, tenant_id: str, project_id: str) -> int:
    """
    Gets total tokens used for current day (UTC).

    Used for token budget enforcement and dashboard displays.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier

    Returns:
        Total tokens (input + output) for today
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_end = datetime.now(timezone.utc)

    stats = await get_cost_statistics(
        pool, tenant_id, project_id, today_start, today_end
    )
    return stats.total_tokens


async def get_monthly_tokens(
    pool: asyncpg.Pool, tenant_id: str, project_id: str
) -> int:
    """
    Gets total tokens used for current month (UTC).

    Used for token budget enforcement and dashboard displays.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier

    Returns:
        Total tokens (input + output) for current month
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = now

    stats = await get_cost_statistics(
        pool, tenant_id, project_id, month_start, month_end
    )
    return stats.total_tokens


async def get_model_breakdown(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    period_start: datetime,
    period_end: datetime,
) -> List[ModelBreakdown]:
    """
    Gets per-model cost breakdown for optimization analysis.

    Helps identify which models are most expensive and where to optimize.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        period_start: Start of period
        period_end: End of period

    Returns:
        List of ModelBreakdown objects sorted by total_cost_usd descending

    Example:
        breakdowns = await get_model_breakdown(
            pool, "tenant-123", "project-456",
            datetime.now() - timedelta(days=7),
            datetime.now()
        )
        for breakdown in breakdowns:
            print(f"{breakdown.model}: ${breakdown.total_cost_usd:.2f}")
    """
    logger.info(
        "get_model_breakdown",
        tenant_id=tenant_id,
        project_id=project_id,
        period_start=period_start,
        period_end=period_end,
    )

    records = await pool.fetch(
        """
        SELECT
            model,
            provider,
            COUNT(*) as total_calls,
            SUM(total_tokens) as total_tokens,
            SUM(total_cost_usd) as total_cost_usd,
            AVG(total_cost_usd) as avg_cost_per_call,
            AVG(latency_ms) as avg_latency_ms
        FROM cost_logs
        WHERE tenant_id = $1
          AND project_id = $2
          AND timestamp >= $3
          AND timestamp <= $4
          AND error = FALSE
        GROUP BY model, provider
        ORDER BY total_cost_usd DESC
        """,
        tenant_id,
        project_id,
        period_start,
        period_end,
    )

    breakdowns = [
        ModelBreakdown(
            model=r["model"],
            provider=r["provider"],
            total_calls=r["total_calls"],
            total_tokens=r["total_tokens"],
            total_cost_usd=float(r["total_cost_usd"]),
            avg_cost_per_call=float(r["avg_cost_per_call"]),
            avg_latency_ms=float(r["avg_latency_ms"]) if r["avg_latency_ms"] else None,
        )
        for r in records
    ]

    logger.info(
        "model_breakdown_retrieved", tenant_id=tenant_id, model_count=len(breakdowns)
    )

    return breakdowns


async def get_cache_savings(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    period_start: datetime,
    period_end: datetime,
) -> Dict[str, Any]:
    """
    Calculates cost savings from cache hits.

    Used for ROI analysis of caching infrastructure.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        period_start: Start of period
        period_end: End of period

    Returns:
        Dictionary with cache savings metrics

    Example:
        savings = await get_cache_savings(
            pool, "tenant-123", "project-456",
            datetime.now() - timedelta(days=30),
            datetime.now()
        )
        print(f"Saved ${savings['estimated_cost_saved_usd']:.2f}")
        print(f"Cache hit rate: {savings['cache_hit_rate']:.1f}%")
    """
    logger.info(
        "get_cache_savings",
        tenant_id=tenant_id,
        project_id=project_id,
        period_start=period_start,
        period_end=period_end,
    )

    record = await pool.fetchrow(
        """
        SELECT
            COUNT(*) as total_calls,
            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
            SUM(CASE WHEN cache_hit THEN cache_tokens_saved ELSE 0 END) as total_tokens_saved,
            SUM(total_cost_usd) as total_actual_cost,
            AVG(total_cost_usd) as avg_cost_per_call
        FROM cost_logs
        WHERE tenant_id = $1
          AND project_id = $2
          AND timestamp >= $3
          AND timestamp <= $4
          AND error = FALSE
        """,
        tenant_id,
        project_id,
        period_start,
        period_end,
    )

    total_calls = record["total_calls"] or 0
    cache_hits = record["cache_hits"] or 0
    total_tokens_saved = record["total_tokens_saved"] or 0
    avg_cost_per_call = float(record["avg_cost_per_call"] or 0)

    # Estimate cost savings (assuming cache hits would have cost avg_cost_per_call)
    estimated_cost_saved = cache_hits * avg_cost_per_call
    cache_hit_rate = (cache_hits / total_calls * 100) if total_calls > 0 else 0.0

    savings = {
        "total_calls": total_calls,
        "cache_hits": cache_hits,
        "cache_hit_rate": cache_hit_rate,
        "total_tokens_saved": total_tokens_saved,
        "estimated_cost_saved_usd": estimated_cost_saved,
        "avg_cost_per_call": avg_cost_per_call,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
    }

    logger.info(
        "cache_savings_calculated",
        tenant_id=tenant_id,
        cache_hits=cache_hits,
        cache_hit_rate=cache_hit_rate,
        estimated_cost_saved_usd=estimated_cost_saved,
    )

    return savings


async def get_recent_logs(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    limit: int = 100,
    include_errors: bool = True,
) -> List[LLMCallLog]:
    """
    Retrieves recent LLM call logs for debugging and monitoring.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        limit: Maximum number of logs to return (default 100)
        include_errors: Whether to include failed calls (default True)

    Returns:
        List of LLMCallLog objects sorted by timestamp descending
    """
    logger.info(
        "get_recent_logs",
        tenant_id=tenant_id,
        project_id=project_id,
        limit=limit,
        include_errors=include_errors,
    )

    error_filter = "" if include_errors else "AND error = FALSE"

    records = await pool.fetch(
        f"""
        SELECT *
        FROM cost_logs
        WHERE tenant_id = $1
          AND project_id = $2
          {error_filter}
        ORDER BY timestamp DESC
        LIMIT $3
        """,  # nosec
        tenant_id,
        project_id,
        limit,
    )

    logs = [LLMCallLog(**dict(r)) for r in records]

    logger.info("recent_logs_retrieved", tenant_id=tenant_id, count=len(logs))
    return logs
