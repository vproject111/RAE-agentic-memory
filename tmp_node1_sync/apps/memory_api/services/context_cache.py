import time
from typing import Dict, List, Optional

import asyncpg
import structlog
import zstandard as zstd

from apps.memory_api import metrics
from apps.memory_api.config import settings
from apps.memory_api.services.redis_client import get_redis_client

logger = structlog.get_logger(__name__)

CACHE_TTL_SECONDS = 60 * 60  # 60 minutes
ZSTD_COMPRESSOR = zstd.ZstdCompressor(level=3)
ZSTD_DECOMPRESSOR = zstd.ZstdDecompressor()


async def get_asyncpg_pool():
    # Helper to get a new pool, as this might be called from outside the app context
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )


class ContextCache:
    def __init__(self):
        self.redis_client = get_redis_client()

    def _build_cache_key(self, tenant_id: str, project: str, cache_type: str) -> str:
        return f"rae:{tenant_id}:{project}:{cache_type}:v2"

    def get_context(
        self, tenant_id: str, project: str, cache_type: str
    ) -> Optional[str]:
        cache_key = self._build_cache_key(tenant_id, project, cache_type)
        compressed_data = self.redis_client.get(cache_key)
        if compressed_data:
            metrics.cache_hit_counter.labels(
                tenant_id=tenant_id, project=project, cache_type=cache_type
            ).inc()
            return ZSTD_DECOMPRESSOR.decompress(compressed_data).decode("utf-8")
        metrics.cache_miss_counter.labels(
            tenant_id=tenant_id, project=project, cache_type=cache_type
        ).inc()
        return None

    def set_context(
        self, tenant_id: str, project: str, cache_type: str, data: str
    ) -> None:
        cache_key = self._build_cache_key(tenant_id, project, cache_type)
        compressed_data = ZSTD_COMPRESSOR.compress(data.encode("utf-8"))
        self.redis_client.setex(cache_key, CACHE_TTL_SECONDS, compressed_data)
        metrics.cache_size_gauge.labels(cache_type=cache_type, project=project).set(
            len(compressed_data) / (1024 * 1024)
        )


async def rebuild_full_cache():
    start_time = time.time()
    pool = await get_asyncpg_pool()
    cache = ContextCache()

    # 1. Fetch all semantic and reflective memories
    semantic_records = await pool.fetch(
        "SELECT tenant_id, project, content FROM memories WHERE layer = 'sm'"
    )
    reflective_records = await pool.fetch(
        "SELECT tenant_id, project, content FROM memories WHERE layer = 'rm'"
    )

    # 2. Group by tenant and project
    semantic_blocks: Dict[tuple[str, str], List[str]] = {}
    for r in semantic_records:
        key = (r["tenant_id"], r["project"])
        if key not in semantic_blocks:
            semantic_blocks[key] = []
        semantic_blocks[key].append(r["content"])

    reflective_blocks: Dict[tuple[str, str], List[str]] = {}
    for r in reflective_records:
        key = (r["tenant_id"], r["project"])
        if key not in reflective_blocks:
            reflective_blocks[key] = []
        reflective_blocks[key].append(r["content"])

    # 3. Build and set context for each tenant/project
    all_keys = set(semantic_blocks.keys()) | set(reflective_blocks.keys())
    for tenant_id, project in all_keys:
        semantic_content = "\n".join(semantic_blocks.get((tenant_id, project), []))
        reflective_content = "\n".join(reflective_blocks.get((tenant_id, project), []))

        cache.set_context(tenant_id, project, "semantic", semantic_content)
        cache.set_context(tenant_id, project, "reflective", reflective_content)

    await pool.close()
    duration = time.time() - start_time
    metrics.cache_rebuild_time_gauge.set(duration)
    logger.info("full_cache_rebuilt", duration_seconds=f"{duration:.2f}")


def get_context_cache() -> ContextCache:
    return ContextCache()
