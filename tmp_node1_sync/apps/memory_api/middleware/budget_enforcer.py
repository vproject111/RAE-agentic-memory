"""
Cost Guard Middleware

Actively enforces budget limits by checking if a tenant has exceeded their budget
before processing the request. Returns HTTP 402 Payment Required if budget is exceeded.
"""

import structlog
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from apps.memory_api.config import settings
from apps.memory_api.services.budget_service import BudgetService

logger = structlog.get_logger(__name__)


class BudgetEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware that blocks requests if the tenant has exceeded their budget.
    This is a "Pre-Flight" check. It does not track costs, only enforces limits.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip for health checks and non-LLM endpoints
        if request.url.path.startswith(
            ("/health", "/metrics", "/docs", "/openapi.json")
        ):
            return await call_next(request)

        # Skip if cost tracking is disabled
        if not settings.ENABLE_COST_TRACKING:
            return await call_next(request)

        # Get tenant ID from header
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            # If no tenant ID, we can't check budget.
            # Depending on policy, we might allow or block.
            # For now, we allow (as some endpoints might not need tenant context)
            return await call_next(request)

        # Check budget
        # We need a database connection. The app state should have the pool.
        if not hasattr(request.app.state, "pool"):
            logger.error("cost_guard_no_db_pool")
            return await call_next(request)

        try:
            pool = request.app.state.pool
            budget_service = BudgetService(pool)

            # Check if budget is exceeded
            is_exceeded, remaining, limit = await budget_service.check_budget_exceeded(
                tenant_id
            )

            if is_exceeded:
                logger.warning(
                    "budget_exceeded_blocking_request",
                    tenant_id=tenant_id,
                    remaining=remaining,
                    limit=limit,
                    path=request.url.path,
                )
                return Response(
                    content='{"error": "Budget exceeded. Please upgrade your plan or wait for the next billing cycle."}',
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    media_type="application/json",
                )

        except Exception as e:
            # If checking budget fails, log error but allow request (fail open)
            logger.error("cost_guard_check_failed", error=str(e), tenant_id=tenant_id)

        return await call_next(request)
