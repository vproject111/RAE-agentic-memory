# RAE Enterprise Services - Quick Reference

This document provides an overview of RAE's enterprise-grade services for production deployments.

## Core Services

### 1. Hybrid Search 2.0 (GraphRAG)
**File**: `apps/memory_api/services/hybrid_search_service.py`

Multi-strategy search combining vector similarity, semantic nodes, graph traversal, and full-text search.

**Key Features**:
- Query analyzer with intent classification
- Dynamic weight calculation
- Graph traversal (BFS) for GraphRAG
- LLM re-ranking
- Intelligent caching layer

📖 **[Full Documentation](./HYBRID_SEARCH.md)**

### 2. Rules Engine (Event Automation)
**File**: `apps/memory_api/services/rules_engine.py`

Event-driven automation system with triggers, conditions, and actions.

**Key Features**:
- 10+ event types
- Complex AND/OR condition logic
- Rate limiting and cooldowns
- Webhook integrations
- Retry with exponential backoff

📖 **[Full Documentation](./RULES_ENGINE.md)**

### 3. Evaluation Service
**File**: `apps/memory_api/services/evaluation_service.py`

Search quality metrics and A/B testing.

**Metrics**: MRR, NDCG, Precision@K, Recall@K, MAP

📖 **[Full Documentation](./EVALUATION_SERVICE.md)**

---

## Quality & Security Services

### 4. PII Scrubber
**File**: `apps/memory_api/services/pii_scrubber.py`

Automatic detection and anonymization of personally identifiable information.

**Detects**:
- Email addresses
- Phone numbers
- Credit card numbers
- Social security numbers
- IP addresses
- Custom patterns via regex

**Usage**:
```python
from apps.memory_api.services.pii_scrubber import scrub_pii

# Automatic scrubbing
clean_content = scrub_pii(
    content="Contact me at john@example.com or 555-123-4567",
    replacement="[REDACTED]"
)
# Returns: "Contact me at [REDACTED] or [REDACTED]"
```

**Configuration**:
```bash
# Enable PII scrubbing globally
PII_SCRUBBING_ENABLED=true
PII_SCRUBBING_MODE=redact  # or 'hash', 'mask'
```

**Integration**: Automatically applied during memory ingestion if enabled.

---

### 5. Drift Detector
**File**: `apps/memory_api/services/drift_detector.py`

Monitors memory quality and detects semantic drift over time.

**Detects**:
- Semantic drift (changing query results over time)
- Quality degradation
- Distribution shifts in memory importance
- Embedding drift

**Key Metrics**:
- **Semantic Similarity Drift**: Measures change in query result embeddings
- **Quality Score Drift**: Tracks average importance scores
- **Coverage Drift**: Monitors changes in semantic coverage

**Usage**:
```python
from apps.memory_api.services.drift_detector import DriftDetector

detector = DriftDetector(pool=db_pool)

# Detect drift for a tenant
drift_report = await detector.detect_drift(
    tenant_id="my-tenant",
    project_id="my-project",
    lookback_days=30
)

# Returns:
# {
#     "drift_detected": True,
#     "drift_score": 0.73,
#     "affected_areas": ["semantic", "quality"],
#     "recommendations": ["Re-run evaluation", "Review recent memories"]
# }
```

**Alerts**: Can trigger events for Rules Engine integration.

---

### 6. Temporal Graph Service
**File**: `apps/memory_api/services/temporal_graph.py`

Tracks knowledge graph evolution and enables time-travel queries.

**Features**:
- **Graph Snapshots**: Capture graph state at specific points
- **Change Tracking**: Record all graph modifications
- **Time Travel**: Query graph as it existed at any past moment
- **Growth Analytics**: Track expansion metrics

**Usage**:
```python
from apps.memory_api.services.temporal_graph import TemporalGraphService
from datetime import datetime, timedelta

temporal = TemporalGraphService(db=db_pool)

# Create snapshot
snapshot = await temporal.create_snapshot(
    tenant_id=tenant_id,
    graph=current_graph,
    metadata={"reason": "daily_backup"}
)

# Time travel - reconstruct graph from 7 days ago
past_graph = await temporal.reconstruct_graph_at_time(
    tenant_id=tenant_id,
    timestamp=datetime.now() - timedelta(days=7)
)

# Get growth metrics
growth = await temporal.get_growth_metrics(
    tenant_id=tenant_id,
    period_days=30
)
# Returns: node growth, edge growth, density changes
```

**Snapshot Storage**: Snapshots stored in PostgreSQL with automatic cleanup.

---

## Monitoring & Analytics Services

### 7. Dashboard WebSocket Service
**File**: `apps/memory_api/services/dashboard_websocket.py`

Real-time updates for dashboard visualization.

**Features**:
- Real-time memory updates
- Graph changes streaming
- Search metrics streaming
- Cost tracking updates

**Channels**:
- `memory_changes`: New/updated memories
- `graph_updates`: Knowledge graph changes
- `reflection_updates`: New reflections
- `metrics_updates`: Search and cost metrics

**Usage**:
```python
from apps.memory_api.services.dashboard_websocket import DashboardWebSocketManager

ws_manager = DashboardWebSocketManager()

# Broadcast update to all connected clients
await ws_manager.broadcast(
    channel="memory_changes",
    data={
        "memory_id": "mem_123",
        "action": "created",
        "content": "...",
        "tenant_id": "my-tenant"
    }
)
```

**Client Connection**: WebSocket endpoint at `/ws/dashboard/{tenant_id}`

---

### 8. Analytics Service
**File**: `apps/memory_api/services/analytics.py`

Advanced analytics and reporting for memory patterns.

**Features**:
- Memory growth tracking
- Tag distribution analysis
- Temporal patterns (hourly, daily, weekly)
- Importance distribution
- Layer distribution (episodic vs semantic vs long-term)
- Entity co-occurrence analysis

**Usage**:
```python
from apps.memory_api.services.analytics import AnalyticsService

analytics = AnalyticsService(pool=db_pool)

# Get memory statistics
stats = await analytics.get_memory_stats(
    tenant_id="my-tenant",
    project_id="my-project",
    start_date=datetime.now() - timedelta(days=30)
)

# Returns:
# {
#     "total_memories": 15234,
#     "avg_importance": 0.67,
#     "growth_rate": 0.15,  # 15% growth
#     "top_tags": ["bug", "feature", "auth"],
#     "layer_distribution": {
#         "episodic": 0.70,
#         "semantic": 0.20,
#         "long_term": 0.10
#     }
# }
```

---

### 9. Cost Controller
**File**: `apps/memory_api/services/cost_controller.py`

Budget tracking and cost optimization.

**Features**:
- LLM API cost tracking
- Budget limits and alerts
- Cost per tenant/project
- Embedding cost tracking
- Cache hit rate monitoring

**Usage**:
```python
from apps.memory_api.services.cost_controller import CostController

controller = CostController()

# Track LLM usage
await controller.track_llm_usage(
    tenant_id="my-tenant",
    model="gpt-4",
    input_tokens=1500,
    output_tokens=800
)

# Check budget status
status = await controller.get_budget_status(tenant_id="my-tenant")
# Returns:
# {
#     "budget_limit": 100.0,
#     "spent": 73.50,
#     "remaining": 26.50,
#     "percent_used": 0.735,
#     "alert_threshold_exceeded": False
# }

# Set budget limit
await controller.set_budget_limit(
    tenant_id="my-tenant",
    limit_usd=100.0,
    alert_threshold=0.8  # Alert at 80%
)
```

**Integration**: Automatically tracks costs when using LLM provider wrappers.

---

## Integration Examples

### 1. Complete Automation Pipeline

```python
# Event: High-importance memory created
# → PII Scrubbing → Semantic Extraction → Webhook Alert

TriggerRule(
    name="High Importance Pipeline",
    event_type=EventType.MEMORY_CREATED,
    condition=TriggerCondition(
        condition_group=ConditionGroup(
            operator="AND",
            conditions=[
                Condition(field="payload.importance", operator="GREATER_THAN", value=0.8)
            ]
        )
    ),
    actions=[
        ActionConfig(action_type=ActionType.EXTRACT_SEMANTICS),
        ActionConfig(action_type=ActionType.SEND_WEBHOOK, config={"url": "..."})
    ]
)
```

### 2. Quality Monitoring Loop

```python
# Drift Detection → Evaluation → Alert if degraded

@app.task
async def quality_monitoring_loop():
    # 1. Check for drift
    drift = await drift_detector.detect_drift(tenant_id=tid)

    if drift["drift_detected"]:
        # 2. Run evaluation
        eval_result = await eval_service.evaluate_search_results(...)

        # 3. Alert if quality dropped
        if eval_result.overall_quality_score < 0.7:
            await send_alert("Search quality degraded!")
```

### 3. Real-time Dashboard Updates

```python
# Memory created → WebSocket broadcast → Dashboard update

async def on_memory_created(memory):
    # Broadcast to connected dashboard clients
    await ws_manager.broadcast(
        channel="memory_changes",
        data={
            "action": "created",
            "memory_id": str(memory.id),
            "content": memory.content[:100],
            "importance": memory.importance,
            "tags": memory.tags
        }
    )
```

---

## Configuration

All services can be configured via environment variables:

```bash
# PII Scrubbing
PII_SCRUBBING_ENABLED=true
PII_SCRUBBING_MODE=redact

# Drift Detection
DRIFT_DETECTION_ENABLED=true
DRIFT_DETECTION_THRESHOLD=0.15
DRIFT_CHECK_INTERVAL_HOURS=24

# Cost Control
COST_TRACKING_ENABLED=true
COST_ALERT_THRESHOLD=0.8

# Analytics
ANALYTICS_RETENTION_DAYS=90

# WebSocket
WEBSOCKET_MAX_CONNECTIONS=1000
```

---

## Monitoring & Logging

All services use structured logging:

```python
logger.info(
    "service_action",
    tenant_id=tenant_id,
    metric_name="mrr",
    metric_value=0.85,
    duration_ms=123
)
```

**Log Levels**:
- `INFO`: Normal operations
- `WARNING`: Rate limits, drift detected, budget thresholds
- `ERROR`: Failed operations, exceptions

---

## Best Practices

1. **Enable PII Scrubbing**: Protect sensitive data automatically
2. **Monitor Drift**: Set up daily drift detection checks
3. **Track Costs**: Set budget limits and alerts
4. **Use Automation**: Configure Rules Engine for common workflows
5. **Regular Evaluation**: Run search quality metrics weekly
6. **Snapshot Graphs**: Create daily graph snapshots
7. **Monitor WebSockets**: Track connected clients and message rates
8. **Review Analytics**: Check memory growth and patterns regularly

---

## Performance Considerations

- **PII Scrubbing**: ~50ms overhead per memory (regex-based)
- **Drift Detection**: Heavy operation, run daily or weekly
- **Evaluation**: Expensive (multiple searches), run on schedule
- **Temporal Snapshots**: Large graphs = large snapshots, compress if needed
- **WebSocket Broadcasts**: Use Redis pub/sub for multi-instance deployments

---

## Security

- **PII Scrubbing**: GDPR/HIPAA compliance support
- **Multi-tenancy**: All services respect tenant isolation
- **Audit Trail**: Temporal graph provides complete change history
- **Cost Limits**: Prevent runaway API costs
- **Rate Limiting**: Rules Engine prevents abuse

---

## Support & Documentation

- **Issues**: Report bugs at GitHub Issues
- **Discussions**: Community support at GitHub Discussions
- **Docs**: Full documentation at `/docs`
- **API Reference**: Interactive docs at `/docs` (Swagger UI)
