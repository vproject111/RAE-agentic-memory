from datetime import datetime, timezone
from uuid import uuid4

from rae_core.context.builder import ContextBuilder, ContextFormat


def test_rank_memories_recency_variants():
    builder = ContextBuilder()

    # Test modified_at as ISO string
    m1 = {
        "id": uuid4(),
        "importance": 0.5,
        "modified_at": datetime.now(timezone.utc).isoformat(),
    }
    # Test modified_at as naive datetime
    m2 = {"id": uuid4(), "importance": 0.5, "modified_at": datetime.now()}
    # Test modified_at as invalid string
    m3 = {"id": uuid4(), "importance": 0.5, "modified_at": "invalid date"}

    ranked = builder._rank_memories([m1, m2, m3])
    assert len(ranked) == 3


def test_format_query_header_formats():
    builder = ContextBuilder()

    assert "Query:" in builder._format_query_header("q", ContextFormat.MINIMAL)
    assert "# Query" in builder._format_query_header("q", ContextFormat.STRUCTURED)
    assert "## Search Query" in builder._format_query_header(
        "q", ContextFormat.DETAILED
    )
    assert "Based on your query" in builder._format_query_header(
        "q", ContextFormat.CONVERSATIONAL
    )


def test_format_memory_detailed():
    builder = ContextBuilder()
    m = {
        "id": uuid4(),
        "content": "test content",
        "importance": 0.9,
        "tags": ["tag1"],
        "created_at": datetime.now().isoformat(),
    }
    res = builder._format_memory(m, ContextFormat.DETAILED)
    assert "### Memory:" in res
    assert "**Importance:** 0.90" in res
    assert "**Tags:** tag1" in res
    assert "**Created:**" in res


def test_builder_statistics():
    builder = ContextBuilder()
    stats = builder.get_statistics()
    assert stats["max_tokens"] == 4096
    assert "window_utilization" in stats
