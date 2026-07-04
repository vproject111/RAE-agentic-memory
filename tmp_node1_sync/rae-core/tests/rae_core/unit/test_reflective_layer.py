from uuid import UUID

import pytest

from rae_core.layers.reflective import ReflectiveLayer
from rae_core.models.memory import MemoryLayer
from rae_core.models.reflection import Reflection, ReflectionPriority, ReflectionType


@pytest.fixture
def reflective_layer(mock_memory_storage):
    return ReflectiveLayer(
        storage=mock_memory_storage,
        tenant_id="test_tenant",
        agent_id="test_agent",
        min_source_memories=2,  # Lower for easier testing
    )


@pytest.mark.asyncio
async def test_add_reflection(reflective_layer):
    """Test adding a reflection."""
    reflection = Reflection(
        content="User has a pattern",
        reflection_type=ReflectionType.PATTERN,
        priority=ReflectionPriority.HIGH,
        source_memory_ids=[
            UUID("00000000-0000-0000-0000-000000000001"),
            UUID("00000000-0000-0000-0000-000000000002"),
        ],
        tenant_id="test_tenant",
        agent_id="test_agent",
        confidence=0.9,
    )

    mem_id = await reflective_layer.add_reflection(reflection)

    memory = await reflective_layer.get_memory(mem_id)
    assert memory.layer == MemoryLayer.REFLECTIVE
    assert memory.metadata["reflection_type"] == "pattern"
    assert memory.importance > 0.8  # High priority -> 0.85 or similar


@pytest.mark.asyncio
async def test_add_reflection_validation(reflective_layer):
    """Test validation of source memories count."""
    reflection = Reflection(
        content="Invalid",
        reflection_type=ReflectionType.INSIGHT,
        source_memory_ids=[UUID("00000000-0000-0000-0000-000000000001")],  # Only 1
        tenant_id="test_tenant",
        agent_id="test_agent",
    )

    with pytest.raises(ValueError, match="Reflection requires at least"):
        await reflective_layer.add_reflection(reflection)


@pytest.mark.asyncio
async def test_get_reflection(reflective_layer):
    """Test retrieving structured reflection."""
    src_ids = [
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000000002"),
    ]
    reflection_in = Reflection(
        content="Deep insight",
        reflection_type=ReflectionType.INSIGHT,
        source_memory_ids=src_ids,
        tenant_id="test_tenant",
        agent_id="test_agent",
        confidence=0.85,
    )

    mem_id = await reflective_layer.add_reflection(reflection_in)

    reflection_out = await reflective_layer.get_reflection(mem_id)
    assert isinstance(reflection_out, Reflection)
    assert reflection_out.content == "Deep insight"
    assert reflection_out.reflection_type == ReflectionType.INSIGHT
    assert reflection_out.confidence == 0.85
    assert reflection_out.source_memory_ids == src_ids


@pytest.mark.asyncio
async def test_search_by_type(reflective_layer):
    """Test searching by reflection type."""
    # Add Insight
    await reflective_layer.add_reflection(
        Reflection(
            content="Insight 1",
            reflection_type=ReflectionType.INSIGHT,
            source_memory_ids=[
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            ],
            tenant_id="test_tenant",
            agent_id="test_agent",
        )
    )

    # Add Pattern
    await reflective_layer.add_reflection(
        Reflection(
            content="Pattern 1",
            reflection_type=ReflectionType.PATTERN,
            source_memory_ids=[
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            ],
            tenant_id="test_tenant",
            agent_id="test_agent",
        )
    )

    # Search Insight
    results = await reflective_layer.search_memories(
        "Insight", reflection_type=ReflectionType.INSIGHT
    )
    assert len(results) == 1
    assert results[0].memory.content == "Insight 1"


@pytest.mark.asyncio
async def test_cleanup_low_confidence(reflective_layer):
    """Test cleanup of low confidence reflections."""
    # High confidence
    await reflective_layer.add_reflection(
        Reflection(
            content="Good",
            reflection_type=ReflectionType.INSIGHT,
            source_memory_ids=[
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            ],
            tenant_id="test_tenant",
            agent_id="test_agent",
            confidence=0.9,
        )
    )

    # Low confidence (< 0.3)
    await reflective_layer.add_reflection(
        Reflection(
            content="Bad",
            reflection_type=ReflectionType.INSIGHT,
            source_memory_ids=[
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            ],
            tenant_id="test_tenant",
            agent_id="test_agent",
            confidence=0.2,
        )
    )

    count = await reflective_layer.storage.count_memories(
        "test_tenant", "test_agent", "reflective"
    )
    assert count == 2

    deleted = await reflective_layer.cleanup()
    assert deleted == 1

    count = await reflective_layer.storage.count_memories(
        "test_tenant", "test_agent", "reflective"
    )
    assert count == 1


@pytest.mark.asyncio
async def test_find_patterns(reflective_layer):
    """Test finding patterns convenience method."""
    await reflective_layer.add_reflection(
        Reflection(
            content="Pattern Found",
            reflection_type=ReflectionType.PATTERN,
            source_memory_ids=[
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            ],
            tenant_id="test_tenant",
            agent_id="test_agent",
        )
    )

    patterns = await reflective_layer.find_patterns()
    assert len(patterns) == 1
    assert patterns[0].content == "Pattern Found"
    assert patterns[0].reflection_type == ReflectionType.PATTERN
