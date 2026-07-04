# RAE API Client

Enhanced Python client for the RAE (Reflective Agentic Memory Engine) API with enterprise-grade resilience patterns.

## Features

### 🔄 Automatic Retry with Exponential Backoff
- Configurable max retries
- Exponential backoff with jitter
- Selective retry based on error category
- Customizable backoff parameters

### 🔌 Circuit Breaker Pattern
- Prevents cascading failures
- Three states: CLOSED, OPEN, HALF_OPEN
- Automatic recovery testing
- Configurable failure thresholds

### 💾 Response Caching
- Automatic caching for GET requests
- TTL-based expiration
- Cache invalidation support
- Significant latency reduction

### 🔗 Connection Pooling
- HTTP/2 support with httpx
- Configurable connection limits
- Keep-alive connections
- Efficient resource usage

### ⏱️ Timeout Handling
- Per-request timeouts
- Stricter timeouts in degraded state
- Prevents hanging requests

### 🏷️ Error Classification
- Network errors
- Timeout errors
- Server errors (5xx)
- Client errors (4xx)
- Rate limiting
- Authentication errors

## Installation

```bash
pip install httpx structlog
```

## Quick Start

### Basic Usage

```python
import asyncio
from apps.memory_api.clients.rae_api import RAEAPIClient

async def main():
    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="your-tenant",
        project_id="your-project"
    ) as client:
        # Create memory
        memory = await client.create_memory(
            content="Machine learning is a subset of AI",
            importance=0.8,
            tags=["ml", "ai"]
        )

        # Search memories
        results = await client.search_memories(
            query="artificial intelligence",
            k=10
        )

        print(f"Found {len(results['results'])} memories")

asyncio.run(main())
```

### Advanced Configuration

```python
async with RAEAPIClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="your-tenant",
    project_id="your-project",

    # Retry configuration
    max_retries=5,
    initial_backoff_ms=200,
    max_backoff_ms=30000,
    backoff_multiplier=2.5,

    # Circuit breaker
    enable_circuit_breaker=True,
    failure_threshold=3,
    success_threshold=2,

    # Caching
    enable_cache=True,
    cache_ttl_seconds=600,

    # Connection pool
    timeout=60.0,
    max_connections=200
) as client:
    # Your code here
    pass
```

## API Methods

### Memory Operations

```python
# Create memory
memory = await client.create_memory(
    content="Content here",
    importance=0.8,
    tags=["tag1", "tag2"]
)

# Get memory
memory = await client.get_memory(memory_id)

# Search memories
results = await client.search_memories(
    query="search query",
    k=10
)
```

### Reflection Operations

```python
# Generate reflection
reflection = await client.generate_reflection(
    memory_ids=[uuid1, uuid2],
    reflection_type="insight"
)

# Get reflection
reflection = await client.get_reflection(reflection_id)

# List reflections
reflections = await client.list_reflections(limit=100)
```

### Semantic Memory Operations

```python
# Extract semantics
extraction = await client.extract_semantics(memory_id=uuid)

# Semantic search
results = await client.semantic_search(
    query="machine learning",
    k=10
)
```

### Graph Operations (GraphRAG)

**Note:** RAE uses GraphRAG for automatic knowledge graph construction.
Manual CRUD operations (`create_graph_node`, `create_graph_edge`, `traverse_graph`)
were never implemented.

```python
# Extract knowledge graph automatically from memories
extraction = await client.extract_knowledge_graph(
    limit=50,
    min_confidence=0.7,
    auto_store=True
)
print(f"Extracted {len(extraction['triples'])} triples")

# Read existing nodes
nodes = await client.get_graph_nodes(limit=20)

# Read existing edges
edges = await client.get_graph_edges(limit=50)

# Hybrid search with graph traversal
results = await client.query_graph(
    query="machine learning optimization",
    top_k_vector=5,
    graph_depth=2
)
```

See `docs/graphrag_guide.md` for details on GraphRAG usage.

### Hybrid Search

```python
# Multi-strategy search
results = await client.hybrid_search(
    query="optimization algorithms",
    k=20,
    weight_profile="quality_focused",
    enable_reranking=True
)

# Analyze query intent
analysis = await client.analyze_query(
    query="how does gradient descent work?"
)
```

### Evaluation Operations

```python
# Evaluate search quality
evaluation = await client.evaluate_search(
    relevance_judgments=judgments,
    search_results=results,
    metrics=["mrr", "ndcg", "precision", "recall"]
)

# Detect drift
drift = await client.detect_drift(
    metric_name="search_score",
    drift_type="data_drift",
    baseline_start=baseline_start,
    baseline_end=baseline_end,
    current_start=current_start,
    current_end=current_end
)
```

### Event Triggers

```python
# Create trigger
trigger = await client.create_trigger(
    rule_name="Auto Reflection",
    event_types=["memory_created"],
    actions=[{
        "action_type": "generate_reflection",
        "config": {}
    }],
    priority=7
)

# Emit event
event = await client.emit_event(
    event_type="quality_degraded",
    payload={"quality_score": 0.65}
)

# List triggers
triggers = await client.list_triggers(limit=100)
```

### Dashboard Operations

```python
# Get metrics
metrics = await client.get_dashboard_metrics(period="last_24h")

# Get visualization
viz = await client.get_visualization(
    visualization_type="semantic_graph",
    limit=50
)

# Check health
health = await client.get_system_health(
    include_sub_components=True
)
```

## Error Handling

```python
from apps.memory_api.clients.rae_client import RAEClientError, ErrorCategory

try:
    result = await client.get_memory(uuid)
except RAEClientError as e:
    if e.category == ErrorCategory.NETWORK:
        print("Network error - check connectivity")
    elif e.category == ErrorCategory.TIMEOUT:
        print("Timeout - server overloaded")
    elif e.category == ErrorCategory.AUTHENTICATION:
        print("Auth error - check API key")
    elif e.category == ErrorCategory.RATE_LIMIT:
        print("Rate limited - back off")
    elif e.category == ErrorCategory.SERVER_ERROR:
        print(f"Server error: {e.message}")
    else:
        print(f"Error: {e.message}")
```

## Monitoring and Statistics

```python
# Get client statistics
stats = client.get_stats()

print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
print(f"Circuit breaker state: {stats['circuit_breaker']['state']}")

# Reset statistics
client.reset_stats()
```

## Cache Management

```python
# Cache is automatic for GET requests

# Invalidate specific cache entry
client.invalidate_cache("GET", "/v1/memories/search")

# Clear entire cache
client.client.cache.clear()

# Cleanup expired entries
client.client.cache.cleanup_expired()
```

## Bulk Operations

```python
# Parallel requests with connection pooling
tasks = [
    client.create_memory(content=f"Memory {i}", importance=0.7)
    for i in range(100)
]

memories = await asyncio.gather(*tasks)
print(f"Created {len(memories)} memories in parallel")
```

## Configuration Best Practices

### Production Settings

```python
client = RAEAPIClient(
    base_url="https://api.production.com",
    api_key=os.environ["RAE_API_KEY"],

    # Aggressive retry for production
    max_retries=5,
    initial_backoff_ms=100,
    max_backoff_ms=30000,

    # Circuit breaker enabled
    enable_circuit_breaker=True,
    failure_threshold=5,

    # Caching enabled
    enable_cache=True,
    cache_ttl_seconds=300,

    # Large connection pool
    max_connections=200,
    timeout=30.0
)
```

### Development Settings

```python
client = RAEAPIClient(
    base_url="http://localhost:8000",

    # Minimal retry for faster feedback
    max_retries=2,
    initial_backoff_ms=50,

    # Circuit breaker disabled for debugging
    enable_circuit_breaker=False,

    # Cache disabled for fresh data
    enable_cache=False,

    # Smaller pool for local dev
    max_connections=20,
    timeout=10.0
)
```

### Testing Settings

```python
client = RAEAPIClient(
    base_url="http://test:8000",

    # No retry for predictable tests
    max_retries=0,

    # Circuit breaker disabled
    enable_circuit_breaker=False,

    # Cache disabled
    enable_cache=False,

    # Short timeout for fast tests
    timeout=5.0
)
```

## Architecture

### Component Overview

```
RAEAPIClient (High-level API)
    ↓
RAEClient (Core client with resilience)
    ↓
├─ CircuitBreaker (Fault tolerance)
├─ ResponseCache (Performance)
└─ httpx.AsyncClient (HTTP/2 connection pool)
```

### Request Flow

```
1. API Method Called (e.g., create_memory)
   ↓
2. Request prepared with headers, auth
   ↓
3. Check cache (GET requests only)
   ↓
4. Circuit Breaker check
   ↓
5. Retry loop with exponential backoff
   ↓
6. HTTP request via connection pool
   ↓
7. Response parsed and cached
   ↓
8. Statistics updated
   ↓
9. Result returned
```

## Examples

See `examples.py` for comprehensive usage examples including:
- Basic operations
- Error handling
- Caching strategies
- Semantic memory workflows
- Evaluation pipelines
- Event triggers
- Dashboard monitoring
- Bulk operations

## License

See main project LICENSE file.
