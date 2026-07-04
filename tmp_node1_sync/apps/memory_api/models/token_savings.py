from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TokenSavingsEntry(BaseModel):
    """Data model for a single token savings event."""

    tenant_id: str
    project_id: str
    request_id: Optional[str] = None
    predicted_tokens: int
    real_tokens: int
    saved_tokens: Optional[int] = None
    savings_type: str = Field(
        ..., description="Type of optimization: 'cache', 'rag', 'rerank'"
    )
    model: Optional[str] = None
    estimated_cost_saved_usd: float = 0.0
    timestamp: Optional[datetime] = None


class SavingsSummary(BaseModel):
    """Aggregated savings statistics."""

    total_saved_tokens: int
    total_saved_usd: float
    savings_by_type: dict[str, int]
    period_start: datetime
    period_end: datetime
