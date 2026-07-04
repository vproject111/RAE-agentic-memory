"""Unit tests for RedisCache adapter."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock redis.asyncio if not available
with patch.dict(sys.modules, {"redis.asyncio": MagicMock()}):
    from rae_adapters.redis import RedisCache


class TestRedisCache:
    """Test suite for RedisCache."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        client.get.return_value = None
        client.set.return_value = True
        client.delete.return_value = 1
        client.exists.return_value = 1
        client.incrby.return_value = 1
        client.decrby.return_value = 1
        client.ttl.return_value = 3600
        client.expire.return_value = True
        client.ping.return_value = True
        return client

    @pytest.fixture
    def redis_cache(self, mock_redis_client):
        """Create RedisCache instance with mock client."""
        # Patch aioredis to avoid import errors and return mock client
        with patch("rae_adapters.redis.aioredis") as mock_aioredis:
            mock_aioredis.Redis.return_value = mock_redis_client
            mock_aioredis.from_url.return_value = mock_redis_client

            cache = RedisCache(url="redis://localhost", redis_client=mock_redis_client)
            return cache

    @pytest.mark.asyncio
    async def test_get_hit(self, redis_cache, mock_redis_client):
        """Test cache hit."""
        mock_redis_client.get.return_value = b'"value"'

        val = await redis_cache.get("key")
        assert val == "value"
        mock_redis_client.get.assert_called_with("rae:key")

    @pytest.mark.asyncio
    async def test_get_miss(self, redis_cache, mock_redis_client):
        """Test cache miss."""
        mock_redis_client.get.return_value = None

        val = await redis_cache.get("key")
        assert val is None

    @pytest.mark.asyncio
    async def test_get_json_error(self, redis_cache, mock_redis_client):
        """Test get with non-JSON value."""
        mock_redis_client.get.return_value = b"not-json"

        val = await redis_cache.get("key")
        assert val == "not-json"

    @pytest.mark.asyncio
    async def test_set_string(self, redis_cache, mock_redis_client):
        """Test setting a string value."""
        await redis_cache.set("key", "value")

        # Check that it was set with default TTL (raw string)
        mock_redis_client.setex.assert_called_with("rae:key", 3600, "value")

    @pytest.mark.asyncio
    async def test_set_dict(self, redis_cache, mock_redis_client):
        """Test setting a dict value (JSON serialization)."""
        data = {"a": 1}
        await redis_cache.set("key", data)

        mock_redis_client.setex.assert_called_with("rae:key", 3600, '{"a": 1}')

    @pytest.mark.asyncio
    async def test_set_no_ttl(self, redis_cache, mock_redis_client):
        """Test setting value with no TTL."""
        await redis_cache.set("key", "value", ttl=0)

        mock_redis_client.set.assert_called_with("rae:key", "value")

    @pytest.mark.asyncio
    async def test_delete(self, redis_cache, mock_redis_client):
        """Test deleting a key."""
        mock_redis_client.delete.return_value = 1

        result = await redis_cache.delete("key")
        assert result is True
        mock_redis_client.delete.assert_called_with("rae:key")

    @pytest.mark.asyncio
    async def test_exists(self, redis_cache, mock_redis_client):
        """Test checking if key exists."""
        mock_redis_client.exists.return_value = 1

        result = await redis_cache.exists("key")
        assert result is True
        mock_redis_client.exists.assert_called_with("rae:key")

    @pytest.mark.asyncio
    async def test_increment(self, redis_cache, mock_redis_client):
        """Test increment."""
        mock_redis_client.incrby.return_value = 2

        result = await redis_cache.increment("counter")
        assert result == 2
        mock_redis_client.incrby.assert_called_with("rae:counter", 1)

    @pytest.mark.asyncio
    async def test_decrement(self, redis_cache, mock_redis_client):
        """Test decrement."""
        mock_redis_client.decrby.return_value = 0

        result = await redis_cache.decrement("counter")
        assert result == 0
        mock_redis_client.decrby.assert_called_with("rae:counter", 1)

    @pytest.mark.asyncio
    async def test_get_ttl(self, redis_cache, mock_redis_client):
        """Test getting TTL."""
        mock_redis_client.ttl.return_value = 100

        result = await redis_cache.get_ttl("key")
        assert result == 100
        mock_redis_client.ttl.assert_called_with("rae:key")

    @pytest.mark.asyncio
    async def test_expire(self, redis_cache, mock_redis_client):
        """Test setting expiration."""
        mock_redis_client.expire.return_value = True

        result = await redis_cache.expire("key", 60)
        assert result is True
        mock_redis_client.expire.assert_called_with("rae:key", 60)

    @pytest.mark.asyncio
    async def test_clear_prefix(self, redis_cache, mock_redis_client):
        """Test clearing keys by prefix."""

        # Mock scan_iter to yield some keys
        async def mock_scan_iter(match):
            yield b"rae:key1"
            yield b"rae:key2"

        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.delete.return_value = 2

        result = await redis_cache.clear_prefix("*")
        assert result == 2
        mock_redis_client.delete.assert_called_with(b"rae:key1", b"rae:key2")

    @pytest.mark.asyncio
    async def test_clear(self, redis_cache, mock_redis_client):
        """Test clear calls clear_prefix."""

        # Mock scan_iter to yield some keys
        async def mock_scan_iter(match):
            yield b"rae:key1"

        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.delete.return_value = 1

        result = await redis_cache.clear()
        assert result == 1

    @pytest.mark.asyncio
    async def test_ping(self, redis_cache, mock_redis_client):
        """Test ping."""
        mock_redis_client.ping.return_value = True
        assert await redis_cache.ping() is True

    @pytest.mark.asyncio
    async def test_close(self, redis_cache, mock_redis_client):
        """Test close."""
        await redis_cache.close()
        mock_redis_client.close.assert_called_once()
