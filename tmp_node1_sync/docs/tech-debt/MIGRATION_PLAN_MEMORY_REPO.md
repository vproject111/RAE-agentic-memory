# Migration Plan: MemoryRepository to RAE-Core Adapters

**Status**: Completed
**Target**: Eliminate `apps/memory_api/repositories/memory_repository.py`
**Goal**: Unified, backend-agnostic data access via `rae-core`.

## Context
Currently, `memory_api` uses a legacy `MemoryRepository` tightly coupled to PostgreSQL (`asyncpg`).
`rae-core` introduces a clean `IMemoryStorage` interface.
To fully adopt `rae-core`, we must migrate all functionality from `MemoryRepository` to `rae-core` adapters.

## Gap Analysis

The following features exist in `MemoryRepository` but are missing or different in `IMemoryStorage`:

| Legacy Method | RAE-Core Equivalent | Status / Action Needed |
| :--- | :--- | :--- |
| `insert_memory` | `store_memory` | **Compatible**. Check `project` vs `agent_id` mapping. |
| `get_memory_by_id` | `get_memory` | **Compatible**. |
| `delete_memory` | `delete_memory` | **Compatible`. |
| `get_semantic_memories` | `list_memories(layer='sm')` | **Compatible**. Use generic list with filters. |
| `get_reflective_memories` | `list_memories(layer='rm')` | **Compatible**. |
| `get_episodic_memories` | `list_memories(layer='em')` | **Compatible**. |
| `count_memories_by_layer` | `count_memories` | **Compatible**. |
| `get_average_strength` | **MISSING** | **Implemented in Phase 1**: `get_metric_aggregate(metric='importance', func='avg')`. |
| `update_memory_access_stats` (Batch) | `update_memory_access` (Single) | **Implemented in Phase 1**: `update_memory_access_batch`. |
| `update_importance` (Delta) | `update_memory` (Set value) | **Implemented in Phase 1**: `adjust_importance(delta)`. |

## Migration Strategy

### Phase 1: Extend RAE-Core Interfaces (PR 1) **Completed**
1.  Update `IMemoryStorage` in `rae-core` to include:
    *   `get_metric_aggregate(metric: str, func: str, filters: dict) -> float` (Generic aggregation)
    *   `update_memory_access_batch(memory_ids: list[UUID], tenant_id: str)`
    *   `adjust_importance(memory_id: UUID, delta: float, tenant_id: str)`
2.  Implement these methods in `PostgreSQLStorage` adapter.
3.  Release new version of `rae-core`.

### Phase 2: Refactor Memory API (PR 2) **Completed**
1.  Update `RAECoreService` to expose new methods.
2.  Replace usages in `services/` layer:
    *   Replace `MemoryRepository.insert_memory` -> `RAECoreService.store_memory`
    *   Replace `MemoryRepository.get_*_memories` -> `RAECoreService.list_memories`
3.  Run parallel tests (Dual Write/Read if risky, or Feature Flag). -> **Verified via Unit Tests**

### Phase 3: Cleanup (PR 3) **Completed**
1.  Delete `apps/memory_api/repositories/memory_repository.py`.
2.  Remove direct `asyncpg` dependency from `memory_api` (except for `main.py` pool creation, if still needed for adapter factory).
3.  Cleaned up all services and tests referencing `MemoryRepository`.

## Benefits
- **Zero Tech Debt**: Single source of truth for DB queries.
- **Agnostic**: Enables SQLite/InMemory testing for Memory API.
- **Consistency**: All memory logic (including validations) in one place.

## Token Economy Note
This migration follows the **RAE-First** principle by leveraging the existing `rae-core` investment instead of patching legacy code.
