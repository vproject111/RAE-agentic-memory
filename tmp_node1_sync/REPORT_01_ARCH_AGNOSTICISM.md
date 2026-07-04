# REPORT_01_ARCH_AGNOSTICISM.md

## Goal
Verify that RAE core is truly agnostic with respect to databases, storage backends, cache implementations, and execution environment.

## Findings

### Confirmed Agnostic Components
- **`IMemoryStorage` Interface**: Located in `rae-core`, it provides a clean, abstract definition of memory operations.
- **`ICacheProvider` Interface**: Provides abstraction for caching mechanisms.

### Suspected Hidden Coupling
- **Interface Leakage**: Some methods in `IMemoryStorage`, such as `delete_memories_with_metadata_filter`, strongly imply support for JSONB querying, which is a Postgres-specific strength. Implementing this efficiently in simpler backends (e.g., SQLite or FileSystem) would be challenging.
- **Full-Text Search Assumption**: `search_memories` mentions full-text search in docstrings, which assumes the underlying storage provides indexing for search, potentially coupling the interface to search-capable engines.

### Explicit Violations
- **Hardcoded Adapters**: The factory functions in `apps/memory_api/adapters/storage.py` and `cache.py` directly instantiate `PostgreSQLStorage` and `RedisCache`. There is no configuration-driven strategy to switch providers at runtime without code modification in the API layer.
- **Postgres-Specific Migrations**: Alembic migrations use Postgres-specific types like `JSONB` and `ARRAY(sa.String())`, making the schema definition tightly coupled to PostgreSQL.

## Risk Level: MEDIUM
While the architecture uses interfaces, the application is currently "Postgres-locked" by its instantiation patterns and schema definitions. Switching to a different relational database would require a significant overhaul of migrations and some adapter logic.
