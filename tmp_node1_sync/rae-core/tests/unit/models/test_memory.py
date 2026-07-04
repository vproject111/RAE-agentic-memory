from datetime import datetime
from uuid import UUID

import pytest

from rae_core.models.memory import (
    MemoryItem,
    MemoryLayer,
    MemoryStats,
    MemoryType,
    ScoredMemoryItem,
)


def test_memory_item_defaults():
    item = MemoryItem(
        content="test content",
        layer=MemoryLayer.SENSORY,
        tenant_id="test-tenant",
        agent_id="test-agent",
    )

    assert isinstance(item.id, UUID)
    assert isinstance(item.created_at, datetime)
    assert isinstance(item.last_accessed_at, datetime)
    assert item.memory_type == MemoryType.TEXT
    assert item.tags == []
    assert item.metadata == {}
    assert item.embedding is None
    assert item.importance == 0.5
    assert item.usage_count == 0


def test_memory_item_validation():
    # Valid importance
    item = MemoryItem(
        content="test",
        layer=MemoryLayer.WORKING,
        tenant_id="t",
        agent_id="a",
        importance=1.0,
    )
    assert item.importance == 1.0

    # Invalid importance > 1.0
    with pytest.raises(ValueError):
        MemoryItem(
            content="test",
            layer=MemoryLayer.WORKING,
            tenant_id="t",
            agent_id="a",
            importance=1.1,
        )

    # Invalid importance < 0.0
    with pytest.raises(ValueError):
        MemoryItem(
            content="test",
            layer=MemoryLayer.WORKING,
            tenant_id="t",
            agent_id="a",
            importance=-0.1,
        )


def test_memory_item_serialization():
    item = MemoryItem(
        content="test content",
        layer=MemoryLayer.EPISODIC,
        tenant_id="test-tenant",
        agent_id="test-agent",
        tags=["tag1", "tag2"],
        importance=0.8,
    )

    json_data = item.model_dump()
    assert json_data["content"] == "test content"
    assert json_data["layer"] == "episodic"
    assert json_data["tags"] == ["tag1", "tag2"]
    assert json_data["importance"] == 0.8


def test_scored_memory_item():
    item = MemoryItem(
        content="test",
        layer=MemoryLayer.SEMANTIC,
        tenant_id="t",
        agent_id="a",
    )

    scored_item = ScoredMemoryItem(
        memory=item, score=0.9, score_breakdown={"similarity": 0.9}
    )

    assert scored_item.score == 0.9
    assert scored_item.memory.content == "test"
    assert (
        scored_item.score_breakdown and scored_item.score_breakdown["similarity"] == 0.9
    )

    # Invalid score
    with pytest.raises(ValueError):
        ScoredMemoryItem(memory=item, score=1.1)


def test_memory_stats():
    stats = MemoryStats(
        total_count=10,
        by_layer={MemoryLayer.SENSORY: 5, MemoryLayer.WORKING: 5},
        by_type={MemoryType.TEXT: 10},
        average_importance=0.6,
        total_usage=100,
    )

    assert stats.total_count == 10
    assert stats.by_layer[MemoryLayer.SENSORY] == 5
    assert stats.average_importance == 0.6
