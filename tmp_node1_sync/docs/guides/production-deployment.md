# Production Deployment Guide

This guide covers deploying RAE to production environments with best practices for security, performance, and reliability.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Security Configuration](#security-configuration)
- [Infrastructure Options](#infrastructure-options)
- [Docker Compose Production](#docker compose-production)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Monitoring & Observability](#monitoring--observability)
- [Backup & Recovery](#backup--recovery)
- [Performance Tuning](#performance-tuning)

## Prerequisites

Before deploying to production:

- [ ] Environment variables configured
- [ ] API keys secured in vault/secrets manager
- [ ] Database backup strategy in place
- [ ] Monitoring and alerting configured
- [ ] SSL/TLS certificates obtained
- [ ] Domain/DNS configured
- [ ] Resource requirements estimated

### Minimum Resource Requirements

**Small Deployment (< 1000 users)**
- CPU: 2 cores
- RAM: 4 GB
- Storage: 50 GB SSD
- Database: PostgreSQL with 2 GB RAM
- Redis: 512 MB RAM

**Medium Deployment (1000-10000 users)**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 200 GB SSD
- Database: PostgreSQL with 4 GB RAM
- Redis: 1 GB RAM

**Large Deployment (> 10000 users)**
- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 500+ GB SSD
- Database: PostgreSQL cluster with 8+ GB RAM per node
- Redis: 2+ GB RAM (consider Redis Cluster)

## Security Configuration

### 1. Enable Authentication

Update `.env`:

```env
# Authentication
ENABLE_API_KEY_AUTH=true
API_KEY=your-secure-api-key-here  # Use strong random key
ENABLE_JWT_AUTH=false  # Set to true if using JWT

# JWT Settings (if enabled)
SECRET_KEY=your-jwt-secret-key  # Generate with: openssl rand -hex 32
```

Generate secure API key:
```bash
# Generate a secure random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Enable Rate Limiting

```env
# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100    # Adjust based on your needs
RATE_LIMIT_WINDOW=60       # seconds
```

### 3. Configure CORS

```env
# CORS - restrict to your domains only
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### 4. Database Security

```env
# Use strong passwords
POSTGRES_PASSWORD=your-strong-database-password

# Enable SSL for database connections
DATABASE_URL=postgresql://user:password@host:5432/db?sslmode=require
```

### 5. Secrets Management

**Never commit secrets to git!**

Use environment-specific `.env` files:
- `.env.production` - Production secrets
- `.env.staging` - Staging secrets
- `.env.development` - Development (non-sensitive)

Or use cloud secrets managers:
- AWS Secrets Manager
- Google Cloud Secret Manager
- Azure Key Vault
- HashiCorp Vault

Example with AWS Secrets Manager:
```bash
# Retrieve secrets at runtime
export DATABASE_URL=$(aws secretsmanager get-secret-value --secret-id rae/database-url --query SecretString --output text)
export API_KEY=$(aws secretsmanager get-secret-value --secret-id rae/api-key --query SecretString --output text)
```

## Infrastructure Options

### Option 1: Docker Compose (Simple)

Best for:
- Small to medium deployments
- Single server
- Quick setup

### Option 2: Kubernetes (Scalable)

Best for:
- Large deployments
- High availability required
- Auto-scaling needs
- Multi-region

### Option 3: Managed Services (Easiest)

Best for:
- No DevOps team
- Focus on application
- Cloud-native

## Docker Compose Production

### 1. Production docker compose.yml

Create `docker compose.prod.yml`:

```yaml
version: '3.8'

services:
  rae-api:
    image: your-registry.com/rae-api:latest
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENABLE_API_KEY_AUTH=true
      - API_KEY=${API_KEY}
      - ENABLE_RATE_LIMITING=true
    depends_on:
      - postgres
      - redis
      - qdrant
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  postgres:
    image: ankane/pgvector:latest
    restart: always
    environment:
      POSTGRES_DB: rae
      POSTGRES_USER: rae
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "127.0.0.1:5432:5432"  # Only bind to localhost
    command: >
      postgres
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c work_mem=10MB
      -c min_wal_size=1GB
      -c max_wal_size=4GB
      -c max_worker_processes=4
      -c max_parallel_workers_per_gather=2
      -c max_parallel_workers=4

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"

  qdrant:
    image: qdrant/qdrant:latest
    restart: always
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "127.0.0.1:6333:6333"
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334

  # Nginx reverse proxy with SSL
  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_cache:/var/cache/nginx
    depends_on:
      - rae-api

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  qdrant_data:
    driver: local
  nginx_cache:
    driver: local
```

### 2. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream rae_api {
        server rae-api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name yourdomain.com;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security Headers
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Proxy settings
        location / {
            proxy_pass http://rae_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Rate limiting
            limit_req zone=api_limit burst=20 nodelay;

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint (no rate limit)
        location /health {
            proxy_pass http://rae_api;
            access_log off;
        }
    }
}
```

### 3. Deploy

```bash
# Build image
docker build -t your-registry.com/rae-api:latest .

# Push to registry
docker push your-registry.com/rae-api:latest

# Deploy
docker compose -f docker compose.prod.yml up -d

# Check health
curl https://yourdomain.com/health

# View logs
docker compose -f docker compose.prod.yml logs -f rae-api
```

## Kubernetes Deployment

### 1. Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rae-memory
```

### 2. Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: rae-secrets
  namespace: rae-memory
type: Opaque
stringData:
  database-url: postgresql://user:password@postgres:5432/rae
  redis-url: redis://redis:6379/0
  api-key: your-secure-api-key
  openai-api-key: sk-...
```

Apply with:
```bash
# Encode secrets in base64 first!
kubectl apply -f k8s/secrets.yaml
```

### 3. Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rae-api
  namespace: rae-memory
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rae-api
  template:
    metadata:
      labels:
        app: rae-api
    spec:
      containers:
      - name: rae-api
        image: your-registry.com/rae-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: rae-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: rae-secrets
              key: redis-url
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: rae-secrets
              key: api-key
        - name: ENABLE_API_KEY_AUTH
          value: "true"
        - name: ENABLE_RATE_LIMITING
          value: "true"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 4. Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: rae-api
  namespace: rae-memory
spec:
  selector:
    app: rae-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 5. Deploy

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check status
kubectl get pods -n rae-memory

# Get service URL
kubectl get svc -n rae-memory

# View logs
kubectl logs -f deployment/rae-api -n rae-memory
```

## Cloud Platforms

### AWS ECS

Use AWS Fargate for serverless containers:

```bash
# Create task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-def.json

# Create service
aws ecs create-service \
  --cluster rae-cluster \
  --service-name rae-api \
  --task-definition rae-api:1 \
  --desired-count 3 \
  --launch-type FARGATE
```

### Google Cloud Run

Simplest cloud deployment:

```bash
# Build and deploy in one command
gcloud run deploy rae-api \
  --image gcr.io/your-project/rae-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL
```

### Azure Container Apps

```bash
# Create container app
az containerapp create \
  --name rae-api \
  --resource-group rae-rg \
  --environment rae-env \
  --image your-registry.azurecr.io/rae-api:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10
```

## Monitoring & Observability

### Health Checks

RAE provides comprehensive health endpoints:

```bash
# Overall health
curl https://yourdomain.com/health

# Readiness (for load balancers)
curl https://yourdomain.com/health/ready

# Liveness (for orchestrators)
curl https://yourdomain.com/health/live

# Metrics
curl https://yourdomain.com/metrics
```

### Prometheus Metrics

RAE exposes Prometheus-compatible metrics at `/metrics`:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'rae-api'
    static_configs:
      - targets: ['rae-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

Key metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `memory_store_operations_total` - Memory operations
- `database_connection_pool_size` - DB pool status

### Logging

Configure structured logging:

```env
# .env
LOG_LEVEL=INFO  # ERROR, WARNING, INFO, DEBUG
LOG_FORMAT=json  # or text
```

### Application Performance Monitoring (APM)

Integrate with APM tools:

**Datadog:**
```python
# Add to main.py
from dd trace import patch_all
patch_all()
```

**New Relic:**
```bash
pip install newrelic
newrelic-admin run-program uvicorn apps.memory_api.main:app
```

## Backup & Recovery

### Database Backups

**Automated daily backups:**

```bash
# backup.sh
#!/bin/bash
BACKUP_DIR=/backups
DATE=$(date +%Y-%m-%d_%H-%M-%S)

docker compose exec -T postgres pg_dump -U rae rae | gzip > $BACKUP_DIR/rae_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "rae_*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

### Restore from Backup

```bash
# Stop services
docker compose down

# Restore database
gunzip < backup.sql.gz | docker compose exec -T postgres psql -U rae rae

# Restart services
docker compose up -d
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_memories_tenant_timestamp ON memories(tenant_id, timestamp DESC);
CREATE INDEX idx_memories_tenant_layer ON memories(tenant_id, layer);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);

-- Vector index
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Analyze tables
ANALYZE memories;
```

### Redis Configuration

```env
# redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Application Tuning

```env
# .env
# Database pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Celery workers
CELERY_WORKERS=4
CELERY_CONCURRENCY=2

# Cache TTL
CACHE_TTL_SECONDS=3600
```

## Troubleshooting

### High Memory Usage

```bash
# Check memory usage
docker stats

# Restart services
docker compose restart rae-api

# Clear Redis cache
docker compose exec redis redis-cli FLUSHALL
```

### Slow Queries

```sql
-- Enable slow query log
ALTER DATABASE rae SET log_min_duration_statement = 1000;

-- View slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

### Connection Errors

```bash
# Check service health
docker compose ps

# Check logs
docker compose logs rae-api

# Test database connection
docker compose exec postgres psql -U rae -d rae -c "SELECT 1;"
```

## Security Checklist

Before going to production:

- [ ] Strong passwords for all services
- [ ] API key authentication enabled
- [ ] Rate limiting configured
- [ ] CORS properly restricted
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Database backups automated
- [ ] Secrets stored securely (not in .env files)
- [ ] Monitoring and alerting set up
- [ ] Security updates automated
- [ ] DDoS protection enabled (e.g., Cloudflare)
- [ ] Audit logging enabled

---

**Related Guides:**
- [Security Best Practices](security-best-practices.md)
- [Performance Tuning](performance-tuning.md)
- [Monitoring & Observability](../observability.md)
