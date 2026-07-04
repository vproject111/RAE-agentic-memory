# API Cookbook - Task-Oriented Recipes

## Overview

This cookbook provides **complete, working examples** for common RAE use cases. Each recipe includes:
- **Goal**: What you want to achieve
- **Complete request**: Full curl command with all parameters
- **Expected response**: What you should receive
- **Explanation**: Why it works this way

**Base URL**: `http://localhost:8000` (adjust for your deployment)

---

## Memory Storage Recipes

### Recipe 1: Store Immediate Context (Sensory Memory)

**Goal**: Capture what just happened - recent context that might not need long-term storage.

**Use Cases**:
- Recent user actions
- Current conversation turns
- Temporary context for next prompt

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memories/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "layer": "sensory",
    "content": "User just clicked the export button in dashboard",
    "tags": ["action", "ui-interaction"],
    "importance": 0.3,
    "source": "ui-tracker"
  }'
```

**Response**:
```json
{
  "id": "mem_abc123",
  "layer": "sensory",
  "message": "Sensory memory created successfully",
  "ttl_seconds": 3600
}
```

**Key Points**:
- `layer: "sensory"` - Short-lived memory (1-24 hours depending on config)
- Low `importance` (0.3) - Won't be promoted to long-term automatically
- `ttl_seconds` - How long before automatic decay

---

### Recipe 2: Store User Preferences (Long-Term Memory)

**Goal**: Remember user settings, preferences, or profile information permanently.

**Use Cases**:
- User preferences
- Profile information
- Learned patterns about user behavior

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memories/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "layer": "semantic",
    "memory_type": "profile",
    "content": "User prefers dark mode, uses TypeScript for all projects, and likes minimal UI",
    "tags": ["preference", "profile", "ui"],
    "importance": 0.9,
    "source": "user-settings",
    "metadata": {
      "category": "preferences",
      "user_confirmed": true
    }
  }'
```

**Response**:
```json
{
  "id": "mem_xyz789",
  "layer": "semantic",
  "memory_type": "profile",
  "message": "Long-term memory created successfully",
  "entities_extracted": ["TypeScript", "dark mode"],
  "relationships_created": 2
}
```

**Key Points**:
- `layer: "semantic"` - Long-term storage
- `memory_type: "profile"` - Categorizes as profile information
- High `importance` (0.9) - Will persist and be prioritized in queries
- `entities_extracted` - GraphRAG automatically extracted entities

---

### Recipe 3: Store Event with Context (Episodic Memory)

**Goal**: Remember specific events with time and context - what happened when.

**Use Cases**:
- User actions with timestamp
- Decisions made
- Specific conversations

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memories/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "layer": "episodic",
    "memory_type": "event",
    "content": "Team decided to migrate from REST to GraphQL API. Main reasons: reduce over-fetching, enable flexible queries, improve mobile app performance. Decision made during sprint planning.",
    "tags": ["decision", "architecture", "api"],
    "importance": 0.85,
    "source": "meeting-notes",
    "metadata": {
      "meeting_type": "sprint-planning",
      "participants": ["Alice", "Bob", "Charlie"],
      "decision_maker": "Alice"
    }
  }'
```

**Response**:
```json
{
  "id": "mem_event456",
  "layer": "episodic",
  "memory_type": "event",
  "message": "Episodic memory created successfully",
  "timestamp": "2025-12-01T14:30:00Z",
  "entities_extracted": ["GraphQL", "REST", "API", "mobile app"],
  "relationships_created": 5
}
```

**Key Points**:
- `layer: "episodic"` - Time-stamped event memory
- `memory_type: "event"` - Specific occurrence
- `metadata.participants` - Rich context for later retrieval
- Automatic timestamp capture

---

### Recipe 4: Store Multiple Related Memories (Batch)

**Goal**: Efficiently store multiple related memories in one request.

**Use Cases**:
- Importing conversation history
- Bulk knowledge base ingestion
- Processing multiple documents

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memories/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "memories": [
      {
        "layer": "semantic",
        "content": "PostgreSQL is used for primary data storage with pgvector extension",
        "tags": ["database", "architecture"],
        "importance": 0.8
      },
      {
        "layer": "semantic",
        "content": "Qdrant handles vector similarity search for semantic memory retrieval",
        "tags": ["database", "vectors", "architecture"],
        "importance": 0.8
      },
      {
        "layer": "semantic",
        "content": "Redis is used for caching and Celery task queue",
        "tags": ["database", "cache", "architecture"],
        "importance": 0.7
      }
    ],
    "extract_graph": true
  }'
```

**Response**:
```json
{
  "batch_id": "batch_123",
  "memories_created": 3,
  "memory_ids": ["mem_001", "mem_002", "mem_003"],
  "entities_extracted": ["PostgreSQL", "Qdrant", "Redis", "Celery"],
  "relationships_created": 8,
  "processing_time_ms": 450
}
```

**Key Points**:
- Batch endpoint is more efficient than multiple individual calls
- `extract_graph: true` - Process all memories together for better entity resolution
- Returns `batch_id` for tracking

---

## Query Recipes

### Recipe 5: Simple Semantic Search

**Goal**: Find relevant memories based on meaning, not just keywords.

**Use Cases**:
- "What does the user like?"
- "Tell me about the architecture"
- General knowledge retrieval

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "What are the user preferences for UI design?",
    "top_k": 5,
    "min_importance": 0.5
  }'
```

**Response**:
```json
{
  "results": [
    {
      "id": "mem_xyz789",
      "content": "User prefers dark mode, uses TypeScript for all projects, and likes minimal UI",
      "score": 0.92,
      "layer": "semantic",
      "tags": ["preference", "profile", "ui"],
      "importance": 0.9
    },
    {
      "id": "mem_ui_002",
      "content": "User mentioned disliking cluttered interfaces during onboarding",
      "score": 0.78,
      "layer": "episodic",
      "tags": ["preference", "ui", "onboarding"],
      "importance": 0.6
    }
  ],
  "total_results": 2,
  "query_time_ms": 45
}
```

**Key Points**:
- Vector similarity search finds semantically related content
- `min_importance: 0.5` - Filter out low-importance memories
- Results sorted by `score` (relevance)

---

### Recipe 6: Query with GraphRAG (Knowledge Graph Enhanced)

**Goal**: Get richer context by traversing entity relationships in the knowledge graph.

**Use Cases**:
- "Tell me everything about X"
- Complex multi-hop queries
- Finding indirect connections

**Request**:
```bash
curl -X POST http://localhost:8000/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "What database technologies are used in the architecture?",
    "use_graph": true,
    "graph_depth": 2,
    "top_k": 10,
    "include_entities": true
  }'
```

**Response**:
```json
{
  "results": [
    {
      "id": "mem_001",
      "content": "PostgreSQL is used for primary data storage with pgvector extension",
      "score": 0.95,
      "layer": "semantic",
      "entities": ["PostgreSQL", "pgvector"]
    },
    {
      "id": "mem_002",
      "content": "Qdrant handles vector similarity search for semantic memory retrieval",
      "score": 0.88,
      "layer": "semantic",
      "entities": ["Qdrant"]
    },
    {
      "id": "mem_003",
      "content": "Redis is used for caching and Celery task queue",
      "score": 0.85,
      "layer": "semantic",
      "entities": ["Redis", "Celery"]
    }
  ],
  "graph_context": {
    "entities_found": ["PostgreSQL", "Qdrant", "Redis", "Celery", "pgvector"],
    "relationships": [
      {"from": "PostgreSQL", "to": "pgvector", "type": "uses"},
      {"from": "Redis", "to": "Celery", "type": "supports"}
    ]
  },
  "total_results": 3,
  "query_time_ms": 120
}
```

**Key Points**:
- `use_graph: true` - Enable GraphRAG
- `graph_depth: 2` - Traverse up to 2 relationship hops
- `include_entities: true` - Return extracted entities
- `graph_context` - Shows entity relationships discovered

---

### Recipe 7: Query Only Reflective Memory (Insights/Wisdom)

**Goal**: Retrieve only high-level reflections, patterns, and learned insights - not raw memories.

**Use Cases**:
- "What have we learned about X?"
- "What patterns emerged?"
- Strategic insights

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "What lessons have we learned about API design?",
    "top_k": 5,
    "filters": {
      "layer": "reflective"
    }
  }'
```

**Response**:
```json
{
  "results": [
    {
      "id": "refl_001",
      "content": "Reflection: Team consistently prefers GraphQL over REST for new projects. Pattern observed: GraphQL adoption correlates with mobile-first requirements and reduces API versioning issues.",
      "score": 0.89,
      "layer": "reflective",
      "reflection_type": "pattern",
      "source_memories": ["mem_event456", "mem_event789"],
      "confidence": 0.85
    }
  ],
  "total_results": 1,
  "query_time_ms": 35
}
```

**Key Points**:
- `filters.layer: "reflective"` - Only reflections, not raw memories
- `reflection_type: "pattern"` - Type of insight (pattern, lesson, principle)
- `source_memories` - Links back to original memories that generated this reflection
- `confidence` - How confident the Reflection Engine is in this insight

---

### Recipe 8: Query Specific Memory Layer

**Goal**: Query a specific memory layer (e.g., only long-term memories, only recent events).

**Request for Long-Term Memory only**:
```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "user preferences",
    "top_k": 10,
    "filters": {
      "layer": "semantic",
      "memory_type": "profile"
    }
  }'
```

**Request for Recent Events only**:
```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "recent user actions",
    "top_k": 20,
    "filters": {
      "layer": "episodic",
      "time_range": {
        "start": "2025-12-01T00:00:00Z",
        "end": "2025-12-01T23:59:59Z"
      }
    }
  }'
```

**Key Points**:
- Use `filters.layer` to target specific memory layers
- Combine with `time_range` for temporal queries
- `memory_type` further narrows results

---

## Reflection Recipes

### Recipe 9: Trigger Manual Reflection

**Goal**: Manually generate reflections from accumulated memories (normally done by background worker).

**Use Cases**:
- After importing batch data
- On-demand insight generation
- Testing reflection quality

**Request**:
```bash
curl -X POST http://localhost:8000/v1/reflections/generate \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "focus_tags": ["architecture", "decision"],
    "min_memories": 3,
    "reflection_type": "pattern"
  }'
```

**Response**:
```json
{
  "reflection_id": "refl_new123",
  "content": "Pattern identified: Architecture decisions are consistently data-driven. Team evaluates performance metrics before choosing technologies. Recent examples: GraphQL adoption (reduced over-fetching by 40%), PostgreSQL with pgvector (semantic search latency <50ms).",
  "confidence": 0.82,
  "source_memory_count": 5,
  "entities_involved": ["GraphQL", "PostgreSQL", "pgvector"],
  "created_at": "2025-12-01T14:45:00Z"
}
```

**Key Points**:
- `focus_tags` - Generate reflections about specific topics
- `min_memories: 3` - Require at least 3 related memories for a reflection
- `reflection_type: "pattern"` - Type of reflection to generate

---

### Recipe 10: Query Reflections About Specific Topic

**Goal**: Find all reflections (insights) related to a specific topic or entity.

**Request**:
```bash
curl -X POST http://localhost:8000/v1/reflections/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "topic": "user preferences",
    "reflection_types": ["pattern", "principle"],
    "min_confidence": 0.7
  }'
```

**Response**:
```json
{
  "reflections": [
    {
      "id": "refl_pref001",
      "content": "Principle: User consistently prioritizes simplicity over feature richness. Evidence: disabled 3 advanced features, chose minimal themes, requested keyboard shortcuts for core actions only.",
      "confidence": 0.88,
      "reflection_type": "principle",
      "created_at": "2025-11-15T10:00:00Z"
    }
  ],
  "total_reflections": 1
}
```

---

## Graph Recipes

### Recipe 11: Extract Entities from Memory

**Goal**: Force entity extraction for memories that didn't have it yet.

**Request**:
```bash
curl -X POST http://localhost:8000/v1/graph/extract \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "memory_ids": ["mem_001", "mem_002", "mem_003"]
  }'
```

**Response**:
```json
{
  "entities_extracted": 12,
  "relationships_created": 8,
  "entities": [
    {"name": "PostgreSQL", "type": "TECHNOLOGY", "mentions": 2},
    {"name": "Redis", "type": "TECHNOLOGY", "mentions": 1},
    {"name": "GraphQL", "type": "TECHNOLOGY", "mentions": 1}
  ]
}
```

---

### Recipe 12: Query Knowledge Graph Directly

**Goal**: Explore entity relationships without memory content.

**Request**:
```bash
curl -X POST http://localhost:8000/v1/graph/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "entity": "PostgreSQL",
    "relationship_types": ["uses", "integrates_with", "supports"],
    "max_depth": 2
  }'
```

**Response**:
```json
{
  "entity": "PostgreSQL",
  "relationships": [
    {
      "target": "pgvector",
      "type": "uses",
      "weight": 0.9,
      "source_memories": ["mem_001"]
    },
    {
      "target": "Qdrant",
      "type": "complements",
      "weight": 0.7,
      "source_memories": ["mem_001", "mem_002"]
    }
  ],
  "total_relationships": 2
}
```

---

## GDPR & Data Management Recipes

### Recipe 13: Delete User Data (GDPR Right to Erasure)

**Goal**: Permanently delete all data for a specific user (GDPR Article 17).

**Use Cases**:
- User account deletion
- GDPR compliance
- Data cleanup

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memory/delete_user \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "user_id": "user_alice",
    "cascade": true,
    "audit_reason": "User requested account deletion per GDPR Article 17"
  }'
```

**Response**:
```json
{
  "deleted_memories": 47,
  "deleted_reflections": 8,
  "deleted_entities": 12,
  "audit_log_id": "audit_del_123",
  "message": "All user data deleted successfully",
  "timestamp": "2025-12-01T15:00:00Z"
}
```

**Key Points**:
- `cascade: true` - Delete all related data (memories, reflections, graph entities)
- `audit_reason` - Required for audit trail (who, when, why)
- `audit_log_id` - Permanent record of deletion for compliance

---

### Recipe 14: Export User Data (GDPR Data Portability)

**Goal**: Export all user data in machine-readable format (GDPR Article 20).

**Request**:
```bash
curl -X POST http://localhost:8000/v1/memory/export \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "user_id": "user_alice",
    "format": "json",
    "include_reflections": true,
    "include_graph": true
  }'
```

**Response** (simplified):
```json
{
  "export_id": "export_456",
  "user_id": "user_alice",
  "memories": [
    {
      "id": "mem_001",
      "content": "...",
      "layer": "semantic",
      "created_at": "2025-11-01T10:00:00Z"
    }
  ],
  "reflections": [...],
  "graph_entities": [...],
  "export_timestamp": "2025-12-01T15:05:00Z",
  "total_memories": 47,
  "download_url": "https://api.example.com/exports/export_456.json"
}
```

---

## Cost Control Recipes

### Recipe 15: Check Current Budget Status

**Goal**: Monitor LLM API spending and budget limits.

**Request**:
```bash
curl -X GET http://localhost:8000/v1/cost/budget \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "tenant_id": "demo-tenant",
  "daily_budget": 10.00,
  "monthly_budget": 100.00,
  "daily_spent": 3.45,
  "monthly_spent": 42.18,
  "daily_remaining": 6.55,
  "monthly_remaining": 57.82,
  "daily_percent_used": 34.5,
  "monthly_percent_used": 42.2,
  "alert_threshold_reached": false
}
```

---

### Recipe 16: Get Cost Breakdown by Operation

**Goal**: Understand where LLM costs are coming from.

**Request**:
```bash
curl -X GET "http://localhost:8000/v1/cost/breakdown?start_date=2025-12-01&end_date=2025-12-01" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "total_cost": 3.45,
  "by_operation": {
    "embedding": 1.20,
    "graph_extraction": 1.50,
    "reflection_generation": 0.60,
    "query_context_building": 0.15
  },
  "by_model": {
    "gpt-4o-mini": 2.80,
    "gpt-4o": 0.65
  },
  "total_tokens": {
    "input": 125000,
    "output": 18000
  }
}
```

**Key Points**:
- Breakdown by operation type helps identify optimization opportunities
- Model-level breakdown shows cost per provider

---

## Advanced Recipes

### Recipe 17: Hybrid Search with Filters and Ranking

**Goal**: Combine semantic search, keyword matching, graph traversal, and custom filters.

**Request**:
```bash
curl -X POST http://localhost:8000/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "database architecture decisions",
    "use_graph": true,
    "graph_depth": 2,
    "use_reranker": true,
    "top_k": 20,
    "filters": {
      "tags": ["architecture", "database"],
      "importance_min": 0.6,
      "layers": ["semantic", "episodic"],
      "time_range": {
        "start": "2025-11-01T00:00:00Z"
      }
    },
    "weights": {
      "semantic": 0.5,
      "keyword": 0.2,
      "graph": 0.3
    }
  }'
```

**Response**:
```json
{
  "results": [
    {
      "id": "mem_001",
      "content": "PostgreSQL chosen for ACID compliance and pgvector support...",
      "final_score": 0.94,
      "score_breakdown": {
        "semantic": 0.92,
        "keyword": 0.85,
        "graph": 0.98
      },
      "reranked": true
    }
  ],
  "total_results": 5,
  "search_strategy": "hybrid_graph_reranked",
  "query_time_ms": 180
}
```

**Key Points**:
- `use_reranker: true` - Apply ML re-ranking (if Reranker Service available)
- `weights` - Custom weighting of search strategies
- `score_breakdown` - Transparency into ranking

---

### Recipe 18: Context Building for LLM Prompts

**Goal**: Build optimal context for an LLM prompt, respecting token limits.

**Request**:
```bash
curl -X POST http://localhost:8000/v1/context/build \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "Help me design a new API endpoint for user analytics",
    "max_tokens": 2000,
    "include_reflections": true,
    "include_recent_context": true,
    "context_window_hours": 24
  }'
```

**Response**:
```json
{
  "context": "## Relevant Knowledge\n\n1. **Architecture**: PostgreSQL + Redis + Qdrant stack...\n\n2. **Recent Decisions**: Team adopted GraphQL for flexible queries...\n\n3. **Patterns**: API design follows RESTful principles with GraphQL for complex queries...",
  "context_tokens": 1850,
  "sources": [
    {"id": "mem_001", "content": "...", "layer": "semantic"},
    {"id": "refl_005", "content": "...", "layer": "reflective"}
  ],
  "total_sources": 8
}
```

**Key Points**:
- `max_tokens` - Respect LLM context window limits
- `include_reflections: true` - Add high-level insights
- `context_window_hours: 24` - Include recent context
- Returns formatted context ready for LLM prompt

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Example Response |
|------|---------|------------------|
| **200** | Success | Standard success response |
| **400** | Bad Request | `{"error": "Invalid layer specified"}` |
| **401** | Unauthorized | `{"error": "Invalid API key"}` |
| **402** | Payment Required | `{"error": "Budget exceeded", "daily_limit": 10.00, "spent": 10.50}` |
| **404** | Not Found | `{"error": "Memory not found"}` |
| **429** | Too Many Requests | `{"error": "Rate limit exceeded", "retry_after": 60}` |
| **500** | Server Error | `{"error": "Internal server error"}` |

### Recipe 19: Handling Budget Exceeded (HTTP 402)

When you receive HTTP 402, it means the cost budget was exceeded:

**Error Response**:
```json
{
  "error": "Budget exceeded",
  "error_code": "BUDGET_EXCEEDED",
  "daily_limit": 10.00,
  "daily_spent": 10.50,
  "monthly_limit": 100.00,
  "monthly_spent": 85.20
}
```

**Actions**:
1. Check budget status: `GET /v1/cost/budget`
2. Increase budget (if authorized): `POST /v1/cost/budget/update`
3. Wait until next billing period (daily/monthly)
4. Optimize usage (use caching, reduce unnecessary operations)

---

## Best Practices

### 1. Memory Layer Selection

| Layer | Use When | TTL | Importance Range |
|-------|----------|-----|------------------|
| **Sensory** | Temporary context (minutes-hours) | 1-24 hours | 0.1 - 0.4 |
| **Episodic** | Specific events with timestamp | Days-weeks | 0.4 - 0.7 |
| **Semantic** | Long-term knowledge/facts | Months-years | 0.7 - 1.0 |
| **Reflective** | Insights/patterns (auto-generated) | Permanent | 0.8 - 1.0 |

### 2. Importance Scoring Guidelines

- **0.1 - 0.3**: Temporary, disposable (logs, debug info)
- **0.4 - 0.6**: Moderate importance (routine events, normal operations)
- **0.7 - 0.8**: Important (key decisions, user preferences, critical events)
- **0.9 - 1.0**: Critical (strategic decisions, core knowledge, security events)

### 3. Tag Strategy

Use hierarchical tags:
- **Category**: `preference`, `decision`, `error`, `achievement`
- **Domain**: `ui`, `api`, `database`, `security`
- **Priority**: `critical`, `important`, `routine`

Example: `["decision", "architecture", "critical"]`

### 4. Cost Optimization

- **Enable caching**: Most queries hit Redis cache first
- **Batch operations**: Use `/batch` endpoints instead of loops
- **Right-size models**: Use smaller models (gpt-4o-mini) for embeddings
- **Filter aggressively**: Use `min_importance` and `filters` to reduce processing

---

## Related Documentation

- [REST API Reference](./rest-api.md) - Complete API endpoint documentation
- [SDK Python Reference](./SDK_PYTHON_REFERENCE.md) - Python client library
- [Hybrid Search Guide](../concepts/hybrid-search.md) - Search algorithm details
- [GraphRAG Implementation](../memory/GRAPHRAG_IMPLEMENTATION.md) - Knowledge graph details
- [Cost Controller](../llm/cost-controller.md) - Budget and cost tracking
- [Multi-Tenancy](../architecture/MULTI_TENANCY.md) - Tenant isolation

---

**Last Updated**: 2025-12-01
**Questions?** See [Documentation Index](../../index.md) or [GitHub Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)
