# RAE Phase 1 Completion Plan

**Status:** 85% Complete
**Target:** 100% Phase 1 Completion
**Timeline:** 2-3 weeks
**Priority:** CRITICAL

---

## Executive Summary

Phase 1 rae-core foundation is 85% complete with solid architecture. **The current system (apps/memory_api) is operational** - Phase 1 is an architectural modernization, not a restoration of functionality.

**What Phase 1 Completion Enables:**
- ✅ Clean separation: rae-core (pure Python) vs rae-server (FastAPI)
- ✅ Standalone rae-core package for PyPI publication
- ✅ Foundation for RAE-Lite (Phase 3)
- ✅ Foundation for RAE-Sync (Phase 5)
- ✅ Testable, maintainable, extensible architecture

---

## Current Status Assessment

### ✅ Completed Components (85%)

| Component | Status | Lines | Notes |
|-----------|--------|-------|-------|
| Interfaces (7 ABCs) | ✅ 100% | ~500 | Storage, Vector, Graph, LLM, Embedding, Cache, Sync |
| Models (9 Pydantic) | ✅ 100% | ~800 | Memory, Search, Reflection, Context, Scoring, Graph, Sync |
| Memory Layers (4) | ✅ 100% | ~1200 | Sensory, Working, LongTerm, Reflective |
| Math Layers (3) | ✅ 100% | ~900 | Structure, Dynamics, Policy + Controller |
| Search Engine | ✅ 100% | ~800 | Hybrid with 4 strategies + RRF |
| Reflection Engine | ✅ 100% | ~1200 | Actor-Evaluator-Reflector pattern |
| LLM Orchestration | ✅ 100% | ~700 | Multi-provider + Fallback |
| Sync Protocol | ✅ 100% | ~1000 | Push/Pull/Diff/Merge/Encryption |
| RAEEngine | ✅ 100% | ~340 | Main orchestrator |
| Config System | ✅ 100% | ~400 | Pydantic-settings |
| Adapters: Postgres | ✅ 100% | ~546 | Full implementation |
| Adapters: Qdrant | ✅ 100% | ~287 | Vector store |
| Adapters: Redis | ✅ 100% | ~213 | Cache |

**Total Implemented:** ~9,369 lines of production code

### ⚠️ Gaps Blocking Phase 1 (15%)

| Component | Priority | Effort | Impact |
|-----------|----------|--------|--------|
| **1. ContextBuilder** | CRITICAL | 1 day | Needed for RAEEngine.search() |
| **2. SQLite Adapters** | CRITICAL | 3-4 days | Needed for RAE-Lite (Phase 3) |
| **3. In-Memory Adapters** | HIGH | 2 days | Needed for isolated testing |
| **4. Unit Tests Suite** | CRITICAL | 5-7 days | Currently ~5% coverage |

---

## Detailed Completion Plan

### Task 1: ContextBuilder (1 day)

**File:** `rae-core/rae_core/context/builder.py`

**Why Critical:**
- RAEEngine.search_memories() returns raw results
- No context assembly for LLM consumption
- Blocking: Cannot use search results in LLM prompts

**Implementation:**

```python
"""Context builder for assembling LLM-ready context from memories."""

from typing import List, Optional
from rae_core.models.memory import MemoryItem
from rae_core.models.context import WorkingContext, ContextWindow


class ContextBuilder:
    """Assembles working context from search results and memory history."""

    def __init__(
        self,
        window: ContextWindow,
        max_tokens: int = 4000,
    ):
        """Initialize context builder.

        Args:
            window: Context window for token management
            max_tokens: Maximum tokens for assembled context
        """
        self.window = window
        self.max_tokens = max_tokens

    async def build(
        self,
        query: str,
        memories: List[MemoryItem],
        system_prompt: Optional[str] = None,
    ) -> WorkingContext:
        """Build working context from search results.

        Args:
            query: User query
            memories: Retrieved memories
            system_prompt: Optional system instructions

        Returns:
            Assembled working context ready for LLM
        """
        # Implementation: assemble memories into coherent context
        # with token counting, relevance sorting, etc.
        pass

    def format_memory(self, memory: MemoryItem) -> str:
        """Format single memory for context inclusion."""
        pass

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (simple heuristic: ~4 chars/token)."""
        return len(text) // 4
```

**Acceptance Criteria:**
- [ ] `build()` assembles memories into LLM-ready string
- [ ] Token limit respected (max_tokens)
- [ ] Memories sorted by relevance/importance
- [ ] System prompt included if provided
- [ ] Unit tests: 5 test cases

**Estimated LOC:** ~150 lines + 100 test lines

---

### Task 2: SQLite Adapters (3-4 days)

**Files:**
- `rae-core/rae_core/adapters/sqlite/storage.py`
- `rae-core/rae_core/adapters/sqlite/vector.py`
- `rae-core/rae_core/adapters/sqlite/graph.py`
- `rae-core/rae_core/adapters/sqlite/__init__.py`

**Why Critical:**
- RAE-Lite (Phase 3) requires SQLite backend
- Offline-first architecture needs local storage
- Blocking: Cannot start RAE-Lite without SQLite

**Implementation:**

#### 2.1 SQLiteMemoryStorage (~400 lines)

```python
"""SQLite implementation of IMemoryStorage."""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.memory import MemoryItem


class SQLiteMemoryStorage(IMemoryStorage):
    """SQLite-based memory storage.

    Schema:
        memories (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            layer TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            embedding BLOB,
            tags TEXT,  -- JSON array
            metadata TEXT,  -- JSON object
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0
        )
    """

    def __init__(self, db_path: str):
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if not exist."""
        # Implementation: CREATE TABLE IF NOT EXISTS
        pass

    async def store_memory(
        self,
        tenant_id: str,
        agent_id: str,
        content: str,
        memory_type: str = "sensory",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> UUID:
        """Store memory in SQLite."""
        # Implementation: INSERT INTO memories
        pass

    async def get_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve memory by ID."""
        # Implementation: SELECT * FROM memories WHERE id = ?
        pass

    # ... other IMemoryStorage methods
```

#### 2.2 SQLiteVectorStore (~300 lines)

```python
"""SQLite vector store with fallback to exact match."""

from rae_core.interfaces.vector import IVectorStore


class SQLiteVectorStore(IVectorStore):
    """SQLite-based vector store.

    Uses sqlite-vss extension if available, fallback to BM25.

    Schema:
        vectors (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            embedding BLOB NOT NULL,  -- Float32 array
            dimension INTEGER NOT NULL
        )
    """

    def __init__(self, db_path: str, use_vss: bool = True):
        """Initialize vector store.

        Args:
            db_path: Path to SQLite database
            use_vss: Use sqlite-vss if available (fallback: BM25)
        """
        self.db_path = db_path
        self.use_vss = use_vss
        self._check_vss_support()

    def _check_vss_support(self):
        """Check if sqlite-vss extension is available."""
        # Try to load sqlite-vss, fallback to BM25
        pass

    async def search(
        self,
        query_vector: List[float],
        tenant_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search vectors (VSS or BM25 fallback)."""
        if self.use_vss:
            return await self._search_vss(query_vector, tenant_id, top_k, filters)
        else:
            return await self._search_bm25(query_vector, tenant_id, top_k, filters)

    # ... other IVectorStore methods
```

#### 2.3 SQLiteGraphStore (~300 lines)

```python
"""SQLite graph store for memory relationships."""

from rae_core.interfaces.graph import IGraphStore


class SQLiteGraphStore(IGraphStore):
    """SQLite-based graph storage.

    Schema:
        nodes (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            memory_id TEXT NOT NULL,
            node_type TEXT,
            properties TEXT  -- JSON
        )

        edges (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            properties TEXT  -- JSON
        )
    """

    async def add_node(self, node: GraphNode) -> UUID:
        """Add graph node."""
        pass

    async def add_edge(self, edge: GraphEdge) -> UUID:
        """Add graph edge."""
        pass

    async def traverse(
        self,
        start_node_id: UUID,
        max_depth: int = 3,
        edge_types: Optional[List[str]] = None,
    ) -> List[GraphNode]:
        """Traverse graph from starting node."""
        # Implementation: Recursive CTE for graph traversal
        pass

    # ... other IGraphStore methods
```

**Acceptance Criteria:**
- [ ] All 3 adapters implement their interfaces
- [ ] SQLite schema created on init
- [ ] CRUD operations work correctly
- [ ] Vector search with VSS fallback
- [ ] Graph traversal with max depth
- [ ] Thread-safe (connection pooling)
- [ ] Unit tests: 15+ test cases per adapter

**Estimated LOC:** ~1000 lines + 500 test lines

---

### Task 3: In-Memory Adapters (2 days)

**Files:**
- `rae-core/rae_core/adapters/memory/storage.py`
- `rae-core/rae_core/adapters/memory/vector.py`
- `rae-core/rae_core/adapters/memory/cache.py`
- `rae-core/rae_core/adapters/memory/__init__.py`

**Why Critical:**
- Unit tests need isolated environment
- No external dependencies for testing
- Fast test execution

**Implementation:**

```python
"""In-memory storage for testing."""

from typing import Dict, List, Optional
from uuid import UUID
from rae_core.interfaces.storage import IMemoryStorage


class InMemoryStorage(IMemoryStorage):
    """In-memory storage using Python dicts.

    For testing only - data lost on restart.
    """

    def __init__(self):
        self._memories: Dict[str, Dict] = {}
        self._by_tenant: Dict[str, List[str]] = {}

    async def store_memory(self, **kwargs) -> UUID:
        """Store in memory dict."""
        memory_id = UUID()
        self._memories[str(memory_id)] = {
            "id": memory_id,
            **kwargs,
        }
        return memory_id

    async def get_memory(self, memory_id: UUID, tenant_id: str) -> Optional[Dict]:
        """Get from memory dict."""
        return self._memories.get(str(memory_id))

    # ... other methods
```

**Acceptance Criteria:**
- [ ] All operations in-memory (no DB)
- [ ] Fast (<1ms per operation)
- [ ] Thread-safe
- [ ] Clear() method for test cleanup
- [ ] Unit tests: 10+ test cases

**Estimated LOC:** ~300 lines + 200 test lines

---

### Task 4: Unit Tests Suite (5-7 days)

**Directory:** `rae-core/tests/`

**Why Critical:**
- Current coverage: ~5% (rae-core)
- Cannot publish to PyPI without tests
- Risk: Undetected bugs in production

**Test Structure:**

```
rae-core/tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── test_models/
│   ├── test_memory.py             # MemoryItem tests
│   ├── test_search.py             # SearchQuery tests
│   ├── test_reflection.py         # Reflection tests
│   └── test_context.py            # Context tests
├── test_layers/
│   ├── test_sensory.py            # SensoryLayer tests
│   ├── test_working.py            # WorkingLayer tests
│   ├── test_longterm.py           # LongTermLayer tests
│   └── test_reflective.py         # ReflectiveLayer tests
├── test_math/
│   ├── test_structure.py          # Structure layer tests
│   ├── test_dynamics.py           # Dynamics layer tests
│   ├── test_policy.py             # Policy layer tests
│   └── test_controller.py         # Controller tests
├── test_search/
│   ├── test_engine.py             # HybridSearchEngine tests
│   ├── test_vector_strategy.py
│   ├── test_sparse_strategy.py
│   ├── test_graph_strategy.py
│   └── test_fulltext_strategy.py
├── test_reflection/
│   ├── test_engine.py             # ReflectionEngine tests
│   ├── test_actor.py              # Actor tests
│   ├── test_evaluator.py          # Evaluator tests
│   └── test_reflector.py          # Reflector tests
├── test_llm/
│   ├── test_orchestrator.py       # LLMOrchestrator tests
│   ├── test_strategies.py         # Strategy tests
│   └── test_fallback.py           # Fallback tests
├── test_sync/
│   ├── test_protocol.py           # SyncProtocol tests
│   ├── test_diff.py               # Diff calculation tests
│   ├── test_merge.py              # Merge tests
│   └── test_encryption.py         # Encryption tests
├── test_adapters/
│   ├── test_postgres.py           # PostgreSQL tests
│   ├── test_qdrant.py             # Qdrant tests
│   ├── test_redis.py              # Redis tests
│   ├── test_sqlite.py             # SQLite tests
│   └── test_memory.py             # In-memory tests
├── test_integration/
│   ├── test_engine.py             # RAEEngine integration
│   ├── test_end_to_end.py         # Full flow tests
│   └── test_performance.py        # Performance benchmarks
└── test_config/
    └── test_settings.py           # Settings tests
```

**Coverage Goals:**

| Module | Target | Priority |
|--------|--------|----------|
| models/ | 95% | HIGH |
| interfaces/ | 90% | MEDIUM |
| layers/ | 90% | HIGH |
| math/ | 85% | HIGH |
| search/ | 90% | HIGH |
| reflection/ | 85% | HIGH |
| llm/ | 80% | MEDIUM |
| sync/ | 85% | HIGH |
| adapters/ | 90% | HIGH |
| context/ | 90% | HIGH |
| config/ | 85% | MEDIUM |
| engine.py | 90% | CRITICAL |

**Overall Target:** 80%+ code coverage

**Test Categories:**

1. **Unit Tests** (~400 tests)
   - Test each class/function in isolation
   - Mock dependencies
   - Fast execution (<10s)

2. **Integration Tests** (~100 tests)
   - Test component interactions
   - Real adapters (SQLite/in-memory)
   - Medium speed (<30s)

3. **Performance Tests** (~20 tests)
   - Benchmark critical paths
   - Memory usage checks
   - Latency measurements

4. **Contract Tests** (~50 tests)
   - Verify interface compliance
   - Adapter implementations
   - Ensure substitutability

**Acceptance Criteria:**
- [ ] 80%+ code coverage (overall)
- [ ] 90%+ for critical modules
- [ ] All tests pass (pytest)
- [ ] Fast execution (<60s for unit tests)
- [ ] CI/CD integration
- [ ] Documentation for test writing

**Estimated LOC:** ~5000 lines of test code

---

## Implementation Schedule

### Week 1: Critical Components

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| Day 1 | ContextBuilder implementation | Dev | Not Started |
| Day 2 | ContextBuilder tests | Dev | Not Started |
| Day 3 | In-Memory adapters (Storage) | Dev | Not Started |
| Day 4 | In-Memory adapters (Vector, Cache) | Dev | Not Started |
| Day 5 | In-Memory adapters tests | Dev | Not Started |

**Deliverable:** ContextBuilder + In-Memory adapters working

### Week 2: SQLite Adapters

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| Day 6 | SQLiteMemoryStorage | Dev | Not Started |
| Day 7 | SQLiteVectorStore | Dev | Not Started |
| Day 8 | SQLiteGraphStore | Dev | Not Started |
| Day 9 | SQLite adapters tests | Dev | Not Started |
| Day 10 | SQLite integration tests | Dev | Not Started |

**Deliverable:** SQLite adapters fully functional

### Week 3: Unit Tests Suite

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| Day 11-12 | Models + Layers tests | Dev | Not Started |
| Day 13-14 | Math + Search tests | Dev | Not Started |
| Day 15-16 | Reflection + LLM tests | Dev | Not Started |
| Day 17-18 | Sync + Adapters tests | Dev | Not Started |
| Day 19-20 | Integration + Performance tests | Dev | Not Started |
| Day 21 | Coverage review & fixes | Dev | Not Started |

**Deliverable:** 80%+ code coverage achieved

---

## Success Criteria

### Phase 1 Complete When:

- [x] All 13 modules implemented (11/13 ✅)
- [ ] ContextBuilder working
- [ ] SQLite adapters functional
- [ ] In-Memory adapters for tests
- [ ] 80%+ test coverage
- [ ] All tests passing
- [ ] Documentation complete
- [ ] PyPI package published

### What Phase 1 Enables:

1. **Standalone Package**
   - `pip install rae-core`
   - Use rae-core without rae-server
   - Pure Python, no FastAPI dependency

2. **RAE-Lite Foundation**
   - SQLite storage ready
   - Offline-first architecture
   - Desktop app can start (Phase 3)

3. **Testing Infrastructure**
   - In-memory adapters for fast tests
   - Comprehensive test suite
   - CI/CD ready

4. **Clean Architecture**
   - Separation of concerns
   - Dependency injection
   - Testable, maintainable

5. **Migration Path**
   - apps/memory_api can gradually adopt rae-core
   - MIGRATION_PLAN.md documents transition
   - Backward compatible

---

## Operational Status

### Current System (apps/memory_api)

**Status:** ✅ OPERATIONAL
- 860/860 tests passing
- 72.31% code coverage
- Production-ready
- Uses legacy services/

**What Works:**
- Memory CRUD operations
- Hybrid search
- Reflection pipeline
- LLM integration
- PostgreSQL + Qdrant + Redis
- API endpoints (v1)

### After Phase 1 Completion

**Status:** ✅ OPERATIONAL + ✅ MODERNIZED
- Same functionality
- Clean architecture
- Testable components
- Ready for RAE-Lite
- Ready for PyPI

**What Changes:**
- apps/memory_api can use rae-core
- Gradual migration (not big bang)
- Both systems coexist during transition
- Zero downtime migration

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SQLite adapters complex | MEDIUM | HIGH | Use sqlite-vss, fallback to BM25 |
| Test coverage time | HIGH | MEDIUM | Prioritize critical paths first |
| Breaking changes | LOW | HIGH | Interface stability, versioning |
| Performance regression | LOW | MEDIUM | Benchmark before/after |
| Documentation debt | MEDIUM | LOW | Write docs inline with code |

---

## Post-Phase 1 Next Steps

### Phase 2: RAE-Server Refactoring (Weeks 5-6)
- Migrate apps/memory_api to use rae-core
- Deprecate old services/
- V2 API endpoints

### Phase 3: RAE-Lite (Weeks 7-10)
- Desktop app with SQLite
- Tray icon, local HTTP server
- Offline-first UX

### Phase 4: Browser Extension (Weeks 11-12, Optional)
- ChatGPT/Claude/Gemini capture
- Local storage via RAE-Lite

### Phase 5: RAE-Sync (Weeks 13-14)
- Client implementation
- E2E encryption
- Conflict resolution UI

### Phase 6: RAE-Mobile (Q2-Q4 2025)
- iOS/Android apps
- React Native or Flutter

---

## Resources & Contacts

**Technical Lead:** Grzegorz Leśniowski
**Repository:** github.com/dreamsoft-pro/RAE-agentic-memory
**Documentation:** /docs/RAE_REFACTORING_FIX_PLAN.md
**Migration Plan:** /apps/memory_api/services/MIGRATION_PLAN.md

**Key Files:**
- rae-core implementation: `/rae-core/rae_core/`
- Tests: `/rae-core/tests/` (to be created)
- Configuration: `/rae-core/pyproject.toml`
- Architecture plan: `/docs/RAE_Architecture_Refactoring_Plan_v2.md`

---

**Document Version:** 1.0
**Last Updated:** 2025-12-10
**Status:** Phase 1 at 85% - 2-3 weeks to completion
