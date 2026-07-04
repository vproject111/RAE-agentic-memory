from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from apps.memory_api.models.token_savings import SavingsSummary
from apps.memory_api.repositories.token_savings_repository import TokenSavingsRepository
from apps.memory_api.services.token_savings_service import TokenSavingsService

router = APIRouter()


def get_savings_service(request: Request) -> TokenSavingsService:
    pool = request.app.state.pool
    repo = TokenSavingsRepository(pool)
    return TokenSavingsService(repo)


@router.get("/metrics/savings", response_model=SavingsSummary)
async def get_savings_summary(
    request: Request,
    project_id: Optional[str] = None,
    period: str = Query("30d", description="Period for summary: 24h, 7d, 30d"),
    service: TokenSavingsService = Depends(get_savings_service),
):
    """
    Get aggregated token savings summary.
    """
    tenant_id = request.state.tenant_id

    # Parse period
    now = datetime.now()
    if period == "24h":
        start_date = now - timedelta(days=1)
    elif period == "7d":
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=30)

    return await service.get_summary(
        tenant_id=tenant_id, project_id=project_id, start_date=start_date, end_date=now
    )


@router.get("/metrics/savings/graph")
async def get_savings_graph(
    request: Request,
    interval: str = Query("day", description="Bucket interval: hour, day"),
    service: TokenSavingsService = Depends(get_savings_service),
):
    """
    Get timeseries data for savings visualization.
    """
    tenant_id = request.state.tenant_id
    data = await service.get_timeseries(tenant_id)
    return {"data": data}
