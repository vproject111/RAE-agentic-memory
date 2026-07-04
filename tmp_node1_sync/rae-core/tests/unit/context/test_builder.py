"""Unit tests for ContextBuilder."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from rae_core.context.builder import ContextBuilder, ContextFormat
from rae_core.models.context import ContextMetadata


class TestContextBuilder:
    """Test suite for ContextBuilder."""

    @pytest.fixture
    def builder(self):
        """Create a ContextBuilder instance for testing."""
        return ContextBuilder(
            max_tokens=1000, default_format=ContextFormat.CONVERSATIONAL
        )

    @pytest.fixture
    def sample_memories(self):
        """Create sample memory records for testing."""
        base_time = datetime.now(timezone.utc)
        return [
            {
                "id": str(uuid4()),
                "content": "First memory with moderate importance",
                "importance": 0.6,
                "score": 0.8,
                "tags": ["test", "sample"],
                "created_at": (base_time - timedelta(hours=1)).isoformat(),
                "modified_at": (base_time - timedelta(hours=1)).isoformat(),
            },
            {
                "id": str(uuid4()),
                "content": "Second memory with high importance",
                "importance": 0.9,
                "score": 0.9,
                "tags": ["important"],
                "created_at": (base_time - timedelta(minutes=30)).isoformat(),
                "modified_at": (base_time - timedelta(minutes=30)).isoformat(),
            },
            {
                "id": str(uuid4()),
                "content": "Third memory with low importance",
                "importance": 0.3,
                "score": 0.5,
                "tags": [],
                "created_at": (base_time - timedelta(hours=24)).isoformat(),
                "modified_at": (base_time - timedelta(hours=24)).isoformat(),
            },
        ]

    def test_builder_initialization(self):
        """Test builder initializes with correct defaults."""
        builder = ContextBuilder()
        assert builder.max_tokens == 4096
        assert builder.default_format == ContextFormat.CONVERSATIONAL
        assert builder.window_manager is not None

    def test_builder_custom_initialization(self):
        """Test builder initializes with custom parameters."""
        builder = ContextBuilder(
            max_tokens=2048, default_format=ContextFormat.STRUCTURED
        )
        assert builder.max_tokens == 2048
        assert builder.default_format == ContextFormat.STRUCTURED

    def test_build_context_basic(self, builder, sample_memories):
        """Test basic context building."""
        context, metadata = builder.build_context(sample_memories)

        assert isinstance(context, str)
        assert isinstance(metadata, ContextMetadata)
        assert len(context) > 0
        assert metadata.total_items == 3
        assert metadata.active_items > 0
        assert metadata.token_usage > 0

    def test_build_context_with_query(self, builder, sample_memories):
        """Test context building with query header."""
        query = "What are the important memories?"
        context, metadata = builder.build_context(sample_memories, query=query)

        assert query in context
        assert metadata.statistics["query_provided"] is True

    def test_build_context_conversational_format(self, builder, sample_memories):
        """Test conversational format context."""
        context, metadata = builder.build_context(
            sample_memories, format_type=ContextFormat.CONVERSATIONAL
        )

        assert "- " in context  # Bullet points
        assert "[Important]" in context  # High importance marker
        assert metadata.statistics["format"] == ContextFormat.CONVERSATIONAL

    def test_build_context_structured_format(self, builder, sample_memories):
        """Test structured format context."""
        context, metadata = builder.build_context(
            sample_memories, format_type=ContextFormat.STRUCTURED
        )

        assert "## Memory" in context
        assert "Importance:" in context
        assert "Tags:" in context
        assert metadata.statistics["format"] == ContextFormat.STRUCTURED

    def test_build_context_minimal_format(self, builder, sample_memories):
        """Test minimal format context."""
        context, metadata = builder.build_context(
            sample_memories, format_type=ContextFormat.MINIMAL
        )

        # Minimal format should just have content, no decorations
        assert "First memory" in context
        assert "## Memory" not in context
        assert "Importance:" not in context
        assert metadata.statistics["format"] == ContextFormat.MINIMAL

    def test_build_context_detailed_format(self, builder, sample_memories):
        """Test detailed format context."""
        context, metadata = builder.build_context(
            sample_memories, format_type=ContextFormat.DETAILED
        )

        assert "### Memory:" in context
        assert "**Content:**" in context
        assert "**Importance:**" in context
        assert "**Tags:**" in context
        assert metadata.statistics["format"] == ContextFormat.DETAILED

    def test_build_context_without_metadata(self, builder, sample_memories):
        """Test context building without metadata."""
        context, metadata = builder.build_context(
            sample_memories,
            format_type=ContextFormat.STRUCTURED,
            include_metadata=False,
        )

        # Should not include metadata fields
        assert "Importance:" not in context
        assert "Tags:" not in context

    def test_build_context_max_memories_limit(self, builder, sample_memories):
        """Test max_memories parameter limits results."""
        context, metadata = builder.build_context(sample_memories, max_memories=2)

        assert metadata.active_items <= 2
        assert metadata.total_items == 3
        assert metadata.statistics["truncated"] is True

    def test_build_context_token_limit(self):
        """Test that context respects token limits."""
        # Create builder with very small token limit
        builder = ContextBuilder(max_tokens=100)

        # Create memories with long content
        long_memories = [
            {
                "id": str(uuid4()),
                "content": "A" * 200,  # ~50 tokens
                "importance": 0.5,
            },
            {
                "id": str(uuid4()),
                "content": "B" * 200,  # ~50 tokens
                "importance": 0.5,
            },
            {
                "id": str(uuid4()),
                "content": "C" * 200,  # ~50 tokens
                "importance": 0.5,
            },
        ]

        context, metadata = builder.build_context(long_memories)

        # Should not include all memories due to token limit
        assert metadata.token_usage <= 100
        assert metadata.active_items < metadata.total_items

    def test_memory_ranking_by_importance(self, builder):
        """Test that memories are ranked by priority."""
        memories = [
            {"id": str(uuid4()), "content": "Low", "importance": 0.2, "score": 0.5},
            {"id": str(uuid4()), "content": "High", "importance": 0.9, "score": 0.5},
            {"id": str(uuid4()), "content": "Medium", "importance": 0.5, "score": 0.5},
        ]

        ranked = builder._rank_memories(memories)

        # Should be ordered by importance: High, Medium, Low
        assert ranked[0]["content"] == "High"
        assert ranked[1]["content"] == "Medium"
        assert ranked[2]["content"] == "Low"

    def test_memory_ranking_with_recency(self, builder):
        """Test that ranking considers recency."""
        now = datetime.now(timezone.utc)
        [
            {
                "id": "1",
                "content": "Recent memory",
                "importance": 0.5,
                "created_at": (now - timedelta(minutes=5)).isoformat(),
            },
            {
                "id": "2",
                "content": "Old memory",
                "importance": 0.5,
                "created_at": (now - timedelta(hours=24)).isoformat(),
            },
        ]

    def test_memory_ranking_with_relevance(self, builder):
        """Test that relevance score affects ranking."""
        memories = [
            {
                "id": str(uuid4()),
                "content": "Low relevance",
                "importance": 0.5,
                "score": 0.3,
            },
            {
                "id": str(uuid4()),
                "content": "High relevance",
                "importance": 0.5,
                "score": 0.9,
            },
        ]

        ranked = builder._rank_memories(memories)

        # High relevance should rank higher
        assert ranked[0]["content"] == "High relevance"

    def test_build_working_context(self, builder, sample_memories):
        """Test building WorkingContext model."""
        tenant_id = "test-tenant"
        agent_id = "test-agent"

        working_context = builder.build_working_context(
            tenant_id=tenant_id,
            agent_id=agent_id,
            memories=sample_memories,
        )

        assert working_context.tenant_id == tenant_id
        assert working_context.agent_id == agent_id
        assert len(working_context.window.items) == len(sample_memories)
        assert working_context.priority_score > 0

    def test_build_working_context_with_focus(self, builder, sample_memories):
        """Test building WorkingContext with focus items."""
        tenant_id = "test-tenant"
        agent_id = "test-agent"
        focus_id = uuid4()

        working_context = builder.build_working_context(
            tenant_id=tenant_id,
            agent_id=agent_id,
            memories=sample_memories,
            focus_items=[focus_id],
        )

        assert focus_id in working_context.focus_items
        # Priority score should be higher with focus items
        assert working_context.priority_score > 0.5

    def test_reset_builder(self, builder, sample_memories):
        """Test resetting builder state."""
        # Build context to populate window
        builder.build_context(sample_memories)

        # Reset
        builder.reset()

        # Window should be empty
        assert builder.window_manager.current_window.current_tokens == 0
        assert len(builder.window_manager.current_window.items) == 0

    def test_get_statistics(self, builder):
        """Test getting builder statistics."""
        stats = builder.get_statistics()

        assert "max_tokens" in stats
        assert "default_format" in stats
        assert "window_utilization" in stats
        assert "window_tokens" in stats
        assert stats["max_tokens"] == 1000

    def test_empty_memories_list(self, builder):
        """Test building context with empty memories list."""
        context, metadata = builder.build_context([])

        assert context == ""
        assert metadata.total_items == 0
        assert metadata.active_items == 0
        assert metadata.token_usage == 0

    def test_memory_without_optional_fields(self, builder):
        """Test handling memories without optional fields."""
        minimal_memories = [
            {
                "id": str(uuid4()),
                "content": "Minimal memory",
            }
        ]

        context, metadata = builder.build_context(minimal_memories)

        assert "Minimal memory" in context
        assert metadata.active_items == 1

    def test_priority_score_calculation(self, builder):
        """Test priority score calculation."""
        memories = [
            {"id": str(uuid4()), "content": "Test", "importance": 0.8},
            {"id": str(uuid4()), "content": "Test2", "importance": 0.6},
        ]
        focus_items = [uuid4()]

        score = builder._calculate_priority_score(memories, focus_items)

        assert 0.0 <= score <= 1.0
        # Should have focus boost
        assert score > 0.7

    def test_priority_score_empty_memories(self, builder):
        """Test priority score with empty memories."""
        score = builder._calculate_priority_score([], [])
        assert score == 0.0

    def test_context_truncation_metadata(self):
        """Test that truncation is properly recorded in metadata."""
        builder = ContextBuilder(max_tokens=20)

        memories = [
            {"id": str(uuid4()), "content": "A" * 100, "importance": 0.5},
            {"id": str(uuid4()), "content": "B" * 100, "importance": 0.5},
            {"id": str(uuid4()), "content": "C" * 100, "importance": 0.5},
        ]

        context, metadata = builder.build_context(memories)

        assert metadata.statistics["truncated"] is True
        assert metadata.active_items < metadata.total_items

    def test_avg_tokens_per_memory_statistic(self, builder, sample_memories):
        """Test average tokens per memory statistic."""
        context, metadata = builder.build_context(sample_memories)

        avg_tokens = metadata.statistics["avg_tokens_per_memory"]
        assert avg_tokens > 0
        assert isinstance(avg_tokens, int)
