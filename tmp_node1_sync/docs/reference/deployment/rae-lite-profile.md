# RAE Lite Profile

> Minimal single-server deployment for small teams and quick start

## Overview

RAE Lite Profile is a simplified deployment configuration designed for:

- **Small teams** (1-10 users) who don't need enterprise-scale features
- **Development and testing** environments
- **Quick evaluation** of RAE without heavy infrastructure
- **Resource-constrained environments** (limited CPU/RAM/GPU)
- **Single-server deployments** without Kubernetes complexity

## What's Included

RAE Lite includes only the **core components** needed for basic memory operations:

| Component | Port | Description |
|-----------|------|-------------|
| **RAE Core API** | 8000 | Main FastAPI service with memory engine |
| **PostgreSQL** | 5432 | Database with pgvector extension |
| **Qdrant** | 6333 | Vector database for semantic search |
| **Redis** | 6379 | Cache and rate limiting |

## What's Excluded

Compared to the full enterprise stack, RAE Lite **does not include**:

| Component | Reason | Impact |
|-----------|--------|--------|
| **ML Service** | Heavy ML dependencies (PyTorch, transformers) | Entity resolution done via API calls to LLM providers |
| **Reranker Service** | Optional re-ranking with CrossEncoder | Basic search without re-ranking |
| **Celery Worker/Beat** | Async background tasks | No scheduled reflections, manual trigger needed |
| **Dashboard** | Optional Streamlit UI | API-only access, no web UI |
| **Monitoring** | Prometheus + Grafana | No built-in metrics visualization |

## Requirements

### Minimum Hardware

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 10 GB (SSD recommended)
- **Network**: 10 Mbps

### Recommended Hardware

- **CPU**: 4 cores
- **RAM**: 8 GB
- **Disk**: 50 GB SSD
- **Network**: 100 Mbps

### Software

- Docker Engine 20.10+
- Docker Compose 2.0+
- LLM API key (OpenAI, Anthropic, or Google Gemini)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory
cd RAE-agentic-memory
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your LLM API key
nano .env
```

Required environment variables:
```bash
# At least one LLM provider API key is required
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
GEMINI_API_KEY=...

# Optional: Customize database credentials
POSTGRES_USER=rae
POSTGRES_PASSWORD=rae_password
POSTGRES_DB=rae
```

### 3. Start RAE Lite

```bash
# Start all services
docker compose -f docker compose.lite.yml up -d

# Check status
docker compose -f docker compose.lite.yml ps

# View logs
docker compose -f docker compose.lite.yml logs -f rae-api
```

### 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "version": "2.0.0-enterprise"}
```

### 5. Access API

- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Usage Examples

### Store Memory

```bash
curl -X POST http://localhost:8000/v1/memories/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -d '{
    "layer": "episodic",
    "content": "User prefers dark mode in applications",
    "tags": ["preference", "ui"]
  }'
```

### Query Memory

```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -d '{
    "query": "What are the user UI preferences?",
    "top_k": 5
  }'
```

### Hybrid Search (GraphRAG)

```bash
curl -X POST http://localhost:8000/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -d '{
    "query": "authentication system architecture",
    "use_graph": true,
    "graph_depth": 2,
    "top_k": 10
  }'
```

## Performance Tuning

### Resource Limits

RAE Lite includes optimized resource limits:

```yaml
# Redis: 256MB max memory with LRU eviction
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

# Qdrant: Reduced indexing thresholds
qdrant:
  environment:
    - QDRANT__STORAGE__OPTIMIZERS__INDEXING_THRESHOLD=10000
    - QDRANT__STORAGE__OPTIMIZERS__MEMMAP_THRESHOLD=50000

# API: Reduced worker count
rae-api:
  environment:
    - MAX_WORKERS=2
```

### Scaling Guidelines

RAE Lite is designed for **up to 10,000 memories** and **100 requests/minute**.

If you exceed these limits, consider:

1. **Add Celery workers** for async tasks:
   ```yaml
   celery-worker:
     build: .
     command: celery -A apps.memory_api.celery_app worker
     depends_on: [rae-api, redis]
   ```

2. **Upgrade to full stack** with ML Service and Reranker for better performance

3. **Migrate to Kubernetes** for horizontal scaling (see [Kubernetes Deployment Guide](kubernetes.md))

## Upgrading to Full Stack

When ready to add enterprise features:

### Option 1: Add Individual Services

Add ML Service for better entity resolution:
```bash
# Edit docker compose.lite.yml and add:
ml-service:
  build: ./apps/ml_service
  ports: ["8001:8001"]
  networks: [rae-lite-network]
```

### Option 2: Switch to Full Compose

```bash
# Stop lite version
docker compose -f docker compose.lite.yml down

# Start full stack
docker compose up -d
```

### Option 3: Kubernetes Deployment

For production with auto-scaling and monitoring:
```bash
helm install rae-memory ./helm/rae-memory \
  --namespace rae-memory \
  --create-namespace
```

See [Kubernetes Deployment Guide](kubernetes.md) for details.

## Troubleshooting

### Port Conflicts

If ports 8000, 5432, 6333, or 6379 are already in use:

```yaml
# Edit docker compose.lite.yml and change ports:
services:
  rae-api:
    ports:
      - "8080:8000"  # Changed from 8000:8000
```

### Memory Issues

If services crash due to OOM (Out of Memory):

```bash
# Increase Docker memory limit (Docker Desktop)
# Settings → Resources → Memory → 8 GB

# Or reduce service memory usage:
# Edit docker compose.lite.yml:
redis:
  command: redis-server --maxmemory 128mb
```

### Database Connection Errors

If API can't connect to PostgreSQL:

```bash
# Check database is healthy
docker compose -f docker compose.lite.yml ps postgres

# View database logs
docker compose -f docker compose.lite.yml logs postgres

# Restart database
docker compose -f docker compose.lite.yml restart postgres
```

### Vector Search Not Working

If Qdrant is not responding:

```bash
# Check Qdrant status
curl http://localhost:6333/health

# View Qdrant logs
docker compose -f docker compose.lite.yml logs qdrant

# Restart Qdrant
docker compose -f docker compose.lite.yml restart qdrant
```

## Cost Optimization

RAE Lite includes cost controls to minimize LLM API spending:

### Caching Strategy

- **Redis cache TTL**: 1 hour for embeddings
- **Hybrid search cache**: Reduces redundant queries
- **Embedding deduplication**: Reuses similar vectors

### Budget Limits

Set daily/monthly limits in `.env`:

```bash
# Enable cost tracking
ENABLE_COST_TRACKING=true

# Set budget limits
DEFAULT_DAILY_LIMIT=10.00
DEFAULT_MONTHLY_LIMIT=100.00

# Budget alerts at 80% and 95%
BUDGET_ALERT_THRESHOLDS=0.8,0.95
```

When budget is exceeded, API returns HTTP 402 (Payment Required).

See [Cost Controller Documentation](../concepts/cost-controller.md) for details.

## Monitoring

While RAE Lite doesn't include Prometheus/Grafana, you can monitor via:

### API Health Endpoint

```bash
curl http://localhost:8000/health

# Response includes:
# - API status
# - Database connectivity
# - Vector store status
# - Redis availability
```

### Docker Stats

```bash
# Real-time resource usage
docker stats rae-api-lite rae-postgres-lite rae-qdrant-lite rae-redis-lite
```

### Logs

```bash
# API logs
docker compose -f docker compose.lite.yml logs -f rae-api

# All services
docker compose -f docker compose.lite.yml logs -f
```

## Security Considerations

RAE Lite is **not hardened for production** by default:

### What's Missing

- ❌ No TLS/HTTPS (plain HTTP only)
- ❌ No authentication (open API)
- ❌ No network policies (all services exposed)
- ❌ No secret management (plaintext .env)
- ❌ No PII scrubbing by default

### Production Checklist

Before deploying RAE Lite to production:

1. **Add reverse proxy** with TLS (nginx, Caddy)
2. **Enable API authentication** (JWT tokens, API keys)
3. **Restrict network access** (firewall, VPN)
4. **Use secret management** (Vault, AWS Secrets Manager)
5. **Enable PII scrubbing** (configure PII detection in environment variables)
6. **Regular backups** of PostgreSQL and Qdrant data

For production deployments, we recommend **Kubernetes** with the official Helm chart.

## Comparison: Lite vs Full vs Enterprise

| Feature | Lite | Full (Docker Compose) | Enterprise (K8s) |
|---------|------|----------------------|------------------|
| **Deployment** | docker compose.lite.yml | docker compose.yml | Helm chart |
| **Services** | 4 (API, DB, Vector, Cache) | 9 (+ ML, Reranker, Celery, Dashboard, Monitoring) | 15+ (+ HPA, Ingress, NetworkPolicy) |
| **Resources** | 4 GB RAM, 2 CPU | 8 GB RAM, 4 CPU | Auto-scaling |
| **Max Memories** | 10,000 | 100,000 | Unlimited |
| **Max RPS** | 10 req/s | 100 req/s | 1000+ req/s |
| **Monitoring** | Manual (logs, health) | Prometheus + Grafana | Full observability |
| **TLS/Auth** | Manual setup | Manual setup | Built-in (cert-manager) |
| **Cost Tracking** | ✅ Basic | ✅ Full | ✅ Multi-tenant |
| **Auto-scaling** | ❌ No | ❌ No | ✅ HPA |
| **Best For** | Dev, Testing, Small Teams | Mid-size deployments | Production, Enterprise |

## Next Steps

1. **[Explore API endpoints](../api/rest-api.md)** - Learn all available operations
2. **[Install Python SDK](../../sdk/python/rae_memory_sdk/README.md)** - Use RAE from Python
3. **[Setup MCP integration](../integrations/mcp_protocol_server.md)** - Connect to IDE
4. **[Upgrade to full stack](../getting-started/)** - Add enterprise features
5. **[Deploy to Kubernetes](kubernetes.md)** - Production deployment

## Support

- 📖 **[Documentation](../)** - Comprehensive guides
- 🐛 **[GitHub Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)** - Bug reports
- 📧 **[Email Support](mailto:lesniowskig@gmail.com)** - Direct help

---

**RAE Lite** - Powerful memory engine, minimal complexity.
