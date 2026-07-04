# RAE Project Structure - Quick Reference for AI Agents

> **Purpose**: This file helps AI agents quickly find where to add/modify code and tests without searching.

## 📁 Directory Layout

```
RAE-agentic-memory/
├── apps/
│   ├── memory_api/           # Main API application
│   │   ├── api/v1/          # FastAPI routes (REST endpoints)
│   │   ├── repositories/    # Data access layer (PostgreSQL)
│   │   ├── services/        # Business logic layer
│   │   ├── models/          # Pydantic data models
│   │   ├── middleware/      # FastAPI middleware
│   │   ├── security/        # Auth, RBAC, tenancy
│   │   ├── tasks/           # Celery background tasks
│   │   ├── utils/           # Helper utilities
│   │   └── tests/           # Test suite (mirrors src structure)
│   │       ├── api/         # API endpoint tests
│   │       ├── repositories/ # Repository tests (DB)
│   │       ├── services/    # Service layer tests
│   │       └── ...
│   │
│   ├── llm/                 # LLM abstraction layer
│   │   ├── broker/          # LLM routing and load balancing
│   │   ├── providers/       # Provider implementations (OpenAI, Anthropic, etc.)
│   │   └── tests/           # LLM tests
│   │
│   └── ml_service/          # Optional ML microservice
│       ├── services/        # ML operations (embeddings, NER, triples)
│       └── tests/           # ML service tests
│
├── sdk/python/              # Python SDK for RAE
│   └── rae_memory_sdk/
│
├── integrations/
│   ├── mcp/                 # Model Context Protocol server
│   └── context-watcher/     # IDE context watching
│
├── tools/
│   └── memory-dashboard/    # Streamlit dashboard
│
├── infra/                   # Infrastructure (Docker, K8s)
│   ├── docker compose.yml
│   └── kubernetes/
│
└── docs/                    # Documentation
    ├── CONVENTIONS.md       # Code patterns and conventions
    ├── .ai-templates/       # Code templates for agents
    └── .auto-generated/     # Auto-generated docs
```

## 🗺️ Where to Find/Add Code

### Adding a New API Endpoint

**Location**: `apps/memory_api/api/v1/<domain>.py`

**Example**: Adding user profile endpoint
- Create: `apps/memory_api/api/v1/users.py`
- Tests: `apps/memory_api/tests/api/v1/test_users.py`
- Register router in: `apps/memory_api/api/v1/__init__.py`

**Template**: See `.ai-templates/route_template.py`

### Adding Business Logic (Service)

**Location**: `apps/memory_api/services/<service_name>.py`

**Example**: Adding caching service
- Create: `apps/memory_api/services/cache_service.py`
- Tests: `apps/memory_api/tests/services/test_cache_service.py`

**Template**: See `.ai-templates/service_template.py`

### Adding Database Access (Repository)

**Location**: `apps/memory_api/repositories/<entity>_repository.py`

**Example**: Adding user repository
- Create: `apps/memory_api/repositories/user_repository.py`
- Tests: `apps/memory_api/tests/repositories/test_user_repository.py`

**Template**: See `.ai-templates/repository_template.py`

### Adding Data Models

**Location**: `apps/memory_api/models/<model>.py` or `apps/memory_api/models/__init__.py`

**Example**: Adding user model
- Create: `apps/memory_api/models/user.py`
- Import in: `apps/memory_api/models/__init__.py`

**Pattern**: Use Pydantic BaseModel

### Adding Background Tasks

**Location**: `apps/memory_api/tasks/<task_name>.py`

**Example**: Adding email notification task
- Create: `apps/memory_api/tasks/email_notifications.py`
- Tests: `apps/memory_api/tests/tasks/test_email_notifications.py`

**Pattern**: Celery task with `@celery_app.task` decorator

### Adding LLM Provider

**Location**: `apps/llm/providers/<provider_name>.py`

**Example**: Adding Cohere provider
- Create: `apps/llm/providers/cohere.py`
- Tests: `apps/llm/tests/providers/test_cohere.py`
- Register in: `apps/llm/broker/llm_router.py`

## 🧪 Testing Structure (CRITICAL)

### Test Location Mapping

| Code Location | Test Location | Test Type |
|---------------|---------------|-----------|
| `apps/memory_api/api/v1/memory.py` | `apps/memory_api/tests/api/v1/test_memory.py` | Integration |
| `apps/memory_api/services/hybrid_search.py` | `apps/memory_api/tests/services/test_hybrid_search.py` | Unit |
| `apps/memory_api/repositories/memory_repository.py` | `apps/memory_api/tests/repositories/test_memory_repository.py` | Integration |
| `apps/llm/providers/openai.py` | `apps/llm/tests/providers/test_openai.py` | Unit |
| `apps/ml_service/services/embeddings.py` | `apps/ml_service/tests/services/test_embeddings.py` | Unit |

### Test Markers (pytest.ini)

```python
import pytest

# Unit test (fast, no external dependencies)
@pytest.mark.unit
def test_calculate_score():
    ...

# Integration test (requires DB/Redis/Qdrant)
@pytest.mark.integration
async def test_store_memory():
    ...

# LLM test (requires API keys, skipped in CI)
@pytest.mark.llm
async def test_openai_completion():
    ...

# Slow test
@pytest.mark.slow
def test_large_graph_traversal():
    ...
```

### Running Tests

```bash
# Quick feedback during development (NO COVERAGE CHECK!)
pytest --no-cov apps/memory_api/tests/services/test_my_service.py

# Or use make target
make test-focus FILE=apps/memory_api/tests/services/test_my_service.py

# Full test suite with coverage (before PR)
pytest -m "not integration and not llm" --cov

# Specific markers
pytest -m "unit and not slow"
pytest -m "integration"
```

## 📦 Import Patterns

### Internal Imports (within memory_api)

```python
# ✅ CORRECT - Absolute imports from app root
from apps.memory_api.models import Memory, QueryRequest
from apps.memory_api.repositories.memory_repository import MemoryRepository
from apps.memory_api.services.hybrid_search import HybridSearchService
from apps.memory_api.config import settings

# ❌ WRONG - Relative imports
from ..models import Memory  # DON'T use relative imports
from .memory_repository import MemoryRepository  # DON'T
```

### External Imports (other apps)

```python
# ✅ CORRECT
from apps.llm.broker import LLMRouter
from apps.llm.providers.openai import OpenAIProvider

# ❌ WRONG
import sys; sys.path.append('../../llm')  # DON'T hack sys.path
```

## 🔍 Finding Existing Code

### By Feature

| Feature | Service | Repository | API Route |
|---------|---------|------------|-----------|
| Memory storage/retrieval | `services/vector_store/` | `repositories/memory_repository.py` | `api/v1/memory.py` |
| Hybrid search | `services/hybrid_search.py` | `repositories/graph_repository.py` | `api/v1/memory.py` |
| Reflections | `services/reflection_engine.py` | `repositories/reflection_repository.py` | `routes/reflections.py` |
| Knowledge graph | `services/graph/` | `repositories/graph_repository.py` | `api/v1/graph.py` |
| Cost tracking | `services/cost_controller.py` | `repositories/cost_logs_repository.py` | `api/v1/compliance.py` |
| Auth & RBAC | `security/rbac_service.py` | `repositories/rbac_repository.py` | Middleware |
| LLM routing | `apps/llm/broker/llm_router.py` | N/A | `api/v1/agent.py` |

### By Layer

**API Layer** (Entry points):
```bash
apps/memory_api/api/v1/*.py
apps/memory_api/routes/*.py
```

**Business Logic** (Services):
```bash
apps/memory_api/services/*.py
apps/memory_api/services/graph/*.py
apps/memory_api/services/llm/*.py
apps/memory_api/services/vector_store/*.py
```

**Data Access** (Repositories):
```bash
apps/memory_api/repositories/*.py
```

**Models** (Data structures):
```bash
apps/memory_api/models/*.py
apps/memory_api/models/graph.py
```

## 🛠️ Configuration

### Environment Variables

**File**: `.env` (root directory)

**Loading**: `apps/memory_api/config.py` (Pydantic settings)

**Usage**:
```python
from apps.memory_api.config import settings

database_url = settings.DATABASE_URL
redis_url = settings.REDIS_URL
```

### Database Migrations

**Location**: `infra/init-scripts/` (SQL initialization)

**Pattern**: PostgreSQL with pgvector extension

## 📝 Common Patterns

### Dependency Injection (Services)

```python
class MyService:
    def __init__(self, repo: MyRepository, other_service: OtherService):
        self.repo = repo
        self.other_service = other_service

    async def do_something(self):
        result = await self.repo.fetch_data()
        return await self.other_service.process(result)
```

### Error Handling (Routes)

```python
@router.post("/endpoint")
async def my_endpoint(...):
    try:
        result = await service.do_work()
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Logging

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("operation_started", tenant_id=tenant_id, operation="search")
logger.error("operation_failed", error=str(e), tenant_id=tenant_id)
```

## 🚀 Quick Start for Common Tasks

### Task: Add new memory retrieval algorithm

1. **Service**: `apps/memory_api/services/custom_retrieval.py`
2. **Tests**: `apps/memory_api/tests/services/test_custom_retrieval.py`
3. **Integrate**: Import in `api/v1/memory.py` and add endpoint
4. **Commit**: `git commit -m "feat: add custom retrieval algorithm"`

### Task: Add new cost tracking metric

1. **Repository**: Update `repositories/cost_logs_repository.py`
2. **Service**: Update `services/cost_controller.py`
3. **API**: Update `api/v1/compliance.py` to expose new metric
4. **Tests**: Add tests in all three layers
5. **Commit**: `git commit -m "feat: add new cost metric"`

### Task: Add new LLM provider

1. **Provider**: `apps/llm/providers/my_provider.py`
2. **Tests**: `apps/llm/tests/providers/test_my_provider.py`
3. **Register**: Update `apps/llm/broker/llm_router.py`
4. **Config**: Add settings in `apps/llm/config/settings.py`
5. **Commit**: `git commit -m "feat: add MyProvider LLM support"`

## 📚 Documentation References

- **Architecture Details**: `docs/ARCHITECTURE.md`
- **Code Conventions**: `docs/CONVENTIONS.md`
- **Testing Policy**: `docs/AGENTS_TEST_POLICY.md`
- **Branching Strategy**: `docs/BRANCHING.md`
- **Code Templates**: `docs/.ai-templates/`

## ⚡ Quick Search Commands

```bash
# Find where a function is defined
grep -r "def function_name" apps/

# Find all uses of a class
grep -r "ClassName" apps/

# Find all tests for a module
find apps/memory_api/tests -name "*my_module*"

# Find all API endpoints
grep -r "@router\." apps/memory_api/api/

# Find all database queries
grep -r "await.*fetch" apps/memory_api/repositories/
```

## 🎯 Key Takeaways for Agents

> **⚠️ BEFORE YOU START**: Read [CRITICAL_AGENT_RULES.md](./CRITICAL_AGENT_RULES.md) for 8 mandatory rules!

### File Structure & Code Organization
1. **Mirror structure**: Tests mirror source structure exactly
2. **Layer separation**: API → Service → Repository (never skip layers)
3. **Absolute imports**: Always use `from apps.` imports
4. **Templates**: Check `.ai-templates/` before writing new code
5. **Conventions**: Read `CONVENTIONS.md` before major changes

### Testing & Quality (CRITICAL!)
6. **3-phase workflow** (RULE #1 & #3):
   - Feature branch: Test ONLY new code (`pytest --no-cov path/`)
   - Develop branch: Test EVERYTHING (`make test-unit`) - MANDATORY!
   - Main branch: CI tests automatically
7. **Format & Lint** (MANDATORY before commit):
   - Always run: `make format && make lint`
8. **Test markers**: Use appropriate pytest markers (`@pytest.mark.unit`, etc.)

### Documentation (RULE #8)
9. **Auto-generated docs** (DON'T EDIT): `CHANGELOG.md`, `STATUS.md`, `TODO.md`, `docs/.auto-generated/`
10. **Manual docs** (DO EDIT): `CONVENTIONS.md`, `PROJECT_STRUCTURE.md`, `docs/guides/`

---

**Last Updated**: 2025-12-04
**Maintained by**: AI Agent Code Quality System
