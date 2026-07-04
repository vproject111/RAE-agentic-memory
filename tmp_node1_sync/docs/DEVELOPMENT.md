# RAE Development Guide

## 🚀 Quick Start - Development Mode

RAE provides a development mode with **hot-reload** capabilities, allowing you to make code changes without rebuilding containers.

### Prerequisites

- Docker & Docker Compose installed
- `.env` file configured (copy from `.env.example`)
- Minimum 8GB RAM, 4 CPU cores recommended

### Start Development Environment

```bash
# Method 1: Using Makefile (recommended)
make -f Makefile.dev dev-up

# Method 2: Using docker compose directly
docker compose -f docker compose.yml -f docker compose.dev.yml up -d

# Method 3: Create an alias for convenience
alias dc-dev='docker compose -f docker compose.yml -f docker compose.dev.yml'
dc-dev up -d
```

### What Happens in Dev Mode?

1. **Hot Reload Enabled**
   - API changes: Auto-reload via `uvicorn --reload`
   - ML Service: Auto-reload via `uvicorn --reload`
   - Celery workers: Auto-restart via `watchdog`
   - Dashboard: Auto-reload via Streamlit

2. **Code Mounted from Host**
   - `./apps` → `/app/apps` (all application code)
   - `./sdk` → `/app/sdk` (Python SDK)
   - Changes appear instantly in containers

3. **Enhanced Logging**
   - `RAE_APP_LOG_LEVEL=DEBUG` for detailed logs
   - Disabled OpenTelemetry tracing for faster iteration

4. **Additional Dev Tools**
   - Adminer DB UI: http://localhost:8080
   - Direct database access on localhost:5432

## 📍 Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **RAE API** | http://localhost:8000 | Main Memory API |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **ML Service** | http://localhost:8001 | ML operations (embeddings, NLP) |
| **Dashboard** | http://localhost:8501 | Streamlit monitoring dashboard |
| **Jaeger UI** | http://localhost:16686 | Distributed tracing (if enabled) |
| **Adminer** | http://localhost:8080 | Database management UI |

## 🔌 Database Connections

### PostgreSQL
```bash
Host: localhost
Port: 5432
User: rae
Password: rae_password
Database: rae
```

### Redis
```bash
Host: localhost
Port: 6379
```

### Qdrant
```bash
HTTP: localhost:6333
gRPC: localhost:6334
UI: http://localhost:6333/dashboard
```

## 💻 Common Development Tasks

### View Logs

```bash
# All services
make -f Makefile.dev dev-logs

# Specific service
make -f Makefile.dev dev-logs-api
make -f Makefile.dev dev-logs-ml

# Or with docker compose
dc-dev logs -f rae-api
```

### Check Service Health

```bash
# Quick health check all services
make -f Makefile.dev dev-health

# Manual checks
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Access Container Shell

```bash
# API container
make -f Makefile.dev dev-shell-api

# ML service container
make -f Makefile.dev dev-shell-ml

# Database shell
make -f Makefile.dev dev-shell-db
```

### Run Tests

```bash
# All tests
make -f Makefile.dev dev-test

# Unit tests only
make -f Makefile.dev dev-test-unit

# Integration tests
make -f Makefile.dev dev-test-integration

# With coverage
make -f Makefile.dev dev-test-coverage
```

### Database Migrations

```bash
# Apply migrations
make -f Makefile.dev dev-migrate

# Create new migration
make -f Makefile.dev dev-migrate-create MSG="add new feature"

# Reset database (DESTRUCTIVE!)
make -f Makefile.dev dev-db-reset
```

### Restart Services

```bash
# Restart all services
make -f Makefile.dev dev-restart

# Restart specific service
dc-dev restart rae-api

# Rebuild and restart
make -f Makefile.dev dev-rebuild SERVICE=rae-api
```

### Stop Development Environment

```bash
# Stop all services (keeps volumes)
make -f Makefile.dev dev-down

# Stop and remove volumes
make -f Makefile.dev dev-clean-volumes

# Complete cleanup (DESTRUCTIVE!)
make -f Makefile.dev dev-clean
```

## 🔄 Hot Reload Behavior

### Python Services (FastAPI/Uvicorn)

**Files Watched:**
- `apps/**/*.py`
- `sdk/**/*.py`

**Reload Time:** ~2-5 seconds

**What Triggers Reload:**
- Editing `.py` files
- Creating new `.py` files
- Deleting `.py` files

**What Does NOT Trigger Reload:**
- Changes to `requirements.txt` (requires rebuild)
- Changes to environment variables (requires restart)
- Changes to Dockerfile (requires rebuild)

### Celery Workers

**Files Watched:**
- `apps/**/*.py`

**Reload Time:** ~5-10 seconds

**Behavior:**
- Uses `watchdog` to detect changes
- Gracefully restarts worker process
- Running tasks complete before restart

### Streamlit Dashboard

**Files Watched:**
- `tools/memory-dashboard/**/*.py`

**Reload Time:** Instant

**Behavior:**
- Automatic reload on file save
- Browser auto-refreshes

## 🛠️ Troubleshooting

### Services Won't Start

```bash
# Check service status
make -f Makefile.dev dev-ps

# Check logs for errors
make -f Makefile.dev dev-logs

# Verify ports are available
netstat -tuln | grep -E '5432|6379|6333|8000|8001|8501'
```

### Hot Reload Not Working

1. **Verify volume mounts:**
   ```bash
   dc-dev exec rae-api ls -la /app/apps
   ```

2. **Check file permissions:**
   ```bash
   # Ensure files are readable
   chmod -R 644 apps/**/*.py
   ```

3. **Restart specific service:**
   ```bash
   dc-dev restart rae-api
   ```

### Database Connection Errors

```bash
# Check PostgreSQL is running
dc-dev ps postgres

# Verify connection
dc-dev exec postgres pg_isready -U rae

# Check database exists
make -f Makefile.dev dev-shell-db
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process or change port in .env
kill -9 <PID>
```

### Slow Performance

1. **Reduce log verbosity:**
   ```bash
   # Edit .env
   RAE_APP_LOG_LEVEL=INFO  # instead of DEBUG
   ```

2. **Disable tracing:**
   ```bash
   OTEL_TRACES_ENABLED=false
   ```

3. **Allocate more resources to Docker:**
   - Docker Desktop → Settings → Resources
   - Increase RAM to 8GB+

## 📦 When to Rebuild Containers

You need to rebuild when you change:

- `requirements.txt` / `pyproject.toml`
- `Dockerfile`
- System dependencies (apt packages)
- Environment variables in `docker compose.yml`

```bash
# Rebuild all services
make -f Makefile.dev dev-up-build

# Rebuild specific service
make -f Makefile.dev dev-rebuild SERVICE=rae-api
```

## 🎯 Development Workflow

### Typical Day

```bash
# 1. Start environment
make -f Makefile.dev dev-up

# 2. Follow logs in another terminal
make -f Makefile.dev dev-logs-api

# 3. Make code changes in your editor
# 4. Watch auto-reload in logs
# 5. Test your changes
curl http://localhost:8000/api/v1/your-endpoint

# 6. Run tests
make -f Makefile.dev dev-test-unit

# 7. Commit when done
git add .
git commit -m "feat: add new feature"

# 8. Stop environment at end of day
make -f Makefile.dev dev-down
```

### Adding New Dependencies

```bash
# 1. Add to requirements.txt
echo "new-package==1.0.0" >> apps/memory_api/requirements.txt

# 2. Rebuild container
make -f Makefile.dev dev-rebuild SERVICE=rae-api

# 3. Verify installation
dc-dev exec rae-api pip list | grep new-package
```

### Creating New API Endpoint

```bash
# 1. Edit code (hot-reload enabled)
vim apps/memory_api/api/v1/my_endpoint.py

# 2. Watch logs for reload confirmation
make -f Makefile.dev dev-logs-api

# 3. Test endpoint
curl http://localhost:8000/api/v1/my-endpoint

# 4. Write tests
vim apps/memory_api/tests/test_my_endpoint.py

# 5. Run tests
make -f Makefile.dev dev-test
```

## 🔐 Security Notes for Development

1. **Default credentials are insecure** - OK for dev, change for production
2. **Ports exposed to localhost** - Not accessible externally
3. **Auth disabled by default** - Enable in .env for testing auth
4. **Debug logging enabled** - May log sensitive data

## 📚 Additional Resources

- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI
- [Architecture Guide](./architecture/README.md) - System design
- [Testing Guide](./TESTING.md) - Writing and running tests
- [Deployment Guide](./deployment/README.md) - Production deployment

## 🤝 Contributing

When developing new features:

1. ✅ Use dev mode for rapid iteration
2. ✅ Write tests alongside code
3. ✅ Run tests before committing
4. ✅ Check logs for errors/warnings
5. ✅ Document new endpoints/features
6. ✅ Update CHANGELOG.md

## 💡 Pro Tips

- **Use tmux/screen** to run logs in split terminal
- **Set up IDE to auto-save** for instant reload
- **Use `.env.local`** for personal settings (git-ignored)
- **Monitor resource usage** with `docker stats`
- **Use Adminer** for quick database inspection
- **Enable SQLAlchemy query logging** for debugging:
  ```python
  # In .env
  LOG_LEVEL=DEBUG
  ```

## 🆘 Need Help?

- Check logs first: `make -f Makefile.dev dev-logs`
- Verify health: `make -f Makefile.dev dev-health`
- Try restart: `make -f Makefile.dev dev-restart`
- Clean slate: `make -f Makefile.dev dev-clean` (removes all data!)
- Ask team in Slack #rae-dev channel
