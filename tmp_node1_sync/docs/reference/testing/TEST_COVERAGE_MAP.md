# Test Coverage Map

## Overview

This document maps RAE features to their test coverage, providing visibility into what is tested and where.

**Test Locations**: `tests/`, `apps/memory_api/tests/`

## Coverage Summary

| Category | Unit Tests | Integration Tests | E2E Tests | Coverage % |
|----------|------------|-------------------|-----------|------------|
| **Core Memory** | ✅ High | ✅ High | ✅ Medium | ~85% |
| **GraphRAG** | ✅ High | ✅ High | ✅ Medium | ~80% |
| **Reflection Engine V2** | ✅ High | ✅ Medium | ⚠️ Low | ~75% |
| **Background Workers** | ✅ Medium | ✅ High | ✅ High | ~80% |
| **Rules Engine** | ✅ High | ✅ Medium | ⚠️ Low | ~70% |
| **Cost Guard** | ✅ High | ✅ High | ✅ Medium | ~85% |
| **Multi-Tenancy** | ✅ High | ✅ High | ✅ High | ~90% |
| **LLM Profiles** | ✅ High | ✅ Medium | ⚠️ Low | ~70% |
| **API Endpoints** | ✅ High | ✅ High | ✅ High | ~88% |
| **Integrations** | ⚠️ Medium | ⚠️ Low | ⚠️ Low | ~60% |

**Overall Coverage**: ~78%

## Feature → Test Mapping

### Core Memory Operations

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| **Memory Storage** | `test_memory_repository.py` | `test_memory_storage_integration.py` | `test_e2e_memory.py` |
| **Memory Retrieval** | `test_memory_repository.py` | `test_memory_retrieval_integration.py` | `test_e2e_memory.py` |
| **Semantic Search** | `test_hybrid_search.py` | `test_semantic_search_integration.py` | `test_e2e_search.py` |
| **Memory Layers** | `test_memory_layers.py` | `test_layer_integration.py` | - |
| **Memory Importance** | `test_importance_scoring.py` | `test_importance_integration.py` | - |
| **Memory Deletion** | `test_memory_repository.py` | `test_deletion_integration.py` | `test_e2e_memory.py` |

**Test Files**:
- `tests/unit/test_memory_repository.py`
- `tests/integration/test_memory_storage.py`
- `tests/e2e/test_memory_operations.py`
- `apps/memory_api/tests/test_memory_*.py`

### GraphRAG

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| **Graph Extraction** | `test_graph_extraction.py` | `test_graph_extraction_integration.py` | `test_e2e_graphrag.py` |
| **Entity Resolution** | `test_entity_resolution.py` | `test_entity_resolution_integration.py` | - |
| **Community Detection** | `test_community_detection.py` | `test_community_integration.py` | - |
| **Graph Query** | `test_graph_query.py` | `test_graph_query_integration.py` | `test_e2e_graphrag.py` |
| **Multi-hop Reasoning** | `test_graph_algorithms.py` | `test_multihop_integration.py` | `test_e2e_graphrag.py` |

**Test Files**:
- `tests/unit/test_graph_*.py`
- `tests/integration/test_graphrag.py`
- `apps/memory_api/tests/test_graph_extraction.py`

### Reflection Engine V2

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| **Reflection Generation** | `test_reflection_engine_v2.py` | `test_reflection_integration.py` | - |
| **Failure Reflection** | `test_reflection_engine_v2.py` | `test_reflection_failure.py` | - |
| **Success Reflection** | `test_reflection_engine_v2.py` | `test_reflection_success.py` | - |
| **Reflection Storage** | `test_reflection_storage.py` | `test_reflection_integration.py` | - |
| **Reflection Query** | `test_reflection_query.py` | `test_reflection_integration.py` | - |

**Test Files**:
- `apps/memory_api/tests/test_reflection_engine_v2.py`
- `tests/integration/test_reflection_engine_v2.py`

**Coverage Gaps**:
- ⚠️ E2E tests for reflection workflows
- ⚠️ Partial outcome testing

### Background Workers

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| **Decay Worker** | `test_workers.py` | `test_decay_worker.py` | `test_maintenance_cycle.py` |
| **Summarization Worker** | `test_summarization_worker.py` | `test_summarization_integration.py` | `test_maintenance_cycle.py` |
| **Dreaming Worker** | `test_workers.py` | `test_dreaming_worker.py` | `test_maintenance_cycle.py` |
| **Maintenance Scheduler** | `test_maintenance_scheduler.py` | `test_maintenance_integration.py` | `test_maintenance_cycle.py` |

**Test Files**:
- `apps/memory_api/tests/test_workers.py`
- `apps/memory_api/tests/test_summarization_worker.py`
- `tests/integration/test_decay_worker.py`
- `tests/integration/test_dreaming_worker.py`

### Rules Engine

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| **Event Processing** | `test_rules_engine.py` | `test_event_triggers.py` | - |
| **Condition Evaluation** | `test_rules_engine.py` | `test_conditions.py` | - |
| **Action Execution** | `test_rules_engine.py` | `test_actions.py` | - |
| **Rate Limiting** | `test_rules_engine.py` | - | - |

**Test Files**:
- `apps/memory_api/tests/test_rules_engine.py`
- `apps/memory_api/tests/test_event_triggers.py`

**Coverage Gaps**:
- ⚠️ Complex condition group testing
- ⚠️ E2E workflow tests

### Cost Guard

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| **Cost Tracking** | `test_cost_controller.py` | `test_cost_tracking.py` | `test_e2e_cost.py` |
| **Budget Enforcement** | `test_cost_controller.py` | `test_budget_enforcement.py` | `test_e2e_cost.py` |
| **Budget Alerts** | `test_cost_controller.py` | `test_budget_alerts.py` | - |
| **Cost Logs** | `test_cost_logs.py` | `test_cost_logging.py` | - |

**Test Files**:
- `apps/memory_api/tests/test_cost_controller.py`
- `tests/integration/test_cost_tracking.py`

### Multi-Tenancy

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| **Tenant Isolation** | `test_tenant_isolation.py` | `test_tenant_isolation_integration.py` | `test_e2e_multitenancy.py` |
| **RLS Policies** | `test_rls.py` | `test_rls_integration.py` | - |
| **Tenant CRUD** | `test_tenant_repository.py` | `test_tenant_operations.py` | - |
| **Cross-Tenant Prevention** | `test_tenant_isolation.py` | `test_cross_tenant.py` | `test_e2e_multitenancy.py` |

**Test Files**:
- `tests/unit/test_tenant_*.py`
- `tests/integration/test_multitenancy.py`
- `tests/e2e/test_multitenancy.py`

### API Endpoints

| Endpoint | Unit Tests | Integration Tests | E2E Tests |
|----------|------------|-------------------|-----------|
| `POST /memories` | `test_api_memories.py` | `test_api_integration.py` | `test_e2e_api.py` |
| `GET /memories/query` | `test_api_queries.py` | `test_api_integration.py` | `test_e2e_api.py` |
| `POST /graph/query` | `test_api_graphrag.py` | `test_api_integration.py` | `test_e2e_graphrag.py` |
| `POST /reflections` | `test_api_reflections.py` | `test_api_integration.py` | - |
| `GET /cost/usage` | `test_api_cost.py` | `test_api_integration.py` | - |

**Test Files**:
- `tests/api/test_*.py`
- `tests/integration/test_api_*.py`

## Test Types

### Unit Tests

**Location**: `tests/unit/`, `apps/memory_api/tests/`

**Purpose**: Test individual functions/classes in isolation

**Example**:
```python
# tests/unit/test_importance_scoring.py
def test_calculate_importance_score():
    scorer = ImportanceScoringService(mock_db)
    score = scorer.calculate_importance(
        content="Critical database failure",
        context={"error": True, "severity": "high"}
    )
    assert score > 0.8
```

### Integration Tests

**Location**: `tests/integration/`

**Purpose**: Test component interactions with real dependencies

**Example**:
```python
# tests/integration/test_memory_storage.py
async def test_store_and_retrieve_memory(db_pool):
    repo = MemoryRepository(db_pool)

    # Store memory
    memory_id = await repo.insert_memory(
        tenant_id="test",
        content="Test memory",
        source="test"
    )

    # Retrieve memory
    memory = await repo.get_memory(memory_id)
    assert memory["content"] == "Test memory"
```

### E2E Tests

**Location**: `tests/e2e/`

**Purpose**: Test complete user workflows

**Example**:
```python
# tests/e2e/test_memory_operations.py
async def test_full_memory_workflow(api_client):
    # Store memory
    response = api_client.post("/api/v1/memories", json={
        "content": "User logged in",
        "source": "app"
    })
    memory_id = response.json()["id"]

    # Query for memory
    response = api_client.post("/api/v1/memories/query", json={
        "query": "user login"
    })
    results = response.json()["results"]
    assert any(r["id"] == memory_id for r in results)
```

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=apps --cov-report=html
```

### By Category

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# Specific feature
pytest -k "test_memory"
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=apps --cov-report=html

# View report
open htmlcov/index.html

# Coverage by file
pytest --cov=apps --cov-report=term-missing
```

## Coverage Gaps

### High Priority

1. **Reflection Engine V2 E2E** - Need end-to-end workflow tests
2. **Rules Engine Complex Conditions** - More complex condition scenarios
3. **LLM Profile Fallback Chains** - Test full fallback sequences
4. **Integration Error Handling** - Test failure scenarios in integrations

### Medium Priority

1. **Background Worker Edge Cases** - More edge case coverage
2. **GraphRAG Performance** - Large graph performance tests
3. **Multi-Tenant Stress Tests** - High concurrency tests

### Low Priority

1. **UI/Dashboard Tests** - Frontend testing
2. **CLI Tests** - CLI command tests
3. **Documentation Tests** - Code example validation

## Test Data

### Fixtures

Test fixtures in `tests/fixtures/`:
- `test_memories.json` - Sample memories
- `test_graphs.json` - Sample knowledge graphs
- `test_tenants.json` - Sample tenant configurations

### Test Database

```bash
# Setup test database
docker compose -f docker compose.test.yml up -d

# Run migrations
alembic -c tests/alembic.ini upgrade head

# Seed test data
python scripts/seed_test_data.py
```

## CI/CD Integration

Tests run automatically on:
- Pull requests (all tests)
- Main branch commits (all tests + coverage)
- Nightly (full test suite + performance tests)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Related Documentation

- [Testing Status](../TESTING_STATUS.md) - Overall testing status
- [Dev Tools](./DEV_TOOLS_AND_SCRIPTS.md) - Test generation tools
- [Evaluation Framework](./EVAL_FRAMEWORK.md) - Performance testing
