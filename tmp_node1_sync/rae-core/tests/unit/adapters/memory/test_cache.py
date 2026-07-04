"""Unit tests for InMemoryCache adapter."""

import asyncio

import pytest

from rae_core.adapters.memory.cache import InMemoryCache


class TestInMemoryCache:
    """Test suite for InMemoryCache."""

    @pytest.fixture
    async def cache(self):
        """Create cache instance for testing."""
        return InMemoryCache()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test setting and getting a value."""
        await cache.set("key1", "value1")
        value = await cache.get("key1")

        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache):
        """Test getting non-existent key."""
        value = await cache.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache):
        """Test setting value with TTL."""
        await cache.set("key1", "value1", ttl=1)

        # Should exist immediately
        value = await cache.get("key1")
        assert value == "value1"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_overwrite(self, cache):
        """Test overwriting existing key."""
        await cache.set("key1", "value1")
        await cache.set("key1", "value2")

        value = await cache.get("key1")
        assert value == "value2"

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test deleting a key."""
        await cache.set("key1", "value1")

        success = await cache.delete("key1")
        assert success is True

        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Test deleting non-existent key."""
        success = await cache.delete("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test checking if key exists."""
        await cache.set("key1", "value1")

        exists = await cache.exists("key1")
        assert exists is True

        exists = await cache.exists("key2")
        assert exists is False

    @pytest.mark.asyncio
    async def test_exists_expired(self, cache):
        """Test exists with expired key."""
        await cache.set("key1", "value1", ttl=1)

        # Should exist immediately
        exists = await cache.exists("key1")
        assert exists is True

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should not exist
        exists = await cache.exists("key1")
        assert exists is False

    @pytest.mark.asyncio
    async def test_clear_all(self, cache):
        """Test clearing all keys."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        count = await cache.clear()
        assert count == 3

        # Verify all keys are gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    @pytest.mark.asyncio
    async def test_clear_with_pattern_asterisk(self, cache):
        """Test clearing keys with wildcard pattern."""
        await cache.set("user:1", "alice")
        await cache.set("user:2", "bob")
        await cache.set("admin:1", "charlie")

        count = await cache.clear("user:*")
        assert count == 2

        # user:* keys should be gone
        assert await cache.get("user:1") is None
        assert await cache.get("user:2") is None

        # admin:1 should still exist
        assert await cache.get("admin:1") == "charlie"

    @pytest.mark.asyncio
    async def test_clear_with_pattern_question_mark(self, cache):
        """Test clearing keys with single character wildcard."""
        await cache.set("cache:1:data", "value1")
        await cache.set("cache:2:data", "value2")
        await cache.set("cache:10:data", "value3")

        count = await cache.clear("cache:?:data")
        assert count == 2  # Matches only single-digit

        # Single digit keys should be gone
        assert await cache.get("cache:1:data") is None
        assert await cache.get("cache:2:data") is None

        # Two-digit key should still exist
        assert await cache.get("cache:10:data") == "value3"

    @pytest.mark.asyncio
    async def test_clear_with_complex_pattern(self, cache):
        """Test clearing with complex pattern."""
        await cache.set("api:v1:users", "data1")
        await cache.set("api:v1:posts", "data2")
        await cache.set("api:v2:users", "data3")
        await cache.set("cache:users", "data4")

        count = await cache.clear("api:v1:*")
        assert count == 2

        assert await cache.get("api:v1:users") is None
        assert await cache.get("api:v1:posts") is None
        assert await cache.get("api:v2:users") == "data3"
        assert await cache.get("cache:users") == "data4"

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache):
        """Test cleaning up expired entries."""
        await cache.set("key1", "value1", ttl=1)
        await cache.set("key2", "value2")  # No TTL

        # Wait for expiration
        await asyncio.sleep(1.1)

        count = await cache.cleanup_expired()
        assert count == 1

        # Expired key should be gone
        assert await cache.get("key1") is None

        # Non-TTL key should still exist
        assert await cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_get_ttl(self, cache):
        """Test getting remaining TTL."""
        await cache.set("key1", "value1", ttl=10)

        ttl = await cache.get_ttl("key1")
        assert ttl is not None
        assert 8 <= ttl <= 10  # Allow some timing variance

    @pytest.mark.asyncio
    async def test_get_ttl_no_expiry(self, cache):
        """Test getting TTL for key without expiry."""
        await cache.set("key1", "value1")

        ttl = await cache.get_ttl("key1")
        assert ttl is None

    @pytest.mark.asyncio
    async def test_get_ttl_nonexistent(self, cache):
        """Test getting TTL for non-existent key."""
        ttl = await cache.get_ttl("nonexistent")
        assert ttl is None

    @pytest.mark.asyncio
    async def test_get_ttl_expired(self, cache):
        """Test getting TTL for expired key."""
        await cache.set("key1", "value1", ttl=1)

        await asyncio.sleep(1.1)

        ttl = await cache.get_ttl("key1")
        assert ttl is None

    @pytest.mark.asyncio
    async def test_set_if_not_exists_new_key(self, cache):
        """Test setting value if key doesn't exist (new key)."""
        success = await cache.set_if_not_exists("key1", "value1")
        assert success is True

        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_set_if_not_exists_existing_key(self, cache):
        """Test setting value if key doesn't exist (existing key)."""
        await cache.set("key1", "value1")

        success = await cache.set_if_not_exists("key1", "value2")
        assert success is False

        # Original value should be unchanged
        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_set_if_not_exists_expired_key(self, cache):
        """Test set_if_not_exists with expired key."""
        await cache.set("key1", "value1", ttl=1)

        # Wait for expiration plus buffer
        await asyncio.sleep(1.2)

        # Should succeed since key is expired
        success = await cache.set_if_not_exists("key1", "value2")
        assert success is True

        value = await cache.get("key1")
        assert value == "value2"

    @pytest.mark.asyncio
    async def test_increment_new_key(self, cache):
        """Test incrementing new key."""
        value = await cache.increment("counter")
        assert value == 1

    @pytest.mark.asyncio
    async def test_increment_existing_key(self, cache):
        """Test incrementing existing key."""
        await cache.set("counter", 5)

        value = await cache.increment("counter")
        assert value == 6

        value = await cache.increment("counter")
        assert value == 7

    @pytest.mark.asyncio
    async def test_increment_with_delta(self, cache):
        """Test incrementing with custom delta."""
        await cache.set("counter", 10)

        value = await cache.increment("counter", delta=5)
        assert value == 15

    @pytest.mark.asyncio
    async def test_increment_negative_delta(self, cache):
        """Test decrementing with negative delta."""
        await cache.set("counter", 10)

        value = await cache.increment("counter", delta=-3)
        assert value == 7

    @pytest.mark.asyncio
    async def test_increment_non_numeric(self, cache):
        """Test incrementing non-numeric value."""
        await cache.set("counter", "not a number")

        # Should reset to 0 and increment
        value = await cache.increment("counter")
        assert value == 1

    @pytest.mark.asyncio
    async def test_increment_preserves_ttl(self, cache):
        """Test that increment preserves original TTL."""
        await cache.set("counter", 5, ttl=10)

        await cache.increment("counter")

        # TTL should still be set
        ttl = await cache.get_ttl("counter")
        assert ttl is not None
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_get_statistics(self, cache):
        """Test getting cache statistics."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2", ttl=10)
        await cache.set("key3", "value3", ttl=1)

        await asyncio.sleep(1.1)  # Let key3 expire

        stats = await cache.get_statistics()

        assert stats["total_keys"] == 3
        assert stats["active_keys"] == 2
        assert stats["expired_keys"] == 1
        assert stats["keys_with_ttl"] == 2

    @pytest.mark.asyncio
    async def test_clear_all_method(self, cache):
        """Test clear_all method."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        count = await cache.clear_all()
        assert count == 2

        stats = await cache.get_statistics()
        assert stats["total_keys"] == 0

    @pytest.mark.asyncio
    async def test_store_complex_types(self, cache):
        """Test storing complex data types."""
        # Dict
        await cache.set("dict", {"a": 1, "b": 2})
        assert await cache.get("dict") == {"a": 1, "b": 2}

        # List
        await cache.set("list", [1, 2, 3])
        assert await cache.get("list") == [1, 2, 3]

        # None
        await cache.set("none", None)
        # Note: get returns None for both non-existent and None value
        # This is a limitation of the simple interface

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, cache):
        """Test thread safety with concurrent operations."""

        async def increment_counter():
            for _ in range(10):
                await cache.increment("counter")

        # Run 5 concurrent tasks, each incrementing 10 times
        tasks = [increment_counter() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Final value should be 50
        value = await cache.get("counter")
        assert value == 50

    @pytest.mark.asyncio
    async def test_glob_pattern_edge_cases(self, cache):
        """Test glob pattern edge cases."""
        await cache.set("a", "1")
        await cache.set("aa", "2")
        await cache.set("aaa", "3")
        await cache.set("b", "4")

        # Pattern: a*
        count = await cache.clear("a*")
        assert count == 3

        assert await cache.get("b") == "4"

    @pytest.mark.asyncio
    async def test_glob_pattern_special_chars(self, cache):
        """Test glob pattern with special regex characters."""
        await cache.set("key.1", "value1")
        await cache.set("key.2", "value2")
        await cache.set("key1", "value3")

        # Pattern with dot (should be escaped)
        count = await cache.clear("key.*")
        assert count == 2

        # key1 (without dot) should still exist
        assert await cache.get("key1") == "value3"
