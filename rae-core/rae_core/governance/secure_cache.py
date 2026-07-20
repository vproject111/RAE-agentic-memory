from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from typing import Any

from redis.asyncio import Redis

from rae_core.governance.cache_serialization import pack_cache_value, unpack_cache_value

logger = logging.getLogger(__name__)

LUA_RELEASE_LOCK = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


from collections import OrderedDict
from threading import Lock

class SecureCacheEngine:
    """Multi-layer secure cache engine with process-local L1, Redis L2, and thundering herd protection."""

    def __init__(
        self,
        redis_client: Redis | None = None,
        l1_max_items: int = 1000,
        l1_max_bytes: int = 256 * 1024,  # 256 KiB
        inventory_generation: int = 1,
    ) -> None:
        self.redis = redis_client
        self.l1_max_items = l1_max_items
        self.l1_max_bytes = l1_max_bytes
        self.inventory_generation = inventory_generation
        self._l1_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._l1_lock = Lock()

    def generate_cache_key(
        self,
        *,
        tenant_id: str,
        policy_version: str,
        scope: list[str],
        query: str,
    ) -> str:
        """Generate a secure, query-obscured cache key."""
        tenant_hash = hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:16]
        scope_str = ",".join(sorted(scope))
        scope_hash = hashlib.sha256(scope_str.encode("utf-8")).hexdigest()[:16]
        query_hash = hashlib.sha256(query.lower().strip().encode("utf-8")).hexdigest()[:16]
        
        return f"rae:kg:v3:{tenant_hash}:{policy_version}:{self.inventory_generation}:{scope_hash}:{query_hash}"

    async def get(self, key: str) -> dict | None:
        """Get value from L1 or L2 cache."""
        now = time.time()
        
        # 1. READ FROM L1 PROCESS CACHE
        with self._l1_lock:
            if key in self._l1_cache:
                expiry, value = self._l1_cache[key]
                if expiry > now:
                    logger.debug("L1 cache hit")
                    self._l1_cache.move_to_end(key)
                    return value
                else:
                    self._l1_cache.pop(key, None)

        # 2. READ FROM L2 REDIS CACHE
        if not self.redis:
            return None

        try:
            raw_val = await self.redis.get(key)
            if not raw_val:
                return None

            document = unpack_cache_value(raw_val)
            
            # Store in L1 if it doesn't exceed the payload limit
            raw_len = len(raw_val)
            if raw_len <= self.l1_max_bytes:
                with self._l1_lock:
                    if key in self._l1_cache:
                        self._l1_cache.pop(key, None)
                    if len(self._l1_cache) >= self.l1_max_items:
                        self._l1_cache.popitem(last=False)
                    self._l1_cache[key] = (now + 30.0, document)  # Short L1 TTL of 30 seconds

            return document
        except Exception as exc:
            logger.warning("Redis cache read failed, falling back gracefully", extra={"error": str(exc)})
            return None

    async def set(self, key: str, value: dict, ttl: int = 300) -> bool:
        """Set value in both L1 and L2 cache layers."""
        now = time.time()
        
        # Write to L1 (process memory cache)
        with self._l1_lock:
            if key in self._l1_cache:
                self._l1_cache.pop(key, None)
            if len(self._l1_cache) >= self.l1_max_items:
                self._l1_cache.popitem(last=False)
            self._l1_cache[key] = (now + min(30.0, float(ttl)), value)

        # Write to L2 (Redis cache)
        if not self.redis:
            return True

        try:
            packed = pack_cache_value(value)
            # Add ±10% Jitter to TTL to prevent cache stampede/thundering herd
            jitter = random.uniform(0.9, 1.1)
            final_ttl = max(1, int(ttl * jitter))

            await self.redis.setex(key, final_ttl, packed)
            return True
        except Exception as exc:
            logger.warning("Redis cache write failed, falling back gracefully to L1", extra={"error": str(exc)})
            return True

    async def acquire_lock(self, lock_key: str, token: str, ttl_ms: int = 5000) -> bool:
        """Acquire a temporary cache stampede lock."""
        if not self.redis:
            return True  # Fallback: assume lock acquired if Redis is down to prevent blocking
        try:
            return bool(await self.redis.set(lock_key, token, px=ttl_ms, nx=True))
        except Exception:
            return True

    async def release_lock(self, lock_key: str, token: str) -> bool:
        """Release the acquired cache stampede lock using safe Lua script."""
        if not self.redis:
            return True
        try:
            res = await self.redis.eval(LUA_RELEASE_LOCK, 1, lock_key, token)
            return bool(res)
        except Exception:
            return False
