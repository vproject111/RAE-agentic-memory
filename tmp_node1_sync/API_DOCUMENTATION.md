# RAE API Documentation

Complete API reference for RAE Memory Engine v2.0 Enterprise

**Base URL:** `http://localhost:8000` (default)
**Format:** REST API, JSON
**Authentication:** API Key (Bearer token) or X-Tenant-ID header

---

## Quick Navigation

| Module | Endpoints | Description |
|--------|-----------|-------------|
| [Memory API](#memory-api) | 6 | Core memory storage and retrieval operations |
| [Agent API](#agent-api) | 1 | Agent orchestration and execution |
| [Graph API](#graph-api) | 7 | Knowledge graph operations (GraphRAG) |
| [Cache API](#cache-api) | 1 | Context cache management |
| [Governance API](#governance-api) | 3 | Cost tracking and budget management |
| [Event Triggers API](#event-triggers-api) | 18 | Event-driven automation with triggers and actions |
| [Reflections API](#reflections-api) | 8 | Hierarchical reflection system with clustering |
| [Hybrid Search API](#hybrid-search-api) | 10 | Multi-strategy search with dynamic weighting |
| [Evaluation API](#evaluation-api) | 12 | Search quality metrics and drift detection |
| [Dashboard API](#dashboard-api) | 7 | Real-time monitoring and visualizations |
| [Graph Management API](#graph-management-api) | 19 | Advanced graph operations and analytics |
| [Health API](#health-api) | 4 | Health checks and system metrics |
| [Feedback API](#feedback-api) | 1 | RLHF feedback submission |
| [Compliance API](#compliance-api) | 12 | ISO 42001 governance and approvals |
| [Control Plane API](#control-plane-api) | 7 | Distributed compute node management |
| [Metrics API](#metrics-api) | 2 | Token savings and additional metrics |

**Total:** 118 enterprise-ready endpoints

---

## Authentication

All requests require authentication via one of:

### API Key (Recommended)
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/v1/memories
```

### Tenant Header
```bash
curl -H "X-Tenant-ID: your-tenant-id" \
     -H "X-Project-ID: your-project-id" \
     http://localhost:8000/v1/memories
```

---

## Memory API

Base path: `/v1/memory`

The Memory API provides core memory storage, retrieval, and management operations. It supports hybrid search combining vector similarity with knowledge graph traversal.

**Memory Lifecycle & Decay:**

All memory retrievals automatically track access statistics:
- **`last_accessed_at`**: Updated to current UTC timestamp on every retrieval
- **`usage_count`**: Incremented on every retrieval

These statistics power the **importance scoring system**, which calculates dynamic importance based on:
- Recency (when created)
- Access frequency (how often used)
- Graph centrality (knowledge graph position)
- Semantic relevance (similarity to recent queries)
- User ratings, consolidation status, and manual adjustments

**Temporal Decay:**
- Memories decay over time based on access patterns
- Recently accessed memories (< 7 days): Decay slower
- Normal memories (7-30 days): Standard decay rate
- Stale memories (30+ days): Accelerated decay

For configuration and implementation details, see:
- [Configuration Guide](docs/configuration.md#memory-decay--importance-scoring)
- [Architecture Documentation](docs/architecture.md#memory-lifecycle--governance)

---

### Store Memory

Store a new memory record in the system.

```http
POST /v1/memory/store
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "content": "User prefers dark mode in the application",
  "source": "user_preference",
  "importance": 0.8,
  "layer": "em",
  "tags": ["preference", "ui"],
  "project": "project-1",
  "timestamp": "2025-11-22T10:00:00Z"
}
```

**Memory Layers:**
- `em` - Episodic Memory (events, interactions)
- `sm` - Semantic Memory (facts, knowledge)
- `rm` - Reflective Memory (insights, patterns)

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### List Memories

List memories with pagination support.

```http
GET /v1/memory/list?limit=50&offset=0
X-Tenant-Id: tenant-1
```

**Query Parameters:**
- `limit` (default: 50) - Number of records to return
- `offset` (default: 0) - Pagination offset
- `project` (optional) - Filter by project ID
- `layer` (optional) - Filter by memory layer (e.g., `episodic`, `semantic`)

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "content": "User prefers dark mode",
      "source": "user_preference",
      "importance": 0.8,
      "layer": "episodic",
      "project": "project-1",
      "timestamp": "2025-11-22T10:00:00Z"
    }
  ],
  "total": 50,
  "limit": 50,
  "offset": 0
}
```

---

### Query Memory

Query memories using vector search or hybrid search with graph traversal (GraphRAG).

**Standard Vector Search:**
```http
POST /v1/memory/query
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "query_text": "user interface preferences",
  "k": 10,
  "project": "project-1",
  "use_graph": false,
  "filters": {
    "tags": ["preference"]
  }
}
```

**Hybrid Search with GraphRAG:**

When `use_graph: true` is specified, the query endpoint performs **hybrid search** combining vector similarity with knowledge graph traversal. This provides richer, more contextual results by:

1. Performing vector search to find semantically similar memories
2. Mapping results to knowledge graph entities
3. Traversing the graph to discover related entities and relationships
4. Synthesizing comprehensive context from all sources

```http
POST /v1/memory/query
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "query_text": "machine learning concepts",
  "k": 5,
  "project": "project-1",
  "use_graph": true,
  "graph_depth": 2
}
```

**GraphRAG Parameters:**
- `use_graph` (default: false) - Enable hybrid search with graph traversal
- `graph_depth` (default: 2, max: 5) - Maximum depth for graph traversal
- `project` (required when use_graph=true) - Project identifier for graph context

**Note:** For advanced graph operations (extraction, statistics, subgraph queries), see the [Graph API](#graph-api) section below.

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "score": 0.92,
      "content": "User prefers dark mode",
      "source": "user_preference",
      "importance": 0.8,
      "layer": "em",
      "tags": ["preference", "ui"],
      "timestamp": "2025-11-22T10:00:00Z",
      "last_accessed_at": "2025-11-23T14:30:00Z",
      "usage_count": 5,
      "project": "project-1"
    }
  ],
  "synthesized_context": "Context from graph traversal...",
  "graph_statistics": {
    "nodes_traversed": 15,
    "edges_traversed": 20
  }
}
```

---

### Delete Memory

Delete a memory record by ID.

```http
DELETE /v1/memory/delete?memory_id={memory_id}
X-Tenant-Id: tenant-1
```

**Response:**
```json
{
  "message": "Memory 550e8400-e29b-41d4-a716-446655440000 deleted successfully."
}
```

---

### Rebuild Reflections

Trigger background task to rebuild reflective memories for a project.

```http
POST /v1/memory/rebuild-reflections
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "project-1"
}
```

**Response (202 Accepted):**
```json
{
  "message": "Reflection rebuild task dispatched for project project-1."
}
```

---

### Get Reflection Statistics

Get statistics about reflective memories in a project.

```http
GET /v1/memory/reflection-stats?project=project-1
X-Tenant-Id: tenant-1
```

**Response:**
```json
{
  "reflective_memory_count": 42,
  "average_strength": 0.75
}
```

---

### Generate Hierarchical Reflection

Generate hierarchical (map-reduce) summarization of episodic memories.

This enterprise endpoint handles large numbers of episodes by recursively summarizing them using a map-reduce pattern, scaling to thousands of episodes without hitting context limits.

```http
POST /v1/memory/reflection/hierarchical?project=project-1&bucket_size=10
X-Tenant-Id: tenant-1
```

**Query Parameters:**
- `project` (required) - Project identifier
- `bucket_size` (optional, default: 10) - Number of episodes per bucket
- `max_episodes` (optional) - Maximum episodes to process

**Response:**
```json
{
  "summary": "Comprehensive hierarchical summary of all episodes...",
  "statistics": {
    "project": "project-1",
    "tenant_id": "tenant-1",
    "episode_count": 150,
    "bucket_size": 10,
    "max_episodes_processed": 150,
    "summary_length": 2500
  }
}
```

---

## Agent API

Base path: `/v1/agent`

The Agent API provides orchestrated AI agent execution with memory retrieval, context caching, reranking, and cost tracking.

### Execute Agent Task

Execute an AI agent task with full memory retrieval and context management.

This enterprise endpoint orchestrates:
1. Retrieval of pre-built semantic & reflective context from cache
2. Vector search for episodic memories
3. Reranking of retrieved memories
4. LLM inference with full context
5. Automatic reflection generation
6. Cost tracking and governance

```http
POST /v1/agent/execute
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "tenant_id": "tenant-1",
  "project": "project-1",
  "prompt": "What are the user's preferences for the dashboard layout?"
}
```

**Response:**
```json
{
  "answer": "Based on the user's interactions, they prefer a dark mode interface with a minimalist layout...",
  "used_memories": {
    "results": [
      {
        "id": "uuid",
        "score": 0.95,
        "content": "User prefers dark mode",
        "source": "user_preference",
        "importance": 0.8,
        "layer": "em",
        "tags": ["preference", "ui"],
        "timestamp": "2025-11-22T10:00:00Z",
        "last_accessed_at": "2025-11-23T14:30:00Z",
        "usage_count": 5,
        "project": "project-1"
      }
    ]
  },
  "cost": {
    "input_tokens": 1250,
    "output_tokens": 180,
    "total_estimate": 0.0245
  }
}
```

**Features:**
- **Context Caching:** Leverages pre-built semantic and reflective context for cost savings
- **Hybrid Retrieval:** Combines vector search with reranking for optimal results
- **Automatic Reflection:** Stores agent interactions as reflective memories
- **Cost Tracking:** Full token and cost breakdown per request
- **Governance:** Budget enforcement and cost guard middleware

---

## Graph API

Base path: `/v1/graph`

The Graph API provides GraphRAG (Graph-Augmented Retrieval) capabilities for knowledge graph extraction, querying, and analysis. It automatically builds knowledge graphs from episodic memories and enables advanced graph-based retrieval.

**Note:** For full conceptual guide, see `docs/graphrag_guide.md`

### Extract Knowledge Graph

Extract knowledge graph from episodic memories using LLM-powered entity and relationship extraction.

```http
POST /v1/graph/extract
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "project_id": "project-1",
  "limit": 50,
  "min_confidence": 0.5,
  "auto_store": true
}
```

**Response:**
```json
{
  "triples": [
    {
      "subject": "User",
      "predicate": "prefers",
      "object": "dark mode",
      "confidence": 0.92,
      "source_memory_id": "uuid"
    }
  ],
  "entities": ["User", "dark mode", "interface"],
  "statistics": {
    "memories_processed": 50,
    "triples_extracted": 35,
    "unique_entities": 18
  }
}
```

---

### Generate Hierarchical Reflection

Generate hierarchical (map-reduce) reflection from large episode collections.

```http
POST /v1/graph/reflection/hierarchical
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "project_id": "project-1",
  "bucket_size": 10,
  "max_episodes": 100
}
```

**Response:**
```json
{
  "project_id": "project-1",
  "summary": "Comprehensive hierarchical summary...",
  "episodes_processed": 100
}
```

---

### Get Graph Statistics

Get comprehensive statistics about the knowledge graph.

```http
GET /v1/graph/stats?project_id=project-1
X-Tenant-Id: tenant-1
```

**Response:**
```json
{
  "project_id": "project-1",
  "tenant_id": "tenant-1",
  "total_nodes": 247,
  "total_edges": 412,
  "unique_relations": ["prefers", "relates_to", "is_part_of", "depends_on"],
  "statistics": {
    "avg_edges_per_node": 1.67,
    "total_relation_types": 4
  }
}
```

---

### Get Graph Nodes

Retrieve graph nodes with optional PageRank filtering for large graphs.

```http
GET /v1/graph/nodes?project_id=project-1&limit=100&use_pagerank=true&min_pagerank_score=0.01
X-Tenant-Id: tenant-1
```

**Query Parameters:**
- `project_id` (required) - Project identifier
- `limit` (default: 100) - Maximum nodes to return
- `use_pagerank` (default: false) - Enable PageRank filtering
- `min_pagerank_score` (default: 0.0) - Minimum PageRank threshold

**Response:**
```json
[
  {
    "id": "uuid",
    "node_id": "entity_123",
    "label": "Machine Learning",
    "properties": {
      "pagerank_score": 0.045,
      "type": "concept"
    },
    "created_at": "2025-11-22T10:00:00Z"
  }
]
```

---

### Get Graph Edges

Retrieve graph edges with optional filtering by relation type.

```http
GET /v1/graph/edges?project_id=project-1&limit=100&relation=prefers
X-Tenant-Id: tenant-1
```

**Query Parameters:**
- `project_id` (required) - Project identifier
- `limit` (default: 100) - Maximum edges to return
- `relation` (optional) - Filter by relation type

**Response:**
```json
[
  {
    "id": "uuid",
    "source_node_id": "uuid1",
    "target_node_id": "uuid2",
    "relation": "prefers",
    "properties": {
      "confidence": 0.92
    },
    "created_at": "2025-11-22T10:00:00Z"
  }
]
```

---

### Query Knowledge Graph

Advanced hybrid search combining vector retrieval with graph traversal.

```http
POST /v1/graph/query
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "query": "machine learning optimization techniques",
  "project_id": "project-1",
  "top_k_vector": 5,
  "graph_depth": 2,
  "traversal_strategy": "bfs"
}
```

**Traversal Strategies:**
- `bfs` - Breadth-First Search (explores nearby entities first)
- `dfs` - Depth-First Search (explores deep relationships)

**Response:**
```json
{
  "vector_matches": [
    {
      "id": "uuid",
      "score": 0.92,
      "content": "Gradient descent optimization...",
      "layer": "em"
    }
  ],
  "graph_nodes": [
    {
      "id": "uuid",
      "label": "gradient descent"
    }
  ],
  "graph_edges": [
    {
      "source_id": "uuid1",
      "target_id": "uuid2",
      "relation": "optimizes"
    }
  ],
  "synthesized_context": "Based on the retrieved memories and graph traversal...",
  "statistics": {
    "vector_results": 5,
    "nodes_traversed": 15,
    "edges_traversed": 22,
    "traversal_depth_reached": 2
  }
}
```

---

### Get Subgraph

Retrieve a subgraph starting from specific nodes.

```http
GET /v1/graph/subgraph?project_id=project-1&node_ids=uuid1,uuid2&depth=2
X-Tenant-Id: tenant-1
```

**Query Parameters:**
- `project_id` (required) - Project identifier
- `node_ids` (required) - Comma-separated node IDs
- `depth` (default: 1) - Maximum traversal depth

**Response:**
```json
{
  "nodes": [
    {
      "id": "uuid",
      "node_id": "entity_123",
      "label": "Machine Learning",
      "properties": {},
      "created_at": "2025-11-22T10:00:00Z"
    }
  ],
  "edges": [
    {
      "id": "uuid",
      "source_node_id": "uuid1",
      "target_node_id": "uuid2",
      "relation": "relates_to",
      "properties": {},
      "created_at": "2025-11-22T10:00:00Z"
    }
  ],
  "statistics": {
    "start_nodes": 2,
    "depth": 2,
    "nodes_found": 15,
    "edges_found": 22
  }
}
```

---

## Cache API

Base path: `/v1/cache`

The Cache API manages the context cache system, which pre-builds and stores semantic and reflective memory contexts for cost optimization in agent execution.

### Rebuild Context Cache

Trigger a background task to rebuild the entire context cache.

This operation:
- Scans all tenants and projects
- Rebuilds semantic memory contexts
- Rebuilds reflective memory contexts
- Updates Redis cache entries

Use this after:
- Bulk memory imports
- Database migrations
- Major schema changes
- Cache corruption

```http
POST /v1/cache/rebuild
```

**Response (202 Accepted):**
```json
{
  "message": "Cache rebuild task dispatched."
}
```

**Note:** This is an asynchronous operation. The cache will be rebuilt in the background via Celery worker. Monitor logs or use metrics endpoints to track progress.

---

## Governance API

Base path: `/v1/governance`

The Governance API provides enterprise-grade cost tracking, budget management, and usage analytics for multi-tenant deployments.

### Get System Overview

Get system-wide cost overview across all tenants (admin only).

```http
GET /v1/governance/overview?days=30
```

**Query Parameters:**
- `days` (default: 30) - Number of days to analyze

**Response:**
```json
{
  "total_cost_usd": 1247.50,
  "total_calls": 15420,
  "total_tokens": 8925000,
  "unique_tenants": 12,
  "period_start": "2025-10-23T00:00:00Z",
  "period_end": "2025-11-23T00:00:00Z",
  "top_tenants": [
    {
      "tenant_id": "tenant-1",
      "calls": 5240,
      "cost_usd": 425.30,
      "tokens": 2850000
    }
  ],
  "top_models": [
    {
      "model": "claude-3-5-sonnet-20241022",
      "calls": 8920,
      "cost_usd": 892.40,
      "tokens": 5420000
    }
  ]
}
```

---

### Get Tenant Statistics

Get comprehensive governance statistics for a specific tenant.

```http
GET /v1/governance/tenant/{tenant_id}?days=30
```

**Query Parameters:**
- `days` (default: 30) - Number of days to analyze

**Response:**
```json
{
  "tenant_id": "tenant-1",
  "total_cost_usd": 425.30,
  "total_calls": 5240,
  "total_tokens": 2850000,
  "average_cost_per_call": 0.081,
  "cache_hit_rate": 0.35,
  "cache_savings_usd": 148.85,
  "period_start": "2025-10-23T00:00:00Z",
  "period_end": "2025-11-23T00:00:00Z",
  "by_project": [
    {
      "project_id": "project-1",
      "calls": 3200,
      "cost_usd": 258.40,
      "tokens": 1740000
    }
  ],
  "by_model": [
    {
      "model": "claude-3-5-sonnet-20241022",
      "calls": 4100,
      "cost_usd": 328.00,
      "tokens": 2100000
    }
  ],
  "by_operation": [
    {
      "operation": "agent_execute",
      "calls": 4200,
      "cost_usd": 360.50,
      "tokens": 2400000
    }
  ]
}
```

**Key Metrics:**
- **cache_hit_rate:** Percentage of requests using cached context (0.0 - 1.0)
- **cache_savings_usd:** Estimated cost savings from context caching
- **by_project:** Cost breakdown by project
- **by_model:** Usage breakdown by LLM model
- **by_operation:** Cost breakdown by operation type

---

### Get Tenant Budget Status

Get current budget status and projections for a tenant.

```http
GET /v1/governance/tenant/{tenant_id}/budget
```

**Response:**
```json
{
  "tenant_id": "tenant-1",
  "budget_usd_monthly": 500.00,
  "budget_tokens_monthly": 5000000,
  "current_month_cost_usd": 425.30,
  "current_month_tokens": 2850000,
  "budget_used_percent": 85.06,
  "days_remaining": 7,
  "projected_month_end_cost": 512.85,
  "alerts": [
    "Warning: 75% of budget used ($425.30 / $500.00)",
    "Projected to exceed budget: $512.85 estimated by month end"
  ],
  "status": "WARNING"
}
```

**Status Levels:**
- **OK:** Under 75% of budget
- **WARNING:** 75-90% of budget used, or projected to exceed
- **CRITICAL:** 90-100% of budget used
- **EXCEEDED:** Budget limit reached

**Features:**
- Real-time budget monitoring
- Projection based on daily average spend
- Multi-level alert system
- Token and cost budget tracking

---

## Health API

The Health API provides comprehensive health checks for all system components, designed for Kubernetes probes, monitoring systems, and observability.

### Health Check

Comprehensive health check of all system components.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T14:30:00Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12.5,
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 3.2,
      "message": "Redis connection successful",
      "details": {
        "version": "7.0.12",
        "used_memory_mb": 245.8,
        "connected_clients": 5
      }
    },
    "vector_store": {
      "status": "healthy",
      "response_time_ms": 8.7,
      "message": "Vector store connection successful",
      "details": {
        "version": "1.7.0",
        "title": "qdrant"
      }
    }
  }
}
```

**Overall Status:**
- **healthy:** All components working normally
- **degraded:** Some non-critical components have issues
- **unhealthy:** Critical components are failing

---

### Readiness Probe

Kubernetes readiness probe endpoint.

```http
GET /health/ready
```

**Response (200 OK):**
```json
{
  "status": "ready"
}
```

**Use Case:** Kubernetes readiness probes to determine if the service can accept traffic.

---

### Liveness Probe

Kubernetes liveness probe endpoint.

```http
GET /health/live
```

**Response (200 OK):**
```json
{
  "status": "alive",
  "timestamp": "2025-11-23T14:30:00Z"
}
```

**Use Case:** Kubernetes liveness probes to detect if the service needs to be restarted.

---

### System Metrics

Get detailed system metrics for monitoring and observability.

```http
GET /metrics
```

**Response:**
```json
{
  "timestamp": "2025-11-23T14:30:00Z",
  "uptime_seconds": 345620.5,
  "memory_usage_mb": 512.4,
  "database": {},
  "redis": {
    "used_memory_mb": 245.8,
    "connected_clients": 5,
    "total_commands": 1547920
  },
  "vector_store": {}
}
```

**Note:** This endpoint also exposes Prometheus metrics at `/metrics` in Prometheus format for scraping.

---

## Event Triggers API

Base path: `/v1/triggers`

The Event Triggers API enables event-driven automation with complex condition evaluation and action execution. Build sophisticated workflows that respond to system events automatically.

### Create Trigger

Create a new event trigger rule.

```http
POST /v1/triggers/create
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "tenant_id": "tenant-1",
  "project": "production",
  "rule_name": "auto_reflection_on_memory_threshold",
  "event_types": ["memory_created"],
  "conditions": {
    "type": "and",
    "conditions": [
      {
        "field": "memory_count",
        "operator": "gt",
        "value": 100
      }
    ]
  },
  "actions": [
    {
      "type": "generate_reflection",
      "config": {
        "max_memories": 100
      }
    }
  ],
  "enabled": true,
  "rate_limit": {
    "max_executions": 10,
    "window_seconds": 3600
  }
}
```

**Response:** `201 Created`

### Other Trigger Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/triggers/{trigger_id}` | Get trigger by ID |
| PUT | `/v1/triggers/{trigger_id}` | Update trigger |
| DELETE | `/v1/triggers/{trigger_id}` | Delete trigger |
| POST | `/v1/triggers/{trigger_id}/enable` | Enable trigger |
| POST | `/v1/triggers/{trigger_id}/disable` | Disable trigger |
| GET | `/v1/triggers/list` | List all triggers |

### Event Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/triggers/events/emit` | Emit custom event |
| GET | `/v1/triggers/events/types` | Get supported event types |
| POST | `/v1/triggers/executions` | Get trigger execution history |

### Workflow Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/triggers/workflows/create` | Create workflow |
| GET | `/v1/triggers/workflows/{workflow_id}` | Get workflow |
| GET | `/v1/triggers/workflows` | List workflows |

### Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/triggers/templates` | Get trigger templates |
| GET | `/v1/triggers/templates/{template_id}` | Get template by ID |
| POST | `/v1/triggers/templates/instantiate` | Create trigger from template |

**Event Types:**
- `memory_created`, `memory_updated`, `memory_deleted`
- `reflection_generated`, `reflection_failed`
- `budget_exceeded`, `budget_warning`
- `drift_detected`, `quality_degraded`
- `graph_updated`, `cache_invalidated`

**Condition Operators:** `equals`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex`, `in`, `not_in`, `between`, `exists`, `not_exists`

**Action Types:** `webhook`, `notification`, `generate_reflection`, `rebuild_cache`, `create_snapshot`, `run_evaluation`, `execute_workflow`

---

## Reflections API

Base path: `/v1/reflections`

The Reflections API provides hierarchical reflection generation with automatic clustering, insight extraction, and relationship management.

### Generate Reflections

Generate reflections from memories using clustering pipeline.

```http
POST /v1/reflections/generate
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "tenant_id": "tenant-1",
  "project": "production",
  "max_memories": 100,
  "min_cluster_size": 5,
  "enable_clustering": true,
  "clustering_method": "hdbscan",
  "generate_meta_insights": true,
  "since": "2025-01-01T00:00:00Z"
}
```

**Returns:** Generated reflections with scoring and metadata.

**Clustering Methods:**
- `hdbscan` - Density-based clustering (automatic cluster count)
- `kmeans` - K-means clustering (requires n_clusters)

### Query Reflections

Search reflections by semantic similarity or filters.

```http
POST /v1/reflections/query
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "production",
  "query": "What patterns emerged in user behavior?",
  "top_k": 10,
  "reflection_type": "insight",
  "min_score": 0.7
}
```

### Other Reflection Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/reflections/{reflection_id}` | Get reflection by ID |
| GET | `/v1/reflections/{reflection_id}/children` | Get child reflections |
| POST | `/v1/reflections/graph` | Get reflection graph |
| POST | `/v1/reflections/relationships` | Create reflection relationship |
| GET | `/v1/reflections/statistics/{tenant_id}/{project}` | Get statistics |
| DELETE | `/v1/reflections/batch` | Batch delete reflections |

**Reflection Types:** `insight`, `meta_insight`, `pattern`, `summary`, `conclusion`

---

## Hybrid Search API

Base path: `/v1/search`

The Hybrid Search API provides multi-strategy search with dynamic weighting, query analysis, and result fusion.

### Hybrid Search

Execute hybrid multi-strategy search.

```http
POST /v1/search/hybrid
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project_id": "production",
  "query": "authentication system architecture",
  "k": 20,
  "enable_vector_search": true,
  "enable_semantic_search": true,
  "enable_graph_search": true,
  "enable_fulltext_search": true,
  "enable_reranking": true,
  "reranking_model": "claude-3-5-sonnet-20241022",
  "graph_max_depth": 3,
  "temporal_filter": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-12-31T23:59:59Z"
  }
}
```

**Features:**
- Automatic query intent classification
- Dynamic weight calculation
- Multi-strategy result fusion
- Optional LLM re-ranking

### Query Analysis

Analyze query intent and get recommended weights.

```http
POST /v1/search/analyze
Content-Type: application/json

{
  "query": "how does the authentication work?",
  "conversation_history": []
}
```

**Response:** Query classification and recommended strategy weights.

### Other Search Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/search/analyze/explain` | Get detailed query analysis |
| GET | `/v1/search/weights/profiles` | Get weight profiles |
| GET | `/v1/search/weights/profiles/{profile_name}` | Get specific profile |
| POST | `/v1/search/weights/calculate` | Calculate dynamic weights |
| POST | `/v1/search/compare` | Compare search strategies |
| POST | `/v1/search/test/weights` | Test custom weights |

**Weight Profiles:** `balanced`, `quality`, `speed`, `comprehensive`, `exploratory`

**Query Intents:** `factual`, `conceptual`, `navigational`, `procedural`, `exploratory`, `relational`

---

## Evaluation API

Base path: `/v1/evaluation`

The Evaluation API provides search quality metrics, drift detection, A/B testing, and quality monitoring.

### Evaluate Search Quality

Evaluate search results using IR metrics.

```http
POST /v1/evaluation/search
Content-Type: application/json

{
  "results": [
    {"memory_id": "mem1", "score": 0.95},
    {"memory_id": "mem2", "score": 0.85}
  ],
  "ground_truth": ["mem1", "mem3", "mem2"],
  "metrics": ["mrr", "ndcg", "precision", "recall"]
}
```

**Supported Metrics:**
- **MRR** (Mean Reciprocal Rank)
- **NDCG@K** (Normalized Discounted Cumulative Gain)
- **Precision@K**
- **Recall@K**
- **MAP** (Mean Average Precision)

### Drift Detection

Detect semantic drift in memory quality.

```http
POST /v1/evaluation/drift/detect
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "production",
  "baseline_start": "2025-01-01T00:00:00Z",
  "baseline_end": "2025-01-31T23:59:59Z",
  "current_start": "2025-11-01T00:00:00Z",
  "current_end": "2025-11-25T23:59:59Z",
  "feature": "importance_scores",
  "test": "ks"
}
```

**Drift Tests:**
- **KS** (Kolmogorov-Smirnov Test)
- **PSI** (Population Stability Index)
- **Chi-Square Test**

**Severity Levels:** `none`, `low`, `medium`, `high`, `critical`

### Other Evaluation Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/evaluation/metrics/supported` | Get supported metrics |
| GET | `/v1/evaluation/drift/severity-levels` | Get severity levels |
| POST | `/v1/evaluation/ab-test/create` | Create A/B test |
| POST | `/v1/evaluation/ab-test/{test_id}/compare` | Compare variants |
| POST | `/v1/evaluation/quality/metrics` | Get quality metrics |
| GET | `/v1/evaluation/quality/thresholds` | Get quality thresholds |
| POST | `/v1/evaluation/benchmark/run` | Run benchmark |
| GET | `/v1/evaluation/benchmark/suites` | Get benchmark suites |

---

## Dashboard API

Base path: `/v1/dashboard`

The Dashboard API provides real-time metrics, visualizations, system health, and activity monitoring.

### Get Dashboard Metrics

Get comprehensive dashboard metrics.

```http
POST /v1/dashboard/metrics
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "production",
  "time_range": "24h",
  "metrics": ["memory_count", "query_count", "cache_hit_rate"]
}
```

**Available Metrics:**
- `memory_count`, `memory_growth_rate`
- `query_count`, `query_latency`
- `cache_hit_rate`, `cache_size`
- `graph_node_count`, `graph_edge_count`
- `reflection_count`, `api_calls`
- `cost_total`, `cost_by_model`

### Get System Health

Get system health status with recommendations.

```http
POST /v1/dashboard/health
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "include_recommendations": true
}
```

**Health Components:**
- Database connectivity
- Cache availability
- Vector store status
- ML service health
- Budget status
- Memory quality

### Other Dashboard Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/dashboard/metrics/timeseries/{metric_name}` | Get time series data |
| POST | `/v1/dashboard/visualizations` | Get visualization data |
| GET | `/v1/dashboard/health/simple` | Simple health check |
| GET | `/v1/dashboard/activity` | Get recent activity |

**Time Ranges:** `1h`, `6h`, `24h`, `7d`, `30d`, `90d`

**Visualization Types:** `reflection_tree`, `semantic_graph`, `timeline`, `quality_trends`, `cost_breakdown`, `performance_heatmap`

---

## Graph Management API

Base path: `/v1/graph-management`

The Graph Management API provides advanced graph operations including temporal graphs, snapshots, traversal algorithms, and batch operations.

### Create Node

Create an enhanced graph node with metrics.

```http
POST /v1/graph/manage/nodes
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "production",
  "node_type": "entity",
  "name": "authentication_module",
  "properties": {
    "category": "code",
    "language": "python"
  }
}
```

**Response:** `201 Created` with node details including centrality metrics.

### Create Edge

Create weighted, temporal graph edge.

```http
POST /v1/graph/manage/edges
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "production",
  "source_node_id": "node-1",
  "target_node_id": "node-2",
  "edge_type": "depends_on",
  "weight": 0.85,
  "valid_from": "2025-01-01T00:00:00Z",
  "valid_to": "2025-12-31T23:59:59Z",
  "properties": {
    "strength": "strong"
  }
}
```

### Traverse Graph

Execute graph traversal with algorithm selection.

```http
POST /v1/graph/manage/traverse
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "production",
  "start_node_id": "node-1",
  "algorithm": "bfs",
  "max_depth": 3,
  "filters": {
    "edge_types": ["related_to", "depends_on"],
    "min_weight": 0.5
  }
}
```

**Algorithms:** `bfs` (Breadth-First Search), `dfs` (Depth-First Search), `dijkstra` (Shortest Path)

### Graph Snapshots

Create and restore point-in-time graph snapshots.

```http
POST /v1/graph/manage/snapshots
Content-Type: application/json

{
  "tenant_id": "tenant-1",
  "project": "production",
  "snapshot_name": "pre_refactor_snapshot",
  "description": "Graph state before major refactoring"
}
```

**Snapshot Operations:**
- `POST /v1/graph/manage/snapshots` - Create snapshot
- `GET /v1/graph/manage/snapshots/{snapshot_id}` - Get snapshot
- `GET /v1/graph/manage/snapshots` - List snapshots
- `POST /v1/graph/manage/snapshots/{snapshot_id}/restore` - Restore snapshot

### Other Graph Management Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/graph/manage/nodes/{node_id}/metrics` | Get node centrality metrics |
| POST | `/v1/graph/manage/nodes/connected` | Find connected nodes |
| PUT | `/v1/graph/manage/edges/{edge_id}/weight` | Update edge weight |
| POST | `/v1/graph/manage/edges/{edge_id}/deactivate` | Deactivate edge |
| POST | `/v1/graph/manage/edges/{edge_id}/activate` | Activate edge |
| PUT | `/v1/graph/manage/edges/{edge_id}/temporal` | Update temporal validity |
| POST | `/v1/graph/manage/path/shortest` | Find shortest path |
| POST | `/v1/graph/manage/cycles/detect` | Detect cycles |
| POST | `/v1/graph/manage/statistics` | Get graph statistics |
| POST | `/v1/graph/manage/nodes/batch` | Batch node operations |
| POST | `/v1/graph/manage/edges/batch` | Batch edge operations |

**Centrality Metrics:** `degree`, `betweenness`, `closeness`, `eigenvector`, `pagerank`

**Graph Statistics:** Node count, edge count, density, diameter, clustering coefficient, component analysis

---

## Feedback API

Base path: `/v1/feedback`

Submit feedback for retrieved memories to support Reinforcement Learning from Human Feedback (RLHF) and dynamic importance adjustment.

### Submit Feedback

```http
POST /v1/feedback
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "feedback_type": "positive",
  "comment": "This memory was highly relevant to the context."
}
```

**Feedback Types:** `positive`, `negative`, `neutral`

**Response:**
```json
{
  "status": "success",
  "message": "Feedback recorded"
}
```

---

## ISO/IEC 42001 Compliance API

Base path: `/v1/compliance`

Comprehensive AI governance API for managing human approvals, decision provenance, and circuit breakers.

### Human Approvals

Request and manage human oversight for high-risk operations.

**Request Approval:**
```http
POST /v1/compliance/approvals
Content-Type: application/json
X-Tenant-Id: tenant-1

{
  "project_id": "project-1",
  "operation_type": "delete_memory",
  "operation_description": "Bulk deletion of user data",
  "risk_level": "high",
  "resource_type": "memory",
  "resource_id": "all",
  "requested_by": "user-123"
}
```

**Check Status:** `GET /v1/compliance/approvals/{request_id}`
**Decide:** `POST /v1/compliance/approvals/{request_id}/decide`

### Circuit Breakers

Monitor and reset system protection mechanisms.

**List All:** `GET /v1/compliance/circuit-breakers` (Admin only)
**Reset:** `POST /v1/compliance/circuit-breakers/{name}/reset` (Admin only)

---

## Control Plane API

Base path: `/control`

Manages distributed compute nodes for offloading heavy tasks (embeddings, LLM inference).

### Register Node

Register a new compute node to the cluster.

```http
POST /control/nodes/register
Content-Type: application/json

{
  "node_id": "node-gpu-01",
  "api_key": "secret-node-key",
  "capabilities": ["embedding", "llm"]
}
```

### Task Delegation

**Create Task:** `POST /control/tasks`
**Poll for Tasks:** `GET /control/tasks_poll?node_id={node_id}`
**Submit Result:** `POST /control/tasks/{task_id}/result`

---

## Metrics API

Base path: `/metrics`

Additional system metrics and savings analysis.

### Token Savings

Get analysis of tokens saved via context caching.

```http
GET /metrics/savings?period=30d
```

---

## Future / Planned APIs

The following APIs are planned for future releases:

### Not Currently Available

- **Semantic Memory API** (`/v1/semantic`) - Dedicated entity extraction and semantic node management
- **MCP Enhanced API** (`/v1/mcp`) - Model Context Protocol enhancements
- **Multi-modal Memory API** (`/v1/multimodal`) - Support for images, audio, and video memories
- **Collaboration API** (`/v1/collaborate`) - Real-time multi-user collaboration features
- **Plugin System API** (`/v1/plugins`) - Custom plugin registration and management

**Implementation Status:** These APIs are part of the product roadmap. Current v2.0 Enterprise release includes 96 production-ready endpoints.

---

## Error Responses

All endpoints follow a consistent error format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-11-22T10:00:00Z",
  "request_id": "uuid"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## Rate Limiting

Default rate limits:
- **Anonymous:** 100 requests/hour
- **Authenticated:** 1000 requests/hour
- **Enterprise:** 10000 requests/hour

Headers returned:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1701000000
```

---

## Pagination

List endpoints support pagination:

```http
GET /v1/memories?limit=50&offset=100
```

Response includes pagination metadata:
```json
{
  "results": [...],
  "total_count": 1000,
  "limit": 50,
  "offset": 100,
  "has_more": true
}
```

---

## Interactive Documentation

**Swagger UI:** http://localhost:8000/docs
**ReDoc:** http://localhost:8000/redoc

---

## SDK Usage

### Python SDK

```python
from rae_memory_sdk import RAEClient

client = RAEClient(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="tenant-1",
    project_id="project-1"
)

# Store a memory
memory_id = await client.store(
    content="User prefers dark mode",
    importance=0.8,
    layer="em",
    tags=["preference", "ui"]
)

# Query memories (vector search)
results = await client.query(
    query_text="user preferences",
    k=10
)

# Query with graph traversal (hybrid search)
results = await client.query(
    query_text="machine learning concepts",
    k=5,
    use_graph=True,
    graph_depth=2
)

# Delete a memory
await client.delete(memory_id=memory_id)
```

**Available SDK Methods:**
- `store()` / `store_async()` - Store memories
- `query()` / `query_async()` - Query memories (supports hybrid search)
- `delete()` / `delete_async()` - Delete memories

**Note:** GraphRAG and Agent execution methods are planned for future SDK releases. Currently, use direct API calls for these features.

See [sdk/python/rae_memory_sdk/README.md](sdk/python/rae_memory_sdk/README.md) for full SDK documentation.

---

## Examples

Complete examples in [apps/memory_api/clients/examples.py](apps/memory_api/clients/examples.py)

---

**API Version:** v2.0 Enterprise
**Last Updated:** 2025-11-25
**Implemented Endpoints:** 96
**Status:** Production Ready ✅

---

## Summary of Changes

This documentation now accurately reflects the **complete** RAE Memory API v2.0 Enterprise endpoints:

### ✅ Implemented APIs (96 endpoints)

**Core APIs:**
- **Memory API** (6 endpoints) - `/v1/memory/*` - Core storage and retrieval
- **Agent API** (1 endpoint) - `/v1/agent/execute` - Agent orchestration
- **Graph API** (7 endpoints) - `/v1/graph/*` - Basic GraphRAG operations
- **Cache API** (1 endpoint) - `/v1/cache/rebuild` - Cache management
- **Governance API** (3 endpoints) - `/v1/governance/*` - Cost tracking and budgets
- **Health API** (4 endpoints) - `/health*`, `/metrics` - System monitoring

**Enterprise APIs (NEW - v2.0):**
- **Event Triggers API** (18 endpoints) - `/v1/triggers/*` - Automation and workflows
- **Reflections API** (8 endpoints) - `/v1/reflections/*` - Hierarchical reflections
- **Hybrid Search API** (10 endpoints) - `/v1/search/*` - Multi-strategy search
- **Evaluation API** (12 endpoints) - `/v1/evaluation/*` - Quality metrics and drift
- **Dashboard API** (7 endpoints) - `/v1/dashboard/*` - Real-time monitoring
- **Graph Management API** (19 endpoints) - `/v1/graph/manage/*` - Advanced graph ops

### 🔮 Planned APIs (Future Releases)
- Semantic Memory API (dedicated entity management)
- Multi-modal Memory API (images, audio, video)
- Collaboration API (multi-user features)
- Plugin System API (custom extensions)

### 🔧 Enterprise Features
- **GraphRAG** - Knowledge graph extraction and traversal with advanced algorithms
- **Event-Driven Automation** - Triggers, conditions, actions, and workflow orchestration
- **Hierarchical Reflections** - Automatic insight extraction with clustering
- **Hybrid Search** - Multi-strategy search with dynamic weighting and LLM re-ranking
- **Quality Monitoring** - Search evaluation, drift detection, and A/B testing
- **Real-time Dashboard** - Live metrics, visualizations, and system health
- **Advanced Graph Operations** - Temporal graphs, snapshots, and batch operations
- **Context Caching** - Cost optimization through intelligent caching
- **Governance** - Cost tracking, budget management, and usage analytics
- **Agent Orchestration** - Full agent execution pipeline with automatic reflection
- **Health Monitoring** - Kubernetes-ready health probes and metrics

For questions or support, visit: https://github.com/dreamsoft-pro/RAE-agentic-memory
