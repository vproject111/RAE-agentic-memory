# REPORT_03_COLD_START.md

## Goal
Verify that a completely clean environment can start RAE, create required structures, and reach a valid initial state.

## Findings

### Cold Start Path
1. **Infrastructure Bootstrap**: `main.py` lifespan handler initializes Postgres, Redis, and Qdrant connections.
2. **Qdrant Auto-creation**: Collections are automatically created if missing, using the `RAE_MEMORY_CONTRACT_V1` definition.
3. **Database Migration**: Alembic migrations run automatically on startup in `init` or `migrate` mode.
4. **Validation**: `ValidationService` verifies the resulting schema against the contract.
5. **Cache Warmup**: `rebuild_full_cache()` populates Redis from Postgres.

### Mandatory Prerequisites
- Postgres, Redis, and Qdrant instances must be reachable via provided environment variables.
- `RAE_DB_MODE` must be set to `init` or `migrate` for the first run.

### Failure Points
- **Incomplete Cleanup**: If migrations fail midway, the system might enter an inconsistent state.
- **Resource Duplication**: `rebuild_full_cache()` creates its own `asyncpg` pool, doubling connections briefly during startup.
- **Network Latency**: No retry mechanism observed for the initial infrastructure connectivity check in `main.py`.

## Risk Level: LOW
The system has a very mature cold-start mechanism with automated schema creation and validation.
