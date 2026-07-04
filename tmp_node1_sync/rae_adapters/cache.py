"""Cache adapter wrapper for RAE-Server.

Configures RAE-core RedisCache with RAE-Server settings.
"""

from redis.asyncio import Redis

from .redis import RedisCache


def get_cache_adapter(redis_client: Redis, prefix: str = "rae:") -> RedisCache:
    """Get configured Redis cache adapter.

    Args:
        redis_client: Redis client from RAE-Server
        prefix: Key prefix for namespacing (default: "rae:")

    Returns:
        Configured RedisCache instance
    """
    return RedisCache(redis_client=redis_client, prefix=prefix)
