# Developer Tools and Scripts

## Overview

RAE includes various developer tools and scripts for testing, code generation, analysis, and maintenance.

**Locations**: `tools/`, `scripts/`, `eval/`

## Tools Directory (`tools/`)

### memory-pack-manager

Manages memory packs (pre-configured memory collections).

**Location**: `tools/memory-pack-manager/`

```bash
# Create memory pack
python tools/memory-pack-manager/pack.py create \
  --name "Python Best Practices" \
  --source ./docs/python/ \
  --output packs/python-best-practices.json

# Install pack
python tools/memory-pack-manager/pack.py install \
  --pack packs/python-best-practices.json \
  --tenant tenant-123
```

### eptt.py

Enterprise Performance Testing Tool for load testing RAE.

**Location**: `tools/eptt.py`

```bash
# Run performance test
python tools/eptt.py \
  --target http://localhost:8000 \
  --concurrent 50 \
  --duration 300 \
  --scenario memory_store_and_query

# Output: Performance metrics, latency percentiles, throughput
```

**Scenarios**:
- `memory_store_and_query` - Store + query cycle
- `graph_traversal` - GraphRAG queries
- `reflection_generation` - Reflection creation
- `mixed_workload` - Realistic mixed operations

### generate_tests_v8.py

Automated test generation from code analysis.

**Location**: `tools/generate_tests_v8.py`

```bash
# Generate tests for module
python tools/generate_tests_v8.py \
  --module apps/memory_api/services/reflection_engine_v2.py \
  --output tests/generated/test_reflection_v8.py

# Generates unit tests, integration tests, edge cases
```

## Scripts Directory (`scripts/`)

### seed_demo_data.py

Seeds demonstration data for testing and demos.

**Location**: `scripts/seed_demo_data.py`

```bash
# Seed demo data
python scripts/seed_demo_data.py \
  --tenant test-tenant \
  --scenario startup_team

# Scenarios:
# - startup_team: Team chat memories
# - code_project: Software development memories
# - research: Research paper memories
# - enrichment: 20 enrichment memories for GraphRAG
```

### migrate_database.py

Database migration helper (complements Alembic).

**Location**: `scripts/migrate_database.py`

```bash
# Run migrations
python scripts/migrate_database.py --direction up

# Rollback
python scripts/migrate_database.py --direction down --steps 1

# Check migration status
python scripts/migrate_database.py --status
```

### export_import_tenant.py

Export/import tenant data for backups or migrations.

**Location**: `scripts/export_import_tenant.py`

```bash
# Export tenant data
python scripts/export_import_tenant.py export \
  --tenant-id tenant-123 \
  --output backup_tenant_123.tar.gz

# Import tenant data
python scripts/export_import_tenant.py import \
  --file backup_tenant_123.tar.gz \
  --tenant-id tenant-456
```

### cleanup_old_data.py

Manual data cleanup (alternative to automatic retention).

**Location**: `scripts/cleanup_old_data.py`

```bash
# Dry run
python scripts/cleanup_old_data.py \
  --tenant-id tenant-123 \
  --older-than-days 90 \
  --dry-run

# Execute cleanup
python scripts/cleanup_old_data.py \
  --tenant-id tenant-123 \
  --older-than-days 90
```

## Evaluation Framework (`eval/`)

### benchmark_suite.py

Comprehensive benchmark suite for RAE performance.

**Location**: `eval/benchmark_suite.py`

```bash
# Run full benchmark
python eval/benchmark_suite.py \
  --output results/benchmark_$(date +%Y%m%d).json

# Run specific benchmarks
python eval/benchmark_suite.py \
  --tests semantic_search,graph_query,reflection
```

**Benchmarks**:
- **Semantic Search**: Embedding generation, vector search speed
- **GraphRAG**: Multi-hop query performance
- **Reflection**: Reflection generation latency
- **Cost**: Token usage and cost efficiency
- **Accuracy**: Retrieval precision and recall

### quality_metrics.py

Evaluates memory quality and RAG performance.

**Location**: `eval/quality_metrics.py`

```bash
# Evaluate RAG quality
python eval/quality_metrics.py \
  --test-set eval/datasets/qa_pairs.json \
  --output results/quality_metrics.json
```

**Metrics**:
- **Precision**: Relevant results retrieved
- **Recall**: Coverage of relevant results
- **F1 Score**: Harmonic mean of precision/recall
- **MRR**: Mean Reciprocal Rank
- **NDCG**: Normalized Discounted Cumulative Gain

### cost_analysis.py

Analyzes cost patterns and optimization opportunities.

**Location**: `eval/cost_analysis.py`

```bash
# Analyze cost patterns
python eval/cost_analysis.py \
  --tenant-id tenant-123 \
  --month 2025-12 \
  --output reports/cost_analysis.html
```

## Development Utilities

### Coverage Analysis

Generate test coverage reports:

```bash
# Generate coverage
pytest --cov=apps/memory_api --cov-report=html

# View report
open htmlcov/index.html
```

### Code Quality Checks

```bash
# Run all quality checks
make lint

# Individual tools
black apps/  # Format code
isort apps/  # Sort imports
mypy apps/   # Type checking
bandit apps/ # Security scan
```

### Docker Utilities

```bash
# Build all services
docker compose build

# Run tests in Docker
docker compose run --rm api pytest

# Generate test reports
docker compose run --rm api pytest --html=report.html
```

## Tool Usage Matrix

| Tool | Purpose | When to Use | User Type |
|------|---------|-------------|-----------|
| `eptt.py` | Load testing | Before releases, capacity planning | Dev/DevOps |
| `generate_tests_v8.py` | Test generation | New features, refactoring | Developers |
| `seed_demo_data.py` | Demo data | Demos, testing, development | Everyone |
| `benchmark_suite.py` | Performance eval | Performance tuning, comparisons | Dev/QA |
| `quality_metrics.py` | RAG quality | Algorithm improvements | ML Engineers |
| `cost_analysis.py` | Cost optimization | Budget review, optimization | DevOps/Finance |
| `memory-pack-manager` | Content management | Sharing knowledge bases | Users/Admins |
| `export_import_tenant.py` | Backup/restore | Migrations, disaster recovery | Admins/DevOps |

## Safety Guidelines

### Safe for Production

These scripts are safe to run in production:
- `seed_demo_data.py` (with care - only in demo tenants)
- `export_import_tenant.py` (export mode)
- `benchmark_suite.py` (read-only)
- `quality_metrics.py` (read-only)
- `cost_analysis.py` (read-only)

### Admin/Dev Only

These require careful use:
- `cleanup_old_data.py` - **DESTRUCTIVE**
- `migrate_database.py` - Affects schema
- `generate_tests_v8.py` - Dev environment only
- `eptt.py` - Can cause high load

## Related Documentation

- [Testing Status](../TESTING_STATUS.md) - Test coverage
- [Evaluation Framework](./EVAL_FRAMEWORK.md) - Detailed eval docs
- [CLI Reference](./CLI_REFERENCE.md) - CLI tools
