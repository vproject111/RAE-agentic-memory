# RAE Standard Profile

**For teams that need full RAE capabilities with reasonable resource requirements.**

## Overview

RAE Standard is the recommended profile for most production deployments. It provides:
- Full 4-layer memory architecture
- GraphRAG with community detection
- Reflection Engine V2 (Actor-Evaluator-Reflector)
- Background workers (Decay, Summarization, Dreaming)
- Cost Guard with budgets
- Multi-tenant support
- Standard security features

**Target Audience**: Small to medium teams, startups, standard production deployments

## Key Features

### ✅ Included in Standard

| Feature | Status | Description |
|---------|--------|-------------|
| **4-Layer Memory** | ✅ Full | Sensory, Episodic, Long-Term, Reflective |
| **GraphRAG** | ✅ Full | Knowledge graph with community detection |
| **Reflection Engine V2** | ✅ Full | Learning from successes and failures |
| **Background Workers** | ✅ Full | Decay, Summarization, Dreaming |
| **Hybrid Search** | ✅ Full | Semantic + keyword search |
| **Cost Guard** | ✅ Full | Budget management and alerts |
| **Multi-Tenancy** | ✅ Basic | Tenant isolation with RLS |
| **LLM Profiles** | ✅ Full | Multiple providers, fallback chains |
| **SDK & CLI** | ✅ Full | Python SDK, CLI tools |
| **MCP Integration** | ✅ Full | IDE integration via MCP |
| **Monitoring** | ✅ Basic | Prometheus metrics, structured logs |

### ❌ Not Included (Enterprise Only)

- Advanced compliance (ISO 42001 full implementation)
- High availability (multi-region, auto-failover)
- Advanced RBAC (fine-grained permissions)
- SLA guarantees
- Priority support
- Advanced security (SIEM integration, advanced audit)
- Custom integrations
- Dedicated resources

## Requirements

### Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 4 cores | 8 cores |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 50 GB | 100 GB |
| **PostgreSQL** | 13+ | 14+ |
| **Qdrant** | Latest | Latest |
| **Redis** | 6+ | 7+ |

### Software Requirements

- Docker 20.10+ or Kubernetes 1.24+
- Python 3.10+ (for SDK)
- PostgreSQL 13+
- Qdrant (vector database)
- Redis (caching and task queue)

## Quick Start

### Docker Compose (Recommended for Start)

```bash
# Clone repository
git clone https://github.com/your-org/rae-agentic-memory.git
cd rae-agentic-memory

# Copy standard profile configuration
cp .env.standard.example .env

# Configure essential variables
cat > .env << EOF
# Database
POSTGRES_HOST=postgres
POSTGRES_DB=rae
POSTGRES_USER=rae
POSTGRES_PASSWORD=your-secure-password

# Vector DB
QDRANT_URL=http://qdrant:6333

# Redis
REDIS_URL=redis://redis:6379

# LLM Provider (choose one or more)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Profile
REFLECTIVE_MEMORY_MODE=full
DREAMING_ENABLED=true
SUMMARIZATION_ENABLED=true

# Cost Guard
COST_GUARD_ENABLED=true
COST_GUARD_MONTHLY_BUDGET_USD=500
EOF

# Start services
docker-compose -f docker-compose.standard.yml up -d

# Run migrations
docker-compose exec api alembic upgrade head

# Verify deployment
curl http://localhost:8000/health
```

### Kubernetes/Helm

```bash
# Add Helm repository
helm repo add rae https://helm.rae.ai
helm repo update

# Install with Standard profile
helm install rae-memory rae/rae-memory \
  --namespace rae \
  --create-namespace \
  --values values-standard.yaml \
  --set postgresql.auth.password=your-secure-password \
  --set api.env.OPENAI_API_KEY=sk-...

# Verify deployment
kubectl get pods -n rae
kubectl logs -n rae -l app=rae-api
```

## Configuration

### Profile Settings

```yaml
# config/standard-profile.yaml
profile: standard

# Memory Configuration
reflective_memory:
  enabled: true
  mode: full  # full capabilities

# Background Workers
workers:
  decay:
    enabled: true
    schedule: "0 2 * * *"  # Daily at 2 AM
  summarization:
    enabled: true
    min_events: 10
  dreaming:
    enabled: true
    lookback_hours: 24
    min_importance: 0.6

# Cost Guard
cost_guard:
  enabled: true
  monthly_budget_usd: 500
  alert_thresholds: [0.8, 0.9, 0.95]
  action_on_exceed: block

# LLM Configuration
llm:
  default_provider: openai
  default_model: gpt-4o
  fallback_chain:
    - gpt-4o
    - gpt-4o-mini
    - ollama/llama3  # Local fallback
  enable_caching: true

# Multi-Tenancy
tenancy:
  enabled: true
  isolation: rls  # Row-Level Security

# Monitoring
monitoring:
  prometheus: true
  structured_logs: true
  log_level: INFO
```

### Environment Variables

```bash
# Core
RAE_PROFILE=standard
RAE_ENV=production

# Memory
REFLECTIVE_MEMORY_ENABLED=true
REFLECTIVE_MEMORY_MODE=full
DREAMING_ENABLED=true
SUMMARIZATION_ENABLED=true

# Performance
API_WORKERS=4
WORKER_CONCURRENCY=2
MAX_CONNECTIONS=100

# Security
API_KEY_REQUIRED=true
ENABLE_CORS=true
CORS_ORIGINS=https://your-app.com

# Observability
LOG_LEVEL=INFO
METRICS_ENABLED=true
TRACING_ENABLED=false  # Enterprise only
```

## Usage Examples

### 1. Basic Memory Operations

```python
from rae_memory_sdk import MemoryClient

client = MemoryClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="your-tenant-id"
)

# Store memory
memory_id = client.store_memory(
    content="Team decided to use PostgreSQL for main database",
    source="team_meeting",
    importance=0.8,
    layer="ltm",
    tags=["decision", "database"]
)

# Query with GraphRAG
results = client.query_graph(
    query="What database technologies are we using?",
    k=5,
    max_depth=2
)
```

### 2. Reflection Generation

```python
# Generate reflection from execution
reflection = client.generate_reflection(
    events=[
        {"event_type": "tool_call", "content": "Database query executed"},
        {"event_type": "error", "content": "Timeout after 30s"}
    ],
    outcome="failure",
    task_description="Fetch customer data"
)

# Query reflections for learning
reflections = client.query_reflections(
    query="database timeout issues",
    k=5,
    min_importance=0.7
)
```

### 3. Cost Monitoring

```python
# Check cost usage
usage = client.get_cost_usage(month="2025-12")

print(f"Budget: ${usage['budget_usd']}")
print(f"Used: ${usage['total_cost_usd']}")
print(f"Remaining: ${usage['budget_remaining_usd']}")
```

## Deployment Architectures

### Single Server (Small Teams)

```
┌─────────────────────────────────┐
│      Single Server (16GB RAM)   │
├─────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐    │
│  │ RAE API  │  │  Worker  │    │
│  │  (4GB)   │  │  (2GB)   │    │
│  └──────────┘  └──────────┘    │
│  ┌──────────┐  ┌──────────┐    │
│  │Postgres  │  │  Qdrant  │    │
│  │  (4GB)   │  │  (4GB)   │    │
│  └──────────┘  └──────────┘    │
│  ┌──────────┐                  │
│  │  Redis   │                  │
│  │  (2GB)   │                  │
│  └──────────┘                  │
└─────────────────────────────────┘
```

### Kubernetes (Medium Teams)

```
┌─────────────────────────────────────────┐
│          Kubernetes Cluster             │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────┐     │
│  │    RAE API (3 pods, HPA)      │     │
│  │    CPU: 2 cores, RAM: 4GB     │     │
│  └───────────────────────────────┘     │
│  ┌───────────────────────────────┐     │
│  │    Workers (2 pods)           │     │
│  │    CPU: 2 cores, RAM: 4GB     │     │
│  └───────────────────────────────┘     │
│  ┌───────────────────────────────┐     │
│  │    PostgreSQL (StatefulSet)   │     │
│  │    Storage: 100GB             │     │
│  └───────────────────────────────┘     │
│  ┌───────────────────────────────┐     │
│  │    Qdrant (StatefulSet)       │     │
│  │    Storage: 50GB              │     │
│  └───────────────────────────────┘     │
│  ┌───────────────────────────────┐     │
│  │    Redis (StatefulSet)        │     │
│  │    Storage: 10GB              │     │
│  └───────────────────────────────┘     │
└─────────────────────────────────────────┘
```

## Monitoring

### Prometheus Metrics

Key metrics to monitor:

```promql
# API Performance
rate(rae_api_requests_total[5m])
histogram_quantile(0.95, rate(rae_api_latency_seconds_bucket[5m]))

# Memory Operations
rate(rae_memories_stored_total[5m])
rate(rae_memories_queried_total[5m])

# Cost Tracking
rae_llm_cost_usd_total
rae_llm_budget_percent

# Background Workers
rae_decay_cycle_duration_seconds
rae_dreaming_reflections_generated_total
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/health/db

# Vector store
curl http://localhost:8000/health/qdrant
```

## Scaling Guidelines

### When to Scale Up

Scale from Standard to Enterprise when:
- **Users**: >100 concurrent users
- **Memory**: >1M memories stored
- **Tenants**: >50 tenants
- **Compliance**: Need ISO 42001, SOC 2
- **Availability**: Need 99.9% uptime SLA
- **Support**: Need priority support

### Horizontal Scaling (within Standard)

```yaml
# Scale API pods
kubectl scale deployment rae-api --replicas=5

# Scale workers
kubectl scale deployment rae-worker --replicas=3

# Add read replicas (PostgreSQL)
postgresql:
  readReplicas:
    replicaCount: 2
```

## Best Practices

### 1. Resource Allocation

- **API**: 2 cores, 4GB RAM per pod (scale horizontally)
- **Workers**: 2 cores, 4GB RAM (dedicated for background tasks)
- **PostgreSQL**: 4 cores, 8GB RAM minimum
- **Qdrant**: 2 cores, 4GB RAM minimum

### 2. Cost Optimization

```python
# Use cheaper models for non-critical operations
client.config.set_profile("cost-optimized", {
    "default_model": "gpt-4o-mini",
    "enable_caching": True,
    "max_tokens": 1000
})

# Monitor and set budgets
client.set_budget(monthly_limit_usd=500)
```

### 3. Backup Strategy

```bash
# Daily PostgreSQL backups
0 3 * * * pg_dump -U rae rae | gzip > /backups/rae-$(date +\%Y\%m\%d).sql.gz

# Weekly Qdrant snapshots
0 4 * * 0 curl -X POST http://qdrant:6333/collections/memories/snapshots
```

### 4. Security

```yaml
# Enable API authentication
api:
  auth:
    required: true
    methods: [api_key, jwt]

# Row-level security
database:
  rls_enabled: true

# Network policies
network:
  ingress:
    enabled: true
    tls: true
```

## Troubleshooting

### Common Issues

#### High Memory Usage

```bash
# Check memory consumption
docker stats

# Optimize PostgreSQL
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 64MB
```

#### Slow Queries

```bash
# Enable query logging
log_min_duration_statement = 1000  # Log queries >1s

# Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

#### Budget Exceeded

```python
# Check cost breakdown
usage = client.get_cost_usage()
for profile, cost in usage['breakdown_by_profile'].items():
    print(f"{profile}: ${cost}")

# Adjust budgets or models
client.update_llm_profile(
    profile_id="default",
    model="gpt-4o-mini"  # Cheaper model
)
```

## Migration Paths

### From Lite to Standard

```bash
# 1. Update configuration
export REFLECTIVE_MEMORY_MODE=full
export DREAMING_ENABLED=true

# 2. Deploy workers
docker compose up -d worker

# 3. Migrate data (if needed)
python scripts/migrate_lite_to_standard.py
```

### From Standard to Enterprise

See [RAE Enterprise Guide](../rae-enterprise/README.md) for migration steps.

## Support

### Community Support

- **GitHub Issues**: https://github.com/your-org/rae/issues
- **Discussions**: https://github.com/your-org/rae/discussions
- **Discord**: https://discord.gg/rae

### Documentation

- [API Reference](../../reference/api/SDK_PYTHON_REFERENCE.md)
- [Deployment Guide](../../reference/deployment/DEPLOY_K8S_HELM.md)
- [Monitoring](../../reference/deployment/observability.md)

## Pricing

RAE Standard is **open source** and **free to use**. Operational costs:
- **Cloud Infrastructure**: ~$200-500/month (depending on usage)
- **LLM API Costs**: Variable (controlled by Cost Guard)
- **Support**: Community support (free)

## Next Steps

1. **Deploy**: Follow the [Quick Start](#quick-start)
2. **Configure**: Customize [Configuration](#configuration)
3. **Monitor**: Set up [Monitoring](#monitoring)
4. **Scale**: Review [Scaling Guidelines](#scaling-guidelines)
5. **Optimize**: Apply [Best Practices](#best-practices)

## Related Guides

- [RAE Lite](../rae-lite/RAE-lite.md) - Cost-optimized deployment
- [RAE Enterprise](../rae-enterprise/README.md) - Full enterprise features
- [Getting Started](../developers/getting_started.md) - Developer guide
