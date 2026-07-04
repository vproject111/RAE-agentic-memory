# Observability in RAE

The RAE Agentic Memory Engine is designed with comprehensive observability through two complementary systems: **Prometheus metrics** for monitoring and **OpenTelemetry distributed tracing** for deep visibility into request flows.

---

## Table of Contents

1. [OpenTelemetry Distributed Tracing](#opentelemetry-distributed-tracing)
2. [Prometheus Metrics](#prometheus-metrics)
3. [Grafana Dashboard](#grafana-dashboard)
4. [Quick Start](#quick-start)
5. [Production Deployment](#production-deployment)

---

## OpenTelemetry Distributed Tracing

RAE implements comprehensive distributed tracing using **OpenTelemetry**, providing deep visibility into request flows, performance bottlenecks, and system behavior.

### ✅ What's Instrumented

#### **Automatic Instrumentation (No Code Changes Required)**

- **FastAPI HTTP Requests** - All HTTP endpoints with method, path, status code
- **PostgreSQL Queries** - Database operations via asyncpg and psycopg2
- **Redis Operations** - Cache hits/misses and all Redis commands
- **External HTTP Calls** - Outbound requests via requests library
- **Celery Tasks** - Background job processing
- **Python Logging** - Trace context automatically added to logs

#### **Custom Instrumentation (RAE-Specific)**

RAE adds detailed custom spans for core operations:

**Mathematical Core Layers** (`apps/memory_api/core/`):
- **State Management** (`state.py`) - State transitions, budget tracking, working memory
- **Action Space** (`actions.py`) - All 12 action types with execution metrics
- **Reward Function** (`reward.py`) - Quality metrics and cost penalties
- **Graph Operator** (`graph_operator.py`) - Graph updates, entity resolution, temporal decay
- **Information Bottleneck** (`information_bottleneck.py`) - Context selection with I(Z;Y) and I(Z;X) metrics

**Services Layer**:
- **Reflection Pipeline** (`reflection_pipeline.py`) - Memory clustering (HDBSCAN/K-means), insight generation
- **Context Builder** (`context_builder.py`) - Working Memory construction with LTM + reflections

**API Endpoints** (`api/v1/memory.py`):
- `/store` - Memory storage with PII scrubbing tracking
- `/query` - Hybrid search (vector + graph) vs vector-only modes
- `/delete` - Memory deletion from DB and vector store
- `/rebuild-reflections` - Background task dispatch
- `/reflection-stats` - Reflection statistics retrieval

### 📊 Trace Attributes (Standardized Namespace: `rae.*`)

All spans use consistent attribute naming:

**Common Attributes:**
- `rae.tenant_id` - Multi-tenant isolation tracking
- `rae.project_id` - Project-level tracking
- `rae.outcome.label` - Operation result (success, error types)

**Memory Operations:**
- `rae.memory.id`, `rae.memory.layer`, `rae.memory.importance`
- `rae.memory.content_length_original`, `rae.memory.content_length_scrubbed`
- `rae.memory.embedding_dimension`

**Query Operations:**
- `rae.query.text_length`, `rae.query.k`, `rae.query.use_graph`
- `rae.query.mode` - "hybrid_graph" or "vector_only"
- `rae.query.vector_count`, `rae.query.graph_count`, `rae.query.total_results`

**Reflection Operations:**
- `rae.reflection.memories_count`, `rae.reflection.clusters_count`
- `rae.reflection.algorithm` - "hdbscan" or "kmeans"
- `rae.reflection.insights_generated`, `rae.reflection.total_cost_usd`

**Mathematical Metrics:**
- `rae.ib.I_Z_Y` - Relevance metric (Information Bottleneck)
- `rae.ib.I_Z_X` - Compression metric
- `rae.ib.compression_ratio`, `rae.ib.objective`
- `rae.reward.quality_score`, `rae.reward.cost_penalty`

### 🚀 Configuration

OpenTelemetry is configured via environment variables:

```bash
# Enable/disable tracing
OTEL_TRACES_ENABLED=true

# Service identification
OTEL_SERVICE_NAME=rae-memory-api
OTEL_SERVICE_VERSION=2.1.0-enterprise

# Exporter configuration
OTEL_EXPORTER_TYPE=otlp              # otlp, console, none
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Optional: Grafana Cloud Tempo
# OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-api-key>"
```

### 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              RAE Memory API                      │
│  ┌──────────────────────────────────────────┐   │
│  │  Auto-Instrumentation                    │   │
│  │  • FastAPI (HTTP requests)               │   │
│  │  • PostgreSQL (asyncpg + psycopg2)       │   │
│  │  • Redis (cache operations)              │   │
│  │  • Celery (background tasks)             │   │
│  │  • External HTTP (requests)              │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Custom Instrumentation                  │   │
│  │  • Mathematical core (5 layers)          │   │
│  │  • Services (reflection, context)        │   │
│  │  • API endpoints (store, query, delete)  │   │
│  └──────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────┘
                 │ OTLP (gRPC)
                 ▼
┌─────────────────────────────────────────────────┐
│         OpenTelemetry Collector (optional)       │
│  • Sampling, filtering, batching                │
│  • Multi-backend export                         │
└────────┬────────────────────────────────────────┘
         │
         ├──▶ Jaeger (local dev)
         ├──▶ Grafana Cloud Tempo
         ├──▶ Elastic APM
         ├──▶ AWS X-Ray
         └──▶ Google Cloud Trace
```

### 📝 Usage Examples

#### **Viewing Traces**

With Jaeger (local development):
```bash
# Start Jaeger
docker run -d --name jaeger \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# View traces
open http://localhost:16686
```

#### **Custom Spans (Advanced)**

For custom application code:

```python
from apps.memory_api.observability.rae_tracing import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("my_custom_operation") as span:
    span.set_attribute("rae.custom.key", "value")
    span.set_attribute("rae.outcome.label", "success")
    # ... your code ...
```

### 🔍 Trace Context Propagation

Trace context is automatically propagated via **W3C TraceContext** headers:
- `traceparent: 00-<trace-id>-<span-id>-<flags>`
- `tracestate: <vendor-specific-state>`

This ensures distributed traces work across:
- Microservices (Memory API → ML Service → Reranker)
- Background tasks (Celery workers)
- External services

### 📚 Implementation Details

See source code:
- **Configuration**: `apps/memory_api/observability/opentelemetry_config.py`
- **Custom Tracers**: `apps/memory_api/observability/rae_tracing.py`
- **Telemetry Schema**: `apps/memory_api/observability/rae_telemetry_schema.py`

---

## Prometheus Metrics

RAE exposes comprehensive metrics in Prometheus format at `/metrics` on the Memory API.

### 📊 Key Metrics

#### **API Performance**
- `rae_request_latency_seconds` - Request latency histogram
- `rae_request_duration_seconds` - Request duration by endpoint
- `http_request_total` - Total HTTP requests by method/path/status

#### **Cache Efficiency**
- `rae_cache_hits_total` - Total cache hits
- `rae_cache_misses_total` - Total cache misses
- `rae_cache_hit_ratio` - Cache hit rate percentage

#### **LLM Usage & Cost**
- `rae_llm_token_usage_total` - Total LLM tokens used (by model/provider)
- `rae_llm_cost_total` - Estimated cost of LLM usage in USD
- `rae_llm_request_duration_seconds` - LLM API call latency

#### **Memory Operations**
- `rae_memory_store_total` - Total memories stored (by tenant)
- `rae_memory_query_total` - Total memory queries (by tenant)
- `rae_memory_delete_total` - Total memories deleted (by tenant)

#### **System Health**
- `process_resident_memory_bytes` - Memory usage
- `process_cpu_seconds_total` - CPU time
- `pg_pool_size` - PostgreSQL connection pool size
- `redis_connected_clients` - Redis active connections

### 📥 Scraping Configuration

Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'rae-memory-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## Grafana Dashboard

RAE includes a pre-configured Grafana dashboard with comprehensive visualizations.

### 📍 Location

`infra/grafana/rae-dashboard.json`

### 📊 Dashboard Panels

The dashboard visualizes:

1. **Request Metrics**
   - Request rate (req/s)
   - Average latency
   - Error rate
   - P95/P99 latency

2. **Cache Performance**
   - Hit rate over time
   - Cache hits vs misses
   - Cache efficiency trend

3. **LLM Usage**
   - Token consumption by model
   - Cost over time
   - Cost by tenant/project

4. **Memory Operations**
   - Store/Query/Delete rates
   - Operations by tenant
   - Memory layer distribution

5. **System Health**
   - Memory usage
   - CPU utilization
   - Database connection pool
   - Redis connections

### 🚀 Setup

```bash
# 1. Start Grafana (via docker compose)
docker compose up -d grafana

# 2. Access Grafana
open http://localhost:3000
# Default: admin / admin

# 3. Add Prometheus data source
Configuration → Data Sources → Add data source → Prometheus
URL: http://prometheus:9090

# 4. Import dashboard
Dashboards → Import → Upload JSON file
Select: infra/grafana/rae-dashboard.json
```

---

## Quick Start

### Local Development (Jaeger + Prometheus + Grafana)

```bash
# 1. Start full observability stack
docker compose -f docker compose.observability.yml up -d

# Services available:
# - Jaeger UI:     http://localhost:16686
# - Prometheus:    http://localhost:9090
# - Grafana:       http://localhost:3000

# 2. Configure RAE
export OTEL_TRACES_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# 3. Start RAE
docker compose up -d

# 4. Generate some traffic
python scripts/seed_demo_data.py

# 5. View traces and metrics
open http://localhost:16686  # Jaeger
open http://localhost:3000   # Grafana
```

---

## Production Deployment

### Grafana Cloud (Recommended)

**Benefits:**
- Managed Prometheus + Tempo
- No infrastructure management
- Built-in alerting
- Long-term retention

**Setup:**

```bash
# 1. Get credentials from Grafana Cloud

# 2. Configure RAE
export OTEL_TRACES_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=https://tempo-prod-xx-xxx.grafana.net:443
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-api-key>"

# 3. Configure Prometheus remote_write
# Add to prometheus.yml:
remote_write:
  - url: https://prometheus-prod-xx-xxx.grafana.net/api/prom/push
    basic_auth:
      username: <username>
      password: <api-key>
```

### Kubernetes with Tempo + Prometheus Operator

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rae-otel-config
data:
  OTEL_TRACES_ENABLED: "true"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://tempo:4317"
  OTEL_SERVICE_NAME: "rae-memory-api"
---
apiVersion: v1
kind: Service
metadata:
  name: rae-api
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
spec:
  ports:
  - port: 8000
  selector:
    app: rae-api
```

### Elastic APM

```bash
export OTEL_TRACES_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=https://apm-server:8200
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <secret-token>"
```

### AWS X-Ray (via ADOT Collector)

```bash
# Deploy AWS Distro for OpenTelemetry Collector
export OTEL_TRACES_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://adot-collector:4317
```

---

## Best Practices

### 📈 Sampling Strategies

For high-traffic production systems, consider sampling:

```yaml
# OpenTelemetry Collector config
processors:
  probabilistic_sampler:
    sampling_percentage: 10  # Sample 10% of traces

  tail_sampling:
    policies:
      - name: error-traces
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow-traces
        type: latency
        latency: {threshold_ms: 1000}
```

### 🔒 Security

- **Production**: Use TLS for OTLP endpoint
- **Cloud**: Store API keys in secrets manager
- **Network**: Restrict Prometheus scrape to internal network
- **Headers**: Filter sensitive headers from traces

### 🎯 Alerting

Set up alerts on key metrics:

```yaml
# Prometheus alerting rules
groups:
  - name: rae-api
    rules:
      - alert: HighErrorRate
        expr: rate(http_request_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(rae_request_latency_seconds_bucket[5m])) > 1
        for: 10m
        annotations:
          summary: "P95 latency above 1s"

      - alert: LowCacheHitRate
        expr: rae_cache_hit_ratio < 0.7
        for: 15m
        annotations:
          summary: "Cache hit rate below 70%"
```

---

## FAQ

**Q: Does OpenTelemetry affect performance?**
A: Minimal impact (<5% overhead). Spans are batched and exported asynchronously.

**Q: Can I disable tracing in production?**
A: Yes, set `OTEL_TRACES_ENABLED=false`. Auto-instrumentation becomes no-op.

**Q: Do I need an OpenTelemetry Collector?**
A: Optional but recommended for production. Provides sampling, filtering, and multi-backend export.

**Q: How long are traces retained?**
A: Depends on backend:
- Jaeger: 7 days (default)
- Grafana Cloud Tempo: 30+ days (configurable)
- Elastic APM: 7 days (default)

**Q: Can I use both Jaeger and Grafana Cloud?**
A: Yes! Use OpenTelemetry Collector to export to multiple backends.

**Q: Are traces correlated with logs?**
A: Yes! `trace_id` and `span_id` are automatically added to structured logs.

---

## Resources

- **OpenTelemetry Docs**: https://opentelemetry.io/docs/
- **Jaeger**: https://www.jaegertracing.io/
- **Grafana Cloud Tempo**: https://grafana.com/oss/tempo/
- **Prometheus**: https://prometheus.io/docs/
- **RAE Telemetry Schema**: `apps/memory_api/observability/rae_telemetry_schema.py`

---

## Summary

RAE provides **production-grade observability** with:

✅ **OpenTelemetry** - Distributed tracing across all operations
✅ **Prometheus** - Rich metrics for monitoring
✅ **Grafana** - Pre-built dashboards
✅ **Flexible Backends** - Jaeger, Tempo, Elastic, X-Ray, Cloud Trace
✅ **Zero Config** - Works out of the box with sensible defaults
✅ **Production Ready** - Sampling, filtering, multi-tenant support

**No API changes required** - All instrumentation is internal and transparent to API clients.

---

## Future Enhancements (TODO)

The following OpenTelemetry instrumentation phases are planned for future implementation:

### Phase 2: Graph API Instrumentation (Priority: Medium)

**File:** `apps/memory_api/api/v1/graph.py`

**Value Proposition:** Critical for research and scientific applications requiring knowledge graph analysis and entity relationship tracking.

**Endpoints to Instrument (7 endpoints):**

1. **POST /graph/build** - Build graph from memories
   - Track: memory count, entities extracted, relationships created, build time
   - Attributes: `rae.graph.memories_count`, `rae.graph.entities_count`, `rae.graph.relationships_count`

2. **GET /graph/query** - Query graph
   - Track: query type, node count, relationship count, traversal depth
   - Attributes: `rae.graph.query_type`, `rae.graph.nodes_returned`, `rae.graph.edges_returned`

3. **GET /graph/entity/{entity_id}** - Get entity details
   - Track: entity type, relationship count, attribute count
   - Attributes: `rae.graph.entity_type`, `rae.graph.relationships_count`

4. **GET /graph/entity/{entity_id}/neighbors** - Get entity neighbors
   - Track: neighbor count, relationship types, traversal depth
   - Attributes: `rae.graph.neighbors_count`, `rae.graph.relationship_types`

5. **GET /graph/path** - Find shortest path
   - Track: path length, nodes traversed, algorithm used
   - Attributes: `rae.graph.path_length`, `rae.graph.algorithm`

6. **GET /graph/community** - Detect communities
   - Track: communities found, modularity score, algorithm
   - Attributes: `rae.graph.communities_count`, `rae.graph.modularity`

7. **GET /graph/stats** - Graph statistics
   - Track: nodes, edges, density, connected components
   - Attributes: `rae.graph.nodes_total`, `rae.graph.edges_total`, `rae.graph.density`

**Implementation Notes:**
- Focus on graph algorithm performance metrics
- Track Neo4j query execution times
- Monitor memory usage for large graph operations
- Add entity resolution accuracy metrics

### Phase 3: Background Workers & Advanced Services (Priority: Low)

**Value Proposition:** Complete end-to-end observability for asynchronous operations and advanced computational tasks.

**Components to Instrument:**

#### 3.1 Celery Background Workers

**Files:**
- `apps/memory_api/tasks/reflection_tasks.py`
- `apps/memory_api/tasks/maintenance_tasks.py`

**Tasks to Instrument:**
- **Reflection Generation** (periodic clustering)
  - Track: memories processed, clusters created, insights generated, execution time
  - Attributes: `rae.task.reflection.memories_count`, `rae.task.reflection.duration_seconds`

- **Temporal Decay** (periodic importance decay)
  - Track: memories decayed, importance changes, execution time
  - Attributes: `rae.task.decay.memories_affected`, `rae.task.decay.avg_decay_rate`

- **Garbage Collection** (cleanup old memories)
  - Track: memories deleted, space freed, execution time
  - Attributes: `rae.task.gc.memories_deleted`, `rae.task.gc.space_freed_mb`

- **Graph Rebuild** (periodic graph reconstruction)
  - Track: nodes updated, edges updated, execution time
  - Attributes: `rae.task.graph_rebuild.nodes_updated`, `rae.task.graph_rebuild.duration_seconds`

#### 3.2 Advanced Services

**Files:**
- `apps/memory_api/services/importance_scoring_v2.py`
- `apps/memory_api/services/memory_decay_service.py`
- `apps/memory_api/services/pii_scrubber.py`

**Operations to Instrument:**
- **Importance Scoring** (ML-based importance calculation)
  - Track: memories scored, model inference time, score distribution
  - Attributes: `rae.importance.memories_scored`, `rae.importance.inference_ms`

- **Memory Decay** (time-based importance decay)
  - Track: decay function used, memories affected, decay rate
  - Attributes: `rae.decay.function`, `rae.decay.memories_count`, `rae.decay.avg_rate`

- **PII Scrubbing** (personal data detection & removal)
  - Track: PII entities found, scrubbing time, entity types
  - Attributes: `rae.pii.entities_found`, `rae.pii.entity_types`, `rae.pii.scrub_time_ms`

#### 3.3 Integration Services

**Files:**
- `apps/memory_api/services/embedding.py`
- `apps/memory_api/services/vector_store.py`
- `apps/memory_api/services/reranker.py`

**Operations to Instrument:**
- **Embedding Generation** (via OpenAI/local models)
  - Track: batch size, generation time, model used, token count
  - Attributes: `rae.embedding.batch_size`, `rae.embedding.model`, `rae.embedding.duration_ms`

- **Vector Store Operations** (Qdrant queries)
  - Track: query latency, result count, filter complexity
  - Attributes: `rae.vector.query_latency_ms`, `rae.vector.results_count`

- **Reranking** (cross-encoder reranking)
  - Track: candidates reranked, reranking time, score distribution
  - Attributes: `rae.rerank.candidates_count`, `rae.rerank.duration_ms`

### Implementation Priority

1. **Phase 2 (Graph API)** - Medium priority
   - Estimated effort: 4-6 hours
   - Dependencies: None
   - Value: High for research applications

2. **Phase 3 (Background Workers)** - Low priority
   - Estimated effort: 8-12 hours
   - Dependencies: None
   - Value: Completeness, debugging async issues

### Implementation Guidelines

When implementing future phases, follow these patterns:

1. **Consistent Namespace**: Use `rae.*` prefix for all attributes
2. **Error Tracking**: Always set `rae.outcome.label` (success/error/not_found)
3. **Error Details**: Include `rae.error.message` on failures
4. **Performance Metrics**: Track duration, count, and size metrics
5. **Business Metrics**: Include tenant_id, project_id for multi-tenant tracking
6. **Outcome Labels**: Standardize on success, error, not_found, timeout, invalid_request

### Testing Recommendations

For each instrumented component:
- Verify spans appear in Jaeger/Tempo
- Check attribute naming consistency
- Validate error scenarios produce proper spans
- Test trace context propagation
- Monitor performance overhead (<5%)

### Documentation Updates

After implementing each phase:
- Update this file with actual implementation details
- Add new attributes to `rae_telemetry_schema.py`
- Update Grafana dashboards with new metrics
- Add example queries to FAQ section
