# Infrastructure Setup

This directory contains **advanced infrastructure configurations** for RAE, including monitoring and development setups.

## For Standard Deployment

**Most users should use the root `docker compose.yml`:**

```bash
# From project root
docker compose up -d
# or
make start
```

See the [Quick Start Guide](../docs/getting-started/quickstart.md) for details.

## Advanced Setups

### Full Infrastructure with Monitoring

This setup includes Prometheus and Grafana for monitoring:

```bash
cd infra
docker compose up -d
```

**Services:**
- PostgreSQL with pgvector
- Qdrant vector database
- Redis cache
- RAE Memory API
- Celery worker (async tasks)
- Reranker service
- **Prometheus** (metrics collection) - http://localhost:9090
- **Grafana** (dashboards) - http://localhost:3000
- **Redis Exporter** (Redis metrics)

**Grafana Access:**
- URL: http://localhost:3000
- Default credentials: admin/admin

### Development Mode

For development with hot-reload:

```bash
cd infra
docker compose -f docker compose.yml -f docker compose.dev.yml up
```

**Development features:**
- Auto-reload on code changes
- Volume mounts for live editing
- Disabled health checks for faster startup
- Debug logging enabled

## Configuration

Create a `.env` file in this directory:

```bash
cp .env.example .env
```

**Required variables:**
- `OPENAI_API_KEY` - OpenAI API key (or other LLM provider)
- `POSTGRES_HOST` - Database host (default: postgres)
- `QDRANT_HOST` - Vector store host (default: qdrant)
- `REDIS_URL` - Redis connection string

## Monitoring

### Prometheus

Access metrics at http://localhost:9090

**Key metrics:**
- `rae_memory_operations_total` - Memory operation counts
- `rae_query_duration_seconds` - Query latency
- `rae_embedding_cache_hit_ratio` - Cache efficiency
- Redis metrics via redis-exporter

### Grafana

Pre-configured dashboards are available in `grafana/rae-dashboard.json`:
- Memory operations overview
- Query performance
- Cache efficiency
- System resources

## Directory Structure

```
infra/
├── docker compose.yml       # Full setup with monitoring
├── docker compose.dev.yml   # Development overrides
├── postgres/
│   └── ddl/                 # Database initialization scripts
├── qdrant/                  # Qdrant configuration
├── prometheus/
│   └── prometheus.yml       # Prometheus configuration
└── grafana/
    ├── provisioning/        # Auto-provisioned datasources
    └── rae-dashboard.json   # RAE monitoring dashboard
```

## Differences from Root Setup

| Feature | Root `docker compose.yml` | `infra/docker compose.yml` |
|---------|---------------------------|----------------------------|
| Target | Production-like deployment | Development + Monitoring |
| Monitoring | ❌ | ✅ Prometheus + Grafana |
| Reranker | ❌ | ✅ Included |
| Dev mode | ❌ | ✅ Via dev overlay |
| Complexity | Simple | Advanced |

## Troubleshooting

### Port Conflicts

If ports 8000, 3000, 9090, or 6333 are in use:

```bash
# Check what's using ports
sudo lsof -i :8000
sudo lsof -i :3000
sudo lsof -i :9090

# Stop conflicting services or modify ports in docker compose.yml
```

### Database Issues

```bash
# Reset database
docker compose down -v
docker compose up -d postgres
# Wait for init
docker compose up -d
```

### Monitoring Not Working

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify services are exposing metrics
curl http://localhost:8000/metrics
```

## Need Help?

- 📖 [Full Documentation](../docs/)
- 🐛 [Report Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)
