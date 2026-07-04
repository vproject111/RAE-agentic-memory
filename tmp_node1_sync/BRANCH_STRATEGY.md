# 🌳 BRANCH STRATEGY - 4-Fazowy Workflow RAE

> **Nowy Model**: feature → develop → release → main
>
> **Zmiana**: Dodano branch **release** jako bramę bezpieczeństwa przed produkcją

---

## 📊 Przegląd Strategii

```
┌──────────────────────────────────────────────────────────────────┐
│                    4-FAZOWY GIT WORKFLOW                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  feature/*  →  develop  →  release  →  main                     │
│   (lokalnie)   (GitHub)   (GitHub)    (GitHub)                  │
│                                                                  │
│  Cel:          Cel:       Cel:        Cel:                      │
│  Rozwój       Integracja  Stabilizacja Produkcja                │
│  szybki       walidacja   final QA     ŚWIĘTY                   │
│                                                                  │
│  Testy:        Testy:      Testy:      Testy:                   │
│  Tylko nowy   Wszystkie   Full +       CI auto                  │
│  kod          lokalne     integration  wszystko                 │
│                                                                  │
│  Push:         Push:       Push:       Push:                    │
│  Opcjonalny   Obowiązkowy Obowiązkowy TYLKO przez               │
│                                       PR z release               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ FEATURE BRANCH - Rozwój

### Cel
Szybki rozwój nowych funkcjonalności lokalnie lub na GitHub.

### Tworzenie

```bash
# Z develop (ZAWSZE!)
git checkout develop
git pull origin develop --no-rebase
git checkout -b feature/my-feature-name
```

### Naming Convention

```
feature/add-cache-service           ✅ Dobre
feature/fix-null-pointer-bug        ✅ Dobre
feature/refactor-graph-repository   ✅ Dobre
feature/improve-performance         ❌ Zbyt ogólne
feature/changes                     ❌ Nieopisowe
my-feature                          ❌ Brak prefixu feature/
```

### Praca na Feature Branch

```bash
# 1. Implementuj (używając templates)
cp .ai-templates/service_template.py apps/memory_api/services/my_service.py

# 2. Testuj TYLKO nowy kod
pytest --no-cov apps/memory_api/tests/services/test_my_service.py

# 3. Format i lint
make format && make lint

# 4. Commit (conventional)
git add .
git commit -m "feat(services): add my service with full DI

- Implements service layer with dependency injection
- Adds comprehensive tests (12/12 passing)
- Follows repository pattern
- Includes tenant_id isolation"

# 5. Push (opcjonalnie)
git push origin feature/my-feature-name
```

### Testowanie na Feature Branch

| Co testować | Jak | Dlaczego |
|-------------|-----|----------|
| ✅ TYLKO nowy kod | `pytest --no-cov <new_test>.py` | Szybki feedback |
| ✅ Zmieniony kod | `pytest --no-cov <changed_test>.py` | Weryfikacja zmian |
| ❌ Cała suite | ~~`make test-unit`~~ | Marnowanie czasu (10-15 min) |
| ❌ Coverage check | ~~`pytest --cov`~~ | Za wolne, nie potrzebne |

### Merge do Develop

```bash
# Lokalnie (bez PR - szybsze)
git checkout develop
git merge feature/my-feature-name --no-ff

# LUB przez PR (dla code review)
gh pr create --base develop --head feature/my-feature-name \
  --title "Add my feature" \
  --body "Implements feature X with tests"
```

---

## 2️⃣ DEVELOP BRANCH - Integracja

### Cel
Integracja wszystkich features i pełna walidacja przed stabilizacją.

### Charakterystyka

| Aspekt | Wartość |
|--------|---------|
| **Lokalizacja** | GitHub (publiczne repo) |
| **Merge z** | feature/* branches |
| **Merge do** | release/* branches |
| **Testy** | ✅ PEŁNA suite MANDATORY lokalnie przed push |
| **CI** | ✅ Full tests (3 Python versions) |
| **Stabilność** | ⚠️ Może być niestabilne (work in progress) |

### Workflow po Merge z Feature

```bash
# Po lokalnym merge z feature
git checkout develop

# 🚨 KRYTYCZNE: Pełne testy MUSZĄ przejść!
make test-unit
# ✅ 461/461 tests PASSED

make lint
# ✅ All checks passed

make security-scan
# ✅ No vulnerabilities

# Jeśli WSZYSTKO przeszło
git push origin develop

# Sprawdź CI
gh run list --branch develop --limit 1
# ✅ Upewnij się że jest zielone
```

### Kiedy Tworzyć Release Branch

Gdy develop jest stabilny i gotowy do produkcji:

```bash
# Sprawdź ostatnie zmiany
git log --oneline -10

# Sprawdź CI status
gh run list --branch develop --limit 5
# Wszystkie powinny być ✅ SUCCESS

# Jeśli stabilny - utwórz release
git checkout -b release/v1.2.0 develop
git push origin release/v1.2.0
```

---

## 3️⃣ RELEASE BRANCH - Stabilizacja (NOWY!)

### Cel
**Brama bezpieczeństwa** między develop a main. Final QA i stabilizacja.

### Charakterystyka

| Aspekt | Wartość |
|--------|---------|
| **Lokalizacja** | GitHub (publiczne repo) |
| **Tworzenie** | Z develop gdy stabilny |
| **Merge do** | TYLKO main (przez PR) |
| **Ochrona** | 🔒 1 approval + all checks |
| **Dozwolone zmiany** | Bug fixes, docs, version bumps |
| **Zakazane zmiany** | ❌ Nowe features (muszą iść przez develop) |

### Tworzenie Release Branch

```bash
# Z develop
git checkout develop
git pull origin develop

# Utwórz release (semantic versioning)
git checkout -b release/v1.2.0
git push origin release/v1.2.0
```

### Dozwolone Operacje na Release

✅ **TAK - Dozwolone:**
- Bug fixes (tylko krytyczne!)
- Aktualizacja dokumentacji
- Version bump w `pyproject.toml`
- Aktualizacja `CHANGELOG.md`
- Poprawki testów (jeśli test był błędny)

❌ **NIE - Zabronione:**
- Nowe features
- Refactoring
- Zmiany w architekturze
- Dodawanie nowych dependencies
- Niepotrzebne zmiany (nice-to-have)

### Przykład - Bug Fix na Release

```bash
# Znaleziono krytyczny bug na release/v1.2.0
git checkout release/v1.2.0

# Napraw bug
# [edycja pliku...]

pytest --no-cov tests/test_fixed_bug.py
# ✅ Test passes

git add .
git commit -m "fix(core): critical null pointer in reflection engine"
git push origin release/v1.2.0

# CI uruchomi się automatycznie
gh run watch
```

### Merge Release → Main (TYLKO przez PR!)

```bash
# NIE rób lokalnie: git merge release/v1.2.0
# ZAWSZE przez PR:

gh pr create --base main --head release/v1.2.0 \
  --title "Release v1.2.0" \
  --body "## Release v1.2.0

### Changes
- Feature X
- Feature Y
- Bug fix Z

### Testing
- ✅ All 461 tests PASSED
- ✅ Integration tests PASSED
- ✅ Benchmark smoke test PASSED
- ✅ Security scan PASSED

### Checklist
- [x] CHANGELOG.md updated
- [x] Version bumped in pyproject.toml
- [x] All CI checks passing
- [x] Documentation updated

Ready for production deployment."

# Poczekaj na:
# - 2 approvals (required)
# - Wszystkie CI checks ✅
# - Code review feedback

# Po approval - merge przez GitHub UI
# Main pozostaje ŚWIĘTY - zero broken code
```

---

## 4️⃣ MAIN BRANCH - Produkcja (ŚWIĘTY)

### Cel
**Zawsze działający kod produkcyjny.** Święty graal stabilności.

### Charakterystyka

| Aspekt | Wartość |
|--------|---------|
| **Status** | 🛡️ ŚWIĘTY - ZAWSZE działa |
| **Merge z** | TYLKO release/* (przez PR z 2 approvals) |
| **Direct push** | ❌ ZABRONIONE (branch protection) |
| **Force push** | ❌ ZABRONIONE NA ZAWSZE |
| **CI** | ✅ Automatyczne, wszystkie checks |
| **Deployment** | ✅ Automatyczny po merge |

### Branch Protection Rules (GitHub)

```yaml
main:
  required_pull_request_reviews:
    required_approving_review_count: 2
    dismiss_stale_reviews: true
    require_code_owner_reviews: true
    require_last_push_approval: true

  required_status_checks:
    strict: true
    contexts:
      - "lint"
      - "test-full (3.10)"
      - "test-full (3.11)"
      - "test-full (3.12)"
      - "test-mcp (3.11)"
      - "benchmark-smoke"
      - "security"
      - "quality-gate"
      - "docker"

  restrictions:
    users: []
    teams: ["core-maintainers"]

  enforce_admins: true
  allow_force_pushes: false
  allow_deletions: false
  require_conversation_resolution: true
```

### Co Robić Gdy Main jest Czerwone (CI Failed)

```bash
# 1. NATYCHMIAST napraw
git checkout main
git pull origin main

# 2. Identyfikuj problem
gh run view --log-failed

# 3. Napraw na release branch
git checkout release/v1.2.0
# [naprawa...]

# 4. Szybkie testy
make test-unit

# 5. Push i PR do main
git push origin release/v1.2.0
gh pr create --base main --head release/v1.2.0 --title "Hotfix: ..."

# 6. Po merge - main znowu zielony ✅
```

---

## 🔥 HOTFIX WORKFLOW

### Kiedy Używać
Krytyczne bugi w produkcji które wymagają NATYCHMIASTOWEJ naprawy.

### Flow

```bash
# 1. Utwórz hotfix z main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-name

# 2. Napraw bug
# [edycja...]

# 3. Testuj
pytest --no-cov tests/test_hotfix.py
make test-unit

# 4. Commit
git commit -m "fix: critical bug in production

BREAKING: This fixes data corruption in memory storage

Refs: #123"

# 5. Push
git push origin hotfix/critical-bug-name

# 6. PR do main (priorytetowy)
gh pr create --base main --head hotfix/critical-bug-name \
  --title "HOTFIX: Critical bug" \
  --label "priority:critical"

# 7. Po merge do main - backport do develop
git checkout develop
git merge hotfix/critical-bug-name --no-ff
git push origin develop

# 8. Cleanup
git branch -d hotfix/critical-bug-name
git push origin --delete hotfix/critical-bug-name
```

---

## 📋 Workflow Comparison Matrix

| Aspekt | Feature | Develop | Release | Main |
|--------|---------|---------|---------|------|
| **Tworzony z** | develop | merge z feature | develop | merge z release |
| **Testy lokalne** | Tylko nowy | Full (MANDATORY!) | Full + integration | - |
| **CI testy** | Quick (opcjonalne) | Full (3 Python) | Full + wszystko | Full + deployment |
| **Approvals** | 0 | 0 | 1 (code owner) | 2 (maintainers) |
| **Force push** | Dozwolone* | Zabronione | Zabronione | ZABRONIONE |
| **Direct push** | Tak | Tak | Tak | NIE (tylko PR) |
| **Czas życia** | Krótki (dni) | Nieskończony | Średni (tydzień) | Nieskończony |
| **Stabilność** | ⚠️ WIP | ⚠️ Rozwój | ✅ Stabilny | ✅✅ Produkcja |

*Feature branch: force push dozwolone TYLKO jeśli branch prywatny (nie współdzielony)

---

## 🔄 Kompletny Example Flow

### Scenariusz: Dodaj Cache Service

```bash
# ═══════════════════════════════════════════════════════════
# FAZA 1: FEATURE BRANCH
# ═══════════════════════════════════════════════════════════

# 1. Utwórz feature branch
git checkout develop
git pull origin develop
git checkout -b feature/add-cache-service

# 2. Implementuj (autonomicznie!)
mkdir -p apps/memory_api/services/cache
cp .ai-templates/service_template.py apps/memory_api/services/cache/cache_service.py
# [implementacja z DI, tenant_id, logging]

mkdir -p apps/memory_api/tests/services/cache
cp .ai-templates/test_template.py apps/memory_api/tests/services/cache/test_cache_service.py
# [12 testów covering all scenarios]

# 3. Testuj TYLKO nowy kod
pytest --no-cov apps/memory_api/tests/services/cache/test_cache_service.py -v
# ✅ 12/12 tests PASSED

# 4. Format i lint
make format && make lint
# ✅ All checks passed

# 5. Commit
git add .
git commit -m "feat(services): add Redis cache service

- Implements CacheService with dependency injection
- Adds get, set, delete, clear operations
- Includes TTL support and tenant isolation
- Comprehensive test coverage (12/12 passing)"

# 6. Push (opcjonalnie)
git push origin feature/add-cache-service

# ═══════════════════════════════════════════════════════════
# FAZA 2: DEVELOP BRANCH
# ═══════════════════════════════════════════════════════════

# 7. Merge lokalnie
git checkout develop
git merge feature/add-cache-service --no-ff

# 8. 🚨 KRYTYCZNE: Pełne testy
make test-unit
# ✅ 473/473 tests PASSED (+12 nowych)

make lint
# ✅ All checks passed

make security-scan
# ✅ No vulnerabilities

# 9. Push do develop
git push origin develop

# 10. Sprawdź CI
gh run list --branch develop --limit 1
# ✅ All checks passed

# ═══════════════════════════════════════════════════════════
# FAZA 3: RELEASE BRANCH (gdy develop stabilny)
# ═══════════════════════════════════════════════════════════

# 11. Utwórz release (po kilku features)
git checkout -b release/v1.3.0 develop
git push origin release/v1.3.0

# 12. Final QA i stabilizacja
# [Testy integracyjne, manualne testy, review]

# 13. Bug fix jeśli potrzebny (tylko krytyczne!)
# [naprawa i commit]
git push origin release/v1.3.0

# 14. Bump version
# Edit pyproject.toml: version = "1.3.0"
git commit -m "chore: bump version to 1.3.0"

# 15. Update CHANGELOG
# [dodaj changes do CHANGELOG.md]
git commit -m "docs: update CHANGELOG for v1.3.0"

# ═══════════════════════════════════════════════════════════
# FAZA 4: MAIN BRANCH (TYLKO przez PR!)
# ═══════════════════════════════════════════════════════════

# 16. Utwórz PR do main
gh pr create --base main --head release/v1.3.0 \
  --title "Release v1.3.0" \
  --body "Release ready for production"

# 17. Poczekaj na:
# - 2 approvals ✅
# - All CI checks ✅
# - Code review ✅

# 18. Merge przez GitHub UI
# [maintainer klika "Merge pull request"]

# 19. Verify deployment
gh run list --branch main --limit 1
# ✅ All checks passed
# ✅ Deployment successful

# 20. Tag release
git checkout main
git pull origin main
git tag -a v1.3.0 -m "Release v1.3.0: Add cache service"
git push origin v1.3.0

# 21. Cleanup
git branch -d release/v1.3.0
git push origin --delete release/v1.3.0
```

---

## 🎯 Quick Decision Tree

```
        Nowa funkcjonalność?
                │
        ┌───────┴───────┐
       TAK             NIE
        │               │
        ▼               ▼
    feature/*      Bug w produkcji?
        │               │
        ▼           ┌───┴───┐
    develop        TAK     NIE
        │           │       │
        ▼           ▼       ▼
   Stabilny?    hotfix/*  feature/*
        │           │       │
    ┌───┴───┐      ▼       ▼
   TAK     NIE    main   develop
    │       │      │
    ▼       ▼      ▼
release/* develop backport
    │              to develop
    ▼
   main
(przez PR)
```

---

## ✅ Checklist - Przed Merge

### Przed Merge feature → develop

- [ ] Testy nowego kodu przeszły (`pytest --no-cov`)
- [ ] Format i lint OK (`make format && make lint`)
- [ ] Conventional commit message
- [ ] Templates użyte z `.ai-templates/`
- [ ] `tenant_id` w queries (jeśli dotyczą DB)

### Przed Merge develop → release

- [ ] Develop jest stabilny (CI zielone)
- [ ] Wszystkie features są gotowe
- [ ] Version bump zaplanowany
- [ ] CHANGELOG będzie zaktualizowany na release

### Przed Merge release → main

- [ ] Wszystkie testy przeszły (CI ✅)
- [ ] Integration tests OK
- [ ] Benchmark smoke test OK
- [ ] Security scan OK
- [ ] Version bumped w `pyproject.toml`
- [ ] CHANGELOG zaktualizowany
- [ ] 2 approvals od maintainers
- [ ] Wszystkie conversations resolved

---

## 🛡️ Branch Protection - Podsumowanie

| Branch | Protection Level | Key Rules |
|--------|------------------|-----------|
| **feature*** | 🟢 Minimal | No protection, fast development |
| **develop** | 🟡 Medium | Require CI passing (1 Python) |
| **release*** | 🟠 High | 1 approval + all checks + up-to-date |
| **main** | 🔴 Maximum | 2 approvals + ALL checks + no force push |

---

**Wersja**: 2.0.0
**Data**: 2025-12-10
**Status**: 🔴 MANDATORY - Wymagane dla wszystkich
**Zmiana**: Dodano release branch jako bramę bezpieczeństwa
**Poprzedni model**: 3-fazowy (feature → develop → main)
**Aktualny model**: 4-fazowy (feature → develop → release → main)
