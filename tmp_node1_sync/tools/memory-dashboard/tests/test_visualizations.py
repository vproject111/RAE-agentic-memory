"""
Tests for Visualization Utilities

Tests chart creation and formatting functions.
"""

import os
import sys
from datetime import datetime

import plotly.graph_objects as go
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.visualizations import (
    create_layer_distribution_chart,
    create_score_distribution,
    create_tags_wordcloud_chart,
    create_temporal_heatmap,
    create_timeline_chart,
    format_memory_preview,
    format_timestamp,
)


class TestChartCreation:
    """Test chart creation functions"""

    @pytest.fixture
    def sample_memories(self):
        """Sample memory data for testing"""
        return [
            {
                "id": "mem1",
                "content": "First memory content",
                "layer": "em",
                "timestamp": "2024-01-01T10:00:00",
                "source": "test",
                "tags": ["tag1", "tag2"],
            },
            {
                "id": "mem2",
                "content": "Second memory content",
                "layer": "wm",
                "timestamp": "2024-01-02T11:00:00",
                "source": "test",
                "tags": ["tag2", "tag3"],
            },
            {
                "id": "mem3",
                "content": "Third memory content",
                "layer": "sm",
                "timestamp": "2024-01-03T12:00:00",
                "source": "test",
                "tags": ["tag1", "tag3"],
            },
        ]

    @pytest.fixture
    def sample_results(self):
        """Sample search results with scores"""
        return [
            {"id": "r1", "content": "Result 1", "score": 0.95},
            {"id": "r2", "content": "Result 2", "score": 0.85},
            {"id": "r3", "content": "Result 3", "score": 0.75},
            {"id": "r4", "content": "Result 4", "score": 0.65},
            {"id": "r5", "content": "Result 5", "score": 0.55},
        ]

    def test_create_timeline_chart(self, sample_memories):
        """Test timeline chart creation"""
        fig = create_timeline_chart(sample_memories)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_create_timeline_chart_empty(self):
        """Test timeline chart with empty data"""
        fig = create_timeline_chart([])

        assert isinstance(fig, go.Figure)

    def test_create_layer_distribution_chart(self, sample_memories):
        """Test layer distribution chart"""
        fig = create_layer_distribution_chart(sample_memories)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_create_layer_distribution_chart_empty(self):
        """Test layer distribution with empty data"""
        fig = create_layer_distribution_chart([])

        assert isinstance(fig, go.Figure)

    def test_create_tags_wordcloud_chart(self, sample_memories):
        """Test tags word cloud chart"""
        fig = create_tags_wordcloud_chart(sample_memories)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_create_tags_wordcloud_chart_no_tags(self):
        """Test tags chart with no tags"""
        memories = [{"id": "m1", "content": "test"}]
        fig = create_tags_wordcloud_chart(memories)

        assert isinstance(fig, go.Figure)

    def test_create_tags_wordcloud_chart_empty(self):
        """Test tags chart with empty data"""
        fig = create_tags_wordcloud_chart([])

        assert isinstance(fig, go.Figure)

    def test_create_temporal_heatmap(self, sample_memories):
        """Test temporal heatmap creation"""
        fig = create_temporal_heatmap(sample_memories)

        assert isinstance(fig, go.Figure)

    def test_create_temporal_heatmap_empty(self):
        """Test heatmap with empty data"""
        fig = create_temporal_heatmap([])

        assert isinstance(fig, go.Figure)

    def test_create_score_distribution(self, sample_results):
        """Test score distribution chart"""
        fig = create_score_distribution(sample_results)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_create_score_distribution_empty(self):
        """Test score distribution with empty data"""
        fig = create_score_distribution([])

        assert isinstance(fig, go.Figure)


class TestFormattingFunctions:
    """Test formatting utility functions"""

    def test_format_memory_preview_short(self):
        """Test formatting short content"""
        content = "Short content"
        result = format_memory_preview(content, max_length=100)

        assert result == content
        assert "..." not in result

    def test_format_memory_preview_long(self):
        """Test formatting long content"""
        content = "A" * 200
        result = format_memory_preview(content, max_length=100)

        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_format_memory_preview_exact_length(self):
        """Test formatting at exact max length"""
        content = "A" * 100
        result = format_memory_preview(content, max_length=100)

        assert result == content
        assert "..." not in result

    def test_format_timestamp_string(self):
        """Test formatting timestamp from string"""
        timestamp = "2024-01-15T10:30:45"
        result = format_timestamp(timestamp)

        assert isinstance(result, str)
        assert "2024" in result
        assert "01" in result
        assert "15" in result

    def test_format_timestamp_datetime(self):
        """Test formatting timestamp from datetime"""
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        result = format_timestamp(timestamp)

        assert isinstance(result, str)
        assert "2024-01-15" in result
        assert "10:30:45" in result

    def test_format_timestamp_invalid(self):
        """Test formatting invalid timestamp"""
        timestamp = "invalid-timestamp"
        result = format_timestamp(timestamp)

        # Should return original string
        assert result == timestamp

    def test_format_timestamp_none(self):
        """Test formatting None timestamp"""
        result = format_timestamp(None)

        assert isinstance(result, str)

    def test_format_timestamp_number(self):
        """Test formatting numeric timestamp"""
        result = format_timestamp(12345)

        assert isinstance(result, str)


class TestChartProperties:
    """Test chart property configurations"""

    def test_timeline_chart_color_mapping(self):
        """Test timeline uses correct color mapping"""
        memories = [
            {
                "id": "m1",
                "content": "test",
                "layer": "em",
                "timestamp": "2024-01-01T10:00:00",
            },
            {
                "id": "m2",
                "content": "test",
                "layer": "wm",
                "timestamp": "2024-01-01T11:00:00",
            },
        ]
        fig = create_timeline_chart(memories)

        # Chart should have data
        assert len(fig.data) > 0

        # Should use dark template
        assert "dark" in fig.layout.template.to_plotly_json()

    def test_layer_distribution_chart_colors(self):
        """Test layer distribution uses color mapping"""
        memories = [
            {"id": "m1", "content": "test", "layer": "em"},
            {"id": "m2", "content": "test", "layer": "wm"},
            {"id": "m3", "content": "test", "layer": "sm"},
        ]
        fig = create_layer_distribution_chart(memories)

        # Should be pie chart
        assert len(fig.data) > 0
        assert fig.data[0].type == "pie"

    def test_heatmap_day_ordering(self):
        """Test heatmap orders days correctly"""
        # Create memories spanning a week
        memories = []
        for i in range(7):
            memories.append(
                {
                    "id": f"m{i}",
                    "content": "test",
                    "timestamp": f"2024-01-{i + 1:02d}T10:00:00",
                }
            )

        fig = create_temporal_heatmap(memories)

        # Should create a heatmap
        assert len(fig.data) > 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_memories_without_timestamps(self):
        """Test handling memories without timestamps"""
        memories = [{"id": "m1", "content": "test", "layer": "em"}]

        # Should not raise exception
        fig = create_timeline_chart(memories)
        assert isinstance(fig, go.Figure)

    def test_memories_with_missing_fields(self):
        """Test handling memories with missing fields"""
        memories = [
            {"id": "m1"},  # Minimal memory
            {"content": "test"},  # No ID
            {"layer": "em"},  # No content
        ]

        # Should handle gracefully
        fig = create_layer_distribution_chart(memories)
        assert isinstance(fig, go.Figure)

    def test_single_memory(self):
        """Test charts with single memory"""
        memories = [
            {
                "id": "m1",
                "content": "Single memory",
                "layer": "em",
                "timestamp": "2024-01-01T10:00:00",
                "tags": ["tag1"],
            }
        ]

        timeline = create_timeline_chart(memories)
        distribution = create_layer_distribution_chart(memories)
        tags = create_tags_wordcloud_chart(memories)

        assert all(isinstance(fig, go.Figure) for fig in [timeline, distribution, tags])

    def test_large_dataset(self):
        """Test charts with large dataset"""
        memories = []
        for i in range(1000):
            memories.append(
                {
                    "id": f"m{i}",
                    "content": f"Memory {i}",
                    "layer": ["em", "wm", "sm", "ltm"][i % 4],
                    "timestamp": f"2024-01-01T{i % 24:02d}:00:00",
                    "tags": [f"tag{i % 10}"],
                }
            )

        # Should handle large datasets
        fig = create_timeline_chart(memories)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
