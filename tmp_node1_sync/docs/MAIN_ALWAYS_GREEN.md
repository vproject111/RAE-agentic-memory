# Main Always Green Policy

## Overview

The **main always green** policy ensures that the `main` branch is always deployable and all CI tests pass. This is enforced through automated checks and branch protection rules.

## Policy Rules

### 1. Workflow

```
feature/* → develop (full CI tests) → main (protected)
```

**Never push directly to main!** All changes must:
1. Go through `develop` branch first
2. Pass **all** CI tests on `develop`
3. Only then merge to `main`

### 2. Branch Protection

**Main branch is protected:**
- ✅ Requires status checks to pass on develop before merge
- ✅ Pre-push hook validates develop CI status
- ✅ No force pushes allowed
- ✅ No direct pushes - only through develop

### 3. Pre-Push Hook

A pre-push hook (`.git/hooks/pre-push`) automatically checks:

```bash
# When pushing to main, verifies:
1. CI tests on develop are completed
2. CI tests on develop are green (conclusion: success)
3. Blocks push if develop CI is red or still running
```

**Output examples:**

✅ **Success:**
```
🔒 Main Always Green Policy - Checking develop status...
  Status: completed
  Conclusion: success
✅ Develop CI is green - push to main allowed
```

❌ **Blocked - Tests Running:**
```
❌ BLOCKED: CI tests on develop are still running!
   Wait for tests to complete before pushing to main.
   Check status: gh run list --branch develop --limit 1
```

❌ **Blocked - Tests Failed:**
```
❌ BLOCKED: CI tests on develop FAILED!
   Fix tests on develop first before merging to main.
   View logs: gh run view --branch develop
```

## Developer Workflow

### Standard Feature Development

```bash
# 1. Create feature branch
git checkout -b feature/my-feature develop

# 2. Make changes and commit
git add .
git commit -m "feat: add feature"

# 3. Push to feature branch (runs quick tests)
git push origin feature/my-feature

# 4. Merge to develop (runs FULL tests)
git checkout develop
git merge feature/my-feature --no-ff
git push origin develop

# 5. Wait for develop CI to be GREEN ✅
gh run list --branch develop --limit 1
# Watch for: status=completed, conclusion=success

# 6. Merge to main (protected by pre-push hook)
git checkout main
git merge develop --no-ff
git push origin main  # ← Hook validates develop CI here!
```

### Checking Develop CI Status

**Quick check:**
```bash
gh run list --branch develop --limit 1
```

**Detailed view:**
```bash
gh run view --branch develop
```

**Watch in real-time:**
```bash
watch -n 10 'gh run list --branch develop --limit 1'
```

### If Develop CI Fails

**DO NOT merge to main!** Instead:

1. **View failure logs:**
   ```bash
   gh run view --branch develop --log-failed
   ```

2. **Fix the issue on develop:**
   ```bash
   git checkout develop
   # Fix the code
   git add .
   git commit -m "fix: resolve CI failure"
   git push origin develop
   ```

3. **Wait for new CI run to pass**

4. **Then merge to main:**
   ```bash
   git checkout main
   git merge develop --no-ff
   git push origin main  # Now hook allows!
   ```

## Emergency Override

**⚠️ USE WITH EXTREME CAUTION!**

If you **must** bypass the pre-push hook (e.g., reverting a critical bug):

```bash
git push origin main --no-verify
```

**Rules for override:**
- Document reason in commit message
- Notify team immediately
- Fix forward ASAP with proper CI validation

## Local vs CI Environment Parity

To ensure local tests match CI behavior:

### 1. Use Same Python Version

```bash
# Check CI version in .github/workflows/ci.yml
python --version  # Should match CI (3.10, 3.11, 3.12)
```

### 2. Use Same Dependencies

```bash
# Sync with requirements files
pip install -r requirements-dev.txt
pip install -r apps/memory_api/requirements-base.txt
pip install -r apps/memory_api/requirements-test.txt
```

### 3. Use Same pytest Configuration

```bash
# Run tests exactly as CI does:
pytest -m "not integration and not llm and not contract and not performance"
```

### 4. Run Local Pre-Commit Checks

```bash
# Before pushing to develop, run:
make lint              # Black, isort, ruff
make test-unit         # Unit tests
make security-check    # Safety scan
```

## Troubleshooting

### "Hook not found" Error

```bash
# Re-install hook
chmod +x .git/hooks/pre-push
```

### "Cannot fetch develop CI status"

```bash
# Install gh CLI
# Ubuntu/Debian:
sudo apt install gh
# macOS:
brew install gh

# Authenticate
gh auth login
```

### "CI still in_progress for too long"

```bash
# Check if run is stuck
gh run view --branch develop

# If stuck, may need to re-run
gh run rerun <run-id>
```

### Local Tests Pass, CI Fails

**Common causes:**

1. **Environment differences:**
   - Check Python version matches
   - Check dependencies are up to date

2. **Missing services:**
   - CI has postgres/redis/qdrant running
   - Mock external services in tests

3. **Timing issues:**
   - Add explicit waits in async tests
   - Use `freezegun` for time-dependent tests

4. **Coverage threshold:**
   - CI enforces 65% coverage minimum
   - Run locally: `pytest --cov --cov-fail-under=65`

## Benefits

✅ **Deployable main:** Always safe to deploy from main
✅ **Reduced incidents:** Catch issues before production
✅ **Clear history:** Clean, passing commits on main
✅ **Confidence:** Team trusts main branch
✅ **Fast rollback:** Any main commit can be deployed

## Related Documentation

- [RAE-CI-QUALITY-IMPLEMENTATION-PLAN.md](RAE-CI-QUALITY-IMPLEMENTATION-PLAN.md) - Full CI quality system
- [AGENT_TESTING_GUIDE.md](AGENT_TESTING_GUIDE.md) - Testing best practices
- [CRITICAL_AGENT_RULES.md](../CRITICAL_AGENT_RULES.md) - Rule #3: Workflow discipline

## Metrics

Track main branch health:

```bash
# Check main CI history
gh run list --branch main --limit 10

# Should show:
# ✅ All runs: conclusion=success
# ❌ Any failures → investigate immediately
```

**Target SLO:** 99.5% success rate on main (< 1 failure per 200 commits)

---

**Remember:** Main always green = Production always stable 🚀
