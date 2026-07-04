# 🛡️ BRANCH PROTECTION - GitHub Rules

> **Cel**: Chronić krytyczne branche przed przypadkowymi lub niebezpiecznymi zmianami
>
> **Status**: MANDATORY dla main, release; RECOMMENDED dla develop

---

## 📊 Podsumowanie Ochrony

| Branch | Protection Level | Key Rules |
|--------|------------------|-----------|
| main | 🔴 MAXIMUM | 2 approvals + ALL checks + no direct push |
| release/* | 🟠 HIGH | 1 approval + all checks + up-to-date |
| develop | 🟡 MEDIUM | CI passing (1 Python) + no force push |
| feature/* | 🟢 MINIMAL | No protection (fast development) |

---

## 1️⃣ MAIN BRANCH (Produkcja - ŚWIĘTY)

### Konfiguracja GitHub

```yaml
Branch: main

Require pull request before merging: ✅ ENABLED
  Required approvals: 2
  Dismiss stale reviews: ✅
  Require review from Code Owners: ✅
  Require approval of most recent push: ✅

Require status checks before merging: ✅ ENABLED
  Require branches to be up to date: ✅
  Required checks:
    - lint
    - test-full (Python 3.10)
    - test-full (Python 3.11)
    - test-full (Python 3.12)
    - test-mcp (Python 3.11)
    - benchmark-smoke
    - security
    - quality-gate
    - docker

Require conversation resolution: ✅ ENABLED

Restrict who can push: ✅ ENABLED
  Teams: core-maintainers

Allow force pushes: ❌ DISABLED
Allow deletions: ❌ DISABLED

Include administrators: ✅ ENABLED
```

### Co to oznacza?

| Rule | Znaczenie | Dlaczego |
|------|-----------|----------|
| 2 approvals | Wymaga zgody 2 maintainerów | Bezpieczeństwo - 4 eyes principle |
| Dismiss stale | Stare review tracą ważność po push | Wymusza re-review po zmianach |
| Code Owners | Musi zatwierdzić właściciel kodu | Eksperci decydują o swoich obszarach |
| Up-to-date | Musi być zsynchronizowany z main | Zapobiega merge conflicts |
| All checks | WSZYSTKIE CI muszą przejść | Zero tolerancji dla failingu |
| No force push | NIGDY nie nadpisuj historii | Historia git jest święta |
| No delete | Nie można usunąć brancha | Trwała dokumentacja |

### Jak Mergować do Main?

```bash
# ❌ ZABRONIONE:
git checkout main
git merge release/v1.2.0
git push origin main

# ✅ JEDYNA DROGA:
gh pr create --base main --head release/v1.2.0 \
  --title "Release v1.2.0" \
  --body "Production ready release"

# Następnie:
# 1. Poczekaj na 2 approvals
# 2. Poczekaj aż wszystkie checks przejdą
# 3. Resolve wszystkie conversations
# 4. Merge przez GitHub UI
```

---

## 2️⃣ RELEASE BRANCH (Stabilizacja)

### Konfiguracja GitHub

```yaml
Branch pattern: release/*

Require pull request before merging: ✅ ENABLED
  Required approvals: 1
  Dismiss stale reviews: ✅
  Require review from Code Owners: ✅

Require status checks before merging: ✅ ENABLED
  Require branches to be up to date: ✅
  Required checks:
    - lint
    - test-full (Python 3.10)
    - test-full (Python 3.11)
    - test-full (Python 3.12)
    - benchmark-smoke
    - security
    - quality-gate

Require conversation resolution: ✅ ENABLED

Restrict who can push: ✅ ENABLED
  Teams: maintainers

Allow force pushes: ❌ DISABLED
Allow deletions: ❌ DISABLED
```

### Workflow

```bash
# Tworzenie release branch (direktalnie z develop)
git checkout develop
git checkout -b release/v1.2.0
git push origin release/v1.2.0

# Dalsze commity (bugfixy, docs)
git commit -m "fix: critical bug"
git push origin release/v1.2.0

# Merge do main (przez PR)
gh pr create --base main --head release/v1.2.0
# Wymaga 1 approval + wszystkie checks
```

---

## 3️⃣ DEVELOP BRANCH (Integracja)

### Konfiguracja GitHub

```yaml
Branch: develop

Require pull request before merging: ❌ DISABLED
  (PR opcjonalne, dozwolone lokalne merge)

Require status checks before merging: ✅ ENABLED
  Require branches to be up to date: ❌ DISABLED
  Required checks:
    - lint
    - test-full (Python 3.11)

Restrict who can push: ❌ DISABLED
  (Wszyscy contributorzy mogą pushować)

Allow force pushes: ❌ DISABLED
Allow deletions: ❌ DISABLED
```

### Workflow

```bash
# Lokalny merge (szybszy)
git checkout develop
git merge feature/my-feature --no-ff
make test-unit  # MANDATORY!
git push origin develop

# LUB przez PR (dla code review)
gh pr create --base develop --head feature/my-feature
```

---

## 4️⃣ FEATURE BRANCHES (Rozwój)

### Konfiguracja GitHub

```yaml
Branch pattern: feature/*

No protection rules
```

### Dlaczego brak ochrony?

- ⚡ Szybki rozwój bez blokad
- 🔄 Można force push (jeśli prywatny branch)
- 🗑️ Można usuwać po merge
- 🚀 Maksymalna swoboda eksperymentowania

**Uwaga**: Jeśli feature branch jest współdzielony (2+ devs), umów się z zespołem czy force push jest OK.

---

## 🔐 CODEOWNERS FILE

### Lokalizacja
`.github/CODEOWNERS`

### Zawartość

```
# Domyślnie wszyscy maintainers
* @dreamsoft-pro/maintainers

# Critical files - require core team
/.github/workflows/* @dreamsoft-pro/core-maintainers
/CRITICAL_AGENT_RULES.md @dreamsoft-pro/core-maintainers
/AI_AGENT_MANIFEST.md @dreamsoft-pro/core-maintainers
/SESSION_START.md @dreamsoft-pro/core-maintainers
/AUTONOMOUS_OPERATIONS.md @dreamsoft-pro/core-maintainers
/BRANCH_STRATEGY.md @dreamsoft-pro/core-maintainers
/.ai-agent-rules.md @dreamsoft-pro/core-maintainers

# Security-sensitive
/apps/memory_api/security/* @dreamsoft-pro/security-team
/apps/memory_api/middleware/auth.py @dreamsoft-pro/security-team
/apps/memory_api/security/rbac_service.py @dreamsoft-pro/security-team

# Infrastructure
/infra/* @dreamsoft-pro/devops
/docker compose*.yml @dreamsoft-pro/devops
/.github/workflows/* @dreamsoft-pro/devops

# Core services (high-risk changes)
/apps/memory_api/services/* @dreamsoft-pro/core-maintainers
/apps/memory_api/repositories/* @dreamsoft-pro/core-maintainers

# Database
/infra/postgres/ddl/* @dreamsoft-pro/database-team
/infra/postgres/migrations/* @dreamsoft-pro/database-team

# Documentation (anyone can update)
/docs/* @dreamsoft-pro/maintainers
```

### Jak Działa?

1. PR modyfikuje plik w `/apps/memory_api/security/`
2. GitHub automatycznie requesta review od `@dreamsoft-pro/security-team`
3. PR nie może być merged bez approval od security team
4. Zwiększa bezpieczeństwo i quality

---

## ⚙️ KONFIGURACJA PRZEZ GITHUB API

### Skrypt Setup

```bash
#!/bin/bash
# scripts/setup_branch_protection.sh

REPO="dreamsoft-pro/RAE-agentic-memory"

# Main branch protection
gh api repos/$REPO/branches/main/protection -X PUT \
  --input - <<EOF
{
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 2,
    "require_last_push_approval": true
  },
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "lint",
      "test-full (Python 3.10)",
      "test-full (Python 3.11)",
      "test-full (Python 3.12)",
      "test-mcp (Python 3.11)",
      "benchmark-smoke",
      "security",
      "quality-gate",
      "docker"
    ]
  },
  "enforce_admins": true,
  "required_conversation_resolution": true,
  "restrictions": {
    "users": [],
    "teams": ["core-maintainers"],
    "apps": []
  },
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

# Release branch protection
gh api repos/$REPO/branches/release/*/protection -X PUT \
  --input - <<EOF
{
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "lint",
      "test-full (Python 3.10)",
      "test-full (Python 3.11)",
      "test-full (Python 3.12)",
      "benchmark-smoke",
      "security",
      "quality-gate"
    ]
  },
  "enforce_admins": false,
  "required_conversation_resolution": true,
  "restrictions": {
    "users": [],
    "teams": ["maintainers"],
    "apps": []
  },
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

# Develop branch protection
gh api repos/$REPO/branches/develop/protection -X PUT \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": false,
    "contexts": [
      "lint",
      "test-full (Python 3.11)"
    ]
  },
  "enforce_admins": false,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

echo "✅ Branch protection configured!"
```

### Uruchomienie

```bash
chmod +x scripts/setup_branch_protection.sh
./scripts/setup_branch_protection.sh
```

---

## 🚨 BYPASS PROTECTION (Emergency)

### Kiedy Używać?

**TYLKO** w sytuacjach emergency:
- Krytyczny hotfix w produkcji (main down)
- Security vulnerability wymaga natychmiastowej naprawy
- CI jest broken i blokuje wszystko

### Jak?

1. GitHub Settings → Branches → main → Edit
2. Tymczasowo wyłącz "Include administrators"
3. Push hotfix
4. **NATYCHMIAST** włącz z powrotem

**Uwaga**: To powinno się zdarzyć < 1 raz na rok!

---

## ✅ WERYFIKACJA KONFIGURACJI

### Checklist

- [ ] Main ma 2 required approvals
- [ ] Main wymaga wszystkich CI checks
- [ ] Main ma no force push
- [ ] Main ma no deletion
- [ ] Release ma 1 approval
- [ ] Release wymaga all checks
- [ ] Develop ma basic checks
- [ ] CODEOWNERS file exists
- [ ] Teams są skonfigurowane na GitHub

### Test

```bash
# Test 1: Próba direct push do main (powinno failować)
git checkout main
echo "test" >> test.txt
git commit -m "test"
git push origin main
# ❌ Expected: remote: error: GH006: Protected branch update failed

# Test 2: Próba force push do develop (powinno failować)
git push -f origin develop
# ❌ Expected: remote: error: GH006: Protected branch update failed

# Test 3: PR do main bez approvals (powinno być blocked)
gh pr create --base main --head release/test
# Status: Blocked (2 approvals required)
```

---

## 📊 PODSUMOWANIE MATRIX

| Operacja | main | release | develop | feature |
|----------|------|---------|---------|---------|
| Direct push | ❌ | ❌ | ✅ | ✅ |
| Force push | ❌ | ❌ | ❌ | ✅* |
| Delete branch | ❌ | ❌ | ❌ | ✅ |
| Merge without PR | ❌ | ❌ | ✅ | ✅ |
| Merge without approval | ❌ | ❌ | ✅ | ✅ |
| Merge with failing CI | ❌ | ❌ | ❌ | ✅ |

*tylko jeśli branch prywatny

---

**Wersja**: 1.0.0
**Data**: 2025-12-10
**Status**: 🔴 MANDATORY - Wymagane dla main, release
**Setup**: `scripts/setup_branch_protection.sh`
