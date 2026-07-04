# 🔧 RAE Troubleshooting Guide

This guide covers common issues and their solutions when deploying RAE with Docker.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Database Issues](#database-issues)
- [Container Health Issues](#container-health-issues)
- [Disk Space Issues](#disk-space-issues)
- [Network and Connection Issues](#network-and-connection-issues)
- [Performance Issues](#performance-issues)

---

## Installation Issues

### Missing Dependencies Error

**Symptoms:**
```
ModuleNotFoundError: No module named 'slowapi'
ModuleNotFoundError: No module named 'instructor'
ModuleNotFoundError: No module named 'scipy'
```

**Solution:**
These dependencies are now included in `requirements-base.txt`. If you cloned before this fix:

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker compose build --no-cache rae-api celery-worker celery-beat
docker compose up -d
```

### Prometheus Instrumentation Error

**Symptoms:**
```
RuntimeError: Cannot add middleware after an application has started
```

**Solution:**
This is fixed in the latest version. The Prometheus instrumentation has been moved outside the lifespan handler. Update your code:

```bash
git pull origin main
docker compose build rae-api
docker compose up -d rae-api
```

---

## Database Issues

### Table "memories" Does Not Exist

**Symptoms:**
```
asyncpg.exceptions.UndefinedTableError: relation "memories" does not exist
```

**Solution:**
The database schema needs to be initialized. Run the DDL scripts:

```bash
# Execute all DDL files
for file in infra/postgres/ddl/*.sql; do
  docker exec -i rae-postgres psql -U rae -d rae < "$file"
done

# Execute migrations
for file in infra/postgres/migrations/*.sql; do
  docker exec -i rae-postgres psql -U rae -d rae < "$file"
done

# Restart API
docker compose restart rae-api
```

### Column "project" Does Not Exist

**Symptoms:**
```
asyncpg.exceptions.UndefinedColumnError: column "project" does not exist
```

**Solution:**
Add the missing column:

```bash
docker exec -i rae-postgres psql -U rae -d rae -c "ALTER TABLE memories ADD COLUMN IF NOT EXISTS project VARCHAR(255);"
docker compose restart rae-api
```

### Database Connection Refused

**Symptoms:**
```
Error 111 connecting to localhost:6379. Connection refused
OSError: Multiple exceptions: [Errno 111] Connect call failed ('127.0.0.1', 5432)
```

**Solution:**
This happens when services try to connect to `localhost` instead of Docker service names. The issue is fixed in `docker compose.yml` by using proper environment variables:

```bash
git pull origin main
docker compose down
docker compose up -d
```

---

## Container Health Issues

### Containers Restarting in a Loop

**Symptoms:**
```bash
$ docker compose ps
rae-api          Restarting
rae-celery-worker Restarting
```

**Solution:**

1. Check logs to identify the issue:
```bash
docker logs rae-api --tail 50
docker logs rae-celery-worker --tail 50
```

2. Common causes:
   - Missing database tables → [See Database Issues](#database-issues)
   - Missing dependencies → [See Missing Dependencies](#missing-dependencies-error)
   - Wrong environment variables → Check docker compose.yml

3. If all else fails, clean restart:
```bash
docker compose down
docker compose up -d
```

### Celery Shows "Unhealthy"

**Note:** Celery workers don't have health checks defined in docker compose.yml, so showing "unhealthy" is expected. What matters is:

```bash
# Check if celery is actually working
docker logs rae-celery-worker --tail 10

# You should see:
# [INFO/MainProcess] Connected to redis://redis:6379/1
# [INFO/MainProcess] celery@xxx ready.
```

If you see "Connected" and "ready", Celery is working correctly despite the health status.

---

## Disk Space Issues

### "No Space Left on Device" Error

**Symptoms:**
```
ENOSPC: no space left on device, write
ERROR: failed to build: failed to compute cache key
```

**Solution:**

1. Check current disk usage:
```bash
df -h /
docker system df
```

2. Clean Docker resources:
```bash
# Remove unused images (saves 15-20GB typically)
docker image prune -af

# Remove unused build cache (saves 10-30GB typically)
docker builder prune -af

# Remove unused volumes (be careful with data!)
docker volume prune -f

# Or clean everything at once
docker system prune -af --volumes
```

3. Verify space recovered:
```bash
df -h /
```

**Prevention:**
- Monitor disk space before large operations: `df -h /`
- Regularly clean unused Docker resources (weekly/monthly)
- Keep at least 20GB free for builds

---

## Network and Connection Issues

### Cannot Connect to Services

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Solution:**

1. Check if containers are running:
```bash
docker compose ps
```

2. Check if services are listening on correct ports:
```bash
docker compose ps | grep "Up"
```

3. Test health endpoints:
```bash
curl http://localhost:8000/health  # API
curl http://localhost:8001/health  # ML Service
curl http://localhost:8501/_stcore/health  # Dashboard
```

4. If services are up but not responding, check logs:
```bash
docker logs rae-api --tail 50
```

### Services Can't Find Each Other

**Symptoms:**
```
Could not resolve host: postgres
Connection refused to redis:6379
```

**Solution:**
All services must be on the same Docker network. Verify:

```bash
docker network ls
docker network inspect rae-agentic-memory_rae-network
```

If network is missing:
```bash
docker compose down
docker compose up -d
```

---

## Performance Issues

### Slow Build Times

**Issue:** Docker builds taking 10+ minutes.

**Solutions:**

1. Use build cache effectively:
```bash
# Don't use --no-cache unless necessary
docker compose build
```

2. For faster rebuilds after code changes:
```bash
# Only rebuild changed services
docker compose build rae-api
docker compose up -d rae-api
```

3. Parallel builds:
```bash
docker compose build --parallel
```

### High Memory Usage

**Issue:** System running out of memory.

**Solutions:**

1. Use RAE Lite profile for limited resources:
```bash
docker compose -f docker compose.lite.yml up -d
```

2. Reduce Celery workers:
Edit `docker compose.yml`:
```yaml
command: celery -A apps.memory_api.celery_app worker --loglevel=info --concurrency=1
```

3. Monitor memory usage:
```bash
docker stats
```

---

## Quick Diagnostic Commands

### Check Everything at Once

```bash
# System resources
df -h /
free -h

# Docker status
docker compose ps
docker system df

# Service health
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8001/health | jq

# Recent logs
docker compose logs --tail=20 --timestamps

# Database connectivity
docker exec -i rae-postgres psql -U rae -d rae -c "SELECT COUNT(*) FROM memories;"
```

### Get Service URLs

```bash
echo "API Docs: http://localhost:8000/docs"
echo "API Health: http://localhost:8000/health"
echo "Dashboard: http://localhost:8501"
echo "ML Service: http://localhost:8001/docs"
echo "Qdrant: http://localhost:6333/dashboard"
```

---

## Getting Help

If you're still experiencing issues:

1. **Check logs for all services:**
   ```bash
   docker compose logs > rae-logs.txt
   ```

2. **Gather system information:**
   ```bash
   docker version
   docker compose version
   df -h
   free -h
   ```

3. **Create an issue:** [GitHub Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)
   - Include logs and system information
   - Describe steps to reproduce
   - Mention your deployment profile (Lite/Standard/Enterprise)

---

## Additional Resources

- [Main README](README.md) - Installation and overview
- [STATUS.md](STATUS.md) - Implementation status
- [Docker Compose Configuration](docker compose.yml)
- [Database Schema](infra/postgres/ddl/)
