# Kubernetes Deployment Guide

Enterprise-grade Kubernetes deployment for RAE Memory Engine with cost control, security, and monitoring.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Deployment Steps](#deployment-steps)
- [Cost Control](#cost-control)
- [Security](#security)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Production Checklist](#production-checklist)

## Prerequisites

### Cluster Requirements

- **Kubernetes**: 1.23+ (tested on 1.27+)
- **Helm**: 3.8+
- **Cluster Size**: Minimum 3 nodes (for production)
- **Node Resources**:
  - Memory: 16GB+ per node
  - CPU: 4 cores+ per node
  - Storage: 200GB+ available

### Required Components

Install these before deploying RAE:

```bash
# 1. Ingress Controller (NGINX)
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer

# 2. cert-manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# 3. Prometheus Operator (for monitoring)
helm install prometheus-operator prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# 4. External Secrets Operator (optional, for production)
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace
```

### Storage Classes

Ensure you have a default StorageClass:

```bash
# Check available storage classes
kubectl get storageclass

# Set default if needed
kubectl patch storageclass <your-storage-class> \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

## Quick Start

Deploy RAE in under 5 minutes:

```bash
# 1. Clone repository
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory
cd RAE-agentic-memory

# 2. Create namespace
kubectl create namespace rae-memory

# 3. Create secrets (replace with your actual keys)
kubectl create secret generic rae-secrets \
  --from-literal=database-url='postgresql://rae:changeme@rae-memory-postgresql:5432/rae_memory' \
  --from-literal=redis-url='redis://:changeme@rae-memory-redis-master:6379/0' \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=anthropic-api-key='sk-ant-...' \
  --from-literal=gemini-api-key='...' \
  --from-literal=jwt-secret='your-jwt-secret-here' \
  --from-literal=api-master-key='your-master-key-here' \
  -n rae-memory

# 4. Install Helm chart
helm install rae-memory ./helm/rae-memory \
  --namespace rae-memory \
  --set ingress.hosts[0].host=rae-api.yourdomain.com

# 5. Wait for deployment
kubectl wait --for=condition=available --timeout=600s \
  deployment/rae-memory-api -n rae-memory

# 6. Verify installation
kubectl get pods -n rae-memory
curl http://rae-api.yourdomain.com/health
```

## Architecture

### Kubernetes Resources

RAE deploys the following resources:

```
┌─────────────────────────────────────────────────────────────┐
│                     Ingress (NGINX)                         │
│              rae-api.example.com → :8000                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Memory API Service                         │
│        ClusterIP: rae-memory-api:8000                       │
│        Pods: 2-10 (HPA enabled)                             │
└───┬───────────────────┬───────────────────────┬─────────────┘
    │                   │                       │
    ▼                   ▼                       ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│ ML Service   │  │ Reranker     │  │ Celery Workers       │
│ :8001        │  │ :8002        │  │ (Background Tasks)   │
│ Pods: 1-5    │  │ Pods: 1      │  │ Pods: 2-10           │
└──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘
       │                 │                      │
       └─────────────────┴──────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│   PostgreSQL     │            │   Redis Master   │
│   + pgvector     │            │   (Cache)        │
│   PVC: 20Gi      │            │   PVC: 8Gi       │
└──────────────────┘            └──────────────────┘
        │
        ▼
┌──────────────────┐
│   Qdrant         │
│   Vector DB      │
│   PVC: 50Gi      │
└──────────────────┘
```

### Key Components

| Component | Purpose | Scaling | Ports |
|-----------|---------|---------|-------|
| Memory API | Main REST API | HPA (2-10) | 8000 |
| ML Service | Entity resolution, embeddings | HPA (1-5) | 8001 |
| Reranker | Search result re-ranking | Static (1) | 8002 |
| Celery Workers | Background tasks (reflections) | HPA (2-10) | - |
| PostgreSQL | Primary database + pgvector | StatefulSet (1) | 5432 |
| Redis | Cache + Celery broker | StatefulSet (1) | 6379 |
| Qdrant | Vector search engine | StatefulSet (1) | 6333 |

## Deployment Steps

### Step 1: Prepare Configuration

Create a custom `values.yaml`:

```yaml
# custom-values.yaml
memoryApi:
  replicaCount: 3
  image:
    repository: your-registry/rae-memory-api
    tag: "2.0.0"

  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20

mlService:
  replicaCount: 2
  image:
    repository: your-registry/rae-ml-service
    tag: "2.0.0"

# Cost Control
configMap:
  ENABLE_COST_TRACKING: "true"
  DEFAULT_DAILY_LIMIT: "50.00"
  DEFAULT_MONTHLY_LIMIT: "1000.00"
  BUDGET_WARNING_THRESHOLD: "0.8"

# Security
networkPolicy:
  enabled: true

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000

# Monitoring
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true

# Ingress
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "1000"
  hosts:
    - host: rae-api.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: rae-tls
      hosts:
        - rae-api.yourdomain.com
```

### Step 2: Secrets Management

**Option A: Kubernetes Secrets (Development)**

```bash
kubectl create secret generic rae-secrets \
  --from-literal=database-url='postgresql://rae:SECURE_PASSWORD@rae-memory-postgresql:5432/rae_memory' \
  --from-literal=redis-url='redis://:SECURE_PASSWORD@rae-memory-redis-master:6379/0' \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=anthropic-api-key='sk-ant-...' \
  --from-literal=gemini-api-key='...' \
  --from-literal=jwt-secret='$(openssl rand -base64 32)' \
  --from-literal=api-master-key='$(openssl rand -base64 32)' \
  -n rae-memory
```

**Option B: External Secrets Operator (Production)**

```yaml
# values.yaml
externalSecrets:
  enabled: true
  secretStore: "aws-secrets-manager"
  refreshInterval: "1h"
  keys:
    databaseUrl: "rae/prod/database-url"
    redisUrl: "rae/prod/redis-url"
    openaiApiKey: "rae/prod/openai-api-key"
    anthropicApiKey: "rae/prod/anthropic-api-key"
    jwtSecret: "rae/prod/jwt-secret"
    apiMasterKey: "rae/prod/api-master-key"
```

Store secrets in AWS:

```bash
# Database URL
aws secretsmanager create-secret \
  --name rae/prod/database-url \
  --secret-string "postgresql://rae:SECURE@host:5432/rae"

# API Keys
aws secretsmanager create-secret \
  --name rae/prod/openai-api-key \
  --secret-string "sk-..."

aws secretsmanager create-secret \
  --name rae/prod/anthropic-api-key \
  --secret-string "sk-ant-..."
```

### Step 3: Deploy with Helm

```bash
# Install
helm install rae-memory ./helm/rae-memory \
  --namespace rae-memory \
  --values custom-values.yaml \
  --wait \
  --timeout 10m

# Verify deployment
kubectl get all -n rae-memory

# Check pods
kubectl get pods -n rae-memory -o wide

# Check services
kubectl get svc -n rae-memory

# Check ingress
kubectl get ingress -n rae-memory
```

### Step 4: Initialize Database

The database is automatically initialized with schema migrations. Verify:

```bash
# Check PostgreSQL pod
kubectl exec -it rae-memory-postgresql-0 -n rae-memory -- \
  psql -U rae -d rae_memory -c "\dt"

# Expected tables:
# - memories
# - graph_nodes
# - graph_edges
# - semantic_memories
# - budgets
# - cost_logs
# - etc.
```

### Step 5: Verify Deployment

```bash
# Health check
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://rae-memory-api:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "2.0.0",
#   "components": {
#     "database": "healthy",
#     "redis": "healthy",
#     "qdrant": "healthy",
#     "ml_service": "healthy"
#   }
# }

# Test API endpoint
kubectl port-forward svc/rae-memory-api 8000:8000 -n rae-memory

# In another terminal:
curl http://localhost:8000/docs
```

## Cost Control

RAE includes sophisticated cost tracking and budget management.

### Enable Cost Tracking

```yaml
# values.yaml
configMap:
  ENABLE_COST_TRACKING: "true"
  DEFAULT_DAILY_LIMIT: "10.00"     # $10 per day
  DEFAULT_MONTHLY_LIMIT: "100.00"  # $100 per month
  BUDGET_WARNING_THRESHOLD: "0.8"  # Warn at 80%
```

### Set Per-Tenant Budgets

```bash
# Set budget via API
curl -X PUT http://rae-api.yourdomain.com/v1/budgets \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: acme-corp" \
  -H "X-Project-ID: project-alpha" \
  -d '{
    "monthly_limit": 500.00,
    "daily_limit": 20.00
  }'
```

### Monitor Costs

```bash
# Check current usage
curl http://rae-api.yourdomain.com/v1/budgets/current \
  -H "X-Tenant-ID: acme-corp" \
  -H "X-Project-ID: project-alpha"

# Response:
# {
#   "monthly_limit": 500.00,
#   "monthly_usage": 123.45,
#   "monthly_remaining": 376.55,
#   "daily_limit": 20.00,
#   "daily_usage": 3.21,
#   "usage_percentage": 24.7
# }
```

### Cost Alerts

Set up alerts using Prometheus:

```yaml
# prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: rae-budget-alerts
  namespace: rae-memory
spec:
  groups:
  - name: rae-budget
    interval: 5m
    rules:
    - alert: RAEBudgetWarning
      expr: rae_budget_remaining{period="monthly"} / rae_budget_limit{period="monthly"} < 0.2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "RAE budget 80% consumed"
        description: "Tenant {{ $labels.tenant_id }} has used 80% of monthly budget"

    - alert: RAEBudgetCritical
      expr: rae_budget_remaining{period="monthly"} / rae_budget_limit{period="monthly"} < 0.05
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "RAE budget 95% consumed"
        description: "Tenant {{ $labels.tenant_id }} has used 95% of monthly budget"
```

See [Cost Controller Documentation](../concepts/cost-controller.md) for details.

## Security

### Network Policies

RAE enforces strict network isolation:

```bash
# Verify NetworkPolicies
kubectl get networkpolicy -n rae-memory

# Expected policies:
# - rae-memory-api (restricts API ingress/egress)
# - rae-memory-ml-service (restricts ML service traffic)
```

**Traffic Flow:**
- API accepts traffic from: ingress-nginx, same-namespace pods
- API can connect to: PostgreSQL, Redis, Qdrant, ML Service, internet (443)
- ML Service accepts traffic from: API, Celery Worker only
- Databases accept traffic from: API, ML Service, Celery only

### Pod Security

All pods run with restricted security context:

```yaml
# Enforced by chart
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
```

### TLS Certificates

Automatic TLS with cert-manager:

```yaml
# ClusterIssuer for Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

Apply and configure ingress:

```bash
kubectl apply -f cluster-issuer.yaml

# Cert-manager will automatically provision certificates
# based on ingress annotations
```

### RBAC

Minimal RBAC permissions:

```bash
# View service account
kubectl get serviceaccount -n rae-memory

# View role bindings
kubectl get rolebinding -n rae-memory
```

### Secrets Rotation

With External Secrets Operator:

```yaml
# values.yaml
externalSecrets:
  enabled: true
  refreshInterval: "1h"  # Sync every hour
```

Secrets automatically rotate when updated in AWS/GCP/Vault.

## Scaling

### Horizontal Pod Autoscaling

RAE includes HPA for all services:

```bash
# Check HPA status
kubectl get hpa -n rae-memory

# Expected HPAs:
# - rae-memory-api (2-10 pods)
# - rae-memory-ml-service (1-5 pods)
# - rae-memory-celery-worker (2-10 pods)
```

### Custom HPA Configuration

```yaml
# values.yaml
memoryApi:
  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 50
    targetCPUUtilizationPercentage: 60
    targetMemoryUtilizationPercentage: 70

celeryWorker:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    behavior:
      scaleUp:
        stabilizationWindowSeconds: 0
        policies:
        - type: Percent
          value: 200  # Scale up aggressively
          periodSeconds: 30
      scaleDown:
        stabilizationWindowSeconds: 600  # Wait 10 min before scale down
```

### Database Scaling

PostgreSQL is deployed as StatefulSet (single instance by default).

**For high availability:**

```yaml
# Use external managed database
externalSecrets:
  enabled: true
  keys:
    databaseUrl: "rae/prod/rds-url"  # AWS RDS

# Disable built-in PostgreSQL
postgresql:
  enabled: false
```

Recommended managed database options:
- AWS RDS PostgreSQL with pgvector
- Google Cloud SQL for PostgreSQL
- Azure Database for PostgreSQL

### Storage Scaling

Expand PVCs:

```bash
# Increase PostgreSQL storage
kubectl patch pvc data-rae-memory-postgresql-0 -n rae-memory \
  -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'

# Increase Qdrant storage
kubectl patch pvc qdrant-storage-rae-memory-qdrant-0 -n rae-memory \
  -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
```

## Monitoring

### Prometheus Metrics

RAE exposes comprehensive metrics:

```bash
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090

# Open http://localhost:9090
# Query examples:
# - rate(rae_api_requests_total[5m])
# - rae_memory_operations_total
# - rae_llm_cost_total
# - rae_budget_remaining
```

### Grafana Dashboards

```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Login: admin / prom-operator
# Import dashboard from helm/rae-memory/dashboards/
```

### Logging

View logs:

```bash
# API logs
kubectl logs -f deployment/rae-memory-api -n rae-memory

# ML Service logs
kubectl logs -f deployment/rae-memory-ml-service -n rae-memory

# Celery Worker logs
kubectl logs -f deployment/rae-memory-celery-worker -n rae-memory

# Stream logs from all pods
kubectl logs -f -l app.kubernetes.io/instance=rae-memory -n rae-memory
```

Centralized logging with Loki:

```bash
# Install Loki
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --set promtail.enabled=true

# Logs automatically collected from all pods
```

## Troubleshooting

### Common Issues

**1. Pods stuck in Pending**

```bash
# Check events
kubectl describe pod <pod-name> -n rae-memory

# Common causes:
# - Insufficient resources
# - PVC not bound
# - Image pull errors
```

**2. Database connection errors**

```bash
# Check PostgreSQL pod
kubectl logs -f rae-memory-postgresql-0 -n rae-memory

# Test connectivity
kubectl exec -it deployment/rae-memory-api -n rae-memory -- \
  nc -zv rae-memory-postgresql 5432
```

**3. ML Service timeout**

```bash
# Check ML Service health
kubectl exec -it deployment/rae-memory-api -n rae-memory -- \
  curl http://rae-memory-ml-service:8001/health

# Increase timeout in values.yaml
memoryApi:
  env:
    - name: ML_SERVICE_TIMEOUT
      value: "60"  # seconds
```

**4. Budget exceeded errors (HTTP 402)**

```bash
# Check current budget
curl http://rae-api.yourdomain.com/v1/budgets/current \
  -H "X-Tenant-ID: your-tenant"

# Increase budget
curl -X PUT http://rae-api.yourdomain.com/v1/budgets \
  -H "X-Tenant-ID: your-tenant" \
  -d '{"monthly_limit": 1000.00}'
```

### Debug Pod

Deploy a debug pod with tools:

```bash
kubectl run -it --rm debug \
  --image=nicolaka/netshoot \
  --restart=Never \
  -n rae-memory \
  -- /bin/bash

# Inside debug pod:
# - curl http://rae-memory-api:8000/health
# - nslookup rae-memory-postgresql
# - nc -zv rae-memory-redis-master 6379
```

## Production Checklist

Before going to production, ensure:

### Infrastructure
- [ ] Kubernetes cluster version 1.23+
- [ ] Minimum 3 worker nodes
- [ ] Node resources: 16GB RAM, 4 CPU cores
- [ ] Persistent volume provisioner configured
- [ ] LoadBalancer or Ingress controller installed
- [ ] cert-manager installed for TLS
- [ ] Prometheus Operator for monitoring

### Security
- [ ] NetworkPolicy enabled
- [ ] Pod Security Standards enforced (non-root, read-only FS)
- [ ] External Secrets Operator configured
- [ ] TLS certificates provisioned
- [ ] API authentication enabled
- [ ] Secrets rotated regularly
- [ ] RBAC permissions reviewed

### Cost Control
- [ ] Cost tracking enabled
- [ ] Per-tenant budgets configured
- [ ] Budget alerts configured (80%, 95%)
- [ ] Cost monitoring dashboard created
- [ ] Fallback strategies implemented

### Scaling
- [ ] HPA configured for API (min: 3, max: 20+)
- [ ] HPA configured for Celery Workers
- [ ] Resource limits set appropriately
- [ ] PVC sizes configured for growth
- [ ] External managed database considered

### Monitoring
- [ ] ServiceMonitor deployed
- [ ] Grafana dashboard imported
- [ ] Prometheus alerts configured
- [ ] Logging aggregation setup (Loki/ELK)
- [ ] Health check endpoints verified
- [ ] Uptime monitoring configured (UptimeRobot, Pingdom)

### Reliability
- [ ] Backup strategy defined for PostgreSQL
- [ ] Disaster recovery plan documented
- [ ] Multi-region deployment considered
- [ ] Database replication configured
- [ ] Redis persistence enabled

### Performance
- [ ] Load testing completed
- [ ] Cache hit ratios monitored
- [ ] Database indexes verified
- [ ] Query performance optimized
- [ ] Rate limiting configured

### Operations
- [ ] Deployment documented
- [ ] Runbook created for common issues
- [ ] On-call rotation defined
- [ ] Incident response plan ready
- [ ] Upgrade strategy tested

## Further Reading

- [Helm Chart README](../../helm/rae-memory/README.md) - Detailed configuration reference
- [Cost Controller Documentation](../concepts/cost-controller.md) - Cost management guide
- [Architecture Overview](../concepts/architecture.md) - System design
- [API Documentation](../api/rest-api.md) - REST API reference

## Support

- Issues: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- Documentation: https://github.com/dreamsoft-pro/RAE-agentic-memory/docs
- Email: lesniowskig@gmail.com
