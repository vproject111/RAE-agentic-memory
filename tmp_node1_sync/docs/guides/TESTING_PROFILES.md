# RAE Testing Profiles

RAE implements a tiered testing strategy to balance speed during development with absolute stability for production.

## 1. Summary Table

| Profile | Command | Context | Speed | Requires Infra |
| :--- | :--- | :--- | :--- | :--- |
| **Unit** | `make test-unit` | Local logic, no DB, no LLM | Fast (<1 min) | No |
| **Smoke** | `make test-smoke` | Critical path E2E check | Fast (<30s) | Yes (Full Stack) |
| **Architecture**| `make test-architecture` | Dependency & isolation rules | Fast | No |
| **Integration** | `make test-integration` | DB, Vector Store, Redis | Medium (~2 min)| Yes (Postgres/Qdrant) |
| **Local LLM** | `make test-local-llm` | Uses Ollama instead of Cloud | Slow | Yes (Ollama) |
| **Full Stack** | `make test-full-stack` | Absolute verification (All tests) | Slow (~5 min) | Yes (Absolute All) |

## 2. Profile Details

### Unit Tests (`make test-unit`)
- **Focus**: Pure Python logic, math heuristics, scoring formulas.
- **Tools**: `pytest` with extensive mocking.
- **Rule**: Must be 100% green before any commit.

### Smoke Tests (`make test-smoke`)
- **Focus**: "Is it alive?" - checks Health, Store, and Search via real API calls.
- **Context**: Used after deployment or container restart to verify connectivity.

### Architecture Tests (`make test-architecture`)
- **Focus**: Prevents circular dependencies and enforces layer isolation (e.g., Services cannot import from Routes).
- **Rule**: Enforces the **Zero Warning Policy** for architectural drift.

### Local LLM (`make test-local-llm`)
- **Focus**: Verifies that RAE can function without external cloud providers.
- **Requirement**: `docker compose --profile local-llm up` must be active.

### Full Stack Verification (`make test-full-stack`)
- **Focus**: Comprehensive regression suite.
- **Enables**: OpenTelemetry tracing (OTEL), all LLM providers, and real DB migrations.
- **Rule**: Mandatory before releasing a new version or merging to `main`.

## 3. Selecting Tests via Markers

You can also use pytest markers directly for more granular control:

```bash
# Run only GraphRAG related tests
pytest -m graphrag

# Run only reflection engine tests
pytest -m reflection

# Run everything EXCEPT slow performance tests
pytest -m "not performance"
```

## 4. Coverage Requirements

RAE enforces a strict coverage policy:
- **Global Minimum**: 65% (CI Gate)
- **Core Modules**: 80%+ target
- **ISO Services**: 100% (Mandatory)

To check coverage, use: `make test-cov`.
