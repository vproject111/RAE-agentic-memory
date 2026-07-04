"""
Reflection V2 Models - Actor-Evaluator-Reflector Pattern

This module defines models for the RAE v1 Reflective Memory implementation
following the Actor → Evaluator → Reflector pattern.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from apps.memory_api.utils.datetime_utils import utc_now

# ============================================================================
# Enums
# ============================================================================


class OutcomeType(str, Enum):
    """Outcome of an actor execution"""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


class ErrorCategory(str, Enum):
    """Categories of errors for reflection"""

    TOOL_ERROR = "tool_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    LLM_ERROR = "llm_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN_ERROR = "unknown_error"


class EventType(str, Enum):
    """Types of events in actor execution"""

    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    LLM_CALL = "llm_call"
    LLM_RESPONSE = "llm_response"
    USER_INPUT = "user_input"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"


# ============================================================================
# Event Models
# ============================================================================


@dataclass
class Event:
    """
    A single event in the actor execution trace.

    Represents tool calls, responses, LLM interactions, or errors.
    """

    event_id: str
    event_type: EventType
    timestamp: datetime
    content: str
    metadata: Dict[str, Any]
    tool_name: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


# ============================================================================
# Error Models
# ============================================================================


@dataclass
class ErrorInfo:
    """
    Information about an error that occurred during execution.
    """

    error_category: ErrorCategory
    error_message: str
    error_code: Optional[str] = None
    traceback: Optional[str] = None
    tool_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


# ============================================================================
# Context Models
# ============================================================================


@dataclass
class ReflectionContext:
    """
    Context for generating a reflection.

    Contains all information needed by the ReflectiveEngine to generate
    meaningful reflections and strategies.
    """

    # Core event trace
    events: List[Event]

    # Outcome
    outcome: OutcomeType

    # Session context (required fields must come before optional fields)
    tenant_id: str
    project_id: str

    # Optional fields
    error: Optional[ErrorInfo] = None
    task_description: Optional[str] = None
    task_goal: Optional[str] = None
    session_id: Optional[UUID] = None

    # Additional context
    user_preferences: Optional[Dict[str, Any]] = None
    previous_attempts: int = 0
    related_memory_ids: Optional[List[UUID]] = None

    def __post_init__(self):
        if self.related_memory_ids is None:
            self.related_memory_ids = []


# ============================================================================
# Result Models
# ============================================================================


@dataclass
class ReflectionResult:
    """
    Result of a reflection generation.

    Contains the generated reflection text, optional strategy,
    and scoring/confidence information.
    """

    # Core content
    reflection_text: str
    strategy_text: Optional[str] = None

    # Scoring
    importance: float = 0.5  # 0.0 - 1.0
    confidence: float = 0.5  # 0.0 - 1.0

    # Categorization
    tags: Optional[List[str]] = None
    error_category: Optional[ErrorCategory] = None

    # Relationships
    source_event_ids: Optional[List[str]] = None
    related_memory_ids: Optional[List[UUID]] = None

    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    generated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.source_event_ids is None:
            self.source_event_ids = []
        if self.related_memory_ids is None:
            self.related_memory_ids = []
        if self.metadata is None:
            self.metadata = {}
        if self.generated_at is None:
            self.generated_at = utc_now()


# ============================================================================
# Actor Models
# ============================================================================


@dataclass
class ActorContext:
    """
    Context provided to the Actor for execution.
    """

    system_prompt: str
    user_prompt: str
    working_memory: List[Dict[str, Any]]
    available_tools: List[str]
    budget_tokens: int = 20000


@dataclass
class ActorResult:
    """
    Result of actor execution.
    """

    response: str
    events: List[Event]
    outcome: OutcomeType
    error: Optional[ErrorInfo] = None
    tokens_used: int = 0
    execution_time_ms: int = 0


# ============================================================================
# Evaluator Models
# ============================================================================


class EvaluationCriterion(str, Enum):
    """Criteria for evaluation"""

    CORRECTNESS = "correctness"
    HELPFULNESS = "helpfulness"
    SAFETY = "safety"
    COMPLETENESS = "completeness"
    EFFICIENCY = "efficiency"


@dataclass
class EvaluationResult:
    """
    Result of evaluation.
    """

    is_ok: bool
    score: float  # 0.0 - 1.0
    reasons: List[str]
    criterion_scores: Dict[EvaluationCriterion, float]
    recommendations: Optional[List[str]] = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


# ============================================================================
# Request/Response Models (Pydantic for API)
# ============================================================================


class GenerateReflectionV2Request(BaseModel):
    """Request model for generating reflection v2"""

    tenant_id: str = Field(..., min_length=1, max_length=255)
    project_id: str = Field(..., min_length=1, max_length=255)
    session_id: Optional[UUID] = None

    # Events
    events: List[Dict[str, Any]] = Field(..., min_length=1)

    # Outcome
    outcome: OutcomeType
    error: Optional[Dict[str, Any]] = None

    # Task context
    task_description: Optional[str] = None
    task_goal: Optional[str] = None

    # Options
    generate_strategy: bool = Field(
        default=True, description="Whether to generate a strategy"
    )
    min_importance: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum importance threshold"
    )


class GenerateReflectionV2Response(BaseModel):
    """Response model for reflection generation v2"""

    reflection_id: UUID
    reflection_text: str
    strategy_text: Optional[str] = None
    importance: float
    confidence: float
    tags: List[str]
    message: str = "Reflection generated successfully"


class QueryReflectionsV2Request(BaseModel):
    """Request model for querying reflections with enhanced filtering"""

    tenant_id: str = Field(..., min_length=1, max_length=255)
    project_id: str = Field(..., min_length=1, max_length=255)

    # Query
    query_text: Optional[str] = None
    k: int = Field(default=5, gt=0, le=20)

    # Filters
    memory_types: Optional[List[str]] = Field(
        default=["reflection", "strategy"], description="Memory types to retrieve"
    )
    min_importance: Optional[float] = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum importance score"
    )
    error_categories: Optional[List[ErrorCategory]] = None
    tags: Optional[List[str]] = None

    # Time range
    since: Optional[datetime] = None
    until: Optional[datetime] = None


class QueryReflectionsV2Response(BaseModel):
    """Response model for querying reflections v2"""

    reflections: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    statistics: Dict[str, Any] = Field(default_factory=dict)


class LLMReflectionResponse(BaseModel):
    """Structured response from LLM for reflection generation"""

    reflection: str = Field(..., description="The reflection text")
    strategy: Optional[str] = Field(None, description="Optional strategy text")
    importance: float = Field(0.5, description="Importance score")
    confidence: float = Field(0.5, description="Confidence score")
    tags: List[str] = Field(default_factory=list, description="Relevant tags")

    @field_validator("importance", "confidence", mode="before")
    @classmethod
    def parse_numeric(cls, v):
        if isinstance(v, (int, float)):
            return float(min(1.0, max(0.0, v)))
        if isinstance(v, str):
            # Try to extract number from string (e.g. "0.8" or "80%")
            import re

            match = re.search(r"(\d+(\.\d+)?)", v)
            if match:
                val = float(match.group(1))
                if val > 1.0 and val <= 100.0:
                    val /= 100.0
                return min(1.0, max(0.0, val))
        return 0.5  # Default fallback

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, list):
            return [str(tag) for tag in v]
        if isinstance(v, str):
            # Handle "['tag1', 'tag2']" or "tag1, tag2"
            import ast

            try:
                # Try literal eval for "['a', 'b']"
                res = ast.literal_eval(v)
                if isinstance(res, list):
                    return [str(x) for x in res]
            except Exception:
                pass
            # Fallback to comma split
            return [
                t.strip()
                for t in v.replace("[", "").replace("]", "").replace("'", "").split(",")
                if t.strip()
            ]
        return []
