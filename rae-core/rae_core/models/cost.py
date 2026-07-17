from pydantic import BaseModel, Field


class CostVector(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    wall_time_s: float = 0.0
    cpu_s: float = 0.0
    gpu_s: float = 0.0
    ram_gb_s: float = 0.0
    storage_gb_s: float = 0.0
    transfer_mb: float = 0.0
    external_api_currency: float = 0.0
    operator_minutes: float = 0.0


class CostPolicy(BaseModel):
    policy_id: str
    name: str
    weights: dict[str, float] = Field(default_factory=dict)
    budget_ncu_daily: float | None = None
    currency: str = "USD"


class BudgetEnvelope(BaseModel):
    policy_id: str
    daily_limit_ncu: float | None = None
    monthly_limit_ncu: float | None = None
    hard_stop: bool = True
