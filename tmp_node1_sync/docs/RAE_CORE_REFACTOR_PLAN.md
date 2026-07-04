# RAE-Core Refactoring Plan - Behavior-Preserving Extraction

> **Cel**: Wydzielić `rae_core` jako niezależny pakiet Pythona bez psucia istniejącego RAE

**Status**: 📋 PLAN - Wymaga Approval

---

## ✅ Odpowiedź na Główne Pytanie

**Czy da się to zrobić bez popsucia?**

✅ **TAK** - ale z zastrzeżeniami:
1. Musi być **iteracyjne** (nie big-bang refactor)
2. Wymaga **behavior-preserving** approach (testy muszą przechodzić non-stop)
3. Potrzebuje **temporary duplication** (kod będzie chwilowo w 2 miejscach)
4. Wymaga **strict testing** na każdym kroku

---

## 🎯 Cel Refaktoru

### Co ma być w `rae_core`:
✅ **Logika biznesowa** (bez infrastruktury):
- 4 warstwy pamięci (episodic, semantic, working, reflective)
- Warstwa matematyczna (Math-1, Math-2, Math-3)
- Modele danych (Memory, Episode, Reflection)
- Abstrakcyjne interfejsy (Repository protocols)
- Core utilities (bez DB-specific kod)

### Co zostaje w "Dużym RAE":
❌ **Infrastruktura & Deployment**:
- FastAPI (API endpoints)
- PostgreSQL adaptery
- Qdrant/pgvector adaptery
- Docker, docker compose
- Celery workers
- Streamlit dashboard
- Grafana, Prometheus
- CI/CD configs

---

## 📦 Proponowana Struktura `rae_core`

```
rae_core/
├── __init__.py                   # Public API exports
├── pyproject.toml                # Package metadata
├── README.md                     # Core documentation
│
├── models/                       # Data models (bez DB dependencies)
│   ├── __init__.py
│   ├── memory.py                 # MemoryItem, MemoryLayer
│   ├── episode.py                # Episode, EpisodeState
│   ├── reflection.py             # Reflection, ReflectionType
│   ├── graph.py                  # GraphNode, GraphEdge
│   └── common.py                 # Shared types (UUID, datetime utils)
│
├── layers/                       # 4-layer memory system
│   ├── __init__.py
│   ├── episodic.py               # Episodic memory logic
│   ├── semantic.py               # Semantic memory logic
│   ├── working.py                # Working memory logic
│   ├── reflective.py             # Reflective memory logic
│   └── base.py                   # Common layer interfaces
│
├── math/                         # Mathematical layer
│   ├── __init__.py
│   ├── structure.py              # Math-1: Structure analysis
│   ├── dynamics.py               # Math-2: Dynamics tracking
│   ├── policy.py                 # Math-3: Policy optimization
│   └── metrics.py                # Common math metrics
│
├── interfaces/                   # Abstract interfaces (ports)
│   ├── __init__.py
│   ├── repository.py             # Repository protocols
│   ├── storage.py                # Storage backend protocols
│   ├── indexing.py               # Vector indexing protocols
│   └── cache.py                  # Cache protocols
│
├── core/                         # Core business logic
│   ├── __init__.py
│   ├── actions.py                # Action definitions
│   ├── state.py                  # State management
│   ├── reward.py                 # Reward calculations
│   └── executor.py               # Action execution
│
└── utils/                        # Pure utilities (no external deps)
    ├── __init__.py
    ├── datetime.py               # DateTime helpers
    ├── validation.py             # Input validation
    └── serialization.py          # JSON/dict conversions
```

---

## 🔍 Co Przenosimy (Analiza Istniejącego Kodu)

### ✅ DO `rae_core` (Core Logic):

#### 1. Models (z `apps/memory_api/models/`)
- ✅ `models.py` → `rae_core/models/memory.py` (MemoryLayer, MemoryItem)
- ✅ `reflection_v2_models.py` → `rae_core/models/reflection.py`
- ✅ `graph.py` → `rae_core/models/graph.py`
- ⚠️ **EXCLUDE**: `tenant.py`, `rbac.py`, `dashboard_models.py` (infra concerns)

#### 2. Core Logic (z `apps/memory_api/core/`)
- ✅ `actions.py` → `rae_core/core/actions.py`
- ✅ `state.py` → `rae_core/core/state.py`
- ✅ `reward.py` → `rae_core/core/reward.py`
- ✅ `action_executor.py` → `rae_core/core/executor.py`
- ✅ `graph_operator.py` → `rae_core/core/graph_operator.py`
- ⚠️ **CLEAN**: Remove FastAPI dependencies

#### 3. Math Layer (nowy katalog)
- ✅ Extract math logic from `apps/memory_api/services/`:
  - `memory_scoring_v2.py` → `rae_core/math/metrics.py`
  - Math-related parts → `rae_core/math/structure.py`, `dynamics.py`, `policy.py`

#### 4. Interfaces (nowe abstrakcje)
- ✅ Create abstract `Repository` protocols based on existing repositories
- ✅ Create abstract `Storage` protocols
- ✅ **NO IMPLEMENTATIONS** - tylko interfejsy (protocols)

### ❌ POZOSTAJE w "Dużym RAE" (Infrastructure):

#### Repositories (Adapters)
- ❌ `repositories/memory_repository.py` (PostgreSQL adapter)
- ❌ `repositories/graph_repository.py` (PostgreSQL adapter)
- ❌ `repositories/reflection_repository.py` (PostgreSQL adapter)
- **Zmiana**: Będą importować abstrakcje z `rae_core.interfaces`

#### Services (Orchestration)
- ❌ `services/context_builder.py` (uses DB)
- ❌ `services/hybrid_search_service.py` (uses Qdrant/pgvector)
- ❌ `services/compliance_service.py` (enterprise features)
- **Zmiana**: Będą używać `rae_core` jako library

#### API & Infrastructure
- ❌ `api/` (FastAPI routes)
- ❌ `config.py` (env vars, DB connections)
- ❌ `dependencies.py` (FastAPI dependencies)
- ❌ `main.py` (FastAPI app)
- ❌ `celery_app.py` (Celery workers)
- ❌ `Dockerfile`, `docker compose.yml`

---

## 📋 Plan Refaktoryzacji (3 Iteracje)

### 🔷 **Iteracja 1**: Setup & Model Extraction (Bezpieczne)

**Cel**: Utworzyć `rae_core` i przenieść modele bez zmiany "Dużego RAE"

#### Krok 1.1: Utworzenie pakietu
```bash
# Utworzyć strukturę
mkdir -p rae_core/{models,layers,math,interfaces,core,utils}
touch rae_core/__init__.py
```

#### Krok 1.2: pyproject.toml
```toml
[project]
name = "rae-core"
version = "0.1.0"
description = "RAE Core - Memory Engine for AI Agents"
dependencies = [
    "pydantic>=2.0",
    "typing-extensions>=4.5"
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

#### Krok 1.3: Przenieść modele (KOPIUJ, nie usuwaj!)
- Skopiuj `models.py` → `rae_core/models/memory.py`
- Skopiuj `reflection_v2_models.py` → `rae_core/models/reflection.py`
- Wyczyść z zależności DB (Pydantic tylko)

#### Krok 1.4: Testowanie
```bash
cd rae_core
pip install -e .

# Test import
python -c "from rae_core.models import MemoryLayer; print(MemoryLayer.STM)"
```

✅ **Exit Criteria**: `rae_core` instaluje się, modele importują się

---

### 🔶 **Iteracja 2**: Core Logic & Interfaces (Uważnie)

**Cel**: Przenieść core logic i stworzyć abstrakcje

#### Krok 2.1: Stworzyć abstrakcyjne interfejsy
```python
# rae_core/interfaces/repository.py
from typing import Protocol, List, UUID
from rae_core.models.memory import MemoryItem

class MemoryRepository(Protocol):
    """Abstract memory repository interface."""

    async def create(self, memory: MemoryItem) -> MemoryItem:
        ...

    async def get(self, memory_id: UUID) -> MemoryItem | None:
        ...

    async def query(self, filters: dict) -> List[MemoryItem]:
        ...
```

#### Krok 2.2: Przenieść core logic
- Skopiuj `core/actions.py` → `rae_core/core/actions.py`
- Skopiuj `core/state.py` → `rae_core/core/state.py`
- Wyczyść z FastAPI dependencies

#### Krok 2.3: Refaktoryzacja "Dużego RAE" (CZĘŚCIOWA)
```python
# apps/memory_api/repositories/memory_repository.py
# PRZED:
from apps.memory_api.models import MemoryItem

# PO:
from rae_core.models.memory import MemoryItem
from rae_core.interfaces.repository import MemoryRepository
```

#### Krok 2.4: Testowanie
```bash
# Uruchom WSZYSTKIE testy
make test-unit

# Wszystkie muszą przejść!
# Jeśli nie - rollback i fix
```

✅ **Exit Criteria**: Wszystkie testy przechodzą, "Duże RAE" używa częściowo `rae_core`

---

### 🔷 **Iteracja 3**: Math Layer & Cleanup (Ostrożnie!)

**Cel**: Dokończyć math layer i usunąć duplikaty

#### Krok 3.1: Extract Math Layer
- Wyciągnij math logic z `services/memory_scoring_v2.py`
- Przenieś do `rae_core/math/`
- Tylko **pure functions** (bez DB queries)

#### Krok 3.2: Refaktoryzacja Services
```python
# apps/memory_api/services/memory_scoring_v2.py
# PRZED: Mieszanka math logic + DB queries

# PO: Import math z rae_core
from rae_core.math.metrics import calculate_importance
from rae_core.math.dynamics import calculate_drift

# Service tylko orchestruje: fetch z DB → call math → save wynik
```

#### Krok 3.3: Usunięcie duplikatów
**DOPIERO TERAZ** usuwaj stare pliki:
```bash
# Usuń stare models.py (już jest w rae_core)
git rm apps/memory_api/models.py

# Zastąp import w 100+ plikach
find apps/ -name "*.py" -exec sed -i 's/from apps.memory_api.models import/from rae_core.models.memory import/g' {} \;
```

#### Krok 3.4: Final Testing
```bash
# Pełna test suite
make test-unit

# Benchmarks (sprawdź czy performance nie spadło)
make benchmark-lite

# Manual smoke test
docker compose up -d
curl http://localhost:8000/health
```

✅ **Exit Criteria**:
- Testy: ✅ All passing
- Performance: ✅ No regression
- "Duże RAE" używa 100% `rae_core`
- Duplikaty usunięte

---

## ⚠️ Ryzyka & Mitigations

### Ryzyko 1: Import Hell
**Problem**: Circular imports między `rae_core` a "Dużym RAE"

**Mitigation**:
- `rae_core` NIGDY nie importuje z "Dużego RAE"
- Tylko "Duże RAE" importuje z `rae_core`
- Dependency flow: "Duże RAE" → `rae_core` (one-way)

### Ryzyko 2: Breaking Changes
**Problem**: Refactor psuje istniejącą funkcjonalność

**Mitigation**:
- **RULE**: Testy muszą przechodzić ZAWSZE (na każdym commit)
- Używaj `git stash` często
- Małe commity (< 200 linii zmiany)
- Rollback przy pierwszym fail

### Ryzyko 3: Performance Regression
**Problem**: Dodatkowa abstrakcja spowalnia system

**Mitigation**:
- Benchmarki przed i po (akademic_lite)
- Jeśli >5% spadek → investigate
- Profile critical paths (memory.py imports)

### Ryzyko 4: Lost Context
**Problem**: Refactor trwa tygodniami, zapominamy co i dlaczego

**Mitigation**:
- **TODO list** w każdej iteracji (TodoWrite!)
- Dokumentuj decyzje w docstrings
- Daily summary commits

---

## 📊 Metryki Sukcesu

Po ukończeniu refaktoru:

✅ **Testy**: 892/955 passing (bez regresji)
✅ **Coverage**: ≥69% (nie może spaść)
✅ **Performance**: <5% overhead
✅ **LOC**: `rae_core` < 5000 linii (mały!)
✅ **Dependencies**: `rae_core` ma <5 deps (Pydantic + typing-extensions + ?)
✅ **Installable**: `pip install -e rae_core` działa
✅ **Portable**: `rae_core` działa w Python 3.10+ (bez Docker)

---

## 🚀 Next Steps (Po Approval)

1. **Review tego planu** (user approval)
2. **Iteracja 1** (3-5 dni):
   - Setup pakietu
   - Modele extraction
   - Pierwsze testy
3. **Iteracja 2** (5-7 dni):
   - Core logic
   - Interfaces
   - Partial integration
4. **Iteracja 3** (7-10 dni):
   - Math layer
   - Cleanup
   - Full integration

**TOTAL**: ~3-4 tygodnie (z testowaniem)

---

## 🎯 Długoterminowa Wizja

Po ukończeniu `rae_core`, możliwe będzie:

1. **RAE-Local** (SQLite + Ollama):
   ```python
   from rae_core import MemoryEngine
   from rae_local.adapters import SQLiteRepository

   engine = MemoryEngine(repo=SQLiteRepository("memory.db"))
   ```

2. **RAE-Mobile** (iOS/Android):
   ```python
   # Python core exportowany do Swift/Kotlin via Py4J
   ```

3. **RAE-Cloud** (bez self-hosting):
   ```python
   # Używa tego samego rae_core, tylko storage w cloud
   ```

---

**Autor**: Claude Sonnet 4.5 + Grzegorz
**Data**: 2025-12-08
**Status**: 📋 WYMAGA APPROVAL

**Pytanie do User**: Czy zatwierdzasz ten plan i przechodzimy do Iteracji 1?
