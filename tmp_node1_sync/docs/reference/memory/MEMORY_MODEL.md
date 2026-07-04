# Memory Model - Layer and Type Mapping Reference

**Quick Reference:** This document defines the authoritative mapping between conceptual memory layers and code implementation.

## 4-Layer Conceptual Model → Code Mapping

| Conceptual Layer | `layer` (DB enum) | `memory_type` (DB text) | Primary Use Cases |
|------------------|-------------------|-------------------------|-------------------|
| **Layer 1: Sensory** | `stm` | `sensory` | • Raw event streams<br>• Tool call inputs/outputs<br>• Unprocessed logs<br>• Immediate sensory data |
| **Layer 2: Working Memory** | `stm`, `em` | `episodic` (recent) | • Active session context<br>• Recent conversation<br>• Current task state<br>• Temporary working set |
| **Layer 3: Long-Term Memory** | `ltm`, `em` | `episodic`, `semantic`, `profile` | • Completed sessions<br>• Domain knowledge<br>• User preferences<br>• Historical facts |
| **Layer 4: Reflective Memory** | `rm` | `reflection`, `strategy` | • Post-mortem analysis<br>• Lessons learned<br>• Strategic patterns<br>• Meta-learning |

## Field Definitions

### `layer` Field
**Type:** Enum (`stm` \| `ltm` \| `em` \| `rm`)
**Purpose:** Determines processing stage and retention policy

- **`stm`** (Short-Term Memory): Transient, low retention priority
- **`ltm`** (Long-Term Memory): Permanent, high retention priority
- **`em`** (Episodic Memory): Time-bound, moderate retention
- **`rm`** (Reflective Memory): High value, permanent retention

### `memory_type` Field
**Type:** Text
**Purpose:** Functional classification for semantic understanding

- **`sensory`**: Raw, unprocessed inputs
- **`episodic`**: Time-sequenced events and interactions
- **`semantic`**: Factual knowledge and documentation
- **`profile`**: User/system configuration and preferences
- **`reflection`**: Analysis and post-mortem insights
- **`strategy`**: Actionable patterns and rules

## Typical Combinations

```
┌─────────────────┬────────┬──────────────┬─────────────────────┐
│ Use Case        │ layer  │ memory_type  │ Description         │
├─────────────────┼────────┼──────────────┼─────────────────────┤
│ Tool call log   │ stm    │ sensory      │ Raw execution trace │
│ Chat message    │ em     │ episodic     │ Conversation turn   │
│ User preference │ ltm    │ profile      │ Persistent setting  │
│ Lesson learned  │ rm     │ reflection   │ Post-mortem insight │
│ Best practice   │ rm     │ strategy     │ Reusable pattern    │
│ Knowledge doc   │ ltm    │ semantic     │ Domain knowledge    │
└─────────────────┴────────┴──────────────┴─────────────────────┘
```

## Retention and Decay Policies

| Layer | Base Decay Rate | Access Count Effect | Typical TTL |
|-------|----------------|---------------------|-------------|
| Sensory (Layer 1) | High (0.01/day) | Minimal | Hours to days |
| Working (Layer 2) | Medium (0.005/day) | Moderate | Days to weeks |
| LTM (Layer 3) | Low (0.001/day) | High | Months to years |
| Reflective (Layer 4) | Very Low (0.0001/day) | Very High | Permanent |

**Note:** Actual decay rates are configurable via `MEMORY_BASE_DECAY_RATE` and adjusted by access patterns.

## Migration Notes

### Legacy Layer Values
Existing code may use these legacy layer values:
- `em` → Should map to Layer 2/3 (episodic)
- `sm` → Should map to Layer 3 (semantic)
- `rm` → Maps to Layer 4 (reflective)
- `stm` → Maps to Layer 1/2 (sensory/working)
- `ltm` → Maps to Layer 3 (long-term)

### Database Schema
See: `alembic/versions/d4e5f6a7b8c9_add_reflective_memory_columns.py`

Key columns:
```sql
layer TEXT NOT NULL          -- 'stm', 'ltm', 'em', 'rm'
memory_type TEXT NOT NULL    -- 'sensory', 'episodic', etc.
session_id UUID              -- Links to execution sessions
importance FLOAT             -- 0.0-1.0 score
last_accessed_at TIMESTAMP   -- For decay calculation
usage_count INT              -- Access frequency
```

## Code References

### Models
- `apps/memory_api/models.py`: Core `MemoryLayer` enum
- `apps/memory_api/models/reflection_v2_models.py`: Reflective memory types

### Services
- `apps/memory_api/services/memory_scoring_v2.py`: Decay and importance
- `apps/memory_api/services/reflection_engine_v2.py`: Reflection generation
- `apps/memory_api/services/context_builder.py`: Layer 2 (Working Memory)

### Repositories
- `apps/memory_api/repositories/memory_repository.py`: Data access layer

## Best Practices

### When to use each layer

**Layer 1 (Sensory):**
- ✅ Raw tool outputs before processing
- ✅ Temporary execution traces
- ❌ Don't use for long-term storage

**Layer 2 (Working):**
- ✅ Active conversation context
- ✅ Current task state
- ❌ Don't persist after session ends

**Layer 3 (LTM):**
- ✅ Completed interactions
- ✅ Domain knowledge
- ✅ User preferences
- ❌ Don't use for meta-learning

**Layer 4 (Reflective):**
- ✅ Post-mortem analysis
- ✅ Recurring patterns
- ✅ Strategic insights
- ❌ Don't use for individual events

### Choosing memory_type

```python
# Example decision tree
if is_raw_input:
    memory_type = "sensory"
elif is_conversation_turn:
    memory_type = "episodic"
elif is_factual_knowledge:
    memory_type = "semantic"
elif is_user_setting:
    memory_type = "profile"
elif is_lesson_learned:
    memory_type = "reflection"
elif is_reusable_strategy:
    memory_type = "strategy"
```

## Related Documentation

- [Reflective Memory V1 Implementation](./REFLECTIVE_MEMORY_V1.md)
- [Memory Scoring](../apps/memory_api/services/memory_scoring_v2.py)
- [Context Building](../apps/memory_api/services/context_builder.py)
- [Architecture Overview](./architecture.md)

---

**Last Updated:** 2025-11-28
**Status:** ✅ Stable Reference
