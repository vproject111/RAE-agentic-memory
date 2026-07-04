# Kubernetes & Helm Deployment Guide

## Overview

Deploy RAE on Kubernetes using Helm charts for production-grade, scalable infrastructure.

**Location**: `helm/rae-memory/`, `charts/rae/`

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- PostgreSQL 14+ (external or in-cluster)
- Qdrant (external or in-cluster)
- Redis (optional, for caching)

## Quick Start

```bash
# Add Helm repository (if published)
helm repo add rae https://helm.rae.ai
helm repo update

# Install with default values
helm install rae-memory rae/rae-memory \
  --namespace rae \
  --create-namespace \
  --set postgresql.auth.password=changeme \
  --set api.env.OPENAI_API_KEY=sk-...

# Or install from local chart
helm install rae-memory ./helm/rae-memory \
  --namespace rae \
  --create-namespace \
  --values values-production.yaml
```

## Architecture

### Components

| Component | Purpose | Replicas |
|-----------|---------|----------|
| **rae-api** | FastAPI REST API | 3+ (auto-scaled) |
| **rae-worker** | Celery background workers | 2+ |
| **rae-beat** | Celery scheduler | 1 |
| **postgresql** | Primary database | 1 (or external) |
| **qdrant** | Vector database | 1+ |
| **redis** | Cache & Celery broker | 1 (or external) |

### Network Diagram

```
Internet → Ingress → rae-api (3 pods)
                      ↓
                   PostgreSQL
                   Qdrant
                   Redis
                      ↓
                   rae-worker (2 pods)
                      ↑
                   rae-beat (1 pod)
```

## Configuration

### values.yaml

Basic configuration:

```yaml
# Global settings
global:
  domain: rae.example.com
  storageClass: standard

# API deployment
api:
  replicaCount: 3
  image:
    repository: rae/memory-api
    tag: "1.0.0"
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "2000m"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

  env:
    RAE_ENV: production
    POSTGRES_HOST: rae-postgresql
    QDRANT_URL: http://rae-qdrant:6333
    REDIS_URL: redis://rae-redis:6379
    OPENAI_API_KEY: ${OPENAI_API_KEY}  # From secret

# Worker deployment
worker:
  replicaCount: 2
  image:
    repository: rae/memory-api
    tag: "1.0.0"
  resources:
    requests:
      memory: "1Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

# PostgreSQL (using bitnami chart)
postgresql:
  enabled: true
  auth:
    username: rae
    password: changeme
    database: rae
  primary:
    persistence:
      size: 100Gi
    resources:
      requests:
        memory: "2Gi"
        cpu: "1000m"

# Qdrant
qdrant:
  enabled: true
  persistence:
    size: 50Gi
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"

# Redis
redis:
  enabled: true
  master:
    persistence:
      size: 10Gi

# Ingress
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: rae.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: rae-tls
      hosts:
        - rae.example.com
```

### Environment-Specific Values

#### values-lite.yaml

For Lite profile (cost-optimized):

```yaml
api:
  replicaCount: 2
  resources:
    requests:
      memory: "256Mi"
      cpu: "250m"

worker:
  replicaCount: 1
  env:
    REFLECTIVE_MEMORY_MODE: lite
    DREAMING_ENABLED: "false"

postgresql:
  primary:
    persistence:
      size: 20Gi

qdrant:
  persistence:
    size: 10Gi
```

#### values-enterprise.yaml

For Enterprise deployment:

```yaml
api:
  replicaCount: 5
  autoscaling:
    minReplicas: 5
    maxReplicas: 20
  resources:
    requests:
      memory: "2Gi"
      cpu: "2000m"
    limits:
      memory: "8Gi"
      cpu: "4000m"

worker:
  replicaCount: 5
  env:
    REFLECTIVE_MEMORY_MODE: full
    DREAMING_ENABLED: "true"

postgresql:
  primary:
    persistence:
      size: 500Gi
    resources:
      requests:
        memory: "8Gi"
        cpu: "4000m"

  # Enable read replicas
  readReplicas:
    replicaCount: 2

# Monitoring
monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: true
```

## Secrets Management

### Using Kubernetes Secrets

```bash
# Create secrets
kubectl create secret generic rae-secrets \
  --namespace rae \
  --from-literal=POSTGRES_PASSWORD=changeme \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...

# Reference in values.yaml
api:
  envFrom:
    - secretRef:
        name: rae-secrets
```

### Using External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: rae-secrets
  namespace: rae
spec:
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: rae-secrets
  data:
    - secretKey: OPENAI_API_KEY
      remoteRef:
        key: prod/rae/openai-key
```

## Database Setup

### Option 1: In-Cluster PostgreSQL

```yaml
postgresql:
  enabled: true
  auth:
    username: rae
    password: ${POSTGRES_PASSWORD}
    database: rae
  primary:
    persistence:
      storageClass: gp3
      size: 100Gi
```

### Option 2: External Managed Database

```yaml
postgresql:
  enabled: false  # Don't deploy in-cluster DB

api:
  env:
    POSTGRES_HOST: rae-db.abc123.us-east-1.rds.amazonaws.com
    POSTGRES_PORT: "5432"
    POSTGRES_DB: rae
    POSTGRES_USER: rae
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # From secret
```

### Database Migrations

Run migrations as init container or job:

```yaml
api:
  initContainers:
    - name: run-migrations
      image: rae/memory-api:1.0.0
      command: ["alembic", "upgrade", "head"]
      envFrom:
        - secretRef:
            name: rae-secrets
```

## Storage

### Persistent Volumes

```yaml
# Storage class for different performance tiers
storageClasses:
  - name: rae-fast
    provisioner: kubernetes.io/aws-ebs
    parameters:
      type: gp3
      iops: "3000"
      throughput: "125"

  - name: rae-standard
    provisioner: kubernetes.io/aws-ebs
    parameters:
      type: gp3
```

### PVC Configuration

```yaml
postgresql:
  primary:
    persistence:
      storageClass: rae-fast
      size: 100Gi
      accessModes:
        - ReadWriteOnce

qdrant:
  persistence:
    storageClass: rae-fast
    size: 50Gi
```

## Networking

### Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: rae.example.com
      paths:
        - path: /api/v1
          pathType: Prefix
          backend:
            service:
              name: rae-api
              port: 8000
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rae-api-netpol
spec:
  podSelector:
    matchLabels:
      app: rae-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgresql
    - to:
        - podSelector:
            matchLabels:
              app: qdrant
```

## Monitoring

### Prometheus Integration

```yaml
monitoring:
  serviceMonitor:
    enabled: true
    interval: 30s
    path: /metrics

  prometheusRule:
    enabled: true
    rules:
      - alert: RAEHighErrorRate
        expr: rate(rae_api_errors_total[5m]) > 0.05
        annotations:
          summary: "High error rate in RAE API"
```

### Grafana Dashboards

Pre-built dashboards included in chart:
- API performance
- Memory statistics
- Cost tracking
- Worker queue status

## Scaling

### Horizontal Pod Autoscaler

```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Vertical Pod Autoscaler

```yaml
vpa:
  enabled: true
  updateMode: "Auto"
```

## Backup and Restore

### Database Backup

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention: 30  # Keep 30 backups
  s3:
    bucket: rae-backups
    region: us-east-1
```

### Disaster Recovery

```bash
# Create backup
kubectl exec -n rae rae-postgresql-0 -- \
  pg_dump -U rae rae > backup.sql

# Restore from backup
kubectl exec -i -n rae rae-postgresql-0 -- \
  psql -U rae rae < backup.sql
```

## High Availability

### Multi-Region Deployment

```yaml
# Deploy in multiple regions with shared database
regions:
  - name: us-east-1
    api:
      replicaCount: 3
  - name: eu-west-1
    api:
      replicaCount: 3

# Cross-region database replication
postgresql:
  replication:
    enabled: true
    readReplicas:
      - region: eu-west-1
        replicaCount: 1
```

## Troubleshooting

### View Logs

```bash
# API logs
kubectl logs -n rae -l app=rae-api -f

# Worker logs
kubectl logs -n rae -l app=rae-worker -f

# Database logs
kubectl logs -n rae rae-postgresql-0
```

### Debug Pod

```bash
# Shell into API pod
kubectl exec -it -n rae $(kubectl get pod -n rae -l app=rae-api -o name | head -1) -- /bin/bash

# Test database connection
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- psql -h rae-postgresql -U rae
```

## Related Documentation

- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant configuration
- [Background Workers](./BACKGROUND_WORKERS.md) - Worker deployment
- [Monitoring](./MONITORING.md) - Observability setup
