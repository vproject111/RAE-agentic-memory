"""
Event Triggers & Automations Models - Rule-Based Event System

This module defines models for the event trigger system including:
- Event definitions and types
- Trigger conditions and rules
- Actions and workflows
- Automation chains
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Enums
# ============================================================================


class EventType(str, Enum):
    """Types of system events"""

    MEMORY_CREATED = "memory_created"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"
    MEMORY_ACCESSED = "memory_accessed"

    REFLECTION_GENERATED = "reflection_generated"
    SEMANTIC_NODE_CREATED = "semantic_node_created"
    SEMANTIC_NODE_DEGRADED = "semantic_node_degraded"

    SEARCH_EXECUTED = "search_executed"
    QUERY_ANALYZED = "query_analyzed"

    DRIFT_DETECTED = "drift_detected"
    QUALITY_DEGRADED = "quality_degraded"

    THRESHOLD_EXCEEDED = "threshold_exceeded"
    SCHEDULE_TRIGGERED = "schedule_triggered"


class ConditionOperator(str, Enum):
    """Operators for condition evaluation"""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    MATCHES_REGEX = "matches_regex"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class ActionType(str, Enum):
    """Types of automated actions"""

    SEND_NOTIFICATION = "send_notification"
    SEND_EMAIL = "send_email"
    SEND_WEBHOOK = "send_webhook"

    CREATE_MEMORY = "create_memory"
    UPDATE_MEMORY = "update_memory"
    DELETE_MEMORY = "delete_memory"

    GENERATE_REFLECTION = "generate_reflection"
    EXTRACT_SEMANTICS = "extract_semantics"

    APPLY_DECAY = "apply_decay"
    REINFORCE_NODE = "reinforce_node"

    CREATE_SNAPSHOT = "create_snapshot"
    RUN_EVALUATION = "run_evaluation"

    EXECUTE_WORKFLOW = "execute_workflow"
    TRIGGER_ANOTHER_RULE = "trigger_another_rule"


class TriggerStatus(str, Enum):
    """Status of trigger"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    """Status of action execution"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# Core Event Models
# ============================================================================


class Event(BaseModel):
    """
    A system event that can trigger automation rules.

    Events are emitted by various system components and evaluated
    against trigger conditions.
    """

    event_id: UUID
    event_type: EventType

    # Event source
    tenant_id: str
    project_id: str
    source_service: str = Field(..., description="Service that emitted the event")

    # Event data
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data"
    )

    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[UUID] = None

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Trigger Condition Models
# ============================================================================


class Condition(BaseModel):
    """
    A single condition in a trigger rule.

    Evaluates a field against a value using an operator.
    """

    field: str = Field(..., description="Field to evaluate (supports dot notation)")
    operator: ConditionOperator
    value: Any = Field(..., description="Value to compare against")

    # Optional modifiers
    case_sensitive: bool = Field(True, description="For string comparisons")
    negate: bool = Field(False, description="Invert the condition result")


class ConditionGroup(BaseModel):
    """
    Group of conditions with AND/OR logic.

    Supports nested condition groups for complex logic.
    """

    operator: str = Field(..., description="'AND' or 'OR'")
    conditions: List[Union[Condition, "ConditionGroup"]] = Field(default_factory=list)

    # Allow nested groups
    groups: List["ConditionGroup"] = Field(default_factory=list)


# Allow recursive type
ConditionGroup.model_rebuild()


class TriggerCondition(BaseModel):
    """
    Complete trigger condition with event type and condition logic.

    Defines when a trigger should fire.
    """

    event_types: List[EventType] = Field(
        ..., min_length=1, description="Events to match"
    )

    # Condition logic (optional - fires on any matching event if not specified)
    condition_group: Optional[ConditionGroup] = None

    # Time-based conditions
    time_window_seconds: Optional[int] = Field(
        default=None, description="Only fire within time window"
    )
    cooldown_seconds: Optional[int] = Field(
        default=None, description="Min time between firings"
    )

    # Rate limiting
    max_executions_per_hour: Optional[int] = None


# ============================================================================
# Action Models
# ============================================================================


class ActionConfig(BaseModel):
    """
    Configuration for an automated action.

    Defines what should happen when a trigger fires.
    """

    action_type: ActionType

    # Action-specific configuration
    config: Dict[str, Any] = Field(default_factory=dict)

    # Conditional execution
    execute_if: Optional[ConditionGroup] = None

    # Error handling
    retry_on_failure: bool = Field(default=False)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, gt=0)

    # Execution constraints
    timeout_seconds: int = Field(default=300, gt=0)
    run_async: bool = Field(default=True, description="Execute asynchronously")


class WorkflowStep(BaseModel):
    """
    A single step in a workflow chain.

    Workflows allow multiple actions to be executed in sequence.
    """

    step_id: str = Field(..., max_length=100)
    step_name: str
    description: Optional[str] = None

    # Action to execute
    action: ActionConfig

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list, description="Step IDs that must complete first"
    )

    # Conditional execution
    skip_if: Optional[ConditionGroup] = None

    # Step ordering
    order: int = Field(1, ge=1)


class Workflow(BaseModel):
    """
    Chain of actions to execute as a workflow.

    Supports sequential and parallel execution with dependencies.
    """

    workflow_id: UUID
    workflow_name: str
    description: Optional[str] = None

    # Steps
    steps: List[WorkflowStep] = Field(..., min_length=1)

    # Execution mode
    stop_on_failure: bool = Field(True, description="Stop if any step fails")
    parallel_execution: bool = Field(
        False, description="Execute steps in parallel when possible"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Trigger Definition Models
# ============================================================================


class TriggerRule(BaseModel):
    """
    Complete trigger rule definition.

    Defines conditions and actions for event-based automation.
    """

    trigger_id: UUID
    tenant_id: str
    project_id: str

    # Rule identification
    rule_name: str = Field(..., max_length=200)
    description: Optional[str] = None

    # Trigger conditions
    condition: TriggerCondition

    # Actions to execute
    actions: List[ActionConfig] = Field(default_factory=list)
    workflow_id: Optional[UUID] = Field(None, description="Or execute a workflow")

    # Priority and ordering
    priority: int = Field(5, ge=1, le=10, description="Higher priority = execute first")

    # Status and control
    status: TriggerStatus = Field(TriggerStatus.ACTIVE)
    is_enabled: bool = Field(True)

    # Execution tracking
    execution_count: int = Field(0, ge=0)
    last_executed_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None

    # Rate limiting state
    executions_this_hour: int = Field(0, ge=0)
    hour_window_start: Optional[datetime] = None

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Ownership
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Execution Models
# ============================================================================


class ActionExecution(BaseModel):
    """
    Record of an action execution.

    Tracks execution history and results for debugging and auditing.
    """

    execution_id: UUID
    trigger_id: UUID

    # Event that triggered this
    event_id: UUID
    event_type: EventType

    # Action details
    action_type: ActionType
    action_config: Dict[str, Any] = Field(default_factory=dict)

    # Execution
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Results
    success: bool = Field(False)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    # Retry info
    attempt_number: int = Field(1, ge=1)
    max_attempts: int = Field(1, ge=1)

    # Context
    tenant_id: str
    project_id: str

    model_config = ConfigDict(from_attributes=True)


class TriggerExecutionSummary(BaseModel):
    """
    Summary of trigger executions.

    Provides statistics for monitoring and debugging.
    """

    trigger_id: UUID
    trigger_name: str

    # Execution stats
    total_executions: int = Field(0, ge=0)
    successful_executions: int = Field(0, ge=0)
    failed_executions: int = Field(0, ge=0)

    # Timing
    avg_duration_ms: float = Field(0.0, ge=0.0)
    min_duration_ms: Optional[int] = None
    max_duration_ms: Optional[int] = None

    # Recent activity
    last_execution_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None

    # Time period
    period_start: datetime
    period_end: datetime


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateTriggerRequest(BaseModel):
    """Request to create a trigger rule"""

    tenant_id: str
    project_id: str
    rule_name: str = Field(..., max_length=200)
    description: Optional[str] = None

    condition: TriggerCondition
    actions: List[ActionConfig] = Field(..., min_length=1)

    priority: int = Field(5, ge=1, le=10)
    is_enabled: bool = Field(True)

    tags: List[str] = Field(default_factory=list)
    created_by: str


class CreateTriggerResponse(BaseModel):
    """Response from trigger creation"""

    trigger_id: UUID
    message: str = "Trigger rule created successfully"


class UpdateTriggerRequest(BaseModel):
    """Request to update a trigger"""

    rule_name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[TriggerCondition] = None
    actions: Optional[List[ActionConfig]] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None
    status: Optional[TriggerStatus] = None


class EmitEventRequest(BaseModel):
    """Request to emit a custom event"""

    tenant_id: str
    project_id: str
    event_type: EventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    user_id: Optional[str] = None


class EmitEventResponse(BaseModel):
    """Response from event emission"""

    event_id: UUID
    triggers_matched: int = Field(0, ge=0)
    actions_queued: int = Field(0, ge=0)
    message: str = "Event emitted successfully"


class GetTriggerExecutionsRequest(BaseModel):
    """Request to get trigger execution history"""

    trigger_id: UUID
    limit: int = Field(100, gt=0, le=1000)
    status_filter: Optional[ExecutionStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class GetTriggerExecutionsResponse(BaseModel):
    """Response with trigger executions"""

    executions: List[ActionExecution]
    total_count: int
    summary: TriggerExecutionSummary


class CreateWorkflowRequest(BaseModel):
    """Request to create a workflow"""

    tenant_id: str
    project_id: str
    workflow_name: str
    description: Optional[str] = None
    steps: List[WorkflowStep] = Field(..., min_length=1)
    stop_on_failure: bool = Field(True)
    parallel_execution: bool = Field(False)
    created_by: str


class CreateWorkflowResponse(BaseModel):
    """Response from workflow creation"""

    workflow_id: UUID
    message: str = "Workflow created successfully"


# ============================================================================
# Pre-configured Trigger Templates
# ============================================================================


class TriggerTemplate(BaseModel):
    """
    Pre-configured trigger template for common use cases.

    Templates can be instantiated with minimal configuration.
    """

    template_id: str = Field(..., max_length=100)
    template_name: str
    description: str
    category: str = Field(
        ..., description="Template category (e.g., 'quality', 'automation')"
    )

    # Template parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_parameters: List[str] = Field(default_factory=list)

    # Default configuration
    default_condition: TriggerCondition
    default_actions: List[ActionConfig]

    # Example usage
    example_config: Optional[Dict[str, Any]] = None
    use_cases: List[str] = Field(default_factory=list)


# Pre-defined templates
DEFAULT_TEMPLATES = {
    "auto_reflection": TriggerTemplate(
        template_id="auto_reflection",
        template_name="Automatic Reflection Generation",
        description="Generate reflections when memory count reaches threshold",
        category="automation",
        parameters={"memory_threshold": 50},
        required_parameters=["memory_threshold"],
        default_condition=TriggerCondition(event_types=[EventType.MEMORY_CREATED]),
        default_actions=[
            ActionConfig(action_type=ActionType.GENERATE_REFLECTION, config={})
        ],
        use_cases=["Periodic knowledge consolidation", "Automatic insight generation"],
    ),
    "quality_alert": TriggerTemplate(
        template_id="quality_alert",
        template_name="Quality Degradation Alert",
        description="Send notification when quality metrics drop",
        category="quality",
        parameters={"min_quality_score": 0.7},
        required_parameters=["min_quality_score"],
        default_condition=TriggerCondition(event_types=[EventType.QUALITY_DEGRADED]),
        default_actions=[
            ActionConfig(
                action_type=ActionType.SEND_NOTIFICATION, config={"channel": "email"}
            )
        ],
        use_cases=["Quality monitoring", "Alert on degradation"],
    ),
}
