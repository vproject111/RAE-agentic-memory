# Complete API Endpoint Index

**Version**: 2.2.0-enterprise
**Total Endpoints**: 116
**Last Updated**: 2025-12-04

This document provides a complete index of all API endpoints in the RAE Agentic Memory system, organized by module.

> **💡 Tip**: For interactive documentation with examples, visit http://localhost:8000/docs

---

## Table of Contents

- [Core Endpoints (26)](#core-endpoints-26)
  - [Health & Monitoring (4)](#health--monitoring-4)
  - [Memory Management (6)](#memory-management-6)
  - [Agent Operations (1)](#agent-operations-1)
  - [Knowledge Graph (7)](#knowledge-graph-7)
  - [Cache Management (1)](#cache-management-1)
  - [Governance & Cost Control (3)](#governance--cost-control-3)
  - [Token Savings (2)](#token-savings-2)
  - [ISO/IEC 42001 Compliance (13)](#isoiec-42001-compliance-13)
- [Enterprise Endpoints (90)](#enterprise-endpoints-90)
  - [Event Triggers & Workflows (18)](#event-triggers--workflows-18)
  - [Reflections (8)](#reflections-8)
  - [Hybrid Search (10)](#hybrid-search-10)
  - [Graph Enhanced Operations (19)](#graph-enhanced-operations-19)
  - [Evaluation & Quality (12)](#evaluation--quality-12)
  - [Dashboard & Analytics (12)](#dashboard--analytics-12)

---

## Core Endpoints (26)

### Health & Monitoring (4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness probe for orchestrators |
| GET | `/metrics` | Prometheus metrics |
| GET | `/health/detailed` | Detailed system health status |

**File**: `apps/memory_api/api/v1/health.py`

---

### Memory Management (6)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/memory/store` | Store a new memory (episodic, semantic, procedural) |
| POST | `/v1/memory/query` | Query memories with vector similarity + filters |
| DELETE | `/v1/memory/delete` | Delete memories by ID or filters |
| POST | `/v1/memory/rebuild-reflections` | Trigger reflection regeneration |
| GET | `/v1/memory/reflection-stats` | Get reflection statistics |
| POST | `/v1/memory/reflection/hierarchical` | Generate hierarchical reflections (deprecated) |

**File**: `apps/memory_api/api/v1/memory.py`

**Key Features**:
- Multi-layer memory (episodic, semantic, procedural, ltm)
- Automatic embeddings via ML service
- Metadata and tagging support
- Tenant isolation

---

### Agent Operations (1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/agent/execute` | Execute agent task with memory-augmented context |

**File**: `apps/memory_api/api/v1/agent.py`

**Features**:
- Retrieves relevant memories
- Builds context automatically
- Cost tracking
- LLM integration

---

### Knowledge Graph (7)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/graph/extract` | Extract entities and relationships from text |
| POST | `/v1/graph/reflection/hierarchical` | Generate hierarchical graph reflections |
| GET | `/v1/graph/stats` | Get graph statistics (nodes, edges, density) |
| GET | `/v1/graph/nodes` | List graph nodes with filters |
| GET | `/v1/graph/edges` | List graph edges with filters |
| POST | `/v1/graph/query` | Hybrid search across graph and vectors |
| GET | `/v1/graph/subgraph` | Extract subgraph by traversal |

**File**: `apps/memory_api/api/v1/graph.py`

**Features**:
- GraphRAG (Graph + RAG)
- Entity extraction via LLM
- Relationship discovery
- Multi-hop traversal

---

### Cache Management (1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/cache/rebuild` | Rebuild context cache for tenant/project |

**File**: `apps/memory_api/api/v1/cache.py`

**Use Case**: Force cache refresh after bulk updates

---

### Governance & Cost Control (3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/governance/overview` | Cost overview across all tenants |
| GET | `/v1/governance/tenant/{tenant_id}` | Tenant-specific cost stats |
| GET | `/v1/governance/tenant/{tenant_id}/budget` | Budget status and alerts |

**File**: `apps/memory_api/api/v1/governance.py`

**Features**:
- Token usage tracking
- Budget alerts
- Cost breakdown by operation
- Per-tenant limits

---

### Token Savings (2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/metrics/savings` | Get token savings summary |
| GET | `/v1/metrics/savings/graph` | Get savings over time (graph data) |

**File**: `apps/memory_api/routes/token_savings.py`

**Features**:
- Cache hit savings tracking
- USD cost savings calculation
- Time series data

---

### ISO/IEC 42001 Compliance (13)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/compliance/approvals` | Create human approval request |
| GET | `/v1/compliance/approvals/{request_id}` | Get approval request status |
| POST | `/v1/compliance/approvals/{request_id}/decide` | Approve/reject request |
| POST | `/v1/compliance/provenance/context` | Record context provenance |
| POST | `/v1/compliance/provenance/decision` | Record decision provenance |
| GET | `/v1/compliance/provenance/lineage/{decision_id}` | Get full provenance chain |
| GET | `/v1/compliance/circuit-breakers` | List all circuit breaker states |
| GET | `/v1/compliance/circuit-breakers/{name}` | Get specific circuit breaker |
| POST | `/v1/compliance/circuit-breakers/{name}/reset` | Reset circuit breaker |
| GET | `/v1/compliance/policies` | List all policy versions |
| POST | `/v1/compliance/policies` | Create new policy version |
| POST | `/v1/compliance/policies/{policy_id}/activate` | Activate policy version |
| POST | `/v1/compliance/policies/{policy_id}/enforce` | Enforce policy on operation |

**File**: `apps/memory_api/api/v1/compliance.py`

**Features**:
- Human-in-the-loop approvals
- Context quality tracking
- Circuit breakers for fail-fast
- Policy versioning and enforcement

---

## Enterprise Endpoints (90)

### Event Triggers & Workflows (18)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/triggers/create` | Create new event trigger rule |
| GET | `/v1/triggers/{trigger_id}` | Get trigger by ID |
| PUT | `/v1/triggers/{trigger_id}` | Update trigger configuration |
| DELETE | `/v1/triggers/{trigger_id}` | Delete trigger |
| POST | `/v1/triggers/{trigger_id}/enable` | Enable trigger |
| POST | `/v1/triggers/{trigger_id}/disable` | Disable trigger |
| GET | `/v1/triggers/list` | List all triggers for tenant |
| POST | `/v1/triggers/events/emit` | Emit custom event |
| GET | `/v1/triggers/events/types` | List available event types |
| POST | `/v1/triggers/executions` | Get trigger execution history |
| POST | `/v1/triggers/workflows/create` | Create workflow definition |
| GET | `/v1/triggers/workflows/{workflow_id}` | Get workflow by ID |
| GET | `/v1/triggers/workflows` | List workflows |
| GET | `/v1/triggers/templates` | List workflow templates |
| GET | `/v1/triggers/templates/{template_id}` | Get template by ID |
| POST | `/v1/triggers/workflows/{workflow_id}/execute` | Execute workflow manually |
| GET | `/v1/triggers/health` | Event trigger system health |
| GET | `/v1/triggers/info` | System info and capabilities |

**File**: `apps/memory_api/routes/event_triggers.py`

**Features**:
- Event-driven automation
- Workflow orchestration
- Webhook integration
- Execution history and audit

**Use Cases**:
- Auto-tagging memories
- Slack notifications on important events
- Backup triggers
- Compliance workflows

---

### Reflections (8)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/reflections/generate` | Generate reflections from memories |
| POST | `/v1/reflections/query` | Query reflections with filters |
| GET | `/v1/reflections/{reflection_id}` | Get specific reflection |
| GET | `/v1/reflections/{reflection_id}/children` | Get child reflections |
| POST | `/v1/reflections/graph` | Get reflection graph structure |
| POST | `/v1/reflections/relationships` | Create reflection relationship |
| GET | `/v1/reflections/statistics/{tenant_id}/{project}` | Get reflection stats |
| DELETE | `/v1/reflections/batch` | Batch delete reflections |

**File**: `apps/memory_api/routes/reflections.py`

**Features**:
- Hierarchical reflection system (L1, L2, L3)
- Semantic clustering
- Insight generation
- Graph-based relationships

**Use Cases**:
- Pattern discovery
- Knowledge consolidation
- Insight generation
- Long-term memory formation

---

### Hybrid Search (10)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/search/hybrid` | Multi-strategy search (vector+semantic+graph+fulltext) |
| POST | `/v1/search/analyze` | Analyze query characteristics |
| POST | `/v1/search/analyze/explain` | Get detailed query analysis |
| GET | `/v1/search/weights/profiles` | List available weight profiles |
| GET | `/v1/search/weights/profiles/{profile_name}` | Get specific weight profile |
| POST | `/v1/search/weights/calculate` | Calculate adaptive weights |
| POST | `/v1/search/compare` | Compare results across strategies |
| POST | `/v1/search/test/weights` | Test weight configuration |
| GET | `/v1/search/health` | Hybrid search system health |
| GET | `/v1/search/info` | System info and capabilities |

**File**: `apps/memory_api/routes/hybrid_search.py`

**Features**:
- 4 search strategies (vector, semantic, graph, fulltext)
- Adaptive weight calculation
- Result reranking
- Cache integration with token savings tracking

**Use Cases**:
- Semantic question answering
- Fact retrieval
- Pattern matching
- Multi-modal search

---

### Graph Enhanced Operations (19)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/graph-management/nodes` | Create enhanced graph node |
| GET | `/v1/graph-management/nodes/{node_id}/metrics` | Get node metrics |
| POST | `/v1/graph-management/nodes/connected` | Find connected nodes |
| POST | `/v1/graph-management/edges` | Create enhanced graph edge |
| PUT | `/v1/graph-management/edges/{edge_id}/weight` | Update edge weight |
| POST | `/v1/graph-management/edges/{edge_id}/deactivate` | Deactivate edge |
| POST | `/v1/graph-management/edges/{edge_id}/activate` | Activate edge |
| PUT | `/v1/graph-management/edges/{edge_id}/temporal` | Update temporal properties |
| POST | `/v1/graph-management/traverse` | Traverse graph with strategy |
| POST | `/v1/graph-management/path/shortest` | Find shortest path |
| POST | `/v1/graph-management/cycles/detect` | Detect cycles in graph |
| POST | `/v1/graph-management/snapshots` | Create graph snapshot |
| GET | `/v1/graph-management/snapshots/{snapshot_id}` | Get snapshot by ID |
| GET | `/v1/graph-management/snapshots` | List all snapshots |
| POST | `/v1/graph-management/snapshots/{snapshot_id}/restore` | Restore from snapshot |
| POST | `/v1/graph-management/statistics` | Get graph statistics |
| POST | `/v1/graph-management/nodes/batch` | Batch create nodes |
| POST | `/v1/graph-management/edges/batch` | Batch create edges |
| GET | `/v1/graph-management/health` | Graph system health |

**File**: `apps/memory_api/routes/graph_enhanced.py`

**Features**:
- Advanced graph algorithms (BFS, DFS, shortest path, cycle detection)
- Temporal graphs (time-based edges)
- Graph snapshots and versioning
- Batch operations
- Centrality metrics

**Use Cases**:
- Knowledge graph exploration
- Dependency analysis
- Temporal reasoning
- Graph version control

---

### Evaluation & Quality (12)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/evaluation/search` | Evaluate search quality |
| GET | `/v1/evaluation/metrics/supported` | List supported metrics |
| POST | `/v1/evaluation/drift/detect` | Detect data/concept drift |
| GET | `/v1/evaluation/drift/severity-levels` | List severity levels |
| POST | `/v1/evaluation/ab-test/create` | Create A/B test |
| POST | `/v1/evaluation/ab-test/{test_id}/compare` | Compare A/B test results |
| POST | `/v1/evaluation/quality/metrics` | Get quality metrics |
| GET | `/v1/evaluation/quality/thresholds` | Get quality thresholds |
| POST | `/v1/evaluation/benchmark/run` | Run benchmark suite |
| GET | `/v1/evaluation/benchmark/suites` | List benchmark suites |
| GET | `/v1/evaluation/health` | Evaluation system health |
| GET | `/v1/evaluation/info` | System info and capabilities |

**File**: `apps/memory_api/routes/evaluation.py`

**Features**:
- Search quality metrics (precision, recall, MRR, NDCG)
- A/B testing with statistical significance
- Drift detection
- Benchmark suites
- Quality monitoring

**Use Cases**:
- Search quality monitoring
- Configuration testing
- Performance regression detection
- Quality assurance

---

### Dashboard & Analytics (12)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/dashboard/metrics` | Get dashboard metrics |
| GET | `/v1/dashboard/metrics/timeseries/{metric_name}` | Get time series data |
| POST | `/v1/dashboard/visualizations` | Get visualization data |
| POST | `/v1/dashboard/health` | Get system health status |
| GET | `/v1/dashboard/health/simple` | Simplified health check |
| GET | `/v1/dashboard/activity` | Get activity feed |
| GET | `/v1/dashboard/info` | Dashboard info and capabilities |
| POST | `/v1/dashboard/monitoring/metrics/time-series` | Get monitoring time series |
| POST | `/v1/dashboard/monitoring/components/health` | Get component health |
| POST | `/v1/dashboard/monitoring/alerts/active` | Get active alerts |
| POST | `/v1/dashboard/monitoring/logs/recent` | Get recent logs |
| GET | `/v1/dashboard/monitoring/performance` | Get performance metrics |

**File**: `apps/memory_api/routes/dashboard.py`

**Features**:
- Real-time metrics
- Time series data (via TimescaleDB)
- WebSocket support for live updates
- System health monitoring
- Activity tracking

**Use Cases**:
- Operations monitoring
- Performance tracking
- Troubleshooting
- Capacity planning

---

## Authentication

All endpoints (except `/health*` and `/metrics`) require authentication:

```bash
# API Key
curl -H "X-API-Key: your-api-key" http://localhost:8000/v1/memory/query

# JWT Bearer Token
curl -H "Authorization: Bearer your-token" http://localhost:8000/v1/memory/query
```

## Common Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` or `Authorization` | Yes | Authentication |
| `X-Tenant-ID` | Yes | Multi-tenancy identifier |
| `X-Project-ID` | No | Project scope (optional) |
| `Content-Type` | Yes | `application/json` |

## Error Responses

All endpoints return consistent error format:

```json
{
  "error": {
    "code": "400",
    "message": "Validation Error",
    "details": {...}
  }
}
```

## Rate Limiting

Default: 100 requests/60 seconds per tenant

Response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1735603200
```

## Further Documentation

- **[API Reference](api_reference.md)** - Overview and getting started
- **[API Cookbook](API_COOKBOOK.md)** - Task-oriented recipes
- **[OpenAPI Spec](OPENAPI.md)** - Auto-generated OpenAPI documentation
- **[REST Examples](rest-api.md)** - Curl examples
- **[Python SDK](python-sdk.md)** - Python client library
- **[Interactive Docs](http://localhost:8000/docs)** - Swagger UI

---

**Last Updated**: 2025-12-04
**API Version**: 2.2.0-enterprise
**Total Endpoints**: 116
