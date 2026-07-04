# RAE-Core Test Coverage Plan (Target: 90%+)

**Status**: Draft
**Target Coverage**: 95% (Global)
**Current Coverage**: ~35%
**Focus**: `rae-core` library

## 1. Executive Summary

This document outlines the roadmap to increase `rae-core` test coverage from the current **35%** to a robust **95%**. The core library is designed to be database-agnostic, which significantly simplifies unit testing through dependency injection and mocking.

**Philosophy**:
- **Unit Tests First**: Focus on logic verification using `unittest.mock`. This is fast and covers 80% of the codebase.
- **Integration Tests Second**: Use `testcontainers` or local service mocks for Adapters (Postgres, Qdrant, Redis).
- **Fix Deprecations**: Eliminate 197+ `datetime.utcnow()` warnings to clean up test output.

## 2. Coverage Gaps & Strategy

Based on the architectural analysis, the following areas require immediate attention:

| Module | Current Status | Priority | Strategy |
|--------|----------------|----------|----------|
| `rae_core/layers/` | 0% | 🔴 CRITICAL | Unit tests with mocked adapters. Test storage/retrieval logic. |
| `rae_core/engine.py` | 0% | 🔴 CRITICAL | Unit tests mocking the Layers to verify orchestration flow. |
| `rae_core/adapters/*` | 14-18% | 🟡 HIGH | Mocked unit tests for logic + Integration tests for DB interaction. |
| `rae_core/llm/` | 0% | 🟡 HIGH | Mock LLM responses. Do NOT call real APIs. |
| `rae_core/math/` | 0% | 🟢 MEDIUM | Pure unit tests (input -> output). No mocks needed mostly. |
| `rae_core/reflection/` | 0% | 🟢 MEDIUM | Mock Evaluator and Engine interaction. |

## 3. Implementation Roadmap

### Phase 0: Hygiene & Configuration (ETA: 1 Day)
**Goal**: Clean test output and ensure stable foundation.
1.  **Fix Deprecations**: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` across `rae-core`.
2.  **Test Config**: Add tests for `rae_core/config/` to ensure default settings and overrides work.
3.  **Setup Fixtures**: Create robust `conftest.py` fixtures for:
    - Mocked MemoryRepository
    - Mocked VectorRepository
    - Mocked LLMProvider

### Phase 1: The Core Logic (Layers) (ETA: 2-3 Days)
**Goal**: Verify the "Brain" of the system.
**Target**: `rae_core/layers/*.py`
1.  **Sensory Layer**: Test buffer management, expiration logic.
2.  **Working Layer**: Test context window management, consolidation rules.
3.  **Episodic/Longterm**: Test storage/retrieval routing and embedding triggering.
4.  **Reflective**: Test meta-analysis triggers.

*Technique*: Inject `Mock(spec=MemoryRepositoryProtocol)` into layer constructors.

### Phase 2: Engine Orchestration (ETA: 1-2 Days)
**Goal**: Ensure components work together.
**Target**: `rae_core/engine.py`
1.  Test `put()` method flows through appropriate layers.
2.  Test `get()` queries routing.
3.  Test bootstrap/startup sequences.

### Phase 3: Adapters (The "Hard" Part) (ETA: 3 Days)
**Goal**: Verify data persistence without relying on external infra for every test.
**Target**: `rae_core/adapters/{postgres,qdrant,redis}.py`

1.  **Unit Tests (Mocked)**:
    - Mock `asyncpg.Connection`, `redis.Redis`, `qdrant_client.QdrantClient`.
    - Verify SQL query generation (check strings).
    - Verify parameter passing.
    - Verify error handling (e.g., connection lost).

2.  **Integration Tests (Optional for Phase 3, mandatory for Release)**:
    - If `testcontainers` is available: Spin up Postgres/Qdrant.
    - If not: Skip for now, rely on high-quality mocks.

### Phase 4: Advanced Features (ETA: 2 Days)
**Goal**: Coverage for Math, Search, and LLM strategies.
1.  **Math**: Test policies, metrics calculation (pure functions).
2.  **Search**: Test hybrid search fusion logic (mock the search results from different sources).
3.  **LLM**: Test fallback strategies and prompt construction.

## 4. Definition of Done

The project will be considered "Standardized & Covered" when:
1.  `pytest --cov=rae-core/rae_core` returns **>90%**.
2.  No `DeprecationWarning` in test output.
3.  All tests pass in `< 30 seconds` (ensured by extensive mocking).
4.  CI pipeline enforces this coverage level.

## 5. Next Steps

1.  Approve this plan.
2.  Start **Phase 0** (Fix deprecations).
3.  Execute **Phase 1** (Core Layers).
