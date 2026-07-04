# RAE Architectural Standard Audit Report

**Date**: 2025-12-25
**Auditor**: Gemini Agent (Session ID: 2025-12-25-AUDIT)
**Status**: 🔴 CRITICAL FINDINGS (Action Required)
**Scope**: Agnosticism, Infrastructure Coupling, Developer Experience (DX)

---

## 1. Executive Summary

The "Standard Audit" reveals a critical deviation from RAE's core philosophy of **Architecture Agnosticism**. While the Developer Experience (DX) and Documentation are robust (🟢), the Core Services are tightly coupled to specific infrastructure drivers (asyncpg, Qdrant Client), preventing the deployment of RAE-Lite and violating the "Clean Architecture" principles.

| Area | Status | Finding |
|------|--------|---------|
| **Service Agnosticism** | 🔴 FAIL | Direct `asyncpg` dependency in Repositories (e.g., `EnhancedGraphRepository`). |
| **Infra Decoupling** | 🔴 FAIL | Hardcoded `lifespan` in `main.py` forces Postgres/Redis/Qdrant startup. |
| **Developer Experience** | 🟢 PASS | SDK and Onboarding guides are excellent. |
| **Test Health** | 🟢 PASS | High pass rate, strictly enforcing contracts. |

---

## 2. Detailed Findings

### Finding A: Direct Database Driver Coupling
**Severity**: High
**Location**: `apps/memory_api/repositories/graph_repository_enhanced.py`
**Issue**: The repository imports `asyncpg` and types `pool: asyncpg.Pool` directly.
**Violation**: RAE Rule #1 (Agnosticism). Logic cannot run on SQLite or remote memory pointers.
**Code Evidence**:
```python
# Current
import asyncpg
class EnhancedGraphRepository:
    def __init__(self, pool: asyncpg.Pool): ...
    await self.pool.fetchrow(...)
```

### Finding B: Monolithic Startup Logic
**Severity**: Medium
**Location**: `apps/memory_api/main.py`
**Issue**: The `lifespan` context manager unconditionally initializes `asyncpg`, `redis`, and `QdrantClient`.
**Impact**: Cannot run unit tests or lightweight instances without full Docker stack.
**Violation**: RAE Rule #4 (Modularity).

---

## 3. Iterative Remediation Plan

We will execute the fixes in the following order to maintain system stability.

### 🔄 Iteration 1: The Abstraction Layer (Current Session)
**Goal**: Remove `asyncpg` from `EnhancedGraphRepository`.

1.  **Define Interface**: Create `rae_core/interfaces/database.py` defining `IDatabaseProvider` (fetch, execute, transaction). (✅ DONE)
2.  **Implement Adapter**: Create `rae_core/adapters/postgres_adapter.py` that wraps `asyncpg`. (✅ DONE)
3.  **Refactor Repository**: Update `EnhancedGraphRepository` to accept `IDatabaseProvider`. (✅ DONE)
4.  **Verify**: Run `pytest apps/memory_api/tests/test_graph_enhanced.py`. (✅ DONE - Verified via `test_enhanced_graph_repository_agnostic.py`)

### 🔄 Iteration 2: Infrastructure Injection
**Goal**: Decouple `main.py` from specific drivers.

1.  **Factory Pattern**: Create `InfrastructureFactory` that reads `RAE_PROFILE` env var.
2.  **Lazy Loading**: Only initialize Qdrant/Redis if the profile requires it.
3.  **Update Main**: Replace hardcoded `lifespan` logic with `InfrastructureFactory.initialize(app)`.

### 🔄 Iteration 3: Lite-Mode Verification
**Goal**: Prove agnosticism works.

1.  **Mock Profile**: Create a `lite` profile using Mock/SQLite adapters.
2.  **Smoke Test**: Boot RAE API with `RAE_PROFILE=lite` and verify `/health`.

---

## 4. Execution Command
Start Iteration 1 immediately:
```bash
# Verify current state of tests
make test-focus FILE=apps/memory_api/tests/test_graph_enhanced.py
```
