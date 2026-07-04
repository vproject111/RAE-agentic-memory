from unittest.mock import MagicMock, patch

import pytest

from apps.memory_api.observability.rae_tracing import (
    AgentRole,
    MemoryLayer,
    RAETracingContext,
    ReasoningStepType,
    SafetyInterventionType,
    start_llm_call,
    start_memory_operation,
    start_reasoning_step,
    start_safety_check,
    trace_agent_operation,
)


# Mock get_tracer to return a mock tracer that yields a mock span
@pytest.fixture
def mock_tracer():
    mock_span = MagicMock()
    # context manager protocol
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)

    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value = mock_span

    return mock_tracer, mock_span


@pytest.fixture
def patch_opentelemetry(mock_tracer):
    tracer, span = mock_tracer
    with (
        patch(
            "apps.memory_api.observability.rae_tracing.OPENTELEMETRY_AVAILABLE", True
        ),
        patch(
            "apps.memory_api.observability.rae_tracing.get_tracer", return_value=tracer
        ),
    ):
        yield tracer, span


def test_rae_tracing_context():
    """Test context management for correlation IDs."""
    with RAETracingContext.session("sess-1"):
        attrs = RAETracingContext.get_context_attributes()
        assert attrs["rae.session.id"] == "sess-1"

        with RAETracingContext.task("task-1"):
            attrs = RAETracingContext.get_context_attributes()
            assert attrs["rae.session.id"] == "sess-1"
            assert attrs["rae.task.id"] == "task-1"

            with RAETracingContext.subtask("sub-1"):
                attrs = RAETracingContext.get_context_attributes()
                assert attrs["rae.subtask.id"] == "sub-1"

    # Context should be cleared/reset (though implementation uses class state,
    # verify it reverts to None/previous state logic if applicable,
    # but here we just check basic nesting)


def test_start_reasoning_step(patch_opentelemetry):
    _, span = patch_opentelemetry

    with start_reasoning_step(ReasoningStepType.DECOMPOSE, step_number=1) as s:
        assert s == span

    # Verify span attributes were set
    span.set_attribute.assert_any_call("rae.reasoning.step_type", "decompose")
    span.set_attribute.assert_any_call("rae.reasoning.step_number", 1)


def test_start_memory_operation(patch_opentelemetry):
    _, span = patch_opentelemetry

    with start_memory_operation(MemoryLayer.EPISODIC, "search") as s:
        assert s == span

    span.set_attribute.assert_any_call("rae.memory.layer", "episodic")
    span.set_attribute.assert_any_call("rae.memory.operation", "search")


def test_start_llm_call(patch_opentelemetry):
    _, span = patch_opentelemetry

    with start_llm_call("openai", "gpt-4") as s:
        assert s == span

    span.set_attribute.assert_any_call("rae.llm.provider", "openai")
    span.set_attribute.assert_any_call("rae.llm.model", "gpt-4")


def test_start_safety_check(patch_opentelemetry):
    _, span = patch_opentelemetry

    with start_safety_check(SafetyInterventionType.PII_SCRUBBER) as s:
        assert s == span

    span.set_attribute.assert_any_call("rae.safety.intervention", "pii_scrubber")


@pytest.mark.asyncio
async def test_trace_agent_operation_decorator_async(patch_opentelemetry):
    _, span = patch_opentelemetry

    @trace_agent_operation(AgentRole.PLANNER, "plan")
    async def plan_task():
        return "plan"

    result = await plan_task()
    assert result == "plan"

    span.set_attribute.assert_any_call("rae.agent.role", "planner")
    # Check success status set (outcome label)
    span.set_attribute.assert_any_call("rae.outcome.label", "success")


def test_trace_agent_operation_decorator_sync(patch_opentelemetry):
    _, span = patch_opentelemetry

    @trace_agent_operation(AgentRole.WORKER, "run")
    def run_task():
        return "done"

    result = run_task()
    assert result == "done"

    span.set_attribute.assert_any_call("rae.agent.role", "worker")


@pytest.mark.asyncio
async def test_trace_agent_operation_error(patch_opentelemetry):
    _, span = patch_opentelemetry

    @trace_agent_operation(AgentRole.PLANNER, "plan")
    async def fail_task():
        raise ValueError("failure")

    with pytest.raises(ValueError):
        await fail_task()

    span.set_attribute.assert_any_call("error", True)
    span.record_exception.assert_called()
