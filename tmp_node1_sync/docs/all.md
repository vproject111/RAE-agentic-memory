## RAE Agentic Memory: Consolidated Functionality Plan

This document synthesizes the core and enterprise functionalities, architectural design, and planned iterative improvements for the RAE (Reflective Agentic Memory Engine).

### 1. RAE–Reflective Memory v1 Iteration Fix and Polish Plan

This plan aims to refine and stabilize the `Reflective Memory v1` implementation, ensuring consistency with the 4-layer memory documentation, operational predictability, ease of use for agents, and robust implementation of feature flags.

**Key Iteration Goals:**
*   **Memory Layer Mapping Standardization:** Align conceptual 4-layer memory with code's `layer` enum and `memory_type` values via a central mapping document (`docs/MEMORY_MODEL.md`). Update code comments to reference this standard.
*   **ContextBuilder & Reflection Injection:** Ensure all agents consistently use `ContextBuilder` to inject profile, reflections/strategies, episodic/semantic memories, and recent messages. Implement token limits for reflections and ensure a "Lessons Learned" section.
*   **Feature Flags and Modes (`lite`/`full`):** Verify and implement correct usage of feature flags (`REFLECTIVE_MEMORY_ENABLED`, `REFLECTIVE_MEMORY_MODE`, `DREAMING_ENABLED`, `SUMMARIZATION_ENABLED`) across the system. Define distinct behaviors for `lite` and `full` modes (e.g., dreaming disabled in `lite`).
*   **Maintenance Workers (Decay, Summarization, Dreaming):** Enhance operational predictability with detailed metrics (e.g., number of processed records, and implement integration tests for each worker. Ensure decay mechanisms prevent negative importance and prioritize fresh memories. Implement logic for episodic memory generation thresholds and high-importance reflection generation.
*   **Actor–Evaluator–Reflector Contract:** Define a clear `Evaluator` interface (`evaluate` method returning `EvaluationResult`) to standardize error assessment and reflection from the output of the LLM.
*   **Tests, Metrics, DX:** Expand integration Qdrant test coverage for Reflective Memory (decay, summarization, dreaming, A-E-R flow). Implement `INFO` level logging for worker activities and export Prometheus-compatible metrics.

### 2. RAE Agentic Memory API Reference

The RAE API is built with FastAPI, offering interactive documentation (Swagger UI, ReDoc) and an OpenAPI 3.0 specification for client generation and integration. Authentication is required for most endpoints via `X-API-Key` or `Authorization` headers. The API is multi-tenant, requiring `X-Tenant-ID`.

**Core API Features (v1):**
*   **Memory Management (`/v1/memory/*`):** Store, query, and delete various types of memories.
*   **Agent Operations (`/v1/agent/*`):** Facilitate the execution of agent tasks, providing memory context.
*   **Knowledge Graphs (`/v1/graph/*`):** Functionality to build and query GraphRAG knowledge graphs.
*   **Cache Management (`/v1/cache/*`):** Operations related to the context cache.
*   **Governance (`/v1/governance/*`):** Includes features for cost tracking and budget management.
*   **Health & Monitoring (`/health`, `/metrics`):** Endpoints for system health checks and Prometheus metrics.

**Enterprise API Features (v1):**
*   **Event Triggers (`/v1/triggers/*`):** Supports event-driven automation, including creating, listing, and managing trigger rules and workflows. Allows manual event emission and provides health/info for the trigger service.
*   **Reflections (`/v1/reflections/*`):** Comprehensive hierarchical reflection system, including generation with clustering, semantic querying, relationship management, statistics, and batch deletion.
*   **Hybrid Search (`/v1/search/*`):** Advanced multi-strategy search (vector + semantic + graph + full-text).
*   **Evaluation (`/v1/evaluation/*`):** Search quality metrics, A/B testing, drift detection.
*   **Dashboard (`/v1/dashboard/*`):** Real-time monitoring with WebSocket support.
*   **Graph Management (`/v1/graph-management/*`):** Advanced graph operations, including creation, retrieval, updating, deleting graph components, and querying complex graph structures for relationship discovery.

### 3. RAE Architecture

The RAE architecture is built on core concepts and services supporting memory management, multi-tenancy, and lifecycle governance for AI agents.

**High-Level Architectural Concepts:**
*   **Memory Layers:** Distinguishes between Episodic (chronological events), Semantic (facts or knowledge), and Reflective (higher-level insights) memories.
*   **Memory Types:** Further categorization of memories (e.g., `event`, `rule`, `sensory`).
*   **Tenancy:** A multi-tenant system that ensures data isolation using `X-Tenant-ID` headers and PostgreSQL's Row Level Security (RLS).

**Core Data Flows:**
*   **Store Memory:** Involves API validation, vector embedding generation, storage in PostgreSQL, and indexing in a vector store (Qdrant or an in-memory vector store).
*   **Query Memory:** Involves query vectorization, vector store search, optional re-ranking by `reranker-service`, PII scrubbing, and optional LLM generation of reflections or answers.

**Key Services:**
*   **LLMService:** An abstraction layer for integrating various LLM backends (Gemini, OpenAI, Ollama, Anthropic).
*   **VectorStore:** An abstraction for vector storage and similarity search (Qdrant or pgvector).
*   **ContextCache:** A Redis-based cache to optimize token usage for recent interactions.
*   **BudgetService & CostController:** Services for monitoring and managing LLM-related costs.
*   **ReflectionEngine:** Dedicated service for generating and managing higher-level reflections from agent memories.

**Memory Lifecycle & Governance:**
*   **Access Tracking:** Automatically updates `last_accessed_at` and `usage_count` for memories on retrieval (e.g., via `/v1/memory/query` or `/v1/agent/execute`).
*   **Importance Scoring:** Utilizes `ImportanceScoringService` to calculate dynamic scores based on factors like Recency, Access Frequency, Graph Centrality, Semantic Relevance, User Rating, Consolidation, and Manual Boost.
*   **Temporal Decay:** Automated periodic process to adjust importance scores based on time and access patterns, with protected, normal, and accelerated decay strategies.
*   **Memory Lifecycle States:** Defines states such as `CREATED`, `ACTIVE`, `AGING`, `STALE`, and `ARCHIVED`, guiding memory management and retention.
*   **Governance Integration:** Memory access statistics are integrated into cost tracking, budget projections, analytics, and an audit trail.

**Observability:**
*   Provides Prometheus-compatible metrics via a `/metrics` endpoint.
*   Integration with Grafana for dashboard visualization.

### 4. GraphRAG - Knowledge Graph Integration

GraphRAG extends RAE's memory capabilities by integrating Knowledge Graph technology with Retrieval-Augmented Generation (RAG).

**Core Concepts:**
*   **Entities:** "Nouns" in the knowledge graph (people, places, concepts, files). Defined by `id`, `name`, `type`, `properties`, `importance`.
*   **Relationships:** "Verbs" connecting entities. Defined by `id`, `source_id`, `target_id`, `relation_type`, `properties`, `confidence`. Common types: `MENTIONS`, `RELATED_TO`, `PART_OF`, `CAUSED_BY`, `USED_IN`, `IMPLEMENTED_IN`.
*   **Triples:** Knowledge stored as (subject-predicate-object) format.
*   **Graph Traversal:** Supports BFS (Breadth-First Search) and DFS (Depth-First Search) for exploring relationships.

**API Endpoints:**
*   **Extract Knowledge Graph (`POST /v1/graph/extract`):** Extracts knowledge graph from episodic memories using LLM-based prompts.
*   **Hybrid Search (extended `POST /v1/memory/query`):** Standard memory query enhanced with graph traversal capabilities.
*   **Advanced Graph Query (`POST /v1/graph/query`):** Dedicated endpoint for complex graph-based searches.
*   **Get Graph Statistics (`GET /v1/graph/stats`):** Retrieves statistics about the knowledge graph.
*   **Get Subgraph (`GET /v1/graph/subgraph`):** Retrieves a subgraph starting from specific nodes.
*   **Hierarchical Reflection (`POST /v1/graph/reflection/hierarchical`):** Generates hierarchical reflections from large episode collections.

**Usage Patterns:** Initial graph construction, incremental updates, contextual AI agent queries, dependency analysis.

**Best Practices:** Confidence thresholds, graph depth, extraction frequency, entity normalization, memory quality, bidirectional relationships, graph validation.

**Performance Considerations:** Indexing for common queries, caching frequently accessed subgraphs, batch processing, pruning of low-importance entities.

### 5. LLM Backends

RAE abstracts LLM interactions, supporting multiple backends.

**Supported Backends:**
*   **OpenAI:** Default choice for advanced capabilities.
*   **Google Gemini:** An experimental choice.
*   **Anthropic:** Another experimental choice.
*   **Ollama:** For local LLM deployment.
*   **Generic LiteLLM Provider:** RAE can interface with any LLM provider supported by the `litellm` library, including Mistral, DeepSeek, and Qwen.

**Configuration:** LLM backend selected via `RAE_LLM_BACKEND` environment variable. `RAE_LLM_MODEL_DEFAULT` specifies the model. API keys are managed via environment variables (e.g., `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `DASHSCOPE_API_KEY`).

### 6. Go SDK (rae_memory_sdk)

A lightweight Go SDK is available for interacting with the RAE Memory API.

**Core Principles:** Simplicity, idiomatic Go, configurability, concurrency-safe.

**Architecture:** `Client` struct with `Config` and `http.Client`. Includes `doRequest` helper for HTTP requests and error responses.

**API Methods:** `StoreMemory`, `QueryMemory`, `DeleteMemory`. Stubs for `EvaluateMemory`, `ReflectOnMemories`, `GetTags`.

**Models:** Go structs mirroring RAE API Pydantic models (e.g., `MemoryLayer`, `MemoryRecord`, `StoreMemoryRequest`).

**Error Handling:** `doRequest` returns Go `error` for network/API issues.

**Dependencies:** Standard Go library only.

### 7. Node.js SDK (rae-memory-sdk)

A lightweight Node.js SDK is available for interacting with the RAE Memory API.

**Core Principles:** Simplicity, idiomatic Node.js (async/await, Promises), type-safe (TypeScript).

**Architecture:** `RaeMemoryClient` class encapsulating all API interactions, with `request` helper.

**API Methods:** `store`, `query`, `delete`. Stubs for `evaluate`, `reflect`, `getTags`.

**Configuration:** `RaeMemoryClientConfig` interface and `fromEnv()` function to load configuration.

**Models:** TypeScript interfaces mirroring RAE API Pydantic models.

**Error Handling:** `request` method throws an `Error` on non-2xx HTTP responses.

**Dependencies:** `node-fetch`, `typescript`.

### 8. RAE Agentic Memory API - OpenAPI Specification

The OpenAPI 3.0.3 specification formally describes the API's structure, endpoints, request/response formats, and data models.

*   **API Endpoints Defined:**
    *   **Health Check (`/health` GET):** Basic API health status.
    *   **Add Memory (`/memory/add` POST):** Allows adding new memories.
    *   **Query Memory (`/memory/query` POST):** Enables querying existing memories.
    *   **Agent Execute (`/agent/execute` POST):** For executing agent tasks.
    *   **Memory Timeline (`/memory/timeline` GET):** Retrieves a chronological timeline of memories.
*   **Core Data Models (`components/schemas`):** Defines `MemoryType` (episodic, semantic, procedural), `AddMemoryRequest`/`Response`, `QueryRequest`/`Response`, `AgentExecuteRequest`/`Response`, `TimelineResponse`.

### 9. RAE Memory Replay Tool - Design Document

Provides transparency and debuggability for RAE-powered agentic systems.

*   **Purpose:** Debugging, training & evaluation, reducing hallucinations, improving reasoning quality, auditing & compliance.
*   **Core Functionality:** Record/list/replay sessions step-by-step, visualize context flow, inspect internal state, filter & search sessions.
*   **Data Model for Recorded Sessions:** Detailed JSON structure storing session information, including retrieval steps, LLM calls, reflection events, and agent answers.
*   **Storage Mechanism:** Dedicated `agent_sessions` database table in Postgres (JSONB column plus indexed fields).
*   **User Interface (High-Level):** Envisions both CLI and Web UI (Dashboard integrated).
*   **Integration Points:** Modifications to `apps/memory-api/routers/agent.py` `execute` endpoint to capture session data.
*   **Future Enhancements:** Comparison mode, what-if scenarios, automated analysis.

### 10. RAE Testing Status - Implicit & Explicit Functionalities

Describes system functionalities based on what is tested.

*   **Pydantic v2 Migration:** Ensures models and configurations are up-to-date.
*   **Semantic Search:** 3-stage semantic search pipeline (topic matching, canonicalization, re-ranking).
*   **Workflow Execution:** Event triggers and workflow dependencies.
*   **Memory Service:** Core API functionalities related to memory management.
*   **ML Service:** Components like embedding service, entity resolution, NLP service, triple extraction.
*   **Reranker Service:** Functionalities of the reranker service.
*   **MCP Integration:** Functionalities related to Model Context Protocol integration.
*   **Reflection from Failure/Success:** Generate reflections based on failed or successful executions.
*   **Reflection Retrieval in Context:** Retrieve reflections as part of context building.
*   **Memory Scoring V2:** Enhanced memory scoring functionality.
*   **Context Injection:** Inject reflections into prompts.
*   **End-to-End Actor-Evaluator-Reflector Flow:** Complete learning loop involving Actor, Evaluator, and Reflector.
*   **Decay Worker:** Background worker for importance decay.
*   **Summarization Worker:** Background worker for session summarization.
*   **Dreaming Worker:** Background worker for generating reflections from historical patterns.
*   **Evaluator Interface:** Standardized `Evaluator` interface for execution assessment.
*   **DB Schema:** Functionality related to the database schema, including `memory_type`, `session_id`, `qdrant_point_id` fields.

### 11. RAE Evaluation Service - Search Quality Metrics

Provides industry-standard Information Retrieval (IR) metrics to measure and monitor search quality.

*   **Overview:** Measures and monitors search quality.
*   **Supported Metrics:** MRR, NDCG, Precision@K, Recall@K, MAP for evaluating search result relevance and ranking.
*   **API Usage:** Evaluate search results against ground truth, A/B test search variants.
*   **Creating Test Sets:** Manual and LLM-assisted annotation of relevance judgments.
*   **Continuous Evaluation:** Scheduled evaluations to monitor quality, store results, and send alerts.
*   **Interpreting Results:** Guidelines for MRR, NDCG@10, Precision@5.
*   **Best Practices:** Use multiple metrics, test regularly, version test sets, stratify queries, monitor trends, A/B test, validate judgments.
*   **Integration with Drift Detection:** Evaluation can be triggered by drift detection events.
*   **Future Enhancements:** Automatic test set generation, inter-annotator agreement, query difficulty estimation, failure analysis, real-time dashboard, statistical significance testing, CTR, user surveys.

### 12. RAE Rules Engine - Event-Driven Automation

RAE's event-driven automation system for defining triggers, conditions, and actions based on memory system events.

*   **Overview:** Event-driven automation system.
*   **Architecture (Event Processing Pipeline):** Event reception, trigger matching, condition evaluation, rate limiting & cooldown, action execution (with retries).
*   **Core Concepts:**
    *   **Events:** Supported types include `MEMORY_CREATED`, `REFLECTION_GENERATED`, `DRIFT_DETECTED`, `BUDGET_WARNING`, `EVALUATION_COMPLETED`, and more.
    *   **Triggers:** Define when rules fire (Event Type, Condition, Actions, Rate Limiting, Cooldown).
    *   **Conditions:** Determine if a trigger fires (various operators, AND/OR logic, nested groups, dot notation).
    *   **Actions:** Operations executed (e.g., `SEND_NOTIFICATION`, `SEND_WEBHOOK`, `GENERATE_REFLECTION`, `RUN_EVALUATION`).
*   **API Usage:** `RulesEngine.process_event`, `POST /v1/automation/triggers` for creation.
*   **Common Use Cases:** Automatic reflection generation, budget alerts, drift detection response, semantic extraction pipeline.
*   **Rate Limiting & Cooldown:** Configurable limits to prevent runaway automation and rapid re-triggers.
*   **Retry Logic:** Actions can be configured with retry mechanisms for transient failures.
*   **Execution Tracking:** Tracks every action execution; history is queryable.
*   **Best Practices:** Use rate limiting, add cooldowns, enable retries, test conditions, monitor executions, use webhooks, structured logging.
*   **Monitoring:** Key metrics include triggers matched, action success/failure rates, retry frequency, execution duration, and rate limit hits.
*   **Troubleshooting:** Guidance for triggers not firing, actions failing, and performance issues.
*   **Future Enhancements:** Scheduled triggers, templates/marketplace, action chaining (workflows), conditional action execution, analytics dashboard, visual builder UI.