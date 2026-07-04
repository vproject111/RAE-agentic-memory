# Reflective Memory Configuration Reference

**Status**: Production Ready
**Version**: 1.0 (Reflective Memory V1)
**Last Updated**: 2025-11-28

## Overview

This document provides the **canonical reference** for all configuration flags related to RAE's Reflective Memory system. Every flag listed here **actually controls runtime behavior** and has been tested.

---

## Core Feature Flags

### `REFLECTIVE_MEMORY_ENABLED`

**Type**: `bool`
**Default**: `True`
**Environment Variable**: `REFLECTIVE_MEMORY_ENABLED`

**Purpose**: Master switch for all reflective memory operations.

**When `True`**:
- Reflections are retrieved and included in agent context
- Background workers can generate new reflections
- Lessons Learned section appears in prompts

**When `False`**:
- No reflections retrieved (empty result set)
- Context shows "[Reflective memory is currently disabled]"
- Dreaming and summarization workers exit early
- New reflections are NOT created

**Code References**:
- `apps/memory_api/services/context_builder.py:350` - Check before retrieval
- `apps/memory_api/workers/memory_maintenance.py:325` - Dreaming worker check
- `apps/memory_api/workers/memory_maintenance.py:161` - Summarization worker check

**Test Coverage**: `apps/memory_api/tests/test_reflective_flags.py:test_reflective_memory_disabled_no_reflections`

---

### `REFLECTIVE_MEMORY_MODE`

**Type**: `enum["lite", "full"]`
**Default**: `"full"`
**Environment Variable**: `REFLECTIVE_MEMORY_MODE`

**Purpose**: Controls the intensity of reflective operations and resource usage.

#### Mode Comparison

| Feature | `lite` Mode | `full` Mode |
|---------|-------------|-------------|
| Reflection Retrieval | ✅ Up to 3 items | ✅ Up to 5 items |
| Dreaming Worker | ❌ Disabled by default | ✅ Enabled |
| Summarization Worker | ✅ Enabled | ✅ Enabled |
| Token Budget | ~512 tokens | ~1024 tokens |
| Resource Usage | Low | Medium |

**Config Validator**: `apps/memory_api/config.py:model_validator` enforces mode-specific limits:
- `lite`: Sets `REFLECTIVE_MAX_ITEMS_PER_QUERY = 3`
- `full`: Sets `REFLECTIVE_MAX_ITEMS_PER_QUERY = 5`

**Use Cases**:
- **`lite`**: Cost-conscious deployments, PoCs, development
- **`full`**: Production deployments with full meta-learning capabilities

**Code References**:
- `apps/memory_api/config.py:104-116` - Mode-based overrides
- `apps/memory_api/services/context_builder.py:365` - Mode-aware retrieval

**Test Coverage**: `apps/memory_api/tests/test_reflective_flags.py:test_lite_mode_uses_lower_limits`

---

### `DREAMING_ENABLED`

**Type**: `bool`
**Default**: `True`
**Environment Variable**: `DREAMING_ENABLED`

**Purpose**: Controls background reflection generation from high-importance memories.

**When `True`**:
- Dreaming worker analyzes high-importance episodes
- New reflections and strategies are created in background
- Meta-learning from experience is active

**When `False`**:
- Dreaming worker exits immediately
- No new automatic reflections generated
- System only uses manually created reflections

**Interaction with `REFLECTIVE_MEMORY_MODE`**:
- In `lite` mode, dreaming is typically disabled regardless of this flag
- In `full` mode, this flag controls dreaming
- Check: `REFLECTIVE_MEMORY_ENABLED AND DREAMING_ENABLED`

**Code References**:
- `apps/memory_api/workers/memory_maintenance.py:325-333` - Dreaming worker check
- `apps/memory_api/tasks/background_tasks.py:513-519` - Celery task check

**Test Coverage**: `apps/memory_api/tests/test_reflective_flags.py:test_dreaming_disabled_no_dreaming`

---

### `SUMMARIZATION_ENABLED`

**Type**: `bool`
**Default**: `True`
**Environment Variable**: `SUMMARIZATION_ENABLED`

**Purpose**: Controls automatic session summarization.

**When `True`**:
- Long sessions are automatically summarized
- Episodic summaries are created for sessions exceeding threshold
- Memory consolidation is active

**When `False`**:
- No automatic summaries created
- Sessions remain as raw episodic memories
- Manual summarization still possible via API

**Code References**:
- `apps/memory_api/workers/memory_maintenance.py:161-167` - Summarization worker check

**Test Coverage**: `apps/memory_api/tests/test_reflective_flags.py:test_summarization_disabled_no_summary`

---

## Retrieval Configuration

### `REFLECTIVE_MAX_ITEMS_PER_QUERY`

**Type**: `int`
**Default**: `5` (full mode), `3` (lite mode)
**Environment Variable**: `REFLECTIVE_MAX_ITEMS_PER_QUERY`

**Purpose**: Maximum number of reflections to retrieve per context building.

**Behavior**:
- Controls `k` parameter in reflection retrieval
- Higher values = more context, more tokens, higher cost
- Lower values = less context, faster, lower cost

**Override**: Automatically set by `REFLECTIVE_MEMORY_MODE` validator

**Code References**:
- `apps/memory_api/services/context_builder.py:359` - Retrieval limit
- `apps/memory_api/config.py:105` - Configuration

---

### `REFLECTION_MIN_IMPORTANCE_THRESHOLD`

**Type**: `float` (0.0-1.0)
**Default**: `0.5`
**Environment Variable**: `REFLECTION_MIN_IMPORTANCE_THRESHOLD`

**Purpose**: Minimum importance score for reflections to be included in context.

**Behavior**:
- Only reflections with `importance >= threshold` are retrieved
- Higher threshold = only most important reflections
- Lower threshold = more reflections included

**Typical Values**:
- `0.3`: Include most reflections (noisy)
- `0.5`: Balanced (default)
- `0.7`: Only high-importance reflections
- `0.9`: Only critical insights

**Code References**:
- `apps/memory_api/services/context_builder.py:360` - Min importance filter

---

### `REFLECTIVE_LESSONS_TOKEN_BUDGET`

**Type**: `int`
**Default**: `1024` (full mode), `512` (lite mode)
**Environment Variable**: `REFLECTIVE_LESSONS_TOKEN_BUDGET`

**Purpose**: Maximum tokens allocated to Lessons Learned section in prompts.

**Behavior**:
- Limits total token consumption by reflections
- Reflections are truncated/omitted if budget exceeded
- Helps control LLM API costs

**Code References**:
- `apps/memory_api/config.py:106` - Token budget configuration

---

## Worker Configuration

### Decay Parameters

#### `MEMORY_BASE_DECAY_RATE`

**Type**: `float`
**Default**: `0.01`
**Environment Variable**: `MEMORY_BASE_DECAY_RATE`

**Purpose**: Base rate of importance decay per day.

**Behavior**:
- Applied daily by decay worker
- `0.01` = 1% decay per day
- Adjusted by recency and usage patterns

**Code References**:
- `apps/memory_api/workers/memory_maintenance.py:474` - Used in decay cycle

---

#### `MEMORY_ACCESS_COUNT_BOOST`

**Type**: `bool`
**Default**: `True`
**Environment Variable**: `MEMORY_ACCESS_COUNT_BOOST`

**Purpose**: Whether frequently accessed memories decay slower.

**When `True`**:
- High `usage_count` reduces effective decay rate
- Popular memories preserved longer

**When `False`**:
- All memories decay at same rate regardless of usage

**Code References**:
- `apps/memory_api/workers/memory_maintenance.py:475` - Usage boost parameter

---

### Dreaming Parameters

#### `DREAMING_LOOKBACK_HOURS`

**Type**: `int`
**Default**: `24`
**Environment Variable**: `DREAMING_LOOKBACK_HOURS`

**Purpose**: How far back to look for high-importance episodes during dreaming.

**Code References**:
- `apps/memory_api/workers/memory_maintenance.py:490` - Lookback window

---

#### `DREAMING_MIN_IMPORTANCE`

**Type**: `float` (0.0-1.0)
**Default**: `0.6`
**Environment Variable**: `DREAMING_MIN_IMPORTANCE`

**Purpose**: Minimum importance for episodes to be considered for dreaming.

**Code References**:
- `apps/memory_api/workers/memory_maintenance.py:491` - Importance filter

---

#### `DREAMING_MAX_SAMPLES`

**Type**: `int`
**Default**: `20`
**Environment Variable**: `DREAMING_MAX_SAMPLES`

**Purpose**: Maximum number of episodes to analyze per dreaming cycle.

**Behavior**:
- Prevents dreaming worker from processing too many memories
- Controls cost and execution time

**Code References**:
- `apps/memory_api/workers/memory_maintenance.py:492` - Sample limit

---

### Summarization Parameters

#### `SUMMARIZATION_MIN_EVENTS`

**Type**: `int`
**Default**: `10`
**Environment Variable**: `SUMMARIZATION_MIN_EVENTS`

**Purpose**: Minimum number of events in a session before summarization.

**Behavior**:
- Sessions with fewer events are not summarized
- Prevents summarization of trivial interactions

**Code References**:
- `apps/memory_api/config.py:131` - Threshold configuration

---

#### `SUMMARIZATION_EVENT_THRESHOLD`

**Type**: `int`
**Default**: `50`
**Environment Variable**: `SUMMARIZATION_EVENT_THRESHOLD`

**Purpose**: Number of events that triggers automatic summarization.

**Behavior**:
- Sessions crossing this threshold are queued for summarization
- Higher value = fewer summaries, lower processing cost

---

## Behavior Matrix

This table shows **actual tested behavior** for different configuration combinations:

| `REFLECTIVE_MEMORY_ENABLED` | `REFLECTIVE_MEMORY_MODE` | `DREAMING_ENABLED` | `SUMMARIZATION_ENABLED` | Result |
|-----------------------------|--------------------------|-------------------|------------------------|--------|
| `False` | any | any | any | ❌ No reflections, no workers |
| `True` | `lite` | any | `True` | ✅ Summaries only, 3 reflection limit |
| `True` | `lite` | any | `False` | ⚠️ Reflections only (retrieval), no generation |
| `True` | `full` | `False` | `True` | ✅ Summaries + reflections, no dreaming |
| `True` | `full` | `True` | `True` | ✅ Full system (5 reflection limit) |
| `True` | `full` | `True` | `False` | ✅ Dreaming + reflections, no summaries |

**Test Coverage**: `apps/memory_api/tests/test_reflective_flags.py:test_maintenance_with_all_flags_*`

---

## Production Recommendations

### Cost-Conscious Deployment (Lite)

```bash
export REFLECTIVE_MEMORY_ENABLED=True
export REFLECTIVE_MEMORY_MODE=lite
export DREAMING_ENABLED=False
export SUMMARIZATION_ENABLED=True
export REFLECTIVE_MAX_ITEMS_PER_QUERY=3
export REFLECTIVE_LESSONS_TOKEN_BUDGET=512
```

**Expected behavior**:
- Minimal token usage (~512 tokens for reflections)
- No background dreaming (cost control)
- Session summarization active
- 3 reflections per query maximum

---

### Full Production Deployment

```bash
export REFLECTIVE_MEMORY_ENABLED=True
export REFLECTIVE_MEMORY_MODE=full
export DREAMING_ENABLED=True
export SUMMARIZATION_ENABLED=True
export REFLECTIVE_MAX_ITEMS_PER_QUERY=5
export REFLECTIVE_LESSONS_TOKEN_BUDGET=1024
export DREAMING_LOOKBACK_HOURS=24
export DREAMING_MIN_IMPORTANCE=0.6
```

**Expected behavior**:
- Full reflective capabilities
- Background learning via dreaming
- Session consolidation via summarization
- Up to 5 reflections per query
- ~1024 tokens for Lessons Learned section

---

### Development / Testing

```bash
export REFLECTIVE_MEMORY_ENABLED=True
export REFLECTIVE_MEMORY_MODE=lite
export DREAMING_ENABLED=False
export SUMMARIZATION_ENABLED=False
```

**Expected behavior**:
- Reflections enabled for testing context building
- No background workers running
- Minimal resource usage

---

## Validation

### Configuration Validation

The configuration is validated on startup:

```python
# apps/memory_api/config.py
@model_validator(mode='after')
def apply_mode_overrides(self) -> 'Settings':
    """Apply mode-specific overrides"""
    if not self.REFLECTIVE_MEMORY_ENABLED:
        # When disabled, force all related features off
        self.DREAMING_ENABLED = False

    if self.REFLECTIVE_MEMORY_MODE == 'lite':
        # Lite mode: lower limits
        self.REFLECTIVE_MAX_ITEMS_PER_QUERY = 3
        self.REFLECTIVE_LESSONS_TOKEN_BUDGET = 512
        self.DREAMING_ENABLED = False

    elif self.REFLECTIVE_MEMORY_MODE == 'full':
        # Full mode: higher limits
        self.REFLECTIVE_MAX_ITEMS_PER_QUERY = 5
        self.REFLECTIVE_LESSONS_TOKEN_BUDGET = 1024

    return self
```

### Runtime Checks

Every flag has runtime checks in the code:

```python
# Example from ContextBuilder
if not settings.REFLECTIVE_MEMORY_ENABLED:
    logger.info("reflections_retrieval_skipped", reason="reflective_memory_disabled")
    return []
```

---

## Troubleshooting

### Reflections Not Appearing in Context

**Check**:
1. `REFLECTIVE_MEMORY_ENABLED=True`
2. Reflections exist in DB with `layer='rm'`
3. Importance >= `REFLECTION_MIN_IMPORTANCE_THRESHOLD`
4. Logs show `reflections_retrieval_started`

### Dreaming Worker Not Creating Reflections

**Check**:
1. `REFLECTIVE_MEMORY_ENABLED=True`
2. `DREAMING_ENABLED=True`
3. `REFLECTIVE_MEMORY_MODE=full` (or explicitly enabled in lite)
4. High-importance memories exist (importance >= `DREAMING_MIN_IMPORTANCE`)
5. Celery worker is running
6. Logs show `dreaming_cycle_started`

### Summarization Not Working

**Check**:
1. `SUMMARIZATION_ENABLED=True`
2. Sessions have >= `SUMMARIZATION_MIN_EVENTS` events
3. Logs show `session_summarization_started`

---

## Related Documentation

- [Memory Model](./MEMORY_MODEL.md) - Canonical layer/type mapping
- [Reflective Memory V1](./REFLECTIVE_MEMORY_V1.md) - Implementation details
- [Status](./STATUS.md) - Current project status
- [Testing Status](./TESTING_STATUS.md) - Test coverage

---

**Maintainers**: Update this document when adding new flags or changing behavior
**Last Reviewed**: 2025-11-28
**Next Review**: Before v1.1 release
