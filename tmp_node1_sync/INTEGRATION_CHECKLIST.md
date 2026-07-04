# 🔍 Integration Checklist - Pre-Merge Verification

> **Purpose**: Use this checklist before merging any code to `develop` or `main` to ensure quality and consistency.
>
> **⚠️ CRITICAL**: This checklist verifies compliance with [CRITICAL_AGENT_RULES.md](./CRITICAL_AGENT_RULES.md). Read those 8 mandatory rules FIRST!

## ⚡ Quick Checklist (Essential)

Before merging to `develop` or `main`, verify ALL of these:

- [ ] **Code follows PROJECT_STRUCTURE.md** (correct file locations)
- [ ] **Code follows CONVENTIONS.md** (architecture patterns)
- [ ] **Design document was created** (for non-trivial changes)
- [ ] **Tests added for all layers** (Repository, Service, API)
- [ ] **All tests pass** (`make test-unit`)
- [ ] **Linting passes** (`make lint`)
- [ ] **Code formatted** (`make format`)
- [ ] **No secrets in code** (API keys, passwords)
- [ ] **Security: tenant_id in all queries**
- [ ] **Docstrings added** (Google style)
- [ ] **Structured logging added** (structlog)
- [ ] **No interactive commands used**
- [ ] **Conventional commit message** (feat/fix/docs/etc.)
- [ ] **CI passes on GitHub Actions**

## 📋 Detailed Checklist

### 1. Documentation & Design

#### 1.1 Design-First Protocol
- [ ] Design document created for significant changes (>50 lines or >2 files)
- [ ] Design includes: Problem, Solution, Architecture Impact, Implementation Plan
- [ ] Design approved by user (if ambiguous or breaking changes)
- [ ] Design document archived or linked in commit message

#### 1.2 Code Documentation
- [ ] All public functions have docstrings (Google style)
- [ ] Complex logic has inline comments explaining WHY (not WHAT)
- [ ] README.md updated if new feature affects usage
- [ ] API documentation updated if new endpoints added

#### 1.3 Architecture Documentation
- [ ] PROJECT_STRUCTURE.md updated if new patterns introduced
- [ ] CONVENTIONS.md updated if new conventions established
- [ ] .ai-templates/ updated if template improvements made

#### 1.4 Documentation Updates (RULE #8 - CRITICAL!)
**⚠️ Auto-generated (CI handles - NEVER EDIT!):**
- [ ] Did NOT edit `CHANGELOG.md` (CI generates from git history)
- [ ] Did NOT edit `STATUS.md` (CI generates project metrics)
- [ ] Did NOT edit `TODO.md` (CI extracts from code comments)
- [ ] Did NOT edit `docs/.auto-generated/` files
- [ ] Did NOT edit `docs/TESTING_STATUS.md` (CI generates from test runs)

**✅ Manual (Your responsibility - DO EDIT if needed!):**
- [ ] Updated `CONVENTIONS.md` if new patterns added
- [ ] Updated `PROJECT_STRUCTURE.md` if new file locations added
- [ ] Updated `docs/guides/` if new features added
- [ ] Updated `.ai-templates/README.md` if template changes made

> **Why this matters**: CI automatically overwrites auto-generated files. If you edit them, your changes will be lost!

### 2. Code Structure & Patterns

#### 2.1 File Locations (PROJECT_STRUCTURE.md)
- [ ] Repository files in `apps/memory_api/repositories/`
- [ ] Service files in `apps/memory_api/services/`
- [ ] API routes in `apps/memory_api/api/v1/`
- [ ] Models in `apps/memory_api/models/`
- [ ] Tests mirror source structure exactly
- [ ] Test files named `test_<module_name>.py`

#### 2.2 Layer Separation (CONVENTIONS.md)
- [ ] API layer only handles HTTP concerns
- [ ] Service layer contains all business logic
- [ ] Repository layer only does data access
- [ ] No SQL in services or routes
- [ ] No business logic in repositories or routes
- [ ] Layers communicate through proper interfaces

#### 2.3 Imports
- [ ] All imports are absolute (from `apps.`)
- [ ] No relative imports (`..` or `.`)
- [ ] No circular imports
- [ ] Imports organized: stdlib → third-party → local

#### 2.4 Dependency Injection
- [ ] Services use dependency injection in `__init__`
- [ ] No hard-coded dependencies
- [ ] Dependencies passed as parameters
- [ ] Easy to mock for testing

### 3. Code Quality

#### 3.1 Formatting
- [ ] `make format` executed (black + isort + ruff)
- [ ] No formatting warnings
- [ ] Line length ≤ 100 characters
- [ ] Consistent indentation (4 spaces)

#### 3.2 Linting
- [ ] `make lint` passes (ruff, black, isort, mypy)
- [ ] No linting errors
- [ ] No unused imports
- [ ] No undefined variables
- [ ] Type hints added where appropriate

#### 3.3 Code Smells
- [ ] No code duplication (DRY principle)
- [ ] Functions are small and focused (Single Responsibility)
- [ ] No deeply nested code (max 3 levels)
- [ ] No magic numbers (use constants)
- [ ] No commented-out code

### 4. Security

#### 4.1 Multi-Tenancy (CRITICAL!)
- [ ] ALL database queries include `tenant_id` in WHERE clause
- [ ] Routes use `Depends(get_and_verify_tenant_id)`
- [ ] No cross-tenant data leakage possible
- [ ] Row Level Security (RLS) enforced

#### 4.2 Secrets Management
- [ ] No API keys in code
- [ ] No passwords in code
- [ ] No tokens in code
- [ ] All secrets in `.env` or environment variables
- [ ] `.env` in `.gitignore`

#### 4.3 Input Validation
- [ ] All user input validated (Pydantic models)
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevention in responses
- [ ] No eval() or exec() calls

#### 4.4 Security Scan
- [ ] `make security` executed
- [ ] Critical vulnerabilities addressed
- [ ] Warnings reviewed and documented

### 5. Testing

#### 5.1 Test Coverage
- [ ] Tests added for all new code
- [ ] Repository tests (integration)
- [ ] Service tests (unit with mocks)
- [ ] API tests (integration with TestClient)
- [ ] Coverage ≥ 80% for new code

#### 5.2 Test Quality
- [ ] Tests follow AAA pattern (Arrange-Act-Assert)
- [ ] Test names are descriptive (`test_<action>_<condition>_<result>`)
- [ ] Tests are isolated (no interdependencies)
- [ ] Tests are deterministic (no flaky tests)
- [ ] Tests use appropriate markers (`@pytest.mark.unit`, etc.)

#### 5.3 Test Execution
- [ ] `make test-focus FILE=...` used during development
- [ ] `make test-unit` passes (full suite)
- [ ] No tests skipped without reason
- [ ] No `pytest.skip()` without explanation
- [ ] Test execution time reasonable (<5 min for unit tests)

#### 5.4 Test Philosophy (AGENTS_TEST_POLICY.md)
- [ ] Tests verify behavior, not implementation
- [ ] Tests are contracts, not snapshots
- [ ] Tests only changed when spec changes
- [ ] Code fixed, not tests (when tests fail correctly)

### 6. Logging & Monitoring

#### 6.1 Structured Logging
- [ ] Uses structlog (`logger = structlog.get_logger(__name__)`)
- [ ] Log format: `logger.info("event_name", field1=value1, field2=value2)`
- [ ] No string formatting in logs (`f"..."` or `%s`)
- [ ] Appropriate log levels (DEBUG, INFO, WARNING, ERROR, EXCEPTION)

#### 6.2 Error Logging
- [ ] All exceptions logged with context
- [ ] `logger.exception()` used in except blocks
- [ ] Stack traces included for unexpected errors
- [ ] Sensitive data not logged (passwords, tokens)

#### 6.3 Operational Logs
- [ ] Important operations logged (tenant_id, operation name)
- [ ] Request start/end logged at INFO level
- [ ] Performance metrics logged (execution time)
- [ ] Business events logged (user actions)

### 7. Error Handling

#### 7.1 Exception Handling
- [ ] All exceptions caught appropriately
- [ ] No bare `except:` clauses
- [ ] Specific exceptions caught before generic
- [ ] Exceptions re-raised or wrapped appropriately

#### 7.2 HTTP Error Responses
- [ ] Correct HTTP status codes used
  - 200 OK for successful GET/PATCH
  - 201 Created for successful POST
  - 204 No Content for successful DELETE
  - 400 Bad Request for invalid input
  - 401 Unauthorized for missing auth
  - 403 Forbidden for insufficient permissions
  - 404 Not Found for missing resources
  - 500 Internal Server Error for unexpected errors
- [ ] Error messages are user-friendly
- [ ] Internal error details not exposed to clients
- [ ] Consistent error response format

#### 7.3 Custom Exceptions
- [ ] Custom exceptions inherit from appropriate base class
- [ ] Exceptions include helpful error messages
- [ ] Exception hierarchy makes sense

### 8. Database & Data

#### 8.1 Queries
- [ ] Parameterized queries used ($1, $2, not string interpolation)
- [ ] SQL injection prevention
- [ ] Queries optimized (indexes considered)
- [ ] N+1 query problem avoided

#### 8.2 Transactions
- [ ] Transactions used for multi-step operations
- [ ] Proper rollback on errors
- [ ] Connection pooling used correctly

#### 8.3 Data Models
- [ ] Pydantic models for input/output
- [ ] Field validation with constraints
- [ ] Default values provided where appropriate
- [ ] Models have examples in schema

### 9. Git & Versioning

#### 9.1 Branching (BRANCHING.md)
- [ ] Feature branch created from `develop`
- [ ] Branch name follows pattern: `feature/description` or `fix/description`
- [ ] No direct commits to `main` or `develop`

#### 9.2 Commits
- [ ] Conventional commit format used
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation
  - `test:` for tests
  - `refactor:` for refactoring
  - `chore:` for maintenance
- [ ] Commit message is descriptive
- [ ] Commit includes WHY, not just WHAT
- [ ] One logical change per commit
- [ ] No "WIP" or "temp" commits in history

#### 9.3 Merge Process
- [ ] Tested only new features on feature branch
- [ ] Merged feature to develop: `git merge --no-ff`
- [ ] **Ran full test suite on develop** (CRITICAL!)
- [ ] Merged develop to main: `git merge --no-ff`
- [ ] Pushed both branches together: `git push origin main develop`
- [ ] GitHub Actions passes on main

### 10. CI/CD

#### 10.1 Local Verification
- [ ] `make format` executed
- [ ] `make lint` passes
- [ ] `make test-unit` passes
- [ ] `make security` reviewed

#### 10.2 GitHub Actions
- [ ] CI triggered on push
- [ ] All jobs pass (tests, linting, security)
- [ ] No warnings in CI output
- [ ] Build succeeds

#### 10.3 Post-Merge Verification
- [ ] GitHub Actions green on main
- [ ] No deployment errors
- [ ] Health checks pass
- [ ] Monitoring shows no issues

### 11. Performance

#### 11.1 Code Performance
- [ ] No obvious performance bottlenecks
- [ ] Async/await used correctly
- [ ] Database queries optimized
- [ ] Large data sets handled efficiently

#### 11.2 API Performance
- [ ] Response times acceptable (<500ms for simple queries)
- [ ] Pagination implemented for large result sets
- [ ] Rate limiting considered
- [ ] Caching used where appropriate

### 12. Backwards Compatibility

#### 12.1 API Changes
- [ ] No breaking changes to existing endpoints (unless major version)
- [ ] New fields added as optional
- [ ] Deprecated features marked clearly
- [ ] Migration path provided for breaking changes

#### 12.2 Database Changes
- [ ] Database migrations provided
- [ ] Migrations are reversible
- [ ] Migrations tested locally
- [ ] Data loss prevented

## 🚦 Quality Gates

### Gate 1: Local Development (Feature Branch)
✅ All of these must pass before merge to develop:
- Code formatted (`make format`)
- Linting passes (`make lint`)
- New tests pass (`make test-focus FILE=...`)

### Gate 2: Integration Testing (Develop Branch)
✅ All of these must pass before merge to main:
- Full test suite passes (`make test-unit`)
- Security scan reviewed (`make security`)
- No merge conflicts
- Documentation updated

### Gate 3: Production Ready (Main Branch)
✅ All of these must pass before deployment:
- GitHub Actions green
- All tests pass in CI
- Code reviewed (if team workflow)
- Deployment plan ready

## 🔄 Workflow Summary

```
1. Create feature branch from develop
   ↓
2. Implement feature (use templates)
   ↓
3. Run focused tests (make test-focus FILE=...)
   ↓
4. Format & lint (make format && make lint)
   ↓
5. Merge to develop
   ↓
6. **RUN FULL TEST SUITE ON DEVELOP** (CRITICAL!)
   ↓
7. If passes → merge to main
   ↓
8. Push both branches (git push origin main develop)
   ↓
9. Verify GitHub Actions green
   ↓
10. If CI fails → fix and repeat from step 6
```

## ⚠️ Critical Mistakes to Avoid

### ❌ Top 10 Integration Mistakes

1. **Pushing to main without full test suite on develop**
   - Result: Breaking main branch, CI fails
   - Fix: Always run `make test-unit` on develop first

2. **Missing tenant_id in queries**
   - Result: Security vulnerability, data leakage
   - Fix: Add `tenant_id` to ALL WHERE clauses

3. **Skipping design document**
   - Result: Code doesn't fit architecture, needs refactoring
   - Fix: Write design first, get approval, then code

4. **Using interactive commands**
   - Result: Blocks CI/automation
   - Fix: Use non-interactive alternatives (cat, Edit tool, etc.)

5. **Testing without --no-cov**
   - Result: Single test fails due to global coverage threshold
   - Fix: Use `make test-focus FILE=...` or `pytest --no-cov`

6. **Mixing layers (SQL in routes)**
   - Result: Untestable, unmaintainable code
   - Fix: Always API → Service → Repository

7. **Changing tests instead of code**
   - Result: Tests no longer verify correct behavior
   - Fix: Tests are contracts - fix code, not tests

8. **Not using templates**
   - Result: Inconsistent patterns, more refactoring
   - Fix: Always start with `.ai-templates/`

9. **Ignoring lint warnings**
   - Result: Code quality debt, technical debt
   - Fix: Fix ALL warnings before merge

10. **Leaving main with red CI**
    - Result: Blocks other developers, deployment issues
    - Fix: Fix immediately, push again until green

## ✅ Sign-Off

Before merging, agent must verify:

**I confirm that:**
- [ ] All items in Quick Checklist are checked
- [ ] All critical items in Detailed Checklist are verified
- [ ] Quality gates 1 & 2 passed (for develop)
- [ ] Quality gate 3 passed (for main)
- [ ] No known issues or technical debt introduced
- [ ] Code is production-ready

**Agent Signature**: [Your Agent ID]
**Date**: [YYYY-MM-DD]
**Branch**: [feature/branch-name]
**Commits**: [SHA1, SHA2, ...]

---

## 📚 Related Documentation

### Mandatory Reading (RULE #2: Work Autonomously!)
- **⚠️ CRITICAL_AGENT_RULES.md** - 8 mandatory rules (READ FIRST!)
- **ONBOARDING_GUIDE.md** - Getting started guide
- **PROJECT_STRUCTURE.md** - Where to put files
- **CONVENTIONS.md** - How to write code

### Supporting Documentation
- **.cursorrules** - Complete rules
- **docs/AGENTS_TEST_POLICY.md** - Testing philosophy (RULE #7)
- **docs/BRANCHING.md** - Git workflow (3-phase)
- **.ai-templates/** - Code templates (RULE #5)

> **Note on RULE #2 (Autonomous Work)**: By the time you're using this checklist, you should already know these patterns and work autonomously without asking permission for standard tasks. If you're unclear, re-read the mandatory documentation above!

---

**Last Updated**: 2025-12-04
**Maintained by**: AI Agent Code Quality System

**Remember**: This checklist exists to maintain high quality. Don't skip items - they save time in the long run!
