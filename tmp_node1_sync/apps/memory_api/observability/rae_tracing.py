"""
RAE Tracing Helpers

Convenient wrappers for creating traces using RAE Telemetry Schema v1.
These helpers abstract away the complexity of span creation and attribute
management, providing a clean interface for instrumenting RAE components.

Design principles:
- Thin, consistent instrumentation
- No mixing of business logic with tracing
- Support for correlation IDs and experiment tracking
- Profile-aware (research/prod/gov)
"""

import functools
import inspect
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, Dict, Optional

import structlog

from .opentelemetry_config import OPENTELEMETRY_AVAILABLE, get_tracer
from .rae_telemetry_schema import (
    AgentRole,
    MemoryLayer,
    OutcomeLabel,
    RAEAgentAttributes,
    RAECorrelationAttributes,
    RAECostAttributes,
    RAEExperimentAttributes,
    RAEHumanAttributes,
    RAELLMAttributes,
    RAEMemoryAttributes,
    RAEOutcomeAttributes,
    RAEPerformanceAttributes,
    RAEReasoningAttributes,
    RAESafetyAttributes,
    ReasoningStepType,
    SafetyInterventionType,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Tracing Context
# ============================================================================


class RAETracingContext:
    """
    Context manager for tracking RAE operations across services.

    Supports:
    - Session tracking
    - Task/Subtask relationships
    - Experiment variant tracking
    - User/Tenant context propagation
    """

    _session_id: Optional[str] = None
    _task_id: Optional[str] = None
    _task_name: Optional[str] = None
    _subtask_id: Optional[str] = None
    _experiment_id: Optional[str] = None
    _experiment_variant: Optional[str] = None
    _user_id: Optional[str] = None
    _tenant_id: Optional[str] = None

    @classmethod
    @contextmanager
    def session(cls, session_id: Optional[str] = None):
        """Create a session context."""
        old_session = cls._session_id
        cls._session_id = session_id or str(uuid.uuid4())
        try:
            yield cls._session_id
        finally:
            cls._session_id = old_session

    @classmethod
    @contextmanager
    def task(cls, task_id: Optional[str] = None, task_name: Optional[str] = None):
        """Create a task context."""
        old_task = cls._task_id
        cls._task_id = task_id or str(uuid.uuid4())

        # Store task name as well if using custom tracer
        if task_name:
            cls._task_name = task_name

        try:
            yield cls._task_id
        finally:
            cls._task_id = old_task

    @classmethod
    @contextmanager
    def subtask(cls, subtask_id: Optional[str] = None, parent_id: Optional[str] = None):
        """Create a subtask context."""
        old_subtask = cls._subtask_id
        cls._subtask_id = subtask_id or str(uuid.uuid4())
        try:
            yield cls._subtask_id
        finally:
            cls._subtask_id = old_subtask

    @classmethod
    @contextmanager
    def experiment(cls, experiment_id: str, variant: str):
        """Create an experiment context."""
        old_exp_id = cls._experiment_id
        old_variant = cls._experiment_variant
        cls._experiment_id = experiment_id
        cls._experiment_variant = variant
        try:
            yield (experiment_id, variant)
        finally:
            cls._experiment_id = old_exp_id
            cls._experiment_variant = old_variant

    @classmethod
    def set_user(cls, user_id: str):
        """Set user ID for current context."""
        cls._user_id = user_id

    @classmethod
    def set_tenant(cls, tenant_id: str):
        """Set tenant ID for current context."""
        cls._tenant_id = tenant_id

    @classmethod
    def get_context_attributes(cls) -> Dict[str, Any]:
        """Get all context attributes."""
        attrs = {}
        if cls._session_id:
            attrs[RAECorrelationAttributes.SESSION_ID] = cls._session_id
        if cls._task_id:
            attrs[RAECorrelationAttributes.TASK_ID] = cls._task_id
        if cls._subtask_id:
            attrs[RAECorrelationAttributes.SUBTASK_ID] = cls._subtask_id
        if cls._experiment_id:
            attrs[RAEExperimentAttributes.ID] = cls._experiment_id
        if cls._experiment_variant:
            attrs[RAEExperimentAttributes.VARIANT] = cls._experiment_variant
        if cls._user_id:
            attrs[RAECorrelationAttributes.USER_ID] = cls._user_id
        if cls._tenant_id:
            attrs[RAECorrelationAttributes.TENANT_ID] = cls._tenant_id
        return attrs


# ============================================================================
# Reasoning Step Tracer
# ============================================================================


@contextmanager
def start_reasoning_step(
    step_type: ReasoningStepType,
    step_number: Optional[int] = None,
    agent_role: Optional[AgentRole] = None,
    **kwargs,
):
    """
    Start a reasoning step span.

    Args:
        step_type: Type of reasoning step
        step_number: Step number in sequence
        agent_role: Agent role performing the step
        **kwargs: Additional attributes

    Usage:
        with start_reasoning_step(
            ReasoningStepType.DECOMPOSE,
            step_number=1,
            agent_role=AgentRole.PLANNER
        ) as span:
            result = decompose_task(task)
            set_reasoning_confidence(span, 0.85)
    """
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return

    tracer = get_tracer("rae.reasoning")
    if not tracer:
        yield None
        return

    span_name = f"reasoning.{step_type.value}"
    start_time = time.time()

    with tracer.start_as_current_span(span_name) as span:
        # Set base attributes
        span.set_attribute(RAEReasoningAttributes.STEP_TYPE, step_type.value)

        if step_number is not None:
            span.set_attribute(RAEReasoningAttributes.STEP_NUMBER, step_number)

        if agent_role:
            span.set_attribute(RAEAgentAttributes.ROLE, agent_role.value)

        # Add context attributes
        for key, value in RAETracingContext.get_context_attributes().items():
            span.set_attribute(key, value)

        # Add custom attributes
        for key, value in kwargs.items():
            span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            span.set_attribute(
                RAEPerformanceAttributes.LATENCY_MS, round(latency_ms, 2)
            )


# ============================================================================
# Memory Operation Tracer
# ============================================================================


@contextmanager
def start_memory_operation(
    layer: MemoryLayer,
    operation: str,
    **kwargs,
):
    """
    Start a memory operation span.

    Args:
        layer: Memory layer
        operation: Operation type (create, read, update, delete, search)
        **kwargs: Additional attributes

    Usage:
        with start_memory_operation(
            MemoryLayer.EPISODIC,
            "search",
            vector_count=10
        ) as span:
            results = search_episodic_memory(query)
            span.set_attribute(RAEMemoryAttributes.HIT_RATE, 0.7)
    """
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return

    tracer = get_tracer("rae.memory")
    if not tracer:
        yield None
        return

    span_name = f"memory.{layer.value}.{operation}"
    start_time = time.time()

    with tracer.start_as_current_span(span_name) as span:
        # Set base attributes
        span.set_attribute(RAEMemoryAttributes.LAYER, layer.value)
        span.set_attribute(RAEMemoryAttributes.OPERATION, operation)

        # Add context attributes
        for key, value in RAETracingContext.get_context_attributes().items():
            span.set_attribute(key, value)

        # Add custom attributes
        for key, value in kwargs.items():
            span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            span.set_attribute(
                RAEPerformanceAttributes.LATENCY_MS, round(latency_ms, 2)
            )


# ============================================================================
# LLM Call Tracer
# ============================================================================


@contextmanager
def start_llm_call(
    provider: str,
    model: str,
    prompt_type: str = "user",
    **kwargs,
):
    """
    Start an LLM call span.

    Args:
        provider: LLM provider (openai, anthropic, etc.)
        model: Model name
        prompt_type: Prompt type
        **kwargs: Additional attributes

    Usage:
        with start_llm_call("openai", "gpt-4o-mini") as span:
            response = llm.generate(prompt)
            set_llm_tokens(span, input_tokens=100, output_tokens=50)
            set_llm_cost(span, 0.001)
    """
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return

    tracer = get_tracer("rae.llm")
    if not tracer:
        yield None
        return

    span_name = f"llm.{provider}.{model}"
    start_time = time.time()

    with tracer.start_as_current_span(span_name) as span:
        # Set base attributes
        span.set_attribute(RAELLMAttributes.PROVIDER, provider)
        span.set_attribute(RAELLMAttributes.MODEL, model)
        span.set_attribute(RAELLMAttributes.PROMPT_TYPE, prompt_type)

        # Add context attributes
        for key, value in RAETracingContext.get_context_attributes().items():
            span.set_attribute(key, value)

        # Add custom attributes
        for key, value in kwargs.items():
            span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            span.set_attribute(
                RAEPerformanceAttributes.LATENCY_MS, round(latency_ms, 2)
            )


# ============================================================================
# Safety Intervention Tracer
# ============================================================================


@contextmanager
def start_safety_check(
    intervention_type: SafetyInterventionType,
    **kwargs,
):
    """
    Start a safety check span.

    Args:
        intervention_type: Type of safety intervention
        **kwargs: Additional attributes

    Usage:
        with start_safety_check(SafetyInterventionType.PII_SCRUBBER) as span:
            scrubbed_text, pii_found = scrub_pii(text)
            span.set_attribute(RAESafetyAttributes.PII_DETECTED, pii_found)
    """
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return

    tracer = get_tracer("rae.safety")
    if not tracer:
        yield None
        return

    span_name = f"safety.{intervention_type.value}"
    start_time = time.time()

    with tracer.start_as_current_span(span_name) as span:
        # Set base attributes
        span.set_attribute(
            RAESafetyAttributes.INTERVENTION_TYPE, intervention_type.value
        )

        # Add context attributes
        for key, value in RAETracingContext.get_context_attributes().items():
            span.set_attribute(key, value)

        # Add custom attributes
        for key, value in kwargs.items():
            span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            span.set_attribute(
                RAEPerformanceAttributes.LATENCY_MS, round(latency_ms, 2)
            )


# ============================================================================
# Span Attribute Setters
# ============================================================================


def set_reasoning_confidence(span, confidence: float):
    """Set reasoning confidence score."""
    if span:
        span.set_attribute(RAEReasoningAttributes.CONFIDENCE, confidence)


def set_reasoning_depth(span, depth: int):
    """Set reasoning depth."""
    if span:
        span.set_attribute(RAEReasoningAttributes.DEPTH, depth)


def set_llm_tokens(span, input_tokens: int, output_tokens: int):
    """Set LLM token usage."""
    if span:
        span.set_attribute(RAECostAttributes.TOKENS_INPUT, input_tokens)
        span.set_attribute(RAECostAttributes.TOKENS_OUTPUT, output_tokens)
        span.set_attribute(RAECostAttributes.TOKENS_TOTAL, input_tokens + output_tokens)


def set_llm_cost(span, cost_usd: float):
    """Set LLM cost."""
    if span:
        span.set_attribute(RAECostAttributes.COST_USD, cost_usd)


def set_outcome(span, label: OutcomeLabel, **metrics):
    """
    Set outcome label and optional quality metrics.

    Args:
        span: Current span
        label: Outcome label
        **metrics: Quality metrics (accuracy, precision, recall, f1_score)
    """
    if not span:
        return

    span.set_attribute(RAEOutcomeAttributes.LABEL, label.value)

    for metric_name, metric_value in metrics.items():
        attr_name = f"rae.outcome.{metric_name}"
        span.set_attribute(attr_name, metric_value)


def set_human_approval(span, required: bool, status: Optional[str] = None):
    """Set human approval information."""
    if span:
        span.set_attribute(RAEHumanAttributes.APPROVAL_REQUIRED, required)
        if status:
            span.set_attribute(RAEHumanAttributes.APPROVAL_STATUS, status)


# ============================================================================
# Decorator for Auto-Tracing
# ============================================================================


def trace_agent_operation(
    agent_role: AgentRole,
    operation_type: str = "execute",
):
    """
    Decorator to automatically trace agent operations.

    Args:
        agent_role: Agent role
        operation_type: Type of operation

    Usage:
        @trace_agent_operation(AgentRole.PLANNER, "plan")
        async def plan_task(task: Task) -> Plan:
            # Implementation
            return plan
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer("rae.agent") if OPENTELEMETRY_AVAILABLE else None
            if not tracer:
                return await func(*args, **kwargs)

            span_name = f"agent.{agent_role.value}.{operation_type}"
            start_time = time.time()

            with tracer.start_as_current_span(span_name) as span:
                # Set agent attributes
                span.set_attribute(RAEAgentAttributes.ROLE, agent_role.value)

                # Add context attributes
                for key, value in RAETracingContext.get_context_attributes().items():
                    span.set_attribute(key, value)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute(
                        RAEOutcomeAttributes.LABEL, OutcomeLabel.SUCCESS.value
                    )
                    return result
                except Exception as e:
                    span.set_attribute("error", True)
                    span.set_attribute(
                        RAEOutcomeAttributes.LABEL, OutcomeLabel.FAIL.value
                    )
                    span.set_attribute(
                        RAEOutcomeAttributes.ERROR_TYPE, type(e).__name__
                    )
                    span.record_exception(e)
                    raise
                finally:
                    latency_ms = (time.time() - start_time) * 1000
                    span.set_attribute(
                        RAEPerformanceAttributes.LATENCY_MS, round(latency_ms, 2)
                    )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer("rae.agent") if OPENTELEMETRY_AVAILABLE else None
            if not tracer:
                return func(*args, **kwargs)

            span_name = f"agent.{agent_role.value}.{operation_type}"
            start_time = time.time()

            with tracer.start_as_current_span(span_name) as span:
                # Set agent attributes
                span.set_attribute(RAEAgentAttributes.ROLE, agent_role.value)

                # Add context attributes
                for key, value in RAETracingContext.get_context_attributes().items():
                    span.set_attribute(key, value)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute(
                        RAEOutcomeAttributes.LABEL, OutcomeLabel.SUCCESS.value
                    )
                    return result
                except Exception as e:
                    span.set_attribute("error", True)
                    span.set_attribute(
                        RAEOutcomeAttributes.LABEL, OutcomeLabel.FAIL.value
                    )
                    span.set_attribute(
                        RAEOutcomeAttributes.ERROR_TYPE, type(e).__name__
                    )
                    span.record_exception(e)
                    raise
                finally:
                    latency_ms = (time.time() - start_time) * 1000
                    span.set_attribute(
                        RAEPerformanceAttributes.LATENCY_MS, round(latency_ms, 2)
                    )

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# Usage Examples
# ============================================================================

"""
# Example 1: Reasoning step with context
with RAETracingContext.session("user-123"):
    with RAETracingContext.task("analyze-doc", task_name="Document Analysis"):
        with start_reasoning_step(
            ReasoningStepType.DECOMPOSE,
            step_number=1,
            agent_role=AgentRole.PLANNER
        ) as span:
            subtasks = decompose_task(task)
            set_reasoning_confidence(span, 0.85)
            set_reasoning_depth(span, 2)

# Example 2: Memory operation
with start_memory_operation(
    MemoryLayer.EPISODIC,
    "search",
    vector_count=10,
    similarity_threshold=0.7
) as span:
    results = search_memory(query)
    span.set_attribute(RAEMemoryAttributes.HIT_RATE, 0.8)

# Example 3: LLM call with cost tracking
with start_llm_call("openai", "gpt-4o-mini") as span:
    response = llm.generate(prompt)
    set_llm_tokens(span, input_tokens=100, output_tokens=50)
    set_llm_cost(span, 0.001)
    set_outcome(span, OutcomeLabel.SUCCESS, accuracy=0.92)

# Example 4: A/B testing
with RAETracingContext.experiment("memory-size-test", variant="large"):
    with start_memory_operation(MemoryLayer.SEMANTIC, "retrieve") as span:
        results = retrieve_semantic_memories(query)

# Example 5: Decorated agent
@trace_agent_operation(AgentRole.EVALUATOR, "evaluate")
async def evaluate_response(response: str) -> float:
    # Evaluation logic
    return evaluation_score
"""
