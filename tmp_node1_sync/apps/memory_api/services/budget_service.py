"""
Enterprise Budget Service - Enhanced with Token Tracking

This service provides comprehensive budget management including:
- USD cost tracking (daily/monthly)
- Token usage tracking (daily/monthly)
- Automatic counter resets
- Budget enforcement with detailed error messages
- Integration with cost_logs for audit trail
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import structlog
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class Budget(BaseModel):
    """Enhanced Budget model with token tracking"""

    id: str
    tenant_id: str
    project_id: str

    # USD Limits
    monthly_limit_usd: Optional[float] = Field(
        None, description="Monthly USD limit (NULL = unlimited)"
    )
    daily_limit_usd: Optional[float] = Field(
        None, description="Daily USD limit (NULL = unlimited)"
    )

    # USD Usage
    monthly_usage_usd: float = Field(0.0, ge=0, description="Current monthly USD usage")
    daily_usage_usd: float = Field(0.0, ge=0, description="Current daily USD usage")

    # Token Limits
    monthly_tokens_limit: Optional[int] = Field(
        None, description="Monthly token limit (NULL = unlimited)"
    )
    daily_tokens_limit: Optional[int] = Field(
        None, description="Daily token limit (NULL = unlimited)"
    )

    # Token Usage
    monthly_tokens_used: int = Field(0, ge=0, description="Current monthly tokens used")
    daily_tokens_used: int = Field(0, ge=0, description="Current daily tokens used")

    # Timestamps
    created_at: datetime
    last_usage_at: datetime
    last_token_update_at: datetime
    last_daily_reset: datetime
    last_monthly_reset: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetUsageIncrement(BaseModel):
    """Data model for incrementing budget usage"""

    cost_usd: float = Field(..., ge=0, description="Cost in USD to increment")
    input_tokens: int = Field(..., ge=0, description="Number of input tokens")
    output_tokens: int = Field(..., ge=0, description="Number of output tokens")

    @property
    def total_tokens(self) -> int:
        """Total tokens = input + output"""
        return self.input_tokens + self.output_tokens


class BudgetService:
    """Service for budget and token usage management"""

    def __init__(self, rae_service: RAECoreService):
        """
        Initialize budget service

        Args:
            rae_service: RAECoreService instance for database access
        """
        self.rae_service = rae_service

    async def get_or_create_budget(
        self, tenant_id: str, project_id: str = "default"
    ) -> Budget:
        """
        Retrieves the budget for a tenant/project, creating a new one if needed.
        """
        logger.info("get_or_create_budget", tenant_id=tenant_id, project_id=project_id)

        # Try to fetch existing budget
        record = await self.rae_service.db.fetchrow(
            """
            SELECT * FROM budgets
            WHERE tenant_id = $1 AND project_id = $2
            """,
            tenant_id,
            project_id,
        )

        if not record:
            # Create new budget with default limits
            logger.info(
                "creating_new_budget", tenant_id=tenant_id, project_id=project_id
            )
            record = await self.rae_service.db.fetchrow(
                """
                INSERT INTO budgets (
                    tenant_id,
                    project_id,
                    daily_limit_usd,
                    monthly_limit_usd,
                    daily_tokens_limit,
                    monthly_tokens_limit
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                tenant_id,
                project_id,
                None,
                None,
                None,
                None,
            )
            logger.info(
                "budget_created",
                tenant_id=tenant_id,
                project_id=project_id,
                budget_id=record["id"] if record else "unknown",
            )

        if not record:
            raise RuntimeError("Failed to create budget record")

        return Budget(**dict(record))

    async def check_budget_exceeded(
        self, tenant_id: str, project_id: str = "default"
    ) -> Tuple[bool, float, float]:
        """
        Check if budget is exceeded for a tenant.
        Returns: (is_exceeded, remaining_budget, total_limit)
        """
        budget = await self.get_or_create_budget(tenant_id, project_id)

        # Check monthly limit
        if budget.monthly_limit_usd is not None:
            remaining = budget.monthly_limit_usd - budget.monthly_usage_usd
            if remaining <= 0:
                return True, 0.0, budget.monthly_limit_usd

        # Check daily limit
        if budget.daily_limit_usd is not None:
            remaining = budget.daily_limit_usd - budget.daily_usage_usd
            if remaining <= 0:
                return True, 0.0, budget.daily_limit_usd

        return False, 999999.0, 999999.0

    async def check_budget(
        self, tenant_id: str, project_id: str, cost_usd: float, tokens: int
    ) -> None:
        """
        Checks if a new cost and token usage is within the budget.
        Raises HTTPException(402) if exceeded.
        """
        logger.info(
            "check_budget",
            tenant_id=tenant_id,
            project_id=project_id,
            cost_usd=cost_usd,
            tokens=tokens,
        )

        budget = await self.get_or_create_budget(tenant_id, project_id)
        now = datetime.now()

        # Resets (Safety check, usually handled by DB triggers)
        if budget.last_daily_reset.date() < now.date():
            budget.daily_usage_usd = 0.0
            budget.daily_tokens_used = 0

        if (budget.last_monthly_reset.year < now.year) or (
            budget.last_monthly_reset.year == now.year
            and budget.last_monthly_reset.month < now.month
        ):
            budget.monthly_usage_usd = 0.0
            budget.monthly_tokens_used = 0

        # Check limits
        if budget.daily_limit_usd is not None:
            if budget.daily_usage_usd + cost_usd > budget.daily_limit_usd:
                raise HTTPException(status_code=402, detail="Daily USD budget exceeded")

        if budget.monthly_limit_usd is not None:
            if budget.monthly_usage_usd + cost_usd > budget.monthly_limit_usd:
                raise HTTPException(
                    status_code=402, detail="Monthly USD budget exceeded"
                )

        if budget.daily_tokens_limit is not None:
            if budget.daily_tokens_used + tokens > budget.daily_tokens_limit:
                raise HTTPException(
                    status_code=402, detail="Daily token budget exceeded"
                )

        if budget.monthly_tokens_limit is not None:
            if budget.monthly_tokens_used + tokens > budget.monthly_tokens_limit:
                raise HTTPException(
                    status_code=402, detail="Monthly token budget exceeded"
                )

    async def increment_usage(
        self, tenant_id: str, project_id: str, usage: BudgetUsageIncrement
    ) -> None:
        """Increments usage for USD and tokens."""
        logger.info(
            "increment_usage",
            tenant_id=tenant_id,
            project_id=project_id,
            cost_usd=usage.cost_usd,
            total_tokens=usage.total_tokens,
        )

        await self.rae_service.db.execute(
            """
            UPDATE budgets
            SET
                daily_usage_usd = daily_usage_usd + $3,
                monthly_usage_usd = monthly_usage_usd + $3,
                daily_tokens_used = daily_tokens_used + $4,
                monthly_tokens_used = monthly_tokens_used + $4,
                last_usage_at = NOW(),
                last_token_update_at = NOW()
            WHERE tenant_id = $1 AND project_id = $2
            """,
            tenant_id,
            project_id,
            usage.cost_usd,
            usage.total_tokens,
        )

    async def get_budget_status(
        self, tenant_id: str, project_id: str
    ) -> Dict[str, Any]:
        """Returns current budget status including usage percentages."""
        budget = await self.get_or_create_budget(tenant_id, project_id)

        return {
            "tenant_id": budget.tenant_id,
            "project_id": budget.project_id,
            "usd": {
                "daily": {
                    "usage": float(budget.daily_usage_usd),
                    "limit": budget.daily_limit_usd,
                    "available": (
                        float(budget.daily_limit_usd - budget.daily_usage_usd)
                        if budget.daily_limit_usd
                        else None
                    ),
                },
                "monthly": {
                    "usage": float(budget.monthly_usage_usd),
                    "limit": budget.monthly_limit_usd,
                    "available": (
                        float(budget.monthly_limit_usd - budget.monthly_usage_usd)
                        if budget.monthly_limit_usd
                        else None
                    ),
                },
            },
            "tokens": {
                "daily": {
                    "usage": budget.daily_tokens_used,
                    "limit": budget.daily_tokens_limit,
                },
                "monthly": {
                    "usage": budget.monthly_tokens_used,
                    "limit": budget.monthly_tokens_limit,
                },
            },
            "last_usage_at": budget.last_usage_at.isoformat(),
        }

    async def set_budget_limits(
        self,
        tenant_id: str,
        project_id: str,
        daily_limit_usd: Optional[float] = None,
        monthly_limit_usd: Optional[float] = None,
        daily_tokens_limit: Optional[int] = None,
        monthly_tokens_limit: Optional[int] = None,
    ) -> Budget:
        """Updates budget limits."""
        # Ensure budget exists
        await self.get_or_create_budget(tenant_id, project_id)

        record = await self.rae_service.db.fetchrow(
            """
            UPDATE budgets
            SET
                daily_limit_usd = $3,
                monthly_limit_usd = $4,
                daily_tokens_limit = $5,
                monthly_tokens_limit = $6
            WHERE tenant_id = $1 AND project_id = $2
            RETURNING *
            """,
            tenant_id,
            project_id,
            daily_limit_usd,
            monthly_limit_usd,
            daily_tokens_limit,
            monthly_tokens_limit,
        )

        if not record:
            raise RuntimeError("Failed to update budget limits")

        return Budget(**dict(record))
