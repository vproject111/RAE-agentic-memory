# RAE Audit Report - 2026-01-17

## 1. Dashboard Fix (Completed)
- **Issue:** Dashboard Overview showed 0 for new projects because the background aggregation job runs hourly.
- **Fix:** Implemented "Live Fallback" in `metrics_repository.py`. If historical data is missing, the system now queries the `memories` table directly for a real-time count.
- **Status:** Committed to `develop`.

## 2. Data Integrity Audit (Ghost Columns)
- **Finding:** The following columns in `memories` table are effectively "dead" (100% or near 100% NULL):
  - `session_id`: 100% NULL.
  - `ttl`: 100% NULL.
- **Root Cause:**
  - `session_id`: supported by API (`StoreMemoryRequest`) and Adapter, but clients (including `verify_mcp.py` and likely `screenwatcher`) are passing `None`.
  - `ttl`: The logic uses `expires_at` column. `ttl` seems to be a legacy column that is no longer populated by the adapter.
- **Recommendation:**
  - Deprecate/Drop `ttl` column in future migration.
  - Enforce `session_id` usage in clients if ISO 42001 compliance (provenance) is required.

## 3. Logic Audit (Code Duplication)
- **Finding:** `ContextBuilder` logic is duplicated/fragmented.
  - `apps/memory_api/services/context_builder.py`: Complex, service-oriented, handles retrieval and formatting.
  - `rae-core/rae_core/context/builder.py`: Utility-oriented, handles token management and formatting.
- **Status:** The `apps` version does *not* use the `core` version, leading to divergent formatting logic.
- **Recommendation:** Refactor `apps/.../context_builder.py` to use `rae-core/.../context/builder.py` for the final assembly step (`_build_formatted_context`), reducing duplication.

## 4. Environment
- **RAE-First:** Validated. MCP connection verified.
- **Databases:** Postgres and Qdrant are active and consistent.
