# Git Branching Strategy (RAE)

> **🚨 CRITICAL**: Read `CRITICAL_AGENT_RULES.md` first - contains mandatory rules!

RAE używa **hybrydowego podejścia** łączącego GitHub Flow (dla codziennej pracy) z Git Flow (dla major releases).

## 🚨 CRITICAL RULE: Testing on Branches

```
┌─────────────────────────────────────────────────────────┐
│ FEATURE BRANCH:  ❌ NO full test suite                  │
│                  ✅ Test ONLY new code (--no-cov)        │
│                                                          │
│ DEVELOP BRANCH:  ✅ FULL test suite (make test-unit)    │
│                  🚨 MANDATORY before merging to main!   │
│                                                          │
│ MAIN BRANCH:     ✅ CI runs full tests automatically    │
│                  🚨 Must ALWAYS be green!               │
└─────────────────────────────────────────────────────────┘
```

### ❌ FORBIDDEN on Feature Branches:
```bash
# ❌ NEVER DO THESE ON FEATURE BRANCH:
pytest                          # Runs ALL tests
pytest --cov                    # Full coverage
make test                       # Full suite
make test-unit                  # Only on develop!
make test-cov                   # Only on develop!
```

### ✅ ALLOWED on Feature Branches:
```bash
# ✅ Test ONLY your new code:
pytest --no-cov apps/memory_api/tests/services/test_my_feature.py
make test-focus FILE=apps/memory_api/tests/services/test_my_feature.py
```

## 🔄 Daily Workflow (GitHub Flow based)

### Tworzenie nowej funkcjonalności

```bash
# 1. Utwórz feature branch z develop
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# 2. Rozwijaj i testuj TYLKO nową funkcjonalność
# 🚨 CRITICAL: Uruchamiaj testy TYLKO dla nowych funkcji!
# ❌ NIE uruchamiaj wszystkich testów na feature branch!
#
# ✅ POPRAWNIE - testuj tylko nowy kod:
pytest --no-cov apps/memory_api/tests/test_my_new_code.py
# LUB
make test-focus FILE=apps/memory_api/tests/test_my_new_code.py

# 3. Commituj zgodnie z conventional commits
git add .
git commit -m "feat: add new feature description"

# 4. Push feature branch (opcjonalnie)
git push origin feature/your-feature-name

# 5. Merge do develop (lokalnie lub przez PR)
git checkout develop
git merge feature/your-feature-name --no-ff

# 6. 🚨 STRICT MERGE VERIFICATION (Zero-Diff Check)
# Must execute these checks BEFORE deleting feature branch:
# A. Check for unmerged commits (Must be empty)
git log feature/your-feature-name ^develop
# B. Check for diffs (Must be empty)
git diff develop...feature/your-feature-name
# IF ANY OUTPUT IS PRESENT -> MERGE FAILED. DO NOT PROCEED.

# 7. KRYTYCZNE: Uruchom WSZYSTKIE testy lokalnie na develop
make test-unit
make lint
make security-scan

# 8. Jeśli wszystkie testy przechodzą lokalnie i weryfikacja (6) OK:
git branch -d feature/your-feature-name
git checkout main
git merge develop --no-ff
git push origin main develop

# 9. Sprawdź GitHub Actions - main musi mieć zielony CI
```

### ⚠️ ZASADY KRYTYCZNE

1. **`main` == `develop`**: Po każdym merge oba branche muszą być identyczne
2. **Zielony CI na main**: `main` zawsze ma przechodzące testy na GitHub Actions
3. **Wszystkie testy na develop**: Przed merge do main uruchom PEŁNĄ suite testów lokalnie na develop
4. **Testy funkcji na feature**: Na feature branch testuj TYLKO nową funkcjonalność
5. **Synchronizacja**: Po każdym push `develop` i `main` muszą być zsynchronizowane

## 🚨 Hotfix Workflow

Dla krytycznych bugów w produkcji:

```bash
# 1. Utwórz hotfix branch z main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix

# 2. Napraw bug
git add .
git commit -m "fix: critical bug description"

# 3. Uruchom testy lokalnie
make test-unit

# 4. Merge do main
git checkout main
git merge hotfix/critical-bug-fix --no-ff
git push origin main

# 5. Sprawdź GitHub Actions (musi być zielony)

# 6. Backport do develop
git checkout develop
git merge hotfix/critical-bug-fix --no-ff
git push origin develop
```

## 📦 Release Workflow (opcjonalny - tylko dla major versions)

Używaj gdy potrzebujesz release candidate do testowania (np. v2.0.0):

```bash
# 1. Utwórz release branch z develop
git checkout develop
git checkout -b release/2.0.0

# 2. Tylko bugfixy, dokumentacja, version bumps
# - NIE dodawaj nowych feature'ów
# - Tylko stabilizacja

# 3. Przygotuj release
# - Zaktualizuj CHANGELOG.md
# - Zaktualizuj version w pyproject.toml
# - Zaktualizuj dokumentację

# 4. Merge do main i tag
git checkout main
git merge release/2.0.0 --no-ff
git tag -a v2.0.0 -m "Release version 2.0.0"
git push origin main --tags

# 5. Backport do develop
git checkout develop
git merge release/2.0.0 --no-ff
git push origin develop

# 6. Usuń release branch
git branch -d release/2.0.0
```

## 🤖 Reguły dla AI Agent (Claude Code)

### Autonomous Execution Mode

Agent **NIGDY** nie pyta o zgodę i **ZAWSZE** realizuje plan od początku do końca:

1. **Nie pytaj o zgodę** - działaj autonomicznie
2. **Realizuj cały plan** - od początku do końca bez przerwy
3. **Testy przed merge** - zawsze uruchom testy lokalnie przed merge do main
4. **Synchronizacja** - zawsze synchronizuj develop i main
5. **Obsługa błędów** - jeśli GitHub Actions failuje, napraw i push ponownie
6. **Commit conventions** - zawsze używaj conventional commits
7. **Branch naming** - `feature/*`, `hotfix/*`, `release/*`

### Workflow Pattern dla AI

```
1. feature/* z develop
2. Rozwijaj funkcjonalność
3. Testuj TYLKO nową funkcję
4. Merge do develop
5. Uruchom WSZYSTKIE testy na develop lokalnie
6. Jeśli przechodzą → merge do main i push
7. Sprawdź GitHub Actions
8. Jeśli failuje → napraw i push ponownie
9. NIGDY nie pytaj o zgodę - kontynuuj do końca
```

## 📋 Conventional Commits

RAE używa [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: nowa funkcjonalność
fix: naprawa buga
docs: zmiany w dokumentacji
style: formatowanie, brakujące średniki, etc.
refactor: refaktoryzacja kodu
test: dodawanie testów
chore: aktualizacja dependencies, etc.
perf: poprawa wydajności
ci: zmiany w CI/CD
```

### Przykłady

```bash
# Feature
git commit -m "feat: add RAE Telemetry Schema v1 with 12 attribute categories"

# Bug fix
git commit -m "fix(tests): fix test_setup_opentelemetry_disabled mock"

# Documentation
git commit -m "docs: add OpenTelemetry Research Guide"

# Breaking change
git commit -m "feat!: change API response format

BREAKING CHANGE: response now returns array instead of object"
```

## 🔍 Branch Naming Convention

```
feature/short-description       # Nowe funkcjonalności
hotfix/bug-description         # Szybkie poprawki
release/x.y.z                  # Przygotowanie release (opcjonalnie)
```

**Przykłady:**
- `feature/opentelemetry-improvements`
- `feature/pii-scrubber`
- `hotfix/test-failure-fix`
- `release/2.0.0`

## 📊 Status Branches

| Branch | Status | Purpose |
|--------|--------|---------|
| `main` | ✅ Zawsze zielony CI | Produkcja |
| `develop` | ✅ Zielony przed merge | Integracja |
| `feature/*` | ⚠️ Testuj nowe funkcje | Rozwój |
| `hotfix/*` | ✅ Zielony przed merge | Krytyczne fixy |
| `release/*` | ✅ Tylko stabilizacja | Major releases |

## 🚀 Deployment

- **`main`** = produkcja
- Każdy push do `main` uruchamia GitHub Actions
- Docker images budują się automatycznie
- `main` musi ZAWSZE mieć zielone testy

## 🛡️ Protection Rules

GitHub Branch Protection dla `main`:
- ✅ Require pull request reviews (opcjonalnie)
- ✅ Require status checks to pass (CI)
- ✅ Require branches to be up to date
- ✅ Include administrators

## 📚 Więcej informacji

- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
