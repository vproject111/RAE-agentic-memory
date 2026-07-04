from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rae_core.adapters.redis import RedisCache


@pytest.mark.asyncio
async def test_clear_prefix_no_keys():
    mock_client = AsyncMock()

    # scan_iter returning no keys
    async def empty_scan_iter(*args, **kwargs):
        if False:
            yield "key"

    mock_client.scan_iter = empty_scan_iter

    cache = RedisCache(redis_client=mock_client)
    assert await cache.clear_prefix("*") == 0


@pytest.mark.asyncio
async def test_redis_key_generation():
    cache = RedisCache(prefix="test:")
    # Cover line 76
    key_agent = cache._make_key("key", agent_id="a1")
    assert key_agent == "test:a1:key"

    # Cover line 78
    key_session = cache._make_key("key", session_id="s1")
    assert key_session == "test:s1:key"

    # Both
    key_both = cache._make_key("key", agent_id="a1", session_id="s1")
    assert key_both == "test:a1:s1:key"


@pytest.mark.asyncio
async def test_redis_init_variants():
    # Patch the global aioredis variable in the rae_core.adapters.redis module
    import rae_core.adapters.redis

    with patch.object(rae_core.adapters.redis, "aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = MagicMock()
        mock_aioredis.Redis.return_value = MagicMock()

        # Test with url
        RedisCache(url="redis://localhost")
        assert mock_aioredis.from_url.called

        # Test default
        RedisCache()
        assert mock_aioredis.Redis.called


@pytest.mark.asyncio
async def test_redis_methods_exception_handling():
    mock_client = AsyncMock()
    # Trigger exceptions
    mock_client.get.side_effect = Exception("Error")
    mock_client.decrby.side_effect = Exception("Error")
    mock_client.ttl.side_effect = Exception("Error")
    mock_client.expire.side_effect = Exception("Error")
    mock_client.ping.side_effect = Exception("Error")
    mock_client.close.side_effect = Exception("Error")

    # scan_iter is an async iterator
    async def mock_scan_iter(*args, **kwargs):
        raise Exception("Error")
        yield "key"

    mock_client.scan_iter = mock_scan_iter

    cache = RedisCache(redis_client=mock_client)

    assert await cache.get("key") is None
    assert await cache.decrement("key") is None
    assert await cache.get_ttl("key") is None
    assert await cache.expire("key", 10) is False
    assert await cache.clear_prefix("*") == 0
    assert await cache.ping() is False
    await cache.close()


@pytest.mark.asyncio
async def test_redis_get_not_json():
    mock_client = AsyncMock()
    # Return non-JSON bytes
    mock_client.get.return_value = b"just a string"

    cache = RedisCache(redis_client=mock_client)
    res = await cache.get("key")
    assert res == "just a string"

    # Return non-JSON string
    mock_client.get.return_value = "just a string"
    res = await cache.get("key")
    assert res == "just a string"


@pytest.mark.asyncio
async def test_redis_set_complex_objects():
    mock_client = AsyncMock()
    cache = RedisCache(redis_client=mock_client)

    # List
    await cache.set("list", [1, 2, 3])
    assert mock_client.setex.called

    # Other object
    class Obj:
        def __str__(self):
            return "obj"

    await cache.set("obj", Obj())
    assert mock_client.setex.called
