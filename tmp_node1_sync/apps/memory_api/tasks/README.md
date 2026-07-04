# RAE Background Tasks (Celery)

**Asynchronous task processing for RAE Memory API** using Celery for long-running and scheduled operations.

![Celery](https://img.shields.io/badge/Celery-5.3+-green)
![Redis](https://img.shields.io/badge/Redis-7+-red)
![Coverage](https://img.shields.io/badge/Test_Coverage-60%+-brightgreen)

## Overview

Background tasks handle operations that are:
- **Too slow** for synchronous API requests
- **Scheduled** to run periodically
- **Resource-intensive** (graph extraction, reflection generation)
- **Optional** for immediate response (can be processed later)

This keeps the API fast and responsive while performing heavy operations in the background.

## Architecture

```
┌──────────────────┐
│   RAE Memory     │
│      API         │──────┐
└──────────────────┘      │
                          │ Enqueue task
                          ↓
                    ┌──────────────┐
                    │    Redis     │
                    │   (Broker)   │
                    └──────┬───────┘
                           │
                           │ Fetch task
                           ↓
                    ┌──────────────┐
                    │    Celery    │
                    │    Worker    │
                    └──────┬───────┘
                           │
                           │ Store result
                           ↓
                    ┌──────────────┐
                    │    Redis     │
                    │  (Backend)   │
                    └──────────────┘
```

**Components:**
- **Celery Worker** - Executes background tasks
- **Celery Beat** - Scheduler for periodic tasks
- **Redis** - Message broker (queue) and result backend
- **PostgreSQL** - Data storage accessed by tasks

## Background Tasks

### 1. Graph Extraction (Lazy)

**Task:** `extract_graph_lazy(memory_id, tenant_id, project_id)`

**Purpose:** Extract knowledge graph triples from memory content asynchronously.

**When triggered:**
- Memory is created with `extract_graph_lazy=True`
- User explicitly requests lazy extraction via API

**What it does:**
1. Fetches memory content from database
2. Calls ML Service or LLM to extract triples
3. Stores extracted entities and relationships
4. Updates memory metadata with extraction timestamp

**Cost optimization:**
- Uses mini model (e.g., GPT-4o-mini) to reduce cost
- Configured via `settings.MINI_MODEL`

**Example:**
```python
# Enqueue task
task = extract_graph_lazy.delay(
    memory_id="mem_123",
    tenant_id="tenant_456",
    project_id="project_789"
)

# Check status
print(task.status)  # PENDING, STARTED, SUCCESS, FAILURE
```

---

### 2. Graph Extraction Queue Processor

**Task:** `process_graph_extraction_queue()`

**Purpose:** Process all memories pending graph extraction in batch.

**Schedule:** Runs every 5 minutes (configurable)

**What it does:**
1. Queries database for memories with `graph_extracted = false`
2. Schedules `extract_graph_lazy` task for each memory
3. Logs statistics (memories processed, tasks scheduled)

**Batch processing benefits:**
- Efficient resource usage
- Predictable cost patterns
- Avoids overwhelming ML Service
- Can be paused/resumed easily

---

### 3. Reflection Generation

**Task:** `generate_reflection_for_project(project, tenant_id)`

**Purpose:** Generate high-level reflections from recent episodic memories.

**When triggered:**
- Scheduled by `schedule_reflections` task
- Manually via API: `POST /v1/reflection/generate`

**What it does:**
1. Fetches recent episodic memories (last 24h-7d)
2. Analyzes patterns, themes, insights
3. Uses ReflectionEngine to generate structured reflection
4. Stores reflection in database
5. Sends notification (if configured)

**Example reflection:**
```json
{
  "project": "ai-research",
  "reflection": {
    "summary": "Focus on transformer architectures and attention mechanisms",
    "key_insights": [
      "Attention is all you need",
      "Scaling laws for neural LMs"
    ],
    "suggested_actions": [
      "Explore multi-head attention variants",
      "Benchmark performance on downstream tasks"
    ]
  }
}
```

---

### 4. Reflection Scheduler

**Task:** `schedule_reflections()`

**Purpose:** Find projects with recent activity and trigger reflection generation.

**Schedule:** Runs every 1 hour

**What it does:**
1. Queries for projects with episodic memories in last hour
2. For each project, schedules `generate_reflection_for_project`
3. Avoids duplicate reflections (checks last reflection timestamp)

**SQL query:**
```sql
SELECT DISTINCT project, tenant_id
FROM memories
WHERE layer = 'em'
  AND created_at > NOW() - INTERVAL '1 hour'
```

---

### 5. Memory Decay

**Task:** `apply_memory_decay()`

**Purpose:** Apply decay factor to memory strength over time.

**Schedule:** Runs daily at 2 AM

**What it does:**
1. Updates all memory strengths: `strength = strength * decay_rate`
2. Deletes memories with `expires_at < NOW()`
3. Logs statistics (memories decayed, expired deleted)

**Configuration:**
- `settings.MEMORY_DECAY_RATE` - Decay factor (default: 0.95 = 5% decay)
- `settings.ENABLE_MEMORY_DECAY` - Enable/disable decay (default: true)

**Example:**
```
Day 0: strength = 1.0
Day 1: strength = 0.95
Day 2: strength = 0.90
Day 7: strength = 0.70
Day 30: strength = 0.21  # Nearly forgotten
```

---

### 6. Old Memory Pruning

**Task:** `prune_old_memories()`

**Purpose:** Delete old episodic memories to manage data lifecycle.

**Schedule:** Runs daily at 3 AM

**Status:** ⚠️ DEPRECATED - Use `cleanup_expired_data_task` instead (ISO 42001 compliance)

**What it does:**
1. Checks `settings.MEMORY_RETENTION_DAYS`
2. If > 0, deletes memories older than retention period
3. Only affects episodic layer (`layer = 'em'`)
4. Preserves semantic and long-term memories

**Configuration:**
- `settings.MEMORY_RETENTION_DAYS` - Retention period (0 = disabled)

---

### 7. Entity Resolution (Batch)

**Task:** `resolve_entities_batch(tenant_id, project_id)`

**Purpose:** Find and merge duplicate entities in knowledge graph.

**When triggered:**
- Manually via API: `POST /v1/graph/resolve-entities`
- Scheduled weekly (optional)

**What it does:**
1. Fetches all entities for project
2. Calls EntityResolutionService to cluster similar entities
3. Merges duplicate entities (e.g., "NYC" → "New York")
4. Updates all relationships to point to canonical entities
5. Logs merge operations for audit trail

**Example:**
```python
# Before
Entity: "New York", "NYC", "New York City"

# After resolution
Entity: "New York"
Aliases: ["NYC", "New York City"]
```

---

### 8. Community Detection

**Task:** `detect_communities(tenant_id, project_id)`

**Purpose:** Detect communities (clusters) in knowledge graph.

**When triggered:**
- After major graph updates
- Manually via API

**What it does:**
1. Builds graph from entities and relationships
2. Applies Louvain algorithm to detect communities
3. Stores community assignments in metadata
4. Updates graph statistics

**Use cases:**
- Topic clustering
- Related entity grouping
- Graph visualization improvements

---

### 9. Context Cache Rebuild

**Task:** `rebuild_context_cache_task(tenant_id, project_id)`

**Purpose:** Rebuild context cache for faster queries.

**When triggered:**
- After bulk imports
- Cache invalidation
- Manual refresh

**What it does:**
1. Clears existing cache entries
2. Pre-computes common queries
3. Stores results in Redis
4. Warms up embedding cache

---

## Task Scheduling

### Celery Beat Configuration

```python
# In celery_app.py
celery_app.conf.beat_schedule = {
    'process-graph-queue': {
        'task': 'apps.memory_api.tasks.background_tasks.process_graph_extraction_queue',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'schedule-reflections': {
        'task': 'apps.memory_api.tasks.background_tasks.schedule_reflections',
        'schedule': crontab(hour='*'),  # Hourly
    },
    'apply-decay': {
        'task': 'apps.memory_api.tasks.background_tasks.apply_memory_decay',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'prune-old': {
        'task': 'apps.memory_api.tasks.background_tasks.prune_old_memories',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}
```

### Custom Schedules

To add a new scheduled task:

```python
@celery_app.task
def my_custom_task():
    """Your custom background task."""
    # Task logic here
    pass

# In beat_schedule:
'my-task': {
    'task': 'apps.memory_api.tasks.background_tasks.my_custom_task',
    'schedule': crontab(hour='*/4'),  # Every 4 hours
}
```

## Running Tasks

### Docker Compose (Recommended)

Background tasks run automatically with Docker Compose:

```bash
# Start all services including Celery
docker compose up -d

# View Celery worker logs
docker compose logs -f celery-worker

# View Celery beat logs
docker compose logs -f celery-beat
```

**Services:**
- `celery-worker` - Executes tasks
- `celery-beat` - Schedules periodic tasks

### Manual Execution

For development or testing:

```bash
# Start Celery worker
celery -A apps.memory_api.celery_app worker --loglevel=info --concurrency=2

# Start Celery beat (scheduler)
celery -A apps.memory_api.celery_app beat --loglevel=info

# Run both together
celery -A apps.memory_api.celery_app worker --beat --loglevel=info
```

### Triggering Tasks Manually

#### From Python:

```python
from apps.memory_api.tasks.background_tasks import extract_graph_lazy

# Synchronous (blocks until complete)
result = extract_graph_lazy("mem_123", "tenant_456", "project_789")

# Asynchronous (returns immediately)
task = extract_graph_lazy.delay("mem_123", "tenant_456", "project_789")
print(task.id)  # Task ID for tracking

# Check status
print(task.status)  # PENDING, STARTED, SUCCESS, FAILURE

# Wait for result (with timeout)
result = task.get(timeout=30)
```

#### From API:

```bash
# Trigger graph extraction
curl -X POST http://localhost:8000/v1/memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Meeting with Sarah about Q3 roadmap",
    "extract_graph_lazy": true
  }'

# Trigger reflection generation
curl -X POST http://localhost:8000/v1/reflection/generate \
  -H "Content-Type: application/json" \
  -d '{
    "project": "ai-research",
    "tenant_id": "demo-tenant"
  }'
```

## Monitoring

### Celery Flower (Web UI)

```bash
# Install Flower
pip install flower

# Start Flower
celery -A apps.memory_api.celery_app flower

# Access at http://localhost:5555
```

**Features:**
- Real-time task monitoring
- Worker status and statistics
- Task history and results
- Retry failed tasks
- Rate limiting configuration

### Task Status via API

```python
from celery.result import AsyncResult

task_id = "abc123..."
result = AsyncResult(task_id, app=celery_app)

print(result.status)      # PENDING, STARTED, SUCCESS, FAILURE
print(result.result)      # Task return value (if SUCCESS)
print(result.traceback)   # Error traceback (if FAILURE)
```

### Logging

Tasks use structured logging:

```python
logger.info(
    "graph_extraction_started",
    memory_id=memory_id,
    tenant_id=tenant_id,
    project_id=project_id
)
```

**Log levels:**
- `INFO` - Task start/completion
- `WARNING` - Retries, degraded performance
- `ERROR` - Task failures
- `DEBUG` - Detailed execution steps

## Testing

### Running Tests

```bash
# Run all background task tests
pytest apps/memory_api/tests/test_background_tasks.py -v

# Run specific test
pytest apps/memory_api/tests/test_background_tasks.py::TestExtractGraphLazy::test_extract_graph_success

# Run with coverage
pytest --cov=apps.memory_api.tasks --cov-report=html apps/memory_api/tests/test_background_tasks.py
```

**Test coverage:**
- 10 test functions
- 334 lines of test code
- Target: 60%+ coverage

### Test Examples

```python
def test_extract_graph_success(self, mock_service_class, mock_get_pool):
    """Test successful graph extraction."""
    # Arrange
    mock_pool = AsyncMock()
    mock_get_pool.return_value = mock_pool

    # Act
    extract_graph_lazy("mem_123", "tenant_456", "project_789")

    # Assert
    mock_service_class.assert_called_once()
    mock_pool.close.assert_called_once()
```

### Testing with Celery Eager Mode

For unit tests, use eager mode (executes tasks synchronously):

```python
# In conftest.py
@pytest.fixture
def celery_config():
    return {
        'task_always_eager': True,
        'task_eager_propagates': True,
    }
```

## Configuration

### Environment Variables

```bash
# Celery configuration
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Task configuration
MEMORY_DECAY_RATE=0.95
MEMORY_RETENTION_DAYS=90
ENABLE_MEMORY_DECAY=true

# Graph extraction
MINI_MODEL=gpt-4o-mini  # Cost-optimized model for background tasks
```

### Celery Settings

```python
# In celery_app.py
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=600,        # 10 minutes max per task
    task_soft_time_limit=540,   # Soft limit at 9 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,        # Acknowledge after completion
    worker_concurrency=2,       # Number of worker processes
)
```

## Error Handling

### Automatic Retries

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def my_task(self, arg):
    try:
        # Task logic
        pass
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### Dead Letter Queue

Failed tasks after max retries are logged but not requeued:

```python
logger.error(
    "task_failed_permanently",
    task_id=self.request.id,
    retries=self.request.retries,
    error=str(exc)
)
```

## Performance

### Optimization Tips

1. **Batch processing**: Process multiple items per task
2. **Concurrency**: Scale workers horizontally
3. **Prefetch**: Adjust `worker_prefetch_multiplier`
4. **Priorities**: Use task priorities for important tasks
5. **Rate limiting**: Prevent overwhelming external services

### Scaling Workers

```bash
# Horizontal scaling
docker compose up --scale celery-worker=4

# Vertical scaling (more threads per worker)
celery -A apps.memory_api.celery_app worker --concurrency=8
```

## Troubleshooting

### Tasks stuck in PENDING

**Cause:** Worker not running or not connected to broker

**Fix:**
```bash
# Check worker status
docker compose ps celery-worker

# Restart worker
docker compose restart celery-worker
```

### High memory usage

**Cause:** Too many concurrent tasks or memory leaks

**Fix:**
```bash
# Reduce concurrency
celery -A apps.memory_api.celery_app worker --concurrency=1

# Enable worker restart after N tasks
celery -A apps.memory_api.celery_app worker --max-tasks-per-child=100
```

### Redis connection errors

**Cause:** Redis not running or misconfigured

**Fix:**
```bash
# Check Redis
docker compose ps redis
docker compose logs redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

## Best Practices

1. **Keep tasks idempotent** - Safe to retry without side effects
2. **Use timeouts** - Prevent runaway tasks
3. **Log extensively** - Aid debugging in production
4. **Monitor task duration** - Optimize slow tasks
5. **Handle failures gracefully** - Don't crash on bad input
6. **Test with real data** - Edge cases matter
7. **Use database pools** - Avoid connection exhaustion
8. **Clean up resources** - Close connections, release locks

## Future Enhancements

- [ ] Task priority queues
- [ ] Dynamic scheduling based on load
- [ ] Advanced retry strategies (exponential backoff)
- [ ] Task result expiration
- [ ] Celery Flower integration in Docker Compose
- [ ] Distributed task locking (Redis)
- [ ] Task chaining and workflows
- [ ] Webhooks for task completion

## References

- Celery Documentation: https://docs.celeryq.dev/
- Redis Documentation: https://redis.io/docs/
- RAE API Documentation: `../../docs/`

## Contributing

When adding new background tasks:

1. Define task in `background_tasks.py`
2. Add to beat schedule if periodic
3. Write tests in `test_background_tasks.py`
4. Update this README with documentation
5. Add monitoring/logging
6. Consider error handling and retries
