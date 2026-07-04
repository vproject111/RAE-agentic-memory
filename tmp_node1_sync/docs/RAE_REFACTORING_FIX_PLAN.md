# RAE Architecture Refactoring - Plan Naprawy

**Data:** 2025-12-10
**Status:** DO WYKONANIA
**Autor:** Plan automatycznej naprawy architektury

## 🎯 Cel

Dokończenie refaktoryzacji RAE zgodnie z planem v2.0, naprawa niespójności nazewnictwa i uzupełnienie brakujących komponentów.

## 🔍 Zidentyfikowane Problemy

### 1. Niespójność nazewnictwa
- ❌ Mieszane `rae-core` (myślnik) i `rae_core` (podkreślenie)
- ❌ Python wymaga `rae_core` w importach
- ❌ Nazwa katalogu vs nazwa pakietu niezgodna

### 2. Niekompletna implementacja (50-60%)

**RAE-core brakujące komponenty (~40%):**
- `py.typed`, `version.py`
- Models: `search.py`, `context.py`, `scoring.py`, `sync.py`
- Math: `controller.py`, `metrics.py`
- Search strategies: `vector.py`, `graph.py`, `sparse.py`, `fulltext.py`
- Reflection: `actor.py`, `evaluator.py`, `reflector.py`
- Context: `window.py`
- Scoring: `decay.py`
- Interfaces: 7 brakujących plików
- Całe katalogi: `llm/`, `sync/`, `config/`

**RAE-Server częściowa migracja (~40%):**
- v1 API wciąż używa starej logiki
- Stare services/ powinny być deprecated
- Brak pełnej integracji z rae_core

**RAE-Lite uproszczone (~30%):**
- Brak system tray app
- Brak local HTTP server
- Brak UI windows
- Brak embedding/LLM adapters

**RAE-Sync (~0%):**
- Cała Phase 5 niezaimplementowana

## 📋 Plan Naprawy - 6 Iteracji

### **Iteracja 1: Audit i Normalizacja Nazewnictwa** (1h)
**Branch:** `fix/rae-naming-normalization`

**Zadania:**
1. Przeprowadź pełny audit struktury katalogów i importów
2. Ustandaryzuj nazewnictwo:
   - Katalog główny: `rae_core/` (Python package)
   - Import: `from rae_core import ...`
   - PyPI package name: `rae-core` (w pyproject.toml)
3. Napraw wszystkie importy w całym projekcie:
   - `apps/memory_api/` → zamień `from rae-core` na `from rae_core`
   - `rae-lite/` → zamień wszystkie importy
   - `browser-extension/` → sprawdź czy są importy
4. Zaktualizuj wszystkie `pyproject.toml`, `setup.py`, `requirements.txt`
5. Zaktualizuj CI/CD: `.github/workflows/ci.yml`

**Weryfikacja:**
```bash
# Sprawdź czy wszystkie importy działają
grep -r "from rae-core" . --exclude-dir=node_modules
grep -r "import rae-core" . --exclude-dir=node_modules
# Powinno nie znaleźć żadnych wyników

# Test importu
python -c "import rae_core; print(rae_core.__version__)"

# Uruchom testy
pytest rae_core/tests/ -v
pytest apps/memory_api/tests/ -k rae_core -v
```

**Commit message:** `fix: normalize rae-core/rae_core naming across codebase`

---

### **Iteracja 2: RAE-core - Uzupełnienie Podstawowych Komponentów** (2h)
**Branch:** `feat/rae-core-complete-base`

**Zadania:**
1. Dodaj brakujące root files:
   - `rae_core/py.typed` (pusty plik dla PEP 561)
   - `rae_core/version.py` z `__version__ = "0.2.0"`

2. Uzupełnij Models:
   - `models/search.py`: SearchQuery, SearchResult, SearchWeights, SearchFilters
   - `models/context.py`: WorkingContext, ContextWindow, ContextMetadata
   - `models/scoring.py`: ScoringWeights, QualityMetrics, DecayConfig
   - `models/sync.py`: SyncState, SyncDelta, ConflictResolution

3. Uzupełnij Math:
   - `math/controller.py`: MathLayerController (może już istnieć, sprawdź)
   - `math/metrics.py`: All metrics classes (CoherenceMetric, EntropyMetric, etc.)

4. Uzupełnij Context:
   - `context/window.py`: ContextWindow management, token counting

5. Uzupełnij Scoring:
   - `scoring/decay.py`: ImportanceDecay, time-based decay functions

**Źródła kodu:**
- Skopiuj z `apps/memory_api/models/` i dostosuj (usuń SQLAlchemy)
- Skopiuj z `apps/memory_api/core/` dla matematyki
- Skopiuj z `apps/memory_api/services/memory_scoring_v2.py` dla scoring

**Weryfikacja:**
```bash
# Sprawdź strukturę
ls -la rae_core/rae_core/models/
ls -la rae_core/rae_core/math/
ls -la rae_core/rae_core/context/
ls -la rae_core/rae_core/scoring/

# Testy importów
python -c "from rae_core.models.search import SearchQuery"
python -c "from rae_core.models.context import WorkingContext"
python -c "from rae_core.math.controller import MathLayerController"
python -c "from rae_core.scoring.decay import ImportanceDecay"

# Unit testy
pytest rae_core/tests/test_models/ -v
pytest rae_core/tests/test_math/ -v
```

**Commit message:** `feat(rae-core): add missing base components (models, math, context, scoring)`

---

### **Iteracja 3: RAE-core - Interfejsy i Strategie Wyszukiwania** (2h)
**Branch:** `feat/rae-core-interfaces-search`

**Zadania:**
1. Uzupełnij wszystkie Interfaces w `interfaces/`:
   - `storage.py`: IMemoryStorage (async CRUD)
   - `vector.py`: IVectorStore (similarity search)
   - `graph.py`: IGraphStore (nodes & edges)
   - `cache.py`: ICacheProvider (get/set/invalidate)
   - `llm.py`: ILLMProvider (generate, stream)
   - `embedding.py`: IEmbeddingProvider (embed text/batch)
   - `sync.py`: ISyncProvider (push/pull/resolve)

2. Uzupełnij Search Strategies w `search/strategies/`:
   - `vector.py`: VectorSearchStrategy (semantic)
   - `graph.py`: GraphTraversalStrategy (relationships)
   - `sparse.py`: SparseVectorStrategy (BM25/TF-IDF)
   - `fulltext.py`: FullTextStrategy (keyword matching)

3. Dodaj `search/cache.py`: Search result caching interface

**Źródła:**
- `apps/memory_api/services/hybrid_search.py` → podziel na strategie
- `apps/memory_api/repositories/` → wyciągnij interfejsy
- Zobacz implementacje w `rae_core/adapters/` jako wzór

**Weryfikacja:**
```bash
# Sprawdź strukturę
ls -la rae_core/rae_core/interfaces/
ls -la rae_core/rae_core/search/strategies/

# Testy typowania
mypy rae_core/rae_core/interfaces/ --strict
mypy rae_core/rae_core/search/ --strict

# Unit testy
pytest rae_core/tests/test_interfaces/ -v
pytest rae_core/tests/test_search/ -v
```

**Commit message:** `feat(rae-core): implement all interfaces and search strategies`

---

### **Iteracja 4: RAE-core - LLM i Reflection V2** (2h)
**Branch:** `feat/rae-core-llm-reflection`

**Zadania:**
1. Stwórz katalog `llm/` z plikami:
   - `orchestrator.py`: LLMOrchestrator (zarządza providerami)
   - `strategies.py`: SingleLLMStrategy, FallbackStrategy, LoadBalancingStrategy
   - `fallback.py`: NoLLM rule-based fallback (bez external API)
   - `config.py`: LLMConfig, ProviderConfig

2. Uzupełnij Reflection V2 w `reflection/`:
   - `actor.py`: Actor component (wykonuje akcje)
   - `evaluator.py`: Evaluator component (ocenia wyniki)
   - `reflector.py`: Reflector component (generuje refleksje)
   - Zaktualizuj `engine.py` żeby używał tych komponentów

**Zasady:**
- LLM komponenty używają interfejsów (ILLMProvider)
- Fallback musi działać bez LLM (rule-based)
- Reflection używa Actor-Evaluator-Reflector pattern

**Źródła:**
- `apps/memory_api/services/llm_orchestrator.py`
- `apps/memory_api/services/reflection_engine.py`

**Weryfikacja:**
```bash
# Sprawdź strukturę
ls -la rae_core/rae_core/llm/
ls -la rae_core/rae_core/reflection/

# Test bez LLM
python -c "
from rae_core.llm.fallback import NoLLMFallback
fallback = NoLLMFallback()
result = fallback.generate('summarize: test')
print(result)
"

# Unit testy
pytest rae_core/tests/test_llm/ -v
pytest rae_core/tests/test_reflection/ -v
```

**Commit message:** `feat(rae-core): add LLM orchestration and Reflection V2 components`

---

### **Iteracja 5: RAE-core - Config i Sync Protocol** (2h)
**Branch:** `feat/rae-core-config-sync`

**Zadania:**
1. Stwórz katalog `config/`:
   - `settings.py`: RAESettings (pydantic-settings)
   - `defaults.py`: DEFAULT_SENSORY_SIZE, DEFAULT_DECAY_RATE, etc.

2. Stwórz katalog `sync/`:
   - `protocol.py`: SyncProtocol class (push/pull/sync)
   - `diff.py`: calculate_memory_diff, DiffResult
   - `merge.py`: CRDT-based merge_memories, ConflictResolver
   - `encryption.py`: E2EEncryption helpers (encrypt/decrypt)

3. Zaktualizuj `engine.py`:
   - Integracja z RAESettings
   - Opcjonalne sync_provider w konstruktorze

**Zasady:**
- Settings używa pydantic-settings (env vars)
- Sync protocol używa ISyncProvider interface
- E2E encryption używa cryptography library

**Weryfikacja:**
```bash
# Test konfiguracji
python -c "
from rae_core.config import RAESettings
settings = RAESettings()
print(settings.sensory_max_size)
"

# Test sync
pytest rae_core/tests/test_sync/ -v

# Test encryption
python -c "
from rae_core.sync.encryption import E2EEncryption
enc = E2EEncryption()
data = enc.encrypt('test')
print(enc.decrypt(data))
"
```

**Commit message:** `feat(rae-core): add configuration system and sync protocol`

---

### **Iteracja 6: RAE-Server - Pełna Migracja do rae_core** (3h)
**Branch:** `feat/rae-server-full-migration`

**Zadania:**
1. Utwórz plik `apps/memory_api/services/MIGRATION_PLAN.md`:
   - Mapowanie: stara service → nowy rae_core komponent
   - Lista deprecated endpointów

2. Migruj v1 API do używania rae_core:
   - `routers/memory.py` → używaj RAECoreService
   - `routers/search.py` → używaj rae_core.search
   - `routers/reflection.py` → używaj rae_core.reflection

3. Oznacz stare services jako deprecated:
   - Dodaj `@deprecated` dekorator
   - Dodaj logging warnings
   - Zaktualizuj dokumentację

4. Zaktualizuj testy:
   - `apps/memory_api/tests/` → używaj rae_core
   - Usuń testy dla deprecated komponentów

5. Zaktualizuj dokumentację:
   - `docs/API_MIGRATION_GUIDE.md` (v1 → v2)
   - `docs/RAE_CORE_INTEGRATION.md`

**Weryfikacja:**
```bash
# Sprawdź deprecated
grep -r "@deprecated" apps/memory_api/services/

# Test v1 API z rae_core
pytest apps/memory_api/tests/routers/test_memory.py -v
pytest apps/memory_api/tests/routers/test_search.py -v

# Test v2 API
pytest apps/memory_api/tests/api/v2/ -v

# E2E test
python -c "
import requests
# Test v1 endpoint (should work with rae_core backend)
resp = requests.post('http://localhost:8000/v1/memories', json={...})
print(resp.json())
"
```

**Commit message:** `feat(api): complete migration from legacy services to rae_core`

---

## 🔄 Workflow Wykonania

Dla każdej iteracji:

### 1. Rozpoczęcie iteracji
```bash
# Przełącz na develop
git checkout develop
git pull origin develop

# Utwórz feature branch
git checkout -b <branch-name>
```

### 2. Implementacja
- Wykonaj wszystkie zadania z iteracji
- Pisz kod zgodnie z istniejącymi wzorcami
- Dodawaj docstringi i type hints
- Twórz unit testy dla nowych komponentów

### 3. Testowanie lokalne
```bash
# Uruchom wszystkie testy
pytest rae_core/tests/ -v
pytest apps/memory_api/tests/ -v

# Sprawdź pokrycie
pytest --cov=rae_core --cov-report=html

# Lint i type checking
ruff check .
mypy rae_core/
```

### 4. Commit i push
```bash
# Dodaj zmiany
git add .

# Commit z komunikatem z planu
git commit -m "<commit-message>"

# Push na develop
git push origin <branch-name>
```

### 5. Integracja z develop
```bash
# Przełącz na develop
git checkout develop

# Merge feature branch
git merge <branch-name> --no-edit

# Push develop
git push origin develop
```

### 6. Czekanie na CI
```bash
# Monitoruj CI na develop
gh run watch --branch develop

# Jeśli testy NIE przechodzą:
#   - Analizuj błędy
#   - Napraw na develop
#   - Commit naprawę
#   - Push i czekaj ponownie
#   - Powtarzaj aż testy przejdą

# Jeśli testy PRZECHODZĄ → przechodź do kolejnej iteracji
```

### 7. Merge do main (tylko po WSZYSTKICH iteracjach)
```bash
# Po zakończeniu WSZYSTKICH 6 iteracji
git checkout main
git merge develop --no-edit
git push origin main

# Monitoruj CI na main
gh run watch --branch main
```

## 📊 Tracking Progress

Utworzyć plik `RAE_REFACTORING_PROGRESS.md`:

```markdown
# RAE Refactoring Progress

## Iteracja 1: Normalizacja Nazewnictwa
- [ ] Status: NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
- [ ] Branch: fix/rae-naming-normalization
- [ ] CI develop: PENDING | SUCCESS | FAILED
- [ ] Commit: <hash>

## Iteracja 2: Podstawowe Komponenty
- [ ] Status: NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
- [ ] Branch: feat/rae-core-complete-base
- [ ] CI develop: PENDING | SUCCESS | FAILED
- [ ] Commit: <hash>

## Iteracja 3: Interfejsy i Search
- [ ] Status: NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
- [ ] Branch: feat/rae-core-interfaces-search
- [ ] CI develop: PENDING | SUCCESS | FAILED
- [ ] Commit: <hash>

## Iteracja 4: LLM i Reflection
- [ ] Status: NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
- [ ] Branch: feat/rae-core-llm-reflection
- [ ] CI develop: PENDING | SUCCESS | FAILED
- [ ] Commit: <hash>

## Iteracja 5: Config i Sync
- [ ] Status: NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
- [ ] Branch: feat/rae-core-config-sync
- [ ] CI develop: PENDING | SUCCESS | FAILED
- [ ] Commit: <hash>

## Iteracja 6: RAE-Server Migration
- [ ] Status: NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
- [ ] Branch: feat/rae-server-full-migration
- [ ] CI develop: PENDING | SUCCESS | FAILED
- [ ] Commit: <hash>

## Final Merge to main
- [ ] Status: NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
- [ ] CI main: PENDING | SUCCESS | FAILED
- [ ] Merge commit: <hash>
```

## ⚠️ Zasady Wykonania

1. **Sekwencyjność:** Iteracje MUSZĄ być wykonywane po kolei (1 → 6)
2. **CI jako gatekeeper:** Każda iteracja musi przejść CI na develop przed następną
3. **Nie skrótów:** Wszystkie zadania z iteracji muszą być wykonane
4. **Testy MUSZĄ działać:** Jeśli testy failują, napraw zanim przejdziesz dalej
5. **Brak user intervention:** Plan musi być wykonany automatycznie od początku do końca
6. **Rollback:** Jeśli iteracja zawiedzie 3 razy, cofnij branch i rozpocznij od nowa

## 📈 Oczekiwane Rezultaty

Po wykonaniu wszystkich 6 iteracji:

- ✅ Nazewnictwo zunifikowane (rae_core wszędzie)
- ✅ RAE-core kompletne 100% według planu v2.0
- ✅ RAE-Server w pełni zmigrowne do rae_core
- ✅ Wszystkie testy przechodzą (100% CI green)
- ✅ Dokumentacja aktualna
- ✅ Gotowe do Phase 5 (RAE-Sync) i Phase 6 (RAE-Mobile)

## 🚀 Rozpoczęcie Wykonania

W nowej sesji uruchom:

```bash
# Ustaw kontekst
cd /home/grzegorz/cloud/Dockerized/RAE-agentic-memory

# Przeczytaj plan
cat docs/RAE_REFACTORING_FIX_PLAN.md

# Rozpocznij od Iteracji 1
# I kontynuuj automatycznie przez wszystkie 6 iteracji
```

---

**Koniec planu naprawy**
