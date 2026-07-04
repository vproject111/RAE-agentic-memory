# Architecture → Code Mapping

## Overview

This document maps RAE's architectural components (from README diagrams) to their actual implementation in the codebase. Use this as a bridge between conceptual architecture and code exploration.

**Purpose**: Help developers and maintainers understand exactly where each architectural component is implemented.

---

## Core Services

### 1. Memory API (Core Service)

**Architecture Component**: Main FastAPI application handling all memory operations

**Code Location**: `apps/memory_api/`

**Key Components**:

| Component | File/Directory | Description |
|-----------|---------------|-------------|
| **Main Application** | `apps/memory_api/main.py` | FastAPI app entry point |
| **API Routes** | `apps/memory_api/routes/` | All HTTP endpoints |
| **Services** | `apps/memory_api/services/` | Business logic layer |
| **Models** | `apps/memory_api/models/` | Pydantic models & DB schemas |
| **Repositories** | `apps/memory_api/repositories/` | Data access layer |
| **Middleware** | `apps/memory_api/middleware/` | Request/response processing |
| **Security** | `apps/memory_api/security/` | Authentication & authorization |

**API Endpoints**:
- Memory CRUD: `routes/` (endpoints TBD based on routing structure)
- Hybrid Search: `routes/hybrid_search.py`
- Graph queries: `routes/graph_enhanced.py`
- Reflections: `routes/reflections.py`
- Events/Rules: `routes/event_triggers.py`
- Evaluation: `routes/evaluation.py`
- Dashboard: `routes/dashboard.py`

---

## Memory System

### 2. Four-Layer Memory Architecture

**Architecture Component**: Sensory → Episodic → Semantic → Reflective Memory

**Implementation**:

| Layer | Model | Repository | Service | Storage |
|-------|-------|------------|---------|---------|
| **Sensory (SM)** | `models/semantic_models.py` | `repositories/memory_repository.py` | Context aware memory storage | PostgreSQL + Qdrant vectors |
| **Episodic (EM)** | `models/semantic_models.py` | `repositories/memory_repository.py` | Time-stamped memories | PostgreSQL + Qdrant vectors |
| **Semantic (LTM)** | `models/semantic_models.py` | `repositories/memory_repository.py` | Long-term knowledge | PostgreSQL + Qdrant vectors |
| **Reflective (RM)** | `models/reflection_models.py`, `models/reflection_v2_models.py` | `repositories/reflection_repository.py` | Insights and patterns | PostgreSQL |

**Database Tables** (PostgreSQL):
- `memories` - Main memory storage (all layers)
- `reflections` - Reflective layer entries
- `memory_relationships` - Cross-layer connections
- `memory_embeddings` - Vector embeddings (optional, primarily in Qdrant)

**Vector Storage** (Qdrant):
- Collection: `memories` - Semantic embeddings for all layers

---

### 3. GraphRAG (Graph-based Retrieval)

**Architecture Component**: Knowledge graph extraction + hybrid search

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Graph Extraction** | `services/graph_extraction.py` | Entity and relationship extraction |
| **Entity Resolution** | `services/entity_resolution.py` | Deduplication and linking |
| **Community Detection** | `services/community_detection.py` | Graph clustering algorithms |
| **Graph Algorithms** | `services/graph_algorithms.py` | PageRank, centrality, etc. |
| **Graph Repository** | `repositories/graph_repository.py`, `repositories/graph_repository_enhanced.py` | Graph data access |
| **Graph Models** | `models/graph.py`, `models/graph_enhanced_models.py` | Entity, Relationship schemas |

**Database Tables**:
- `entities` - Extracted entities from memories
- `relationships` - Connections between entities
- `communities` - Detected entity clusters

**API Endpoints**:
- `routes/graph_enhanced.py` - Graph queries and traversal

---

### 4. Hybrid Search Service

**Architecture Component**: Vector + keyword + graph search

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Hybrid Search Core** | `services/hybrid_search.py`, `services/hybrid_search_service.py` | Combined search logic |
| **Hybrid Cache** | `services/hybrid_cache.py` | Search result caching |
| **Embedding Service** | `services/embedding.py` | Vector generation |
| **Context Builder** | `services/context_builder.py` | Search result assembly |

**Models**:
- `models/hybrid_search_models.py` - Request/response schemas

**API Endpoints**:
- `routes/hybrid_search.py` - Hybrid search API

**External Dependencies**:
- **Qdrant** (port 6333) - Vector similarity search
- **PostgreSQL Full-Text Search** - Keyword matching
- **Graph queries** - Entity relationship traversal

---

## Reflection System

### 5. Reflection Engine V2 (Actor-Evaluator-Reflector)

**Architecture Component**: Automatic insight generation from memories

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Reflection Engine** | `services/reflection_engine.py` (if exists) | Main orchestrator |
| **Actor** | Pattern implemented in reflection service | Experience collection |
| **Evaluator** | `services/evaluator.py` | Quality and importance assessment |
| **Reflector** | Reflection generation logic | Insight extraction |
| **Evaluation Service** | `services/evaluation_service.py` | Reflection quality scoring |

**Models**:
- `models/reflection_models.py` - V1 reflection schemas
- `models/reflection_v2_models.py` - V2 Actor-Evaluator-Reflector schemas

**Repository**:
- `repositories/reflection_repository.py` - Reflection data access
- `repositories/evaluation_repository.py` - Evaluation storage

**API Endpoints**:
- `routes/reflections.py` - Reflection CRUD and generation

**Related Documentation**:
- `docs/reference/architecture/REFLECTION_ENGINE_V2_IMPLEMENTATION.md`

---

## Enterprise Features

### 6. Rules Engine

**Architecture Component**: Event-driven automation and triggers

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Rules Engine Core** | Likely in `services/` (to be verified) | Rule evaluation and execution |
| **Event Models** | `models/event_models.py` | Event and trigger schemas |
| **Trigger Repository** | `repositories/trigger_repository.py` | Rule storage and retrieval |

**API Endpoints**:
- `routes/event_triggers.py` - Rule and trigger management

**Related Documentation**:
- `docs/reference/architecture/RULES_ENGINE.md`

---

### 7. Cost Control & Budget Enforcement

**Architecture Component**: LLM cost tracking and budget limits (HTTP 402 blocking)

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Cost Controller** | `services/cost_controller.py` | Real-time cost tracking |
| **Budget Service** | `services/budget_service.py` | Budget limits and alerts |
| **Cost Logs Repository** | `repositories/cost_logs_repository.py` | Cost data storage |

**Database Tables**:
- `cost_logs` - Per-request LLM cost tracking
- `budgets` - Per-tenant budget limits
- `budget_alerts` - Alert thresholds

**Integration**:
- Middleware hooks for request interception
- HTTP 402 (Payment Required) when budget exceeded

**Related Documentation**:
- `docs/reference/llm/LLM_PROFILES_AND_COST_GUARD.md`

---

### 8. Multi-Tenancy & RBAC

**Architecture Component**: Tenant isolation and role-based access control

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Tenant Models** | `models/tenant.py` | Tenant schemas |
| **RBAC Models** | `models/rbac.py` | Role and permission models |
| **Security Layer** | `security/` | Authentication & authorization |
| **Middleware** | `middleware/` | Tenant context injection |

**Database Tables**:
- `tenants` - Tenant records
- `users` - User accounts
- `roles` - RBAC roles
- `permissions` - Fine-grained permissions
- **Row-Level Security (RLS)** - PostgreSQL policies on `memories`, `reflections`, etc.

**Related Documentation**:
- `docs/reference/architecture/MULTI_TENANCY.md`
- `docs/reference/deployment/RLS-Deployment-Guide.md`

---

### 9. Compliance & Governance

**Architecture Component**: ISO 42001, GDPR, audit logging

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Compliance Service** | `services/compliance_service.py` | Compliance checks and reporting |
| **Context Provenance** | `services/context_provenance_service.py` | Decision lineage tracking |
| **Human Approval** | `services/human_approval_service.py` | Risk-based approval workflow |
| **Drift Detection** | `services/drift_detector.py` | AI drift monitoring |
| **Analytics** | `services/analytics.py` | Compliance metrics |

**Database Tables**:
- `audit_logs` - All operations logged
- `approval_requests` - Human-in-the-loop workflows
- `compliance_metrics` - ISO 42001 KPIs

**API Endpoints**:
- Dashboard compliance endpoints (routes/dashboard.py)

**Related Documentation**:
- `docs/reference/iso-security/ISO42001_IMPLEMENTATION_MAP.md`
- `docs/reference/iso-security/RAE-ISO_42001.md`
- `docs/reference/iso-security/SECURITY.md`

---

## Background Workers

### 10. Celery Workers

**Architecture Component**: Async tasks (decay, summarization, dreaming)

**Code Location**:

| Component | File | Description |
|-----------|------|-------------|
| **Memory Maintenance** | `workers/memory_maintenance.py` | All background workers |
| **Decay Worker** | Function in `memory_maintenance.py` | Memory importance decay |
| **Summarization Worker** | Function in `memory_maintenance.py` | Periodic memory summarization |
| **Dreaming Worker** | Function in `memory_maintenance.py` | Reflection generation cycles |

**Task Queue**:
- **Redis** (port 6379) - Celery broker
- **Celery Beat** - Task scheduling

**Related Documentation**:
- `docs/reference/architecture/BACKGROUND_WORKERS.md`

---

## External Services

### 11. ML Service (Optional - Standard/Enterprise only)

**Architecture Component**: Machine learning models for entity resolution and embeddings

**Code Location**: `apps/ml_service/`

**Key Components**:
- `apps/ml_service/main.py` - FastAPI service
- `apps/ml_service/services/` - ML inference logic
- `apps/ml_service/tests/` - ML service tests

**API**: Internal HTTP API (port 8001)

**Dependencies**:
- PyTorch, Transformers, SentenceTransformers

**Used By**:
- Entity resolution service (when available)
- Custom embedding models

---

### 12. Reranker Service (Optional - Standard/Enterprise only)

**Architecture Component**: CrossEncoder for search result re-ranking

**Code Location**: `apps/reranker-service/`

**Key Components**:
- `apps/reranker-service/main.py` - FastAPI service
- `apps/reranker-service/tests/` - Reranker tests

**API**: Internal HTTP API (port 8002)

**Used By**:
- Hybrid search service (post-processing)

---

## LLM Integration

### 13. Multi-Model LLM Broker

**Architecture Component**: Provider abstraction and fallback chains

**Code Location**: `apps/llm/`

**Key Components**:

| Component | Directory | Description |
|-----------|-----------|-------------|
| **LLM Broker** | `apps/llm/broker/` | Provider routing and fallback |
| **LLM Config** | `apps/llm/config/` | Profile management |
| **LLM Models** | `apps/llm/models/` | Request/response schemas |
| **Providers** | `apps/llm/providers/` | OpenAI, Anthropic, Google, DeepSeek, Qwen, Grok, Ollama |

**Supported Providers**:
- OpenAI (gpt-4o, gpt-3.5-turbo)
- Anthropic (Claude 3.5 Sonnet, Opus, Haiku)
- Google (Gemini)
- DeepSeek, Qwen, Grok
- Ollama (local models)

**Features**:
- Automatic fallback chains
- Cost tracking per provider
- Tool calling support
- JSON mode

**Related Documentation**:
- `docs/reference/llm/LLM_PROFILES_AND_COST_GUARD.md`
- `docs/reference/llm/llm_backends.md`

---

## Data Storage

### 14. Database Architecture

**PostgreSQL** (port 5432):

| Table Category | Key Tables | Purpose |
|----------------|------------|---------|
| **Memory** | `memories`, `memory_relationships`, `memory_embeddings` | Core memory storage |
| **Graph** | `entities`, `relationships`, `communities` | Knowledge graph |
| **Reflection** | `reflections`, `evaluations` | Insights and quality scores |
| **Governance** | `audit_logs`, `approval_requests`, `compliance_metrics` | ISO 42001 compliance |
| **Cost** | `cost_logs`, `budgets`, `budget_alerts` | LLM cost tracking |
| **Multi-Tenancy** | `tenants`, `users`, `roles`, `permissions` | Tenant isolation + RBAC |
| **Rules** | `event_triggers`, `rule_definitions` | Rules engine |

**Qdrant** (port 6333):
- Collection: `memories` - Vector embeddings for semantic search

**Redis** (port 6379):
- **Cache**: Search results, context cache, LLM responses
- **Queue**: Celery task queue
- **Rate Limiting**: API throttling

---

## Testing Structure

### 15. Test Coverage

**Test Locations**:
- `apps/memory_api/tests/` - Unit and integration tests
- `tests/` - Project-wide E2E tests (if exists)

**Key Test Files**:
- Memory operations: `test_memory_*.py`
- GraphRAG: `test_graph_*.py`, `test_hybrid_search*.py`
- Reflection: `test_reflection*.py`, `test_evaluation*.py`
- Cost control: `test_cost_*.py`, `test_budget_*.py`
- Compliance: `test_compliance_*.py`, `test_audit_*.py`

**Related Documentation**:
- `docs/reference/testing/TEST_COVERAGE_MAP.md`
- `docs/reference/testing/TESTING_STATUS.md`

---

## Infrastructure & Deployment

### 16. Deployment Configurations

**Docker Compose**:
- `docker compose.lite.yml` - RAE Lite (4 services)
- `docker compose.yml` - Full stack (9+ services)

**Kubernetes/Helm**:
- `helm/rae-memory/` - Helm chart for enterprise deployment
- `charts/rae/` - Alternative chart structure

**Infrastructure**:
- `infra/` - Terraform, cloud configs (TBD)

**Scripts**:
- `scripts/quickstart.sh` - One-line full stack setup
- `scripts/init-database.sh` - Database initialization
- Other utility scripts in `scripts/`

**Related Documentation**:
- `docs/reference/deployment/DEPLOY_K8S_HELM.md`
- `docs/reference/deployment/rae-lite-profile.md`

---

## SDK and Integrations

### 17. Python SDK

**Code Location**: `sdk/python/rae_memory_sdk/`

**Key Components**:
- Client library for external applications
- Type-safe wrappers around REST API

**Related Documentation**:
- `docs/reference/api/SDK_PYTHON_REFERENCE.md`

---

### 18. Integrations

**Code Location**: `integrations/`

**Available Integrations**:

| Integration | Directory | Description |
|-------------|-----------|-------------|
| **MCP Server** | `integrations/mcp/` | Model Context Protocol for IDE integration |
| **Context Watcher** | `integrations/context-watcher/` | Automatic code context tracking |
| **Ollama Wrapper** | `integrations/ollama-wrapper/` | Local LLM support |
| **Slack** | `integrations/slack/` (planned) | Team knowledge bot |
| **GitHub** | `integrations/github/` (planned) | PR and issue memory |

**Related Documentation**:
- `docs/reference/integrations/INTEGRATIONS_OVERVIEW.md`
- `docs/reference/integrations/MCP_IDE_INTEGRATION.md`

---

## CLI Tools

### 19. Agent CLI

**Code Location**: `cli/agent-cli/`

**Features**:
- Memory ingestion from files/URLs
- Query interface
- Cost monitoring
- Diagnostics

**Related Documentation**:
- `docs/reference/api/CLI_REFERENCE.md`

---

## Quick Reference: Component → Code

| Architectural Component | Primary Code Location | Key Files |
|------------------------|----------------------|-----------|
| **Memory Storage** | `apps/memory_api/repositories/` | `memory_repository.py` |
| **Hybrid Search** | `apps/memory_api/services/` | `hybrid_search.py`, `hybrid_search_service.py` |
| **GraphRAG** | `apps/memory_api/services/` | `graph_extraction.py`, `entity_resolution.py` |
| **Reflection Engine V2** | `apps/memory_api/services/` | `evaluator.py`, `evaluation_service.py` |
| **Rules Engine** | `apps/memory_api/services/` + `routes/event_triggers.py` | Event-driven automation |
| **Cost Guard** | `apps/memory_api/services/` | `cost_controller.py`, `budget_service.py` |
| **Compliance** | `apps/memory_api/services/` | `compliance_service.py`, `context_provenance_service.py` |
| **Background Workers** | `apps/memory_api/workers/` | `memory_maintenance.py` |
| **LLM Broker** | `apps/llm/` | `broker/`, `providers/` |
| **API Routes** | `apps/memory_api/routes/` | All HTTP endpoints |
| **Models** | `apps/memory_api/models/` | Pydantic + DB schemas |
| **Security** | `apps/memory_api/security/` + `middleware/` | Auth, RBAC, tenant isolation |

---

## How to Use This Map

### For New Developers
1. Start with the **Quick Reference** table above
2. Navigate to the primary code location
3. Read the key files to understand implementation
4. Check related documentation links

### For Feature Development
1. Identify the architectural component you're modifying
2. Find the code location in this document
3. Review related services, models, and repositories
4. Check database tables and API endpoints affected

### For Bug Investigation
1. Identify which layer/component is failing
2. Find the service and repository
3. Check related tests in TEST_COVERAGE_MAP.md
4. Review logs and database state

---

## Related Documentation

- [Architecture Overview](./architecture.md) - High-level system design
- [Background Workers](./BACKGROUND_WORKERS.md) - Async task details
- [Reflection Engine V2](./REFLECTION_ENGINE_V2_IMPLEMENTATION.md) - Reflection system deep dive
- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant isolation architecture
- [Rules Engine](./RULES_ENGINE.md) - Event automation details
- [Repository Pattern](./repository-pattern.md) - Data access layer design
- [Test Coverage Map](../testing/TEST_COVERAGE_MAP.md) - Feature → test mapping
- [ISO 42001 Implementation](../iso-security/ISO42001_IMPLEMENTATION_MAP.md) - Compliance → code mapping

---

**Last Updated**: 2025-12-01
**Maintainers**: Architecture team
**Status**: Living document - update as architecture evolves
