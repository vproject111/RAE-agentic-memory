# Background Workers – Decay, Summarization, and Dreaming

This document describes the background maintenance workers in RAE that handle:
- **Memory importance decay** (aging memories over time)
- **Session summarization** (creating summaries from episodic memories)
- **Dreaming cycles** (generating reflections from historical patterns)

## Overview

RAE implements three key background workers that run periodically to maintain and enhance the memory system:

| Worker | Purpose | Frequency | Configuration |
|--------|---------|-----------|---------------|
| **DecayWorker** | Apply time-based decay to memory importance scores | Daily (2 AM) | `MEMORY_DECAY_RATE`, `MEMORY_BASE_DECAY_RATE` |
| **SummarizationWorker** | Create summaries of sessions with many events | Hourly / on-demand | `SUMMARIZATION_ENABLED`, `SUMMARIZATION_MIN_EVENTS` |
| **DreamingWorker** | Generate meta-reflections from high-importance memories | Daily (3 AM) | `DREAMING_ENABLED`, `DREAMING_LOOKBACK_HOURS` |

All workers are coordinated by the **MaintenanceScheduler** and respect system-wide configuration flags.

## Architecture

### Implementation Files

- **Core Implementation**: `apps/memory_api/workers/memory_maintenance.py`
- **Celery Tasks**: `apps/memory_api/tasks/background_tasks.py`
- **Tests**:
  - `tests/integration/test_decay_worker.py`
  - `apps/memory_api/tests/test_summarization_worker.py`
  - `tests/integration/test_dreaming_worker.py`

### Scheduling

Background tasks are scheduled using Celery Beat:
- `decay_memory_importance_task` - Daily at 2 AM
- `run_maintenance_cycle_task` - Daily at 3 AM (includes dreaming & summarization)
- `apply_memory_decay` - Hourly (legacy simple decay)

## 1. Decay Worker

### Purpose

The DecayWorker applies time-based importance decay to memories, ensuring that:
- Old, stale memories gradually lose importance
- Recently accessed memories are protected from aggressive decay
- Memory scores reflect both recency and relevance

### How It Works

1. **Get Tenant List**: Fetch all tenants with memories (or process specific tenants)
2. **Per-Tenant Processing**: For each tenant:
   - Query memories eligible for decay (importance > 0.01)
   - Calculate decay based on:
     - Base decay rate (configurable)
     - Time since last access (access stats)
     - Memory age
   - Update importance scores in bulk
3. **Record Metrics**: Track updated memory counts and duration per tenant

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MEMORY_DECAY_RATE` | `0.01` | Legacy decay rate (1% per day) |
| `MEMORY_BASE_DECAY_RATE` | `0.001` | Base decay rate per second |
| `MEMORY_MIN_DECAY_RATE` | `0.0001` | Minimum decay rate |
| `MEMORY_MAX_DECAY_RATE` | `0.01` | Maximum decay rate |
| `MEMORY_IMPORTANCE_DECAY_ENABLED` | `True` | Enable importance-based decay |
| `MEMORY_ACCESS_COUNT_BOOST` | configurable | Use access stats for decay calculation |

### Usage

#### Via Celery Task (Scheduled)

```python
# Automatically runs daily at 2 AM via Celery Beat
# No manual invocation needed
```

#### Via MaintenanceScheduler

```python
from apps.memory_api.workers.memory_maintenance import DecayWorker
import asyncpg

pool = await asyncpg.create_pool(database_url)
worker = DecayWorker(pool)

# Run decay for all tenants
stats = await worker.run_decay_cycle(
    tenant_ids=None,  # None = all tenants
    decay_rate=0.01,
    consider_access_stats=True
)

# Output: {'total_tenants': 5, 'total_updated': 1247}
```

#### Via CLI

```bash
python -m apps.memory_api.workers.memory_maintenance
```

### Decay Algorithm

The decay calculation in `ImportanceScoringService.decay_importance()` considers:

1. **Base Decay**: All memories decay at the base rate
2. **Accelerated Decay**: Memories not accessed for >30 days decay faster
3. **Protected Decay**: Recently accessed memories (<7 days) decay slower
4. **Minimum Threshold**: Memories below 0.01 importance are skipped

### Metrics

The worker emits Prometheus metrics:
- `rae_reflective_decay_updated_total{tenant_id}` - Total memories updated per tenant
- `rae_reflective_decay_duration_seconds{tenant_id}` - Duration per tenant

## 2. Summarization Worker

### Purpose

The SummarizationWorker creates concise summaries of episodic memory sessions:
- Reduces redundancy in long conversation sessions
- Creates higher-level semantic representations
- Improves context window efficiency for retrieval

### How It Works

1. **Session Detection**: Find sessions with sufficient events (`min_events`)
2. **Memory Retrieval**: Get episodic memories for the session
3. **LLM Summarization**: Use LLM to generate structured summary:
   - Summary text
   - Key topics
   - Sentiment
4. **Store Summary**: Save as episodic memory with special tags (`session_summary`, `auto_generated`)

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SUMMARIZATION_ENABLED` | `True` | Enable session summarization |
| `SUMMARIZATION_MIN_EVENTS` | `10` | Minimum events required for summarization |
| `SUMMARIZATION_EVENT_THRESHOLD` | `100` | Threshold for long sessions |

### Usage

#### Summarize a Specific Session

```python
from apps.memory_api.workers.memory_maintenance import SummarizationWorker
from uuid import UUID

pool = await asyncpg.create_pool(database_url)
worker = SummarizationWorker(pool)

summary = await worker.summarize_session(
    tenant_id="tenant-123",
    project_id="default",
    session_id=UUID("session-uuid"),
    min_events=10
)

# Returns: {'id': 'summary-id', 'content': 'Session summary...', ...}
```

#### Batch Summarize Long Sessions

```python
# Find all sessions with >100 events and summarize them
summaries = await worker.summarize_long_sessions(
    tenant_id="tenant-123",
    project_id="default",
    event_threshold=100
)

# Returns: [{'id': 'sum1', ...}, {'id': 'sum2', ...}]
```

### Summary Format

The LLM generates a structured summary using `SessionSummaryResponse` model:

```json
{
  "summary": "The user discussed database optimization strategies...",
  "key_topics": ["database", "optimization", "indexing", "performance"],
  "sentiment": "positive"
}
```

The final summary stored in memory:

```
The user discussed database optimization strategies, focusing on indexing and query performance improvements.

Key Topics: database, optimization, indexing, performance

Sentiment: positive
```

### Fallback Behavior

If LLM summarization fails, the worker uses a simple fallback:
- Concatenate first 5 memory contents
- Add count of remaining events

## 3. Dreaming Worker

### Purpose

The DreamingWorker implements "light dreaming" - periodic analysis of memory to:
- Identify patterns in recent high-importance memories
- Generate meta-level reflections and strategies
- Discover recurring themes or issues
- Synthesize insights across sessions

### How It Works

1. **Memory Sampling**: Query high-importance episodic memories from recent period
2. **Event Conversion**: Convert memories to `Event` objects for reflection context
3. **Reflection Generation**: Use `ReflectionEngineV2` to analyze patterns
4. **Store Insights**: Save reflections and strategies to Reflective Memory layer

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DREAMING_ENABLED` | `False` (lite mode) / `True` (full mode) | Enable dreaming cycles |
| `REFLECTIVE_MEMORY_ENABLED` | `True` | Master switch for reflective operations |
| `REFLECTIVE_MEMORY_MODE` | `"full"` | Mode: `"lite"` or `"full"` |
| `DREAMING_LOOKBACK_HOURS` | `24` | Hours to look back for memories |
| `DREAMING_MIN_IMPORTANCE` | `0.6` | Minimum importance to consider |
| `DREAMING_MAX_SAMPLES` | `20` | Maximum memories per cycle |

### Usage

#### Run Dreaming Cycle for Tenant

```python
from apps.memory_api.workers.memory_maintenance import DreamingWorker

pool = await asyncpg.create_pool(database_url)
worker = DreamingWorker(pool)

results = await worker.run_dreaming_cycle(
    tenant_id="tenant-123",
    project_id="default",
    lookback_hours=24,
    min_importance=0.6,
    max_samples=20
)

# Returns: [{'reflection_id': 'uuid', 'strategy_id': 'uuid'}]
```

#### Via Celery Task

```python
from apps.memory_api.tasks.background_tasks import run_dreaming_task

# Schedule dreaming for specific tenant
run_dreaming_task.delay(tenant_id="tenant-123", project_id="default")
```

### Dreaming Algorithm

1. **Query Memories**:
   ```sql
   SELECT id, content, importance, created_at, tags, metadata
   FROM memories
   WHERE tenant_id = $1
     AND project = $2
     AND layer = 'em'
     AND importance >= $3
     AND created_at >= NOW() - INTERVAL '$4 hours'
   ORDER BY importance DESC, created_at DESC
   LIMIT $5
   ```

2. **Create Reflection Context**:
   - Convert memories to events
   - Set outcome type to `PARTIAL` (exploratory)
   - Define task: "Analyzing patterns in recent high-importance memories"

3. **Generate Reflection**:
   - Use `ReflectionEngineV2.generate_reflection()`
   - Extract patterns, themes, strategies

4. **Store Results**:
   - Save reflection to Reflective Memory layer
   - Store strategies for future use

### Mode Differences

| Mode | Dreaming Enabled | Reflection Depth | Use Case |
|------|------------------|------------------|----------|
| **lite** | No | Basic | Cost-conscious deployments |
| **full** | Yes | Advanced | Full capability, enterprise |

## 4. Maintenance Scheduler

The `MaintenanceScheduler` coordinates all maintenance workers and provides a unified entry point.

### Usage

#### Run Daily Maintenance

```python
from apps.memory_api.workers.memory_maintenance import MaintenanceScheduler

pool = await asyncpg.create_pool(database_url)
scheduler = MaintenanceScheduler(pool)

# Run complete daily maintenance
stats = await scheduler.run_daily_maintenance(tenant_ids=None)

print(stats)
# Output:
# {
#   'decay': {'total_tenants': 5, 'total_updated': 1247},
#   'dreaming': {'tenants_processed': 5, 'reflections_generated': 3},
#   'summarization': {...},
#   'started_at': '2025-12-01T02:00:00Z',
#   'completed_at': '2025-12-01T02:05:23Z',
#   'config': {'reflective_enabled': True, 'mode': 'full', ...}
# }
```

#### Via Celery (Recommended)

```python
# Automatically runs daily at 3 AM via Celery Beat
# Defined in background_tasks.py:setup_periodic_tasks()
```

### Configuration Flags

The scheduler respects these global flags:

| Flag | Effect |
|------|--------|
| `REFLECTIVE_MEMORY_ENABLED=False` | Disables dreaming and advanced features |
| `DREAMING_ENABLED=False` | Disables only dreaming cycles |
| `SUMMARIZATION_ENABLED=False` | Disables session summarization |
| `REFLECTIVE_MEMORY_MODE="lite"` | Automatically disables dreaming |

## Monitoring and Observability

### Logs

All workers emit structured logs (via structlog):

```python
logger.info(
    "decay_cycle_completed",
    stats={'total_tenants': 5, 'total_updated': 1247},
    total_duration_seconds=123.45
)
```

### Metrics

Prometheus metrics are emitted:
- `rae_reflective_decay_updated_total`
- `rae_reflective_decay_duration_seconds`

### Error Handling

Workers implement graceful degradation:
- Per-tenant errors are logged and skipped (continues with other tenants)
- Celery tasks retry with exponential backoff (max 3 retries)
- Failures are recorded in structured logs for alerting

## Deployment Considerations

### Scheduling Options

1. **Celery Beat** (Recommended):
   - Defined in `background_tasks.py:setup_periodic_tasks()`
   - Automatic scheduling with monitoring

2. **Cron**:
   ```bash
   # /etc/crontab
   0 2 * * * python -m apps.memory_api.workers.memory_maintenance
   ```

3. **Kubernetes CronJob**:
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: rae-maintenance
   spec:
     schedule: "0 2 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: maintenance
               image: rae-memory:latest
               command: ["python", "-m", "apps.memory_api.workers.memory_maintenance"]
   ```

### Resource Requirements

| Worker | Memory | CPU | Duration (per 1000 memories) |
|--------|--------|-----|------------------------------|
| Decay | ~100MB | Low | ~5-10 seconds |
| Summarization | ~500MB | Medium | ~30-60 seconds (LLM calls) |
| Dreaming | ~1GB | High | ~2-5 minutes (reflection generation) |

### Scaling

- **Multi-tenant**: Workers process tenants sequentially - safe for concurrent execution
- **Parallelization**: Use multiple Celery workers for different tenant batches
- **Rate Limiting**: Built-in rate limiting for LLM calls (random delay 0.5-2s)

## Troubleshooting

### Decay Not Running

Check configuration:
```python
# Verify settings
MEMORY_IMPORTANCE_DECAY_ENABLED = True  # Must be True
```

Verify Celery task is scheduled:
```bash
celery -A apps.memory_api.celery_app inspect scheduled
```

### Summarization Skipped

Check reasons in logs:
- `reason="summarization_disabled"` → Set `SUMMARIZATION_ENABLED=True`
- `reason="insufficient_events"` → Session has < `SUMMARIZATION_MIN_EVENTS` events

### Dreaming Not Running

Verify configuration:
```python
REFLECTIVE_MEMORY_ENABLED = True
DREAMING_ENABLED = True
REFLECTIVE_MEMORY_MODE = "full"  # Not "lite"
```

Check logs for:
- `dreaming_cycle_skipped` with `reason="disabled_by_config"`
- `reason="insufficient_memories"` → Need at least 3 high-importance memories

## Related Documentation

- [Reflection Engine V2 Implementation](./REFLECTION_ENGINE_V2_IMPLEMENTATION.md) - Details on reflection generation
- [LLM Profiles and Cost Guard](./LLM_PROFILES_AND_COST_GUARD.md) - LLM configuration for workers
- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant isolation in workers
- [Test Coverage Map](./TEST_COVERAGE_MAP.md) - Worker test coverage

## API Reference

### DecayWorker

```python
class DecayWorker:
    async def run_decay_cycle(
        self,
        tenant_ids: Optional[List[str]] = None,
        decay_rate: float = 0.01,
        consider_access_stats: bool = True,
    ) -> Dict[str, int]
```

### SummarizationWorker

```python
class SummarizationWorker:
    async def summarize_session(
        self,
        tenant_id: str,
        project_id: str,
        session_id: UUID,
        min_events: int = 10,
    ) -> Optional[Dict[str, Any]]

    async def summarize_long_sessions(
        self,
        tenant_id: str,
        project_id: str,
        event_threshold: int = 100,
    ) -> List[Dict[str, Any]]
```

### DreamingWorker

```python
class DreamingWorker:
    async def run_dreaming_cycle(
        self,
        tenant_id: str,
        project_id: str,
        lookback_hours: int = 24,
        min_importance: float = 0.6,
        max_samples: int = 20,
    ) -> List[Dict[str, Any]]
```

### MaintenanceScheduler

```python
class MaintenanceScheduler:
    async def run_daily_maintenance(
        self, tenant_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]

    async def run_hourly_maintenance(self) -> Dict[str, Any]
```
