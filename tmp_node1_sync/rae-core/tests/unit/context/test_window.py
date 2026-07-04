"""Unit tests for ContextWindowManager."""

from uuid import uuid4

import pytest

from rae_core.context.window import ContextWindowManager, estimate_tokens
from rae_core.models.context import ContextWindow


class TestContextWindowManager:
    """Test suite for ContextWindowManager."""

    @pytest.fixture
    def manager(self):
        """Create a ContextWindowManager instance for testing."""
        return ContextWindowManager(max_tokens=1000)

    def test_manager_initialization(self):
        """Test manager initializes with correct defaults."""
        manager = ContextWindowManager()
        assert manager.max_tokens == 4096
        assert manager.current_window is None

    def test_manager_custom_initialization(self):
        """Test manager initializes with custom max_tokens."""
        manager = ContextWindowManager(max_tokens=2048)
        assert manager.max_tokens == 2048

    def test_create_window(self, manager):
        """Test creating a new context window."""
        window = manager.create_window()

        assert isinstance(window, ContextWindow)
        assert window.max_tokens == 1000
        assert window.current_tokens == 0
        assert len(window.items) == 0
        assert manager.current_window is window

    def test_add_item_success(self, manager):
        """Test successfully adding item to window."""
        manager.create_window()
        item_id = uuid4()

        result = manager.add_item(item_id, tokens=100)

        assert result is True
        assert item_id in manager.current_window.items
        assert manager.current_window.current_tokens == 100

    def test_add_item_creates_window_if_needed(self, manager):
        """Test that add_item creates window if none exists."""
        assert manager.current_window is None

        item_id = uuid4()
        result = manager.add_item(item_id, tokens=100)

        assert result is True
        assert manager.current_window is not None

    def test_add_item_respects_token_limit(self, manager):
        """Test that add_item respects max_tokens limit."""
        manager.create_window()

        # Add item that fills most of window
        item1_id = uuid4()
        manager.add_item(item1_id, tokens=900)

        # Try to add item that would exceed limit
        item2_id = uuid4()
        result = manager.add_item(item2_id, tokens=200)

        assert result is False
        assert item2_id not in manager.current_window.items
        assert manager.current_window.current_tokens == 900

    def test_add_item_exactly_at_limit(self, manager):
        """Test adding item that exactly reaches limit."""
        manager.create_window()

        item1_id = uuid4()
        manager.add_item(item1_id, tokens=500)

        item2_id = uuid4()
        result = manager.add_item(item2_id, tokens=500)

        assert result is True
        assert manager.current_window.current_tokens == 1000

    def test_add_multiple_items(self, manager):
        """Test adding multiple items to window."""
        manager.create_window()

        items = [uuid4() for _ in range(5)]
        for item_id in items:
            manager.add_item(item_id, tokens=100)

        assert len(manager.current_window.items) == 5
        assert manager.current_window.current_tokens == 500

    def test_remove_item_success(self, manager):
        """Test successfully removing item from window."""
        manager.create_window()
        item_id = uuid4()
        manager.add_item(item_id, tokens=100)

        result = manager.remove_item(item_id, tokens=100)

        assert result is True
        assert item_id not in manager.current_window.items
        assert manager.current_window.current_tokens == 0

    def test_remove_item_no_window(self, manager):
        """Test removing item when no window exists."""
        item_id = uuid4()
        result = manager.remove_item(item_id, tokens=100)

        assert result is False

    def test_remove_item_not_in_window(self, manager):
        """Test removing item that's not in window."""
        manager.create_window()
        item_id = uuid4()

        result = manager.remove_item(item_id, tokens=100)

        assert result is False

    def test_remove_item_updates_tokens(self, manager):
        """Test that remove_item properly updates token count."""
        manager.create_window()

        item1_id = uuid4()
        item2_id = uuid4()
        manager.add_item(item1_id, tokens=300)
        manager.add_item(item2_id, tokens=200)

        manager.remove_item(item1_id, tokens=300)

        assert manager.current_window.current_tokens == 200
        assert item2_id in manager.current_window.items

    def test_remove_item_prevents_negative_tokens(self, manager):
        """Test that token count never goes below zero."""
        manager.create_window()
        item_id = uuid4()
        manager.add_item(item_id, tokens=100)

        # Try to remove more tokens than exist
        manager.remove_item(item_id, tokens=500)

        assert manager.current_window.current_tokens == 0

    def test_compact_keeps_specified_items(self, manager):
        """Test compacting window to keep only specified items."""
        manager.create_window()

        item1_id = uuid4()
        item2_id = uuid4()
        item3_id = uuid4()

        manager.add_item(item1_id, tokens=100)
        manager.add_item(item2_id, tokens=100)
        manager.add_item(item3_id, tokens=100)

        # Keep only item1 and item3
        removed = manager.compact([item1_id, item3_id])

        assert removed == 1
        assert item1_id in manager.current_window.items
        assert item2_id not in manager.current_window.items
        assert item3_id in manager.current_window.items
        assert len(manager.current_window.items) == 2

    def test_compact_no_window(self, manager):
        """Test compacting when no window exists."""
        removed = manager.compact([uuid4()])
        assert removed == 0

    def test_compact_empty_keep_list(self, manager):
        """Test compacting with empty keep list removes all items."""
        manager.create_window()

        manager.add_item(uuid4(), tokens=100)
        manager.add_item(uuid4(), tokens=100)

        removed = manager.compact([])

        assert removed == 2
        assert len(manager.current_window.items) == 0

    def test_get_utilization_no_window(self, manager):
        """Test getting utilization when no window exists."""
        utilization = manager.get_utilization()
        assert utilization == 0.0

    def test_get_utilization_empty_window(self, manager):
        """Test getting utilization for empty window."""
        manager.create_window()
        utilization = manager.get_utilization()
        assert utilization == 0.0

    def test_get_utilization_partial(self, manager):
        """Test getting utilization for partially filled window."""
        manager.create_window()
        manager.add_item(uuid4(), tokens=250)

        utilization = manager.get_utilization()
        assert utilization == 0.25

    def test_get_utilization_full(self, manager):
        """Test getting utilization for full window."""
        manager.create_window()
        manager.add_item(uuid4(), tokens=1000)

        utilization = manager.get_utilization()
        assert utilization == 1.0

    def test_has_space_for_no_window(self, manager):
        """Test has_space_for when no window exists."""
        result = manager.has_space_for(500)
        assert result is True

        result = manager.has_space_for(2000)
        assert result is False

    def test_has_space_for_empty_window(self, manager):
        """Test has_space_for with empty window."""
        manager.create_window()

        result = manager.has_space_for(500)
        assert result is True

        result = manager.has_space_for(1000)
        assert result is True

        result = manager.has_space_for(1001)
        assert result is False

    def test_has_space_for_partial_window(self, manager):
        """Test has_space_for with partially filled window."""
        manager.create_window()
        manager.add_item(uuid4(), tokens=600)

        result = manager.has_space_for(400)
        assert result is True

        result = manager.has_space_for(401)
        assert result is False

    def test_has_space_for_full_window(self, manager):
        """Test has_space_for with full window."""
        manager.create_window()
        manager.add_item(uuid4(), tokens=1000)

        result = manager.has_space_for(1)
        assert result is False

        result = manager.has_space_for(0)
        assert result is True


class TestEstimateTokens:
    """Test suite for estimate_tokens function."""

    def test_estimate_tokens_empty_string(self):
        """Test estimating tokens for empty string."""
        tokens = estimate_tokens("")
        assert tokens == 1  # Minimum is 1

    def test_estimate_tokens_short_text(self):
        """Test estimating tokens for short text."""
        text = "Hello"  # 5 chars
        tokens = estimate_tokens(text)
        assert tokens == 1  # 5 // 4 = 1

    def test_estimate_tokens_medium_text(self):
        """Test estimating tokens for medium text."""
        text = "This is a test sentence with multiple words."  # ~45 chars
        tokens = estimate_tokens(text)
        assert tokens == 11  # 45 // 4 = 11

    def test_estimate_tokens_long_text(self):
        """Test estimating tokens for long text."""
        text = "A" * 1000  # 1000 chars
        tokens = estimate_tokens(text)
        assert tokens == 250  # 1000 // 4 = 250

    def test_estimate_tokens_heuristic(self):
        """Test that estimate follows 4 chars per token heuristic."""
        text = "x" * 400  # 400 chars
        tokens = estimate_tokens(text)
        assert tokens == 100  # 400 // 4 = 100

    def test_estimate_tokens_minimum_value(self):
        """Test that estimate_tokens returns at least 1."""
        text = "a"  # 1 char
        tokens = estimate_tokens(text)
        assert tokens == 1

        text = "ab"  # 2 chars
        tokens = estimate_tokens(text)
        assert tokens == 1

        text = "abc"  # 3 chars
        tokens = estimate_tokens(text)
        assert tokens == 1

        text = "abcd"  # 4 chars
        tokens = estimate_tokens(text)
        assert tokens == 1
