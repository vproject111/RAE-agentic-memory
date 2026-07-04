from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from apps.memory_api.services.context_builder import (
    ContextBuilder,
    ContextConfig,
    WorkingMemoryContext,
)

# --- Context Builder Tests ---


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def mock_rae_service():
    return AsyncMock()


@pytest.fixture
def mock_reflection_engine():
    return AsyncMock()


@pytest.fixture
def context_builder(mock_rae_service, mock_reflection_engine):
    return ContextBuilder(
        rae_service=mock_rae_service,
        reflection_engine=mock_reflection_engine,
        config=ContextConfig(),
    )


@pytest.mark.asyncio
async def test_build_context_basic(
    context_builder, mock_rae_service, mock_reflection_engine
):
    """Test basic context building flow"""
    # Add required fields for scoring
    # Mock return values for list_memories (called twice: once for episodic, once for semantic)
    mock_rae_service.list_memories.side_effect = [
        [
            {
                "id": "e1",
                "content": "E1",
                "layer": "em",
                "created_at": datetime.now(timezone.utc),
                "importance": 0.5,
                "last_accessed_at": None,
                "usage_count": 0,
            }
        ],
        [
            {
                "id": "s1",
                "content": "S1",
                "layer": "sm",
                "created_at": datetime.now(timezone.utc),
                "importance": 0.5,
                "last_accessed_at": None,
                "usage_count": 0,
            }
        ],
    ]

    mock_reflection_engine.query_reflections.return_value = [
        {
            "id": "r1",
            "content": "R1",
            "tags": ["learn"],
            "importance": 0.8,
            "created_at": datetime.now(timezone.utc),
        }
    ]

    context = await context_builder.build_context(
        tenant_id="t1",
        project_id="p1",
        query="test query",
        recent_messages=[{"role": "user", "content": "hello"}],
    )

    assert isinstance(context, WorkingMemoryContext)
    assert len(context.messages) == 1
    assert len(context.ltm_items) > 0
    assert len(context.reflections) == 1
    assert (
        "Lessons Learned" in context.system_prompt
        or "Lessons Learned" in context.context_text
    )
    assert "Relevant Context" in context.context_text


@pytest.mark.asyncio
async def test_build_context_no_reflections(context_builder, mock_reflection_engine):
    """Test building context when reflections are disabled or empty"""
    context_builder.config.enable_enhanced_scoring = (
        False  # Coverage for basic scoring branch
    )
    mock_reflection_engine.query_reflections.return_value = []

    context = await context_builder.build_context(
        tenant_id="t1",
        project_id="p1",
        query="test",
    )

    assert len(context.reflections) == 0


@pytest.mark.asyncio
async def test_format_messages(context_builder):
    """Test message formatting"""
    msgs = [{"role": "user", "content": "hi"}] * 15  # 15 messages
    components = context_builder._format_messages(msgs)

    assert len(components) == 10  # Should truncate to last 10
    assert components[0].type == "message"


@pytest.mark.asyncio
async def test_inject_reflections_into_prompt(context_builder, mock_reflection_engine):
    """Test prompt injection helper"""
    mock_reflection_engine.query_reflections.return_value = [{"content": "Insight 1"}]

    prompt = await context_builder.inject_reflections_into_prompt(
        "Base prompt", "t1", "p1", "query"
    )

    assert "Base prompt" in prompt
    assert "Insight 1" in prompt
    assert "Lessons Learned" in prompt


@pytest.mark.asyncio
async def test_retrieve_ltm_empty(context_builder, mock_rae_service):
    mock_rae_service.list_memories.return_value = []

    items = await context_builder._retrieve_ltm("t1", "p1", "q")
    assert items == []


@pytest.mark.asyncio
async def test_working_memory_context_serialization():
    """Test serialization"""
    ctx = WorkingMemoryContext(
        messages=[],
        ltm_items=[],
        reflections=[],
        profile_items=[],
        system_prompt="sys",
        context_text="ctx",
        total_tokens=100,
        retrieval_stats={},
    )
    data = ctx.to_dict()
    assert data["total_tokens"] == 100
