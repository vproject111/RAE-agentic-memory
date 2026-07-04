"""
Governance API - Enterprise Cost Tracking & Budget Management

This module provides comprehensive governance endpoints for:
- Cost tracking and aggregation
- Budget monitoring and alerts
- Token usage analytics
- Multi-tenant cost reporting
- Compliance and audit trails

Endpoints:
- GET /v1/governance/overview - System-wide cost overview
- GET /v1/governance/tenant/{tenant_id} - Tenant-specific statistics
- GET /v1/governance/tenant/{tenant_id}/costs - Detailed cost breakdown
- GET /v1/governance/tenant/{tenant_id}/budget - Budget status
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from apps.memory_api.dependencies import get_db_pool
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import require_admin, verify_tenant_access

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)
router = APIRouter(
    prefix="/governance",
    tags=["Governance"],
    dependencies=[Depends(auth.verify_token)],  # All endpoints require auth
)


# ============================================================================
# Response Models
# ============================================================================


class CostOverview(BaseModel):
    """System-wide cost overview"""

    total_cost_usd: float = Field(..., description="Total cost across all tenants")
    total_calls: int = Field(..., description="Total LLM API calls")
    total_tokens: int = Field(..., description="Total tokens consumed")
    unique_tenants: int = Field(..., description="Number of unique tenants")
    period_start: datetime = Field(..., description="Start of reporting period")
    period_end: datetime = Field(..., description="End of reporting period")
    top_tenants: List[dict] = Field(
        default_factory=list, description="Top 5 tenants by cost"
    )
    top_models: List[dict] = Field(
        default_factory=list, description="Top 5 models by usage"
    )


class TenantGovernanceStats(BaseModel):
    """Tenant-specific governance statistics"""

    tenant_id: UUID
    total_cost_usd: float
    total_calls: int
    total_tokens: int
    average_cost_per_call: float
    cache_hit_rate: float
    cache_savings_usd: float
    period_start: datetime
    period_end: datetime
    by_project: List[dict] = Field(default_factory=list)
    by_model: List[dict] = Field(default_factory=list)
    by_operation: List[dict] = Field(default_factory=list)


class TenantBudgetStatus(BaseModel):
    """Tenant budget status and alerts"""

    tenant_id: UUID
    budget_usd_monthly: Optional[float] = None
    budget_tokens_monthly: Optional[int] = None
    current_month_cost_usd: float
    current_month_tokens: int
    budget_used_percent: Optional[float] = None
    days_remaining: int
    projected_month_end_cost: float
    alerts: List[str] = Field(default_factory=list)
    status: str = Field(..., description="OK, WARNING, CRITICAL, EXCEEDED")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/overview", response_model=CostOverview)
async def get_governance_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    pool=Depends(get_db_pool),
    admin_access: bool = Depends(require_admin),
):
    """
    Get system-wide governance overview.

    Provides aggregate statistics across all tenants for the specified period.
    Useful for platform administrators to monitor overall costs and usage.

    **Permissions:** Admin only
    **Security:** Requires system admin authentication
    """
    with tracer.start_as_current_span("rae.api.governance.overview") as span:
        span.set_attribute("rae.governance.days", days)

        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            logger.info("governance_overview_request", days=days)

            # Get overall statistics
            async with pool.acquire() as conn:
                # Total costs and calls
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*)::int as total_calls,
                        COALESCE(SUM(total_cost_usd), 0) as total_cost_usd,
                        COALESCE(SUM(total_tokens), 0) as total_tokens,
                        COUNT(DISTINCT tenant_id)::int as unique_tenants
                    FROM cost_logs
                    WHERE timestamp >= $1 AND timestamp <= $2
                """,
                    start_date,
                    end_date,
                )

                # Top tenants by cost
                top_tenants_rows = await conn.fetch(
                    """
                    SELECT
                        tenant_id,
                        COUNT(*)::int as calls,
                        COALESCE(SUM(total_cost_usd), 0) as cost_usd,
                        COALESCE(SUM(total_tokens), 0) as tokens
                    FROM cost_logs
                    WHERE timestamp >= $1 AND timestamp <= $2
                    GROUP BY tenant_id
                    ORDER BY cost_usd DESC
                    LIMIT 5
                """,
                    start_date,
                    end_date,
                )

                # Top models by usage
                top_models_rows = await conn.fetch(
                    """
                    SELECT
                        model,
                        COUNT(*)::int as calls,
                        COALESCE(SUM(total_cost_usd), 0) as cost_usd,
                        COALESCE(SUM(total_tokens), 0) as tokens
                    FROM cost_logs
                    WHERE timestamp >= $1 AND timestamp <= $2
                    GROUP BY model
                    ORDER BY calls DESC
                    LIMIT 5
                """,
                    start_date,
                    end_date,
                )

            # Add telemetry attributes
            span.set_attribute(
                "rae.governance.total_cost_usd", float(row["total_cost_usd"])
            )
            span.set_attribute("rae.governance.total_calls", row["total_calls"])
            span.set_attribute("rae.governance.total_tokens", int(row["total_tokens"]))
            span.set_attribute("rae.governance.unique_tenants", row["unique_tenants"])
            span.set_attribute(
                "rae.governance.top_tenants_count", len(top_tenants_rows)
            )
            span.set_attribute("rae.governance.top_models_count", len(top_models_rows))
            span.set_attribute("rae.outcome.label", "success")

            return CostOverview(
                total_cost_usd=float(row["total_cost_usd"]),
                total_calls=row["total_calls"],
                total_tokens=int(row["total_tokens"]),
                unique_tenants=row["unique_tenants"],
                period_start=start_date,
                period_end=end_date,
                top_tenants=[dict(r) for r in top_tenants_rows],
                top_models=[dict(r) for r in top_models_rows],
            )

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("governance_overview_error", error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to get governance overview: {str(e)}"
            ) from e


@router.get("/tenant/{tenant_id}", response_model=TenantGovernanceStats)
async def get_tenant_governance_stats(
    tenant_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    pool=Depends(get_db_pool),
    tenant_access: bool = Depends(verify_tenant_access),
):
    """
    Get comprehensive governance statistics for a specific tenant.

    Includes:
    - Total costs and token usage
    - Breakdown by project, model, and operation
    - Cache hit rates and savings
    - Average cost per API call

    **Permissions:** Tenant owner or admin
    **Security:** Requires authentication and tenant access
    """
    with tracer.start_as_current_span("rae.api.governance.tenant_stats") as span:
        span.set_attribute("rae.tenant_id", tenant_id)
        span.set_attribute("rae.governance.days", days)

        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            logger.info("tenant_governance_request", tenant_id=tenant_id, days=days)

            async with pool.acquire() as conn:
                # Overall tenant statistics
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*)::int as total_calls,
                        COALESCE(SUM(total_cost_usd), 0) as total_cost_usd,
                        COALESCE(SUM(total_tokens), 0) as total_tokens,
                        COALESCE(AVG(total_cost_usd), 0) as avg_cost_per_call,
                        COALESCE(SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0), 0) as cache_hit_rate,
                        COALESCE(SUM(CASE WHEN cache_hit THEN total_cost_usd ELSE 0 END), 0) as cache_savings
                    FROM cost_logs
                    WHERE tenant_id = $1 AND timestamp >= $2 AND timestamp <= $3
                """,
                    tenant_id,
                    start_date,
                    end_date,
                )

                if row["total_calls"] == 0:
                    span.set_attribute("rae.outcome.label", "not_found")
                    raise HTTPException(
                        status_code=404, detail=f"No data found for tenant {tenant_id}"
                    )

                # By project
                by_project_rows = await conn.fetch(
                    """
                    SELECT
                        project_id,
                        COUNT(*)::int as calls,
                        COALESCE(SUM(total_cost_usd), 0) as cost_usd,
                        COALESCE(SUM(total_tokens), 0) as tokens
                    FROM cost_logs
                    WHERE tenant_id = $1 AND timestamp >= $2 AND timestamp <= $3
                    GROUP BY project_id
                    ORDER BY cost_usd DESC
                """,
                    tenant_id,
                    start_date,
                    end_date,
                )

                # By model
                by_model_rows = await conn.fetch(
                    """
                    SELECT
                        model,
                        COUNT(*)::int as calls,
                        COALESCE(SUM(total_cost_usd), 0) as cost_usd,
                        COALESCE(SUM(total_tokens), 0) as tokens
                    FROM cost_logs
                    WHERE tenant_id = $1 AND timestamp >= $2 AND timestamp <= $3
                    GROUP BY model
                    ORDER BY calls DESC
                """,
                    tenant_id,
                    start_date,
                    end_date,
                )

                # By operation
                by_operation_rows = await conn.fetch(
                    """
                    SELECT
                        operation,
                        COUNT(*)::int as calls,
                        COALESCE(SUM(total_cost_usd), 0) as cost_usd,
                        COALESCE(SUM(total_tokens), 0) as tokens
                    FROM cost_logs
                    WHERE tenant_id = $1 AND timestamp >= $2 AND timestamp <= $3
                    GROUP BY operation
                    ORDER BY calls DESC
                """,
                    tenant_id,
                    start_date,
                    end_date,
                )

            # Add telemetry attributes
            span.set_attribute(
                "rae.governance.total_cost_usd", float(row["total_cost_usd"])
            )
            span.set_attribute("rae.governance.total_calls", row["total_calls"])
            span.set_attribute("rae.governance.total_tokens", int(row["total_tokens"]))
            span.set_attribute(
                "rae.governance.avg_cost_per_call", float(row["avg_cost_per_call"])
            )
            span.set_attribute(
                "rae.governance.cache_hit_rate", float(row["cache_hit_rate"])
            )
            span.set_attribute(
                "rae.governance.cache_savings_usd", float(row["cache_savings"])
            )
            span.set_attribute("rae.governance.projects_count", len(by_project_rows))
            span.set_attribute("rae.governance.models_count", len(by_model_rows))
            span.set_attribute(
                "rae.governance.operations_count", len(by_operation_rows)
            )
            span.set_attribute("rae.outcome.label", "success")

            return TenantGovernanceStats(
                tenant_id=tenant_id,
                total_cost_usd=float(row["total_cost_usd"]),
                total_calls=row["total_calls"],
                total_tokens=int(row["total_tokens"]),
                average_cost_per_call=float(row["avg_cost_per_call"]),
                cache_hit_rate=float(row["cache_hit_rate"]),
                cache_savings_usd=float(row["cache_savings"]),
                period_start=start_date,
                period_end=end_date,
                by_project=[dict(r) for r in by_project_rows],
                by_model=[dict(r) for r in by_model_rows],
                by_operation=[dict(r) for r in by_operation_rows],
            )

        except HTTPException:
            raise
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("tenant_governance_error", tenant_id=tenant_id, error=str(e))
            raise HTTPException(
                status_code=500, detail=f"Failed to get tenant statistics: {str(e)}"
            ) from e


@router.get("/tenant/{tenant_id}/budget", response_model=TenantBudgetStatus)
async def get_tenant_budget_status(
    tenant_id: UUID,
    pool=Depends(get_db_pool),
    tenant_access: bool = Depends(verify_tenant_access),
):
    """
    Get current budget status and projections for a tenant.

    Returns:
    - Current month usage (cost and tokens)
    - Budget limits (if configured)
    - Usage percentage
    - Projected month-end cost
    - Alerts if approaching or exceeding limits

    **Permissions:** Tenant owner or admin
    **Security:** Requires authentication and tenant access
    """
    with tracer.start_as_current_span("rae.api.governance.budget_status") as span:
        span.set_attribute("rae.tenant_id", tenant_id)

        try:
            logger.info("tenant_budget_status_request", tenant_id=tenant_id)

            # Get current month start/end
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Calculate days in month and days remaining
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)

            days_in_month = (next_month - month_start).days
            days_elapsed = (now - month_start).days + 1
            days_remaining = days_in_month - days_elapsed

            async with pool.acquire() as conn:
                # Get current month usage
                row = await conn.fetchrow(
                    """
                    SELECT
                        COALESCE(SUM(total_cost_usd), 0) as current_cost_usd,
                        COALESCE(SUM(total_tokens), 0) as current_tokens
                    FROM cost_logs
                    WHERE tenant_id = $1 AND timestamp >= $2
                """,
                    tenant_id,
                    month_start,
                )

                current_cost = float(row["current_cost_usd"])
                current_tokens = int(row["current_tokens"])

                # Get budget limits (stub - would come from budget_service or config)
                # For now, return None to indicate no budget is configured
                budget_usd = None
                budget_tokens = None

                # Calculate projection
                if days_elapsed > 0:
                    daily_avg_cost = current_cost / days_elapsed
                    projected_cost = daily_avg_cost * days_in_month
                else:
                    projected_cost = 0.0

                # Calculate budget usage percentage
                budget_used_percent = None
                if budget_usd:
                    budget_used_percent = (current_cost / budget_usd) * 100

                # Generate alerts
                alerts: List[str] = []
                status = "OK"

                if budget_usd:
                    if current_cost >= budget_usd:
                        alerts.append(
                            f"Budget exceeded: ${current_cost:.2f} / ${budget_usd:.2f}"
                        )
                        status = "EXCEEDED"
                    elif current_cost >= budget_usd * 0.9:
                        alerts.append(
                            f"Critical: 90% of budget used (${current_cost:.2f} / ${budget_usd:.2f})"
                        )
                        status = "CRITICAL"
                    elif current_cost >= budget_usd * 0.75:
                        alerts.append(
                            f"Warning: 75% of budget used (${current_cost:.2f} / ${budget_usd:.2f})"
                        )
                        status = "WARNING"

                    if projected_cost > budget_usd:
                        alerts.append(
                            f"Projected to exceed budget: ${projected_cost:.2f} estimated by month end"
                        )
                        if status == "OK":
                            status = "WARNING"

                if budget_tokens and current_tokens >= budget_tokens:
                    alerts.append(
                        f"Token budget exceeded: {current_tokens:,} / {budget_tokens:,}"
                    )
                    status = "EXCEEDED"

            # Add telemetry attributes
            span.set_attribute("rae.governance.current_month_cost_usd", current_cost)
            span.set_attribute("rae.governance.current_month_tokens", current_tokens)
            span.set_attribute("rae.governance.projected_cost_usd", projected_cost)
            span.set_attribute("rae.governance.days_remaining", days_remaining)
            span.set_attribute("rae.governance.budget_status", status)
            span.set_attribute("rae.governance.alerts_count", len(alerts))
            if budget_usd:
                span.set_attribute("rae.governance.budget_usd", budget_usd)
                span.set_attribute(
                    "rae.governance.budget_used_percent", budget_used_percent
                )
            span.set_attribute("rae.outcome.label", "success")

            return TenantBudgetStatus(
                tenant_id=tenant_id,
                budget_usd_monthly=budget_usd,
                budget_tokens_monthly=budget_tokens,
                current_month_cost_usd=current_cost,
                current_month_tokens=current_tokens,
                budget_used_percent=budget_used_percent,
                days_remaining=days_remaining,
                projected_month_end_cost=projected_cost,
                alerts=alerts,
                status=status,
            )

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error(
                "tenant_budget_status_error", tenant_id=tenant_id, error=str(e)
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to get budget status: {str(e)}"
            ) from e
