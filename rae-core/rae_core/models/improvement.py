from __future__ import annotations
from typing import Any, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

class ImprovementProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    rationale: str
    proposed_patch: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"

class PolicyPatchProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    target_policy_id: str
    rationale: str
    proposed_patch: dict[str, Any] = Field(default_factory=dict)

class ExperimentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: str
    mode: str
    result: str

class Hypothesis(BaseModel):
    hypothesis_id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str
    motivation: str
    target_metric: str
