from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from apps.memory_api.models.reflection_v2_models import (
    ErrorCategory,
    ErrorInfo,
    Event,
    EventType,
    OutcomeType,
    ReflectionContext,
    ReflectionResult,
)
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.reflection_engine_v2 import (
    LLMReflectionResponse,
    ReflectionEngineV2,
)


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def mock_rae_service():
    service = MagicMock(spec=RAECoreService)
    service.store_memory = AsyncMock(return_value=str(uuid4()))
    service.list_memories = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_llm_provider():
    provider = AsyncMock()
    provider.generate_structured = AsyncMock()
    return provider


@pytest.fixture
def engine(mock_rae_service, mock_llm_provider):
    engine = ReflectionEngineV2(rae_service=mock_rae_service)
    engine.llm_provider = mock_llm_provider
    return engine


@pytest.fixture
def sample_context():
    return ReflectionContext(
        tenant_id="test_tenant",
        project_id="test_project",
        outcome=OutcomeType.SUCCESS,
        events=[
            Event(
                event_id="evt1",
                event_type=EventType.TOOL_CALL,
                timestamp=datetime.now(timezone.utc),
                content="Calling tool search",
                metadata={},
                tool_name="search",
            )
        ],
        task_goal="Find information",
        task_description="Search for X",
    )


@pytest.mark.asyncio
async def test_generate_reflection_success(engine, sample_context, mock_llm_provider):
    """Test generating reflection for success outcome"""
    # Setup LLM response
    mock_response = LLMReflectionResponse(
        reflection="Success reflection",
        strategy="Use this pattern",
        importance=0.8,
        confidence=0.9,
        tags=["search", "pattern"],
    )
    mock_llm_provider.generate_structured.return_value = mock_response

    result = await engine.generate_reflection(sample_context)

    assert result.reflection_text == "Success reflection"
    assert result.strategy_text == "Use this pattern"
    assert result.importance == 0.8
    assert result.confidence == 0.9
    assert result.tags == ["search", "pattern"]

    # Verify LLM call
    mock_llm_provider.generate_structured.assert_called_once()
    call_args = mock_llm_provider.generate_structured.call_args
    assert "success" in call_args[1]["system"].lower()


@pytest.mark.asyncio
async def test_generate_reflection_failure(engine, sample_context, mock_llm_provider):
    """Test generating reflection for failure outcome"""
    sample_context.outcome = OutcomeType.FAILURE
    sample_context.error = ErrorInfo(
        error_category=ErrorCategory.TIMEOUT_ERROR, error_message="Task timed out"
    )

    mock_response = LLMReflectionResponse(
        reflection="Failure reflection",
        strategy="Increase timeout",
        importance=0.9,
        confidence=0.8,
        tags=["timeout"],
    )
    mock_llm_provider.generate_structured.return_value = mock_response

    result = await engine.generate_reflection(sample_context)

    assert result.reflection_text == "Failure reflection"
    assert result.strategy_text == "Increase timeout"
    assert result.importance == 0.9
    assert result.confidence == 0.8
    assert result.tags == ["timeout"]

    # Verify LLM call
    call_args = mock_llm_provider.generate_structured.call_args
    assert "traces" in call_args[1]["system"].lower()


@pytest.mark.asyncio
async def test_generate_reflection_partial(engine, sample_context, mock_llm_provider):
    """Test generating reflection for partial outcome"""
    sample_context.outcome = OutcomeType.PARTIAL

    mock_response = LLMReflectionResponse(
        reflection="Partial reflection", importance=0.5, confidence=0.5, tags=[]
    )
    mock_llm_provider.generate_structured.return_value = mock_response

    result = await engine.generate_reflection(sample_context)

    assert result.reflection_text == "Partial reflection"
    assert result.strategy_text is None
    assert result.importance == 0.5
    assert result.confidence == 0.5
    assert result.tags == []

    # Should use failure prompt logic for partial
    call_args = mock_llm_provider.generate_structured.call_args
    assert "traces" in call_args[1]["system"].lower()


def test_format_events(engine):
    """Test memory formatting logic for LLM input"""
    events = [
        Event(
            event_id="1",
            event_type=EventType.TOOL_CALL,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            content="Call tool",
            metadata={},
            tool_name="tool1",
        ),
        Event(
            event_id="2",
            event_type=EventType.ERROR_EVENT,
            timestamp=datetime(2024, 1, 1, 12, 0, 1),
            content="Error occurred",
            metadata={},
            error={"msg": "bad"},
        ),
    ]

    formatted = engine._format_events(events)
    # Check for presence of formatted strings. Exact format might vary but key info must be there.
    assert "Call tool" in formatted
    assert "Tool: tool1" in formatted
    assert "Error occurred" in formatted
    assert "Error: {'msg': 'bad'}" in formatted


@pytest.mark.asyncio
async def test_store_reflection(engine, mock_rae_service):
    """Test storing reflection to repository"""
    result = ReflectionResult(
        reflection_text="Reflection",
        strategy_text="Strategy",
        importance=0.8,
        confidence=0.9,
        tags=["tag1"],
        generated_at=datetime.now(timezone.utc),
    )

    ids = await engine.store_reflection(result, "tenant1", "proj1")

    assert "reflection_id" in ids
    assert "strategy_id" in ids

    # Should call store_memory twice (reflection + strategy)
    assert mock_rae_service.store_memory.call_count == 2


@pytest.mark.asyncio
async def test_store_reflection_no_strategy(engine, mock_rae_service):
    """Test storing reflection without strategy"""
    result = ReflectionResult(
        reflection_text="Reflection",
        strategy_text=None,  # No strategy
        importance=0.8,
        confidence=0.9,
        tags=["tag1"],
    )

    ids = await engine.store_reflection(result, "tenant1", "proj1")

    assert "reflection_id" in ids
    assert "strategy_id" not in ids

    assert mock_rae_service.store_memory.call_count == 1


@pytest.mark.asyncio
async def test_query_reflections(engine, mock_rae_service):
    """Test querying reflections"""
    mock_rae_service.list_memories.return_value = [
        {"id": "1", "importance": 0.9},
        {"id": "2", "importance": 0.4},  # Low importance
        {"id": "3", "importance": 0.8},
    ]

    # Query with min_importance 0.5
    results = await engine.query_reflections("t1", "p1", min_importance=0.5)

    assert len(results) == 2
    assert results[0]["id"] == "1"
    assert results[1]["id"] == "3"

    mock_rae_service.list_memories.assert_called_once_with(
        tenant_id="t1", layer="reflective", project="p1", limit=100
    )


@pytest.mark.asyncio
async def test_error_handling(engine, sample_context, mock_llm_provider):
    """Test error handling in generate_reflection"""
    mock_llm_provider.generate_structured.side_effect = Exception("LLM Error")

    with pytest.raises(Exception, match="LLM Error"):
        await engine.generate_reflection(sample_context)
