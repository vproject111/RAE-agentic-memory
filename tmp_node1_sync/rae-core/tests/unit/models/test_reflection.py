from datetime import datetime
from uuid import UUID, uuid4

import pytest

from rae_core.models.reflection import (
    Reflection,
    ReflectionPolicy,
    ReflectionPriority,
    ReflectionType,
)


def test_reflection_defaults():
    reflection = Reflection(
        content="test reflection",
        reflection_type=ReflectionType.INSIGHT,
        tenant_id="t",
        agent_id="a",
    )

    assert isinstance(reflection.id, UUID)
    assert reflection.priority == ReflectionPriority.MEDIUM
    assert reflection.source_memory_ids == []
    assert reflection.tags == []
    assert reflection.confidence == 0.5
    assert isinstance(reflection.created_at, datetime)
    assert isinstance(reflection.last_updated_at, datetime)


def test_reflection_validation():
    # Valid
    reflection = Reflection(
        content="test",
        reflection_type=ReflectionType.PATTERN,
        tenant_id="t",
        agent_id="a",
        confidence=1.0,
    )
    assert reflection.confidence == 1.0

    # Invalid confidence
    with pytest.raises(ValueError):
        Reflection(
            content="test",
            reflection_type=ReflectionType.PATTERN,
            tenant_id="t",
            agent_id="a",
            confidence=1.1,
        )


def test_reflection_policy_defaults():
    policy = ReflectionPolicy()
    assert policy.min_memories == 5
    assert policy.max_age_hours == 24
    assert policy.min_confidence == 0.6
    assert len(policy.enabled_types) == len(ReflectionType)


def test_reflection_full_init():
    source_id = uuid4()
    reflection = Reflection(
        content="Full test",
        reflection_type=ReflectionType.CONTRADICTION,
        priority=ReflectionPriority.HIGH,
        source_memory_ids=[source_id],
        tenant_id="tenant",
        agent_id="agent",
        tags=["important"],
        confidence=0.9,
    )

    assert reflection.content == "Full test"
    assert reflection.reflection_type == ReflectionType.CONTRADICTION
    assert reflection.priority == ReflectionPriority.HIGH
    assert reflection.source_memory_ids == [source_id]
    assert reflection.tags == ["important"]
    assert reflection.confidence == 0.9
