# PLAN_REPAIR_001: RAE Engineering Remediation Strategy

> **Status:** Draft / Ready for Execution
> **Source:** FINAL_RAE_ENGINEERING_ASSESSMENT.md
> **Goal:** Eliminate 100% of identified engineering risks without breaking existing functionality.

## 1. Executive Summary

This plan addresses critical stability and integrity risks identified during the Cold Engineering Review. It prioritizes the **prevention of system lock-up** (Event Loop Starvation) and **data corruption** (Ghost Memories).

**Success Metric:** 0 identified problems from the engineering assessment remaining.

## 2. Phase 1: Urgent Stabilization (Event Loop Safety)

**Objective:** Prevent `ReflectionPipeline` from blocking the async event loop during heavy clustering operations.

*   **Risk:** CRITICAL (System Unresponsiveness)
*   **Target:** `apps/memory_api/services/reflection_pipeline.py`

### Implementation Plan
1.  **Refactor `_cluster_memories`**:
    *   Identify CPU-bound calls: `HDBSCAN.fit_predict` and `KMeans.fit_predict`.
    *   Wrap these calls using `asyncio.get_running_loop().run_in_executor(None, ...)` to offload them to a thread pool.
    *   Ensure thread safety of the data passed to the executor.
2.  **Verification**:
    *   Create a load test that triggers reflection generation while simultaneously pinging `/health`.
    *   Assert that `/health` remains responsive (< 500ms) during clustering of 1000+ vectors.

## 3. Phase 2: Data Integrity (Reconciliation Engine)

**Objective:** Fix the "Dual Write" consistency issue between PostgreSQL and Qdrant.

*   **Risk:** MEDIUM (Ghost Memories / Orphaned Embeddings)
*   **Target:** New Service `ConsistencyService` + Background Task.

### Implementation Plan
1.  **Create `ConsistencyService`**:
    *   Implement method `scan_orphaned_embeddings()`:
        *   Scroll through Qdrant points.
        *   Check existence of IDs in Postgres (in batches).
        *   Delete points from Qdrant if missing in Postgres.
2.  **Schedule Background Job**:
    *   Add a periodic task (e.g., daily or triggered via API) to run the reconciliation.
3.  **Enhance `delete_memory`**:
    *   Add explicit error logging with a specific tag `[INTEGRITY_RISK]` if vector deletion fails.
4.  **Verification**:
    *   Test: Manually inject a vector into Qdrant that doesn't exist in Postgres.
    *   Run the reconciliation job.
    *   Assert the orphan is removed.

## 4. Phase 3: Architectural Hygiene & Cleanup

**Objective:** Reduce coupling and fix naming drift.

*   **Risk:** MEDIUM (Lock-in & Maintenance Overhead)
*   **Target:** `rae-core`, `apps/memory_api/adapters/`, `MemoryLayer` enum.

### Implementation Plan
1.  **Fix Naming Drift**:
    *   In `apps/memory_api/models.py`, map `MemoryLayer.stm` to `MemoryLayer.working` and `ltm` to `semantic` using Pydantic aliases or a migration script for the codebase (not DB yet).
    *   Ensure all new code uses the standard names (`working`, `semantic`).
2.  **Decouple Adapters**:
    *   Refactor `get_storage_adapter` in `apps/memory_api/adapters/storage.py`.
    *   Read `RAE_STORAGE_TYPE` from env (default: `postgres`).
    *   If `postgres`, return `PostgreSQLStorage`.
    *   (Future proofing for other backends).
3.  **Verification**:
    *   Run full test suite (`make test-unit`) to ensure no regression.
    *   Verify `mypy` passes with strict checking.

## 5. Execution Order & Safety Checklist

1.  **Snapshot**: Ensure DB backup before Phase 2.
2.  **Test-First**: Write the reproduction/verification test *before* the fix.
3.  **Rollback**: Each phase is isolated. If Phase 1 fails, revert `reflection_pipeline.py` changes.

## 6. Todo List

- [ ] **Phase 1**: Offload clustering to thread pool.
- [ ] **Phase 1**: Verify async responsiveness under load.
- [ ] **Phase 2**: Implement `ConsistencyService`.
- [ ] **Phase 2**: Add reconciliation task to `background_tasks.py`.
- [ ] **Phase 3**: Refactor `get_storage_adapter` factory.
- [ ] **Phase 3**: Standardize `MemoryLayer` enum usage.
