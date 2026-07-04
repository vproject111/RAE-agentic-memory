# 🌍 PUBLIC REPO STRATEGY - Strategy for Public Repo

> **Goal**: Securely manage an open-source public repository
>
> **Status**: MANDATORY for RAE as a public repo

---

## 🎯 Branch Model for Open Source

```
EXTERNAL CONTRIBUTORS:
fork → feature/* → PR to develop (ONLY!)
                     ↓
                  Code Review
                     ↓
                  Merge to develop

MAINTAINERS (Internal):
feature/* → develop → release → main
```

**Key principle**: Externals can target ONLY `develop`, NEVER `main` or `release`.

---

## 🔐 SECURITY

### 1. Secrets and API Keys

| Element | Status | Protection |
|---------|--------|------------|
| API Keys | ❌ NEVER in repo | `.env` + `.gitignore` |
| Passwords | ❌ NEVER in repo | Secrets management |
| Private keys | ❌ NEVER in repo | Vault/GitHub Secrets |
| `.env.example` | ✅ OK | No values, only keys |
| Test fixtures | ⚠️ Caution | Use fake data |

### 2. Automated Checks

```yaml
# .github/workflows/pr-security-check.yml
name: PR Security Check

on:
  pull_request_target:  # Safe for external PRs
    types: [opened, synchronize]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}

      - name: Check for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}

      - name: Check for large files
        run: |
          find . -type f -size +10M | while read file; do
            echo "❌ Large file: $file"
            exit 1
          done

      - name: Check for sensitive paths
        run: |
          if git diff --name-only ${{ github.event.pull_request.base.sha }} | grep -E '\.env$|\.pem$|\.key$'; then
            echo "❌ Sensitive file detected"
            exit 1
          fi
```

---

## 🚪 EXTERNAL CONTRIBUTORS

### Requirements for PRs

| Requirement | Mandatory? | Checked by |
|-------------|------------|------------|
| DCO sign-off | ✅ YES | dcoapp/app |
| Target = develop | ✅ YES | PR check workflow |
| Passing CI | ✅ YES | GitHub Actions |
| Code review | ✅ YES | Maintainers |
| CONTRIBUTING.md | ✅ YES | Manual check |
| Conventional commits | ✅ YES | commitlint |

### DCO (Developer Certificate of Origin)

```bash
# Each commit must be signed
git commit -s -m "feat: add feature X"

# Adds to commit message:
Signed-off-by: Jan Kowalski <jan@example.com>
```

**DCO checking workflow**:
```yaml
# .github/workflows/dco.yml
name: DCO Check

on: [pull_request]

jobs:
  dco:
    runs-on: ubuntu-latest
    steps:
      - uses: dcoapp/app@v1
```

### Workflow for Externals

```bash
# 1. Fork repo
https://github.com/dreamsoft-pro/RAE-agentic-memory
[Click "Fork"]

# 2. Clone fork
git clone https://github.com/your-username/RAE-agentic-memory
cd RAE-agentic-memory

# 3. Add upstream
git remote add upstream https://github.com/dreamsoft-pro/RAE-agentic-memory

# 4. Create feature branch
git checkout develop
git pull upstream develop
git checkout -b feature/my-contribution

# 5. Implement
# [code...]

# 6. Commit with DCO
git commit -s -m "feat: add my feature"

# 7. Push to fork
git push origin feature/my-contribution

# 8. Create PR (via GitHub UI)
# Base: dreamsoft-pro/RAE-agentic-memory:develop
# Head: your-username/RAE-agentic-memory:feature/my-contribution
```

---

## ⚠️ FORBIDDEN CHANGES (Externals)

### We DO NOT accept PRs that:

| Change | Why forbidden |
|--------|---------------|
| `.github/workflows/*` | Security risk - CI/CD manipulation |
| `/apps/memory_api/security/*` | Security-sensitive code |
| `/infra/*` | Infrastructure changes require deep review |
| `CRITICAL_AGENT_RULES.md` | Core policies - internal only |
| Direct to `main` or `release` | Only maintainers via release process |
| Large binary files (>10MB) | Bloats repository |
| Secrets/credentials | Security violation |

### Automated Blocking

```yaml
# .github/workflows/pr-validation.yml
name: PR Validation

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Check target branch
        if: |
          github.event.pull_request.base.ref != 'develop' &&
          github.event.sender.login != 'dreamsoft-pro'
        run: |
          echo "❌ External PRs must target 'develop' branch"
          echo "Current target: ${{ github.event.pull_request.base.ref }}"
          exit 1

      - name: Check forbidden paths
        uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - run: |
          CHANGED=$(git diff --name-only HEAD^ HEAD)

          FORBIDDEN=(
            ".github/workflows/"
            "apps/memory_api/security/"
            "infra/"
            "CRITICAL_AGENT_RULES.md"
          )

          for path in "${FORBIDDEN[@]}"; do
            if echo "$CHANGED" | grep -q "^$path"; then
              if [ "${{ github.event.sender.login }}" != "dreamsoft-pro" ]; then
                echo "❌ Forbidden path for external contributors: $path"
                exit 1
              fi
            fi
          done
```

---

## 👥 CODEOWNERS (Enhanced for Public Repo)

```
# .github/CODEOWNERS

# Everything by default
* @dreamsoft-pro/maintainers

# Critical files - ONLY core team
/.github/workflows/* @dreamsoft-pro/core-maintainers
/CRITICAL_AGENT_RULES.md @dreamsoft-pro/core-maintainers
/AI_AGENT_MANIFEST.md @dreamsoft-pro/core-maintainers
/SESSION_START.md @dreamsoft-pro/core-maintainers
/AUTONOMOUS_OPERATIONS.md @dreamsoft-pro/core-maintainers
/BRANCH_STRATEGY.md @dreamsoft-pro/core-maintainers

# Security - ONLY security team
/apps/memory_api/security/* @dreamsoft-pro/security-team
/apps/memory_api/middleware/auth.py @dreamsoft-pro/security-team

# Infrastructure - ONLY devops
/infra/* @dreamsoft-pro/devops
/docker compose*.yml @dreamsoft-pro/devops

# Core services - review by core team
/apps/memory_api/services/* @dreamsoft-pro/core-maintainers
/apps/memory_api/repositories/* @dreamsoft-pro/core-maintainers

# Public contributions welcome (documentation, tests)
/docs/* @dreamsoft-pro/maintainers
/tests/* @dreamsoft-pro/maintainers
/examples/* @dreamsoft-pro/maintainers
```

---

## 📋 REVIEW PROCESS (External PRs)

### Checklist for Reviewers

Before approving an external PR, check:

- [ ] ✅ Target branch = `develop`
- [ ] ✅ DCO sign-off present
- [ ] ✅ Conventional commit format
- [ ] ✅ All CI checks passing
- [ ] ✅ No secrets in code
- [ ] ✅ No large binary files
- [ ] ✅ No changes to forbidden paths
- [ ] ✅ Tests added for new code
- [ ] ✅ Documentation updated
- [ ] ✅ Code quality (follows CONVENTIONS.md)
- [ ] ✅ No malicious code
- [ ] ✅ License compatible (MIT)

### Review Time

| PR Size | Expected Review Time |
|---------|----------------------|
| Trivial (<10 lines) | 1-2 days |
| Small (<100 lines) | 2-3 days |
| Medium (<500 lines) | 3-5 days |
| Large (>500 lines) | 5-10 days |

**Note**: Large PRs are harder to review. We encourage smaller, more frequent PRs!

---

## 🏷️ LABEL SYSTEM

### Labels for PRs

| Label | When | Who sets |
|-------|------|----------|
| `external-contribution` | PR from non-maintainer | Automatic (bot) |
| `needs-review` | Awaiting review | Automatic |
| `changes-requested` | Requires fixes | Reviewer |
| `approved` | Approved | Reviewer |
| `security-review` | Requires security review | Automatic (if security paths) |
| `breaking-change` | Breaks API | Author or reviewer |
| `documentation` | Docs only | Author |

### Automated Labelling

```yaml
# .github/workflows/auto-label.yml
name: Auto Label

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v4
        with:
          configuration-path: .github/labeler.yml
```

```yaml
# .github/labeler.yml
'external-contribution':
  - '!maintainers/**'

'documentation':
  - 'docs/**'
  - '*.md'

'security-review':
  - 'apps/memory_api/security/**'
  - 'apps/memory_api/middleware/auth.py'

'tests':
  - 'tests/**'
  - '**/*_test.py'
  - '**/test_*.py'
```

---

## 🤝 CONTRIBUTOR LICENSE AGREEMENT (CLA)

### Do we need a CLA?

**For MIT License: NO**

The MIT license is sufficiently permissive. A CLA is not required.

However, we require a **DCO (Developer Certificate of Origin)** which is a lighter alternative.

### DCO vs CLA

| Aspect | DCO | CLA |
|--------|-----|-----|
| Complexity | Simple | Complex |
| Sign-off | Every commit | One-time |
| Legal | Sufficient | Complete |
| For MIT | ✅ Recommended | ❌ Overkill |

---

## 📊 STATISTICS AND TRANSPARENCY

### Public Dashboard

We publicly provide:
- ✅ Test coverage (codecov badge)
- ✅ CI status (GitHub Actions badge)
- ✅ Security scan results (Snyk/GitHub)
- ✅ License (MIT badge)
- ✅ Release notes (CHANGELOG.md)

### README Badges

```markdown
[![Tests](https://github.com/dreamsoft-pro/RAE-agentic-memory/workflows/CI/badge.svg)](https://github.com/dreamsoft-pro/RAE-agentic-memory/actions)
[![Coverage](https://codecov.io/gh/dreamsoft-pro/RAE-agentic-memory/branch/main/graph/badge.svg)](https://codecov.io/gh/dreamsoft-pro/RAE-agentic-memory)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

---

## 🎓 EXTERNAL ONBOARDING

### CONTRIBUTING.md (Key document)

Must contain:
1. **How to contribute** - step-by-step
2. **Code of conduct** - rules of conduct
3. **Development setup** - how to run locally
4. **Testing** - how to test changes
5. **PR process** - how to create a good PR
6. **Review timeline** - what to expect

### Good First Issues

Label `good-first-issue` for simple tasks:
- Documentation fixes
- Test coverage improvement
- Small bug fixes
- Code formatting

```yaml
# .github/workflows/label-good-first-issues.yml
# Automatically label simple issues
```

---

## ⚖️ LICENSE ENFORCEMENT

### MIT License

RAE uses the MIT License - very permissive.

**Requirements**:
- ✅ Retain copyright notice
- ✅ Retain license text
- ✅ Can be used commercially
- ✅ Can be modified
- ✅ Can be distributed

**Not required**:
- ❌ Share source code (can fork closed-source)
- ❌ Same license for derivative works

### License Check

```yaml
# .github/workflows/license-check.yml
name: License Check

on: [pull_request]

jobs:
  license:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check license headers
        run: |
          # Check if every .py has a license header
          python scripts/check_license_headers.py
```

---

## 🚨 SECURITY POLICY

### `SECURITY.md`

```markdown
# Security Policy

## Reporting a Vulnerability

**DO NOT** open a public issue for security vulnerabilities.

Instead, email security@dreamsoft-pro.com with:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

## Security Update Process

1. Receive report → Verify (48h)
2. Develop fix → Test (1 week)
3. Private security advisory (GitHub)
4. Release hotfix
5. Public disclosure (after fix deployed)

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | ✅        |
| develop | ⚠️ Beta   |
| < 1.0   | ❌        |
```

---

## ✅ CHECKLIST - Setup Public Repo

### Initial Setup

- [ ] Repository set to Public on GitHub
- [ ] LICENSE file added (MIT)
- [ ] CODE_OF_CONDUCT.md added
- [ ] CONTRIBUTING.md added
- [ ] SECURITY.md added
- [ ] README badges added
- [ ] .github/CODEOWNERS configured
- [ ] Branch protection enabled (main, release)
- [ ] GitHub Teams created (maintainers, core-maintainers, security)

### CI/CD for External PRs

- [ ] PR validation workflow (target branch check)
- [ ] DCO check workflow
- [ ] Security scan (TruffleHog)
- [ ] Forbidden paths check
- [ ] Auto-labelling workflow
- [ ] License check

### Documentation

- [ ] PUBLIC_REPO_STRATEGY.md (this document)
- [ ] Contributor guidelines clear
- [ ] Setup instructions in README
- [ ] API documentation published

---

**Version**: 1.0.0
**Date**: 2025-12-10
**Status**: 🔴 MANDATORY - For public repos
**License**: MIT
