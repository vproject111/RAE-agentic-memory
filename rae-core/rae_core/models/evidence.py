from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import uuid
from rae_core.models.cost import CostVector

class ActionRecord(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    department: str
    role: str
    goal: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str

class DecisionEvidenceRecord(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_summary: str
    reasoning_summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    cost_vector: Optional[CostVector] = None

class OutcomeRecord(BaseModel):
    outcome_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str
    result: str
    cost_vector: Optional[CostVector] = None
