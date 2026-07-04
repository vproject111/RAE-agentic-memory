from datetime import datetime
from typing import Optional

import structlog

from apps.memory_api.models.token_savings import SavingsSummary, TokenSavingsEntry
from apps.memory_api.repositories.token_savings_repository import TokenSavingsRepository
from apps.memory_api.services.cost_controller import calculate_cost

logger = structlog.get_logger(__name__)


class TokenSavingsService:
    """
    Service for calculating and tracking token savings.
    """

    def __init__(self, repository: TokenSavingsRepository):
        self.repository = repository

    async def track_savings(
        self,
        tenant_id: str,
        project_id: str,
        model: str,
        predicted_tokens: int,
        real_tokens: int,
        savings_type: str,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Calculate and log savings from an optimization event.

        Args:
            predicted_tokens: Tokens that WOULD have been used without optimization.
            real_tokens: Tokens ACTUALLY used (e.g. 0 for cache hit).
        """
        if predicted_tokens <= real_tokens:
            return  # No savings

        saved_tokens = predicted_tokens - real_tokens

        # Calculate estimated money saved
        # We assume the saved tokens are proportional mix of input/output or mostly input
        # For simplicity in v1, we treat saved tokens as INPUT tokens cost,
        # as optimizations (cache, RAG filtering) usually save on input context.
        cost_info = calculate_cost(model, input_tokens=saved_tokens, output_tokens=0)
        saved_usd = cost_info.get("total_cost_usd", 0.0)

        entry = TokenSavingsEntry(
            tenant_id=tenant_id,
            project_id=project_id,
            request_id=request_id,
            predicted_tokens=predicted_tokens,
            real_tokens=real_tokens,
            saved_tokens=saved_tokens,
            savings_type=savings_type,
            model=model,
            estimated_cost_saved_usd=saved_usd,
        )

        await self.repository.log_savings(entry)
        logger.info(
            "savings_tracked",
            saved_tokens=saved_tokens,
            saved_usd=saved_usd,
            type=savings_type,
        )

    async def get_summary(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SavingsSummary:
        return await self.repository.get_savings_summary(
            tenant_id, project_id, start_date, end_date
        )

    async def get_timeseries(self, tenant_id: str) -> list[dict]:
        return await self.repository.get_timeseries(tenant_id)
