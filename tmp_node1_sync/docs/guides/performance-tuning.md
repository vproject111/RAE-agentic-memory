# Performance Tuning Guide

Optimize RAE for production workloads.

## Database Optimization

### Indexes
```sql
-- Add indexes for common queries
CREATE INDEX idx_memories_tenant_time ON memories(tenant_id, timestamp DESC);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX idx_memories_layer ON memories(tenant_id, layer);

-- Vector index (pgvector)
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

### Connection Pooling
```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

### Query Optimization
```python
# Use EXPLAIN ANALYZE
EXPLAIN ANALYZE 
SELECT * FROM memories 
WHERE tenant_id = '...' 
AND timestamp > NOW() - INTERVAL '7 days';
```

## Redis Caching

### Configuration
```env
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

### Cache Strategy
```python
# Cache embeddings (24h TTL)
@cache(ttl=86400)
async def get_embedding(text: str):
    ...

# Cache query results (1h TTL)
@cache(ttl=3600)
async def query_memory(query: str):
    ...
```

## Vector Store Optimization

### Qdrant Settings
```yaml
# qdrant-config.yaml
service:
  max_request_size_mb: 32
  max_workers: 4

storage:
  performance:
    max_search_threads: 4
```

### Collection Configuration
```python
# Optimize for search speed
collection_config = {
    "vectors": {
        "size": 1536,
        "distance": "Cosine"
    },
    "hnsw_config": {
        "m": 16,
        "ef_construct": 100
    }
}
```

## Application Tuning

### Async Workers
```env
# Increase Celery workers
CELERY_WORKERS=4
CELERY_CONCURRENCY=2
```

### Batch Operations
```python
# Batch store memories
async def store_batch(memories: List[Memory]):
    await db.executemany(INSERT_QUERY, memories)
```

### Pagination
```python
# Use cursor-based pagination
async def get_memories_paginated(
    cursor: str = None,
    limit: int = 50
):
    ...
```

## Monitoring

### Key Metrics
- Query latency (p50, p95, p99)
- Database connection pool utilization
- Cache hit rate
- Vector search time

### Tools
- Prometheus + Grafana
- pg_stat_statements (PostgreSQL)
- Redis INFO command

## Load Testing

```bash
# Using Locust
locust -f load_test.py --host=http://localhost:8000
```

See [Production Deployment](production-deployment.md) for infrastructure scaling.
