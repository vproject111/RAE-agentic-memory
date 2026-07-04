# Reflection Engine V2 – Implementation Guide

This document describes the implementation of the **Reflection Engine V2**, which implements the **Actor-Evaluator-Reflector pattern** for generating insights from execution traces.

## Overview

The Reflection Engine V2 analyzes task execution events (successes and failures) to generate:
- **Reflections**: Insights about what happened and why
- **Strategies**: Actionable rules for handling similar scenarios in the future
- **Importance & Confidence scores**: Metadata for ranking and filtering reflections

### Key Features

- Structured reflection generation using LLM
- Support for multiple outcome types (success, failure, partial, timeout, error)
- Automatic categorization and tagging
- Storage to Reflective Memory layer (`rm`)
- Graph linking for semantic retrieval (via Qdrant)

## Architecture

### Implementation Files

| File | Purpose |
|------|---------|
| `apps/memory_api/services/reflection_engine_v2.py` | Core engine implementation |
| `apps/memory_api/models/reflection_v2_models.py` | Data models and enums |
| `apps/memory_api/repositories/memory_repository.py` | Storage operations |
| `tests/integration/test_reflection_engine_v2.py` | Integration tests |

### Dependencies

- **LLM Provider**: `apps/memory_api/services/llm.py` (supports OpenAI, Anthropic, etc.)
- **Memory Repository**: For storing reflections and strategies
- **Database**: PostgreSQL + asyncpg for persistence

## Actor-Evaluator-Reflector Pattern

### 1. Actor (External)

The Actor executes tasks and generates an event trace:
- Tool calls and responses
- LLM interactions
- Errors and exceptions
- System events

**Note**: The Actor is typically implemented by the calling application (e.g., an AI agent). The Reflection Engine V2 only receives the Actor's execution trace.

### 2. Evaluator (Future)

The Evaluator assesses execution quality based on criteria:
- Correctness
- Helpfulness
- Safety
- Completeness
- Efficiency

**Status**: Models defined in `reflection_v2_models.py`, but full evaluation logic is not yet implemented.

### 3. Reflector (Core)

The Reflector (`ReflectionEngineV2`) analyzes the execution trace and generates:
- **Reflection**: What happened and why
- **Strategy**: How to handle similar scenarios
- **Scores**: Importance and confidence

## Data Models

### Event

Represents a single event in the execution trace:

```python
@dataclass
class Event:
    event_id: str
    event_type: EventType  # TOOL_CALL, LLM_CALL, ERROR_EVENT, etc.
    timestamp: datetime
    content: str
    metadata: Dict[str, Any]
    tool_name: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
```

### ReflectionContext

Input to the reflection generation process:

```python
@dataclass
class ReflectionContext:
    # Core event trace
    events: List[Event]
    outcome: OutcomeType  # SUCCESS, FAILURE, PARTIAL, TIMEOUT, ERROR

    # Session context
    tenant_id: str
    project_id: str
    session_id: Optional[UUID] = None

    # Optional context
    error: Optional[ErrorInfo] = None
    task_description: Optional[str] = None
    task_goal: Optional[str] = None
    related_memory_ids: List[UUID] = None
```

### ReflectionResult

Output of the reflection generation:

```python
@dataclass
class ReflectionResult:
    # Core content
    reflection_text: str
    strategy_text: Optional[str] = None

    # Scoring
    importance: float = 0.5  # 0.0 - 1.0
    confidence: float = 0.5  # 0.0 - 1.0

    # Categorization
    tags: List[str] = None
    error_category: Optional[ErrorCategory] = None

    # Relationships
    source_event_ids: List[str] = None
    related_memory_ids: List[UUID] = None

    # Metadata
    metadata: Dict[str, Any] = None
    generated_at: Optional[datetime] = None
```

## Core Workflows

### 1. Generate Reflection from Failure

#### Flow

1. **Receive Context**: Actor passes `ReflectionContext` with `outcome=FAILURE`
2. **Format Prompt**: Build failure reflection prompt with:
   - Task goal and description
   - Execution events
   - Error category, message, and context
3. **LLM Call**: Generate structured reflection using `LLMReflectionResponse` model
4. **Build Result**: Create `ReflectionResult` with reflection, strategy, scores
5. **Return**: Caller can then store the result

#### Example

```python
from apps.memory_api.services.reflection_engine_v2 import ReflectionEngineV2
from apps.memory_api.models.reflection_v2_models import (
    ReflectionContext, Event, EventType, OutcomeType, ErrorInfo, ErrorCategory
)
from datetime import datetime, timezone

# Initialize engine
pool = await asyncpg.create_pool(database_url)
engine = ReflectionEngineV2(pool)

# Create context
context = ReflectionContext(
    events=[
        Event(
            event_id="e1",
            event_type=EventType.TOOL_CALL,
            timestamp=datetime.now(timezone.utc),
            content="Called database query with complex JOIN",
            metadata={"tool": "postgres_query"}
        ),
        Event(
            event_id="e2",
            event_type=EventType.ERROR_EVENT,
            timestamp=datetime.now(timezone.utc),
            content="Query timeout after 30 seconds",
            metadata={},
            error={"message": "Timeout", "code": "QUERY_TIMEOUT"}
        )
    ],
    outcome=OutcomeType.TIMEOUT,
    error=ErrorInfo(
        error_category=ErrorCategory.TIMEOUT_ERROR,
        error_message="Query execution exceeded 30s limit",
        context={"query": "SELECT * FROM orders JOIN customers..."}
    ),
    task_description="Fetch customer order history",
    task_goal="Retrieve all orders for customer analysis",
    tenant_id="tenant-123",
    project_id="default"
)

# Generate reflection
result = await engine.generate_reflection(context)

# Output:
# ReflectionResult(
#   reflection_text="The query timed out due to a complex JOIN operation on large tables...",
#   strategy_text="For large table JOINs, add indexes on join columns or use pagination...",
#   importance=0.85,
#   confidence=0.9,
#   tags=["sql", "timeout", "performance", "database"]
# )

# Store reflection
stored = await engine.store_reflection(
    result=result,
    tenant_id="tenant-123",
    project_id="default"
)

# Returns: {'reflection_id': 'uuid-123', 'strategy_id': 'uuid-456'}
```

### 2. Generate Reflection from Success

#### Flow

1. **Receive Context**: Actor passes `ReflectionContext` with `outcome=SUCCESS`
2. **Format Prompt**: Build success reflection prompt with:
   - Task goal and description
   - Execution events showing successful approach
3. **LLM Call**: Generate structured reflection
4. **Build Result**: Create `ReflectionResult` highlighting successful patterns
5. **Return**: Caller stores the result

#### Example

```python
context = ReflectionContext(
    events=[
        Event(
            event_id="e1",
            event_type=EventType.TOOL_CALL,
            timestamp=datetime.now(timezone.utc),
            content="Used cached embeddings for semantic search",
            metadata={"cache_hit": True}
        ),
        Event(
            event_id="e2",
            event_type=EventType.TOOL_RESPONSE,
            timestamp=datetime.now(timezone.utc),
            content="Retrieved 10 relevant results in 50ms",
            metadata={"latency_ms": 50}
        )
    ],
    outcome=OutcomeType.SUCCESS,
    task_description="Semantic search for user query",
    task_goal="Find relevant documents quickly",
    tenant_id="tenant-123",
    project_id="default"
)

result = await engine.generate_reflection(context)

# Output:
# ReflectionResult(
#   reflection_text="The cached embeddings strategy reduced latency from 2s to 50ms...",
#   strategy_text="Always check cache before computing embeddings for frequently accessed queries",
#   importance=0.7,
#   confidence=0.85,
#   tags=["optimization", "caching", "best-practice", "performance"]
# )
```

### 3. Query Reflections

Retrieve stored reflections for learning:

```python
# Query reflections by importance
reflections = await engine.query_reflections(
    tenant_id="tenant-123",
    project_id="default",
    query_text="database optimization",
    k=5,
    min_importance=0.7,
    tags=["performance", "database"]
)

# Returns list of reflection records from memory
```

## LLM Prompts

### Failure Reflection Prompt

```python
REFLECTION_FAILURE_PROMPT = """You are a reflective reasoning engine that learns from failures.

Analyze the following task execution that resulted in an error or failure:

Task Goal: {task_goal}
Task Description: {task_description}

Execution Events:
{events}

Error Information:
- Category: {error_category}
- Message: {error_message}
- Context: {error_context}

Your task:
1. Identify the root cause of the failure
2. Explain what went wrong and why
3. Generate a concise "lesson learned" that can prevent similar issues
4. If possible, suggest a specific strategy or rule for handling this scenario

Provide your analysis as a structured JSON with:
- reflection: A clear explanation of what went wrong (2-3 sentences)
- strategy: A specific actionable strategy or rule (1-2 sentences, optional)
- importance: How important is this lesson? (0.0-1.0, where 1.0 is critical)
- confidence: How confident are you in this analysis? (0.0-1.0)
- tags: List of relevant tags (e.g., ["sql", "timeout", "performance"])
"""
```

### Success Reflection Prompt

```python
REFLECTION_SUCCESS_PROMPT = """You are a reflective reasoning engine that learns from successes.

Analyze the following task execution that resulted in success:

Task Goal: {task_goal}
Task Description: {task_description}

Execution Events:
{events}

Outcome: SUCCESS

Your task:
1. Identify what strategies or approaches led to success
2. Determine if this is a reusable pattern worth remembering
3. Generate a concise insight about effective approaches

Provide your analysis as a structured JSON with:
- reflection: A clear explanation of what worked well (2-3 sentences)
- strategy: A specific actionable strategy if reusable (1-2 sentences, optional)
- importance: How valuable is this insight? (0.0-1.0, where 1.0 is highly valuable)
- confidence: How confident are you in this analysis? (0.0-1.0)
- tags: List of relevant tags (e.g., ["optimization", "best-practice", "pattern"])
"""
```

## Storage

### Memory Layers

Reflections are stored in the **Reflective Memory (rm) layer**:

```sql
INSERT INTO memories (tenant_id, content, source, importance, layer, tags, project, ...)
VALUES ($1, $2, 'reflection_engine_v2', $3, 'rm', $4, $5, ...)
```

### Storage Schema

| Field | Description |
|-------|-------------|
| `content` | Reflection text or strategy text |
| `source` | Always `"reflection_engine_v2"` |
| `importance` | 0.0 - 1.0 (strategies get 10% boost) |
| `layer` | Always `"rm"` (Reflective Memory) |
| `tags` | Generated by LLM + additional tags (e.g., `["strategy"]` for strategies) |
| `metadata` | Contains outcome, task_description, event_count, session_id |

### Dual Storage

For each reflection generation:
1. **Reflection** is stored with generated tags
2. **Strategy** (if present) is stored separately with `"strategy"` tag and +10% importance

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REFLECTIVE_MEMORY_ENABLED` | `True` | Enable reflective memory system |
| `REFLECTIVE_MEMORY_MODE` | `"full"` | Mode: `"lite"` or `"full"` |
| `RAE_LLM_MODEL_DEFAULT` | Provider-specific | LLM model for reflection generation |

### Mode Differences

| Mode | Reflection Generation | Dreaming | Use Case |
|------|----------------------|----------|----------|
| **lite** | On-demand only | Disabled | Cost-conscious, basic reflection |
| **full** | On-demand + periodic | Enabled | Full capability, enterprise |

## Integration Points

### 1. From Agents

Agents call Reflection Engine V2 after task completion:

```python
# Agent executes task and collects events
events = [...]  # Tool calls, LLM responses, errors

# Create reflection context
context = ReflectionContext(
    events=events,
    outcome=OutcomeType.FAILURE if error else OutcomeType.SUCCESS,
    error=error_info if error else None,
    task_description="User's task",
    tenant_id=tenant_id,
    project_id=project_id
)

# Generate and store reflection
result = await engine.generate_reflection(context)
await engine.store_reflection(result, tenant_id, project_id)
```

### 2. From Background Workers

The Dreaming Worker uses Reflection Engine V2:

```python
# DreamingWorker (apps/memory_api/workers/memory_maintenance.py)
from apps.memory_api.services.reflection_engine_v2 import ReflectionEngineV2

# Sample high-importance memories
memories = await query_high_importance_memories(...)

# Convert to events
events = [Event(...) for memory in memories]

# Create context
context = ReflectionContext(
    events=events,
    outcome=OutcomeType.PARTIAL,  # Exploratory
    task_description="Analyzing patterns in recent memories",
    tenant_id=tenant_id,
    project_id=project_id
)

# Generate reflection
result = await engine.generate_reflection(context)
await engine.store_reflection(result, tenant_id, project_id)
```

### 3. From API Endpoints

Expose reflection generation via API:

```python
# POST /api/v1/reflections/generate
{
  "tenant_id": "tenant-123",
  "project_id": "default",
  "events": [
    {"event_type": "tool_call", "content": "...", ...},
    {"event_type": "error_event", "content": "...", ...}
  ],
  "outcome": "failure",
  "error": {
    "error_category": "timeout_error",
    "error_message": "Query timeout"
  },
  "task_description": "Database query"
}

# Response
{
  "reflection_id": "uuid-123",
  "reflection_text": "...",
  "strategy_text": "...",
  "importance": 0.85,
  "confidence": 0.9,
  "tags": ["sql", "timeout", "performance"]
}
```

## Metrics and Observability

### Structured Logging

The engine emits structured logs for monitoring:

```python
logger.info(
    "reflection_generation_started",
    tenant_id=context.tenant_id,
    project_id=context.project_id,
    outcome=context.outcome.value,
    event_count=len(context.events)
)

logger.info(
    "reflection_generated",
    tenant_id=context.tenant_id,
    importance=result.importance,
    confidence=result.confidence,
    has_strategy=result.strategy_text is not None
)

logger.info(
    "reflection_stored",
    tenant_id=tenant_id,
    reflection_id=reflection_record["id"],
    importance=result.importance
)
```

### Error Handling

Errors during reflection generation are logged and raised:

```python
logger.error(
    "reflection_generation_failed",
    tenant_id=context.tenant_id,
    error=str(e),
    exc_info=True
)
```

## Testing

### Test Files

- `tests/integration/test_reflection_engine_v2.py` - Integration tests
- `apps/memory_api/tests/test_reflection_*.py` - Unit tests

### Example Test

```python
async def test_reflection_generation_failure():
    engine = ReflectionEngineV2(pool)

    context = ReflectionContext(
        events=[
            Event(event_id="e1", event_type=EventType.ERROR_EVENT, ...)
        ],
        outcome=OutcomeType.FAILURE,
        error=ErrorInfo(
            error_category=ErrorCategory.TIMEOUT_ERROR,
            error_message="Timeout"
        ),
        tenant_id="test-tenant",
        project_id="test-project"
    )

    result = await engine.generate_reflection(context)

    assert result.reflection_text
    assert result.importance > 0.0
    assert "timeout" in result.tags
```

## Best Practices

### 1. Event Collection

Collect rich events during task execution:
- **Tool calls**: Include tool name, parameters, response
- **LLM interactions**: Include prompt, response, model
- **Errors**: Include full context (stack trace, inputs)

### 2. Task Context

Provide clear task description and goal:
- **Description**: What the task is doing
- **Goal**: What success looks like

### 3. Importance Tuning

Adjust importance thresholds based on needs:
- **Critical failures**: 0.8 - 1.0 (always store)
- **Valuable insights**: 0.6 - 0.8 (store selectively)
- **Minor issues**: 0.3 - 0.6 (consider filtering)

### 4. Storage Optimization

- Query existing reflections before generating new ones (avoid duplicates)
- Prune low-importance reflections periodically
- Use tags for efficient filtering

## Troubleshooting

### Reflection Not Generated

Check logs for errors:
- `reflection_generation_failed` - LLM error or network issue
- Verify `REFLECTIVE_MEMORY_ENABLED=True`
- Check LLM provider configuration

### Low Quality Reflections

Improve input quality:
- Provide richer event traces
- Include clear task descriptions
- Add error context for failures

### Storage Failures

Check database connection:
- Verify PostgreSQL is accessible
- Check `memories` table exists
- Verify tenant_id format (UUID)

## Related Documentation

- [Background Workers](./BACKGROUND_WORKERS.md) - Dreaming Worker integration
- [LLM Profiles and Cost Guard](./LLM_PROFILES_AND_COST_GUARD.md) - LLM configuration
- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant isolation
- [Test Coverage Map](./TEST_COVERAGE_MAP.md) - Test coverage for reflection engine

## Future Enhancements

### Planned Features

1. **Evaluator Implementation**: Full evaluation logic with criteria scoring
2. **Graph Linking**: Link reflections to entities in knowledge graph
3. **Reflection Clustering**: Group similar reflections automatically
4. **Strategy Execution**: Apply strategies automatically in future tasks
5. **Reflection Versioning**: Track how reflections evolve over time

### Extension Points

The engine is designed for extensibility:
- **Custom Prompts**: Override `REFLECTION_FAILURE_PROMPT` and `REFLECTION_SUCCESS_PROMPT`
- **Custom Scoring**: Implement custom importance/confidence calculators
- **Custom Storage**: Replace `MemoryRepository` with custom storage backend
- **Custom LLM**: Swap `get_llm_provider()` for different LLM backends

## API Reference

### ReflectionEngineV2

```python
class ReflectionEngineV2:
    def __init__(
        self,
        pool: asyncpg.Pool,
        memory_repository: Optional[MemoryRepository] = None
    )

    async def generate_reflection(
        self,
        context: ReflectionContext
    ) -> ReflectionResult

    async def store_reflection(
        self,
        result: ReflectionResult,
        tenant_id: str,
        project_id: str,
        session_id: Optional[UUID] = None
    ) -> Dict[str, str]

    async def query_reflections(
        self,
        tenant_id: str,
        project_id: str,
        query_text: Optional[str] = None,
        k: int = 5,
        min_importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]
```
