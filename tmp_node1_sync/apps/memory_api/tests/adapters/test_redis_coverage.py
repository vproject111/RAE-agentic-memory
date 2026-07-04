"""Unit tests for RedisCache to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rae_adapters.redis import RedisCache


class TestRedisCacheCoverage:
    """Test suite for RedisCache coverage gaps."""

    @pytest.mark.asyncio
    async def test_init_no_aioredis(self):
        """Test initialization when redis-client is not available."""
        with patch("rae_adapters.redis.aioredis", None):
            with pytest.raises(ImportError, match="redis is required"):
                RedisCache()

    @pytest.mark.asyncio
    async def test_get_exception(self):
        """Test get returning None on exception."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.get("key")
        assert res is None

    @pytest.mark.asyncio
    async def test_set_exception(self):
        """Test set returning False on exception."""
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.set("key", "val", ttl=10)
        assert res is False

    @pytest.mark.asyncio
    async def test_delete_exception(self):
        """Test delete returning False on exception."""
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.delete("key")
        assert res is False

    @pytest.mark.asyncio
    async def test_exists_exception(self):
        """Test exists returning False on exception."""
        mock_redis = AsyncMock()
        mock_redis.exists.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.exists("key")
        assert res is False

    @pytest.mark.asyncio
    async def test_increment_exception(self):
        """Test increment returning None on exception."""
        mock_redis = AsyncMock()
        mock_redis.incrby.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.increment("key")
        assert res is None

    @pytest.mark.asyncio
    async def test_decrement_exception(self):
        """Test decrement returning None on exception."""
        mock_redis = AsyncMock()
        mock_redis.decrby.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.decrement("key")
        assert res is None

    @pytest.mark.asyncio
    async def test_clear_exception(self):
        """Test clear returning 0 on exception."""
        mock_redis = (
            MagicMock()
        )  # scan_iter is usually not AsyncMock but returns async iterator
        mock_redis.scan_iter.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.clear("*")
        assert res == 0

    @pytest.mark.asyncio
    async def test_ping_exception(self):
        """Test ping returning False on exception."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        res = await cache.ping()
        assert res is False

    @pytest.mark.asyncio
    async def test_close_exception(self):
        """Test close handling exception silently."""
        mock_redis = AsyncMock()
        mock_redis.close.side_effect = Exception("Redis error")
        cache = RedisCache(redis_client=mock_redis)
        await cache.close()
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_from_url(self):
        """Test initialization from URL."""
        mock_redis = MagicMock()
        with patch("rae_adapters.redis.aioredis") as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis
            cache = RedisCache(url="redis://host:6379/0")
            assert cache.redis == mock_redis
            mock_aioredis.from_url.assert_called_once_with("redis://host:6379/0")

    @pytest.mark.asyncio
    async def test_init_default(self):
        """Test default initialization."""
        mock_redis = MagicMock()
        with patch("rae_adapters.redis.aioredis") as mock_aioredis:
            mock_aioredis.Redis.return_value = mock_redis
            cache = RedisCache()
            assert cache.redis == mock_redis
            mock_aioredis.Redis.assert_called_once()
