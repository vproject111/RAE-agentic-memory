# 🧠 RAE Memory Layers - Complete Architecture Reference

> **4-Layer Cognitive Memory System** - How RAE organizes and processes information like human memory.

---

## Overview

RAE implements a **complete 4-layer cognitive architecture** inspired by human memory systems. Each layer serves a distinct cognitive function, from immediate sensory input to high-level meta-learning.

```
┌────────────────────────────────────────────────────────────┐
│  LAYER 4: REFLECTIVE MEMORY (Meta-Learnings)              │
│  "Authentication module needs architectural refactoring"   │
└──────────────────────┬─────────────────────────────────────┘
                       │ Reflection Engine V2
┌──────────────────────┴─────────────────────────────────────┐
│  LAYER 3: LONG-TERM MEMORY (Facts + Events + Profiles)    │
│  Episodic: "User fixed auth bug" | Semantic: "auth.py"    │
└──────────────────────┬─────────────────────────────────────┘
                       │ Consolidation
┌──────────────────────┴─────────────────────────────────────┐
│  LAYER 2: WORKING MEMORY (Active Task Context)            │
│  "Currently debugging auth" + "Lessons: frequent bugs"    │
└──────────────────────┬─────────────────────────────────────┘
                       │ Attention & Filtering
┌──────────────────────┴─────────────────────────────────────┐
│  LAYER 1: SENSORY MEMORY (Raw Inputs)                     │
│  "User clicked submit button"                              │
└────────────────────────────────────────────────────────────┘
```

---

## 🔷 Layer 1: Sensory Memory (Raw Input)

**Purpose**: Capture immediate, unprocessed sensory inputs.

### Characteristics
- **Retention**: Hours to days (high decay rate: 0.01/day)
- **Capacity**: High volume, low retention priority
- **Processing**: Minimal filtering, raw storage

### Database Mapping
- `layer` = `stm` (Short-Term Memory)
- `memory_type` = `sensory`

### Use Cases
- Raw event streams (tool calls, API requests)
- Unprocessed logs and traces
- Immediate sensory data
- Debugging information

### Example
```json
{
  "layer": "stm",
  "memory_type": "sensory",
  "content": "User clicked 'Submit' button at 2025-12-08T17:30:00Z",
  "importance": 0.1,
  "tags": ["ui", "event", "raw"]
}
```

**Code Reference**: [`apps/memory_api/models.py:MemoryLayer`](../../apps/memory_api/models.py)

---

## 🔶 Layer 2: Working Memory (Active Context)

**Purpose**: Maintain active task context and current conversation state.

### Characteristics
- **Retention**: Days to weeks (medium decay: 0.005/day)
- **Capacity**: Limited (context window size)
- **Processing**: Active filtering and attention

### Database Mapping
- `layer` = `stm` or `em` (Short-Term/Episodic)
- `memory_type` = `episodic` (recent events)

### Use Cases
- Active session context
- Current conversation turns
- Temporary working set
- Recent task state

### Context Builder Integration
Working Memory is dynamically assembled by `ContextBuilder`:
- Retrieves relevant memories
- Injects reflections automatically
- Maintains context window constraints
- Prioritizes by importance and recency

### Example
```json
{
  "layer": "em",
  "memory_type": "episodic",
  "content": "User is currently debugging authentication bug in auth.py",
  "importance": 0.7,
  "tags": ["active_task", "debugging", "auth"],
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Code Reference**: [`apps/memory_api/services/context_builder.py`](../../apps/memory_api/services/context_builder.py)

---

## 🔷 Layer 3: Long-Term Memory (Facts, Events, Profiles)

**Purpose**: Persistent storage of knowledge, experiences, and preferences.

### Characteristics
- **Retention**: Months to years (low decay: 0.001/day)
- **Capacity**: Large, permanent storage
- **Processing**: Consolidated from working memory

### Database Mapping
- `layer` = `ltm` or `em` (Long-Term/Episodic)
- `memory_type` = `episodic`, `semantic`, `profile`

### Memory Types

#### 3.1. Episodic Memory (Historical Events)
- Completed sessions and conversations
- Historical facts with temporal context
- Cause-effect sequences

```json
{
  "layer": "em",
  "memory_type": "episodic",
  "content": "User fixed authentication bug by adding JWT validation on 2025-12-01",
  "importance": 0.8,
  "tags": ["bug_fix", "auth", "jwt"]
}
```

#### 3.2. Semantic Memory (Domain Knowledge)
- Factual knowledge and documentation
- Conceptual understanding
- General truths without temporal context

```json
{
  "layer": "ltm",
  "memory_type": "semantic",
  "content": "JWT tokens must be validated using signature verification",
  "importance": 0.9,
  "tags": ["security", "auth", "best_practice"]
}
```

#### 3.3. Profile Memory (Preferences & Configuration)
- User preferences and settings
- System configuration
- Persistent behavioral patterns

```json
{
  "layer": "ltm",
  "memory_type": "profile",
  "content": "User prefers Python over JavaScript for backend development",
  "importance": 0.85,
  "tags": ["preference", "programming"]
}
```

**Code Reference**: [`apps/memory_api/repositories/memory_repository.py`](../../apps/memory_api/repositories/memory_repository.py)

---

## 🔶 Layer 4: Reflective Memory (Meta-Learning)

**Purpose**: High-level insights, lessons learned, and strategic patterns.

### Characteristics
- **Retention**: Permanent (very low decay: 0.0001/day)
- **Capacity**: Selective, high-value only
- **Processing**: Generated by Reflection Engine V2

### Database Mapping
- `layer` = `rm` (Reflective Memory)
- `memory_type` = `reflection`, `strategy`

### Memory Types

#### 4.1. Reflection Memory (Analysis & Insights)
- Post-mortem analysis of failures/successes
- Lessons learned from experiences
- Causal analysis and root causes

```json
{
  "layer": "rm",
  "memory_type": "reflection",
  "content": "Authentication failures often stem from missing JWT validation. Always verify signatures before trusting tokens.",
  "importance": 0.95,
  "tags": ["lesson_learned", "auth", "security"],
  "reflection_type": "failure_analysis"
}
```

#### 4.2. Strategy Memory (Actionable Patterns)
- Reusable decision patterns
- Best practices and workflows
- Strategic approaches

```json
{
  "layer": "rm",
  "memory_type": "strategy",
  "content": "When debugging auth issues: 1) Check JWT expiration, 2) Verify signature, 3) Validate claims",
  "importance": 0.9,
  "tags": ["strategy", "auth", "debugging"],
  "reflection_type": "best_practice"
}
```

### Reflection Engine V2 (Actor-Evaluator-Reflector)

Automatic reflection generation using three components:

1. **Actor**: Executes actions and records outcomes
2. **Evaluator**: Assesses success/failure (deterministic, threshold, LLM)
3. **Reflector**: Generates insights from failures (LLM-powered)

**Code Reference**: [`apps/memory_api/services/reflection_engine_v2.py`](../../apps/memory_api/services/reflection_engine_v2.py)

---

## 📊 Layer Comparison Table

| Layer | Database `layer` | `memory_type` | Decay Rate | Typical TTL | Access Effect |
|-------|-----------------|---------------|------------|-------------|---------------|
| **Sensory (L1)** | `stm` | `sensory` | High (0.01/day) | Hours-Days | Minimal |
| **Working (L2)** | `stm`, `em` | `episodic` | Medium (0.005/day) | Days-Weeks | Moderate |
| **Long-Term (L3)** | `ltm`, `em` | `episodic`, `semantic`, `profile` | Low (0.001/day) | Months-Years | High |
| **Reflective (L4)** | `rm` | `reflection`, `strategy` | Very Low (0.0001/day) | Permanent | Very High |

**Note**: Actual decay rates are configurable via `MEMORY_BASE_DECAY_RATE` and adjusted by access patterns (usage frequency).

---

## 🔄 Memory Lifecycle

```
1. INGESTION (Layer 1 - Sensory)
   ↓
   Raw input captured → Immediate storage

2. ATTENTION (Layer 2 - Working Memory)
   ↓
   Filtered by relevance → Active context assembled

3. CONSOLIDATION (Layer 3 - Long-Term)
   ↓
   Summarization Worker → Permanent storage
   Episodic/Semantic/Profile classification

4. REFLECTION (Layer 4 - Reflective)
   ↓
   Reflection Engine V2 → Meta-learning extraction
   Dreaming Worker (batch processing)
```

---

## 🔧 Database Schema

Key columns in the `memories` table:

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,          -- Multi-tenancy isolation
    project_id UUID NOT NULL,

    layer TEXT NOT NULL,               -- 'stm', 'ltm', 'em', 'rm'
    memory_type TEXT NOT NULL,         -- 'sensory', 'episodic', etc.
    content TEXT NOT NULL,

    importance FLOAT DEFAULT 0.5,      -- 0.0-1.0 score
    usage_count INT DEFAULT 0,         -- Access frequency
    last_accessed_at TIMESTAMP,        -- For decay calculation

    session_id UUID,                   -- Links to execution sessions
    tags TEXT[],                       -- Categorical tags

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Migration Reference**: [`alembic/versions/d4e5f6a7b8c9_add_reflective_memory_columns.py`](../../alembic/versions/)

---

## 🎯 Best Practices

### 1. Choose the Right Layer

- **Sensory (L1)**: Only for raw, unprocessed data that needs logging
- **Working (L2)**: Active task context, current conversation
- **Long-Term (L3)**: Anything that should persist beyond current session
- **Reflective (L4)**: High-value insights only (don't overuse!)

### 2. Set Appropriate Importance

```python
# Low importance (0.1-0.3) - Transient data
# Medium importance (0.4-0.7) - Standard memories
# High importance (0.8-1.0) - Critical knowledge, reflections
```

### 3. Use Correct Memory Types

```python
# Episodic: Events with temporal context
# Semantic: Timeless facts and knowledge
# Profile: User/system preferences
# Reflection: Insights from experience
# Strategy: Actionable patterns
```

### 4. Tag Consistently

Use hierarchical tags for better retrieval:
```python
tags = ["auth", "security", "jwt", "bug_fix"]  # Good
tags = ["thing", "stuff", "misc"]              # Bad
```

---

## 📚 Related Documentation

- **[Math Layers](./MATH_LAYERS.md)** - Mathematical intelligence above memory layers
- **[Hybrid Search](./HYBRID_SEARCH.md)** - Multi-strategy retrieval system
- **[Reflection Engine V2](../reference/services/reflection_engine_v2.md)** - Automatic meta-learning
- **[Context Builder](../reference/services/context_builder.md)** - Working Memory assembly
- **[Memory Scoring V2](../reference/services/memory_scoring_v2.md)** - Importance and decay

---

## 🔬 Implementation Details

### Services
- **Memory Repository**: [`apps/memory_api/repositories/memory_repository.py`](../../apps/memory_api/repositories/memory_repository.py)
- **Context Builder**: [`apps/memory_api/services/context_builder.py`](../../apps/memory_api/services/context_builder.py)
- **Reflection Engine**: [`apps/memory_api/services/reflection_engine_v2.py`](../../apps/memory_api/services/reflection_engine_v2.py)
- **Memory Scoring**: [`apps/memory_api/services/memory_scoring_v2.py`](../../apps/memory_api/services/memory_scoring_v2.py)

### Background Workers
- **Decay Worker**: Automatic importance decay (scheduled)
- **Summarization Worker**: Session-based consolidation
- **Dreaming Worker**: Batch reflection generation

**Worker Documentation**: [`apps/memory_api/tasks/README.md`](../../apps/memory_api/tasks/README.md)

---

## 🧪 Testing

Complete test coverage for all layers:

```bash
# Test memory layer logic
pytest apps/memory_api/tests/repositories/test_memory_repository.py

# Test context assembly
pytest apps/memory_api/tests/services/test_context_builder.py

# Test reflection generation
pytest apps/memory_api/tests/services/test_reflection_engine_v2.py
```

**Coverage**: 955 tests total, 892 passing (69% coverage)

---

**Version**: 2.1.0
**Last Updated**: 2025-12-08
**Status**: Production Ready ✅

**See also**: [Main README](../../README.md) | [Architecture Overview](../reference/concepts/architecture.md)
