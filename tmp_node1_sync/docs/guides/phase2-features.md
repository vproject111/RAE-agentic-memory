# Phase 2 Advanced Features

This guide covers all advanced features introduced in Phase 2 of RAE.

## Table of Contents

- [Multi-Tenancy & RBAC](#multi-tenancy--rbac)
- [Analytics Service](#analytics-service)
- [Advanced GraphRAG](#advanced-graphrag)
- [Temporal Graphs](#temporal-graphs)
- [Importance Scoring](#importance-scoring)
- [Memory Consolidation](#memory-consolidation)
- [Plugin System](#plugin-system)

---

## Multi-Tenancy & RBAC

### Overview

RAE supports full multi-tenancy with role-based access control (RBAC) for enterprise deployments.

### Tenant Tiers

Three subscription tiers with different features and limits:

| Feature | FREE | PRO | ENTERPRISE |
|---------|------|-----|------------|
| Max Memories | 10,000 | 100,000 | Unlimited |
| Max Projects | 3 | 10 | Unlimited |
| API Calls/Day | 1,000 | 10,000 | Unlimited |
| GraphRAG | ❌ | ✅ | ✅ |
| Analytics | ❌ | ✅ | ✅ |
| SSO | ❌ | ❌ | ✅ |
| Audit Logs | ❌ | ❌ | ✅ |

### Creating a Tenant

```python
from apps.memory_api.models import Tenant, TenantTier, TenantConfig

# Create FREE tier tenant
tenant = Tenant(
    id=uuid4(),
    name="Acme Corp",
    tier=TenantTier.FREE,
    config=Tenant.get_default_config_for_tier(TenantTier.FREE),
    contact_email="admin@acme.com"
)

# Create ENTERPRISE tier with custom config
enterprise_tenant = Tenant(
    id=uuid4(),
    name="BigCorp Inc",
    tier=TenantTier.ENTERPRISE,
    config=TenantConfig(
        max_memories=-1,  # Unlimited
        enable_graphrag=True,
        enable_analytics=True,
        encryption_enabled=True,
        sso_enabled=True
    )
)
```

### Role-Based Access Control

Five roles with hierarchical permissions:

#### Roles

1. **OWNER** (Level 5)
   - Full access to everything
   - Can delete tenant
   - Can assign any role

2. **ADMIN** (Level 4)
   - Manage users, settings, billing
   - Cannot delete tenant
   - Can assign roles below ADMIN

3. **DEVELOPER** (Level 3)
   - Full API access
   - Read/write memories
   - Access GraphRAG and reflections

4. **ANALYST** (Level 2)
   - Analytics and read-only access
   - Can view memories and graphs
   - Cannot modify data

5. **VIEWER** (Level 1)
   - Read-only access to memories
   - No analytics or admin access

#### Assigning Roles

```python
from apps.memory_api.services.rbac_service import RBACService
from apps.memory_api.models import Role

rbac = RBACService()

# Assign developer role to user
user_role = await rbac.assign_role(
    user_id="user_123",
    tenant_id=tenant_id,
    role=Role.DEVELOPER,
    assigned_by="admin_user",
    project_ids=["project_1", "project_2"]  # Optional project scope
)

# Check permissions
allowed, reason = await check_permission(
    user_id="user_123",
    tenant_id=tenant_id,
    action="memories:write"
)

if not allowed:
    print(f"Access denied: {reason}")
```

#### Permission Actions

```
memories:read, memories:write, memories:delete
graph:read, graph:write
reflections:read, reflections:write
analytics:read
users:read, users:write, users:delete
settings:read, settings:write
billing:read, billing:write
```

### Checking Quotas

```python
# Check if tenant has quota available
if tenant.has_quota_available("memories"):
    # Create memory
    tenant.increment_usage("memories")
else:
    raise QuotaExceededError("Memory quota exceeded")
```

---

## Analytics Service

### Overview

Enterprise-tier analytics for monitoring usage, performance, and costs.

### Getting Tenant Statistics

```python
from apps.memory_api.services.analytics import AnalyticsService

analytics = AnalyticsService(db, redis, vector_store)

# Get comprehensive stats
stats = await analytics.get_tenant_stats(
    tenant_id=tenant_id,
    period_days=30
)

print(f"Total memories: {stats['memories']['total']}")
print(f"API calls today: {stats['api_usage']['requests_today']}")
print(f"Cache hit rate: {stats['performance']['cache_hit_rate']}")
```

### Statistics Categories

#### Memory Stats
- Total memories by layer
- Growth rate per day
- Storage size
- Most active projects

#### Query Stats
- Total queries
- Average latency (P50, P95, P99)
- Most common queries
- Success rate

#### Knowledge Graph Stats
- Nodes and edges
- Graph density
- Top entities by centrality
- Communities detected

#### Reflection Stats
- Total reflections generated
- Average insight quality
- Success rate
- Processing time

#### API Usage
- Requests by endpoint
- Error rate
- Rate limit hits
- Peak usage hours

#### Performance Metrics
- Response times
- Cache hit rate
- Database query time
- Vector search time

#### Cost Tracking
- LLM API calls
- Token usage
- Estimated costs (LLM, storage, compute)

### Generating Reports

```python
# Generate JSON report
report = await analytics.generate_report(
    tenant_id=tenant_id,
    period_days=30,
    format="json"
)

# Generate CSV report
csv_report = await analytics.generate_report(
    tenant_id=tenant_id,
    period_days=30,
    format="csv"
)

# Real-time metrics (not cached)
real_time = await analytics.get_real_time_metrics(tenant_id)
print(f"Current RPS: {real_time['requests_per_second']}")
```

---

## Advanced GraphRAG

### Overview

Advanced graph algorithms for knowledge graph analysis and traversal.

### PageRank

Calculate entity importance based on graph structure:

```python
from apps.memory_api.services.graph_algorithms import GraphAlgorithmsService

graph_service = GraphAlgorithmsService(db, vector_store)

# Calculate PageRank
scores = await graph_service.pagerank(
    tenant_id=tenant_id,
    damping=0.85,
    max_iterations=100
)

# Get top 10 most important entities
top_entities = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

for entity_id, score in top_entities:
    print(f"{entity_id}: {score:.4f}")
```

### Community Detection

Identify clusters of related entities:

```python
# Detect communities using Louvain method
communities = await graph_service.community_detection(
    tenant_id=tenant_id,
    algorithm="louvain"
)

# Or use label propagation
communities = await graph_service.community_detection(
    tenant_id=tenant_id,
    algorithm="label_propagation"
)

# Group entities by community
community_groups = {}
for entity_id, community_id in communities.items():
    if community_id not in community_groups:
        community_groups[community_id] = []
    community_groups[community_id].append(entity_id)
```

### Shortest Path

Find connections between entities:

```python
# Find shortest path
path = await graph_service.shortest_path(
    tenant_id=tenant_id,
    source_id="entity_1",
    target_id="entity_2",
    max_hops=10
)

if path:
    print(f"Path: {' -> '.join(path)}")
    print(f"Distance: {len(path) - 1} hops")

# Find all paths (up to max_paths)
all_paths = await graph_service.find_all_paths(
    tenant_id=tenant_id,
    source_id="entity_1",
    target_id="entity_2",
    max_hops=5,
    max_paths=10
)
```

### Finding Related Entities

```python
# Find entities related to given entity within 2 hops
related = await graph_service.find_related_entities(
    tenant_id=tenant_id,
    entity_id="person:john_doe",
    max_distance=2,
    limit=20
)

for entity in related:
    print(f"{entity['entity_id']} - {entity['relation']} - Distance: {entity['distance']}")
```

### Centrality Measures

```python
# Degree centrality (number of connections)
degree = await graph_service.calculate_centrality(
    tenant_id=tenant_id,
    method="degree"
)

# Betweenness centrality (bridge nodes)
betweenness = await graph_service.calculate_centrality(
    tenant_id=tenant_id,
    method="betweenness"
)

# Closeness centrality (average distance to all nodes)
closeness = await graph_service.calculate_centrality(
    tenant_id=tenant_id,
    method="closeness"
)
```

### Graph Summary

```python
# Get comprehensive graph statistics
summary = await graph_service.graph_summary(tenant_id)

print(f"Nodes: {summary['num_nodes']}")
print(f"Edges: {summary['num_edges']}")
print(f"Density: {summary['density']:.4f}")
print(f"Avg Degree: {summary['avg_degree']:.2f}")
print(f"Node Types: {summary['node_types']}")
```

---

## Temporal Graphs

### Overview

Track how your knowledge graph evolves over time.

### Creating Snapshots

```python
from apps.memory_api.services.temporal_graph import TemporalGraphService

temporal = TemporalGraphService(db, vector_store)

# Create snapshot of current graph state
snapshot = await temporal.create_snapshot(
    tenant_id=tenant_id,
    graph=current_graph,
    metadata={"trigger": "daily_backup"}
)
```

### Time Travel Queries

```python
# Reconstruct graph as it existed at specific time
past_graph = await temporal.reconstruct_graph_at_time(
    tenant_id=tenant_id,
    timestamp=datetime(2024, 1, 1, 12, 0, 0)
)

# Get specific snapshot
snapshot = await temporal.get_snapshot_at_time(
    tenant_id=tenant_id,
    timestamp=datetime(2024, 1, 1)
)
```

### Tracking Changes

```python
from apps.memory_api.services.temporal_graph import GraphChange, ChangeType

# Record a change
change = GraphChange(
    change_type=ChangeType.NODE_ADDED,
    timestamp=datetime.utcnow(),
    entity_id="new_entity",
    entity_type="node",
    new_value={"entity_type": "person", "properties": {}}
)

await temporal.record_change(tenant_id, change)

# Get changes in time range
changes = await temporal.get_changes(
    tenant_id=tenant_id,
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    change_types=[ChangeType.NODE_ADDED, ChangeType.EDGE_ADDED]
)
```

### Entity History

```python
# Get complete history for an entity
history = await temporal.get_entity_history(
    tenant_id=tenant_id,
    entity_id="person:john_doe"
)

for change in history:
    print(f"{change.timestamp}: {change.change_type} - {change.entity_id}")
```

### Comparing Graphs

```python
# Compare two graphs
diff = await temporal.compare_graphs(old_graph, new_graph)

print(f"Nodes added: {diff['nodes_added_count']}")
print(f"Nodes removed: {diff['nodes_removed_count']}")
print(f"Edges added: {diff['edges_added_count']}")
print(f"Total changes: {diff['total_changes']}")
```

### Growth Metrics

```python
# Calculate graph growth over period
growth = await temporal.get_growth_metrics(
    tenant_id=tenant_id,
    period_days=30
)

print(f"Node growth: {growth['nodes']['growth']} ({growth['nodes']['growth_rate']:.1%})")
print(f"Daily node growth: {growth['nodes']['daily_growth']:.2f}")
```

### Emerging Patterns

```python
# Find emerging patterns and trends
patterns = await temporal.find_emerging_patterns(
    tenant_id=tenant_id,
    window_days=7
)

for pattern in patterns:
    if pattern['type'] == 'rapidly_growing_entity':
        print(f"Trending: {pattern['entity_id']} - {pattern['new_connections']} connections")
```

---

## Importance Scoring

### Overview

Automatic memory prioritization based on multiple factors.

### Calculating Importance

```python
from apps.memory_api.services.importance_scoring import (
    ImportanceScoringService,
    Memory,
    ScoringFactors
)

# Initialize service with custom weights
scoring = ImportanceScoringService(
    db=db,
    vector_store=vector_store,
    scoring_factors=ScoringFactors(
        recency=0.15,
        access_frequency=0.20,
        graph_centrality=0.15,
        semantic_relevance=0.15,
        user_rating=0.10,
        consolidation=0.10,
        manual_boost=0.15
    )
)

# Calculate importance for a memory
memory = Memory(
    id="mem_123",
    content="Important information about authentication",
    layer="semantic",
    tenant_id=tenant_id,
    created_at=datetime.utcnow(),
    access_count=50,
    graph_centrality=0.8
)

importance = await scoring.calculate_importance(memory)
print(f"Importance: {importance:.3f} ({memory.importance_level.value})")
```

### Scoring Factors

- **Recency**: Exponential decay (half-life: 7 days)
- **Access Frequency**: Logarithmic scale with recency boost
- **Graph Centrality**: Position in knowledge graph
- **Semantic Relevance**: Similarity to recent queries
- **User Rating**: Explicit 1-5 star ratings
- **Consolidation**: Bonus for consolidated memories
- **Manual Boost**: User-specified importance

### Importance Levels

| Level | Score Range | Description |
|-------|-------------|-------------|
| CRITICAL | > 0.8 | Essential knowledge |
| HIGH | 0.6 - 0.8 | Important information |
| MEDIUM | 0.4 - 0.6 | Standard relevance |
| LOW | 0.2 - 0.4 | Lower priority |
| MINIMAL | ≤ 0.2 | Archival candidate |

### Bulk Recalculation

```python
# Recalculate all memories for tenant
stats = await scoring.recalculate_all_scores(
    tenant_id=tenant_id,
    batch_size=100
)

print(f"Processed: {stats['total_processed']}")
print(f"By level: {stats['by_level']}")
```

### Top Important Memories

```python
# Get most important memories
top_memories = await scoring.get_top_important_memories(
    tenant_id=tenant_id,
    limit=20,
    layer="semantic",
    min_score=0.6
)
```

### Manual Adjustments

```python
# Boost memory importance
await scoring.boost_importance(
    memory_id="mem_123",
    boost_amount=0.2,
    reason="Critical security information"
)

# Auto-archive low importance memories
archived = await scoring.auto_archive_low_importance(
    tenant_id=tenant_id,
    threshold=0.1,
    min_age_days=90
)
```

### Importance Explanation

```python
# Get detailed explanation of score
explanation = scoring.get_scoring_explanation(memory)

print(f"Overall: {explanation['overall_score']:.3f}")
print("Factors:")
for factor, details in explanation['factors'].items():
    print(f"  {factor}: weight={details['weight']}")
```

---

## Memory Consolidation

### Overview

Automatic consolidation of memories through layers:
**Episodic → Working → Semantic → LTM**

### Consolidation Process

```python
from apps.memory_api.services.memory_consolidation import (
    MemoryConsolidationService,
    ConsolidationStrategy
)

consolidation = MemoryConsolidationService(db, vector_store, llm_client)

# Run full automatic consolidation pipeline
summary = await consolidation.run_automatic_consolidation(tenant_id)

print(f"Total consolidated: {summary['total_consolidated']}")
print(f"Episodic→Working: {len(summary['episodic_to_working'])}")
print(f"Working→Semantic: {len(summary['working_to_semantic'])}")
print(f"Semantic→LTM: {len(summary['semantic_to_ltm'])}")
```

### Manual Consolidation

```python
# Consolidate episodic to working memory
results = await consolidation.consolidate_episodic_to_working(
    tenant_id=tenant_id,
    max_memories=100,
    min_importance=0.5
)

# Consolidate working to semantic
results = await consolidation.consolidate_working_to_semantic(
    tenant_id=tenant_id,
    max_memories=50,
    min_age_days=7
)

# Consolidate semantic to LTM
results = await consolidation.consolidate_semantic_to_ltm(
    tenant_id=tenant_id,
    max_memories=20,
    min_age_days=30,
    min_importance=0.7
)
```

### Consolidation Strategies

- **PATTERN_BASED**: Group by recurring patterns
- **IMPORTANCE_BASED**: Consolidate high-importance memories
- **TIME_BASED**: Consolidate after time threshold
- **SEMANTIC_CLUSTER**: Group semantically similar memories
- **MANUAL**: User-triggered consolidation

### Preview Consolidation

```python
# Preview what consolidation would produce
preview = await consolidation.preview_consolidation(
    tenant_id=tenant_id,
    memory_ids=["mem_1", "mem_2", "mem_3"]
)

print(f"Preview:\n{preview['preview_content']}")
print(f"Target layer: {preview['estimated_layer']}")
```

### Revert Consolidation

```python
# Undo consolidation
success = await consolidation.revert_consolidation(
    consolidated_memory_id="consolidated_123"
)
```

### Consolidation Statistics

```python
# Get consolidation stats
stats = await consolidation.get_consolidation_stats(
    tenant_id=tenant_id,
    period_days=30
)

print(f"Total consolidations: {stats['total_consolidations']}")
print(f"Success rate: {stats['success_rate']:.1%}")
```

---

## Plugin System

### Overview

Extend RAE with custom plugins for notifications, validation, analytics, and more.

### Creating a Plugin

```python
from apps.memory_api.plugins.base import Plugin, PluginMetadata, PluginHook
from typing import Dict, Any
from uuid import UUID

class MyCustomPlugin(Plugin):
    """Custom plugin example"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_custom_plugin",
            version="1.0.0",
            author="Your Name",
            description="Description of what this plugin does",
            hooks=[
                PluginHook.AFTER_MEMORY_CREATE,
                PluginHook.BEFORE_QUERY
            ],
            config=self.config
        )

    async def initialize(self):
        """Called when plugin is loaded"""
        await super().initialize()
        # Your initialization code here
        self.api_key = self.config.get("api_key")

    async def on_after_memory_create(
        self,
        tenant_id: UUID,
        memory_id: str,
        memory_data: Dict[str, Any]
    ):
        """Called after memory is created"""
        self.logger.info(
            "memory_created",
            memory_id=memory_id,
            layer=memory_data.get("layer")
        )

    async def on_before_query(
        self,
        tenant_id: UUID,
        query: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify query parameters"""
        # Add custom parameter
        params["custom_field"] = "custom_value"
        return params
```

### Registering Plugins

```python
from apps.memory_api.plugins.base import get_plugin_registry

# Get global registry
registry = get_plugin_registry()

# Register plugin
plugin = MyCustomPlugin(config={"api_key": "secret"})
registry.register(plugin)

# Initialize all plugins
await registry.initialize_all()
```

### Using Plugins

```python
# Execute a hook
result = await registry.execute_hook(
    PluginHook.AFTER_MEMORY_CREATE,
    tenant_id=tenant_id,
    memory_id="mem_123",
    memory_data={"content": "test", "layer": "episodic"}
)
```

### Example Plugins

#### 1. Slack Notifier

```python
from apps.memory_api.plugins.examples import SlackNotifierPlugin

slack = SlackNotifierPlugin(config={
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "channel": "#rae-notifications",
    "notify_on_create": False,
    "notify_on_reflection": True,
    "notify_on_consolidation": True
})

registry.register(slack)
```

#### 2. Memory Validator

```python
from apps.memory_api.plugins.examples import MemoryValidatorPlugin

validator = MemoryValidatorPlugin(config={
    "min_content_length": 10,
    "max_content_length": 50000,
    "auto_tag": True,
    "profanity_filter": True
})

registry.register(validator)
```

#### 3. Analytics Tracker

```python
from apps.memory_api.plugins.examples import AnalyticsTrackerPlugin

tracker = AnalyticsTrackerPlugin(config={
    "track_creates": True,
    "track_queries": True,
    "track_reflections": True
})

registry.register(tracker)

# Get analytics
analytics = tracker.get_analytics()
print(f"Total creates: {analytics['totals']['creates']}")
```

### Available Hooks

- `BEFORE_MEMORY_CREATE` - Before creating memory
- `AFTER_MEMORY_CREATE` - After creating memory
- `BEFORE_MEMORY_UPDATE` - Before updating memory
- `AFTER_MEMORY_UPDATE` - After updating memory
- `BEFORE_MEMORY_DELETE` - Before deleting memory
- `AFTER_MEMORY_DELETE` - After deleting memory
- `BEFORE_QUERY` - Before executing query
- `AFTER_QUERY` - After executing query
- `QUERY_RESULTS_TRANSFORM` - Transform query results
- `BEFORE_REFLECTION` - Before generating reflection
- `AFTER_REFLECTION` - After generating reflection
- `BEFORE_CONSOLIDATION` - Before consolidating memories
- `AFTER_CONSOLIDATION` - After consolidating memories
- `METRICS_COLLECTED` - When metrics are collected
- `NOTIFICATION` - General notifications
- `ALERT` - System alerts
- `STARTUP` - System startup
- `SHUTDOWN` - System shutdown
- `HEALTH_CHECK` - Health check requests

### Plugin Health Checks

```python
# Check all plugins
health = await registry.health_check_all()

for plugin_name, status in health.items():
    print(f"{plugin_name}: {status['status']}")
```

### Loading Plugins from Directory

```python
# Load all plugins from directory
registry.load_plugins_from_directory("./custom_plugins")
```

---

## Best Practices

### Multi-Tenancy
1. Always check quotas before operations
2. Use appropriate tier for workload
3. Monitor usage regularly
4. Set up alerts for quota limits

### RBAC
1. Follow principle of least privilege
2. Use project scoping when possible
3. Audit role assignments regularly
4. Never share API keys between users

### Analytics
1. Enable analytics for enterprise tiers
2. Review metrics dashboard weekly
3. Set up alerts for anomalies
4. Export reports for compliance

### GraphRAG
1. Run PageRank periodically to update importance
2. Use community detection for topic discovery
3. Cache centrality calculations
4. Limit graph traversal depth

### Temporal Graphs
1. Create daily snapshots
2. Clean up old snapshots (90-day retention)
3. Use for debugging and auditing
4. Track critical entity changes

### Importance Scoring
1. Recalculate scores daily
2. Review undervalued memories weekly
3. Archive low-importance memories (>90 days)
4. Use manual boosts sparingly

### Memory Consolidation
1. Run automatic consolidation nightly
2. Preview before bulk operations
3. Monitor consolidation success rate
4. Keep consolidation history for auditing

### Plugin System
1. Test plugins thoroughly before deployment
2. Use health checks to monitor plugin status
3. Handle errors gracefully in plugins
4. Log plugin operations for debugging

---

## Troubleshooting

### Common Issues

#### Quota Exceeded
```python
# Check current usage
print(f"Memories: {tenant.current_memory_count}/{tenant.config.max_memories}")

# Upgrade tier or clean up old memories
```

#### Permission Denied
```python
# Check user role
user_role = await rbac.get_user_role(user_id, tenant_id)
print(f"Role: {user_role.role.value if user_role else 'None'}")

# Check specific permission
allowed, reason = await check_permission(user_id, tenant_id, "memories:write")
```

#### Plugin Not Working
```python
# Check plugin status
health = await registry.health_check_all()
print(health["my_plugin"])

# Check plugin is enabled
plugin = registry.get("my_plugin")
print(f"Enabled: {plugin.metadata.enabled}")
```

#### Consolidation Failing
```python
# Check consolidation stats
stats = await consolidation.get_consolidation_stats(tenant_id)
print(f"Success rate: {stats['success_rate']}")

# Preview consolidation
preview = await consolidation.preview_consolidation(tenant_id, memory_ids)
```

---

## Next Steps

- [Production Deployment Guide](production-deployment.md)
- [Performance Tuning](performance-tuning.md)
- [Security Best Practices](security-best-practices.md)
- [API Reference](../api/rest-api.md)

---

For questions or support, visit: https://github.com/yourusername/rae-memory-api
