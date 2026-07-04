import uuid
from unittest.mock import AsyncMock

import pytest

from apps.memory_api.services.evaluator import (
    ExecutionContext,
    LLMEvaluationResponse,
    LLMEvaluator,
    OutcomeType,
)


@pytest.mark.asyncio
async def test_llm_evaluator_evaluate_success():
    """Test LLM evaluator correctly handles a successful evaluation."""
    # Mock LLM provider
    mock_llm_provider = AsyncMock()
    mock_llm_provider.generate_structured.return_value = LLMEvaluationResponse(
        is_success=True,
        quality_score=0.9,
        outcome_type="success",
        reasons=["Task completed successfully", "Good response quality"],
        should_reflect=False,
        importance=0.2,
    )

    # Create evaluator with mock
    evaluator = LLMEvaluator()
    evaluator.llm_provider = mock_llm_provider

    # Create context
    context = ExecutionContext(
        events=[{"type": "tool_call", "name": "search", "args": "query"}],
        response="Here is the answer.",
        execution_time_ms=1000,
        task_goal="Find answer",
        tenant_id=str(uuid.uuid4()),
        project_id="default",
    )

    # Run evaluation
    result = await evaluator.evaluate(context)

    # Verify result
    assert result.outcome == OutcomeType.SUCCESS
    assert result.is_ok is True
    assert result.quality_score == 0.9
    assert result.reasons and "Good response quality" in result.reasons
    assert result.should_reflect is False
    assert result.importance_hint == 0.2
    assert result.evaluation_method == "llm"


@pytest.mark.asyncio
async def test_llm_evaluator_evaluate_failure():
    """Test LLM evaluator correctly handles a failure evaluation."""
    # Mock LLM provider
    mock_llm_provider = AsyncMock()
    mock_llm_provider.generate_structured.return_value = LLMEvaluationResponse(
        is_success=False,
        quality_score=0.2,
        outcome_type="failure",
        reasons=["Incorrect answer", "Hallucination"],
        should_reflect=True,
        importance=0.8,
    )

    # Create evaluator with mock
    evaluator = LLMEvaluator()
    evaluator.llm_provider = mock_llm_provider

    # Create context
    context = ExecutionContext(
        events=[],
        response="Wrong answer.",
        execution_time_ms=1000,
        task_goal="Find answer",
        tenant_id=str(uuid.uuid4()),
        project_id="default",
    )

    # Run evaluation
    result = await evaluator.evaluate(context)

    # Verify result
    assert result.outcome == OutcomeType.FAILURE
    assert result.is_ok is False
    assert result.quality_score == 0.2
    assert result.should_reflect is True
    assert result.importance_hint == 0.8


@pytest.mark.asyncio
async def test_llm_evaluator_fallback():
    """Test LLM evaluator falls back to deterministic on error."""
    # Mock LLM provider to raise error
    mock_llm_provider = AsyncMock()
    mock_llm_provider.generate_structured.side_effect = Exception("LLM Error")

    # Create evaluator with mock
    evaluator = LLMEvaluator()
    evaluator.llm_provider = mock_llm_provider

    # Create context with explicit error to trigger deterministic failure
    from apps.memory_api.models.reflection_v2_models import ErrorCategory, ErrorInfo

    context = ExecutionContext(
        events=[],
        response="",
        execution_time_ms=1000,
        error=ErrorInfo(
            error_category=ErrorCategory.TOOL_ERROR, error_message="Tool failed"
        ),
        tenant_id=str(uuid.uuid4()),
        project_id="default",
    )

    # Run evaluation
    result = await evaluator.evaluate(context)

    # Verify fallback result (should be deterministic error)
    assert result.outcome == OutcomeType.ERROR
    assert result.evaluation_method == "deterministic"
