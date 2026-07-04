# RAE CI Quality Implementation Plan

## Kompleksowy, Iteracyjny Plan Wdrożenia CI Quality Governance

**Dokument:** RAE-CI-QUALITY-IMPLEMENTATION-PLAN.md
**Wersja:** 1.0
**Data:** 2025-12-08
**Projekt:** RAE-agentic-memory
**Bazuje na:** RAE-CI-QUALITY-SPEC.md, RAE-CI-QUALITY-SPEC-enterprise-v2.0.md, AGENT_TESTING_GUIDE.md

---

## Executive Summary

Ten dokument zawiera kompletny, wykonalny plan wdrożenia systemu CI Quality Governance dla projektu RAE w 4 iteracjach:

| Iteracja | Czas | Story Points | Główne Deliverables |
|----------|------|--------------|---------------------|
| 1. Zero Warnings | 3 dni | 9 SP | pytest -W error, warning-check job, branch protection |
| 2. Zero Flake | 5 dni | 18 SP | Flaky detection, tests/quarantine/, tickets |
| 3. Zero Drift | 7 dni | 24 SP | Metrics snapshots, SLO enforcement, OTel integration |
| 4. Auto-Healing | 9 dni | 30 SP | AI fix generator, auto-PR, human-in-the-loop |
| **TOTAL** | **24 dni** | **81 SP** | Enterprise-grade CI/CD quality system |

---

## Spis Treści

1. [Kontekst i Stan Obecny](#kontekst-i-stan-obecny)
2. [Architektura Docelowa](#architektura-docelowa)
3. [Iteracja 1: Zero Warnings](#iteracja-1-zero-warnings)
4. [Iteracja 2: Zero Flake](#iteracja-2-zero-flake)
5. [Iteracja 3: Zero Drift](#iteracja-3-zero-drift)
6. [Iteracja 4: Auto-Healing CI](#iteracja-4-auto-healing-ci)
7. [Struktura Katalogów](#struktura-katalogów)
8. [Implementation Checklist](#implementation-checklist)
9. [Diagram Przepływu](#diagram-przepływu)

---

## Kontekst i Stan Obecny

### Analiza Istniejących Zasobów

| Kategoria | Stan | Lokalizacja |
|-----------|------|-------------|
| **Workflow CI** | Zaawansowany (10 jobs) | `.github/workflows/ci.yml` (1014 linii) |
| **pytest.ini** | Skonfigurowany | `/pytest.ini` |
| **Warnings removal** | ✅ 100% done | `docs/testing/WARNING_REMOVAL_PLAN.md` |
| **Flaky detection** | Szkielet | `scripts/detect_flaky_tests.py` |
| **Benchmark comparison** | ✅ Działający | `benchmarking/scripts/compare_runs.py` |
| **OpenTelemetry** | ✅ Skonfigurowany | `apps/memory_api/observability/opentelemetry_config.py` |
| **AI Code Review** | ✅ Działający | `scripts/ai_code_review.py`, `.github/workflows/ai-code-review.yml` |
| **Metrics Reference** | ✅ Kompletny | `benchmarking/results/metrics_reference.json` |

### Istniejące Joby CI

Z analizy `.github/workflows/ci.yml`:

1. `test-quick` - Smart selection dla feature branches
2. `test-full` - Pełny test suite (Python 3.10, 3.11, 3.12)
3. `test-mcp` - MCP integration tests
4. `benchmark-smoke` - Benchmark smoke test
5. `lint` - black, isort, ruff, mypy
6. `quality-gate` - Dokumentacja, security checks
7. `security` - safety, bandit
8. `docs-update` - Auto-update dokumentacji
9. `docker` - Build Docker images
10. `publish` - Publish do GHCR

---

## Architektura Docelowa

```mermaid
flowchart TD
    subgraph "Pillar 1: Zero Warnings"
        A[Commit/PR] --> B[pytest -W error]
        B --> C{Warnings?}
        C -->|YES| D[Block Merge]
        C -->|NO| E[Pass]
    end

    subgraph "Pillar 2: Zero Flake"
        E --> F[Run Tests 3x]
        F --> G{Inconsistent?}
        G -->|YES| H[Move to Quarantine]
        G -->|NO| I[Pass]
    end

    subgraph "Pillar 3: Zero Drift"
        I --> J[Collect Metrics]
        J --> K[Compare vs Baseline]
        K --> L{Regression > SLO?}
        L -->|YES| M[Block + Alert]
        L -->|NO| N[Pass]
    end

    subgraph "Pillar 4: Auto-Healing"
        D --> O[Generate Context]
        H --> O
        M --> O
        O --> P[AI Agent via Broker]
        P --> Q[Create PR with Fix]
        Q --> R[Human Review]
        R -->|Approve| A
    end
```

---

## Iteracja 1: Zero Warnings

**Status:** ✅ Częściowo ukończone (237 warningów naprawionych)
**Pozostało:** Wymuszenie `-W error` w CI, filtrowanie external warnings, blokada merge

**Priorytet:** P0 - KRYTYCZNE
**Effort:** 3 dni (9 SP)

### 1.1 Cele i Deliverables

| Cel | Deliverable | Plik | Priorytet |
|-----|-------------|------|-----------|
| Wymuszenie `-W error` | Zmodyfikowany `ci.yml` | `.github/workflows/ci.yml` | P0 |
| Filtrowanie external warnings | Rozszerzony `pytest.ini` | `pytest.ini` | P0 |
| Automatyczna detekcja nowych | Nowy job `warning-check` | `.github/workflows/ci.yml` | P1 |
| Nowy skrypt detekcji | check_new_warnings.py | `scripts/ci/check_new_warnings.py` | P0 |
| Blokada merge | Branch protection rule | GitHub Settings | P0 |

### 1.2 Wymagane Zmiany w CI/CD

**Plik:** `.github/workflows/ci.yml`

Dodać do job `test-full` (około linii 244):

```yaml
- name: Run ALL unit tests with warnings as errors
  env:
    DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_rae
    REDIS_URL: redis://localhost:6379/0
    QDRANT_URL: http://localhost:6333
    RAE_VECTOR_BACKEND: qdrant
    PYTHONWARNINGS: error
  run: |
    echo "Running FULL test suite with -W error..."
    pytest -W error \
      -W "ignore::DeprecationWarning:google._upb._message" \
      -W "ignore::ResourceWarning:tldextract" \
      -W "ignore::DeprecationWarning:spacy.cli._util" \
      -m "not integration and not llm and not contract and not performance" \
      --cov --cov-report=xml --cov-report=term
```

Dodać nowy job na końcu pliku:

```yaml
warning-check:
  name: Warning Detection
  runs-on: ubuntu-latest
  needs: [test-full]

  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: pip install -r requirements-dev.txt

    - name: Check for new warnings
      run: |
        pytest -W default --tb=no -q 2>&1 | tee warnings.log
        python scripts/ci/check_new_warnings.py warnings.log
```

### 1.3 Nowe Narzędzia/Skrypty

**Plik:** `scripts/ci/check_new_warnings.py` (NOWY)

```python
#!/usr/bin/env python3
"""
Check for new warnings in test output.
Exit 1 if unknown warnings detected.

Part of RAE CI Quality Implementation - Iteration 1: Zero Warnings
"""
import sys
import re
from pathlib import Path

KNOWN_EXTERNAL_WARNINGS = [
    r"google\._upb\._message",
    r"tldextract.*socket",
    r"spacy\.cli\._util",
    r"Can't initialize NVML",
]

def main():
    if len(sys.argv) < 2:
        print("Usage: check_new_warnings.py <warnings.log>")
        sys.exit(2)

    log_file = Path(sys.argv[1])
    content = log_file.read_text()

    # Find all warnings
    warning_pattern = r"(.*Warning.*|.*DeprecationWarning.*)"
    warnings = re.findall(warning_pattern, content, re.IGNORECASE)

    unknown_warnings = []
    for w in warnings:
        is_known = any(re.search(pattern, w) for pattern in KNOWN_EXTERNAL_WARNINGS)
        if not is_known and "RAE" not in w and "apps/" in w:
            unknown_warnings.append(w)

    if unknown_warnings:
        print(f"❌ UNKNOWN WARNINGS DETECTED ({len(unknown_warnings)}):")
        for w in unknown_warnings[:10]:
            print(f"  - {w}")
        sys.exit(1)

    print("✅ No new warnings detected")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### 1.4 Zmiany w pytest.ini

**Plik:** `pytest.ini`

Dodać/zaktualizować sekcję `filterwarnings`:

```ini
[pytest]
# ... istniejąca konfiguracja ...

filterwarnings =
    error
    # External library warnings (udokumentowane, nie można naprawić)
    # [EXTERNAL] google-protobuf: deprecated in Python 3.14
    ignore::DeprecationWarning:google._upb._message
    # [EXTERNAL] tldextract: ResourceWarning socket
    ignore::ResourceWarning:tldextract
    # [EXTERNAL] spacy: Click parser deprecated
    ignore::DeprecationWarning:spacy.cli._util
    # [EXTERNAL] torch: NVML not available (CPU-only environment)
    ignore:Can't initialize NVML:UserWarning
```

### 1.5 Branch Protection Rules

**GitHub Settings → Branches → Branch protection rules**

Dla `main`:
- ✅ Require status checks to pass before merging
  - `Full Test (Python 3.12)`
  - `Warning Detection` (NOWY)
  - `Lint`
- ✅ Require pull request reviews before merging (1 approval)

Dla `develop`:
- ✅ Require status checks to pass before merging
  - `Full Test (Python 3.12)`
  - `Warning Detection` (NOWY)

### 1.6 Kryteria Sukcesu

| Kryterium | Metryka | Target | Weryfikacja |
|-----------|---------|--------|-------------|
| Zero warnings w testach | `pytest -W error` pass | 100% | CI green |
| CI blokuje merge z warning | Job `warning-check` fail | Aktywne | Manual test |
| Dokumentacja filtrów | Komentarze w pytest.ini | 100% | Code review |
| External warnings filtrowane | Known warnings suppressed | 100% | Logs check |

### 1.7 Szacowany Effort

| Zadanie | Story Points | Dni | Właściciel |
|---------|--------------|-----|------------|
| Modyfikacja ci.yml | 2 | 0.5 | Dev |
| check_new_warnings.py | 3 | 1 | Dev |
| pytest.ini filters | 1 | 0.5 | Dev |
| Branch protection | 1 | 0.25 | Admin |
| Testowanie | 2 | 0.5 | QA |
| **TOTAL** | **9 SP** | **~3 dni** | |

### 1.8 Ryzyko i Mitigation

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|--------|-------------------|--------|------------|
| External lib warning breaking build | Średnie | Wysokie | Dodać do filterwarnings z komentarzem |
| False positives w detekcji | Niskie | Średnie | Whitelista znanych warningów |
| Blokada merge przez stare warnings | Niskie | Niskie | Warningi już usunięte (237 done) |
| CI timeout przez strict checks | Niskie | Średnie | Monitoring, timeout adjustments |

### 1.9 Dependencies

- **Wymagane przed startem:** ✅ `docs/testing/WARNING_REMOVAL_PLAN.md` (DONE)
- **Zależy od:** Brak
- **Blokuje:** Iterację 2 (Zero Flake)

---

## Iteracja 2: Zero Flake

**Status:** ⏳ Do zrobienia (szkielet istnieje: `scripts/detect_flaky_tests.py`)
**Cel:** System detekcji, kwarantanny i naprawy flaky tests

**Priorytet:** P1 - WYSOKIE
**Effort:** 5 dni (18 SP)

### 2.1 Cele i Deliverables

| Cel | Deliverable | Plik | Priorytet |
|-----|-------------|------|-----------|
| Automatyczna detekcja flaky | Rozszerzony skrypt | `scripts/ci/analyze_flaky_tests.py` | P0 |
| Katalog kwarantanny | Struktura testów | `tests/quarantine/` | P0 |
| Job CI wielokrotnego uruchomienia | Nowy job | `.github/workflows/ci.yml` | P1 |
| Raportowanie | JSON artifact | `flaky_report.json` | P1 |
| Marker pytest | Nowy marker | `pytest.ini` | P1 |
| Skrypt przenoszenia do kwarantanny | quarantine_test.py | `scripts/ci/quarantine_test.py` | P0 |

### 2.2 Wymagane Zmiany w CI/CD

**Plik:** `.github/workflows/ci.yml`

Dodać nowy job (uruchamiany nightly lub on-demand):

```yaml
flaky-detection:
  name: Flaky Test Detection
  runs-on: ubuntu-latest
  if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[flaky-check]')

  services:
    postgres:
      image: ankane/pgvector:latest
      env:
        POSTGRES_PASSWORD: postgres
        POSTGRES_USER: postgres
        POSTGRES_DB: test_rae
      ports:
        - 5432:5432
    redis:
      image: redis:7-alpine
      ports:
        - 6379:6379
    qdrant:
      image: qdrant/qdrant:latest
      ports:
        - 6333:6333

  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt
        pip install pytest-json-report

    - name: Run tests multiple times
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_rae
        REDIS_URL: redis://localhost:6379/0
        QDRANT_URL: http://localhost:6333
      run: |
        mkdir -p .flaky-reports
        for i in 1 2 3; do
          echo "Run $i/3..."
          pytest -m "not integration and not llm" \
            --json-report \
            --json-report-file=.flaky-reports/run_$i.json \
            --tb=no -q || true
        done

    - name: Analyze flakiness
      run: |
        python scripts/ci/analyze_flaky_tests.py \
          .flaky-reports/run_1.json \
          .flaky-reports/run_2.json \
          .flaky-reports/run_3.json \
          --output flaky_report.json

    - name: Upload flaky report
      uses: actions/upload-artifact@v4
      with:
        name: flaky-report
        path: flaky_report.json
        retention-days: 30

    - name: Fail if flaky tests found
      run: |
        if [ -f "flaky_report.json" ]; then
          FLAKY_COUNT=$(jq '.flaky_tests | length' flaky_report.json)
          if [ "$FLAKY_COUNT" -gt 0 ]; then
            echo "❌ Found $FLAKY_COUNT flaky tests!"
            jq '.flaky_tests' flaky_report.json
            exit 1
          fi
        fi
```

Dodać schedule trigger na górze pliku:

```yaml
on:
  # ... existing triggers ...
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
```

### 2.3 Nowe Narzędzia/Skrypty

**Plik:** `scripts/ci/analyze_flaky_tests.py` (NOWY)

```python
#!/usr/bin/env python3
"""
Enhanced flaky test analyzer.
Analyzes multiple pytest-json-report outputs to detect inconsistent tests.

Part of RAE CI Quality Implementation - Iteration 2: Zero Flake
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict


def load_reports(files: List[str]) -> List[Dict]:
    """Load pytest-json-report JSON files."""
    reports = []
    for f in files:
        with open(f) as fp:
            reports.append(json.load(fp))
    return reports


def analyze_flakiness(reports: List[Dict], min_runs: int = 3) -> Dict:
    """Analyze test outcomes across runs."""
    outcomes = defaultdict(list)

    for report in reports:
        for test in report.get("tests", []):
            nodeid = test.get("nodeid", "unknown")
            outcome = test.get("outcome", "unknown")
            duration = test.get("duration", 0)
            outcomes[nodeid].append({
                "outcome": outcome,
                "duration": duration
            })

    flaky_tests = []
    stable_tests = []

    for nodeid, runs in outcomes.items():
        if len(runs) < min_runs:
            continue

        run_outcomes = [r["outcome"] for r in runs]

        # Test is flaky if it has different outcomes
        if len(set(run_outcomes)) > 1:
            pass_rate = run_outcomes.count("passed") / len(run_outcomes)
            avg_duration = sum(r["duration"] for r in runs) / len(runs)

            flaky_tests.append({
                "nodeid": nodeid,
                "outcomes": run_outcomes,
                "pass_rate": round(pass_rate, 2),
                "avg_duration_seconds": round(avg_duration, 3),
                "recommendation": get_recommendation(nodeid, run_outcomes, avg_duration)
            })
        else:
            stable_tests.append(nodeid)

    return {
        "total_tests": len(outcomes),
        "flaky_tests": sorted(flaky_tests, key=lambda x: x["pass_rate"]),
        "stable_tests_count": len(stable_tests),
        "analysis_runs": len(reports)
    }


def get_recommendation(nodeid: str, outcomes: List[str], duration: float) -> str:
    """Generate fix recommendation based on failure pattern."""
    pass_rate = outcomes.count("passed") / len(outcomes)

    if duration > 5.0:
        return "Consider adding timeout or async wait - long-running test"
    if pass_rate < 0.5:
        return "Test fails frequently - likely timing/race condition issue"
    if "async" in nodeid.lower() or "integration" in nodeid.lower():
        return "Async test - add explicit waits or increase timeouts"
    return "Review for non-deterministic behavior (random, time, external deps)"


def main():
    parser = argparse.ArgumentParser(description="Analyze flaky tests")
    parser.add_argument("reports", nargs="+", help="pytest-json-report files")
    parser.add_argument("--output", "-o", default="flaky_report.json")
    parser.add_argument("--min-runs", type=int, default=3)

    args = parser.parse_args()

    reports = load_reports(args.reports)
    result = analyze_flakiness(reports, args.min_runs)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ Analysis complete: {len(result['flaky_tests'])} flaky tests found")
    print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()
```

**Plik:** `scripts/ci/quarantine_test.py` (NOWY)

```python
#!/usr/bin/env python3
"""
Move flaky test to quarantine directory.

Usage:
  python quarantine_test.py tests/api/v1/test_cache.py::test_flaky_function

Part of RAE CI Quality Implementation - Iteration 2: Zero Flake
"""
import argparse
import shutil
from pathlib import Path
from datetime import datetime


def quarantine_test(nodeid: str, reason: str = "flaky"):
    """Move test to quarantine based on nodeid."""
    # Parse nodeid: tests/api/v1/test_cache.py::test_function
    parts = nodeid.split("::")
    file_path = Path(parts[0])

    if not file_path.exists():
        print(f"❌ Error: {file_path} not found")
        return False

    # Create quarantine directory mirroring original structure
    quarantine_base = Path("tests/quarantine")
    relative_path = file_path.relative_to("tests") if file_path.is_relative_to("tests") else file_path
    quarantine_path = quarantine_base / relative_path.parent
    quarantine_path.mkdir(parents=True, exist_ok=True)

    # Copy file to quarantine
    target = quarantine_path / file_path.name
    shutil.copy(file_path, target)

    # Add quarantine marker at the top
    content = target.read_text()
    marker = f'''"""
QUARANTINED: {reason}
Original: {file_path}
Nodeid: {nodeid}
Date: {datetime.now().isoformat()}

This test has been identified as flaky and moved to quarantine.
See tests/quarantine/README.md for fixing guidelines.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Quarantined flaky test - {reason}")

'''
    target.write_text(marker + content)

    print(f"✅ Test quarantined: {target}")
    print(f"📝 Next step: Create ticket to fix and move back to main suite")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("nodeid", help="Test nodeid to quarantine")
    parser.add_argument("--reason", default="flaky", help="Quarantine reason")
    args = parser.parse_args()

    success = quarantine_test(args.nodeid, args.reason)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

### 2.4 Struktura Testów - Kwarantanna

**Katalog:** `tests/quarantine/` (NOWY)

```
tests/
  quarantine/           # NOWY
    __init__.py
    README.md           # Dokumentacja procesu
    api/
      v1/
        # Przeniesione flaky testy
    services/
      # Przeniesione flaky testy
```

**Plik:** `tests/quarantine/README.md` (NOWY)

```markdown
# Test Quarantine Directory

This directory contains tests that have been identified as flaky and are
temporarily excluded from the main test suite.

## Why Quarantine?

Flaky tests (tests with non-deterministic outcomes) reduce CI reliability
and make it harder to trust test results. Instead of ignoring them, we:

1. Move them to quarantine
2. Mark them with `@pytest.mark.skip`
3. Create a ticket to fix them
4. Once fixed, move them back to the main suite

## Flaky Test Lifecycle

```
Detection → Analysis → Quarantine → Fix → Verification → Restore
```

### Detection
- Automated via `flaky-detection` CI job
- Runs tests 3x and compares outcomes
- Generates `flaky_report.json`

### Quarantine
```bash
python scripts/ci/quarantine_test.py tests/path/to/test.py::test_name
```

### Fix
1. Run locally multiple times:
   ```bash
   for i in {1..10}; do pytest tests/quarantine/path/to/test.py -v; done
   ```

2. Common fixes:
   - **Timing issues:** Add explicit waits (`time.sleep()`, `await asyncio.sleep()`)
   - **Race conditions:** Add locks, synchronization
   - **External deps:** Mock them (`@patch`, `monkeypatch`)
   - **Random data:** Add seed (`random.seed(42)`)
   - **Time-based:** Use `freezegun` to freeze time

3. Verify stability (10+ consecutive passes)

### Restore
```bash
mv tests/quarantine/path/to/test.py tests/path/to/test.py
# Remove quarantine marker from file
# Open PR with fix
```

## SLA

Per RAE-CI-QUALITY-SPEC-enterprise-v2.0.md:
- **SLA-2:** Every flaky test in main → fix or quarantine within 5 working days

## Running Quarantined Tests

```bash
# Run all quarantined tests (for debugging)
pytest tests/quarantine/ -v

# Check which tests are quarantined
find tests/quarantine -name "test_*.py"

# Run specific quarantined test
pytest tests/quarantine/api/v1/test_cache.py::test_flaky -v
```

## Current Status

See `flaky_report.json` artifact in latest `flaky-detection` CI run.
```

### 2.5 Konfiguracja pytest.ini

**Plik:** `pytest.ini`

Dodać nowe markery:

```ini
[pytest]
# ... existing config ...

markers =
    # ... existing markers ...
    flaky: marks tests as flaky (excluded from main run)
    quarantine: marks tests in quarantine (skipped by default)

# Exclude quarantine from default runs
testpaths =
    apps/memory_api/tests
    integrations/context-watcher/tests
    tests
    test_enterprise_features.py
    # NOTE: tests/quarantine is NOT included by default
```

### 2.6 Kryteria Sukcesu

| Kryterium | Metryka | Target | Weryfikacja |
|-----------|---------|--------|-------------|
| Zero flaky w main suite | `flaky-detection` job pass | 100% | Nightly CI |
| Flaky detection accuracy | False positive rate | < 5% | Manual review |
| Time to quarantine | Od wykrycia do przeniesienia | < 1 dzień | Process metrics |
| Quarantine backlog | Liczba testów w quarantine | < 10 | Weekly check |
| Fix rate | Quarantine → restored per week | >= 2 | GitHub metrics |

### 2.7 Szacowany Effort

| Zadanie | Story Points | Dni | Właściciel |
|---------|--------------|-----|------------|
| analyze_flaky_tests.py | 5 | 1.5 | Dev |
| quarantine_test.py | 3 | 1 | Dev |
| flaky-detection job | 5 | 1.5 | DevOps |
| tests/quarantine struktura | 2 | 0.5 | Dev |
| pytest.ini markers | 1 | 0.25 | Dev |
| Dokumentacja (README.md) | 2 | 0.5 | Tech Writer |
| **TOTAL** | **18 SP** | **~5 dni** | |

### 2.8 Ryzyko i Mitigation

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|--------|-------------------|--------|------------|
| False positive flaky detection | Średnie | Średnie | Min 3 runs, manual review before quarantine |
| Quarantine backlog growth | Średnie | Wysokie | Weekly review, P1 tickets per flaky |
| CI timeout z 3x run | Niskie | Średnie | Run only subset, schedule nightly |
| Flaky tests maskują real bugs | Niskie | Wysokie | Quarantine analysis, not just skip |

### 2.9 Dependencies

- **Wymagane przed startem:** ✅ Iteracja 1 (Zero Warnings)
- **Zewnętrzne:** `pytest-json-report` package
- **Blokuje:** Iterację 3 (Zero Drift)

---

## Iteracja 3: Zero Drift

**Status:** ⏳ Do zrobienia (częściowo istniejące: benchmark system, metrics_reference.json)
**Cel:** Automatyczna detekcja regresji wydajności, pamięci, logów z SLO

**Priorytet:** P1 - WYSOKIE
**Effort:** 7 dni (24 SP)

### 3.1 Cele i Deliverables

| Cel | Deliverable | Plik | Priorytet |
|-----|-------------|------|-----------|
| Snapshoty metryk | JSON snapshots | `ci/metrics_snapshot.json` | P0 |
| Porównanie z baseline | Rozszerzony compare | `scripts/ci/collect_metrics.py` | P0 |
| SLO enforcement | Checker | `scripts/ci/check_slo.py` | P0 |
| Konfiguracja SLO | YAML config | `ci/slo_config.yaml` | P0 |
| OpenTelemetry dla math/reflective | Rozszerzone metryki | `benchmarking/math_metrics/` | P1 |
| Dashboard metryk | Artifact + summary | `drift_report.md` | P1 |
| Job CI | drift-detection | `.github/workflows/ci.yml` | P0 |

### 3.2 SLO/SLA z Dokumentacji

Z `docs/RAE-CI-QUALITY-SPEC-enterprise-v2.0.md`:

| Obszar | SLO (cel) | SLA (zobowiązanie) | Plik Config |
|--------|-----------|-------------------|-------------|
| Warnings | 0 w CI i testach | Naprawa w 3 dni | N/A (Iter 1) |
| Flaky tests | 0 w main | Naprawa/kwarantanna w 5 dni | N/A (Iter 2) |
| Drift wydajności | ≤ 5% wzrostu | P1 ticket w 7 dni | `ci/slo_config.yaml` |
| Logi WARNING/ERROR | 0 w testach | Natychmiastowy blok | `ci/slo_config.yaml` |
| Coverage (math+reflective) | ≥ 80% | - | `ci/slo_config.yaml` |
| API latency (p95) | ≤ 200ms | Wzrost > 20% = FAIL | `ci/slo_config.yaml` |
| Memory peak | ≤ 2GB | Wzrost > 10% = FAIL | `ci/slo_config.yaml` |

### 3.3 Wymagane Zmiany w CI/CD

**Plik:** `.github/workflows/ci.yml`

Dodać nowy job (na PR i merge do develop/main):

```yaml
drift-detection:
  name: Zero Drift Check
  runs-on: ubuntu-latest
  if: |
    github.event_name == 'pull_request' ||
    github.ref == 'refs/heads/develop' ||
    github.ref == 'refs/heads/main'
  needs: [test-full]

  services:
    postgres:
      image: ankane/pgvector:latest
      env:
        POSTGRES_PASSWORD: postgres
        POSTGRES_USER: postgres
        POSTGRES_DB: test_rae
      ports:
        - 5432:5432
    redis:
      image: redis:7-alpine
      ports:
        - 6379:6379
    qdrant:
      image: qdrant/qdrant:latest
      ports:
        - 6333:6333

  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Need full history for comparison

    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt
        pip install -r apps/memory_api/requirements-base.txt
        pip install memory-profiler pytest-timeout psutil

    - name: Collect performance metrics
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_rae
        REDIS_URL: redis://localhost:6379/0
        QDRANT_URL: http://localhost:6333
      run: |
        python scripts/ci/collect_metrics.py \
          --output metrics_current.json \
          --include-memory \
          --include-timing

    - name: Check against SLO
      run: |
        python scripts/ci/check_slo.py \
          --current metrics_current.json \
          --baseline benchmarking/results/metrics_reference.json \
          --slo-config ci/slo_config.yaml \
          --output drift_report.md

    - name: Upload metrics snapshot
      uses: actions/upload-artifact@v4
      with:
        name: metrics-snapshot-${{ github.sha }}
        path: metrics_current.json
        retention-days: 90

    - name: Upload drift report
      uses: actions/upload-artifact@v4
      with:
        name: drift-report
        path: drift_report.md
        retention-days: 30

    - name: Comment on PR with drift report
      if: github.event_name == 'pull_request' && always()
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          if (fs.existsSync('drift_report.md')) {
            const report = fs.readFileSync('drift_report.md', 'utf8');
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.payload.pull_request.number,
              body: report
            });
          }
```

### 3.4 Nowe Narzędzia/Skrypty

**Plik:** `scripts/ci/collect_metrics.py` (NOWY)

```python
#!/usr/bin/env python3
"""
Collect performance metrics for drift detection.
Integrates with existing benchmarking infrastructure.

Part of RAE CI Quality Implementation - Iteration 3: Zero Drift
"""
import argparse
import json
import time
import subprocess
import psutil
from datetime import datetime
from pathlib import Path


def collect_test_timing():
    """Run tests and collect timing metrics."""
    print("📊 Collecting timing metrics...")
    start = time.time()
    result = subprocess.run(
        ["pytest", "-m", "not integration and not llm",
         "--tb=no", "-q", "--durations=50"],
        capture_output=True,
        text=True
    )
    duration = time.time() - start

    # Parse slowest tests from durations output
    slowest_tests = []
    for line in result.stdout.split("\n"):
        if "s call" in line:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    test_duration = float(parts[0].replace("s", ""))
                    slowest_tests.append({
                        "test": parts[-1],
                        "duration": test_duration
                    })
                except (ValueError, IndexError):
                    pass

    return {
        "total_duration_seconds": round(duration, 2),
        "slowest_tests": slowest_tests[:10],
        "test_count": result.stdout.count("passed") + result.stdout.count("failed")
    }


def collect_memory_metrics():
    """Collect memory usage during test run."""
    print("💾 Collecting memory metrics...")
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    subprocess.run(
        ["pytest", "-m", "not integration and not llm",
         "--tb=no", "-q", "-x"],
        capture_output=True
    )

    mem_after = process.memory_info().rss / 1024 / 1024
    mem_peak = process.memory_info().peak_wset / 1024 / 1024 if hasattr(
        process.memory_info(), 'peak_wset') else mem_after

    return {
        "memory_before_mb": round(mem_before, 2),
        "memory_after_mb": round(mem_after, 2),
        "memory_peak_mb": round(mem_peak, 2),
        "memory_delta_mb": round(mem_after - mem_before, 2)
    }


def collect_log_metrics():
    """Collect log level counts from test run."""
    print("📝 Collecting log metrics...")
    result = subprocess.run(
        ["pytest", "-m", "not integration and not llm",
         "--tb=no", "-q", "-s"],
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    # Count log levels (exclude pytest markers like "error::")
    warning_count = output.lower().count("warning")
    error_count = output.lower().count("error") - output.lower().count("error::")
    critical_count = output.lower().count("critical")

    return {
        "warning_count": warning_count,
        "error_count": error_count,
        "critical_count": critical_count,
        "log_volume_lines": len(output.split("\n"))
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="metrics_current.json")
    parser.add_argument("--include-memory", action="store_true")
    parser.add_argument("--include-timing", action="store_true")
    args = parser.parse_args()

    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "git_sha": subprocess.getoutput("git rev-parse HEAD"),
        "git_branch": subprocess.getoutput("git rev-parse --abbrev-ref HEAD"),
        "collector_version": "1.0.0"
    }

    metrics["timing"] = collect_test_timing()

    if args.include_memory:
        metrics["memory"] = collect_memory_metrics()

    metrics["logs"] = collect_log_metrics()

    with open(args.output, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"✅ Metrics saved to {args.output}")


if __name__ == "__main__":
    main()
```

**Plik:** `scripts/ci/check_slo.py` (NOWY)

```python
#!/usr/bin/env python3
"""
Check metrics against SLO thresholds.
Generates drift_report.md with results.

Part of RAE CI Quality Implementation - Iteration 3: Zero Drift
"""
import argparse
import json
import yaml
from pathlib import Path


def load_slo_config(path: str) -> dict:
    """Load SLO configuration."""
    with open(path) as f:
        return yaml.safe_load(f)


def check_slo(current: dict, baseline: dict, slo: dict) -> dict:
    """Compare current metrics against baseline with SLO thresholds."""
    results = {
        "status": "PASS",
        "violations": [],
        "warnings": [],
        "metrics": {}
    }

    # Timing SLO
    if "timing" in current and "timing" in slo:
        current_duration = current["timing"]["total_duration_seconds"]
        # Get baseline from reference
        baseline_duration = baseline.get("reference_run", {}).get(
            "results", {}).get("duration_seconds", current_duration)
        threshold = slo["timing"].get("max_increase_percent", 10)

        increase = ((current_duration - baseline_duration) / baseline_duration * 100
                   if baseline_duration > 0 else 0)

        results["metrics"]["timing"] = {
            "current": current_duration,
            "baseline": baseline_duration,
            "increase_percent": round(increase, 2),
            "threshold_percent": threshold
        }

        if increase > threshold:
            results["violations"].append(
                f"Test duration increased by {increase:.1f}% (threshold: {threshold}%)")
            results["status"] = "FAIL"
        elif increase > threshold * 0.7:
            results["warnings"].append(
                f"Test duration approaching threshold: {increase:.1f}%")

    # Memory SLO
    if "memory" in current and "memory" in slo:
        current_mem = current["memory"]["memory_peak_mb"]
        max_mem = slo["memory"].get("max_peak_mb", 2048)

        results["metrics"]["memory"] = {
            "current_peak_mb": current_mem,
            "max_allowed_mb": max_mem
        }

        if current_mem > max_mem:
            results["violations"].append(
                f"Memory peak {current_mem}MB exceeds limit {max_mem}MB")
            results["status"] = "FAIL"

    # Log SLO
    if "logs" in current and "logs" in slo:
        for level in ["warning", "error", "critical"]:
            count = current["logs"].get(f"{level}_count", 0)
            max_allowed = slo["logs"].get(f"max_{level}", 0)

            results["metrics"][f"log_{level}"] = {
                "count": count,
                "max_allowed": max_allowed
            }

            if count > max_allowed:
                results["violations"].append(
                    f"{level.upper()} logs: {count} (max: {max_allowed})")
                results["status"] = "FAIL"

    return results


def generate_report(results: dict, current: dict) -> str:
    """Generate Markdown drift report."""
    status_emoji = "✅" if results["status"] == "PASS" else "❌"

    report = f"""## {status_emoji} Drift Detection Report

**Status:** {results['status']}
**Timestamp:** {current.get('timestamp', 'N/A')}
**Branch:** {current.get('git_branch', 'N/A')}
**SHA:** {current.get('git_sha', 'N/A')[:8]}

### Metrics Summary

| Metric | Current | Baseline | Delta | Threshold | Status |
|--------|---------|----------|-------|-----------|--------|
"""

    for name, data in results["metrics"].items():
        if "current" in data and "baseline" in data:
            delta = data.get("increase_percent", 0)
            threshold = data.get("threshold_percent", 0)
            status = "✅" if delta <= threshold else "❌"
            report += f"| {name} | {data['current']:.2f} | {data['baseline']:.2f} | {delta:+.1f}% | {threshold}% | {status} |\n"
        elif "count" in data:
            status = "✅" if data["count"] <= data["max_allowed"] else "❌"
            report += f"| {name} | {data['count']} | - | - | {data['max_allowed']} | {status} |\n"

    if results["violations"]:
        report += "\n### ❌ Violations\n\n"
        for v in results["violations"]:
            report += f"- {v}\n"

    if results["warnings"]:
        report += "\n### ⚠️ Warnings\n\n"
        for w in results["warnings"]:
            report += f"- {w}\n"

    if results["status"] == "PASS" and not results["warnings"]:
        report += "\n### ✅ All Checks Passed\n\nNo performance regressions detected.\n"

    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True, help="Current metrics JSON")
    parser.add_argument("--baseline", required=True, help="Baseline metrics JSON")
    parser.add_argument("--slo-config", required=True, help="SLO config YAML")
    parser.add_argument("--output", default="drift_report.md", help="Output report file")
    args = parser.parse_args()

    with open(args.current) as f:
        current = json.load(f)
    with open(args.baseline) as f:
        baseline = json.load(f)
    slo = load_slo_config(args.slo_config)

    results = check_slo(current, baseline, slo)
    report = generate_report(results, current)

    with open(args.output, "w") as f:
        f.write(report)

    print(report)
    print(f"\n📄 Report saved to: {args.output}")

    if results["status"] == "FAIL":
        exit(1)


if __name__ == "__main__":
    main()
```

**Plik:** `ci/slo_config.yaml` (NOWY)

```yaml
# SLO Configuration for Zero Drift
# Based on RAE-CI-QUALITY-SPEC-enterprise-v2.0.md
# Version: 1.0

timing:
  max_increase_percent: 10  # SLO: <= 5% between releases, CI allows 10%
  max_test_duration_seconds: 300  # 5 minutes max for full suite
  description: "Test execution time regression check"

memory:
  max_peak_mb: 2048  # 2GB max
  max_increase_percent: 10
  description: "Memory usage regression check"

logs:
  max_warning: 0  # Zero warnings policy
  max_error: 0    # Zero errors in tests
  max_critical: 0  # Zero critical logs in tests
  description: "Log volume and severity check"

coverage:
  min_overall: 65  # From pytest.ini --cov-fail-under
  min_math_layer: 80  # SLO for math+reflective (from spec)
  min_reflective_layer: 80
  description: "Test coverage minimum thresholds"

api_latency:
  p95_max_ms: 200  # 95th percentile max latency
  p99_max_ms: 350  # 99th percentile max latency
  increase_threshold_percent: 20  # Max allowed increase
  description: "API endpoint latency check"

benchmark:
  mrr_drop_threshold: 0.05  # Max 5% drop in MRR
  quality_drop_threshold: 0.10  # Max 10% drop in quality metrics
  description: "Benchmark quality regression check"
```

### 3.5 Integracja z OpenTelemetry

**Rozszerzenie:** `benchmarking/math_metrics/base.py`

Dodać klasę eksportującą metryki do OTel:

```python
# W benchmarking/math_metrics/base.py

from apps.memory_api.observability.opentelemetry_config import get_tracer
from opentelemetry import metrics

class MathMetricsCollector:
    """Collect and export math layer metrics to OpenTelemetry."""

    def __init__(self):
        self.tracer = get_tracer("rae.math_metrics")
        meter = metrics.get_meter("rae.math_metrics")

        # Create meters for key metrics
        self.pagerank_duration = meter.create_histogram(
            name="math.pagerank.duration_ms",
            description="PageRank computation duration",
            unit="ms"
        )
        self.graph_size = meter.create_histogram(
            name="math.graph.node_count",
            description="Knowledge graph node count",
            unit="nodes"
        )
        self.reflection_steps = meter.create_histogram(
            name="reflective.episode.steps",
            description="Reflection episode step count",
            unit="steps"
        )

    def record_pagerank_metrics(self, graph_size: int, duration_ms: float,
                                convergence_iterations: int):
        """Record PageRank computation metrics."""
        with self.tracer.start_as_current_span("math.pagerank") as span:
            span.set_attribute("graph.node_count", graph_size)
            span.set_attribute("computation.duration_ms", duration_ms)
            span.set_attribute("computation.iterations", convergence_iterations)

            self.pagerank_duration.record(duration_ms)
            self.graph_size.record(graph_size)

    def record_reflection_metrics(self, episode_id: str, steps: int,
                                  improvement_delta: float):
        """Record reflection layer metrics."""
        with self.tracer.start_as_current_span("reflective.episode") as span:
            span.set_attribute("episode.id", episode_id)
            span.set_attribute("episode.steps", steps)
            span.set_attribute("episode.improvement_delta", improvement_delta)

            self.reflection_steps.record(steps)
```

### 3.6 Kryteria Sukcesu

| Kryterium | Metryka | Target | Weryfikacja |
|-----------|---------|--------|-------------|
| Drift detection accuracy | False positive rate | < 5% | Monthly review |
| SLO enforcement | Violations caught | 100% | CI logs |
| Metrics coverage | Math + reflective layers | >= 80% | OTel dashboard |
| Report generation | Per PR | 100% | GitHub artifacts |
| Baseline refresh | Quarterly update | 4x/year | Calendar reminder |

### 3.7 Szacowany Effort

| Zadanie | Story Points | Dni | Właściciel |
|---------|--------------|-----|------------|
| collect_metrics.py | 5 | 1.5 | Dev |
| check_slo.py | 5 | 1.5 | Dev |
| slo_config.yaml | 2 | 0.5 | Architect |
| drift-detection job | 5 | 1.5 | DevOps |
| OTel integration | 5 | 1.5 | Dev |
| Dokumentacja | 2 | 0.5 | Tech Writer |
| **TOTAL** | **24 SP** | **~7 dni** | |

### 3.8 Ryzyko i Mitigation

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Flaky metrics (CI variability) | Wysokie | Średnie | Średnia z 3 runs, tolerance buffer (+/- 10%) |
| OTel overhead | Niskie | Niskie | Conditional enable, sampling (10%) |
| Baseline drift over time | Średnie | Średnie | Quarterly baseline refresh process |
| False regressions (infra changes) | Średnie | Wysokie | Manual review, infrastructure tagging |

### 3.9 Dependencies

- **Wymagane przed startem:** ✅ Iteracja 1 + 2
- **Zewnętrzne:** `memory-profiler`, `pytest-timeout`, `psutil`, `pyyaml`, OTel packages
- **Istniejące zasoby:** `benchmarking/results/metrics_reference.json` (baseline)
- **Blokuje:** Iterację 4 (Auto-Healing)

---

## Iteracja 4: Auto-Healing CI

**Status:** ⏳ Do zrobienia (częściowo istniejące: `scripts/ai_code_review.py`)
**Cel:** Agent AI generuje PR z poprawkami na podstawie błędów CI

**Priorytet:** P2 - ŚREDNIE (innovation, competitive advantage)
**Effort:** 9 dni (30 SP)

### 4.1 Cele i Deliverables

| Cel | Deliverable | Plik | Priorytet |
|-----|-------------|------|-----------|
| Context generator | Analyzer | `scripts/ci/analyze_failure.py` | P0 |
| LLM integration | Fix generator | `scripts/ci/ci_fix_agent.py` | P0 |
| Automatyczne PR | Workflow | `.github/workflows/auto-fix.yml` | P0 |
| Human-in-the-loop | Review process | GitHub settings | P0 |
| Fix templates | Template library | `ci/fix_templates/` | P1 |
| Cost control | Budget limits | Config | P1 |

### 4.2 Architektura Auto-Healing

```mermaid
flowchart LR
    A[CI Failure] --> B[analyze_failure.py]
    B --> C{Can Auto-Fix?}
    C -->|YES| D[ci_fix_agent.py]
    C -->|NO| E[Create Manual Ticket]
    D --> F[LLM Claude/Gemini]
    F --> G[Generate Code Fix]
    G --> H[Create PR]
    H --> I[Human Review]
    I -->|Approve| J[Merge]
    I -->|Reject| K[Manual Fix]
```

### 4.3 Wymagane Zmiany w CI/CD

**Plik:** `.github/workflows/auto-fix.yml` (NOWY)

```yaml
name: Auto-Healing CI

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  analyze-failure:
    name: Analyze CI Failure
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    outputs:
      should_fix: ${{ steps.analyze.outputs.should_fix }}
      fix_type: ${{ steps.analyze.outputs.fix_type }}

    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.workflow_run.head_branch }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Download CI artifacts
        uses: actions/download-artifact@v4
        continue-on-error: true
        with:
          run-id: ${{ github.event.workflow_run.id }}
          path: ci-artifacts/

      - name: Analyze failure
        id: analyze
        run: |
          python scripts/ci/analyze_failure.py \
            --workflow-run-id ${{ github.event.workflow_run.id }} \
            --artifacts-dir ci-artifacts/ \
            --output failure_context.json

          if [ -f "failure_context.json" ]; then
            FIX_TYPE=$(jq -r '.fix_type' failure_context.json)
            CAN_FIX=$(jq -r '.can_auto_fix' failure_context.json)

            echo "fix_type=$FIX_TYPE" >> $GITHUB_OUTPUT
            echo "should_fix=$CAN_FIX" >> $GITHUB_OUTPUT
          else
            echo "should_fix=false" >> $GITHUB_OUTPUT
          fi

      - name: Upload context
        if: steps.analyze.outputs.should_fix == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: fix-context-${{ github.event.workflow_run.id }}
          path: failure_context.json
          retention-days: 7

  generate-fix:
    name: Generate Fix with AI
    runs-on: ubuntu-latest
    needs: analyze-failure
    if: needs.analyze-failure.outputs.should_fix == 'true'

    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.workflow_run.head_branch }}
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Download fix context
        uses: actions/download-artifact@v4
        with:
          name: fix-context-${{ github.event.workflow_run.id }}

      - name: Install dependencies
        run: pip install anthropic openai pyyaml

      - name: Generate fix
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          FIX_TYPE: ${{ needs.analyze-failure.outputs.fix_type }}
        run: |
          python scripts/ci/ci_fix_agent.py \
            --context failure_context.json \
            --fix-type $FIX_TYPE \
            --provider anthropic \
            --output-dir fixes/

      - name: Create fix branch and PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          BRANCH_NAME="fix/auto-$(date +%Y%m%d-%H%M%S)"
          git config user.name "RAE Auto-Heal Bot"
          git config user.email "noreply@github.com"
          git checkout -b $BRANCH_NAME

          # Apply fixes
          if [ -d "fixes" ]; then
            for file in fixes/*.py; do
              if [ -f "$file" ]; then
                TARGET=$(grep "# TARGET:" "$file" | cut -d: -f2 | xargs)
                if [ -n "$TARGET" ] && [ -f "$TARGET" ]; then
                  cp "$file" "$TARGET"
                  git add "$TARGET"
                fi
              fi
            done
          fi

          git commit -m "fix: auto-generated fix for ${{ needs.analyze-failure.outputs.fix_type }}

          Fix type: ${{ needs.analyze-failure.outputs.fix_type }}
          Original run: ${{ github.event.workflow_run.html_url }}

          🤖 Generated with [Claude Code](https://claude.com/claude-code)

          Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

          git push origin $BRANCH_NAME

          gh pr create \
            --title "[Auto-Fix] ${{ needs.analyze-failure.outputs.fix_type }}" \
            --body "$(cat <<'EOF'
          ## 🤖 Auto-Generated Fix

          This PR was automatically generated to fix a CI failure.

          **Fix Type:** ${{ needs.analyze-failure.outputs.fix_type }}
          **Original CI Run:** ${{ github.event.workflow_run.html_url }}
          **Branch:** ${{ github.event.workflow_run.head_branch }}

          ### Changes

          See commit for details.

          ### Review Checklist

          - [ ] Code changes make sense
          - [ ] No security issues introduced
          - [ ] Tests pass locally
          - [ ] No unintended side effects

          ### Context

          This fix was generated using AI based on the CI failure context.
          Please review carefully before merging.

          ---
          *Generated by RAE Auto-Healing CI - Iteration 4*
          EOF
          )" \
            --label "auto-fix,ci" \
            --reviewer "${{ github.event.workflow_run.actor.login }}" \
            --draft
```

### 4.4 Nowe Narzędzia/Skrypty

**Plik:** `scripts/ci/analyze_failure.py` (NOWY)

```python
#!/usr/bin/env python3
"""
Analyze CI failure and generate context for fix generation.

Part of RAE CI Quality Implementation - Iteration 4: Auto-Healing CI
"""
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


class FailureAnalyzer:
    """Analyze CI failures and categorize them."""

    # Patterns for different types of fixable failures
    FIX_PATTERNS = {
        "warning": {
            "patterns": [
                r"DeprecationWarning",
                r"UserWarning",
                r"PydanticDeprecatedSince20",
            ],
            "can_auto_fix": True,
            "confidence": "high"
        },
        "import_error": {
            "patterns": [
                r"ModuleNotFoundError",
                r"ImportError",
            ],
            "can_auto_fix": True,
            "confidence": "high"
        },
        "type_error": {
            "patterns": [
                r"TypeError.*argument",
                r"mypy.*error",
            ],
            "can_auto_fix": True,
            "confidence": "medium"
        },
        "flaky_test": {
            "patterns": [
                r"FAILED.*::.*test_",
                r"error.*timeout",
            ],
            "can_auto_fix": True,
            "confidence": "medium"
        },
        "lint": {
            "patterns": [
                r"ruff.*error",
                r"black.*would reformat",
                r"isort.*error",
            ],
            "can_auto_fix": True,
            "confidence": "high"
        },
        "drift": {
            "patterns": [
                r"Regression detected",
                r"SLO violation",
                r"threshold exceeded",
            ],
            "can_auto_fix": False,
            "confidence": "low"
        },
    }

    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.logs: List[str] = []
        self.failures: List[Dict] = []

    def load_artifacts(self):
        """Load all log files from artifacts."""
        if not self.artifacts_dir.exists():
            print(f"⚠️ Artifacts directory not found: {self.artifacts_dir}")
            return

        for log_file in self.artifacts_dir.rglob("*.log"):
            try:
                self.logs.append(log_file.read_text())
            except Exception as e:
                print(f"⚠️ Failed to read {log_file}: {e}")

        for json_file in self.artifacts_dir.rglob("*.json"):
            try:
                data = json.loads(json_file.read_text())
                if "tests" in data:  # pytest report
                    for test in data["tests"]:
                        if test.get("outcome") == "failed":
                            self.failures.append(test)
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ Failed to parse {json_file}: {e}")

    def classify_failure(self) -> tuple[str, bool, str]:
        """Classify the type of failure.

        Returns:
            (fix_type, can_auto_fix, confidence)
        """
        all_text = "\n".join(self.logs)

        for fix_type, config in self.FIX_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, all_text, re.IGNORECASE):
                    return (fix_type, config["can_auto_fix"], config["confidence"])

        return ("unknown", False, "none")

    def extract_context(self) -> Dict:
        """Extract relevant context for fix generation."""
        fix_type, can_auto_fix, confidence = self.classify_failure()

        context = {
            "fix_type": fix_type,
            "can_auto_fix": can_auto_fix,
            "confidence": confidence,
            "failures": self.failures[:10],  # Limit to 10
            "relevant_logs": self._extract_relevant_logs(fix_type),
            "affected_files": self._extract_affected_files(),
            "suggestions": self._get_suggestions(fix_type)
        }

        return context

    def _extract_relevant_logs(self, fix_type: str, max_lines: int = 50) -> List[str]:
        """Extract most relevant log lines."""
        relevant = []
        all_text = "\n".join(self.logs)

        patterns = self.FIX_PATTERNS.get(fix_type, {}).get("patterns", [])

        for line in all_text.split("\n"):
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
                relevant.append(line)
            if len(relevant) >= max_lines:
                break

        return relevant

    def _extract_affected_files(self) -> List[str]:
        """Extract file paths from failures."""
        affected = []

        for failure in self.failures:
            nodeid = failure.get("nodeid", "")
            if "::" in nodeid:
                file_path = nodeid.split("::")[0]
                if file_path not in affected:
                    affected.append(file_path)

        return affected

    def _get_suggestions(self, fix_type: str) -> List[str]:
        """Get fix suggestions based on failure type."""
        suggestions = {
            "warning": [
                "Update deprecated API calls",
                "Add filterwarnings to pytest.ini",
                "Use pytest.warns() for expected warnings"
            ],
            "import_error": [
                "Add missing dependency to requirements.txt",
                "Fix import path",
                "Add __init__.py if needed"
            ],
            "type_error": [
                "Fix function signature",
                "Add type hints",
                "Update caller to match new signature"
            ],
            "flaky_test": [
                "Add explicit waits for async operations",
                "Mock external dependencies",
                "Add test isolation with fixtures"
            ],
            "lint": [
                "Run black --fix",
                "Run isort --fix",
                "Fix ruff violations"
            ],
            "drift": [
                "Review performance-critical code",
                "Check for N+1 queries",
                "Optimize slow tests"
            ]
        }
        return suggestions.get(fix_type, ["Manual investigation required"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--output", default="failure_context.json")
    args = parser.parse_args()

    analyzer = FailureAnalyzer(Path(args.artifacts_dir))
    analyzer.load_artifacts()
    context = analyzer.extract_context()

    context["workflow_run_id"] = args.workflow_run_id

    with open(args.output, "w") as f:
        json.dump(context, f, indent=2)

    status_emoji = "✅" if context["can_auto_fix"] else "❌"
    print(f"{status_emoji} Analysis complete: {context['fix_type']}")
    print(f"   Can auto-fix: {context['can_auto_fix']}")
    print(f"   Confidence: {context['confidence']}")
    print(f"   Context saved to: {args.output}")


if __name__ == "__main__":
    main()
```

**Plik:** `scripts/ci/ci_fix_agent.py` (NOWY)

```python
#!/usr/bin/env python3
"""
AI-powered CI fix generator.
Uses Claude or Gemini to generate fixes based on failure context.

Part of RAE CI Quality Implementation - Iteration 4: Auto-Healing CI
"""
import argparse
import json
import os
from pathlib import Path
from typing import Dict, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None


class CIFixAgent:
    """Generate CI fixes using LLM."""

    FIX_TEMPLATES = {
        "warning": """You are fixing a Python warning in the RAE project.

Policy: ZERO WARNINGS (pytest -W error)

Context:
{context}

Generate a fix that:
1. Eliminates the warning at its source
2. If from external library, add appropriate filterwarnings with comment
3. Preserves existing functionality
4. Follows project conventions (see AGENT_TESTING_GUIDE.md)

Return ONLY the modified code, no explanations.
""",
        "flaky_test": """You are fixing a flaky test in the RAE project.

Test: {test_name}
Failure pattern: {failure_info}

Common causes:
- Timing issues (add explicit waits)
- Race conditions (add synchronization)
- External dependencies (add mocks)
- Non-deterministic data (add seed)

Generate a fix that makes the test deterministic.
Follow AGENT_TESTING_GUIDE.md principles.
Return ONLY the modified test code.
""",
        "lint": """Fix the following linting issues:
{issues}

Apply black, isort, and ruff fixes.
Return the corrected code.
""",
        "import_error": """Fix the following import error:
{error_message}

Common fixes:
- Add missing dependency to requirements.txt
- Fix import path
- Add __init__.py

Return the fixed code or requirements.txt update.
""",
        "type_error": """Fix the following type error:
{error_message}

Update function signature or caller to match.
Add type hints if missing.
Return the fixed code.
""",
    }

    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        if provider == "anthropic" and anthropic:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self.client = anthropic.Anthropic(api_key=api_key)
        elif provider == "openai" and openai:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set")
            self.client = openai.OpenAI(api_key=api_key)
        else:
            raise RuntimeError(f"Provider {provider} not available")

    def generate_fix(self, context: Dict, fix_type: str) -> Optional[str]:
        """Generate fix using LLM."""
        template = self.FIX_TEMPLATES.get(fix_type)
        if not template:
            print(f"⚠️ No template for fix type: {fix_type}")
            return None

        # Prepare prompt
        prompt = template.format(
            context=json.dumps(context, indent=2),
            test_name=context.get("failures", [{}])[0].get("nodeid", "unknown"),
            failure_info=json.dumps(context.get("failures", [])[:3], indent=2),
            issues="\n".join(context.get("relevant_logs", [])[:20]),
            error_message="\n".join(context.get("relevant_logs", [])[:10])
        )

        print(f"🤖 Generating fix using {self.provider}...")

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model="claude-sonnet-4-5-20241022",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
        except Exception as e:
            print(f"❌ Error generating fix: {e}")
            return None

    def save_fix(self, fix_content: str, output_dir: Path, affected_file: str):
        """Save generated fix to file."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as .py file with target annotation
        fix_file = output_dir / f"fix_{Path(affected_file).stem}.py"
        fix_file.write_text(f"# TARGET: {affected_file}\n{fix_content}")

        print(f"✅ Fix saved: {fix_file}")
        return fix_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True, help="Context JSON file")
    parser.add_argument("--fix-type", required=True, help="Type of fix to generate")
    parser.add_argument("--output-dir", default="fixes/", help="Output directory")
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"])
    args = parser.parse_args()

    with open(args.context) as f:
        context = json.load(f)

    if not context.get("can_auto_fix", False):
        print("⚠️ Context indicates this failure cannot be auto-fixed")
        exit(1)

    agent = CIFixAgent(provider=args.provider)

    affected_files = context.get("affected_files", [])
    if not affected_files:
        print("⚠️ No affected files identified")
        exit(1)

    output_dir = Path(args.output_dir)

    for file_path in affected_files[:5]:  # Limit to 5 files
        print(f"📝 Generating fix for: {file_path}")
        fix = agent.generate_fix(context, args.fix_type)

        if fix:
            agent.save_fix(fix, output_dir, file_path)
        else:
            print(f"❌ No fix generated for: {file_path}")


if __name__ == "__main__":
    main()
```

### 4.5 Fix Templates

**Katalog:** `ci/fix_templates/` (NOWY)

**Plik:** `ci/fix_templates/README.md`

```markdown
# Auto-Fix Templates

This directory contains templates and examples for common CI fixes.
These guide the AI agent in generating appropriate fixes.

## Available Templates

1. **warning_fix.md** - Deprecation warnings, Pydantic migrations
2. **flaky_fix.md** - Flaky test patterns and solutions
3. **lint_fix.md** - Linting and formatting issues
4. **import_fix.md** - Import errors and dependency issues

## Template Structure

Each template follows this format:

```markdown
# Fix Type: <name>

## Pattern Description
[What this fix addresses]

## Common Causes
- Cause 1
- Cause 2

## Fix Strategy
1. Step 1
2. Step 2

## Examples
### Before
[Bad code]

### After
[Fixed code]

## Verification
[How to verify the fix works]
```

## Adding New Templates

1. Create new `.md` file in this directory
2. Follow the structure above
3. Add examples from real fixes
4. Update `ci_fix_agent.py` FIX_TEMPLATES dict
```

**Plik:** `ci/fix_templates/warning_fix.md` (przykład)

```markdown
# Fix Type: Warning

## Pattern: Deprecation Warning

### Before
```python
from datetime import datetime
timestamp = datetime.utcnow()
```

### After
```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)
```

## Pattern: External Library Warning

### pytest.ini
```ini
filterwarnings =
    error
    # [EXTERNAL] google-protobuf: deprecated in Python 3.14
    ignore::DeprecationWarning:google._upb._message
```

## Pattern: Expected Warning in Test

### Before
```python
def test_deprecated_function():
    deprecated_function()  # Generates warning
```

### After
```python
import pytest

def test_deprecated_function():
    with pytest.warns(DeprecationWarning, match="deprecated"):
        deprecated_function()
```

## Verification

```bash
# Run with strict warning check
pytest -W error tests/path/to/test.py

# Should pass with no warnings
```
```

### 4.6 Human-in-the-Loop Configuration

**GitHub Branch Protection Rules:**

Dla branch pattern `fix/auto-*`:
- ✅ Require pull request reviews before merging (1 approval)
- ✅ Require status checks to pass
- ✅ Dismiss stale reviews when new commits pushed
- ✅ Require review from code owners
- ❌ Allow bypassing required pull requests (disabled for auto-fix)

**Labels for Auto-Fix PRs:**
- `auto-fix` - Identifies AI-generated fixes
- `ci` - CI-related changes
- `review-required` - Requires careful human review

### 4.7 Cost Control

**Plik:** `ci/cost_control.yaml` (NOWY)

```yaml
# Cost control for Auto-Healing CI
# Limits API usage to prevent runaway costs

limits:
  max_fixes_per_day: 10
  max_fixes_per_pr: 3
  max_tokens_per_fix: 4000

providers:
  anthropic:
    model: "claude-sonnet-4-5-20241022"
    max_cost_per_month_usd: 50

  openai:
    model: "gpt-4o-mini"
    max_cost_per_month_usd: 20

alert_thresholds:
  daily_fixes: 5  # Alert if > 5 fixes per day
  monthly_cost_usd: 30  # Alert if approaching budget

exclude_fix_types:
  - manual  # Never auto-fix
  - unknown  # Require investigation
```

### 4.8 Kryteria Sukcesu

| Kryterium | Metryka | Target | Weryfikacja |
|-----------|---------|--------|-------------|
| Fix generation rate | Fixes generated / failures | >= 60% | GitHub Insights |
| Fix acceptance rate | PRs merged / PRs created | >= 70% | PR analytics |
| Time to fix | Failure → merged PR | < 24h | Average cycle time |
| False positive rate | Bad fixes / total fixes | < 10% | Review feedback |
| Cost efficiency | Cost / successful fix | < $5 | API billing |
| Human review time saved | Hours saved per week | >= 5h | Time tracking |

### 4.9 Szacowany Effort

| Zadanie | Story Points | Dni | Właściciel |
|---------|--------------|-----|------------|
| analyze_failure.py | 5 | 1.5 | Dev |
| ci_fix_agent.py | 8 | 2.5 | Dev + AI Expert |
| auto-fix.yml workflow | 5 | 1.5 | DevOps |
| Fix templates | 3 | 1 | Dev |
| Branch protection | 2 | 0.5 | Admin |
| Cost control | 2 | 0.5 | DevOps |
| Testowanie E2E | 5 | 1.5 | QA |
| Dokumentacja | 2 | 0.5 | Tech Writer |
| **TOTAL** | **30 SP** | **~9 dni** | |

### 4.10 Ryzyko i Mitigation

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Bad fix wprowadza bug | Średnie | Wysokie | Required review, CI re-run, draft PR |
| LLM hallucination | Średnie | Wysokie | Template-based prompts, validation |
| Cost overrun (API) | Niskie | Średnie | Budget limits, monitoring, caching |
| Security vulnerability | Niskie | Krytyczne | Code review, no secrets in context, SAST |
| Over-reliance on AI | Niskie | Średnie | Human-in-the-loop required, education |

### 4.11 Dependencies

- **Wymagane przed startem:** ✅ Iteracje 1-3
- **Zewnętrzne:** `anthropic` lub `openai` package
- **API Keys:** ANTHROPIC_API_KEY lub OPENAI_API_KEY (GitHub Secrets)
- **Permissions:** GitHub App or PAT with PR write access

---

## Struktura Katalogów

### Nowa Struktura (po wszystkich iteracjach)

```
RAE-agentic-memory/
  .github/
    workflows/
      ci.yml                      # Rozszerzony o warning-check, flaky-detection, drift-detection
      auto-fix.yml                # NOWY - Iteracja 4
      ai-code-review.yml          # Istniejący
      benchmark-nightly.yml       # Istniejący

  ci/                             # NOWY - Katalog konfiguracji CI
    slo_config.yaml               # Iteracja 3 - SLO thresholds
    cost_control.yaml             # Iteracja 4 - Budget limits
    fix_templates/                # Iteracja 4 - AI fix templates
      README.md
      warning_fix.md
      flaky_fix.md
      lint_fix.md
      import_fix.md

  scripts/
    ci/                           # NOWY - Skrypty CI
      __init__.py
      check_new_warnings.py       # Iteracja 1
      analyze_flaky_tests.py      # Iteracja 2
      quarantine_test.py          # Iteracja 2
      collect_metrics.py          # Iteracja 3
      check_slo.py                # Iteracja 3
      analyze_failure.py          # Iteracja 4
      ci_fix_agent.py             # Iteracja 4
    detect_flaky_tests.py         # Istniejący (do rozszerzenia w Iter 2)
    ai_code_review.py             # Istniejący

  tests/
    quarantine/                   # NOWY - Iteracja 2
      __init__.py
      README.md
      api/v1/
      services/
    architecture/                 # Istniejący
    contracts/                    # Istniejący

  benchmarking/
    results/
      metrics_reference.json      # Istniejący - baseline
      metrics_snapshots/          # NOWY - Iteracja 3
    math_metrics/                 # Istniejący (rozszerzenie OTel w Iter 3)

  docs/
    RAE-CI-QUALITY-SPEC.md                     # Istniejący
    RAE-CI-QUALITY-SPEC-enterprise-v2.0.md     # Istniejący
    AGENT_TESTING_GUIDE.md                     # Istniejący
    RAE-CI-QUALITY-IMPLEMENTATION-PLAN.md      # TEN DOKUMENT
    testing/
      WARNING_REMOVAL_PLAN.md                  # Istniejący (DONE)
      FLAKY_TEST_POLICY.md                     # NOWY - Iteracja 2
      DRIFT_DETECTION_GUIDE.md                 # NOWY - Iteracja 3
      AUTO_HEALING_GUIDE.md                    # NOWY - Iteracja 4
```

---

## Implementation Checklist

### Przed Rozpoczęciem (Prerequisites)

- [ ] Review dokumentacji: RAE-CI-QUALITY-SPEC.md, enterprise v2.0, AGENT_TESTING_GUIDE.md
- [ ] Confirm GitHub permissions (workflows, branch protection, secrets)
- [ ] Setup API keys: ANTHROPIC_API_KEY lub OPENAI_API_KEY w GitHub Secrets
- [ ] Review current CI/CD: `.github/workflows/ci.yml` (1014 linii)
- [ ] Backup baseline: `benchmarking/results/metrics_reference.json`

### Iteracja 1: Zero Warnings (3 dni)

- [ ] **Day 1:**
  - [ ] Utwórz `scripts/ci/check_new_warnings.py`
  - [ ] Testuj lokalnie: `pytest -W default | python scripts/ci/check_new_warnings.py`
  - [ ] Zmodyfikuj `pytest.ini` - dodaj filterwarnings
- [ ] **Day 2:**
  - [ ] Rozszerz `.github/workflows/ci.yml` - dodaj PYTHONWARNINGS=error
  - [ ] Dodaj job `warning-check`
  - [ ] Test CI na feature branch
- [ ] **Day 3:**
  - [ ] Skonfiguruj branch protection rules (main + develop)
  - [ ] Dokumentacja w README
  - [ ] Verify: Create test PR with warning → should block

### Iteracja 2: Zero Flake (5 dni)

- [ ] **Day 1:**
  - [ ] Utwórz `scripts/ci/analyze_flaky_tests.py`
  - [ ] Install `pytest-json-report`
  - [ ] Testuj lokalnie: run tests 3x, analyze
- [ ] **Day 2:**
  - [ ] Utwórz `scripts/ci/quarantine_test.py`
  - [ ] Utwórz strukturę `tests/quarantine/`
  - [ ] Napisz `tests/quarantine/README.md`
- [ ] **Day 3-4:**
  - [ ] Dodaj job `flaky-detection` do ci.yml
  - [ ] Dodaj schedule trigger (nightly)
  - [ ] Test workflow z [flaky-check] w commit message
- [ ] **Day 5:**
  - [ ] Zaktualizuj pytest.ini - markers
  - [ ] Dokumentacja: `docs/testing/FLAKY_TEST_POLICY.md`
  - [ ] Verify: Simulate flaky test → quarantine → fix → restore

### Iteracja 3: Zero Drift (7 dni)

- [ ] **Day 1-2:**
  - [ ] Utwórz `scripts/ci/collect_metrics.py`
  - [ ] Test collection: timing, memory, logs
  - [ ] Install dependencies: memory-profiler, psutil
- [ ] **Day 3:**
  - [ ] Utwórz `ci/slo_config.yaml`
  - [ ] Utwórz `scripts/ci/check_slo.py`
  - [ ] Test SLO checking against current metrics
- [ ] **Day 4-5:**
  - [ ] Dodaj job `drift-detection` do ci.yml
  - [ ] Integracja z artifacts (retention 90 dni)
  - [ ] Test PR comment generation
- [ ] **Day 6:**
  - [ ] Rozszerz `benchmarking/math_metrics/` o OTel export
  - [ ] Test OTel span creation
- [ ] **Day 7:**
  - [ ] Dokumentacja: `docs/testing/DRIFT_DETECTION_GUIDE.md`
  - [ ] Verify: Create PR with slow test → drift report

### Iteracja 4: Auto-Healing CI (9 dni)

- [ ] **Day 1-2:**
  - [ ] Utwórz `scripts/ci/analyze_failure.py`
  - [ ] Implementuj failure classification
  - [ ] Test z sample CI artifacts
- [ ] **Day 3-4:**
  - [ ] Utwórz `scripts/ci/ci_fix_agent.py`
  - [ ] Integracja z Anthropic Claude API
  - [ ] Test fix generation dla warning, flaky, lint
- [ ] **Day 5-6:**
  - [ ] Utwórz `.github/workflows/auto-fix.yml`
  - [ ] Test workflow_run trigger
  - [ ] Test PR creation
- [ ] **Day 7:**
  - [ ] Utwórz `ci/fix_templates/` (4 pliki)
  - [ ] Utwórz `ci/cost_control.yaml`
  - [ ] Skonfiguruj branch protection dla fix/auto-*
- [ ] **Day 8:**
  - [ ] Testowanie E2E:
    - [ ] Simulate CI failure
    - [ ] Verify context generation
    - [ ] Verify fix generation
    - [ ] Verify PR creation
    - [ ] Review and merge
- [ ] **Day 9:**
  - [ ] Dokumentacja: `docs/testing/AUTO_HEALING_GUIDE.md`
  - [ ] Team training session
  - [ ] Monitor first real failures

### Po Wdrożeniu (Ongoing)

- [ ] **Weekly:**
  - [ ] Review quarantine backlog
  - [ ] Review auto-fix PR quality
  - [ ] Monitor API costs
- [ ] **Monthly:**
  - [ ] Review SLO violations
  - [ ] Update baseline metrics (jeśli stable)
  - [ ] Review and improve fix templates
- [ ] **Quarterly:**
  - [ ] Refresh `metrics_reference.json` baseline
  - [ ] Review and update SLO thresholds
  - [ ] Audit auto-fix effectiveness

---

## Diagram Przepływu (Complete System)

```mermaid
flowchart TD
    subgraph "Developer Flow"
        A[Developer Push] --> B[GitHub Actions CI]
    end

    subgraph "Iteracja 1: Zero Warnings"
        B --> C[pytest -W error]
        C --> D{Warnings?}
        D -->|YES| E1[warning-check FAIL]
        D -->|NO| F1[Pass to Iter 2]
        E1 --> BLOCK1[Block Merge]
    end

    subgraph "Iteracja 2: Zero Flake"
        F1 --> G[Run Tests 3x]
        G --> H{Consistent?}
        H -->|NO| I[Flaky Detected]
        I --> J[quarantine_test.py]
        J --> K[Move to tests/quarantine/]
        K --> L[Create Ticket]
        H -->|YES| M[Pass to Iter 3]
    end

    subgraph "Iteracja 3: Zero Drift"
        M --> N[collect_metrics.py]
        N --> O[check_slo.py]
        O --> P{SLO OK?}
        P -->|NO| Q[drift FAIL]
        Q --> R[Generate drift_report.md]
        R --> BLOCK3[Block + Alert]
        P -->|YES| S[Pass to Success]
    end

    subgraph "Iteracja 4: Auto-Healing"
        BLOCK1 --> T[analyze_failure.py]
        BLOCK3 --> T
        L --> T
        T --> U{Can Auto-Fix?}
        U -->|YES| V[ci_fix_agent.py]
        V --> W[AI Generate Fix]
        W --> X[Create PR fix/auto-*]
        X --> Y[Human Review]
        Y -->|Approve| Z[Merge]
        Z --> B
        Y -->|Reject| AA[Manual Fix]
        AA --> B
        U -->|NO| AB[Create Manual Ticket]
    end

    subgraph "Success Path"
        S --> AC[All Checks Pass]
        AC --> AD[Update Baseline]
        AD --> AE[Merge Allowed]
    end

    style BLOCK1 fill:#f88,stroke:#f00,stroke-width:2px
    style BLOCK3 fill:#f88,stroke:#f00,stroke-width:2px
    style AC fill:#8f8,stroke:#0f0,stroke-width:2px
    style AE fill:#8f8,stroke:#0f0,stroke-width:2px
```

---

## Kluczowe Pliki do Wdrożenia

### Top 5 najważniejszych plików:

1. **`.github/workflows/ci.yml`**
   - Główny workflow CI do rozszerzenia
   - Dodanie 3 nowych jobs: warning-check, flaky-detection, drift-detection
   - ~1014 linii → ~1500 linii (rozszerzenie)

2. **`scripts/ci/` (katalog)**
   - 7 nowych skryptów Python
   - Każdy z dokumentacją i error handling
   - Integralny element wszystkich 4 iteracji

3. **`pytest.ini`**
   - Konfiguracja filterwarnings (Iter 1)
   - Nowe markery: flaky, quarantine (Iter 2)
   - Testpaths - wykluczenie tests/quarantine/

4. **`ci/slo_config.yaml`**
   - Definicje SLO/SLA dla Zero Drift
   - Thresholdy dla timing, memory, logs
   - Referencja dla check_slo.py

5. **`.github/workflows/auto-fix.yml`**
   - Nowy workflow dla Auto-Healing
   - Trigger: workflow_run na CI failure
   - Integracja z LLM, PR creation

---

## Compliance z Dokumentacją

### Zgodność z RAE-CI-QUALITY-SPEC.md ✅

| Filar | Spec | Plan | Status |
|-------|------|------|--------|
| Zero Warnings | Wymagane | Iteracja 1 | ✅ Covered |
| Zero Flake | Wymagane | Iteracja 2 | ✅ Covered |
| Zero Drift | Opcjonalne | Iteracja 3 | ✅ Covered |
| Auto-Healing | Opcjonalne | Iteracja 4 | ✅ Covered |

### Zgodność z RAE-CI-QUALITY-SPEC-enterprise-v2.0.md ✅

| Element | Spec | Plan | Status |
|---------|------|------|--------|
| SLO/SLA | Wymagane | ci/slo_config.yaml | ✅ Covered |
| Diagram Mermaid | Wymagany | W planie | ✅ Included |
| BigTech comparison | Opcjonalny | Executive Summary | ✅ Referenced |
| 4-layer integration | Wymagany | OTel metrics | ✅ Covered |

### Zgodność z AGENT_TESTING_GUIDE.md ✅

| Zasada | Plan Implementation | Status |
|--------|---------------------|--------|
| ZERO WARNINGS policy | Iteracja 1 - pytest -W error | ✅ Core |
| Tests as contracts | Fix templates, review process | ✅ Covered |
| Deterministic tests | Iteracja 2 - flaky detection | ✅ Core |
| Agent instructions | Fix templates w ci/fix_templates/ | ✅ Covered |

---

## Podsumowanie

Ten plan wdrożenia zapewnia:

✅ **Kompletność:** Wszystkie 4 filary z specyfikacji
✅ **Iteracyjność:** Postupowe wdrażanie bez big-bang
✅ **Mierzalność:** Jasne kryteria sukcesu i metryki
✅ **Realność:** Osadzenie w istniejącej infrastrukturze CI
✅ **Skalowalno ść:** Od prostego (Zero Warnings) do zaawansowanego (Auto-Healing)
✅ **Zgodność:** Z wszystkimi 3 dokumentami źródłowymi

**Total Effort:** 24 dni (81 SP) - ~5 tygodni pracy 1 seniora dev + DevOps support

**ROI:** Enterprise-grade CI quality system porównywalny z Google/OpenAI/AWS

---

## Następne Kroki

1. **Review tego planu** z zespołem (1h meeting)
2. **Priorytetyzacja:** Confirm Iter 1 → 2 → 3 → 4 order
3. **Resource allocation:** Assign dev + devops
4. **Kick-off Iteracji 1:** Setup meeting (30 min)
5. **Start implementation:** Branch `feature/ci-quality-iter-1`

---

*Dokument przygotowany przez: Claude Opus 4.5 (Plan Agent)*
*Data: 2025-12-08*
*Projekt: RAE-agentic-memory*
