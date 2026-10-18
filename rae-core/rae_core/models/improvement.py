from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    hypothesis_id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str
    motivation: str
    target_metric: str
    origin: str = "lab"


class FailurePatternPack(BaseModel):
    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    version: str = "1.0.0"
    patterns: list[dict[str, Any]]
    source_failures: list[str]


class InsightPack(BaseModel):
    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    insights: list[dict[str, Any]]
    recommendations: list[str]


class ImprovementProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    experiment_id: str = ""
    rationale: str = ""
    proposed_patch: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    promotion_requirements: list[str] | dict[str, Any] = Field(default_factory=dict)


class PolicyPatchProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    target_policy_id: str
    patch_payload: dict[str, Any]
    epistemic_status: str = "proposed"


class Experiment(BaseModel):
    experiment_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    hypothesis_id: str
    candidate: str = ""
    success_criteria: str = ""


class ExperimentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: str = ""
    experiment_id: str = ""
    mode: str = "shadow"  # shadow | canary | offline
    result: str = "pass"  # pass | fail
    role: str | None = None  # e.g., L1_writer, L2_auditor
    model_ref: str | None = None  # e.g., ollama/qwen3.5:9b
    metrics: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None


class PromotionDecision(BaseModel):
    proposal_id: str
    approved: bool
    reason: str


class RollbackDecision(BaseModel):
    proposal_id: str
    rollback_triggered: bool = False
    reason: str
