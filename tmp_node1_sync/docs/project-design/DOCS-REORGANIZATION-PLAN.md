# Plan Reorganizacji Katalogu docs/

**Data utworzenia:** 2025-12-03
**Status:** Proposed
**Priorytet:** HIGH

## 🎯 Cel reorganizacji

Uporządkowanie struktury dokumentacji RAE zgodnie z profesjonalnymi standardami:
- Jasne rozdzielenie dokumentacji stałej od auto-generowanej
- Implementacja 4-warstwowej architektury zgodności (security/certification/norms/compliance)
- Przeniesienie prac rozwojowych do odpowiednich katalogów
- Usunięcie duplikatów i pustych katalogów
- Automatyzacja aktualizacji dokumentów dynamicznych

## 📊 Analiza obecnego stanu

### Problemy zidentyfikowane:

1. **Puste katalogi** (bez plików):
   - `docs/api/` - pusty
   - `docs/architecture/` - pusty
   - `docs/deployment/` - pusty
   - `docs/integrations/` - pusty
   - `docs/contributing/` - pusty

2. **Duplikacja struktury**:
   - `docs/security/` vs `docs/reference/iso-security/`
   - Dokumentacja API rozproszona w wielu miejscach

3. **Prace rozwojowe w głównym katalogu docs**:
   - `docs/opentelemetry/` - plany implementacji (powinno być w project-design)
   - `docs/security/` - opis funkcjonalności do certyfikacji (powinno być w compliance/)

4. **Brak struktury dla auto-generowanych dokumentów**:
   - STATUS.md, TESTING_STATUS.md, CHANGELOG.md w różnych miejscach
   - Brak dedykowanego katalogu dla raportów CI/CD

5. **Brak implementacji 4-warstwowej architektury zgodności**:
   - Zgodnie z `RAE-security-Architektura-4-warstwy-zgodnosci.md`
   - Brak struktury dla policy packs (ISO 42001, NIST, HIPAA, FedRAMP, etc.)

## 🏗️ Proponowana nowa struktura

```
docs/
├── .auto-generated/           # 🤖 Katalog dla automatycznie generowanych dokumentów
│   ├── status/
│   │   ├── STATUS.md         # Auto: Status projektu (metrics, health)
│   │   ├── TESTING_STATUS.md # Auto: Status testów (coverage, pass rate)
│   │   └── CI_STATUS.md      # Auto: Status GitHub Actions
│   ├── reports/
│   │   ├── CHANGELOG.md      # Auto: Changelog z commitów
│   │   ├── TEST_REPORT.md    # Auto: Szczegółowy raport testów
│   │   ├── COVERAGE_REPORT.md # Auto: Coverage analysis
│   │   └── CODE_METRICS.md   # Auto: LOC, complexity, etc.
│   ├── api/
│   │   ├── openapi.json      # Auto: OpenAPI spec z FastAPI
│   │   └── api_endpoints.md  # Auto: Lista endpointów
│   └── README.md             # Jak czytać auto-generowane dokumenty
│
├── guides/                    # 📖 Podręczniki użytkownika (ręczne)
│   ├── getting-started/
│   │   ├── quickstart.md
│   │   ├── installation.md
│   │   └── first-steps.md
│   ├── user/
│   │   ├── memory-basics.md
│   │   ├── hybrid-search.md
│   │   └── agent-execution.md
│   ├── admin/
│   │   ├── deployment.md
│   │   ├── configuration.md
│   │   ├── monitoring.md
│   │   └── backup-restore.md
│   └── developer/
│       ├── architecture-overview.md
│       ├── api-integration.md
│       ├── sdk-usage.md
│       └── contributing.md
│
├── reference/                 # 📚 Dokumentacja referencyjna (ręczna + semi-auto)
│   ├── api/
│   │   ├── rest-api/
│   │   │   ├── memory.md
│   │   │   ├── agent.md
│   │   │   ├── graph.md
│   │   │   └── governance.md
│   │   ├── sdk/
│   │   │   ├── python-sdk.md
│   │   │   ├── typescript-sdk.md (planned)
│   │   │   └── go-sdk.md (planned)
│   │   └── mcp/
│   │       ├── mcp-protocol.md
│   │       └── ide-integration.md
│   ├── architecture/
│   │   ├── system-overview.md
│   │   ├── memory-layers.md
│   │   ├── graph-rag.md
│   │   ├── reflection-engine.md
│   │   ├── multi-tenancy.md
│   │   └── background-workers.md
│   ├── deployment/
│   │   ├── docker compose.md
│   │   ├── kubernetes.md
│   │   ├── rae-lite.md
│   │   └── production-ha.md
│   └── configuration/
│       ├── environment-vars.md
│       ├── llm-profiles.md
│       ├── telemetry.md
│       └── feature-flags.md
│
├── compliance/                # 🛡️ 4-warstwowa architektura zgodności
│   ├── README.md             # Omówienie 4 warstw zgodności
│   │
│   ├── layer-1-foundation/   # Warstwa podstawowa: ISO 42001
│   │   ├── iso-42001/
│   │   │   ├── implementation-map.md
│   │   │   ├── risk-register.md
│   │   │   ├── roles-responsibilities.md
│   │   │   └── audit-trail.md
│   │   └── README.md
│   │
│   ├── layer-2-mapping/      # Warstwa mapowania: Regulation Compatibility
│   │   ├── iso42001-to-nist.md
│   │   ├── iso42001-to-hipaa.md
│   │   ├── iso42001-to-fedramp.md
│   │   ├── iso42001-to-gdpr.md
│   │   ├── iso42001-to-ai-act.md
│   │   └── README.md
│   │
│   ├── layer-3-modules/      # Warstwa wdrożeniowa: Compliance Modules
│   │   ├── hipaa/
│   │   │   ├── policy-pack.yaml
│   │   │   ├── implementation.md
│   │   │   ├── phi-handling.md
│   │   │   └── tests/
│   │   ├── nist-ai-rmf/
│   │   │   ├── policy-pack.yaml
│   │   │   ├── implementation.md
│   │   │   └── tests/
│   │   ├── fedramp/
│   │   │   ├── policy-pack.yaml
│   │   │   ├── moderate-baseline.md
│   │   │   ├── high-baseline.md
│   │   │   └── tests/
│   │   ├── gdpr/
│   │   │   ├── policy-pack.yaml
│   │   │   ├── data-protection.md
│   │   │   └── tests/
│   │   ├── ai-act/
│   │   │   ├── policy-pack.yaml
│   │   │   ├── risk-classification.md
│   │   │   └── tests/
│   │   ├── iso-27001/
│   │   │   ├── policy-pack.yaml
│   │   │   ├── controls.md
│   │   │   └── tests/
│   │   └── README.md
│   │
│   ├── layer-4-enforcement/  # Warstwa egzekucji: Policy Engine
│   │   ├── guardrails/
│   │   ├── cost-controllers/
│   │   ├── risk-controllers/
│   │   └── README.md
│   │
│   └── certifications/       # Dokumenty certyfikacyjne
│       ├── iso-42001-readiness.md
│       ├── nist-attestation.md
│       └── audit-reports/
│
├── project-design/            # 🔧 Plany i prace rozwojowe (ręczne)
│   ├── active/               # Aktywne prace rozwojowe
│   │   └── opentelemetry/    # Przeniesione z docs/opentelemetry/
│   │       ├── implementation-plan-01.md
│   │       ├── implementation-plan-02.md
│   │       ├── implementation-plan-03.md
│   │       ├── implementation-plan-04.md
│   │       ├── improvements-plan.md
│   │       └── research-guide.md
│   ├── completed/            # Zakończone prace
│   │   ├── reflective-memory-v1/
│   │   ├── enterprise-roadmap/
│   │   └── rae-4layer-design/
│   ├── planned/              # Planowane funkcjonalności
│   │   └── multi-modal-memory/
│   └── research/             # Badania i pomysły
│       └── research-ideas/
│
├── operations/               # 🔄 Dokumenty operacyjne
│   ├── runbooks/
│   │   ├── incident-response.md
│   │   ├── backup-restore.md
│   │   └── disaster-recovery.md
│   ├── monitoring/
│   │   ├── metrics-guide.md
│   │   ├── alerting-rules.md
│   │   └── dashboard-setup.md
│   └── maintenance/
│       ├── upgrade-guide.md
│       ├── database-migrations.md
│       └── security-patches.md
│
├── contributing/             # 👥 Dokumenty dla kontrybutorów
│   ├── CONTRIBUTING.md       # Jak kontrybuować
│   ├── CODE_OF_CONDUCT.md    # Kodeks postępowania
│   ├── DEVELOPMENT.md        # Setup środowiska dev
│   ├── TESTING.md            # Strategie testowania
│   ├── BRANCHING.md          # Git workflow
│   └── STYLE_GUIDE.md        # Code style
│
├── ai-specs/                 # 🤖 Specyfikacje dla AI agentów
│   ├── agents/
│   ├── generation/
│   ├── evaluation/
│   └── tests/
│
└── index.md                  # 🏠 Główna strona dokumentacji

ROOT FILES (do przeniesienia):
- STATUS.md → .auto-generated/status/STATUS.md
- TESTING_STATUS.md → .auto-generated/status/TESTING_STATUS.md
- CHANGELOG.md → .auto-generated/reports/CHANGELOG.md
- LOCAL_SETUP.md → guides/getting-started/local-setup.md
- BRANCHING.md → contributing/BRANCHING.md
```

## 🤖 Dokumenty do automatycznej aktualizacji

### 1. Status i metryki (co commit/push)

| Plik | Źródło danych | Narzędzie | Częstotliwość |
|------|---------------|-----------|---------------|
| `.auto-generated/status/STATUS.md` | Git, pytest, coverage | GitHub Actions | Po każdym push |
| `.auto-generated/status/TESTING_STATUS.md` | pytest output | GitHub Actions | Po każdym push |
| `.auto-generated/status/CI_STATUS.md` | GitHub Actions API | GitHub Actions | Po każdym workflow |

### 2. Raporty (codziennie/tygodniowo)

| Plik | Źródło danych | Narzędzie | Częstotliwość |
|------|---------------|-----------|---------------|
| `.auto-generated/reports/CHANGELOG.md` | git log, commits | git-changelog | Daily |
| `.auto-generated/reports/TEST_REPORT.md` | pytest --html | pytest-html | Po testach |
| `.auto-generated/reports/COVERAGE_REPORT.md` | coverage.py | coverage html | Po testach |
| `.auto-generated/reports/CODE_METRICS.md` | radon, lizard | radon | Weekly |

### 3. API Documentation (po zmianie kodu)

| Plik | Źródło danych | Narzędzie | Częstotliwość |
|------|---------------|-----------|---------------|
| `.auto-generated/api/openapi.json` | FastAPI app | FastAPI export | Po zmianach API |
| `.auto-generated/api/api_endpoints.md` | openapi.json | openapi-generator | Po zmianach API |

### 4. Compliance Reports (miesięcznie)

| Plik | Źródło danych | Narzędzie | Częstotliwość |
|------|---------------|-----------|---------------|
| `.auto-generated/compliance/iso42001-status.md` | Policy tests | pytest markers | Monthly |
| `.auto-generated/compliance/nist-coverage.md` | NIST tests | pytest markers | Monthly |
| `.auto-generated/compliance/audit-summary.md` | Access logs, DB | Custom script | Monthly |

## 🔧 Narzędzia do automatyzacji

### 1. GitHub Actions Workflow: `docs-auto-update.yml`

```yaml
name: Auto-Update Documentation

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  update-status:
    - Generate STATUS.md
    - Generate TESTING_STATUS.md
    - Generate CI_STATUS.md

  update-reports:
    - Generate CHANGELOG.md
    - Generate CODE_METRICS.md

  update-api-docs:
    - Export OpenAPI spec
    - Generate API endpoints list

  commit-changes:
    - Git commit with [skip ci]
    - Push to branch
```

### 2. Pre-commit Hook: API Documentation

```bash
# Regenerate OpenAPI spec if API files changed
if git diff --cached --name-only | grep "apps/memory_api/api/"
then
    python scripts/generate_openapi.py
    git add docs/.auto-generated/api/openapi.json
fi
```

### 3. Monthly Cron: Compliance Reports

```bash
# Generate compliance status reports
0 0 1 * * /usr/bin/python3 /path/to/generate_compliance_reports.py
```

## 📋 Plan migracji

### Faza 1: Przygotowanie (1 dzień)
1. Utworzenie nowej struktury katalogów
2. Stworzenie README.md w każdym katalogu
3. Przygotowanie skryptów migracji

### Faza 2: Migracja plików (2 dni)
1. Przeniesienie auto-generowanych dokumentów do `.auto-generated/`
2. Przeniesienie `docs/opentelemetry/` do `project-design/active/opentelemetry/`
3. Reorganizacja `docs/security/` według 4-warstwowej architektury:
   - Layer 1: ISO 42001 foundation
   - Layer 2: Mapping dokumenty
   - Layer 3: Policy packs (HIPAA, NIST, FedRAMP, etc.)
   - Layer 4: Enforcement (guardrails, controllers)
4. Przeniesienie przewodników użytkownika do `guides/`
5. Reorganizacja dokumentacji referencyjnej w `reference/`
6. Usunięcie pustych katalogów

### Faza 3: Automatyzacja (3 dni)
1. Implementacja GitHub Actions workflow dla auto-update
2. Dodanie pre-commit hooks
3. Stworzenie skryptów generujących raporty
4. Testowanie całego pipeline

### Faza 4: Dokumentacja compliance (4 dni)
1. Utworzenie struktury 4-warstwowej zgodności
2. Przeniesienie dokumentów ISO 42001
3. Stworzenie mapowań (Layer 2)
4. Przygotowanie policy packs (Layer 3):
   - HIPAA module
   - NIST AI RMF module
   - FedRAMP module
   - GDPR module
   - AI Act module
   - ISO 27001 module
5. Dokumentacja policy engine (Layer 4)

### Faza 5: Aktualizacja linków (1 dzień)
1. Aktualizacja wszystkich wewnętrznych linków
2. Aktualizacja README.md głównego projektu
3. Aktualizacja CI/CD pipelines
4. Weryfikacja wszystkich linków

### Faza 6: Czyszczenie (1 dzień)
1. Usunięcie zduplikowanych plików
2. Archiwizacja starych dokumentów
3. Ostateczna weryfikacja struktury

## 🎯 Korzyści z reorganizacji

### Dla użytkowników:
- ✅ Łatwe znajdowanie dokumentacji
- ✅ Zawsze aktualne statusy i metryki
- ✅ Przejrzysta struktura compliance
- ✅ Jasny podział: guides vs reference

### Dla developerów:
- ✅ Automatyczna aktualizacja dokumentów dynamicznych
- ✅ Łatwe dodawanie nowych policy packs
- ✅ Jasna struktura dla prac rozwojowych
- ✅ Redukcja manual work

### Dla compliance/certyfikacji:
- ✅ Modułowa struktura zgodności (4 warstwy)
- ✅ Łatwe mapowanie do różnych norm (ISO, NIST, HIPAA, etc.)
- ✅ Automatyczne raporty zgodności
- ✅ Transparentność dla audytorów

### Dla projektu:
- ✅ Profesjonalny wygląd dokumentacji
- ✅ Łatwiejsza konserwacja
- ✅ Gotowość do certyfikacji
- ✅ Open source friendly (policy packs)

## 📝 Lista kontrolna wykonania

- [ ] Faza 1: Przygotowanie struktury
- [ ] Faza 2: Migracja plików
- [ ] Faza 3: Automatyzacja
- [ ] Faza 4: Dokumentacja compliance
- [ ] Faza 5: Aktualizacja linków
- [ ] Faza 6: Czyszczenie
- [ ] Weryfikacja: Wszystkie linki działają
- [ ] Weryfikacja: Auto-update działa
- [ ] Weryfikacja: CI/CD pipeline OK
- [ ] Weryfikacja: README zaktualizowane

## 🚀 Następne kroki

Po akceptacji planu:
1. Commit tego planu do `docs/project-design/DOCS-REORGANIZATION-PLAN.md`
2. Utworzenie feature brancha: `feature/docs-reorganization`
3. Wykonanie Fazy 1-6 zgodnie z planem
4. Code review
5. Merge do develop
6. Merge do main
7. Aktualizacja dokumentacji w README.md

---

**Status:** ✅ READY FOR REVIEW
**Czas realizacji:** ~12 dni (z testowaniem)
**Priorytet:** HIGH
**Zależności:** Brak
