# 🎯 RAE Ecosystem - Comprehensive Completion Plan

**Version**: 1.0
**Date**: 2025-12-11
**Status**: 📋 READY TO EXECUTE
**Based on**: RAE_Architecture_Refactoring_Plan_v2.md + Gemini's work analysis

---

## 🌟 VISION - RAE Ecosystem (4 Products)

```
         ┌─────────────────┐
         │    RAE-core     │  ← Universal engine (Pure Python)
         │   (Library)     │
         └────────┬────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │           │
      ▼           ▼           ▼           ▼
  ┌───────┐   ┌───────┐   ┌────────┐  ┌────────┐
  │Server │   │ Lite  │   │ Mobile │  │ Cloud  │
  │Docker │   │ .exe  │   │iOS/And │  │ K8s    │
  │PgSQL  │   │SQLite │   │SQLite  │  │PgSQL   │
  └───────┘   └───────┘   └────────┘  └────────┘
```

**Products**:
1. **RAE-core** - Pure Python library (storage agnostic)
2. **RAE-Server** - Enterprise (PostgreSQL, Qdrant, Redis, Docker/K8s)
3. **RAE-Lite** - Desktop (.exe/.app, SQLite, zero dependencies)
4. **RAE-Mobile** - Future (iOS/Android, SQLite, on-device LLM)

**Additional**:
- **RAE-Sync** - P2P synchronization protocol (E2E encrypted, CRDT)
- **Browser Extension** - ✅ Already implemented (ChatGPT, Claude, Gemini)

---

## 📊 CURRENT STATUS

### ✅ What Gemini Completed (HUGE work!):

1. **Extended IMemoryStorage interface** with 6 new methods:
   - `delete_memories_with_metadata_filter()`
   - `delete_memories_below_importance()`
   - `search_memories()`
   - `delete_expired_memories()`
   - `update_memory_access()`
   - `update_memory_expiration()`

2. **Implemented ALL in production adapters**:
   - ✅ PostgreSQLStorage (100% complete)
   - ✅ QdrantVectorStore (100% complete)
   - ✅ RedisCache (100% complete)

3. **Fixed datetime deprecation warnings**:
   - ✅ Replaced `datetime.utcnow()` → `datetime.now(timezone.utc)` in **197 places**!

4. **Wrote comprehensive unit tests**:
   - ✅ `test_postgres.py` (100+ lines)
   - ✅ `test_qdrant.py` (100+ lines)
   - ✅ `test_redis.py` (100+ lines)
   - ✅ `test_engine.py`
   - ✅ All layers (sensory, working, longterm, reflective)
   - ✅ All math modules (metrics, dynamics, policy, structure)
   - ✅ All models (memory, reflection)
   - ✅ Reflection engine & LLM orchestrator
   - ✅ Search engine

### 🔴 CRITICAL ISSUES - Must Fix Now (Blocking RAE-Lite):

1. **InMemoryCache bug** - `UnboundLocalError` in `set_if_not_exists()`
2. **InMemoryStorage incomplete** - Missing 6 new interface methods
3. **SQLiteStorage incomplete** - Missing 6 new interface methods

**Impact**: RAE-Lite broken, local-first scenarios don't work

---

## 🚀 EXECUTION PLAN

### PHASE 0: Cleanup & Organization (1-2 hours)

**Goal**: Fix structural issues, organize codebase

**Tasks**:

1. **Resolve /rae-core vs /rae_core duplication** (CRITICAL!)
   ```bash
   # Decision needed:
   # Option A: /rae-core is active, delete /rae_core
   # Option B: Merge differences, keep /rae-core
   # Option C: /rae_core is backup, rename to /rae_core.backup
   ```

   **Current state**:
   - `/rae-core/` - 8 subdirs, newer, more files (ACTIVE)
   - `/rae_core/` - 4 subdirs, older, different files (STALE?)
   - Files differ: postgres.py, qdrant.py, redis.py, sqlite/* different

   **Recommendation**: Option B - Carefully merge unique code from /rae_core into /rae-core, then delete /rae_core

2. **Commit Gemini's work**:
   ```bash
   # Current uncommitted changes (20 files):
   git add rae-core/rae_core/interfaces/storage.py
   git add rae-core/rae_core/adapters/postgres.py
   git add rae-core/rae_core/adapters/redis.py
   git add rae-core/rae_core/adapters/qdrant.py
   # ... all 20 files
   git add rae-core/tests/
   git add docs/RAE_EFFECTIVENESS_LOG.md
   git add docs/RAE_CORE_TEST_COVERAGE_PLAN.md

   git commit -m "feat(rae-core): extend storage interface and fix adapters

   Gemini completed:
   - Extended IMemoryStorage with 6 new methods
   - Implemented all in PostgreSQL, Qdrant, Redis adapters
   - Fixed 197 datetime.utcnow() deprecation warnings
   - Added comprehensive unit tests for all adapters

   Remaining work: InMemory and SQLite adapters (next commit)"
   ```

3. **Update documentation**:
   - Mark this plan as active roadmap
   - Update STATUS.md with current state

**Deliverable**: Clean repo structure, Gemini's work committed

---

### PHASE 1: Fix Critical Bugs (30 minutes)

**Goal**: Make reference adapters work again

**Tasks**:

#### Task 1.1: Fix InMemoryCache.set_if_not_exists() (5 minutes)

**File**: `rae-core/rae_core/adapters/memory/cache.py`

**Bug** (line 206):
```python
async def set_if_not_exists(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    async with self._lock:
        if key in self._cache:
            if not expiry or datetime.now(timezone.utc) <= expiry:  # ← BUG: expiry undefined!
                return False
```

**Fix**:
```python
async def set_if_not_exists(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    async with self._lock:
        if key in self._cache:
            value, expiry = self._cache[key]  # ← FIX: Unpack tuple first!
            if not expiry or datetime.now(timezone.utc) <= expiry:
                return False
```

**Test**:
```bash
pytest rae-core/tests/unit/adapters/memory/test_cache.py::test_set_if_not_exists -v
```

#### Task 1.2: Implement missing methods in InMemoryStorage (1 hour)

**File**: `rae-core/rae_core/adapters/memory/storage.py`

**Missing methods** (6):

```python
async def delete_memories_with_metadata_filter(
    self, tenant_id: str, agent_id: str, layer: str, metadata_filter: Dict[str, Any]
) -> int:
    """Delete memories matching metadata filter."""
    async with self._lock:
        matching_ids = []
        for memory_id, memory in self._memories.items():
            if (
                memory["tenant_id"] == tenant_id
                and memory["agent_id"] == agent_id
                and memory["layer"] == layer
            ):
                # Check if metadata matches filter
                if self._matches_metadata_filter(memory.get("metadata", {}), metadata_filter):
                    matching_ids.append(memory_id)

        for memory_id in matching_ids:
            await self._delete_memory_internal(memory_id)

        return len(matching_ids)

async def delete_memories_below_importance(
    self, tenant_id: str, agent_id: str, layer: str, importance_threshold: float
) -> int:
    """Delete memories below importance threshold."""
    async with self._lock:
        matching_ids = [
            memory_id
            for memory_id, memory in self._memories.items()
            if (
                memory["tenant_id"] == tenant_id
                and memory["agent_id"] == agent_id
                and memory["layer"] == layer
                and memory.get("importance", 0) < importance_threshold
            )
        ]

        for memory_id in matching_ids:
            await self._delete_memory_internal(memory_id)

        return len(matching_ids)

async def search_memories(
    self,
    query: str,
    tenant_id: str,
    agent_id: str,
    layer: str,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search memories using simple substring matching."""
    async with self._lock:
        results = []
        query_lower = query.lower()

        for memory in self._memories.values():
            if (
                memory["tenant_id"] == tenant_id
                and memory["agent_id"] == agent_id
                and memory["layer"] == layer
            ):
                # Simple substring search in content
                content_lower = memory["content"].lower()
                if query_lower in content_lower:
                    # Calculate simple score based on position
                    score = 1.0 - (content_lower.index(query_lower) / len(content_lower))
                    results.append({"memory": memory.copy(), "score": score})

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:limit]

async def delete_expired_memories(
    self, tenant_id: str, agent_id: str, layer: str
) -> int:
    """Delete expired memories."""
    async with self._lock:
        now = datetime.now(timezone.utc)
        matching_ids = [
            memory_id
            for memory_id, memory in self._memories.items()
            if (
                memory["tenant_id"] == tenant_id
                and memory["agent_id"] == agent_id
                and memory["layer"] == layer
                and memory.get("expires_at")
                and memory["expires_at"] < now
            )
        ]

        for memory_id in matching_ids:
            await self._delete_memory_internal(memory_id)

        return len(matching_ids)

async def update_memory_access(
    self, memory_id: UUID, tenant_id: str
) -> bool:
    """Update last access time and increment usage count."""
    async with self._lock:
        memory = self._memories.get(memory_id)

        if not memory or memory["tenant_id"] != tenant_id:
            return False

        memory["last_accessed_at"] = datetime.now(timezone.utc)
        memory["access_count"] = memory.get("access_count", 0) + 1

        return True

async def update_memory_expiration(
    self, memory_id: UUID, tenant_id: str, expires_at: Any
) -> bool:
    """Update memory expiration time."""
    async with self._lock:
        memory = self._memories.get(memory_id)

        if not memory or memory["tenant_id"] != tenant_id:
            return False

        memory["expires_at"] = expires_at
        memory["modified_at"] = datetime.now(timezone.utc)

        return True

def _matches_metadata_filter(self, metadata: Dict[str, Any], filter: Dict[str, Any]) -> bool:
    """Check if metadata matches filter criteria."""
    for key, value in filter.items():
        if key not in metadata or metadata[key] != value:
            return False
    return True

async def _delete_memory_internal(self, memory_id: UUID):
    """Internal delete helper (assumes lock is held)."""
    memory = self._memories.get(memory_id)
    if not memory:
        return

    # Remove from main storage
    del self._memories[memory_id]

    # Remove from indexes
    tenant_id = memory["tenant_id"]
    agent_id = memory["agent_id"]
    layer = memory["layer"]

    self._by_tenant[tenant_id].discard(memory_id)
    self._by_agent[(tenant_id, agent_id)].discard(memory_id)
    self._by_layer[(tenant_id, layer)].discard(memory_id)

    for tag in memory.get("tags", []):
        self._by_tags[(tenant_id, tag)].discard(memory_id)
```

**Test**:
```bash
pytest rae-core/tests/unit/adapters/memory/test_storage.py -v
```

#### Task 1.3: Implement missing methods in SQLiteStorage (1.5 hours)

**File**: `rae-core/rae_core/adapters/sqlite/storage.py`

**Missing methods** (6) - Similar to InMemory but with SQL:

```python
async def delete_memories_with_metadata_filter(
    self, tenant_id: str, agent_id: str, layer: str, metadata_filter: Dict[str, Any]
) -> int:
    """Delete memories matching metadata filter."""
    await self.initialize()

    # Build metadata filter clause
    filter_json = json.dumps(metadata_filter)

    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            """
            DELETE FROM memories
            WHERE tenant_id = ? AND agent_id = ? AND layer = ?
            AND json_extract(metadata, '$') LIKE ?
            RETURNING id
            """,
            (tenant_id, agent_id, layer, f"%{filter_json}%")
        )

        deleted_ids = await cursor.fetchall()
        await db.commit()

        return len(deleted_ids)

async def delete_memories_below_importance(
    self, tenant_id: str, agent_id: str, layer: str, importance_threshold: float
) -> int:
    """Delete memories below importance threshold."""
    await self.initialize()

    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            """
            DELETE FROM memories
            WHERE tenant_id = ? AND agent_id = ? AND layer = ?
            AND importance < ?
            RETURNING id
            """,
            (tenant_id, agent_id, layer, importance_threshold)
        )

        deleted_ids = await cursor.fetchall()
        await db.commit()

        return len(deleted_ids)

async def search_memories(
    self,
    query: str,
    tenant_id: str,
    agent_id: str,
    layer: str,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search memories using FTS5 full-text search."""
    await self.initialize()

    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                m.*,
                rank AS score
            FROM memories m
            JOIN memories_fts ON memories_fts.rowid = m.rowid
            WHERE memories_fts MATCH ?
            AND m.tenant_id = ?
            AND m.agent_id = ?
            AND m.layer = ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, tenant_id, agent_id, layer, limit)
        )

        rows = await cursor.fetchall()

        results = []
        for row in rows:
            memory = dict(row)
            # Parse JSON fields
            memory["tags"] = json.loads(memory.get("tags", "[]"))
            memory["metadata"] = json.loads(memory.get("metadata", "{}"))

            results.append({
                "memory": memory,
                "score": memory.pop("score", 0.0)
            })

        return results

async def delete_expired_memories(
    self, tenant_id: str, agent_id: str, layer: str
) -> int:
    """Delete expired memories."""
    await self.initialize()

    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            """
            DELETE FROM memories
            WHERE tenant_id = ? AND agent_id = ? AND layer = ?
            AND expires_at IS NOT NULL
            AND expires_at < ?
            RETURNING id
            """,
            (tenant_id, agent_id, layer, now)
        )

        deleted_ids = await cursor.fetchall()
        await db.commit()

        return len(deleted_ids)

async def update_memory_access(
    self, memory_id: UUID, tenant_id: str
) -> bool:
    """Update last access time and increment usage count."""
    await self.initialize()

    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            """
            UPDATE memories
            SET last_accessed_at = ?,
                access_count = access_count + 1
            WHERE id = ? AND tenant_id = ?
            """,
            (now, str(memory_id), tenant_id)
        )

        await db.commit()

        return cursor.rowcount > 0

async def update_memory_expiration(
    self, memory_id: UUID, tenant_id: str, expires_at: Any
) -> bool:
    """Update memory expiration time."""
    await self.initialize()

    if isinstance(expires_at, datetime):
        expires_at = expires_at.isoformat()

    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            """
            UPDATE memories
            SET expires_at = ?,
                modified_at = ?
            WHERE id = ? AND tenant_id = ?
            """,
            (
                expires_at,
                datetime.now(timezone.utc).isoformat(),
                str(memory_id),
                tenant_id
            )
        )

        await db.commit()

        return cursor.rowcount > 0
```

**Test**:
```bash
pytest rae-core/tests/unit/adapters/sqlite/test_storage.py -v
```

**Deliverable**: All adapters implement IMemoryStorage interface completely

---

### PHASE 2: Complete RAE-core Library (2-3 hours)

**Goal**: RAE-core as standalone, agnostic library

**Tasks**:

#### Task 2.1: Write tests for reference adapters (1 hour)

Create comprehensive tests:
- `rae-core/tests/unit/adapters/memory/test_storage.py`
- `rae-core/tests/unit/adapters/memory/test_cache.py`
- `rae-core/tests/unit/adapters/sqlite/test_storage.py`

#### Task 2.2: Update pyproject.toml dependencies (15 minutes)

**File**: `rae-core/pyproject.toml`

Ensure ONLY core dependencies:
```toml
[project]
name = "rae-core"
version = "0.2.0"  # Bump version after interface changes
description = "RAE Core - Universal Memory Engine for AI Agents"
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "numpy>=1.24",
    "typing-extensions>=4.0",
    "cryptography>=41.0",  # For RAE-Sync
    "aiosqlite>=0.19",     # For SQLiteStorage
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "black>=23.0",
    "isort>=5.12",
    "mypy>=1.0",
    "ruff>=0.1",
]

# Production adapters are OPTIONAL (not core dependencies!)
postgres = ["asyncpg>=0.29"]
qdrant = ["qdrant-client>=1.7"]
redis = ["redis[hiredis]>=5.0"]
all_adapters = [
    "asyncpg>=0.29",
    "qdrant-client>=1.7",
    "redis[hiredis]>=5.0",
]
```

**Install options**:
```bash
# Core only (SQLite + InMemory)
pip install rae-core

# With production adapters
pip install rae-core[postgres,qdrant,redis]
# or
pip install rae-core[all_adapters]
```

#### Task 2.3: Update README.md (30 minutes)

**File**: `rae-core/README.md`

Clear explanation:
- What RAE-core is (universal engine)
- Storage agnostic architecture
- Available adapters
- Installation options
- Basic usage examples

#### Task 2.4: Run full test suite (15 minutes)

```bash
cd rae-core
pytest tests/ -v --cov=rae_core --cov-report=term-missing

# Expected coverage: >90%
```

#### Task 2.5: Package and test installation (15 minutes)

```bash
cd rae-core
python -m build
pip install -e .

# Test imports
python -c "from rae_core import RAEEngine; print('✅ RAE-core ready!')"
python -c "from rae_core.adapters.memory import InMemoryStorage; print('✅ InMemory ready!')"
python -c "from rae_core.adapters.sqlite import SQLiteStorage; print('✅ SQLite ready!')"
```

**Deliverable**: RAE-core as complete, tested, installable library

---

### PHASE 3: RAE-Server Integration (1 day)

**Goal**: RAE-Server uses RAE-core as library

**Current state**: RAE-Server (apps/memory_api) has own copies of logic

**Tasks**:

#### Task 3.1: Create adapters directory in RAE-Server (2 hours)

**Structure**:
```
apps/memory_api/
├── adapters/           # NEW - Production adapters
│   ├── __init__.py
│   ├── postgres.py    # Move from rae-core, add RAE-Server specific logic
│   ├── qdrant.py      # Move from rae-core, add pooling/config
│   ├── redis.py       # Move from rae-core, add cluster support
│   └── llm/
│       ├── openai.py
│       ├── anthropic.py
│       └── ollama.py
├── services/          # Use rae-core engine
└── ...
```

**Why move adapters?**:
- RAE-core: Reference implementations (simple, mockable)
- RAE-Server: Production implementations (pooling, monitoring, enterprise features)

#### Task 3.2: Refactor services to use RAE-core (4 hours)

**Before**:
```python
# apps/memory_api/services/memory_service.py
from apps.memory_api.core.actions import Action
from apps.memory_api.models import MemoryLayer

class MemoryService:
    # ... custom logic
```

**After**:
```python
# apps/memory_api/services/memory_service.py
from rae_core import RAEEngine
from rae_core.models import MemoryLayer
from apps.memory_api.adapters.postgres import ProductionPostgreSQLStorage
from apps.memory_api.adapters.qdrant import ProductionQdrantStore

class MemoryService:
    def __init__(self):
        self.engine = RAEEngine(
            memory_storage=ProductionPostgreSQLStorage(pool=self.pool),
            vector_store=ProductionQdrantStore(client=self.qdrant),
            embedding_provider=self.embeddings,
            llm_provider=self.llm,
            cache_provider=self.redis,
        )

    async def store_memory(self, ...):
        return await self.engine.store_memory(...)
```

#### Task 3.3: Update tests (2 hours)

Update RAE-Server tests to use rae-core:
```bash
# Old imports
from apps.memory_api.models import MemoryLayer

# New imports
from rae_core.models import MemoryLayer
```

#### Task 3.4: Run integration tests (30 minutes)

```bash
cd apps/memory_api
pytest tests/ -v

# Verify all 892 tests still pass!
```

**Deliverable**: RAE-Server using RAE-core as engine

---

### PHASE 4: RAE-Lite Completion (2-3 days)

**Goal**: Working desktop app (.exe/.app)

**Current state**: rae-lite/ exists but incomplete

**Tasks**:

#### Task 4.1: Use RAE-core in RAE-Lite (1 hour)

**File**: `rae-lite/rae_lite/engine.py`

```python
from rae_core import RAEEngine
from rae_core.adapters.sqlite import SQLiteStorage
from rae_core.adapters.memory import InMemoryCache, InMemoryVectorStore

class RAELiteEngine:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # SQLite storage (local-first!)
        self.storage = SQLiteStorage(
            db_path=str(self.data_dir / "rae.db")
        )

        # In-memory vector store (or sqlite-vec later)
        self.vector_store = InMemoryVectorStore()

        # In-memory cache
        self.cache = InMemoryCache()

        # RAE Engine
        self.engine = RAEEngine(
            memory_storage=self.storage,
            vector_store=self.vector_store,
            cache_provider=self.cache,
            embedding_provider=None,  # Optional: Ollama
            llm_provider=None,  # Optional: Ollama
        )
```

#### Task 4.2: Implement system tray app (4 hours)

**File**: `rae-lite/rae_lite/tray.py`

Using `pystray`:
```python
import pystray
from PIL import Image

class RAETrayApp:
    def __init__(self):
        self.icon = self.create_icon()
        self.engine = RAELiteEngine(data_dir="~/.rae-lite/data")

    def create_icon(self):
        # Create tray icon
        pass

    def on_quit(self, icon, item):
        icon.stop()
        # Cleanup

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Dashboard", self.open_dashboard),
            pystray.MenuItem("Data Folder", self.open_data_folder),
            pystray.MenuItem("About", self.show_about),
            pystray.MenuItem("Quit", self.on_quit)
        )

        self.icon = pystray.Icon("RAE-Lite", self.create_icon(), menu=menu)
        self.icon.run()
```

#### Task 4.3: Build standalone executable (PyInstaller) (2 hours)

**File**: `rae-lite/build_exe.py`

```python
import PyInstaller.__main__

PyInstaller.__main__.run([
    'rae_lite/main.py',
    '--name=RAE-Lite',
    '--onefile',
    '--windowed',  # No console window
    '--icon=assets/icon.ico',
    '--add-data=assets:assets',
])
```

Build:
```bash
cd rae-lite
python build_exe.py

# Output: dist/RAE-Lite.exe (Windows) or dist/RAE-Lite.app (macOS)
```

#### Task 4.4: Test RAE-Lite + Browser Extension (1 hour)

1. Run RAE-Lite
2. Load browser extension
3. Visit ChatGPT/Claude
4. Verify conversations are captured
5. Check RAE-Lite dashboard

**Deliverable**: Working RAE-Lite desktop app

---

### PHASE 5: Future Roadmap (3-6 months)

#### 5.1 RAE-Mobile (2-3 months)

**Goals**:
- iOS/Android native apps
- Use RAE-core engine
- SQLite storage
- On-device LLM (ONNX/CoreML)
- Sync with RAE-Lite/Server

**Tech stack**:
- React Native or Flutter
- Python bridge (Chaquopy for Android, PyCall for iOS)
- Or: Pure native with RAE-core ported to Kotlin/Swift

#### 5.2 RAE-Sync Protocol (1-2 months)

**Goals**:
- P2P synchronization between instances
- E2E encryption
- CRDT-based conflict resolution
- LAN discovery + cloud relay

**Implementation**:
- `rae-core/sync/protocol.py` (already exists!)
- Extend with actual sync implementation
- Add to RAE-Lite and RAE-Mobile

#### 5.3 Production Hardening (ongoing)

- Security audits
- Performance optimization
- Load testing
- Documentation expansion
- SDK improvements (Go, Node.js)

---

## 📊 SUMMARY - Effort Estimation

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| **Phase 0** | Cleanup, commit Gemini's work | 1-2 hours | 🔴 CRITICAL |
| **Phase 1** | Fix 3 bugs | 2-3 hours | 🔴 CRITICAL |
| **Phase 2** | Complete RAE-core | 2-3 hours | 🟡 HIGH |
| **Phase 3** | RAE-Server integration | 1 day | 🟡 HIGH |
| **Phase 4** | RAE-Lite completion | 2-3 days | 🟢 MEDIUM |
| **Phase 5** | Future (Mobile, Sync) | 3-6 months | 🔵 LOW |
| **TOTAL (Phase 0-2)** | RAE-core complete | **1 day** | Core ready! |
| **TOTAL (Phase 0-4)** | Full ecosystem | **1 week** | Production ready! |

---

## 🎯 NEXT IMMEDIATE ACTIONS

**RIGHT NOW** (next 4 hours):

1. **Resolve /rae-core vs /rae_core** (30 min)
2. **Commit Gemini's work** (15 min)
3. **Fix InMemoryCache bug** (5 min)
4. **Implement InMemoryStorage methods** (1 hour)
5. **Implement SQLiteStorage methods** (1.5 hours)
6. **Run tests** (15 min)
7. **Commit Phase 1** (15 min)

**Result**: RAE-core 100% complete and tested! 🎉

---

## 📋 DECISION POINTS

User needs to decide:

1. **Duplication resolution**: Keep /rae-core, what to do with /rae_core?
   - Recommended: Merge unique code, then delete /rae_core

2. **Phase execution order**:
   - Quick win: Phase 0-1-2 (1 day, RAE-core done)
   - Full delivery: Phase 0-4 (1 week, all working)
   - Or parallel: Phase 3+4 can run concurrently

3. **RAE-Lite priority**:
   - High? Then prioritize Phase 4 after Phase 2
   - Medium? Then Phase 3 first (RAE-Server using RAE-core)

---

## ✅ SUCCESS CRITERIA

**Phase 1 Complete** when:
- ✅ InMemoryCache.set_if_not_exists() works
- ✅ InMemoryStorage implements all 6 new methods
- ✅ SQLiteStorage implements all 6 new methods
- ✅ All tests pass (pytest coverage >90%)

**RAE-core Complete** when:
- ✅ All adapters implement IMemoryStorage 100%
- ✅ pip install rae-core works
- ✅ Can be used independently in any project
- ✅ Documentation complete

**Full Ecosystem Complete** when:
- ✅ RAE-core: Standalone library
- ✅ RAE-Server: Uses RAE-core, all tests pass
- ✅ RAE-Lite: .exe/.app works, captures browser conversations
- ✅ All 4 products working as per vision

---

**Ready to execute! Which phase do you want to start with?** 🚀
