from __future__ import annotations
from typing import Any, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

class ImprovementProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    experiment_id: str = ""
    rationale: str = ""
    proposed_patch: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    promotion_requirements: dict[str, Any] = Field(default_factory=dict)

class PromotionDecision(BaseModel):
    proposal_id: str
    approved: bool
    reason: str

class PolicyPatchProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    target_policy_id: str
    rationale: str
    proposed_patch: dict[str, Any] = Field(default_factory=dict)

class ExperimentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: Optional[str] = None
    experiment_id: str = ""
    mode: str
    result: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    trace_id: str = ""

class Experiment(BaseModel):
    experiment_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    hypothesis_id: str
    candidate: str
    success_criteria: str

class Hypothesis(BaseModel):
    hypothesis_id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str
    motivation: str
    target_metric: str

class InsightPack(BaseModel):
    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    insights: List[Any] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class RollbackDecision(BaseModel):
    proposal_id: str
    rollback_triggered: bool
    reason: str

class FailurePatternPack(BaseModel):
    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    patterns: List[Any] = Field(default_factory=list)
