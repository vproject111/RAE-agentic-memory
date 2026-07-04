"""Additional unit tests for InMemoryCache to achieve 100% coverage."""

import pytest

from rae_adapters.memory.cache import InMemoryCache


class TestInMemoryCacheCoverage:
    """Test suite for InMemoryCache coverage gaps."""

    @pytest.fixture
    async def cache(self):
        """Create cache instance for testing."""
        return InMemoryCache()

    @pytest.mark.asyncio
    async def test_get_full_key_logic(self, cache):
        """Test the key generation with agent and session IDs."""
        # This covers _get_full_key through public methods
        await cache.set("key", "val", agent_id="agent1")
        assert await cache.get("key", agent_id="agent1") == "val"
        assert await cache.get("key") is None

        await cache.set("key", "val_session", agent_id="agent1", session_id="sess1")
        assert (
            await cache.get("key", agent_id="agent1", session_id="sess1")
            == "val_session"
        )
        assert await cache.get("key", agent_id="agent1") == "val"

    @pytest.mark.asyncio
    async def test_clear_with_agent_filter(self, cache):
        """Test clearing keys filtered by agent_id."""
        await cache.set("key1", "val1", agent_id="agent1")
        await cache.set("key2", "val2", agent_id="agent1")
        await cache.set("key3", "val3", agent_id="agent2")

        # Clear only agent1
        count = await cache.clear(agent_id="agent1")
        assert count == 2
        assert await cache.get("key1", agent_id="agent1") is None
        assert await cache.get("key2", agent_id="agent1") is None
        assert await cache.get("key3", agent_id="agent2") == "val3"

    @pytest.mark.asyncio
    async def test_clear_with_agent_and_session_filter(self, cache):
        """Test clearing keys filtered by agent_id and session_id."""
        await cache.set("key1", "val1", agent_id="agent1", session_id="sess1")
        await cache.set("key2", "val2", agent_id="agent1", session_id="sess2")

        count = await cache.clear(agent_id="agent1", session_id="sess1")
        assert count == 1
        assert await cache.get("key1", agent_id="agent1", session_id="sess1") is None
        assert await cache.get("key2", agent_id="agent1", session_id="sess2") == "val2"

    @pytest.mark.asyncio
    async def test_clear_with_prefix_and_pattern(self, cache):
        """Test clearing with both prefix (from agent_id) and pattern."""
        await cache.set("user:1", "data1", agent_id="agent1")
        await cache.set("admin:1", "data2", agent_id="agent1")
        await cache.set("user:1", "data3", agent_id="agent2")

        # Clear user:* for agent1
        count = await cache.clear(pattern="user:*", agent_id="agent1")
        assert count == 1
        assert await cache.get("user:1", agent_id="agent1") is None
        assert await cache.get("admin:1", agent_id="agent1") == "data2"
        assert await cache.get("user:1", agent_id="agent2") == "data3"

    @pytest.mark.asyncio
    async def test_increment_non_numeric_types(self, cache):
        """Test increment with various non-numeric types to trigger catch blocks."""
        await cache.set("key_list", [1, 2])
        val = await cache.increment("key_list")
        assert val == 1

        await cache.set("key_dict", {"a": 1})
        val = await cache.increment("key_dict")
        assert val == 1

        await cache.set("key_none", None)
        val = await cache.increment("key_none")
        assert val == 1
