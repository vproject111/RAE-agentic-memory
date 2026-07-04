"""
Cost Tracker Utility

Handles post-execution cost accounting and budget usage increments.
Used to track costs for successful LLM requests.
"""

import structlog
from fastapi import Request

from apps.memory_api.services.budget_service import BudgetService, BudgetUsageIncrement
from apps.memory_api.services.cost_controller import calculate_cost

logger = structlog.get_logger(__name__)


async def track_request_cost(
    request: Request,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    tenant_id: str,
    project_id: str = "default",
):
    """
    Calculates cost and increments budget usage.
    Should be called after successful LLM execution.
    """
    try:
        # Calculate cost
        cost_info = calculate_cost(
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        total_cost = cost_info["total_cost_usd"]

        # Get DB pool
        if not hasattr(request.app.state, "pool"):
            logger.error("track_cost_no_pool")
            return

        pool = request.app.state.pool

        # Increment usage
        usage = BudgetUsageIncrement(
            cost_usd=total_cost, input_tokens=input_tokens, output_tokens=output_tokens
        )

        await BudgetService(pool).increment_usage(
            tenant_id=tenant_id, project_id=project_id, usage=usage
        )

        logger.info(
            "cost_tracked_successfully",
            tenant_id=tenant_id,
            cost_usd=total_cost,
            tokens=usage.total_tokens,
        )

        return cost_info

    except Exception as e:
        logger.error("track_cost_failed", error=str(e), tenant_id=tenant_id)
        # Don't raise - accounting failure shouldn't fail the user request
