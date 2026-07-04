# RAE-Server Migration Plan: Legacy Services → rae_core

## Overview

This document outlines the migration from legacy `apps/memory_api/services/` to the new `rae_core` architecture.

**Migration Status:** In Progress
**Target Version:** v2.2.0-enterprise
**Completion Date:** TBD

---

## Component Mapping

### Memory Management

| Legacy Service | New rae_core Component | Status | Notes |
|---|---|---|---|
| `memory_manager.py` | `rae_core.engine.RAEEngine` | ✅ Migrated | Use RAEEngine.store_memory(), retrieve_memory() |
| `memory_scoring_v2.py` | `rae_core.scoring.decay.ImportanceDecay` | ✅ Migrated | Decay logic in rae_core |
| `memory_consolidation.py` | `rae_core.reflection.actor.Actor` | ✅ Migrated | Consolidation via Actor.consolidate_memories() |

### Search & Retrieval

| Legacy Service | New rae_core Component | Status | Notes |
|---|---|---|---|
| `semantic_search.py` | `rae_core.search.engine.HybridSearchEngine` | ✅ Migrated | Hybrid search with multiple strategies |
| `vector_search.py` | `rae_core.search.strategies.vector.VectorSearchStrategy` | ✅ Migrated | Part of hybrid search |
| `graph_search.py` | `rae_core.search.strategies.graph.GraphTraversalStrategy` | ✅ Migrated | Graph-based traversal |

### Reflection & Meta-Cognition

| Legacy Service | New rae_core Component | Status | Notes |
|---|---|---|---|
| `reflection_pipeline.py` | `rae_core.reflection.engine.ReflectionEngine` | ✅ Migrated | Full Actor-Evaluator-Reflector pattern |
| `reflection_generators/` | `rae_core.reflection.reflector.Reflector` | ✅ Migrated | Multiple reflection types |
| - | `rae_core.reflection.evaluator.Evaluator` | ✅ New | Quality assessment & metrics |
| - | `rae_core.reflection.actor.Actor` | ✅ New | Action execution |

### LLM Integration

| Legacy Service | New rae_core Component | Status | Notes |
|---|---|---|---|
| `llm_client.py` | `rae_core.llm.orchestrator.LLMOrchestrator` | ✅ Migrated | Multi-provider orchestration |
| - | `rae_core.llm.fallback.NoLLMFallback` | ✅ New | Rule-based fallback |
| - | `rae_core.llm.strategies.*` | ✅ New | Fallback & load balancing strategies |

### Synchronization

| Legacy Service | New rae_core Component | Status | Notes |
|---|---|---|---|
| - | `rae_core.sync.protocol.SyncProtocol` | ✅ New | Push/pull/sync operations |
| - | `rae_core.sync.diff.calculate_memory_diff` | ✅ New | Memory diff calculation |
| - | `rae_core.sync.merge.merge_memories` | ✅ New | CRDT-based merge |
| - | `rae_core.sync.encryption.E2EEncryption` | ✅ New | E2E encryption |

### Configuration

| Legacy Service | New rae_core Component | Status | Notes |
|---|---|---|---|
| Settings in `.env` | `rae_core.config.settings.RAESettings` | ✅ Migrated | Pydantic-based settings |
| Hardcoded constants | `rae_core.config.defaults.*` | ✅ Migrated | Centralized defaults |

---

## API Router Migration

### V1 API Endpoints → rae_core

#### Memory Router (`routers/memory.py`)

**Before:**
```python
from apps.memory_api.services.memory_manager import MemoryManager

memory_manager = MemoryManager(...)
result = await memory_manager.store_memory(...)
```

**After:**
```python
from rae_core.engine import RAEEngine
from rae_core.config import RAESettings

settings = RAESettings()
engine = RAEEngine(
    memory_storage=memory_storage,
    vector_store=vector_store,
    embedding_provider=embedding_provider,
    settings=settings,
)
result = await engine.store_memory(...)
```

#### Search Router (`routers/search.py`)

**Before:**
```python
from apps.memory_api.services.semantic_search import SemanticSearch

search = SemanticSearch(...)
results = await search.search(query)
```

**After:**
```python
from rae_core.engine import RAEEngine

results = await engine.search_memories(
    query=query,
    tenant_id=tenant_id,
    agent_id=agent_id,
    use_reranker=True,
)
```

#### Reflection Router (`routers/reflection.py`)

**Before:**
```python
from apps.memory_api.services.reflection_pipeline import ReflectionPipeline

pipeline = ReflectionPipeline(...)
result = await pipeline.generate_reflection(memory_ids)
```

**After:**
```python
from rae_core.engine import RAEEngine

result = await engine.generate_reflection(
    memory_ids=memory_ids,
    tenant_id=tenant_id,
    agent_id=agent_id,
    reflection_type="consolidation",
)
```

---

## Deprecated Components

The following components are marked as **DEPRECATED** and will be removed in v3.0:

### Phase 1 Deprecation (v2.2.0)
- ⚠️ `services/memory_manager.py` → Use `rae_core.engine.RAEEngine`
- ⚠️ `services/memory_scoring_v2.py` → Use `rae_core.scoring.*`
- ⚠️ `services/semantic_search.py` → Use `rae_core.search.engine.HybridSearchEngine`
- ⚠️ `services/vector_search.py` → Use `rae_core.search.strategies.vector`
- ⚠️ `services/graph_search.py` → Use `rae_core.search.strategies.graph`
- ⚠️ `services/reflection_pipeline.py` → Use `rae_core.reflection.engine.ReflectionEngine`
- ⚠️ `services/llm_client.py` → Use `rae_core.llm.orchestrator.LLMOrchestrator`

### Phase 2 Deprecation (v2.3.0)
- ⚠️ All remaining services in `services/` directory
- ⚠️ Legacy models in `models/` (replaced by rae_core.models)

### Removal Timeline
- **v2.2.0** (Current): Mark as deprecated, add warnings
- **v2.3.0** (Q1 2025): Remove deprecated code, breaking changes
- **v3.0.0** (Q2 2025): Clean architecture, rae_core only

---

## Migration Checklist

### ✅ Completed
- [x] Create rae_core base structure
- [x] Implement interfaces (storage, vector, graph, llm, etc.)
- [x] Implement search strategies (vector, graph, sparse, fulltext)
- [x] Implement LLM orchestration with fallback
- [x] Implement Reflection V2 (Actor-Evaluator-Reflector)
- [x] Implement configuration system (RAESettings)
- [x] Implement sync protocol (push/pull/sync, CRDT merge)
- [x] Create RAEEngine as unified interface

### 🚧 In Progress
- [ ] Migrate v1 API routers to use RAEEngine
- [ ] Add @deprecated decorators to legacy services
- [ ] Update tests to use rae_core
- [ ] Create v2 API endpoints

### ⏳ Pending
- [ ] Update documentation (API_MIGRATION_GUIDE.md)
- [ ] Performance benchmarking (rae_core vs legacy)
- [ ] Remove deprecated code in v3.0
- [ ] Naming normalization (rae-core → rae_core across all imports)

---

## Testing Strategy

### Unit Tests
- Test each rae_core component independently
- Ensure backward compatibility with v1 API
- Verify deprecated warnings are shown

### Integration Tests
- Test full flow: v1 API → RAEEngine → storage/vector backends
- Test reflection pipeline end-to-end
- Test sync protocol with mock remote

### E2E Tests
- Test v1 API endpoints with rae_core backend
- Test v2 API endpoints
- Verify no regressions in existing functionality

---

## Rollback Plan

If issues arise during migration:

1. **Revert to legacy services:** Set feature flag `USE_RAE_CORE=false`
2. **Gradual rollout:** Enable per-endpoint or per-tenant
3. **Monitor metrics:** Track errors, latency, memory usage
4. **Fallback mechanism:** Automatic failover to legacy on errors

---

## Performance Considerations

### Expected Improvements
- **Unified caching:** rae_core uses single cache layer
- **Reduced duplication:** Eliminates redundant code in services/
- **Better memory management:** Optimized data structures in rae_core
- **Async-first:** Full async/await throughout rae_core

### Potential Issues
- **Initial overhead:** RAEEngine initialization cost
- **Learning curve:** New API patterns for developers
- **Testing coverage:** Need comprehensive test suite

---

## Support & Questions

For questions or issues during migration:
- **GitHub Issues:** Use label `migration-rae-core`
- **Docs:** See `docs/RAE_CORE_INTEGRATION.md`
- **Slack:** #rae-core-migration channel

---

**Last Updated:** 2025-12-10
**Version:** 0.4.0
**Author:** Grzegorz Leśniowski
