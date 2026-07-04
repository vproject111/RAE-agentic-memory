# RAE Sandbox Environments

RAE supports running isolated sandbox environments alongside the main development setup. This allows testing different profiles (Lite vs Standard) and running integration tests without impacting your work.

## 1. RAE-Lite Sandbox
**Profile:** `lite` (No ML Service, no Celery, lightweight)
**Purpose:** Integration tests, quick verification, low-resource usage.

| Service | Port |
|---------|------|
| API     | 8010 |
| Postgres| 5440 |
| Qdrant  | 6340 |
| Redis   | 6390 |

**Start:**
```bash
docker compose -f docker-compose.test-sandbox.yml up -d
```

**Stop:**
```bash
docker compose -f docker-compose.test-sandbox.yml down -v
```

## 2. RAE-Full Sandbox
**Profile:** `standard` (Full stack: API + ML Service + Celery + Redis + Postgres + Qdrant)
**Purpose:** Testing full enterprise features, async tasks, ML pipelines in isolation.

| Service | Port |
|---------|------|
| API     | 8020 |
| ML Service| 8021 |
| Postgres| 5450 |
| Qdrant  | 6350 |
| Redis   | 6380 |

**Start:**
```bash
docker compose -f docker-compose.sandbox-full.yml -p rae-sandbox-full up -d
```

**Stop:**
```bash
docker compose -f docker-compose.sandbox-full.yml -p rae-sandbox-full down -v
```

## 3. Main Development Environment (Default)
**Profile:** `standard` (with Hot Reload)

| Service | Port |
|---------|------|
| API     | 8000 |
| Dashboard| 8501 |
| Postgres| 5432 |
| Qdrant  | 6333 |
| Redis   | 6379 |

**Start:**
```bash
make dev-full
# OR
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---
**Note:** All environments use isolated networks and volumes. You can run them simultaneously.
