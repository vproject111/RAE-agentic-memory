# Hybrid Search 2.0 - GraphRAG Implementation

## Overview

Hybrid Search 2.0 is RAE's advanced multi-strategy search system that combines vector similarity, semantic knowledge, graph traversal, and full-text search into a unified, intelligent search experience.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Hybrid Search Pipeline                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. Query Analysis (LLM-powered)                    │
│     ├─ Intent Classification (6 types)              │
│     ├─ Entity Extraction                            │
│     ├─ Concept Extraction                           │
│     └─ Dynamic Weight Calculation                   │
│                                                      │
│  2. Multi-Strategy Execution (Parallel)             │
│     ├─ Vector Search (pgvector/Qdrant)             │
│     ├─ Semantic Node Search                         │
│     ├─ Graph Traversal (BFS, GraphRAG)             │
│     └─ Full-Text Search (PostgreSQL FTS)            │
│                                                      │
│  3. Result Fusion                                    │
│     ├─ Score Normalization                          │
│     ├─ Weighted Combination                         │
│     └─ Deduplication                                │
│                                                      │
│  4. LLM Re-ranking (Optional)                       │
│     └─ Contextual relevance scoring                 │
│                                                      │
│  5. Caching Layer                                    │
│     └─ Hash-based cache with temporal windowing     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. Query Analyzer (`query_analyzer.py`)

**Purpose**: Analyzes user queries to determine optimal search strategies.

**Key Features**:
- **Intent Classification**: 6 query types (factual, conceptual, exploratory, temporal, relational, aggregative)
- **Entity Extraction**: Identifies key entities in the query
- **Concept Extraction**: Extracts abstract concepts
- **Dynamic Weighting**: Calculates optimal weights for each search strategy

**Example**:
```python
from apps.memory_api.services.query_analyzer import QueryAnalyzer

analyzer = QueryAnalyzer()

analysis = await analyzer.analyze_query(
    query="How does authentication relate to the payment system?",
    context=["Previous conversation context"]
)

# Returns:
# QueryAnalysis(
#     intent=QueryIntent.RELATIONAL,
#     confidence=0.95,
#     key_entities=["authentication", "payment system"],
#     key_concepts=["security", "architecture"],
#     recommended_strategies=[SearchStrategy.GRAPH, SearchStrategy.SEMANTIC],
#     strategy_weights={"vector": 0.2, "semantic": 0.3, "graph": 0.4, "fulltext": 0.1}
# )
```

### 2. Hybrid Search Service (`hybrid_search_service.py`)

**Purpose**: Orchestrates multi-strategy search execution.

**Search Strategies**:

#### Vector Search
- Uses embedding similarity (cosine distance)
- Best for: Semantic similarity, paraphrases, concept matching
- Backend: pgvector or Qdrant

#### Semantic Search
- Searches semantic nodes (definitions, facts)
- Best for: Concept lookups, knowledge retrieval
- Returns: Source memories linked to semantic nodes

#### Graph Search (GraphRAG)
- Traverses knowledge graph using BFS
- Discovers connected memories through entity relationships
- Best for: Relationship queries, connected concepts
- **Implementation**: Recursive CTE for efficient graph traversal

**Key Feature - Graph Traversal**:
```python
# Graph search implementation uses:
# 1. Find starting nodes matching query entities
# 2. BFS traversal up to max_depth
# 3. Extract memory_ids from node properties
# 4. Fetch and return connected memories

# Supports bidirectional traversal:
# - Follows edges in both directions
# - Discovers all connected memories
# - Configurable max depth (default: 3)
```

#### Full-Text Search
- PostgreSQL full-text search
- Best for: Exact keyword matching
- Uses: `to_tsvector` and `plainto_tsquery`

### 3. Hybrid Cache (`hybrid_cache.py`)

**Purpose**: High-performance caching layer for search results.

**Features**:
- **Hash-based Keys**: `SHA256(query + tenant + project + filters + time_window)`
- **Temporal Windowing**: Groups queries in time windows (default: 60s)
- **Automatic Expiration**: Configurable TTL (default: 5 minutes)
- **LRU Eviction**: Evicts oldest entries when cache is full
- **Statistics**: Track hit rate, cache size, evictions

**Configuration**:
```python
cache = HybridSearchCache(
    default_ttl_seconds=300,      # 5 minutes
    window_size_seconds=60,       # 1 minute window
    max_cache_size=1000           # Max 1000 entries
)
```

**Cache Statistics**:
```python
stats = cache.get_statistics()
# Returns:
# {
#     "cache_size": 234,
#     "hits": 1523,
#     "misses": 456,
#     "hit_rate": 0.769,
#     "hit_rate_percent": "76.90%"
# }
```

### 4. Result Fusion

**Purpose**: Combines results from multiple strategies into a unified ranking.

**Algorithm**:
1. **Normalize Scores**: Scale each strategy's scores to 0-1 range
2. **Apply Weights**: Multiply by strategy-specific weights
3. **Combine**: Sum weighted scores for each memory
4. **Deduplicate**: Merge duplicate memories across strategies
5. **Rank**: Sort by final hybrid score

**Example**:
```
Memory A appears in:
- Vector search: score=0.9 (weight=0.3) → 0.27
- Graph search: score=0.7 (weight=0.4) → 0.28
Final hybrid score: 0.55

Memory B appears in:
- Fulltext search: score=0.8 (weight=0.3) → 0.24
Final hybrid score: 0.24

Ranking: Memory A > Memory B
```

### 5. LLM Re-ranking

**Purpose**: Contextual re-ranking using LLMs for improved relevance.

**Models Supported**:
- Claude (Haiku, Sonnet, Opus)
- OpenAI GPT (3.5, 4)
- Custom models

**Process**:
1. Format top-K results with snippets
2. Send to LLM with query and results
3. LLM assigns relevance scores (0.0-1.0)
4. Combine with hybrid scores (70% LLM + 30% hybrid)
5. Re-sort by final score

## API Usage

### Basic Search

```python
from apps.memory_api.services.hybrid_search_service import HybridSearchService

search_service = HybridSearchService(pool=db_pool)

result = await search_service.search(
    tenant_id="my-tenant",
    project_id="my-project",
    query="authentication best practices",
    k=10,
    enable_vector=True,
    enable_semantic=True,
    enable_graph=True,
    enable_fulltext=True,
    enable_reranking=True
)

# Returns: HybridSearchResult with:
# - results: List[SearchResultItem]
# - query_analysis: QueryAnalysis
# - vector_results_count, semantic_results_count, etc.
# - total_time_ms, search_time_ms, reranking_time_ms
# - applied_weights: Dict[str, float]
```

### Advanced Search with Filters

```python
from datetime import datetime, timedelta

result = await search_service.search(
    tenant_id="my-tenant",
    project_id="my-project",
    query="recent security issues",
    k=5,
    temporal_filter=datetime.now() - timedelta(days=7),
    tag_filter=["security", "bug"],
    min_importance=0.5,
    graph_max_depth=2,
    bypass_cache=False
)
```

### Manual Weight Override

```python
# Override automatic weight calculation
result = await search_service.search(
    tenant_id="my-tenant",
    project_id="my-project",
    query="system architecture",
    k=10,
    manual_weights={
        "vector": 0.1,
        "semantic": 0.2,
        "graph": 0.6,  # Emphasize graph search
        "fulltext": 0.1
    }
)
```

## Performance Optimization

### 1. Caching Strategy
- **Cache Enabled**: First query hits database, subsequent queries served from cache
- **TTL**: Balance between freshness and performance (default: 5 minutes)
- **Invalidation**: Clear cache on memory updates via `cache.invalidate(tenant_id, project_id)`

### 2. Parallel Execution
- All search strategies execute concurrently
- PostgreSQL connection pooling
- Async/await for I/O-bound operations

### 3. Query Optimization
- **Vector Search**: Index on `embedding` column with `ivfflat` or `hnsw`
- **Graph Traversal**: Recursive CTE with proper indexes on `knowledge_graph_edges`
- **Full-Text**: GIN index on `to_tsvector(content)`

## Configuration

### Environment Variables

```bash
# Enable/disable caching
HYBRID_SEARCH_CACHE_ENABLED=true
HYBRID_SEARCH_CACHE_TTL=300
HYBRID_SEARCH_CACHE_SIZE=1000

# Default search parameters
HYBRID_SEARCH_DEFAULT_K=10
HYBRID_SEARCH_GRAPH_MAX_DEPTH=3
HYBRID_SEARCH_ENABLE_RERANKING=true
```

## Monitoring & Metrics

### Key Metrics
- **Query Analysis Time**: Time spent analyzing query (LLM call)
- **Search Time**: Time for parallel strategy execution
- **Reranking Time**: Time for LLM re-ranking (if enabled)
- **Total Time**: End-to-end search latency
- **Cache Hit Rate**: Percentage of requests served from cache
- **Strategy Distribution**: Which strategies returned results

### Logging

```python
# Structured logging with structlog
logger.info(
    "hybrid_search_complete",
    results=10,
    total_time=245,
    cache_hit=False,
    strategies_used=["vector", "graph"],
    hit_rate=0.78
)
```

## Best Practices

1. **Enable Caching in Production**: Significantly reduces latency and cost
2. **Use Re-ranking Selectively**: Adds latency but improves relevance for critical queries
3. **Tune Graph Depth**: Lower depth (1-2) for performance, higher (3-5) for discovery
4. **Monitor Cache Hit Rate**: Low hit rate may indicate cache size or TTL issues
5. **Profile Slow Queries**: Use `EXPLAIN ANALYZE` for query optimization

## Troubleshooting

### Slow Queries
- Check graph traversal depth
- Verify database indexes
- Profile with `total_time_ms` breakdown

### Low Cache Hit Rate
- Increase cache size
- Increase TTL
- Check query variation (exact string match required)

### Poor Relevance
- Enable re-ranking
- Adjust strategy weights
- Review query analysis intent classification

## Future Enhancements

- [ ] Redis-based distributed cache
- [ ] Query result pagination
- [ ] Negative filters (exclude terms)
- [ ] Faceted search
- [ ] Query suggestions
- [ ] Personalized ranking based on user history
