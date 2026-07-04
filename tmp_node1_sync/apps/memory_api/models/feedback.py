from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    memory_id: str = Field(..., description="ID of the memory to provide feedback on")
    feedback_type: str = Field(
        ..., pattern="^(positive|negative)$", description="Type of feedback"
    )
    score: Optional[float] = Field(
        None, description="Numeric score from -1.0 to 1.0 (derived from type if missing)"
    )
    query_text: Optional[str] = Field(
        None, description="The query that triggered this result"
    )
    comment: Optional[str] = Field(None, description="Optional comment")
    context_id: Optional[str] = Field(
        None, description="Context/Trace ID where memory was used"
    )
    weights_snapshot: Optional[Dict[str, float]] = Field(
        None, description="Weights used during query (alpha, beta, gamma)"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

