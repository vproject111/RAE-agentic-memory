# Experiment: Fix Warnings & Investigate Skipped Tests

**Date:** 2025-12-24
**Executor:** Gemini (Writer Role)
**Status:** Completed

## 1. Objective
- Fix 2 FastAPI DeprecationWarnings (`HTTP_422_UNPROCESSABLE_ENTITY`).
- Investigate 22 (found 14) skipped tests.
- Verify system stability via `make test-unit`.

## 2. Deprecation Warnings Analysis
- **Target:** `HTTP_422_UNPROCESSABLE_ENTITY` usage.
- **Method:** `grep -r`, `make test-unit` log analysis.
- **Findings:**
  - No usage of `HTTP_422_UNPROCESSABLE_ENTITY` found in `apps/` or `tests/`.
  - `apps/memory_api/main.py` uses hardcoded `422` and standard `FastAPI` patterns.
  - `make test-unit` produced **0 DeprecationWarnings**.
- **Conclusion:** The warnings appear to be already fixed or are not present in the unit test suite. No code changes required.

## 3. Skipped Tests Investigation
Total Skipped: **14** (from `make test-unit` output).

### Category A: E2E / Integration (3 Tests)
- **File:** `apps/memory_api/tests/test_api_e2e.py`
- **Reason:** Requires full infrastructure (API + DB + Vector Store) running.
- **Action:** Retain skip. These should be run in a dedicated E2E pipeline, not unit tests.

### Category B: OpenTelemetry / Complex Mocking (5 Tests)
- **File:** `apps/memory_api/tests/test_opentelemetry.py`
- **Reason:** "Complex mocking - tested in integration".
- **Action:** Retain skip. Tracing logic is better tested in integration.

### Category C: Architecture & Technical Debt (6 Tests)
- **File:** `tests/architecture/test_architecture.py`
- **Failures (Skipped to Green):**
  1. `test_models_dont_import_services`: Import violation in `models/rbac.py`.
  2. `test_file_size_limits`: `core/graph_operator.py` is 868 lines (limit 800).
  3. `test_function_complexity`: `observability/memory_tracing.py:332` is too complex.
  4. `test_tests_mirror_source_structure`: Structure mismatch in `tests/api`.
  5. `test_no_hardcoded_secrets`: Possible secret in `observability/rae_telemetry_schema.py`.
  6. `test_services_use_dependency_injection`: DI violation in `rae_core_service.py`.
- **Action:** These represent **Technical Debt**. They should be addressed in the "Weekly Deep Refactor".

### Category D: Performance (Missing)
- **Status:** `pytest-benchmark` is not installed, so `test_performance.py` tests are likely deselected or silently skipped (not counted in the 14).
- **Recommendation:** Add `pytest-benchmark` to `requirements-dev.txt` if performance baselining is needed in this env.

## 4. Summary & Recommendations
- **System Health:** 890 Tests Passed. Green.
- **Warnings:** Clean.
- **Delegation:** This analysis serves as the "Writer" output for Node1.
- **Next Steps:**
  - Schedule refactoring for `graph_operator.py` and `memory_tracing.py`.
  - Create a task to fix the architecture violations.
