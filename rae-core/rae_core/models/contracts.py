from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class AgentDecision(str, Enum):
    PROCEED = "proceed"
    RETRY = "retry"
    ABORT = "abort"
    INSUFFICIENT_DATA = "insufficient_data"
    ESCALATE = "escalate"

class AgentOutputContract(BaseModel):
    """
    Level 1 Contract: Structural Integrity.
    Every agent response MUST follow this schema.
    """
    analysis: str = Field(..., min_length=10, description="Deep reasoning behind the decision")
    decision: AgentDecision = Field(..., description="Selected action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    retrieved_sources: List[str] = Field(default_factory=list, description="IDs of memories used as evidence")
    pattern_used: Optional[str] = Field(None, description="The agentic pattern used (e.g., Double-Check)")

    @field_validator('confidence')
    @classmethod
    def symmetry_check(cls, v: float, info: Any) -> float:
        # Epistemic Rule: High confidence requires evidence
        return v

class ContractValidationResult(BaseModel):
    """Result of the 3-stage validation pipeline."""
    is_valid: bool = False
    level: int = 1 # 1: Structural, 2: Semantic, 3: Epistemic
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AutonomyState(str, Enum):
    """Immutable steps of RAE Sequence of Autonomy under Hard Frames mode."""
    INIT = "INIT"
    INTENT_DECLARED = "INTENT_DECLARED"
    RISK_ASSESSED = "RISK_ASSESSED"
    CAPABILITY_GRANTED = "CAPABILITY_GRANTED"
    SANDBOX_READY = "SANDBOX_READY"
    DRY_RUN_PASSED = "DRY_RUN_PASSED"
    QUALITY_GATE_PASSED = "QUALITY_GATE_PASSED"
    EVIDENCE_PACKED = "EVIDENCE_PACKED"
    DECISION_RECORDED = "DECISION_RECORDED"
    MEMORY_COMMITTED = "MEMORY_COMMITTED"
    ROLLBACK_TRIGGERED = "ROLLBACK_TRIGGERED"

