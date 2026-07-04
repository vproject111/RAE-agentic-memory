# Database Refactor Upgrade Notes (Phase 1 & 2)

## API Changes (v2)
The `StoreMemoryRequest` (and V2 equivalent) has been updated to accept canonical fields explicitly:
- `session_id` (string, optional): For conversation grouping.
- `memory_type` (string, optional): e.g., 'text', 'code', 'chat'.
- `ttl` (int, optional): Time-to-live in seconds (maps to `expires_at`).

## Database Schema Requirements
The `memories` table MUST have the following columns (previously considered "dead" or missing):
- `project` (VARCHAR)
- `session_id` (TEXT)
- `source` (VARCHAR)

*Note: `memory_type` and `expires_at` were already present and used.*

## Logic & Storage Changes
- **No Duplication:** The `project` and `source` fields are now stored **exclusively** in their respective columns and are **removed** from the `metadata` JSON blob to prevent data duplication.
- **Backward Compatibility:**
    - Input: Old clients sending `project` via metadata might still work if they hit V1 endpoints that weren't updated, but V2/Service strictly uses the explicit arguments.
    - Output: `get_memory` now returns `project`, `session_id`, `memory_type`, `source` as top-level dictionary keys. Clients relying on `metadata['project']` *may break* if they don't check top-level keys.

## Migration Actions
1. Ensure the `memories` table has the required columns.
2. If restoring from backup or legacy data, run a migration script (Phase 4) to backfill `project`/`source`/`session_id` from `metadata` into the new columns.

---

# Upgrade Notes (v2.7.0)

**What changed:**
The Memory API and Database layer have been refactored to support ISO 42001 compliance and high-performance querying. Key fields (`session_id`, `project`, `source`) are now first-class database citizens.

**Compatibility:**
*   **API Consumers (V1/V2):** Fully backward compatible for writes. Reads now return these fields at the root level of the memory object.
*   **Database:**
    *   Requires running the Phase 4 migration (`alembic/versions/20260105_phase4_backfill.py`) to populate new columns from existing JSON metadata.
    *   Requires running the Phase 5 migration (`alembic/versions/20260105_phase5_indexes.py`) to create performance indexes.

**Feature Flags:**
*   No new environment variables required. The system automatically uses the new columns.

**Critical Action:**
Run the migrations immediately after deployment to ensure the Dashboard and Graph features can see historical data and perform efficiently.
```bash
alembic upgrade head
```

**Performance Improvements:**
*   Added B-Tree indexes on `project`, `session_id`, `source`.
*   Added Composite Index on `(project, created_at)` for optimized time-range queries in Dashboard.

**Schema Additions:**
*   `strength` (FLOAT, default 1.0): Added to `memories` table to support explicit decay tracking.

**Vector Handling Notes:**
*   **Variable Lengths:** The `embedding` column in Postgres is typed (e.g., `VECTOR(1536)`). Storing mixed-dimension vectors (e.g., from small vs large LLMs) in the *same* column is **not supported**. If multi-model support is needed, consider separate tables or a dedicated vector database configuration.
*   **Qdrant Point ID:** RAE uses the memory `id` (UUID) directly as the Qdrant Point ID. The `qdrant_point_id` column in Postgres is redundant and should be considered deprecated/dead.
