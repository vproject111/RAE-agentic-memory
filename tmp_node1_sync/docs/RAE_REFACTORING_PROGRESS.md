# RAE Refactoring Progress Tracker

**Started:** Not yet started
**Last Updated:** 2025-12-10
**Status:** READY_TO_START

---

## Iteracja 1: Normalizacja Nazewnictwa
- **Status:** NOT_STARTED
- **Branch:** fix/rae-naming-normalization
- **Estimated Time:** 1h
- **CI develop:** PENDING
- **Commit:** -
- **Started:** -
- **Completed:** -
- **Notes:** -

### Subtasks
- [ ] Audit struktury katalogów i importów
- [ ] Ustandaryzuj nazewnictwo (rae_core wszędzie)
- [ ] Napraw importy w apps/memory_api/
- [ ] Napraw importy w rae-lite/
- [ ] Zaktualizuj pyproject.toml, requirements.txt
- [ ] Zaktualizuj CI/CD workflows
- [ ] Weryfikacja: brak importów "rae-core"
- [ ] Testy: import rae_core działa
- [ ] Testy: pytest rae_core/tests/

---

## Iteracja 2: Podstawowe Komponenty
- **Status:** NOT_STARTED
- **Branch:** feat/rae-core-complete-base
- **Estimated Time:** 2h
- **CI develop:** PENDING
- **Commit:** -
- **Started:** -
- **Completed:** -
- **Notes:** -

### Subtasks
- [ ] Dodaj py.typed
- [ ] Dodaj version.py
- [ ] Uzupełnij models/search.py
- [ ] Uzupełnij models/context.py
- [ ] Uzupełnij models/scoring.py
- [ ] Uzupełnij models/sync.py
- [ ] Uzupełnij math/controller.py
- [ ] Uzupełnij math/metrics.py
- [ ] Uzupełnij context/window.py
- [ ] Uzupełnij scoring/decay.py
- [ ] Testy: wszystkie importy działają
- [ ] Testy: pytest rae_core/tests/test_models/
- [ ] Testy: pytest rae_core/tests/test_math/

---

## Iteracja 3: Interfejsy i Search
- **Status:** NOT_STARTED
- **Branch:** feat/rae-core-interfaces-search
- **Estimated Time:** 2h
- **CI develop:** PENDING
- **Commit:** -
- **Started:** -
- **Completed:** -
- **Notes:** -

### Subtasks
- [ ] Dodaj interfaces/storage.py
- [ ] Dodaj interfaces/vector.py
- [ ] Dodaj interfaces/graph.py
- [ ] Dodaj interfaces/cache.py
- [ ] Dodaj interfaces/llm.py
- [ ] Dodaj interfaces/embedding.py
- [ ] Dodaj interfaces/sync.py
- [ ] Dodaj search/strategies/vector.py
- [ ] Dodaj search/strategies/graph.py
- [ ] Dodaj search/strategies/sparse.py
- [ ] Dodaj search/strategies/fulltext.py
- [ ] Dodaj search/cache.py
- [ ] Testy: mypy rae_core/rae_core/interfaces/ --strict
- [ ] Testy: pytest rae_core/tests/test_interfaces/
- [ ] Testy: pytest rae_core/tests/test_search/

---

## Iteracja 4: LLM i Reflection
- **Status:** NOT_STARTED
- **Branch:** feat/rae-core-llm-reflection
- **Estimated Time:** 2h
- **CI develop:** PENDING
- **Commit:** -
- **Started:** -
- **Completed:** -
- **Notes:** -

### Subtasks
- [ ] Stwórz katalog llm/
- [ ] Dodaj llm/orchestrator.py
- [ ] Dodaj llm/strategies.py
- [ ] Dodaj llm/fallback.py (rule-based, no API)
- [ ] Dodaj llm/config.py
- [ ] Dodaj reflection/actor.py
- [ ] Dodaj reflection/evaluator.py
- [ ] Dodaj reflection/reflector.py
- [ ] Zaktualizuj reflection/engine.py
- [ ] Test: NoLLMFallback działa bez API
- [ ] Testy: pytest rae_core/tests/test_llm/
- [ ] Testy: pytest rae_core/tests/test_reflection/

---

## Iteracja 5: Config i Sync
- **Status:** NOT_STARTED
- **Branch:** feat/rae-core-config-sync
- **Estimated Time:** 2h
- **CI develop:** PENDING
- **Commit:** -
- **Started:** -
- **Completed:** -
- **Notes:** -

### Subtasks
- [ ] Stwórz katalog config/
- [ ] Dodaj config/settings.py (pydantic-settings)
- [ ] Dodaj config/defaults.py
- [ ] Stwórz katalog sync/
- [ ] Dodaj sync/protocol.py
- [ ] Dodaj sync/diff.py
- [ ] Dodaj sync/merge.py (CRDT)
- [ ] Dodaj sync/encryption.py (E2E)
- [ ] Zaktualizuj engine.py (integracja settings)
- [ ] Test: RAESettings wczytuje env vars
- [ ] Test: encryption encrypt/decrypt działa
- [ ] Testy: pytest rae_core/tests/test_sync/

---

## Iteracja 6: RAE-Server Migration
- **Status:** NOT_STARTED
- **Branch:** feat/rae-server-full-migration
- **Estimated Time:** 3h
- **CI develop:** PENDING
- **Commit:** -
- **Started:** -
- **Completed:** -
- **Notes:** -

### Subtasks
- [ ] Utwórz MIGRATION_PLAN.md
- [ ] Migruj routers/memory.py do rae_core
- [ ] Migruj routers/search.py do rae_core
- [ ] Migruj routers/reflection.py do rae_core
- [ ] Oznacz stare services jako @deprecated
- [ ] Dodaj logging warnings dla deprecated
- [ ] Zaktualizuj testy: używaj rae_core
- [ ] Usuń testy deprecated komponentów
- [ ] Utwórz API_MIGRATION_GUIDE.md
- [ ] Utwórz RAE_CORE_INTEGRATION.md
- [ ] Test: v1 API działa z rae_core
- [ ] Test: v2 API działa
- [ ] Testy: pytest apps/memory_api/tests/ -v

---

## Final Merge to main
- **Status:** NOT_STARTED
- **Prerequisites:** All 6 iterations completed with CI green on develop
- **CI main:** PENDING
- **Merge commit:** -
- **Started:** -
- **Completed:** -
- **Notes:** -

### Checklist
- [ ] All 6 iterations completed
- [ ] All develop CI runs successful
- [ ] git checkout main
- [ ] git merge develop --no-edit
- [ ] git push origin main
- [ ] gh run watch --branch main
- [ ] Main CI successful
- [ ] Verification tests pass
- [ ] Documentation updated
- [ ] READY FOR PHASE 5 (RAE-Sync)

---

## Summary Statistics

- **Total Iterations:** 6
- **Completed:** 0
- **In Progress:** 0
- **Failed:** 0
- **Pending:** 6
- **Overall Progress:** 0%
- **Estimated Total Time:** 12h
- **Actual Time Spent:** 0h

---

## Execution Log

### Session 1 - 2025-12-10
- Plan created
- Status: READY_TO_START
- Next action: Begin Iteracja 1 in new session

---

**Instructions for Next Session:**

1. Read this file to understand current progress
2. Read `docs/RAE_REFACTORING_FIX_PLAN.md` for detailed instructions
3. Start with first NOT_STARTED iteration
4. Update this file after each step
5. Follow workflow strictly: develop → CI → next iteration
6. Update statistics and logs
7. Do NOT skip ahead - complete each iteration fully

**Status Codes:**
- NOT_STARTED: Not begun
- IN_PROGRESS: Currently working on
- COMPLETED: Done and CI passed
- FAILED: Encountered errors, needs retry
- BLOCKED: Waiting on dependencies
