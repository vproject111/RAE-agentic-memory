# RAE Architecture

> **Latest Update**: RAE now implements the Repository/DAO pattern for improved separation of concerns and testability. See [Repository Pattern Documentation](../architecture/repository-pattern.md) for details.

Complete architectural overview of the Reflective Agentic Memory Engine.

## System Overview

RAE is a sophisticated cognitive memory system for AI agents, consisting of multiple interconnected components working together to provide persistent, intelligent memory.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Python SDK   │  │ MCP Server   │  │ REST API     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                      API GATEWAY                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI Application (apps/memory_api/main.py)          │   │
│  │  - Authentication (API Key / JWT)                        │   │
│  │  - Rate Limiting (Redis)                                │   │
│  │  - CORS                                                  │   │
│  │  - Request Validation                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────────┐
│                      SERVICE LAYER (Business Logic)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Memory     │  │  Reflection  │  │    Graph     │         │
│  │   Service    │  │   Engine     │  │   Service    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐         │
│  │   Context    │  │  Embedding   │  │   Scoring    │         │
│  │    Cache     │  │   Service    │  │   Service    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────────┐
│                  REPOSITORY LAYER (Data Access)                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ GraphRepository  │  │ MemoryRepository │                    │
│  │ - Node CRUD      │  │ - Memory CRUD    │                    │
│  │ - Edge CRUD      │  │ - Query ops      │                    │
│  │ - Traversal      │  │ - Batch ops      │                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
└───────────┼──────────────────────┼──────────────────────────────┘
            │                      │
┌───────────┴──────────────────────┴──────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │    Qdrant    │  │    Redis     │         │
│  │  + pgvector  │  │   (Vectors)  │  │   (Cache)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. API Gateway (FastAPI)

**Location**: `apps/memory_api/main.py`

**Responsibilities**:
- HTTP request handling
- Authentication & authorization
- Rate limiting
- Input validation
- CORS policy enforcement
- API documentation (OpenAPI)

**Key Features**:
```python
# Security middleware
- API Key authentication
- JWT token verification
- Rate limiting (Redis-based)
- CORS configuration

# Monitoring
- Health check endpoints
- Prometheus metrics
- Structured logging
```

### 2. Memory Service

**Location**: `apps/memory_api/services/memory_service.py`

**Responsibilities**:
- Store memories across layers (EM, WM, SM, LTM)
- Query memories (vector + keyword search)
- Memory lifecycle management
- Multi-tenancy enforcement

**Key Operations**:
```python
class MemoryService:
    async def store_memory(content, layer, tags, metadata)
    async def query_memory(query, layer, top_k)
    async def update_memory(memory_id, updates)
    async def delete_memory(memory_id)
    async def consolidate_memories(min_age_days)
```

### 3. Repository Layer (NEW)

**Locations**: `apps/memory_api/repositories/`

**Purpose**: Implements the Repository/DAO pattern to separate data access from business logic.

**Key Repositories**:
- **GraphRepository** - All knowledge graph operations (nodes, edges, traversal)
- **MemoryRepository** - Memory storage and retrieval operations

**Benefits**:
- **Separation of Concerns**: Business logic in services, SQL in repositories
- **Testability**: Services can be unit tested with mocked repositories
- **Maintainability**: Database changes isolated to repository layer
- **Consistency**: Standardized data access patterns

See [Repository Pattern Documentation](../architecture/repository-pattern.md) for implementation details.

### 4. Reflection Engine

**Location**: `apps/memory_api/services/reflection_service.py`

**Responsibilities**:
- Analyze episodic memories
- Extract patterns and insights
- Generate semantic knowledge
- Create long-term memories

**Process Flow**:
```
Episodic Memories
    ↓
Collection (recent memories)
    ↓
Analysis (LLM-powered)
    ↓
Pattern Detection
    ↓
Insight Generation
    ↓
Store as Semantic/LTM
```

### 4. Graph Service (GraphRAG)

**Location**: `apps/memory_api/services/graph_service.py`

**Responsibilities**:
- Extract entities and relationships
- Build knowledge graph
- Graph traversal and querying
- Path finding algorithms

**Graph Operations**:
```python
class GraphService:
    async def extract_graph(memory)
    async def add_entity(name, type, properties)
    async def add_relationship(source, relation, target)
    async def traverse(start_nodes, max_depth)
    async def find_path(start, end)
    async def pagerank(top_k)
```

### 5. Context Cache Service

**Location**: `apps/memory_api/services/context_cache.py`

**Responsibilities**:
- Cache expensive computations
- Store embeddings
- Reduce LLM API costs
- Session management

**Caching Strategy**:
```python
# Multi-level caching
L1: In-memory (application)
L2: Redis (distributed)
L3: Database (persistent)

# Cache key structure
key = f"embedding:{model}:{hash(content)}"
ttl = 24 * 3600  # 24 hours
```

### 6. Embedding Service

**Location**: `apps/memory_api/services/embedding_service.py`

**Responsibilities**:
- Generate text embeddings
- Support multiple models
- Batch processing
- Caching for efficiency

**Supported Models**:
```python
- OpenAI (text-embedding-3-small/large)
- Sentence Transformers (local)
- ONNX models (optimized)
- Cohere
- Voyage AI
```

### 7. Vector Store

**Technology**: Qdrant or pgvector

**Responsibilities**:
- Store embedding vectors
- Fast similarity search
- Hybrid search (vector + keyword)
- Collection management

**Operations**:
```python
# Qdrant operations
await qdrant.upsert(collection, points)
await qdrant.search(collection, vector, top_k)
await qdrant.scroll(collection, filters)
```

### 8. Database (PostgreSQL + pgvector)

**Schema Overview**:
```sql
-- Memories table
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    project_id UUID,
    layer TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    tags TEXT[],
    metadata JSONB,
    importance FLOAT,
    timestamp TIMESTAMP,
    created_at TIMESTAMP
);

-- Knowledge graph entities
CREATE TABLE kg_entities (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    properties JSONB,
    importance FLOAT
);

-- Knowledge graph relationships
CREATE TABLE kg_relationships (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    source_id UUID REFERENCES kg_entities(id),
    target_id UUID REFERENCES kg_entities(id),
    relation_type TEXT NOT NULL,
    confidence FLOAT
);
```

### 9. Background Workers (Celery)

**Location**: `apps/memory_api/celery_app.py`

**Tasks**:
```python
# Scheduled tasks
@celery.task
def periodic_reflection():
    """Run reflection every 6 hours"""

@celery.task
def consolidate_old_memories():
    """Consolidate episodic → semantic daily"""

@celery.task
def update_importance_scores():
    """Recalculate importance scores"""

@celery.task
def prune_working_memory():
    """Clear old working memory hourly"""
```

## Data Flow

### Store Memory Flow

```
1. Client Request
   POST /v1/memory/store
   {
     "content": "...",
     "layer": "episodic",
     "tags": ["..."]
   }
   ↓
2. API Gateway
   - Authenticate
   - Rate limit check
   - Validate input
   ↓
3. Memory Service
   - Extract metadata
   - Generate embedding
   - Check duplicates
   ↓
4. Storage
   - Store in PostgreSQL
   - Store vector in Qdrant
   - Cache in Redis
   ↓
5. Background Processing (async)
   - Extract graph entities
   - Update importance scores
   - Trigger reflection if needed
   ↓
6. Response
   {
     "id": "mem_123",
     "status": "stored"
   }
```

### Query Memory Flow

```
1. Client Request
   POST /v1/memory/query
   {
     "query": "...",
     "top_k": 10,
     "use_graph": true
   }
   ↓
2. Cache Check
   - Check Redis for cached results
   - Return if found
   ↓
3. Embedding
   - Generate query embedding
   - Check embedding cache
   ↓
4. Vector Search
   - Query Qdrant
   - Get top_k similar vectors
   ↓
5. Graph Expansion (if enabled)
   - Extract entities from results
   - Traverse graph
   - Find related memories
   ↓
6. Scoring & Ranking
   - Calculate relevance scores
   - Apply recency boost
   - Rank by importance
   ↓
7. Context Synthesis
   - Combine vector + graph results
   - Deduplicate
   - Format response
   ↓
8. Cache & Return
   - Cache results in Redis
   - Return to client
```

## Multi-Tenancy

### Tenant Isolation

```python
# Row Level Security (RLS)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON memories
    FOR ALL
    TO authenticated
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

# Middleware enforcement
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    request.state.tenant_id = tenant_id

    # Set for database session
    async with db.connection() as conn:
        await conn.execute(
            "SET LOCAL app.current_tenant = $1",
            tenant_id
        )

    return await call_next(request)
```

### Tenant Configuration

```python
class TenantConfig:
    tenant_id: str
    max_memories: int
    max_projects: int
    features_enabled: List[str]
    llm_provider: str
    embedding_model: str
```

## Security Architecture

### Authentication Flow

```
1. Client includes credentials:
   - X-API-Key header, OR
   - Authorization: Bearer <token>
   ↓
2. Authentication Middleware
   - Verify API key / JWT token
   - Check expiration
   - Load user context
   ↓
3. Authorization Check
   - Verify tenant access
   - Check permissions
   ↓
4. Request Processing
   (if authenticated)
```

### Rate Limiting

```python
# Redis-based sliding window
key = f"rate_limit:{identifier}"
window = 60  # seconds
limit = 100  # requests

# Increment counter
count = await redis.incr(key)
if count == 1:
    await redis.expire(key, window)

if count > limit:
    raise HTTPException(429, "Rate limit exceeded")
```

## Scalability

### Horizontal Scaling

```
┌──────────────────────────────────────┐
│         Load Balancer                │
│         (Nginx / ALB)                │
└──────────┬───────────────────────────┘
           │
     ┌─────┴─────┬─────────┬─────────┐
     │           │         │         │
┌────▼────┐ ┌───▼────┐ ┌──▼─────┐ ┌─▼──────┐
│  API 1  │ │  API 2 │ │  API 3 │ │  ...   │
└────┬────┘ └───┬────┘ └──┬─────┘ └─┬──────┘
     │          │         │         │
     └──────────┴─────────┴─────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼──┐  ┌────▼────┐  ┌───▼──────┐
│PostgreSQL│  │ Qdrant  │  │  Redis   │
│ Primary  │  │Cluster  │  │ Cluster  │
└──────────┘  └─────────┘  └──────────┘
```

### Database Replication

```
┌──────────────┐
│  Primary DB  │
│  (Write)     │
└──────┬───────┘
       │
  Replication
       │
  ┌────┴─────┬──────────┐
  │          │          │
┌─▼──────┐ ┌▼────────┐ ┌▼────────┐
│Replica1│ │Replica2 │ │Replica3 │
│(Read)  │ │(Read)   │ │(Read)   │
└────────┘ └─────────┘ └─────────┘
```

## Monitoring & Observability

### Health Checks

```python
GET /health          # Overall health
GET /health/ready    # Readiness probe
GET /health/live     # Liveness probe
GET /metrics         # Prometheus metrics
```

### Key Metrics

```
# Application metrics
http_requests_total
http_request_duration_seconds
memory_store_operations_total
memory_query_latency_seconds

# Business metrics
memories_stored_total{layer="episodic"}
memories_stored_total{layer="semantic"}
reflections_generated_total
graph_entities_total

# Infrastructure metrics
database_connections_active
redis_cache_hit_rate
qdrant_collection_size
```

### Logging

```python
# Structured logging with structlog
logger.info(
    "memory_stored",
    memory_id=memory.id,
    tenant_id=memory.tenant_id,
    layer=memory.layer,
    duration_ms=duration
)
```

## Deployment Architecture

### Development

```
Local Machine
├── Docker Compose
│   ├── PostgreSQL
│   ├── Redis
│   ├── Qdrant
│   └── RAE API
└── Python venv (for development)
```

### Production (Kubernetes)

```
Kubernetes Cluster
├── Namespace: rae-memory
│   ├── Deployment: rae-api (3 replicas)
│   ├── Deployment: celery-worker (2 replicas)
│   ├── StatefulSet: postgresql
│   ├── StatefulSet: redis
│   ├── StatefulSet: qdrant
│   ├── Service: rae-api (LoadBalancer)
│   ├── Service: postgresql (ClusterIP)
│   ├── Service: redis (ClusterIP)
│   ├── Service: qdrant (ClusterIP)
│   ├── ConfigMap: app-config
│   ├── Secret: app-secrets
│   └── Ingress: rae-ingress (with TLS)
```

## Technology Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **asyncpg** - Async PostgreSQL driver
- **Celery** - Background tasks

### Databases
- **PostgreSQL 15** - Primary datastore
- **pgvector** - Vector extension
- **Qdrant** - Vector database
- **Redis 7** - Caching

### AI/ML
- **OpenAI API** - LLM & embeddings
- **Anthropic Claude** - Alternative LLM
- **LangChain** - LLM framework
- **Sentence Transformers** - Local embeddings

### Infrastructure
- **Docker** - Containerization
- **Kubernetes** - Orchestration
- **Nginx** - Reverse proxy
- **Prometheus** - Metrics
- **Grafana** - Visualization

## Configuration

All configuration via environment variables:

```env
# Application
RAE_ENV=production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://...
DB_POOL_SIZE=20

# Redis
REDIS_URL=redis://...

# Vector Store
RAE_VECTOR_BACKEND=qdrant
QDRANT_URL=http://...

# LLM
RAE_LLM_BACKEND=openai
OPENAI_API_KEY=sk-...

# Security
ENABLE_API_KEY_AUTH=true
ENABLE_RATE_LIMITING=true

# Features
ENABLE_REFLECTION=true
ENABLE_GRAPH_EXTRACTION=true
```

## Best Practices

### 1. Use Connection Pooling
```python
# PostgreSQL pool
pool = await asyncpg.create_pool(
    host=...,
    min_size=5,
    max_size=20
)
```

### 2. Cache Aggressively
```python
# Cache embeddings
@cache(ttl=86400)
async def get_embedding(text: str):
    ...
```

### 3. Async All the Things
```python
# Use async/await for I/O
async def store_memory(...):
    await db.execute(...)
    await redis.set(...)
    await vector_store.upsert(...)
```

### 4. Monitor Everything
```python
# Add metrics
from prometheus_client import Counter

memories_stored = Counter(
    'memories_stored_total',
    'Total memories stored',
    ['layer', 'tenant']
)
```

## Performance Characteristics

### Latency (p95)
- Store memory: < 100ms
- Query memory (vector): < 50ms
- Query memory (hybrid): < 200ms
- Reflection generation: 2-5 seconds

### Throughput
- Store: 1000+ req/sec (single instance)
- Query: 500+ req/sec (single instance)
- Background tasks: 100+ memories/sec

### Storage
- PostgreSQL: ~1KB per memory
- Vector store: ~6KB per vector (1536 dims)
- Cache: ~500 bytes per cached item

## Further Reading

- [Memory Layers](memory-layers.md)
- [Reflection Engine](reflection-engine.md)
- [GraphRAG](graphrag.md)
- [API Reference](../api/rest-api.md)
- [Deployment Guide](../guides/production-deployment.md)
