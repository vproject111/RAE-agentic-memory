# Reflective Memory V1 - Implementation Documentation

**Status:** ✅ Implemented (v1.0)
**Date:** 2025-11-28
**Implementation Plan:** `docs/RAE-–Reflective_Memory_v1-Implementati.md`

## Overview

This document describes the implementation of the 4-layer Reflective Memory system in RAE, following the Actor-Evaluator-Reflector pattern. This implementation enables RAE to learn from both successes and failures, building a library of "lessons learned" that inform future executions.

## Architecture

### 4-Layer Memory Model

```
Layer 4: Reflective Memory
├── Reflections (lessons learned from failures/successes)
└── Strategies (actionable rules and patterns)
         ↑
Layer 3: Long-Term Memory (LTM)
├── Episodic (task history)
├── Semantic (knowledge, documents)
└── Profile (user preferences)
         ↑
Layer 2: Working Memory
├── Recent messages
├── Retrieved LTM items
├── Injected reflections
└── User profile
         ↑
Layer 1: Sensory
└── Raw inputs (messages, events, tool calls)
```

### Memory Layers Mapping (Code Implementation)

The conceptual 4-layer model maps to database schema as follows:

| Conceptual Layer | `layer` (enum) | `memory_type` (typical) | Examples | Usage |
|------------------|----------------|-------------------------|----------|-------|
| **Layer 1: Sensory** | `stm` | `sensory` | Raw events, logs, tool calls | Immediate inputs, rarely persisted long-term |
| **Layer 2: Working** | `stm`, `em` | `episodic` (recent) | Current session context | Short-term context for active tasks |
| **Layer 3: LTM** | `ltm`, `em` | `episodic`, `semantic`, `profile` | Completed sessions, facts, user profile | Long-term storage, retrieved by relevance |
| **Layer 4: Reflective** | `rm` | `reflection`, `strategy` | Post-mortems, lessons, strategies | Meta-learning, injected into future contexts |

**Key distinctions:**
- **`layer`**: Processing stage (STM/LTM/episodic/reflective) - determines retention and retrieval strategy
- **`memory_type`**: Functional classification (sensory/episodic/semantic/profile/reflection/strategy) - determines content semantics

**Migration note:** Existing memories use:
- `em` (episodic memory) → Layer 2/3 boundary
- `sm` (semantic memory) → Layer 3
- `rm` (reflective memory) → Layer 4
- `stm` (short-term) → Layer 1/2
- `ltm` (long-term) → Layer 3

See also: Database schema in `alembic/versions/d4e5f6a7b8c9_add_reflective_memory_columns.py`

### Actor-Evaluator-Reflector Pattern

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│   Actor    │────▶│ Evaluator  │────▶│ Reflector  │
│ (Execute)  │     │ (Assess)   │     │ (Learn)    │
└────────────┘     └────────────┘     └────────────┘
      │                   │                   │
      │                   │                   ▼
      │                   │            ┌─────────────┐
      │                   │            │ Reflection  │
      │                   │            │   Storage   │
      │                   │            └─────────────┘
      │                   │                   │
      │                   │                   ▼
      │                   │            ┌─────────────┐
      │                   │            │  Layer 4:   │
      └───────────────────┴───────────▶│ Reflective  │
              (Next execution)         │   Memory    │
                                      └─────────────┘
```

## Core Components

### 1. Database Schema

**New columns in `memories` table:**

```sql
-- Memory type classification
memory_type TEXT NOT NULL  -- 'sensory', 'episodic', 'semantic', 'profile', 'reflection', 'strategy'

-- Session tracking
session_id UUID NULL  -- Links memories to execution sessions

-- Vector store integration
qdrant_point_id TEXT NULL  -- Reference to Qdrant vector point

-- Indexes for performance
CREATE INDEX idx_memories_memory_type ON memories(memory_type);
CREATE INDEX idx_memories_session_id ON memories(session_id);
CREATE INDEX idx_memories_tenant_project_type ON memories(tenant_id, project, memory_type);
```

**Migration:** `alembic/versions/d4e5f6a7b8c9_add_reflective_memory_columns.py`

### 2. Reflection Models

**File:** `apps/memory_api/models/reflection_v2_models.py`

Key models:
- `ReflectionContext` - Input for reflection generation (events, outcome, error)
- `ReflectionResult` - Output from reflection (reflection_text, strategy_text, scoring)
- `Event` - Single execution event (tool call, response, error)
- `ErrorInfo` - Error details for failure analysis
- `OutcomeType` - Success/Failure/Partial/Timeout/Error

### 3. ReflectionEngineV2

**File:** `apps/memory_api/services/reflection_engine_v2.py`

**Main method:**
```python
async def generate_reflection(context: ReflectionContext) -> ReflectionResult
```

**Features:**
- LLM-powered reflection generation using structured output
- Separate prompts for failure vs. success scenarios
- Importance and confidence scoring
- Automatic tagging and categorization
- Error analysis and pattern detection

**Reflection Types:**
1. **Failure Reflections** - Learn from errors
   - Tool failures, timeouts, validation errors
   - Root cause analysis
   - Preventive strategies

2. **Success Reflections** - Learn from what works
   - Effective patterns
   - Optimization techniques
   - Reusable strategies

### 4. Memory Scoring V2

**File:** `apps/memory_api/services/memory_scoring_v2.py`

**Core function:**
```python
def compute_memory_score(
    similarity: float,      # Relevance (vector similarity)
    importance: float,      # Content importance (0-1)
    last_accessed_at: datetime,
    created_at: datetime,
    access_count: int,
    weights: ScoringWeights = default,
    decay_config: DecayConfig = default,
) -> MemoryScoreResult
```

**Formula:**
```
score = α·relevance + β·importance + γ·recency

where:
  relevance = similarity (vector search)
  importance = 0-1 score (manual or LLM-driven)
  recency = exp(-effective_decay * time_diff)

  effective_decay = base_decay / (log(1 + access_count) + 1)
```

**Default weights:**
- α (relevance): 0.5
- β (importance): 0.3
- γ (recency): 0.2

**Configurable via:**
```env
MEMORY_SCORE_WEIGHTS_ALPHA=0.5
MEMORY_SCORE_WEIGHTS_BETA=0.3
MEMORY_SCORE_WEIGHTS_GAMMA=0.2
MEMORY_BASE_DECAY_RATE=0.001
```

### 5. ContextBuilder

**File:** `apps/memory_api/services/context_builder.py`

**Main method:**
```python
async def build_context(
    tenant_id: str,
    project_id: str,
    query: str,
    recent_messages: List[Dict],
) -> WorkingMemoryContext
```

**Context structure:**
```
# User Profile
- User preferences and settings

# Lessons Learned (internal reflective memory)
- [sql, timeout] Always use LIMIT clause for large queries
- [auth, security] Validate authentication headers before API calls
- [performance] Cache frequently accessed data

# Relevant Context
- [em] User asked about database optimization
- [sm] Documentation about query performance
- [sm] Best practices for SQL queries

# Recent Messages
- User: "How do I query a large table?"
- Assistant: "Let me help you with that..."
```

**Helper method:**
```python
async def inject_reflections_into_prompt(
    base_prompt: str,
    tenant_id: str,
    project_id: str,
    query: str,
) -> str
```

### 6. Background Workers

**File:** `apps/memory_api/workers/memory_maintenance.py`

#### DecayWorker
- Runs daily (configurable)
- Applies time-based importance decay
- Considers access patterns (frequently accessed decay slower)
- Supports per-tenant and global execution

#### SummarizationWorker
- Creates session summaries from episodic memories
- Triggers after sessions complete or for long sessions
- Reduces memory overhead while preserving key information

#### DreamingWorker
- Generates reflections from historical patterns
- Runs periodically (e.g., daily)
- Analyzes high-importance memories
- Identifies recurring themes and strategies

#### MaintenanceScheduler
- Coordinates all maintenance workers
- Provides daily and hourly maintenance cycles
- CLI entry point for cron/systemd

**Usage:**
```bash
# Run daily maintenance
python -m apps.memory_api.workers.memory_maintenance

# Or integrate with cron
0 2 * * * cd /path/to/rae && python -m apps.memory_api.workers.memory_maintenance
```

## Configuration

### Environment Variables

```env
# Feature flags
REFLECTIVE_MEMORY_ENABLED=true
REFLECTIVE_MEMORY_MODE=full  # "lite" or "full"

# Retrieval limits
REFLECTIVE_MAX_ITEMS_PER_QUERY=5
REFLECTIVE_LESSONS_TOKEN_BUDGET=1024

# Scoring weights
MEMORY_SCORE_WEIGHTS_ALPHA=0.5
MEMORY_SCORE_WEIGHTS_BETA=0.3
MEMORY_SCORE_WEIGHTS_GAMMA=0.2

# Decay configuration
MEMORY_BASE_DECAY_RATE=0.001
MEMORY_ACCESS_COUNT_BOOST=true

# Reflection generation
REFLECTION_MIN_IMPORTANCE_THRESHOLD=0.3
REFLECTION_GENERATE_ON_ERRORS=true
REFLECTION_GENERATE_ON_SUCCESS=false  # true in full mode

# Dreaming (batch reflection)
DREAMING_ENABLED=false  # true in full mode
DREAMING_LOOKBACK_HOURS=24
DREAMING_MIN_IMPORTANCE=0.6

# Summarization
SUMMARIZATION_ENABLED=true
SUMMARIZATION_MIN_EVENTS=10
```

### Modes

#### Lite Mode (`REFLECTIVE_MEMORY_MODE=lite`)
- Minimal overhead
- Reflections only on critical errors
- No "dreaming" (batch analysis)
- 3 reflections per query
- 512 token budget

#### Full Mode (`REFLECTIVE_MEMORY_MODE=full`)
- All features enabled
- Reflections on errors + successes
- Periodic "dreaming" enabled
- 5 reflections per query
- 1024 token budget

### Mode Behavior Matrix

| Flag / Setting | Effect | Lite Mode | Full Mode |
|----------------|--------|-----------|-----------|
| `REFLECTIVE_MEMORY_ENABLED=false` | No reflections, no "Lessons Learned" section | ❌ Disabled | ❌ Disabled |
| `REFLECTIVE_MEMORY_ENABLED=true` | Enable reflective memory system | ✅ Enabled | ✅ Enabled |
| `REFLECTIVE_MEMORY_MODE=lite` | Minimal overhead, critical errors only | ✅ Active | - |
| `REFLECTIVE_MEMORY_MODE=full` | Full pipeline with all features | - | ✅ Active |
| `REFLECTION_GENERATE_ON_ERRORS` | Generate reflections from failures | ✅ Always | ✅ Always |
| `REFLECTION_GENERATE_ON_SUCCESS` | Generate reflections from successes | ❌ Disabled | ✅ Enabled |
| `DREAMING_ENABLED` | Periodic batch reflection analysis | ❌ Disabled | ✅ Enabled |
| `SUMMARIZATION_ENABLED` | Session summarization | ✅ Basic | ✅ Advanced |
| `REFLECTIVE_MAX_ITEMS_PER_QUERY` | Max reflections in context | 3 | 5 |
| `REFLECTIVE_LESSONS_TOKEN_BUDGET` | Token budget for lessons | 512 | 1024 |
| Memory decay | Importance decay rate | Standard | Standard |
| Maintenance workers | Background tasks | Essential only | All tasks |

**Recommendations:**
- **Development/Testing:** Use `lite` mode for faster iterations
- **Production (low-traffic):** Use `lite` mode to minimize overhead
- **Production (high-value):** Use `full` mode for maximum learning
- **Resource-constrained:** Disable `DREAMING_ENABLED` even in full mode

## Usage Examples

### 1. Generate Reflection from Error

```python
from apps.memory_api.services.reflection_engine_v2 import ReflectionEngineV2
from apps.memory_api.models.reflection_v2_models import (
    ReflectionContext, Event, EventType, OutcomeType, ErrorInfo, ErrorCategory
)

engine = ReflectionEngineV2(pool)

# Create context from failed execution
events = [
    Event(
        event_id="evt_1",
        event_type=EventType.TOOL_CALL,
        content="SELECT * FROM users",
        tool_name="sql_executor",
    ),
    Event(
        event_id="evt_2",
        event_type=EventType.ERROR_EVENT,
        content="Query timeout after 30s",
        error={"code": "TIMEOUT"},
    ),
]

error = ErrorInfo(
    error_code="TIMEOUT",
    error_category=ErrorCategory.TIMEOUT_ERROR,
    error_message="SQL query timeout",
)

context = ReflectionContext(
    events=events,
    outcome=OutcomeType.FAILURE,
    error=error,
    task_description="Fetch user data",
    tenant_id="tenant-1",
    project_id="project-1",
)

# Generate reflection
result = await engine.generate_reflection(context)

print(f"Reflection: {result.reflection_text}")
print(f"Strategy: {result.strategy_text}")
print(f"Importance: {result.importance}")
print(f"Tags: {result.tags}")

# Store reflection
stored = await engine.store_reflection(
    result=result,
    tenant_id="tenant-1",
    project_id="project-1",
)
```

### 2. Build Context with Reflections

```python
from apps.memory_api.services.context_builder import ContextBuilder

builder = ContextBuilder(pool)

# Build context for new task
context = await builder.build_context(
    tenant_id="tenant-1",
    project_id="project-1",
    query="I need to query the users table",
    recent_messages=[
        {"role": "user", "content": "How do I get user data?"}
    ],
)

# Access reflections
for reflection in context.reflections:
    print(f"Lesson: {reflection.content}")
    print(f"Tags: {reflection.metadata['tags']}")

# Get formatted context for LLM
print(context.system_prompt)
print(context.context_text)
```

### 3. Enhanced Memory Scoring

```python
from apps.memory_api.services.memory_scoring_v2 import compute_memory_score
from datetime import datetime, timezone

score_result = compute_memory_score(
    similarity=0.85,  # From vector search
    importance=0.7,   # From memory importance
    last_accessed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    access_count=10,
    now=datetime(2024, 1, 8, tzinfo=timezone.utc),
)

print(f"Final score: {score_result.final_score:.3f}")
print(f"Components:")
print(f"  Relevance: {score_result.relevance_score:.3f}")
print(f"  Importance: {score_result.importance_score:.3f}")
print(f"  Recency: {score_result.recency_score:.3f}")
```

### 4. Run Maintenance Workers

```python
from apps.memory_api.workers import MaintenanceScheduler

scheduler = MaintenanceScheduler(pool)

# Run daily maintenance
stats = await scheduler.run_daily_maintenance()

print(f"Decay: {stats['decay']}")
print(f"Dreaming: {stats['dreaming']}")
```

## Testing

### Integration Tests

**File:** `tests/integration/test_reflection_flow.py`

Key test scenarios:
1. ✅ Generate reflection from failure
2. ✅ Generate reflection from success
3. ✅ Retrieve reflections in context
4. ✅ Memory scoring with component breakdown
5. ✅ Inject reflections into prompts
6. ✅ End-to-end Actor-Evaluator-Reflector flow

**Run tests:**
```bash
pytest tests/integration/test_reflection_flow.py -v
```

## Performance Considerations

### Token Budget
- Reflections consume tokens in LLM context
- Default budget: 1024 tokens (configurable)
- Automatic truncation if budget exceeded
- Prioritize by importance score

### Database Performance
- Indexed on `memory_type` for fast filtering
- Indexed on `session_id` for session queries
- Composite index on `(tenant_id, project, memory_type)`

### Caching
- Consider caching high-importance reflections
- Use Redis for frequently accessed lessons
- Invalidate on new reflection generation

## Future Enhancements (v1.1+)

### v1.1 - Advanced Prompts
- Domain-specific reflection templates
- Multi-turn reflection refinement
- Confidence calibration

### v1.2 - Enhanced Dreaming
- Clustering-based pattern detection
- Cross-session trend analysis
- Automatic strategy evolution

### v2.0 - Enterprise Graph
- Rich semantic relationships
- LangGraph integration
- Distributed reflection engine

## Troubleshooting

### No reflections generated
- Check `REFLECTIVE_MEMORY_ENABLED=true`
- Verify LLM backend is configured
- Check logs for errors in reflection generation

### Reflections not appearing in context
- Verify `memory_type='reflection'` in database
- Check importance > `min_reflection_importance`
- Verify query retrieves relevant memories

### High token usage
- Reduce `REFLECTIVE_MAX_ITEMS_PER_QUERY`
- Lower `REFLECTIVE_LESSONS_TOKEN_BUDGET`
- Use `lite` mode instead of `full`

### Decay too aggressive
- Increase `MEMORY_BASE_DECAY_RATE` (lower = slower decay)
- Enable `MEMORY_ACCESS_COUNT_BOOST=true`
- Adjust min/max decay rates

## References

### Implementation Files

- **Implementation Plan:** `docs/RAE-–Reflective_Memory_v1-Implementati.md`
- **Models:** `apps/memory_api/models/reflection_v2_models.py`
- **Engine:** `apps/memory_api/services/reflection_engine_v2.py`
- **Scoring:** `apps/memory_api/services/memory_scoring_v2.py`
- **Context:** `apps/memory_api/services/context_builder.py`
- **Workers:** `apps/memory_api/workers/memory_maintenance.py`
- **Tests:** `tests/integration/test_reflection_flow.py`
- **Flag Tests:** `apps/memory_api/tests/test_reflective_flags.py`
- **Config:** `apps/memory_api/config.py`
- **Migration:** `alembic/versions/d4e5f6a7b8c9_add_reflective_memory_columns.py`

### Documentation

- **[Memory Model Reference](./MEMORY_MODEL.md)** - Canonical layer/type mapping for 4-layer architecture
- **[Configuration Reference](./CONFIG_REFLECTIVE_MEMORY.md)** - Complete guide to all feature flags, modes, and production recommendations
- **[Security Assessment](./SECURITY.md)** - Honest "Almost Enterprise" security documentation with deployment patterns
- **[Closure Report](./RAE-ReflectiveMemory_v1-Closure-Report.md)** - Complete finalization audit trail and implementation status
- **[Status](../STATUS.md)** - Current project status with Reflective Memory V1 completion details

---

**Implemented by:** RAE Development Team
**Date:** 2025-11-28
**Version:** 1.0 ✅ **COMPLETE (Production Ready)**

**Note:** Reflective Memory V1 finalization completed 2025-11-28. The system is production-ready for internal tools and controlled environments. See the Closure Report for complete details on what was done, what's in scope, and future roadmap.
