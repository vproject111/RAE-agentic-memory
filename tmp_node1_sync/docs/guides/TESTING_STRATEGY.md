# RAE Testing Strategy & Quality Assurance

## 📊 Overview

**RAE Agentic Memory** employs a comprehensive, multi-layered testing strategy designed to ensure code quality, prevent regressions, and support AI-generated code.

**Current Coverage:** 48% → **Target:** 75%+
**Test Count:** 640+ tests
**CI Runtime:** 4-5 minutes (optimized with smart selection)

---

## 🏗️ Testing Pyramid

```
                  E2E Tests (5%)
                 ┌─────────────┐
                 │  Smoke Tests │
                 └─────────────┘
               Integration Tests (15%)
            ┌──────────────────────┐
            │  Service Integration  │
            │  Database + Redis     │
            └──────────────────────┘
         Contract & Architectural Tests (10%)
      ┌────────────────────────────────────┐
      │  API Contracts │ Layer Isolation    │
      │  OpenAPI Schema │ Complexity Limits │
      └────────────────────────────────────┘
                Unit Tests (70%)
    ┌──────────────────────────────────────────┐
    │  Core Logic │ Services │ Utilities        │
    │  Fast (<1ms) │ Isolated │ Comprehensive   │
    └──────────────────────────────────────────┘
```

---

## 🎯 Test Types

### 1. Unit Tests (70% of test suite)

**Purpose:** Test individual functions/methods in isolation
**Speed:** <1ms per test
**Coverage Target:** 75%+

```python
# apps/memory_api/tests/core/test_state.py
def test_state_initialization_with_valid_data():
    """Test State object creation with valid data"""
    state = State(memory_layers={"em": [], "sm": []}, budget={"tokens": 1000})
    assert state.memory_layers is not None
    assert state.budget["tokens"] == 1000
```

**Best Practices:**
- Test one thing per test
- Use descriptive names
- Mock external dependencies
- Fast execution (<100ms)

### 2. Integration Tests (15% of test suite)

**Purpose:** Test interactions between components
**Speed:** ~100-500ms per test
**Coverage Target:** Key workflows

```python
# tests/integration/test_memory_workflow.py
@pytest.mark.integration
async def test_full_memory_workflow(db_connection, vector_store):
    """Test complete memory storage and retrieval"""
    memory_id = await store_memory(content="Test", layer="em")
    results = await query_memory("Test", k=5)
    assert len(results) > 0
    assert results[0].id == memory_id
```

**Best Practices:**
- Test realistic scenarios
- Use test database/services
- Clean up after each test
- Allow longer execution

### 3. Architectural Tests (NEW!)

**Purpose:** Enforce code quality and design principles
**Speed:** <1s total
**Validation:** Every CI run

```python
# tests/architecture/test_architecture.py
def test_core_layer_isolation():
    """Ensure core/ doesn't import from api/ or services/"""
    # Validates architectural boundaries
```

**Checks:**
- ✅ Layer isolation (core → models, NOT core → api)
- ✅ Max file length (800 lines)
- ✅ Max complexity (McCabe < 15)
- ✅ No circular dependencies
- ✅ No hardcoded secrets
- ✅ No bare except clauses

### 4. Contract Tests (NEW!)

**Purpose:** Prevent API breaking changes
**Speed:** <5s total
**Validation:** Every PR

```python
# tests/contracts/test_api_contracts.py
@pytest.mark.contract
def test_memory_store_response_schema(client):
    """Ensure /v1/memory/store maintains response schema"""
    response = client.post("/v1/memory/store", json={...})
    assert "id" in response.json()
    assert "created_at" in response.json()
    # Ensures backward compatibility
```

**Checks:**
- ✅ Response schemas unchanged
- ✅ Required fields present
- ✅ Field types consistent
- ✅ No removed endpoints

### 5. Performance Tests (NEW!)

**Purpose:** Prevent performance regressions
**Speed:** Benchmark-based
**Validation:** CI on develop/main

```python
# tests/performance/test_performance.py
@pytest.mark.performance
def test_memory_query_performance(benchmark):
    """Ensure query completes in <200ms"""
    result = benchmark(query_memory, "test")
    assert benchmark.stats.mean < 0.2
```

**Thresholds:**
- Query operation: <200ms
- Embedding generation: <500ms
- Graph traversal: <100ms
- Bulk insert (100 items): <1s

### 6. Mutation Testing (NEW!)

**Purpose:** Test quality of tests (do tests catch bugs?)
**Schedule:** Weekly (Sunday 2 AM)
**Target:** 70%+ mutation score

```bash
# Runs automatically via .github/workflows/mutation-testing.yml
mutmut run --paths-to-mutate=apps/memory_api/core/
```

**What it does:**
- Introduces small bugs (mutations) into code
- Runs tests against mutated code
- Tests should fail if they're effective
- Score = % of mutations caught

---

## 🚀 Smart Test Strategy

### Feature Branch: Smart Selection (FAST)

**Goal:** Quick feedback without wasting CI credits

```yaml
# Runs ONLY affected tests
pytest --testmon -x
```

**What runs:**
- ✅ Quick tests (1-2 min)
- ✅ Only tests affected by changes
- ✅ Lint + Quality Gate
- ✅ Security scan
- ❌ NOT full test suite
- ❌ NOT integration tests
- ❌ NOT all Python versions

**When:** Every push to feature/*

### Develop/Main: Full Validation (THOROUGH)

**Goal:** Comprehensive validation before production

```yaml
# Runs ALL tests
pytest -m "not integration and not llm"
pytest -m "integration"
pytest tests/architecture/
pytest -m contract
```

**What runs:**
- ✅ Full test suite (640+ tests)
- ✅ Integration tests
- ✅ Architectural tests
- ✅ Contract tests
- ✅ Python 3.10, 3.11, 3.12
- ✅ Coverage tracking
- ✅ Flaky test detection (3x runs)

**When:** Push to main/develop, or [full-test] in commit message

### Pull Requests: AI Review + Validation

**Goal:** Human-level code review with AI assistance

```yaml
# AI Code Review (Claude Sonnet 4.5)
python scripts/ai_code_review.py
```

**What happens:**
- ✅ AI reviews diff for security, performance, quality
- ✅ Automated PR comment with feedback
- ✅ Contract tests verify API compatibility
- ✅ Architectural tests enforce design
- ✅ Full test suite validates correctness

**When:** PR opened/synchronized

---

## 📊 Coverage Strategy

### Current Status:
- **Overall:** 48% → Target: 75%
- **Core:** 65% → Target: 85%
- **Services:** 55% → Target: 80%
- **API:** 50% → Target: 75%

### Enforcement:
```ini
# pytest.ini
--cov-fail-under=65  # Increased from 48%
```

### Trend Tracking:
```bash
# Prevents coverage regression >2%
python scripts/check_coverage_trend.py current.xml previous.xml
```

### Iterative Improvement:
See `docs/guides/GEMINI_TEST_COVERAGE_GUIDE.md` for step-by-step instructions on increasing coverage.

---

## 🛠️ Tools & Infrastructure

### Testing Framework:
- **pytest** - Test runner
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage tracking
- **pytest-testmon** - Smart test selection
- **pytest-benchmark** - Performance testing
- **pytest-json-report** - Flaky test detection

### Quality Tools:
- **mutmut** - Mutation testing
- **ruff** - Fast linting
- **black** - Code formatting
- **mypy** - Type checking
- **anthropic** - AI code review

### CI/CD:
- **GitHub Actions** - CI/CD platform
- **Codecov** - Coverage reporting
- **Pre-commit hooks** - Local validation

---

## 🔄 Development Workflow

### 1. Local Development (Feature Branch)

```bash
# 1. Create feature branch
git checkout -b feature/my-feature develop

# 2. Write code + tests
# ...

# 3. Run affected tests (FAST)
pytest --testmon -x

# 4. Pre-commit hooks run automatically
# - Black, isort, ruff
# - Quick validation
# - Affected tests only

# 5. Push to GitHub
git push origin feature/my-feature

# 6. CI runs smart selection
# - 1-2 minutes
# - Only affected tests
# - Quick feedback
```

### 2. Ready for Review (PR to Develop)

```bash
# 1. Create PR
gh pr create --base develop --title "feat: my feature"

# 2. AI Code Review runs automatically
# - Claude analyzes diff
# - Comments on PR with feedback

# 3. Full test suite runs
# - All 640+ tests
# - Python 3.10, 3.11, 3.12
# - Integration tests
# - Architectural tests
# - Contract tests

# 4. Coverage checked
# - Must be ≥65%
# - Cannot decrease >2%

# 5. Merge to develop (if all pass ✅)
```

### 3. Production Release (Develop → Main)

```bash
# 1. Merge develop to main
git checkout main
git merge --no-ff develop

# 2. Full validation runs AGAIN
# - Paranoid mode: double-check everything
# - All tests, all checks

# 3. Mutation testing (weekly)
# - Tests the tests
# - Ensures test quality

# 4. Deploy to production (if all pass ✅)
```

---

## 📈 Quality Metrics

### Test Quality:
- **Mutation Score:** 70%+ (tests catch bugs)
- **Flaky Test Rate:** <1% (reliable CI)
- **Test Speed:** <5 min full suite (fast feedback)

### Code Quality:
- **Coverage:** 75%+ (well-tested)
- **Complexity:** McCabe <15 (maintainable)
- **File Length:** <800 lines (readable)

### CI Efficiency:
- **Feature Branch:** 1-2 min (smart selection)
- **Develop/Main:** 4-5 min (full validation)
- **PR Review:** <10 min total (automated)

---

## 🆘 Troubleshooting

### "Tests are too slow"
```bash
# Use smart selection
pytest --testmon -x

# Run only unit tests
pytest -m "not integration"

# Parallelize
pytest -n auto
```

### "Coverage dropped below 65%"
```bash
# Check missing lines
pytest --cov=apps --cov-report=term-missing

# See HTML report
pytest --cov=apps --cov-report=html
open htmlcov/index.html

# Follow Gemini guide
docs/guides/GEMINI_TEST_COVERAGE_GUIDE.md
```

### "Test is flaky"
```bash
# Run test 10 times
pytest test_file.py::test_name --count=10

# Debug with verbose
pytest test_file.py::test_name -vvs

# Check for:
# - Async race conditions
# - Shared state between tests
# - Time-based assertions
# - External dependencies
```

### "CI is failing but tests pass locally"
```bash
# Run with same environment
docker compose -f docker compose.test.yml up

# Run full suite
pytest -m "not integration and not llm"

# Check architectural tests
pytest tests/architecture/

# Check contract tests
pytest -m contract
```

---

## 📚 Resources

### Documentation:
- **Test Coverage Guide:** `docs/guides/GEMINI_TEST_COVERAGE_GUIDE.md`
- **API Reference:** `docs/reference/api/api_reference.md`
- **Architecture:** `docs/reference/architecture/rae-mathematical-formalization.md`

### External:
- **Pytest:** https://docs.pytest.org/
- **Coverage.py:** https://coverage.readthedocs.io/
- **Mutmut:** https://mutmut.readthedocs.io/

---

## ✅ Quick Reference

```bash
# Local development
pytest --testmon -x                    # Smart selection
pytest -v                               # Verbose output
pytest --cov=apps --cov-report=html    # Coverage report

# Specific test types
pytest -m unit                          # Unit tests only
pytest -m integration                   # Integration tests
pytest -m architecture                  # Architectural tests
pytest -m contract                      # Contract tests
pytest -m performance                   # Performance tests

# CI simulation
pytest -m "not integration and not llm" # Full unit suite
pytest tests/architecture/              # Architectural checks
pytest -m contract                      # Contract checks

# Debugging
pytest test_file.py::test_name -vvs    # Single test, verbose
pytest --lf                             # Last failed
pytest --pdb                            # Drop into debugger on failure
```

---

**Last Updated:** 2025-12-04
**Maintained by:** RAE Development Team
**Questions?** See troubleshooting section or ask in #engineering
