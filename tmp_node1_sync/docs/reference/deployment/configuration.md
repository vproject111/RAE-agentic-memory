# Configuration Management

**Last Updated:** 2025-11-25
**RAE Version:** v2.0.0-enterprise
**Verified Against:** apps/memory_api/config.py

The RAE Agentic Memory system is configured primarily through environment variables. For local development, these can be conveniently placed in a `.env` file at the root of the project.

## Table of Contents

- [Loading Order](#loading-order)
- [Database Settings](#database-settings)
- [Vector Store Settings](#vector-store-settings)
- [Cache & Message Queue](#cache--message-queue)
- [LLM Backend Settings](#llm-backend-settings)
- [Security Settings](#security-settings)
- [Authentication & Authorization](#authentication--authorization)
- [Rate Limiting](#rate-limiting)
- [CORS Configuration](#cors-configuration)
- [Microservices](#microservices)
- [Memory Lifecycle Settings](#memory-lifecycle-settings)
- [Memory Decay & Importance Scoring](#memory-decay--importance-scoring)
- [Logging Configuration](#logging-configuration)
- [Advanced Settings](#advanced-settings)
- [Complete Example](#complete-example)

## Loading Order

The configuration is managed by the `pydantic-settings` library, which loads settings from the following sources in order of precedence:

1.  **Environment variables** (highest priority)
2.  **`.env` file** in project root
3.  **Default values** in code (lowest priority)

This means that an environment variable will always override a value in the `.env` file.

---

## Database Settings

RAE uses PostgreSQL for persistent storage of memories, graph data, and system state.

### Required Settings

-   **`POSTGRES_HOST`**: Hostname of the PostgreSQL database.
    - Default: `localhost`
    - Docker: Use service name (e.g., `postgres`)

-   **`POSTGRES_DB`**: Database name
    - Default: `memory`
    - Recommendation: Use descriptive name (e.g., `rae_production`)

-   **`POSTGRES_USER`**: Database username
    - Default: `memory`
    - **Security:** Use strong, unique username in production

-   **`POSTGRES_PASSWORD`**: Database password
    - Default: `example`
    - **Security:** Use strong, unique password in production. Consider secret management.

### Optional Settings

-   **`POSTGRES_PORT`**: Database port
    - Default: `5432`
    - Change only if using non-standard port

### Database Connection

RAE uses connection pooling via `asyncpg`. The connection string is constructed as:
```
postgresql://{user}:{password}@{host}/{database}
```

---

## Vector Store Settings

RAE supports multiple vector store backends for similarity search.

### Backend Selection

-   **`RAE_VECTOR_BACKEND`**: Vector store implementation
    - Options: `qdrant`, `pgvector`
    - Default: `qdrant`
    - **Legacy:** `VECTOR_STORE_BACKEND` still supported for backward compatibility

### Qdrant Configuration

When using `RAE_VECTOR_BACKEND=qdrant`:

-   **`QDRANT_HOST`**: Qdrant server hostname
    - Default: `localhost`
    - Docker: `qdrant`

-   **`QDRANT_PORT`**: Qdrant gRPC port
    - Default: `6333`

### PGVector Configuration

When using `RAE_VECTOR_BACKEND=pgvector`:

No additional configuration needed. Uses same PostgreSQL connection as primary database.

### Embedding Model

-   **`ONNX_EMBEDDER_PATH`**: Path to local ONNX embedding model (optional)
    - Default: `None` (uses SentenceTransformers)
    - Use for offline/air-gapped deployments

---

## Cache & Message Queue

RAE uses Redis for context caching and Celery for background tasks.

### Redis Configuration

-   **`REDIS_URL`**: Redis connection URL
    - Default: `redis://localhost:6379/0`
    - Format: `redis://[username:password@]host:port/db`
    - Docker: `redis://redis:6379/0`

**Legacy Settings (deprecated):**
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` - Use `REDIS_URL` instead

### Celery Configuration

-   **`CELERY_BROKER_URL`**: Message broker for Celery tasks
    - Default: `redis://localhost:6379/1`
    - Recommendation: Use separate Redis DB from cache

-   **`CELERY_RESULT_BACKEND`**: Result backend for Celery
    - Default: `redis://localhost:6379/2`
    - Recommendation: Use separate Redis DB from broker

---

## LLM Backend Settings

RAE supports multiple LLM providers with automatic failover and cost tracking.

### Provider Selection

-   **`RAE_LLM_BACKEND`**: LLM provider to use
    - Options: `openai`, `anthropic`, `gemini`, `ollama`
    - Default: `ollama` (for local development)

-   **`RAE_LLM_MODEL_DEFAULT`**: Default model for general operations
    - Default: `llama3` (when using Ollama)
    - Examples:
      - OpenAI: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`
      - Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
      - Gemini: `gemini-1.5-pro`, `gemini-1.5-flash`
      - Ollama: `llama3`, `mistral`, `mixtral`

### Specialized Models

-   **`EXTRACTION_MODEL`**: Model for knowledge graph extraction
    - Default: `gpt-4o-mini`
    - Recommendation: Use capable but cost-effective model

-   **`SYNTHESIS_MODEL`**: Model for context synthesis and reflections
    - Default: `gpt-4o`
    - Recommendation: Use most capable model for quality

-   **`LLM_MODEL`**: Override for all LLM operations (optional)
    - Default: `None` (uses specialized models)

### API Keys

-   **`OPENAI_API_KEY`**: OpenAI API key
    - Required when `RAE_LLM_BACKEND=openai`
    - Format: `sk-...`

-   **`ANTHROPIC_API_KEY`**: Anthropic API key
    - Required when `RAE_LLM_BACKEND=anthropic`
    - Format: `sk-ant-...`

-   **`GEMINI_API_KEY`**: Google Gemini API key
    - Required when `RAE_LLM_BACKEND=gemini`

-   **`OLLAMA_API_URL`**: Ollama server URL
    - Default: `http://localhost:11434`
    - Required when `RAE_LLM_BACKEND=ollama`

### Other Providers (Commented in code)

Additional providers can be added by defining API keys:
- `MISTRAL_API_KEY` - Mistral AI
- `DEEPSEEK_API_KEY` - DeepSeek
- `DASHSCOPE_API_KEY` - Alibaba Cloud (Qwen)

---

## Security Settings

### Multi-Tenancy

-   **`TENANCY_ENABLED`**: Enforce tenant isolation
    - Default: `True`
    - **Production:** Always `True`
    - When enabled, `X-Tenant-Id` header required on all requests
    - Enforced via PostgreSQL Row Level Security (RLS)

### OAuth2 / JWT Authentication

-   **`OAUTH_ENABLED`**: Enable OAuth2 JWT authentication
    - Default: `True`
    - **Production:** `True` recommended
    - When disabled, authentication is bypassed (dev/test only)

-   **`OAUTH_DOMAIN`**: OAuth2 provider domain
    - Example: `your-tenant.us.auth0.com`
    - Used to fetch JWKS public keys for token verification

-   **`OAUTH_AUDIENCE`**: JWT audience claim
    - Example: `https://api.yourcompany.com`
    - Must match JWT `aud` claim

---

## Authentication & Authorization

RAE supports multiple authentication methods for flexibility.

### API Key Authentication

-   **`ENABLE_API_KEY_AUTH`**: Enable API key authentication
    - Default: `False`
    - **Production:** Set to `True` for service-to-service auth
    - Clients send `X-API-Key` header

-   **`API_KEY`**: Shared API key for service authentication
    - Default: `secret`
    - **Security:** Change in production, use secret management

### JWT Authentication

-   **`ENABLE_JWT_AUTH`**: Enable JWT token authentication
    - Default: `False`
    - Set to `True` when using OAuth2/OIDC

-   **`SECRET_KEY`**: Secret key for JWT signing/verification
    - Default: `change-this-secret-key-in-production`
    - **Security:** Must be long, random, and kept secret
    - Recommendation: Generate with `openssl rand -hex 32`

**Authentication Priority:**
1. JWT token (if `ENABLE_JWT_AUTH=True` and `Authorization` header present)
2. API key (if `ENABLE_API_KEY_AUTH=True` and `X-API-Key` header present)
3. No auth (if both disabled - dev only)

---

## Rate Limiting

Protect your API from abuse with configurable rate limiting.

-   **`ENABLE_RATE_LIMITING`**: Enable rate limiting middleware
    - Default: `False`
    - **Production:** Set to `True`

-   **`RATE_LIMIT_REQUESTS`**: Maximum requests per window
    - Default: `100`
    - Recommendation: Adjust based on expected load

-   **`RATE_LIMIT_WINDOW`**: Time window in seconds
    - Default: `60` (1 minute)
    - Common values: `60` (1min), `300` (5min), `3600` (1hr)

**Example:** `RATE_LIMIT_REQUESTS=100` + `RATE_LIMIT_WINDOW=60` = 100 requests per minute per client

---

## CORS Configuration

Control which domains can access your API from browsers.

-   **`ALLOWED_ORIGINS`**: List of allowed CORS origins
    - Default: `["http://localhost:3000", "http://localhost:8501"]`
    - Format: List of full origin URLs
    - **Production:** Specify exact domains, avoid wildcards
    - Example: `["https://app.yourcompany.com", "https://admin.yourcompany.com"]`

---

## Microservices

RAE architecture includes specialized microservices.

### Reranker Service

-   **`RERANKER_API_URL`**: URL of reranker microservice
    - Default: `http://localhost:8001`
    - Docker: `http://reranker-service:8001`
    - Used for semantic reranking of search results
    - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (hardcoded)

### ML Service

-   ML Service configuration is internal (no env variables)
    - Default port: `8002`
    - Handles: Entity resolution, embeddings, NLP operations
    - Model: `all-MiniLM-L6-v2` for embeddings (default)

### Memory API Service

-   **`MEMORY_API_URL`**: URL of main Memory API
    - Default: `http://localhost:8000`
    - Used for inter-service communication

---

## Memory Lifecycle Settings

Control automatic memory retention and pruning.

-   **`MEMORY_RETENTION_DAYS`**: Days to keep episodic memories before automatic pruning
    - Default: `30`
    - Set to `0` or negative to disable pruning
    - Only affects `episodic` memories (layer `em`)
    - Semantic and reflective memories are not pruned

**Note:** This is separate from memory decay (importance scoring). Retention controls deletion, decay controls importance.

### Memory Decay & Importance Scoring

RAE implements an enterprise-grade memory decay system that automatically adjusts memory importance based on usage patterns and temporal factors.

-   **`MEMORY_DECAY_RATE`**: Base decay rate applied daily to memory importance scores. Value between 0.0 and 1.0. Default: `0.01` (1% per day).
    - Example: `0.005` = 0.5% per day (slow decay)
    - Example: `0.02` = 2% per day (fast decay)
    - Set to `0.0` to disable automatic decay

-   **`MEMORY_DECAY_ENABLED`**: Master switch for memory decay system. Default: `True`.
    - Set to `False` to completely disable decay calculations

-   **`MEMORY_DECAY_CONSIDER_ACCESS`**: Whether to use `last_accessed_at` and `usage_count` in decay calculations. Default: `True`.
    - When enabled, recently accessed memories decay slower
    - Stale memories (not accessed in 30+ days) decay faster
    - Provides intelligent, usage-based importance adjustment

#### How Memory Decay Works

The system tracks two critical metrics for each memory:

1. **`last_accessed_at`**: Timestamp of last retrieval (updated on every query/agent execution)
2. **`usage_count`**: Total number of times memory has been accessed

These metrics feed into the **ImportanceScoringService** which calculates dynamic importance scores:

**Decay Formula:**
```
if days_since_access > 30:
    effective_rate = decay_rate * (1 + days_since_access / 30)  # Accelerated decay
elif days_since_access < 7:
    effective_rate = decay_rate * 0.5  # Protected decay
else:
    effective_rate = decay_rate  # Normal decay

new_importance = old_importance * (1 - effective_rate)
new_importance = max(0.01, new_importance)  # Floor at 0.01
```

**Practical Impact:**
- **Recently used memories** (accessed within 7 days): Decay at 50% of base rate → stay important longer
- **Normal memories** (accessed 7-30 days ago): Decay at base rate
- **Stale memories** (not accessed in 30+ days): Decay accelerates → importance drops faster

#### Importance Score Factors

Memory importance is calculated using weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Recency | 15% | How recently the memory was created |
| Access Frequency | 20% | How often the memory is accessed (logarithmic) |
| Graph Centrality | 15% | Position in knowledge graph |
| Semantic Relevance | 15% | Similarity to recent queries |
| User Rating | 10% | Explicit user importance ratings |
| Consolidation | 10% | Whether memory is reflected/consolidated |
| Manual Boost | 15% | Manual importance adjustments |

**Note:** Weights can be customized by instantiating `ImportanceScoringService` with custom `ScoringFactors`.

#### Scheduled Decay Task

For production deployments, set up a daily cron job or Celery beat task:

```python
# Daily at 2 AM UTC
from apps.memory_api.services.importance_scoring import ImportanceScoringService

scoring_service = ImportanceScoringService(db=pool)
await scoring_service.decay_importance(
    tenant_id=tenant_uuid,
    decay_rate=0.01,  # From env: MEMORY_DECAY_RATE
    consider_access_stats=True
)
```

#### Configuration Examples

**Conservative (Slow Decay):**
```env
MEMORY_DECAY_RATE=0.005  # 0.5% per day
MEMORY_DECAY_ENABLED=True
MEMORY_DECAY_CONSIDER_ACCESS=True
```
Use when: Memories should remain important for longer periods.

**Aggressive (Fast Decay):**
```env
MEMORY_DECAY_RATE=0.02  # 2% per day
MEMORY_DECAY_ENABLED=True
MEMORY_DECAY_CONSIDER_ACCESS=True
```
Use when: System needs to quickly prioritize recent/relevant memories.

**Disabled:**
```env
MEMORY_DECAY_ENABLED=False
```
Use when: Manual importance management is preferred.

---

## Logging Configuration

Control logging verbosity for debugging and monitoring.

-   **`LOG_LEVEL`**: Log level for external libraries
    - Default: `WARNING`
    - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
    - Affects: uvicorn, asyncpg, httpx, and other dependencies
    - **Production:** Use `WARNING` or `ERROR` to reduce noise

-   **`RAE_APP_LOG_LEVEL`**: Log level for RAE application code
    - Default: `INFO`
    - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
    - Affects: All RAE-specific modules and services
    - **Development:** Use `DEBUG` for detailed debugging
    - **Production:** Use `INFO` for operational visibility

**Log Format:**

RAE uses `structlog` for structured JSON logging:
```json
{
  "event": "memory_stored",
  "tenant_id": "tenant-1",
  "memory_id": "uuid",
  "timestamp": "2025-11-23T10:00:00Z",
  "level": "info"
}
```

**Logging Best Practices:**
- Development: `RAE_APP_LOG_LEVEL=DEBUG` + `LOG_LEVEL=INFO`
- Staging: `RAE_APP_LOG_LEVEL=INFO` + `LOG_LEVEL=WARNING`
- Production: `RAE_APP_LOG_LEVEL=INFO` + `LOG_LEVEL=ERROR`

---

## Advanced Settings

### Backward Compatibility

-   **`VECTOR_STORE_BACKEND`** (deprecated): Legacy name for `RAE_VECTOR_BACKEND`
    - Still supported for backward compatibility
    - Recommendation: Migrate to `RAE_VECTOR_BACKEND`

### Environment Detection

RAE automatically detects environment based on settings:
- **Development:** When `OAUTH_ENABLED=False` or using default passwords
- **Production:** When authentication enabled and strong secrets configured

### Secret Management

**Production Recommendations:**

1. **Never commit secrets** to version control
2. **Use secret management systems:**
   - Kubernetes Secrets
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault
3. **Rotate secrets regularly:**
   - Database passwords: Quarterly
   - API keys: On compromise or quarterly
   - JWT secrets: Annually or on compromise
4. **Use environment-specific configs:**
   - `.env.development`
   - `.env.staging`
   - `.env.production`

---

## Complete Example

### Development Configuration

```env
# --- DATABASE ---
POSTGRES_HOST=localhost
POSTGRES_DB=rae_dev
POSTGRES_USER=rae_dev
POSTGRES_PASSWORD=dev_password

# --- VECTOR STORE ---
RAE_VECTOR_BACKEND=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# --- REDIS & CELERY ---
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# --- LLM ---
RAE_LLM_BACKEND=ollama
RAE_LLM_MODEL_DEFAULT=llama3
OLLAMA_API_URL=http://localhost:11434
EXTRACTION_MODEL=llama3
SYNTHESIS_MODEL=llama3

# --- SECURITY (DEV) ---
OAUTH_ENABLED=False
TENANCY_ENABLED=True
ENABLE_API_KEY_AUTH=False
ENABLE_JWT_AUTH=False
ENABLE_RATE_LIMITING=False

# --- CORS ---
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8501"]

# --- MICROSERVICES ---
RERANKER_API_URL=http://localhost:8001
MEMORY_API_URL=http://localhost:8000

# --- MEMORY LIFECYCLE ---
MEMORY_RETENTION_DAYS=30
MEMORY_DECAY_RATE=0.01
MEMORY_DECAY_ENABLED=True
MEMORY_DECAY_CONSIDER_ACCESS=True

# --- LOGGING ---
LOG_LEVEL=INFO
RAE_APP_LOG_LEVEL=DEBUG
```

### Production Configuration

```env
# --- DATABASE ---
POSTGRES_HOST=rae-db.internal
POSTGRES_DB=rae_production
POSTGRES_USER=rae_prod_user
POSTGRES_PASSWORD=${DB_PASSWORD_FROM_SECRET_MANAGER}

# --- VECTOR STORE ---
RAE_VECTOR_BACKEND=qdrant
QDRANT_HOST=qdrant.internal
QDRANT_PORT=6333

# --- REDIS & CELERY ---
REDIS_URL=redis://redis.internal:6379/0
CELERY_BROKER_URL=redis://redis.internal:6379/1
CELERY_RESULT_BACKEND=redis://redis.internal:6379/2

# --- LLM ---
RAE_LLM_BACKEND=openai
RAE_LLM_MODEL_DEFAULT=gpt-4o-mini
OPENAI_API_KEY=${OPENAI_KEY_FROM_SECRET_MANAGER}
EXTRACTION_MODEL=gpt-4o-mini
SYNTHESIS_MODEL=gpt-4o

# --- SECURITY (PRODUCTION) ---
OAUTH_ENABLED=True
OAUTH_DOMAIN=your-company.auth0.com
OAUTH_AUDIENCE=https://api.yourcompany.com
TENANCY_ENABLED=True
ENABLE_API_KEY_AUTH=True
API_KEY=${API_KEY_FROM_SECRET_MANAGER}
ENABLE_JWT_AUTH=True
SECRET_KEY=${JWT_SECRET_FROM_SECRET_MANAGER}
ENABLE_RATE_LIMITING=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# --- CORS ---
ALLOWED_ORIGINS=["https://app.yourcompany.com", "https://admin.yourcompany.com"]

# --- MICROSERVICES ---
RERANKER_API_URL=http://reranker-service:8001
MEMORY_API_URL=http://memory-api:8000

# --- MEMORY LIFECYCLE ---
MEMORY_RETENTION_DAYS=90
MEMORY_DECAY_RATE=0.01
MEMORY_DECAY_ENABLED=True
MEMORY_DECAY_CONSIDER_ACCESS=True

# --- LOGGING ---
LOG_LEVEL=ERROR
RAE_APP_LOG_LEVEL=INFO
```

### Docker Compose Configuration

```env
# --- DATABASE ---
POSTGRES_HOST=postgres
POSTGRES_DB=rae_db
POSTGRES_USER=rae_user
POSTGRES_PASSWORD=secure_password_here

# --- VECTOR STORE ---
RAE_VECTOR_BACKEND=qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# --- REDIS & CELERY ---
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# --- LLM ---
RAE_LLM_BACKEND=openai
RAE_LLM_MODEL_DEFAULT=gpt-4o-mini
OPENAI_API_KEY=sk-your-key-here
EXTRACTION_MODEL=gpt-4o-mini
SYNTHESIS_MODEL=gpt-4o

# --- SECURITY ---
OAUTH_ENABLED=True
OAUTH_DOMAIN=your-tenant.auth0.com
OAUTH_AUDIENCE=https://api.yourcompany.com
TENANCY_ENABLED=True
ENABLE_API_KEY_AUTH=True
API_KEY=your-secure-api-key
ENABLE_RATE_LIMITING=True

# --- CORS ---
ALLOWED_ORIGINS=["http://localhost:3000"]

# --- MICROSERVICES ---
RERANKER_API_URL=http://reranker-service:8001
MEMORY_API_URL=http://memory-api:8000

# --- MEMORY ---
MEMORY_RETENTION_DAYS=30
MEMORY_DECAY_RATE=0.01

# --- LOGGING ---
LOG_LEVEL=WARNING
RAE_APP_LOG_LEVEL=INFO
```

---

## Configuration Checklist

### Before Deploying to Production

- [ ] **Database**
  - [ ] Strong, unique password set
  - [ ] Connection pooling configured
  - [ ] Backup strategy in place

- [ ] **Security**
  - [ ] `OAUTH_ENABLED=True` or authentication configured
  - [ ] `TENANCY_ENABLED=True` for multi-tenant isolation
  - [ ] Strong `SECRET_KEY` generated and stored securely
  - [ ] `API_KEY` changed from default
  - [ ] CORS origins limited to production domains
  - [ ] Rate limiting enabled

- [ ] **LLM**
  - [ ] API keys stored in secret manager
  - [ ] Appropriate models selected for cost/quality
  - [ ] Fallback provider configured (optional)

- [ ] **Monitoring**
  - [ ] Logging levels appropriate (`INFO` for app, `ERROR` for libs)
  - [ ] Metrics endpoint exposed for Prometheus
  - [ ] Health checks configured in orchestrator

- [ ] **Memory Lifecycle**
  - [ ] Retention period set appropriately
  - [ ] Decay rate tuned for use case
  - [ ] Scheduled decay task configured (Celery beat or cron)

- [ ] **Infrastructure**
  - [ ] Redis persistent storage enabled
  - [ ] PostgreSQL with sufficient resources
  - [ ] Vector store with appropriate node sizing

---

## Troubleshooting

### Common Configuration Issues

**Issue:** "Connection refused" errors to database/Redis/Qdrant

**Solution:** Check hostnames in Docker/Kubernetes:
- Use service names, not `localhost`
- Example: `postgres` instead of `localhost` in Docker Compose

**Issue:** LLM provider errors or timeouts

**Solution:**
- Verify API keys are correct and active
- Check `RAE_LLM_BACKEND` matches provider
- Ensure model names are valid for provider

**Issue:** Authentication failures

**Solution:**
- Verify `OAUTH_DOMAIN` and `OAUTH_AUDIENCE` match JWT
- Check `SECRET_KEY` is same across all instances
- Ensure `ENABLE_JWT_AUTH` or `ENABLE_API_KEY_AUTH` is True

**Issue:** CORS errors in browser

**Solution:**
- Add frontend domain to `ALLOWED_ORIGINS`
- Use full origin URL with protocol: `https://app.example.com`
- Restart API after configuration change

---

## Example `.env` File (Quick Start)

For rapid local development:

```env
# --- DATABASE ---
POSTGRES_HOST=localhost
# ... (rest of DB settings)

# --- LLM ---
RAE_LLM_BACKEND=openai
RAE_LLM_MODEL_DEFAULT=gpt-4o-mini
OPENAI_API_KEY=your-openai-api-key

# --- SECURITY ---
OAUTH_ENABLED=True
OAUTH_DOMAIN=your-tenant.us.auth0.com
OAUTH_AUDIENCE=https://your-api-audience.com
TENANCY_ENABLED=True
ALLOWED_ORIGINS=http://localhost:3000

# --- MEMORY LIFECYCLE ---
MEMORY_RETENTION_DAYS=30
```

For complete examples, see sections above.

```env
# --- DATABASE ---
POSTGRES_HOST=postgres
# ... (rest of DB settings)

# --- LLM ---
RAE_LLM_BACKEND=openai
RAE_LLM_MODEL_DEFAULT=gpt-4o-mini
OPENAI_API_KEY=your-openai-api-key

# --- SECURITY ---
OAUTH_ENABLED=True
OAUTH_DOMAIN=your-tenant.us.auth0.com
OAUTH_AUDIENCE=https://your-api-audience.com
TENANCY_ENABLED=True
ALLOWED_ORIGINS=http://localhost:3000

# --- MEMORY LIFECYCLE ---
MEMORY_RETENTION_DAYS=30
```
