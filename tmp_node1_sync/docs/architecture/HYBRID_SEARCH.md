# 🔍 RAE Hybrid Search - GraphRAG Multi-Strategy Retrieval

> **Beyond Simple RAG** - Intelligent multi-strategy search combining vector similarity, graph traversal, sparse vectors, and full-text search.

---

## Overview

Traditional RAG systems use only vector similarity. RAE's **Hybrid Search 2.0** combines **four complementary search strategies** into a unified, intelligent retrieval system guided by query analysis and mathematical optimization.

```
┌────────────────────────────────────────────────────────┐
│              HYBRID SEARCH PIPELINE                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│  1. QUERY ANALYSIS (LLM-Powered Intent Classification) │
│     ├─ Intent: factual | conceptual | exploratory |    │
│     │         temporal | relational | aggregative      │
│     ├─ Entity Extraction: ["auth", "payment"]          │
│     ├─ Concept Extraction: ["security", "architecture"]│
│     └─ Dynamic Weight Calculation                      │
│                                                         │
│  2. MULTI-STRATEGY EXECUTION (Parallel)                │
│     ┌─────────────┬─────────────┬─────────────┬───────┴─────┐
│     │ Vector      │ Semantic    │ Graph       │ Full-Text   │
│     │ Search      │ Node Search │ Traversal   │ Search      │
│     │ (Qdrant/PG) │ (Nodes)     │ (BFS)       │ (PostgreSQL)│
│     │ Dense emb.  │ Definitions │ GraphRAG    │ Keywords    │
│     └─────┬───────┴──────┬──────┴──────┬──────┴──────┬──────┘
│           └──────────────┴─────────────┴─────────────┘
│                                                         │
│  3. RESULT FUSION                                       │
│     ├─ Score Normalization (0-1 range)                 │
│     ├─ Weighted Combination (dynamic weights)          │
│     └─ Deduplication                                   │
│                                                         │
│  4. LLM RE-RANKING (Optional)                          │
│     └─ Contextual relevance scoring                    │
│                                                         │
│  5. CACHING LAYER (Redis)                              │
│     └─ Hash-based cache with temporal windowing        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Why Hybrid Search?

### The Problem with Vector-Only Search

```
Query: "authentication bug from last week"

Vector-Only RAG:
  → Embeds query → Finds similar vectors
  → Returns: Generic auth documentation (high similarity)
  → MISSES: Temporal context, keyword precision, connected issues

RAE Hybrid Search:
  1. Query Analyzer: "temporal + technical + keyword-specific"
  2. Vector Search: Semantic similarity to "authentication bug"
  3. Graph Traversal: BFS from "authentication" node → finds related bugs
  4. Sparse Vector: Keyword match "bug" + "authentication"
  5. Full-Text: Exact phrase "last week" + temporal filter
  6. Fusion: Combines all signals → precise results
  → Returns: Exact bug report from last week + related context
```

### The RAE Advantage

| Feature | Traditional RAG | RAE Hybrid Search |
|---------|----------------|-------------------|
| **Semantic matching** | ✅ Vector similarity | ✅ Dense embeddings (Qdrant) |
| **Keyword precision** | ❌ None | ✅ Sparse vectors (BM25-style) |
| **Relational reasoning** | ❌ None | ✅ Graph traversal (GraphRAG) |
| **Exact phrases** | ❌ Poor | ✅ Full-text search (PostgreSQL FTS) |
| **Intent adaptation** | ❌ Static | ✅ LLM-powered query analysis |
| **Cost optimization** | ❌ Manual | ✅ Math-3 policy layer |

---

## 🧩 Component 1: Query Analyzer

> **LLM-Powered Intent Classification** - Understands what the user really wants.

### Purpose

Analyzes queries to determine:
- **Intent type**: Factual? Exploratory? Relational?
- **Key entities**: "authentication", "payment system"
- **Key concepts**: "security", "architecture"
- **Optimal strategy weights**: Vector=0.3, Graph=0.4, Sparse=0.2, FTS=0.1

### 6 Query Intent Types

1. **Factual**: "What is JWT?"
   - **Best strategy**: Semantic nodes + Full-text
   - **Why**: Looking for definitions and facts

2. **Conceptual**: "Explain microservices architecture"
   - **Best strategy**: Vector search + Semantic nodes
   - **Why**: Broad semantic matching needed

3. **Exploratory**: "Tell me about security"
   - **Best strategy**: Vector search + Graph traversal
   - **Why**: Discover related concepts

4. **Temporal**: "What happened last week?"
   - **Best strategy**: Full-text + Temporal filter
   - **Why**: Time-based retrieval

5. **Relational**: "How does auth relate to payments?"
   - **Best strategy**: Graph traversal (GraphRAG)
   - **Why**: Need relationship discovery

6. **Aggregative**: "Summarize all auth bugs"
   - **Best strategy**: Vector + Full-text + Aggregation
   - **Why**: Collect and synthesize multiple memories

### Example

```python
from apps.memory_api.services.query_analyzer import QueryAnalyzer

analyzer = QueryAnalyzer()

analysis = await analyzer.analyze_query(
    query="How does authentication relate to the payment system?",
    context=["Previous conversation context"]
)

print(f"Intent: {analysis.intent}")               # RELATIONAL
print(f"Confidence: {analysis.confidence:.2%}")   # 95%
print(f"Entities: {analysis.key_entities}")       # ["authentication", "payment system"]
print(f"Concepts: {analysis.key_concepts}")       # ["security", "architecture"]
print(f"Weights: {analysis.strategy_weights}")    # {"graph": 0.4, "vector": 0.3, ...}
```

**Code Reference**: [`apps/memory_api/services/query_analyzer.py`](../../apps/memory_api/services/query_analyzer.py)

---

## 🧩 Component 2: Multi-Strategy Search

> **Four Complementary Search Strategies** - Each optimized for different query types.

### Strategy 1: Vector Search (Dense Embeddings)

**Technology**: Qdrant or PostgreSQL pgvector

**How it works**:
1. Embed query using OpenAI, Cohere, or local model
2. Compute cosine similarity with stored embeddings
3. Return top-k most similar memories

**Best for**:
- Semantic similarity
- Paraphrases and synonyms
- Concept matching

**Example**:
```
Query: "How to secure APIs?"
Matches: "API security best practices" (high similarity)
```

**Performance**:
- **Latency**: 20-50ms (with HNSW index)
- **Accuracy**: 0.8-0.9 MRR on semantic queries

---

### Strategy 2: Semantic Node Search

**Technology**: PostgreSQL (semantic_nodes table)

**How it works**:
1. Search semantic nodes (definitions, facts, concepts)
2. Return source memories linked to matching nodes
3. Useful for knowledge lookups

**Best for**:
- Concept definitions
- Factual knowledge retrieval
- Ontology-based queries

**Example**:
```
Query: "What is JWT?"
Matches semantic node: "JWT (JSON Web Token) - RFC 7519"
Returns: All memories referencing JWT
```

---

### Strategy 3: Graph Traversal (GraphRAG)

**Technology**: PostgreSQL (knowledge_graph_nodes + edges)

**How it works**:
1. Find starting nodes matching query entities
2. **BFS traversal** up to max_depth (default: 3)
3. Extract memory_ids from node properties
4. Fetch and return connected memories

**Algorithm**:
```sql
WITH RECURSIVE graph_traversal AS (
    -- Base case: Find starting nodes
    SELECT id, 0 as depth
    FROM knowledge_graph_nodes
    WHERE name ILIKE ANY(ARRAY['%auth%', '%payment%'])

    UNION

    -- Recursive case: Follow edges
    SELECT e.target_id, gt.depth + 1
    FROM graph_traversal gt
    JOIN knowledge_graph_edges e ON gt.id = e.source_id OR gt.id = e.target_id
    WHERE gt.depth < 3  -- max_depth
)
SELECT DISTINCT memory_id FROM graph_traversal;
```

**Best for**:
- **Relationship queries**: "How X relates to Y?"
- **Concept discovery**: "What's connected to authentication?"
- **Causal chains**: "What led to the bug?"

**Example**:
```
Query: "authentication issues affecting payments"
Graph traversal:
  authentication → [bug_fix] → payment_module → [error] → transaction_failure
Returns: All memories in this connection path
```

**Performance**:
- **Latency**: 50-150ms (with proper indexes)
- **Accuracy**: 0.85-0.95 on relational queries

**This is the core of GraphRAG** - discovering connections that pure vector search misses!

---

### Strategy 4: Full-Text Search (Sparse Vectors)

**Technology**: PostgreSQL `to_tsvector` + `plainto_tsquery`

**How it works**:
1. Convert content to text search vector (tsvector)
2. Match query keywords using tsvector similarity
3. Rank by keyword frequency (TF-IDF-like)

**Best for**:
- **Exact keyword matching**: "authentication bug"
- **Rare terms**: Technical jargon, names
- **Phrase matching**: "last week", "version 2.0"

**Example**:
```
Query: "circuit breaker pattern"
Full-text matches: Exact phrase "circuit breaker" in content
Vector search might miss: Matches "fault tolerance" (similar but not exact)
```

**Performance**:
- **Latency**: 10-30ms (with GIN index)
- **Accuracy**: 0.9+ on keyword queries

---

## 🧩 Component 3: Result Fusion

> **Intelligent Score Combination** - Combines results from all strategies into unified ranking.

### Algorithm

1. **Normalize Scores**: Scale each strategy's scores to [0, 1]
   ```python
   normalized_score = (score - min_score) / (max_score - min_score)
   ```

2. **Apply Weights**: Multiply by strategy-specific weights
   ```python
   weighted_score = normalized_score * strategy_weight
   ```

3. **Combine**: Sum weighted scores for each memory
   ```python
   hybrid_score = Σ(weighted_scores across strategies)
   ```

4. **Deduplicate**: Merge duplicate memories across strategies
   ```python
   if memory appears in multiple strategies:
       hybrid_score = sum(all weighted scores)
   ```

5. **Rank**: Sort by final hybrid score

### Example

```
Memory A appears in:
- Vector search: score=0.9 (weight=0.3) → 0.27
- Graph search: score=0.7 (weight=0.4) → 0.28
→ Final hybrid score: 0.55

Memory B appears in:
- Fulltext search: score=0.8 (weight=0.3) → 0.24
→ Final hybrid score: 0.24

Ranking: Memory A (0.55) > Memory B (0.24)
```

---

## 🧩 Component 4: LLM Re-Ranking (Optional)

> **Contextual Relevance** - Uses LLM to re-rank top results for improved precision.

### Purpose

Improves relevance by:
- Understanding query intent in context
- Assessing semantic relevance beyond vector similarity
- Considering user's implicit needs

### Process

1. Take top-K results from hybrid search (default: K=20)
2. Format results with snippets (first 200 chars)
3. Send to LLM (Claude Haiku, GPT-3.5-turbo)
4. LLM assigns relevance scores (0.0-1.0)
5. Combine: **70% LLM score + 30% hybrid score**
6. Re-sort by final score

### When to Use

- ✅ **Use reranking** for complex queries (relational, exploratory)
- ❌ **Skip reranking** for simple factual queries (to save cost)

### Cost-Benefit

- **Cost**: ~$0.001-0.005 per query (with cheap models)
- **Benefit**: +10-20% improvement in MRR (Mean Reciprocal Rank)
- **Latency**: +100-300ms

**Configuration**: Controlled by `enable_reranking` parameter and Math-3 policy.

---

## 🧩 Component 5: Caching Layer

> **High-Performance Redis Cache** - Minimize latency and cost.

### Features

- **Hash-based Keys**: `SHA256(query + tenant + project + filters + time_window)`
- **Temporal Windowing**: Groups similar queries in time windows (60s)
- **Automatic Expiration**: TTL-based eviction (default: 5 minutes)
- **LRU Eviction**: Least Recently Used eviction when cache full
- **Statistics Tracking**: Hit rate, cache size, evictions

### Configuration

```python
from apps.memory_api.services.hybrid_cache import HybridSearchCache

cache = HybridSearchCache(
    default_ttl_seconds=300,      # 5 minutes
    window_size_seconds=60,       # 1 minute window
    max_cache_size=1000           # Max 1000 entries
)
```

### Cache Statistics

```python
stats = cache.get_statistics()
# {
#     "cache_size": 234,
#     "hits": 1523,
#     "misses": 456,
#     "hit_rate": 0.769,
#     "hit_rate_percent": "76.90%"
# }
```

### Performance Impact

- **Cold query**: 200-500ms (database + embedding + LLM)
- **Cached query**: 5-15ms (Redis retrieval)
- **Cost savings**: 90%+ (skip LLM calls, embeddings, DB queries)

---

## 🎯 Complete Usage Example

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

# Returns HybridSearchResult:
print(f"Found {len(result.results)} results in {result.total_time_ms}ms")
print(f"Query intent: {result.query_analysis.intent}")
print(f"Applied weights: {result.applied_weights}")

for item in result.results:
    print(f"  [{item.hybrid_score:.3f}] {item.content[:100]}...")
```

### Advanced Search with Filters

```python
from datetime import datetime, timedelta

result = await search_service.search(
    tenant_id="my-tenant",
    project_id="my-project",
    query="recent security issues",
    k=5,
    temporal_filter=datetime.now() - timedelta(days=7),  # Last 7 days
    tag_filter=["security", "bug"],                      # Must have these tags
    min_importance=0.5,                                  # Only important memories
    graph_max_depth=2,                                   # Limit graph traversal
    bypass_cache=False                                   # Use cache if available
)
```

### Manual Weight Override

```python
# Override automatic weight calculation (for power users)
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

---

## 📊 Performance Optimization

### 1. Database Indexes

**Critical indexes for performance**:

```sql
-- Vector search (pgvector)
CREATE INDEX idx_memories_embedding_ivfflat
ON memories USING ivfflat (embedding vector_cosine_ops);

-- OR for better accuracy (Qdrant-style):
CREATE INDEX idx_memories_embedding_hnsw
ON memories USING hnsw (embedding vector_cosine_ops);

-- Graph traversal
CREATE INDEX idx_kg_edges_source ON knowledge_graph_edges(source_id);
CREATE INDEX idx_kg_edges_target ON knowledge_graph_edges(target_id);
CREATE INDEX idx_kg_nodes_name ON knowledge_graph_nodes(name);

-- Full-text search
CREATE INDEX idx_memories_fts ON memories USING GIN (to_tsvector('english', content));

-- Filtering
CREATE INDEX idx_memories_tenant_project ON memories(tenant_id, project_id);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_importance ON memories(importance DESC);
```

### 2. Parallel Execution

All strategies execute **concurrently** using asyncio:

```python
async def search(self, query, ...):
    tasks = [
        self._vector_search(query, k),
        self._semantic_search(query, k),
        self._graph_search(query, k, max_depth),
        self._fulltext_search(query, k)
    ]
    results = await asyncio.gather(*tasks)
    return self._fuse_results(results)
```

**Result**: 4× faster than sequential execution!

### 3. Caching Strategy

- **Cache Hit**: 5-15ms (95%+ faster)
- **Cache Miss**: 200-500ms (normal DB query)
- **Target Hit Rate**: 70-80% (typical for production)

---

## 🔧 Configuration

### Environment Variables

```bash
# Caching
HYBRID_SEARCH_CACHE_ENABLED=true
HYBRID_SEARCH_CACHE_TTL=300
HYBRID_SEARCH_CACHE_SIZE=1000
HYBRID_SEARCH_CACHE_WINDOW=60

# Default search parameters
HYBRID_SEARCH_DEFAULT_K=10
HYBRID_SEARCH_GRAPH_MAX_DEPTH=3
HYBRID_SEARCH_ENABLE_RERANKING=true

# LLM re-ranking
HYBRID_SEARCH_RERANKING_MODEL="claude-3-haiku-20240307"
HYBRID_SEARCH_RERANKING_COST_THRESHOLD=0.01
```

---

## 📈 Monitoring & Metrics

### Key Metrics (Prometheus)

```python
# Latency
hybrid_search_query_analysis_duration_seconds
hybrid_search_search_duration_seconds
hybrid_search_reranking_duration_seconds
hybrid_search_total_duration_seconds

# Strategy distribution
hybrid_search_strategy_results_total{strategy="vector"}
hybrid_search_strategy_results_total{strategy="graph"}
hybrid_search_strategy_results_total{strategy="sparse"}
hybrid_search_strategy_results_total{strategy="fulltext"}

# Cache performance
hybrid_search_cache_hits_total
hybrid_search_cache_misses_total
hybrid_search_cache_hit_rate
```

### Grafana Dashboard

Pre-built dashboard includes:
- **Query latency** (P50, P95, P99)
- **Cache hit rate** over time
- **Strategy usage distribution** (pie chart)
- **Query intent distribution** (bar chart)
- **LLM re-ranking cost** tracking

**Location**: [`infra/grafana/dashboards/hybrid-search.json`](../../infra/grafana/dashboards/)

---

## 🧪 Testing & Benchmarking

### Unit Tests

```bash
# Test individual strategies
pytest apps/memory_api/tests/services/test_hybrid_search_service.py::test_vector_search
pytest apps/memory_api/tests/services/test_hybrid_search_service.py::test_graph_search

# Test result fusion
pytest apps/memory_api/tests/services/test_hybrid_search_service.py::test_result_fusion

# Test caching
pytest apps/memory_api/tests/services/test_hybrid_cache.py
```

### Benchmarks

```bash
# Run hybrid search benchmark
make benchmark-extended

# Metrics measured:
# - MRR (Mean Reciprocal Rank): 0.84
# - Hit Rate @5: 91.4%
# - Precision @k: 0.78
# - Avg Latency: 45ms (P95: 78ms)
```

**See**: [Benchmarking Guide](../../benchmarking/README.md)

---

## 📚 Related Documentation

- **[Memory Layers](./MEMORY_LAYERS.md)** - 4-layer cognitive architecture
- **[Math Layers](./MATH_LAYERS.md)** - Decision intelligence layer
- **[Query Analyzer](../reference/services/query_analyzer.md)** - Intent classification
- **[GraphRAG Implementation](../reference/concepts/graphrag.md)** - Knowledge graph details
- **[Caching Strategy](../reference/concepts/caching.md)** - Redis cache implementation

---

## 🔬 Implementation Status

| Component | Status | Tests | Coverage |
|-----------|--------|-------|----------|
| **Query Analyzer** | ✅ Complete | 28 tests | 92% |
| **Vector Search** | ✅ Complete | 45 tests | 88% |
| **Semantic Search** | ✅ Complete | 22 tests | 85% |
| **Graph Traversal** | ✅ Complete | 38 tests | 90% |
| **Full-Text Search** | ✅ Complete | 18 tests | 87% |
| **Result Fusion** | ✅ Complete | 35 tests | 94% |
| **LLM Re-Ranking** | ✅ Complete | 15 tests | 82% |
| **Caching Layer** | ✅ Complete | 42 tests | 95% |

**Total**: 243 tests, 89% average coverage

**Code Location**: [`apps/memory_api/services/`](../../apps/memory_api/services/)

---

**Version**: 2.1.0
**Last Updated**: 2025-12-08
**Status**: Production Ready ✅

**See also**: [Main README](../../README.md) | [Architecture Overview](../reference/concepts/architecture.md)
