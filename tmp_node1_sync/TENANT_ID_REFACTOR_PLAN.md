# Tenant ID Refactoring Plan - 2026-01-13

## Objective
To unify and streamline the handling of `tenant_id` across the RAE Memory API, ensuring consistency, type safety (UUID), and reducing redundancy, while adhering to best practices and avoiding hardcoding.

## Problem Statement
The current implementation of `tenant_id` handling exhibits inconsistencies:
1.  **Type Inconsistency**: `tenant_id` is sometimes treated as `str` and sometimes as `UUID` in different parts of the codebase, leading to redundant `str` to `UUID` conversions and potential errors.
2.  **Extraction Duplication**: `tenant_id` is extracted from HTTP headers/query parameters in multiple places (middleware, FastAPI dependencies).
3.  **Hardcoded Alias**: The special string "default-tenant" is mapped to a hardcoded `UUID("0000...")`, which is not configurable.

## Proposed Strategy (Revised)

The strategy focuses on centralizing `tenant_id` conversion and validation early in the request lifecycle, leveraging FastAPI's capabilities, and making the "default-tenant" alias configurable.

### Phase 1: Streamline `tenant_id` handling in `apps/memory_api/security/dependencies.py`

**Goal**: Make `get_and_verify_tenant_id` the single source of truth for extracting, validating, and converting `tenant_id` to `UUID`.

**Proposed Changes:**

1.  **Modify `get_and_verify_tenant_id`**:
    *   It will directly use FastAPI's `Header` and `Query` parameters to extract `tenant_id` as a string from `X-Tenant-Id` header or `tenant_id` query parameter.
    *   It will perform the `str` to `UUID` conversion, including mapping `DEFAULT_TENANT_ALIAS` (e.g., "default-tenant") to a `DEFAULT_TENANT_UUID` (e.g., `UUID("0000...")`).
    *   It will raise an `HTTPException` if `tenant_id` is missing or invalid.
    *   It will store the *converted UUID* on `request.state.tenant_id`.
    *   It will then call `auth.check_tenant_access` with the `UUID` (assuming `auth.py` is updated) and return the `UUID`.
    *   **Note**: The constants `DEFAULT_TENANT_ALIAS` and `DEFAULT_TENANT_UUID` will initially be defined within `dependencies.py` for clarity, with the understanding that they will be moved to a configuration file in a subsequent step.
2.  **Modify `verify_tenant_access`**: Change its signature to accept `tenant_id: UUID` (it will be called with a UUID).
3.  **Remove `get_verified_tenant_uuid`**: The separate `get_verified_tenant_uuid` dependency is no longer needed as its functionality is absorbed into the refined `get_and_verify_tenant_id`.

### Phase 2: Update `apps/memory_api/security/auth.py`

**Goal**: Ensure `auth.py` functions consistently handle `tenant_id` as `UUID` and remove redundant conversion logic.

**Proposed Changes:**

1.  **Modify `check_tenant_access`**: Change its signature to accept `tenant_id: UUID` instead of `str`. Remove the internal `str` to `UUID` conversion logic and the special "default-tenant" string check, as this is now handled upstream.
2.  **Modify `require_permission`**: Similar to `check_tenant_access`, change its signature to `tenant_id: UUID` and remove redundant conversion.

### Phase 3: Update other Dependencies and API Routes

**Goal**: Ensure all consumers of `tenant_id` dependencies are updated to expect and handle `UUID`.

**Proposed Changes:**

1.  **Update `require_tenant_role`**: Change its `tenant_id` parameter to `UUID` and remove its internal `str` to `UUID` conversion.
2.  **Trace and Update API Routes**: Go through all API routes (`routes/*.py`) and other dependencies that use `tenant_id` and ensure they:
    *   If using `Depends(get_and_verify_tenant_id)`, type their `tenant_id` parameter as `UUID`.
    *   If `tenant_id` is a `Path` or `Query` parameter, type it as `UUID` directly, allowing FastAPI to handle the conversion (and error if invalid).
    *   Ensure all internal calls pass `UUID` where `UUID` is expected.

### Phase 4: Refactor `DEFAULT_TENANT_ALIAS` and `DEFAULT_TENANT_UUID`

**Goal**: Move the hardcoded alias and UUID mapping to a configurable location.

**Proposed Changes:**

1.  Create or update a configuration file (e.g., `apps/memory_api/config.py`) to define `DEFAULT_TENANT_ALIAS` and `DEFAULT_TENANT_UUID`.
2.  Import these constants into `dependencies.py` and `auth.py` as needed.

### Phase 5: Clean up and Testing

**Goal**: Remove redundant middleware and thoroughly test the changes.

**Proposed Changes:**

1.  **Review `apps/memory_api/middleware/tenant.py`**: Once `get_and_verify_tenant_id` handles the full extraction, this middleware might become redundant or its scope could be significantly reduced. Re-evaluate its necessity.
2.  **Comprehensive Testing**: Write or update unit/integration tests to cover all `tenant_id` related flows, including valid/invalid UUIDs, "default-tenant" alias, missing `tenant_id`, and RBAC checks.

## Implementation Steps (for the Agent)

1.  Save this plan to `TENANT_ID_REFACTOR_PLAN.md`.
2.  Attempt to save this plan content to RAE memory.
3.  Proceed with Phase 1, starting with modifications to `apps/memory_api/security/dependencies.py`.

---

## Architectural Refactoring: Addressing `rae_core` Agnosticism

### Problem Statement (Identified during Phase 5: Testing)

During testing, a `ModuleNotFoundError: No module named 'rae_core'` was encountered. Investigation revealed a deeper architectural issue contradicting the mandate for `rae_core` to be **agnostic to infrastructure (database, disk, cache)**.

Currently:
1.  `rae-core/rae_core/adapters` was found to contain concrete implementations (e.g., `postgres_db.py`, `qdrant.py`, `redis.py`).
2.  `apps/memory_api`'s modules (e.g., `graph_repository_enhanced.py`) were attempting to import these concrete adapters directly from `rae_core.adapters`.

This means `rae_core` is coupled to specific infrastructure choices, violating its intended agnosticism. The `ModuleNotFoundError` is a symptom of this misplaced dependency.

### Mandate for `rae_core` Agnosticism

*   `rae_core` should define *interfaces* (e.g., `IDatabaseProvider`, `ICacheProvider`, `IVectorStore`) in `rae-core/rae_core/interfaces`.
*   `apps/memory_api` (or other application layers) should contain the *implementations* of these interfaces.
*   `apps/memory_api` should then *inject* these concrete implementations into `rae_core` components (e.g., `RAEEngine`).

### Proposed Refactoring Plan

This refactoring will be executed in a new dedicated session due to its complexity and architectural importance.

#### Zadania ukończone
*   **[DONE] Move Adapters**: Transfer all concrete adapter implementations from `rae-core/rae_core/adapters` to a new directory: `apps/memory_api/adapters`. This establishes `apps/memory_api` as the layer responsible for concrete infrastructure integrations.
*   **[DONE] Update Imports**: Modify all Python files within `apps/memory_api` (and potentially other parts of the project that import these adapters) to reflect the new import paths.

#### Pozostałe zadania (do wykonania)
1.  **Validate `RAEEngine` Integration**: Confirm that `rae_core.engine.RAEEngine` (and any other `rae_core` components) are correctly designed to accept instances of the *interface* types (from `rae_core/rae_core/interfaces`), rather than directly depending on concrete adapter classes.
2.  **Adjust `apps/memory_api/services/rae_core_service.py`**: This service is the primary instantiation point for `RAEEngine`. It must be updated to construct the now moved concrete adapters (from `apps/memory_api/adapters`) and pass them to the `RAEEngine` constructor as per the defined interfaces.
3.  **Re-evaluate Testing Environment**: After moving the adapters, re-run tests. The original `ModuleNotFoundError` for `rae_core` should resolve itself for adapter-related imports. Further `ModuleNotFoundError` might indicate other paths issues, which we'll address then.

**This refactoring directly addresses the `ModuleNotFoundError` by correcting the architectural placement of concrete adapter implementations and aligning with the `rae_core` agnosticism principle.**