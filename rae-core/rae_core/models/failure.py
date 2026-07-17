import uuid

from pydantic import BaseModel, Field


class FailureLearningRecord(BaseModel):
    failure_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    failure_type: str
    failure_stage: str
    impact_scope: str = "local"
    wasted_cost: float | None = None
    root_cause_hypothesis: str | None = None
    lesson_learned: str | None = None
    future_guardrail: str | None = None
    retry_recommendation: str | None = None
