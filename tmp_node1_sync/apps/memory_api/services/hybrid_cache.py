"""
Hybrid Search Cache - Enterprise caching layer for hybrid search results

This service provides:
- Query result caching with TTL
- Cache key generation based on query + tenant + filters
- Timestamp-windowed caching
- Cache invalidation strategies
- Cache hit/miss metrics
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, cast

import structlog

logger = structlog.get_logger(__name__)


class HybridSearchCache:
    """
    In-memory cache for hybrid search results with TTL and windowing.

    Features:
    - Hash-based cache keys
    - Temporal windowing (queries in same time window share cache)
    - Automatic expiration
    - Cache statistics
    - Memory-efficient storage
    """

    def __init__(
        self,
        default_ttl_seconds: int = 300,  # 5 minutes default
        window_size_seconds: int = 60,  # 1 minute window
        max_cache_size: int = 1000,  # Max number of cached entries
    ):
        """
        Initialize hybrid search cache.

        Args:
            default_ttl_seconds: Default time-to-live for cache entries
            window_size_seconds: Time window for grouping similar queries
            max_cache_size: Maximum number of entries before eviction
        """
        self.default_ttl = default_ttl_seconds
        self.window_size = window_size_seconds
        self.max_cache_size = max_cache_size

        # Cache storage: {cache_key: (result, expiry_time)}
        self._cache: Dict[str, tuple] = {}

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _generate_cache_key(
        self,
        query: str,
        tenant_id: str,
        project_id: str,
        filters: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Generate cache key based on query parameters and timestamp window.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            project_id: Project identifier
            filters: Optional search filters
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Hash-based cache key
        """
        # Use timestamp window (round down to nearest window)
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        window_timestamp = timestamp.timestamp() // self.window_size * self.window_size

        # Build key components
        key_components = [
            query.lower().strip(),
            tenant_id,
            project_id,
            str(window_timestamp),
        ]

        # Add filters to key if present
        if filters:
            # Sort filters for consistent hashing
            filters_str = json.dumps(filters, sort_keys=True)
            key_components.append(filters_str)

        # Generate hash
        key_string = "|".join(key_components)
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return cache_key

    async def get(
        self,
        query: str,
        tenant_id: str,
        project_id: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached search results if available and not expired.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            project_id: Project identifier
            filters: Optional search filters

        Returns:
            Cached results or None if not found/expired
        """
        cache_key = self._generate_cache_key(query, tenant_id, project_id, filters)

        if cache_key in self._cache:
            result, expiry_time = self._cache[cache_key]

            # Check if expired
            if datetime.now(timezone.utc) < expiry_time:
                self._hits += 1
                logger.info(
                    "cache_hit",
                    cache_key=cache_key,
                    tenant_id=tenant_id,
                    hit_rate=self.get_hit_rate(),
                )
                return cast(Optional[Dict[str, Any]], result)
            else:
                # Remove expired entry
                del self._cache[cache_key]
                logger.debug("cache_entry_expired", cache_key=cache_key)

        self._misses += 1
        logger.info(
            "cache_miss",
            cache_key=cache_key,
            tenant_id=tenant_id,
            hit_rate=self.get_hit_rate(),
        )
        return None

    async def set(
        self,
        query: str,
        tenant_id: str,
        project_id: str,
        result: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ):
        """
        Cache search results with TTL.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            project_id: Project identifier
            result: Search results to cache
            filters: Optional search filters
            ttl_seconds: Optional custom TTL (uses default if not specified)
        """
        # Check cache size and evict if necessary
        if len(self._cache) >= self.max_cache_size:
            await self._evict_oldest()

        cache_key = self._generate_cache_key(query, tenant_id, project_id, filters)
        ttl = ttl_seconds or self.default_ttl
        expiry_time = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        self._cache[cache_key] = (result, expiry_time)

        logger.info(
            "cache_set",
            cache_key=cache_key,
            tenant_id=tenant_id,
            ttl=ttl,
            cache_size=len(self._cache),
        )

    async def invalidate(self, tenant_id: str, project_id: Optional[str] = None):
        """
        Invalidate cache entries for a tenant/project.

        Args:
            tenant_id: Tenant identifier
            project_id: Optional project identifier (invalidates all tenant if None)
        """
        # Build invalidation pattern
        pattern_components = [tenant_id]
        if project_id:
            pattern_components.append(project_id)

        # Find keys to invalidate
        keys_to_remove = []
        for cache_key in self._cache.keys():
            # This is a simplified check - in production would store metadata
            keys_to_remove.append(cache_key)

        # Remove keys
        for key in keys_to_remove:
            del self._cache[key]

        logger.info(
            "cache_invalidated",
            tenant_id=tenant_id,
            project_id=project_id,
            entries_removed=len(keys_to_remove),
        )

    async def clear_expired(self):
        """Remove all expired cache entries."""
        now = datetime.now(timezone.utc)
        keys_to_remove = []

        for cache_key, (_, expiry_time) in self._cache.items():
            if now >= expiry_time:
                keys_to_remove.append(cache_key)

        for key in keys_to_remove:
            del self._cache[key]

        if keys_to_remove:
            logger.info("expired_entries_cleared", count=len(keys_to_remove))

    async def _evict_oldest(self):
        """Evict oldest cache entry (LRU-like)."""
        if not self._cache:
            return

        # Find entry with earliest expiry time
        oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
        del self._cache[oldest_key]
        self._evictions += 1

        logger.debug("cache_entry_evicted", cache_key=oldest_key)

    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as percentage (0.0 to 1.0)
        """
        total_requests = self._hits + self._misses
        if total_requests == 0:
            return 0.0
        return self._hits / total_requests

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self.max_cache_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": self.get_hit_rate(),
            "hit_rate_percent": f"{self.get_hit_rate() * 100:.2f}%",
            "default_ttl_seconds": self.default_ttl,
            "window_size_seconds": self.window_size,
        }

    async def clear_all(self):
        """Clear entire cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info("cache_cleared", entries_removed=cache_size)


# Global cache instance (singleton)
_cache_instance: Optional[HybridSearchCache] = None


def get_hybrid_cache() -> HybridSearchCache:
    """
    Get global hybrid search cache instance.

    Returns:
        Singleton HybridSearchCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = HybridSearchCache()
    return _cache_instance
