# VERSION MATRIX - RAE (Reflective Agentic Memory Engine)

**Current Release:** `2.0.0-enterprise`
**Release Date:** TBD (in development)
**Status:** Pre-release (Enterprise Grade preparation)

---

## Version Strategy

RAE follows **Semantic Versioning 2.0.0** (https://semver.org/):

```
MAJOR.MINOR.PATCH[-PRERELEASE]
  |     |     |        |
  |     |     |        └─ Optional: alpha, beta, rc, enterprise
  |     |     └─ Backwards-compatible bug fixes
  |     └─ New features (backwards-compatible)
  └─ Breaking changes
```

---

## Component Versions (v2.0.0-enterprise)

### Production Ready (GA - Generally Available) ✅

Components ready for production use with full support and stability guarantees.

| Component | Version | Status | Support | Description |
|-----------|---------|--------|---------|-------------|
| **Core API** | 2.0.0-enterprise | ✅ **GA** | Full | Main Memory API with 4-layer architecture |
| **Enterprise Security** | 2.0.0 | ✅ **GA** | Full | RBAC, authentication, audit logging, tenant isolation |
| **Memory Decay Scheduler** | 2.0.0 | ✅ **GA** | Full | Automated importance decay with temporal logic |
| **GraphRAG** | 2.0.0 | ✅ **GA** | Full | Knowledge graph + hybrid search |
| **MCP Integration** | 1.2.0 | ✅ **GA** | Full | Model Context Protocol server (OpenTelemetry, load tests, rate limiting) |
| **Governance API** | 2.0.0 | ✅ **GA** | Full | Cost tracking & budget management |
| **Context Watcher** | 1.0.0 | ✅ **GA** | Full | File system monitoring |
| **Reranker Service** | 1.0.0 | ✅ **GA** | Full | Result re-ranking service |

### Beta (Production-Ready but Evolving) 🟡

Components suitable for production but may have breaking changes in minor versions.

| Component | Version | Status | Support | Description |
|-----------|---------|--------|---------|-------------|
| **ML Service** | 2.0.0 | 🟡 **Beta** | Best-effort | Embeddings, NLP, Entity Resolution |
| **Dashboard** | 1.0.0 | 🟡 **Beta** | Best-effort | Web UI for monitoring & visualization |
| **Python SDK** | 0.1.0 | 🟡 **Beta** | Best-effort | Client library for Python |
| **Helm Chart** | 1.0.0 | 🟡 **Beta** | Best-effort | Kubernetes deployment |

### Experimental (Preview Features) ⚠️

Components in active development, not recommended for production use.

| Component | Version | Status | Support | Description |
|-----------|---------|--------|---------|-------------|
| **Multi-modal Memory** | - | ⚠️ **Experimental** | Community | Images, audio, video support (planned) |
| **Plugin System** | - | ⚠️ **Experimental** | Community | Custom extensions (planned) |
| **Replay Tool** | - | ⚠️ **Experimental** | Community | Agent session replay (concept)

---

## Version History

### 2.0.0-enterprise (Current - In Development)

**Release Goal:** Enterprise-grade production readiness

**Breaking Changes:**
- Refactored Repository/DAO pattern (DI-based architecture)
- New Reflection API (`project` instead of `project_id`)
- GraphExtractionService requires `graph_repo` parameter
- HybridSearchService requires `graph_repo` + `pool` parameters
- Deprecated old MCP endpoints

**New Features:**
- ✅ **Enterprise Security (Phase 1-5 Complete)**
  - ✅ Unified authentication (API Key + JWT)
  - ✅ Role-Based Access Control (RBAC) with 5-tier hierarchy
  - ✅ Tenant isolation at query level
  - ✅ Comprehensive audit logging
  - ✅ Memory decay scheduler with temporal logic
  - ✅ Database-backed RBAC with migrations
- ✅ GraphRAG integration (knowledge graph + vector search)
- ✅ Hierarchical Reflection Engine with clustering
- ✅ Multi-tenancy with full isolation
- ✅ Structured logging (structlog + JSON)
- ✅ Comprehensive API documentation (v2.0)
- ✅ Cost Controller with budget enforcement
- ✅ Governance dashboard with RBAC protection
- 🟡 OpenTelemetry distributed tracing
- 🟡 Rate limiting (SlowAPI/FastAPI-Limiter)
- 🟡 Event Engine with retry/cooldown
- 🟡 Helm Chart for Kubernetes

**Test Coverage:**
- Global: 32% → Target: 75%+
- Core modules: Target: 80%+
- Tests: 264 collected, 200 passing, 21 failing (work in progress)

**Infrastructure:**
- CI/CD: Matrix tests (Python 3.10, 3.11, 3.12)
- Docker: Multi-service composition
- Database: PostgreSQL 16+ with pgvector
- Vector Store: Qdrant
- Cache: Redis

### 1.0.0-beta (Previous)

**Release Date:** November 2024
**Status:** Deprecated (migrating to 2.0.0-enterprise)

**Features:**
- Basic memory storage (episodic, working, semantic, long-term)
- Vector similarity search
- Simple reflection generation
- Basic multi-tenancy
- MCP integration

**Known Limitations:**
- No GraphRAG
- No hierarchical reflections
- Limited cost control
- No distributed tracing
- Test coverage ~58%

---

## Compatibility Matrix

### Python Versions

| Python | 2.0.0-enterprise | 1.0.0-beta |
|--------|------------------|------------|
| 3.10   | ✅ Supported     | ✅ Supported |
| 3.11   | ✅ Supported     | ✅ Supported |
| 3.12   | ✅ Supported     | ⚠️ Experimental |
| 3.13   | ⚠️ Experimental   | ❌ Not supported |

### Database Versions

| Database | 2.0.0-enterprise | 1.0.0-beta |
|----------|------------------|------------|
| PostgreSQL 14 | ⚠️ Minimum | ✅ Supported |
| PostgreSQL 15 | ✅ Supported | ✅ Supported |
| PostgreSQL 16 | ✅ Recommended | ✅ Supported |
| PostgreSQL 17 | ⚠️ Experimental | ❌ Not tested |

**Requirements:**
- pgvector extension >= 0.5.0
- JSONB support
- Concurrent index support

### Vector Store Versions

| Store | 2.0.0-enterprise | 1.0.0-beta |
|-------|------------------|------------|
| Qdrant 1.7+ | ✅ Supported | ✅ Supported |
| Qdrant 1.8+ | ✅ Recommended | ✅ Supported |
| Qdrant 1.9+ | ⚠️ Experimental | ⚠️ Experimental |

### LLM Provider Compatibility

| Provider | 2.0.0-enterprise | Models Tested |
|----------|------------------|---------------|
| OpenAI | ✅ Supported | gpt-4o, gpt-4o-mini, gpt-3.5-turbo |
| Anthropic | ✅ Supported | claude-3-5-sonnet, claude-3-opus |
| Google | ⚠️ Experimental | gemini-1.5-pro |
| Ollama (local) | ✅ Supported | llama3, mistral, phi |

---

## API Version

s

### v1 API (Current)

**Base URL:** `/v1`
**Status:** Stable
**Authentication:** Bearer token (tenant_id)

**Key Endpoints:**
- `/v1/memories/*` - Memory management
- `/v1/search/hybrid` - Hybrid vector + graph search
- `/v1/graph/*` - Knowledge graph operations
- `/v1/reflections/*` - Reflection engine
- `/v1/governance/*` - Cost and governance (coming soon)
- `/v1/health` - Health and metrics

### v2 API (Planned)

**Base URL:** `/v2`
**Status:** Not yet implemented
**Target:** v2.1.0

**Planned Improvements:**
- Streaming responses
- Bulk operations
- Improved error messages
- Pagination standardization

---

## Migration Guide (1.0.0-beta → 2.0.0-enterprise)

### Code Changes Required

#### 1. GraphExtractionService Initialization

**Before (1.0.0-beta):**
```python
service = GraphExtractionService(db_pool)
```

**After (2.0.0-enterprise):**
```python
from apps.memory_api.repositories.memory_repository import MemoryRepository
from apps.memory_api.repositories.graph_repository import GraphRepository

memory_repo = MemoryRepository(db_pool)
graph_repo = GraphRepository(db_pool)
service = GraphExtractionService(memory_repo, graph_repo)
```

#### 2. HybridSearchService Initialization

**Before (1.0.0-beta):**
```python
service = HybridSearchService(db_pool)
```

**After (2.0.0-enterprise):**
```python
from apps.memory_api.repositories.graph_repository import GraphRepository

graph_repo = GraphRepository(db_pool)
service = HybridSearchService(graph_repo, db_pool)
```

#### 3. GenerateReflectionRequest

**Before (1.0.0-beta):**
```python
request = GenerateReflectionRequest(
    tenant_id="...",
    project_id="...",  # old field name
    memory_ids=[...],
    created_by="..."
)
```

**After (2.0.0-enterprise):**
```python
request = GenerateReflectionRequest(
    tenant_id="...",
    project="...",  # new field name
    reflection_type=ReflectionType.INSIGHT,
    enable_clustering=True
)
```

### Database Migrations

All migrations are handled automatically via Alembic:

```bash
# Run migrations
alembic upgrade head

# Check current version
alembic current

# Rollback (if needed)
alembic downgrade -1
```

**Note:** Migration from 1.0.0-beta to 2.0.0-enterprise includes:
- New `cost_logs` table
- New `reflection_relationships` table
- New indexes for graph operations
- Updated JSONB structures

---

## Release Schedule

### 2.0.0-enterprise Timeline

| Phase | Target Date | Status |
|-------|-------------|--------|
| **Alpha** | Week 1-2 | 🟡 In Progress |
| - Core refactoring | | ✅ Complete |
| - Test fixes (80%+) | | 🟡 70% complete |
| - Documentation cleanup | | 🟡 In progress |
| **Beta** | Week 3-4 | ⚪ Not started |
| - Cost Controller | | ⚪ Not started |
| - Governance API | | ⚪ Not started |
| - Event Engine | | ⚪ Not started |
| - Dashboard MVP | | ⚪ Not started |
| **RC** | Week 5-6 | ⚪ Not started |
| - OpenTelemetry | | ⚪ Not started |
| - Rate Limiting | | ⚪ Not started |
| - Helm Chart | | ⚪ Not started |
| - Full test coverage | | ⚪ Not started |
| **GA** | Week 7 | ⚪ Not started |
| - Final docs | | ⚪ Not started |
| - Release notes | | ⚪ Not started |
| - Security audit | | ⚪ Not started |

---

## Deprecation Policy

### Deprecated in 2.0.0-enterprise

The following APIs/features are deprecated and will be removed in v3.0.0:

- ❌ Old MCP endpoints in `/memory/add`, `/memory/store`
- ❌ `datetime.utcnow()` (replace with `datetime.now(datetime.UTC)`)
- ❌ Direct pool passing to services (use Repository pattern)
- ❌ `project_id` field (use `project` instead)

### Migration Timeline

- **2.0.0-enterprise:** Deprecated features still work but show warnings
- **2.1.0:** Deprecated features disabled by default (can be enabled via config)
- **3.0.0:** Deprecated features completely removed

---

## Support

| Version | Status | Support Until | Security Fixes |
|---------|--------|---------------|----------------|
| 2.0.0-enterprise | Current | TBD | ✅ Yes |
| 1.0.0-beta | Deprecated | 3 months after 2.0.0 GA | ⚠️ Critical only |
| < 1.0.0 | Unsupported | - | ❌ No |

---

## Version Detection

### Check Version at Runtime

```python
# Memory API
from apps.memory_api.main import app
print(app.version)  # "2.0.0-enterprise"

# ML Service
from apps.ml_service import __version__
print(__version__)  # "2.0.0"

# SDK
from rae_memory_sdk import __version__
print(__version__)  # "0.1.0"
```

### Check Version via API

```bash
curl https://your-rae-instance/v1/health
```

Response:
```json
{
  "status": "healthy",
  "version": "2.0.0-enterprise",
  "components": {
    "api": "2.0.0-enterprise",
    "ml_service": "2.0.0",
    "database": "PostgreSQL 16.1"
  }
}
```

---

## References

- **Semantic Versioning:** https://semver.org/
- **CHANGELOG:** `CHANGELOG.md` (to be created)
- **Release Notes:** `docs/RELEASE_NOTES.md` (to be created)
- **Migration Guide:** This document (section above)
- **Testing Status:** `docs/TESTING_STATUS.md`

---

**Last Updated:** 2025-11-22
**Document Version:** 1.0
**Maintained by:** RAE Core Team
