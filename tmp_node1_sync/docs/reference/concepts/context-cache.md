# Context Cache

RAE's Context Cache is an intelligent caching system that dramatically reduces LLM API costs and improves response times by caching frequently accessed context and embeddings.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Caching Strategies](#caching-strategies)
- [Compression](#compression)
- [Cache Invalidation](#cache-invalidation)
- [Performance Impact](#performance-impact)
- [Configuration](#configuration)
- [Best Practices](#best-practices)

## Overview

### Why Caching Matters

LLM API costs are primarily driven by:
1. **Token count** (both input and output)
2. **Number of API calls**

Context caching addresses both by:
- Storing pre-computed embeddings
- Caching semantic and reflective memories
- Reusing context across requests
- Compressing data for efficient storage

### Cost Savings

**Without caching:**
```
Query → Generate embedding → Vector search → LLM call
Each query: $0.001 embedding + $0.01 LLM = $0.011
1000 queries/day = $11/day = $330/month
```

**With caching:**
```
Query → Check cache → (hit) Return cached → No LLM call
Cache hit rate: 80%
200 queries hit API: $2.20
800 queries from cache: $0
Total: $2.20/day = $66/month (80% savings!)
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Query Request                       │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│            Check Redis Cache                         │
│  Key: rae:{tenant}:{project}:{type}:v2              │
└─────────────────┬───────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    Cache HIT         Cache MISS
         │                 │
         ▼                 ▼
┌──────────────┐   ┌──────────────────┐
│ Decompress   │   │ Query Database   │
│ Return Data  │   │ Generate Context │
└──────────────┘   │ Compress         │
                   │ Store in Cache   │
                   │ Return Data      │
                   └──────────────────┘
```

### Cache Layers

RAE implements multi-level caching:

**Layer 1: Application Memory (L1)**
- In-process LRU cache
- Ultra-fast (nanoseconds)
- Limited size (~100MB)
- Short TTL (5 minutes)

**Layer 2: Redis (L2)**
- Distributed cache
- Fast (milliseconds)
- Configurable size (GBs)
- Medium TTL (60 minutes)

**Layer 3: Database (L3)**
- Persistent storage
- Slower (10-100ms)
- Unlimited size
- No TTL

## Caching Strategies

### 1. Context Caching

Cache semantic and reflective memories per tenant/project:

```python
class ContextCache:
    def _build_cache_key(self, tenant_id: str, project: str, cache_type: str) -> str:
        return f"rae:{tenant_id}:{project}:{cache_type}:v2"

    def get_context(self, tenant_id: str, project: str, cache_type: str) -> Optional[str]:
        """
        Retrieve cached context
        Returns: Decompressed context string or None
        """
        cache_key = self._build_cache_key(tenant_id, project, cache_type)
        compressed_data = self.redis_client.get(cache_key)

        if compressed_data:
            # Cache HIT
            metrics.cache_hit_counter.inc()
            return decompress(compressed_data)

        # Cache MISS
        metrics.cache_miss_counter.inc()
        return None

    def set_context(self, tenant_id: str, project: str, cache_type: str, data: str):
        """
        Store context in cache with compression
        """
        cache_key = self._build_cache_key(tenant_id, project, cache_type)
        compressed_data = compress(data)
        self.redis_client.setex(cache_key, CACHE_TTL_SECONDS, compressed_data)
```

### 2. Embedding Caching

Cache generated embeddings by content hash:

```python
import hashlib

def get_embedding_cached(text: str) -> List[float]:
    """
    Get embedding from cache or generate and cache it
    """
    # Create content hash
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    cache_key = f"embedding:{content_hash}"

    # Check cache
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Generate embedding
    embedding = embedding_service.generate(text)

    # Cache for 24 hours
    redis.setex(cache_key, 86400, json.dumps(embedding))

    return embedding
```

### 3. Query Result Caching

Cache query results for identical queries:

```python
def cache_query_results(query_hash: str, results: List[dict]):
    """
    Cache search results
    """
    cache_key = f"query_results:{query_hash}"
    redis.setex(cache_key, 300, json.dumps(results))  # 5 min TTL
```

### 4. LLM Response Caching

Cache LLM responses for deterministic prompts:

```python
def get_reflection_cached(memories: List[str]) -> str:
    """
    Cache reflection generation results
    """
    # Hash input memories
    input_hash = hashlib.sha256(
        "|".join(sorted(memories)).encode()
    ).hexdigest()

    cache_key = f"reflection:{input_hash}"

    # Check cache
    cached = redis.get(cache_key)
    if cached:
        return cached.decode()

    # Generate reflection
    reflection = llm.generate_reflection(memories)

    # Cache for 1 hour
    redis.setex(cache_key, 3600, reflection.encode())

    return reflection
```

## Compression

RAE uses **Zstandard (zstd)** compression to minimize Redis memory usage:

### Why Zstandard?

- **Fast**: Compression/decompression in microseconds
- **High ratio**: 2-5x compression for text data
- **Low CPU**: Minimal overhead
- **Streaming**: Supports large data

### Implementation

```python
import zstandard as zstd

# Initialize compressor (level 3 = balanced speed/ratio)
ZSTD_COMPRESSOR = zstd.ZstdCompressor(level=3)
ZSTD_DECOMPRESSOR = zstd.ZstdDecompressor()

def compress(data: str) -> bytes:
    """
    Compress string data using zstd
    """
    return ZSTD_COMPRESSOR.compress(data.encode('utf-8'))

def decompress(compressed: bytes) -> str:
    """
    Decompress zstd data to string
    """
    return ZSTD_DECOMPRESSOR.decompress(compressed).decode('utf-8')
```

### Compression Benchmarks

```
Example: 10KB semantic memory context

Uncompressed: 10,240 bytes
Compressed:    2,560 bytes (75% reduction)

Compression time:   0.5 ms
Decompression time: 0.3 ms

Cost savings:
- 75% less Redis memory
- 75% less network transfer
- Faster Redis operations (less data)
```

## Cache Invalidation

### Time-based Invalidation (TTL)

```python
# Default TTLs
CACHE_TTL_SECONDS = {
    "context": 3600,      # 1 hour
    "embedding": 86400,   # 24 hours
    "query": 300,         # 5 minutes
    "reflection": 3600,   # 1 hour
}
```

### Event-based Invalidation

Invalidate cache when data changes:

```python
async def store_memory(memory: Memory):
    """
    Store memory and invalidate related caches
    """
    # Store in database
    await db.insert(memory)

    # Invalidate context cache
    cache_key = f"rae:{memory.tenant_id}:{memory.project_id}:semantic:v2"
    await redis.delete(cache_key)

    # Invalidate query result caches for this project
    pattern = f"query_results:{memory.tenant_id}:{memory.project_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
```

### Manual Cache Rebuild

Force cache rebuild via API:

```bash
# Rebuild all caches
curl -X POST http://localhost:8000/v1/cache/rebuild \
  -H "X-API-Key: your-key"
```

```python
async def rebuild_full_cache():
    """
    Rebuild entire context cache from database
    """
    # Fetch all semantic and reflective memories
    semantic_records = await db.fetch(
        "SELECT tenant_id, project, content FROM memories WHERE layer = 'sm'"
    )
    reflective_records = await db.fetch(
        "SELECT tenant_id, project, content FROM memories WHERE layer = 'rm'"
    )

    # Group by tenant/project
    groups = defaultdict(lambda: {"semantic": [], "reflective": []})

    for record in semantic_records:
        key = (record['tenant_id'], record['project'])
        groups[key]["semantic"].append(record['content'])

    for record in reflective_records:
        key = (record['tenant_id'], record['project'])
        groups[key]["reflective"].append(record['content'])

    # Build and cache
    for (tenant_id, project), data in groups.items():
        semantic_context = "\n".join(data["semantic"])
        reflective_context = "\n".join(data["reflective"])

        cache.set_context(tenant_id, project, 'semantic', semantic_context)
        cache.set_context(tenant_id, project, 'reflective', reflective_context)
```

## Performance Impact

### Latency Improvement

```
Without cache:
- Embedding generation: 50-200ms
- LLM call: 1000-3000ms
- Total: 1050-3200ms

With cache (hit):
- Redis lookup: 1-5ms
- Decompression: 0.5ms
- Total: 1.5-5.5ms

Speed up: 200-600x faster! 🚀
```

### Throughput Improvement

```
Without cache:
- Max 10-20 req/sec (limited by LLM API)

With cache (80% hit rate):
- 80% served from cache: ~1000 req/sec
- 20% hit API: ~4 req/sec
- Combined: ~200 req/sec

Throughput: 10-20x improvement
```

### Cost Reduction

```
Monthly costs (1M requests):

Without cache:
- Embeddings: 1M × $0.0001 = $100
- LLM calls: 1M × $0.01 = $10,000
- Total: $10,100

With cache (80% hit rate):
- Embeddings: 200K × $0.0001 = $20
- LLM calls: 200K × $0.01 = $2,000
- Redis: $50/month
- Total: $2,070

Savings: $8,030/month (79% reduction)
```

## Configuration

### Environment Variables

```env
# Redis configuration
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Cache TTLs (seconds)
CACHE_TTL_CONTEXT=3600
CACHE_TTL_EMBEDDING=86400
CACHE_TTL_QUERY=300

# Compression
CACHE_COMPRESSION_ENABLED=true
CACHE_COMPRESSION_LEVEL=3  # 1-22, higher = more compression

# Cache size limits
REDIS_MAX_MEMORY=2gb
REDIS_EVICTION_POLICY=allkeys-lru  # Evict least recently used
```

### Redis Configuration

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru

# Enable persistence (optional)
save 900 1
save 300 10
save 60 10000

# Network
bind 0.0.0.0
protected-mode yes
requirepass your-redis-password
```

## Best Practices

### 1. Cache Hot Data

Identify and cache frequently accessed data:

```sql
-- Find most queried projects
SELECT tenant_id, project_id, COUNT(*) as query_count
FROM query_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY tenant_id, project_id
ORDER BY query_count DESC
LIMIT 100;
```

Pre-warm cache for these projects:
```bash
for project in hot_projects:
    curl -X POST /v1/cache/rebuild?project=${project}
```

### 2. Monitor Cache Hit Rate

Target: **> 70% hit rate**

```python
# Prometheus metrics
cache_hit_rate = cache_hits / (cache_hits + cache_misses)

if cache_hit_rate < 0.7:
    # Increase TTL
    # Pre-warm more data
    # Review cache keys (too specific?)
```

### 3. Use Appropriate TTLs

```python
TTL_GUIDELINES = {
    "static_data": 86400,      # 24h (rarely changes)
    "user_preferences": 3600,  # 1h (changes occasionally)
    "search_results": 300,     # 5min (changes frequently)
    "real_time_data": 60,      # 1min (changes constantly)
}
```

### 4. Implement Cache Warming

Pre-populate cache during low-traffic periods:

```python
# Celery scheduled task
@celery.task
def warm_cache_daily():
    """
    Run at 2 AM daily to warm cache
    """
    active_tenants = get_active_tenants(days=7)

    for tenant in active_tenants:
        rebuild_cache_for_tenant(tenant.id)
```

### 5. Handle Cache Stampede

Prevent multiple simultaneous cache misses:

```python
import asyncio

async def get_with_lock(key: str, generator_fn):
    """
    Prevent cache stampede with distributed lock
    """
    cached = await redis.get(key)
    if cached:
        return cached

    # Acquire lock
    lock_key = f"{key}:lock"
    lock_acquired = await redis.set(lock_key, "1", ex=10, nx=True)

    if lock_acquired:
        # Generate and cache
        result = await generator_fn()
        await redis.setex(key, 3600, result)
        await redis.delete(lock_key)
        return result
    else:
        # Wait for other process to finish
        await asyncio.sleep(0.1)
        return await get_with_lock(key, generator_fn)
```

### 6. Monitor Redis Memory

```bash
# Check Redis memory usage
redis-cli INFO memory

# Key distribution
redis-cli --bigkeys

# Memory by key pattern
redis-cli --memkeys-samples 100000
```

### 7. Use Cache Tags for Bulk Invalidation

```python
def tag_cache_key(tenant_id: str, tags: List[str]):
    """
    Associate cache keys with tags for bulk invalidation
    """
    for tag in tags:
        tag_key = f"cache_tag:{tag}"
        redis.sadd(tag_key, cache_key)

def invalidate_by_tag(tag: str):
    """
    Invalidate all cache entries with given tag
    """
    tag_key = f"cache_tag:{tag}"
    keys = redis.smembers(tag_key)
    if keys:
        redis.delete(*keys)
        redis.delete(tag_key)
```

## Monitoring

### Key Metrics

```prometheus
# Cache hit rate
rae_cache_hit_rate = rae_cache_hits / (rae_cache_hits + rae_cache_misses)

# Cache memory usage
rae_cache_memory_bytes{type="redis"}

# Cache operation latency
rae_cache_operation_duration_seconds{operation="get|set"}

# Cost savings
rae_cache_cost_saved_usd = (cache_hits * avg_llm_cost)
```

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Cache Hit Rate",
      "targets": ["rae_cache_hit_rate"],
      "thresholds": [0.5, 0.7]
    },
    {
      "title": "Cost Savings",
      "targets": ["rae_cache_cost_saved_usd"]
    }
  ]
}
```

## Further Reading

- [Cost Controller](cost-controller.md) - Budget management
- [Architecture](architecture.md) - System design
- [Performance Tuning](../guides/performance-tuning.md) - Optimization tips
