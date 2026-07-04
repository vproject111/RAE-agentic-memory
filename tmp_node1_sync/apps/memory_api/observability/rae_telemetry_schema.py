"""
RAE Telemetry Schema v1

Standardized attribute names and semantic conventions for RAE observability.
This schema ensures consistency across all telemetry data and enables:
- Research: Reproducible analysis of agent behavior
- Operations: Reliable monitoring and debugging
- Governance: Compliance with ISO 42001 and regulatory requirements

Schema versioning: MAJOR.MINOR
- MAJOR: Breaking changes to attribute semantics
- MINOR: Additive changes (new attributes)
"""

from enum import Enum

# Schema version
SCHEMA_VERSION = "1.0"


# ============================================================================
# Agent Attributes
# ============================================================================


class AgentRole(str, Enum):
    """Agent role in the system."""

    PLANNER = "planner"
    EVALUATOR = "evaluator"
    WORKER = "worker"
    ROUTER = "router"
    REFLECTOR = "reflector"
    SYNTHESIZER = "synthesizer"
    ORCHESTRATOR = "orchestrator"


class RAEAgentAttributes:
    """Agent-related attributes."""

    # Agent identification
    ROLE = "rae.agent.role"  # AgentRole enum
    ID = "rae.agent.id"  # Unique agent instance ID
    VERSION = "rae.agent.version"  # Agent version

    # Agent state
    STATE = "rae.agent.state"  # active, paused, terminated
    PARENT_AGENT_ID = "rae.agent.parent_id"  # For hierarchical agents


# ============================================================================
# Memory Attributes
# ============================================================================


class MemoryLayer(str, Enum):
    """Memory layer type."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    REFLECTIVE = "reflective"
    GRAPH = "graph"
    WORKING = "working"
    LONG_TERM = "long_term"


class RAEMemoryAttributes:
    """Memory-related attributes."""

    # Memory layer
    LAYER = "rae.memory.layer"  # MemoryLayer enum
    OPERATION = "rae.memory.operation"  # create, read, update, delete, search

    # Memory metrics
    ACCESS_COUNT = "rae.memory.access_count"  # Number of memory accesses
    HIT_RATE = "rae.memory.hit_rate"  # Cache hit rate (0.0-1.0)
    VECTOR_COUNT = "rae.memory.vector_count"  # Number of vectors processed
    SIMILARITY_THRESHOLD = "rae.memory.similarity_threshold"  # Search threshold

    # Graph-specific
    GRAPH_NODES = "rae.memory.graph_nodes"  # Number of nodes
    GRAPH_EDGES = "rae.memory.graph_edges"  # Number of edges
    GRAPH_DEPTH = "rae.memory.graph_depth"  # Traversal depth

    # Memory quality
    IMPORTANCE_SCORE = "rae.memory.importance_score"  # Memory importance (0.0-1.0)
    DECAY_RATE = "rae.memory.decay_rate"  # Memory decay rate


# ============================================================================
# Reasoning Attributes
# ============================================================================


class ReasoningStepType(str, Enum):
    """Type of reasoning step."""

    DECOMPOSE = "decompose"  # Task decomposition
    RETRIEVE = "retrieve"  # Information retrieval
    REFLECT = "reflect"  # Self-reflection
    REVISE = "revise"  # Revision/correction
    DECIDE = "decide"  # Decision making
    SYNTHESIZE = "synthesize"  # Information synthesis
    PLAN = "plan"  # Planning
    EVALUATE = "evaluate"  # Evaluation


class RAEReasoningAttributes:
    """Reasoning-related attributes."""

    # Reasoning step
    STEP_TYPE = "rae.reasoning.step_type"  # ReasoningStepType enum
    STEP_NUMBER = "rae.reasoning.step_number"  # Step number in sequence
    TOTAL_STEPS = "rae.reasoning.total_steps"  # Total steps in reasoning chain

    # Reasoning depth and complexity
    DEPTH = "rae.reasoning.depth"  # Nesting depth of reasoning
    ITERATIONS = "rae.reasoning.iterations"  # Number of iterations
    BRANCHING_FACTOR = "rae.reasoning.branching_factor"  # Number of branches explored

    # Reasoning quality
    CONFIDENCE = "rae.reasoning.confidence"  # Confidence score (0.0-1.0)
    UNCERTAINTY = "rae.reasoning.uncertainty"  # Uncertainty score (0.0-1.0)
    CONSISTENCY_SCORE = "rae.reasoning.consistency_score"  # Internal consistency


# ============================================================================
# LLM Attributes
# ============================================================================


class RAELLMAttributes:
    """LLM-related attributes."""

    # LLM identification
    PROVIDER = "rae.llm.provider"  # openai, anthropic, google, etc.
    MODEL = "rae.llm.model"  # Model name
    MODEL_VERSION = "rae.llm.model_version"  # Model version

    # LLM usage
    PROMPT_TYPE = "rae.llm.prompt_type"  # system, user, assistant, function
    TEMPERATURE = "rae.llm.temperature"  # Temperature parameter
    MAX_TOKENS = "rae.llm.max_tokens"  # Max tokens limit

    # LLM caching
    CACHE_HIT = "rae.llm.cache_hit"  # Boolean
    CACHE_KEY = "rae.llm.cache_key"  # Cache key (hashed)


# ============================================================================
# Cost Attributes
# ============================================================================


class RAECostAttributes:
    """Cost-related attributes."""

    # Token usage
    TOKENS_INPUT = "rae.cost.tokens_input"  # Input tokens
    TOKENS_OUTPUT = "rae.cost.tokens_output"  # Output tokens
    TOKENS_TOTAL = "rae.cost.tokens_total"  # Total tokens
    TOKENS_CACHED = "rae.cost.tokens_cached"  # Cached tokens saved

    # Cost calculation
    COST_USD = "rae.cost.usd"  # Cost in USD
    COST_PER_TOKEN = "rae.cost.per_token_usd"  # Cost per token
    SAVINGS_USD = "rae.cost.savings_usd"  # Savings from caching

    # Budget tracking
    BUDGET_ID = "rae.cost.budget_id"  # Budget identifier
    BUDGET_REMAINING = "rae.cost.budget_remaining_usd"  # Remaining budget


# ============================================================================
# Safety Attributes
# ============================================================================


class SafetyInterventionType(str, Enum):
    """Type of safety intervention."""

    CONTENT_FILTER = "content_filter"
    TOXICITY_FILTER = "toxicity_filter"
    PII_SCRUBBER = "pii_scrubber"
    BIAS_DETECTOR = "bias_detector"
    HALLUCINATION_DETECTOR = "hallucination_detector"
    RATE_LIMITER = "rate_limiter"
    CIRCUIT_BREAKER = "circuit_breaker"


class RAESafetyAttributes:
    """Safety and guardrail attributes."""

    # Intervention
    INTERVENTION_TYPE = "rae.safety.intervention"  # SafetyInterventionType enum
    INTERVENTION_TRIGGERED = "rae.safety.intervention_triggered"  # Boolean
    INTERVENTION_REASON = "rae.safety.intervention_reason"  # Reason text

    # Content safety
    TOXICITY_SCORE = "rae.safety.toxicity_score"  # Toxicity score (0.0-1.0)
    PII_DETECTED = "rae.safety.pii_detected"  # Boolean
    PII_TYPES = "rae.safety.pii_types"  # List of PII types found

    # Policy compliance
    POLICY_ID = "rae.safety.policy_id"  # Policy identifier
    POLICY_VERSION = "rae.safety.policy_version"  # Policy version
    COMPLIANCE_STATUS = "rae.safety.compliance_status"  # pass, fail, unknown


# ============================================================================
# Outcome Attributes
# ============================================================================


class OutcomeLabel(str, Enum):
    """Outcome label for task/operation."""

    SUCCESS = "success"
    FAIL = "fail"
    UNCERTAIN = "uncertain"
    NEEDS_HUMAN = "needs_human"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RAEOutcomeAttributes:
    """Outcome-related attributes."""

    # Outcome
    LABEL = "rae.outcome.label"  # OutcomeLabel enum
    SUCCESS_RATE = "rae.outcome.success_rate"  # Success rate (0.0-1.0)
    ERROR_TYPE = "rae.outcome.error_type"  # Error type if failed

    # Quality metrics
    ACCURACY = "rae.outcome.accuracy"  # Accuracy score (0.0-1.0)
    PRECISION = "rae.outcome.precision"  # Precision score (0.0-1.0)
    RECALL = "rae.outcome.recall"  # Recall score (0.0-1.0)
    F1_SCORE = "rae.outcome.f1_score"  # F1 score (0.0-1.0)

    # Evaluation
    EVALUATOR_SCORE = "rae.outcome.evaluator_score"  # Automatic evaluation score
    HUMAN_RATING = "rae.outcome.human_rating"  # Human rating if available


# ============================================================================
# Correlation Identifiers
# ============================================================================


class RAECorrelationAttributes:
    """Correlation identifiers for tracing relationships."""

    # Session tracking
    SESSION_ID = "rae.session.id"  # User/agent session ID
    SESSION_START_TIME = "rae.session.start_time"  # Session start timestamp
    SESSION_DURATION_MS = "rae.session.duration_ms"  # Session duration

    # Task tracking
    TASK_ID = "rae.task.id"  # Top-level task ID
    TASK_NAME = "rae.task.name"  # Task name/description
    TASK_TYPE = "rae.task.type"  # Task type category

    # Subtask tracking
    SUBTASK_ID = "rae.subtask.id"  # Subtask ID
    SUBTASK_NAME = "rae.subtask.name"  # Subtask name
    SUBTASK_PARENT_ID = "rae.subtask.parent_id"  # Parent subtask ID

    # Request tracking
    REQUEST_ID = "rae.request.id"  # HTTP request ID
    USER_ID = "rae.user.id"  # User identifier (anonymized if needed)
    TENANT_ID = "rae.tenant.id"  # Multi-tenant identifier


# ============================================================================
# Experiment Attributes
# ============================================================================


class RAEExperimentAttributes:
    """Experiment and A/B testing attributes."""

    # Experiment identification
    ID = "rae.experiment.id"  # Experiment ID
    NAME = "rae.experiment.name"  # Experiment name
    VARIANT = "rae.experiment.variant"  # Variant name (A, B, control, etc.)

    # Experiment configuration
    HYPOTHESIS = "rae.experiment.hypothesis"  # Experiment hypothesis
    START_TIME = "rae.experiment.start_time"  # Experiment start
    END_TIME = "rae.experiment.end_time"  # Experiment end

    # Experiment parameters
    PARAMETER_NAME = "rae.experiment.parameter"  # Parameter being tested
    PARAMETER_VALUE = "rae.experiment.parameter_value"  # Parameter value

    # Experiment results
    METRIC_NAME = "rae.experiment.metric"  # Metric being measured
    METRIC_VALUE = "rae.experiment.metric_value"  # Metric value
    STATISTICAL_SIGNIFICANCE = "rae.experiment.p_value"  # P-value


# ============================================================================
# Performance Attributes
# ============================================================================


class RAEPerformanceAttributes:
    """Performance-related attributes."""

    # Timing
    LATENCY_MS = "rae.performance.latency_ms"  # Operation latency
    QUEUE_TIME_MS = "rae.performance.queue_time_ms"  # Time in queue
    PROCESSING_TIME_MS = "rae.performance.processing_time_ms"  # Processing time

    # Throughput
    OPERATIONS_PER_SECOND = "rae.performance.ops_per_second"  # Throughput
    BATCH_SIZE = "rae.performance.batch_size"  # Batch size

    # Resource usage
    MEMORY_USAGE_MB = "rae.performance.memory_mb"  # Memory usage
    CPU_USAGE_PERCENT = "rae.performance.cpu_percent"  # CPU usage


# ============================================================================
# Data Quality Attributes
# ============================================================================


class RAEDataQualityAttributes:
    """Data quality metrics."""

    # Completeness
    COMPLETENESS_SCORE = "rae.data.completeness"  # Completeness (0.0-1.0)
    MISSING_FIELDS = "rae.data.missing_fields"  # Number of missing fields

    # Validity
    VALIDATION_STATUS = "rae.data.validation_status"  # valid, invalid, unknown
    VALIDATION_ERRORS = "rae.data.validation_errors"  # Number of errors

    # Freshness
    DATA_AGE_SECONDS = "rae.data.age_seconds"  # Data age
    LAST_UPDATED = "rae.data.last_updated"  # Last update timestamp


# ============================================================================
# Human-in-the-Loop Attributes
# ============================================================================


class RAEHumanAttributes:
    """Human-in-the-loop attributes."""

    # Approval workflow
    APPROVAL_REQUIRED = "rae.human.approval_required"  # Boolean
    APPROVAL_STATUS = "rae.human.approval_status"  # pending, approved, rejected
    APPROVER_ID = "rae.human.approver_id"  # Approver identifier

    # Human feedback
    FEEDBACK_PROVIDED = "rae.human.feedback_provided"  # Boolean
    FEEDBACK_RATING = "rae.human.feedback_rating"  # Rating (1-5)
    FEEDBACK_TEXT = "rae.human.feedback_text"  # Feedback text (may be scrubbed)

    # Interaction timing
    HUMAN_WAIT_TIME_MS = "rae.human.wait_time_ms"  # Time waiting for human
    HUMAN_RESPONSE_TIME_MS = "rae.human.response_time_ms"  # Human response time


# ============================================================================
# Helper Functions
# ============================================================================


def get_schema_version() -> str:
    """Get the current schema version."""
    return SCHEMA_VERSION


def get_all_attribute_names() -> dict[str, list[str]]:
    """Get all attribute names organized by category."""
    return {
        "agent": [
            v for k, v in RAEAgentAttributes.__dict__.items() if not k.startswith("_")
        ],
        "memory": [
            v for k, v in RAEMemoryAttributes.__dict__.items() if not k.startswith("_")
        ],
        "reasoning": [
            v
            for k, v in RAEReasoningAttributes.__dict__.items()
            if not k.startswith("_")
        ],
        "llm": [
            v for k, v in RAELLMAttributes.__dict__.items() if not k.startswith("_")
        ],
        "cost": [
            v for k, v in RAECostAttributes.__dict__.items() if not k.startswith("_")
        ],
        "safety": [
            v for k, v in RAESafetyAttributes.__dict__.items() if not k.startswith("_")
        ],
        "outcome": [
            v for k, v in RAEOutcomeAttributes.__dict__.items() if not k.startswith("_")
        ],
        "correlation": [
            v
            for k, v in RAECorrelationAttributes.__dict__.items()
            if not k.startswith("_")
        ],
        "experiment": [
            v
            for k, v in RAEExperimentAttributes.__dict__.items()
            if not k.startswith("_")
        ],
        "performance": [
            v
            for k, v in RAEPerformanceAttributes.__dict__.items()
            if not k.startswith("_")
        ],
        "data_quality": [
            v
            for k, v in RAEDataQualityAttributes.__dict__.items()
            if not k.startswith("_")
        ],
        "human": [
            v for k, v in RAEHumanAttributes.__dict__.items() if not k.startswith("_")
        ],
    }


def validate_attribute_name(name: str) -> bool:
    """Validate if attribute name follows RAE schema conventions."""
    return name.startswith("rae.") and len(name.split(".")) >= 3


# ============================================================================
# Schema Documentation
# ============================================================================

SCHEMA_DOCUMENTATION = """
RAE Telemetry Schema v1.0
=========================

This schema defines standardized attribute names for RAE observability.

Naming Conventions:
------------------
- All attributes start with 'rae.'
- Format: rae.<category>.<attribute_name>
- Use snake_case for attribute names
- Use lowercase for all names

Categories:
----------
- agent: Agent identification and behavior
- memory: Memory layer operations
- reasoning: Reasoning process tracking
- llm: LLM usage and configuration
- cost: Token usage and cost tracking
- safety: Safety interventions and compliance
- outcome: Task outcomes and quality metrics
- correlation: Session, task, and request tracking
- experiment: A/B testing and experimentation
- performance: Performance and resource metrics
- data_quality: Data quality measurements
- human: Human-in-the-loop interactions

Usage:
------
```python
from apps.memory_api.observability.rae_telemetry_schema import (
    RAEAgentAttributes,
    RAEMemoryAttributes,
    AgentRole,
    MemoryLayer,
)

# Add attributes to span
span.set_attribute(RAEAgentAttributes.ROLE, AgentRole.PLANNER.value)
span.set_attribute(RAEMemoryAttributes.LAYER, MemoryLayer.EPISODIC.value)
span.set_attribute(RAEMemoryAttributes.ACCESS_COUNT, 5)
```

Versioning:
----------
Schema version follows MAJOR.MINOR format:
- MAJOR: Breaking changes to attribute semantics
- MINOR: Additive changes (new attributes)

Current version: 1.0
"""
