# RAE Memory Engine - Helm Chart

Enterprise-grade Kubernetes deployment for RAE (Reflective Agentic Memory Engine).

## Prerequisites

- Kubernetes 1.23+
- Helm 3.8+
- PersistentVolume provisioner support in the underlying infrastructure
- LoadBalancer support (or Ingress controller)

## Installing the Chart

```bash
# Add Helm repository (if published)
helm repo add rae https://charts.rae.memory

# Create namespace
kubectl create namespace rae-memory

# Create secrets
kubectl create secret generic rae-secrets \
  --from-literal=database-url='postgresql://user:pass@postgres:5432/rae' \
  --from-literal=redis-url='redis://:pass@redis:6379/0' \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=anthropic-api-key='sk-ant-...' \
  -n rae-memory

# Install chart
helm install rae-memory ./helm/rae-memory \
  --namespace rae-memory \
  --values custom-values.yaml
```

## Configuration

### Core Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `memoryApi.replicaCount` | Number of API replicas | `2` |
| `memoryApi.resources.requests.memory` | API memory request | `1Gi` |
| `memoryApi.resources.requests.cpu` | API CPU request | `500m` |
| `memoryApi.autoscaling.enabled` | Enable HPA | `true` |
| `memoryApi.autoscaling.minReplicas` | Min replicas | `2` |
| `memoryApi.autoscaling.maxReplicas` | Max replicas | `10` |

### ML Service Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mlService.replicaCount` | Number of ML service replicas | `2` |
| `mlService.resources.requests.memory` | ML memory request | `2Gi` |
| `mlService.resources.requests.cpu` | ML CPU request | `1000m` |

### Database Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Deploy PostgreSQL | `true` |
| `postgresql.auth.username` | PostgreSQL username | `rae` |
| `postgresql.primary.persistence.size` | PostgreSQL volume size | `20Gi` |

### Redis Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Deploy Redis | `true` |
| `redis.auth.enabled` | Enable Redis auth | `true` |
| `redis.master.persistence.size` | Redis volume size | `8Gi` |

### Qdrant Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `qdrant.enabled` | Deploy Qdrant | `true` |
| `qdrant.persistence.size` | Qdrant volume size | `50Gi` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts[0].host` | API hostname | `rae-api.example.com` |

### Cost Control Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `cost.enableTracking` | Enable cost tracking | `true` |
| `cost.defaultDailyLimit` | Default daily budget (USD) | `10.00` |
| `cost.defaultMonthlyLimit` | Default monthly budget (USD) | `100.00` |
| `cost.warningThreshold` | Budget warning threshold (0.0-1.0) | `0.8` |

### Celery Worker Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `celeryWorker.enabled` | Deploy Celery workers | `true` |
| `celeryWorker.replicaCount` | Number of worker replicas | `2` |
| `celeryWorker.concurrency` | Worker concurrency | `4` |
| `celeryWorker.maxTasksPerChild` | Max tasks before restart | `1000` |
| `celeryWorker.autoscaling.enabled` | Enable HPA | `true` |

### External Secrets Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `externalSecrets.enabled` | Use External Secrets Operator | `false` |
| `externalSecrets.secretStore` | Secret store type | `aws-secrets-manager` |
| `externalSecrets.refreshInterval` | Secret refresh interval | `1h` |

### Monitoring Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.enabled` | Enable Prometheus monitoring | `true` |
| `monitoring.serviceMonitor.enabled` | Deploy ServiceMonitor | `true` |
| `monitoring.serviceMonitor.interval` | Scrape interval | `30s` |
| `monitoring.grafanaDashboard.enabled` | Deploy Grafana dashboard | `true` |

### Security Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `networkPolicy.enabled` | Enable NetworkPolicy | `true` |
| `podSecurityContext.runAsNonRoot` | Run as non-root user | `true` |
| `podSecurityContext.runAsUser` | User ID | `1000` |
| `securityContext.readOnlyRootFilesystem` | Read-only root FS | `true` |

## Example Values Files

### Production Configuration

```yaml
# production-values.yaml
memoryApi:
  replicaCount: 5
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
    requests:
      cpu: 1000m
      memory: 2Gi
  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60

mlService:
  replicaCount: 3
  resources:
    limits:
      cpu: 4000m
      memory: 8Gi
    requests:
      cpu: 2000m
      memory: 4Gi

postgresql:
  primary:
    persistence:
      size: 100Gi
    resources:
      limits:
        memory: 4Gi
        cpu: 2000m

qdrant:
  persistence:
    size: 200Gi
  resources:
    limits:
      memory: 8Gi
      cpu: 4000m

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "1000"
  hosts:
    - host: api.rae.prod.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: rae-prod-tls
      hosts:
        - api.rae.prod.example.com
```

### Development Configuration

```yaml
# dev-values.yaml
memoryApi:
  replicaCount: 1
  resources:
    limits:
      cpu: 500m
      memory: 1Gi
    requests:
      cpu: 250m
      memory: 512Mi
  autoscaling:
    enabled: false

mlService:
  replicaCount: 1

postgresql:
  primary:
    persistence:
      size: 10Gi

redis:
  master:
    persistence:
      size: 2Gi

qdrant:
  persistence:
    size: 10Gi

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: rae-dev.local
      paths:
        - path: /
          pathType: Prefix
  tls: []
```

## Enterprise Features

### Cost Control

RAE includes sophisticated cost tracking and budget management for LLM API usage.

**Enable Cost Tracking:**

```yaml
# values.yaml
configMap:
  ENABLE_COST_TRACKING: "true"
  DEFAULT_DAILY_LIMIT: "10.00"
  DEFAULT_MONTHLY_LIMIT: "100.00"
  BUDGET_WARNING_THRESHOLD: "0.8"
```

**Features:**
- Real-time cost tracking for all LLM providers (OpenAI, Anthropic, Google)
- Daily and monthly budget limits with automatic enforcement
- Multi-tenant cost isolation
- HTTP 402 responses when budget exceeded
- Detailed usage analytics and cost logs

**Set Budgets via API:**

```bash
curl -X PUT http://rae-api.example.com/v1/budgets \
  -H "X-Tenant-ID: acme-corp" \
  -d '{"monthly_limit": 500.00, "daily_limit": 20.00}'
```

See [Cost Controller Documentation](../../docs/concepts/cost-controller.md) for details.

### External Secrets Operator

For production deployments, use External Secrets Operator instead of standard Kubernetes secrets.

**Prerequisites:**
- External Secrets Operator installed in cluster
- SecretStore or ClusterSecretStore configured

**Enable External Secrets:**

```yaml
# values.yaml
externalSecrets:
  enabled: true
  refreshInterval: "1h"
  secretStore: "aws-secrets-manager"
  secretStoreKind: "SecretStore"
  keys:
    databaseUrl: "rae/database-url"
    redisUrl: "rae/redis-url"
    openaiApiKey: "rae/openai-api-key"
    anthropicApiKey: "rae/anthropic-api-key"
```

**AWS Secrets Manager Example:**

```bash
# Store secrets in AWS
aws secretsmanager create-secret \
  --name rae/database-url \
  --secret-string "postgresql://user:pass@host:5432/rae"

aws secretsmanager create-secret \
  --name rae/openai-api-key \
  --secret-string "sk-..."
```

**GCP Secret Manager Example:**

```yaml
externalSecrets:
  enabled: true
  secretStore: "gcpsm"
  keys:
    databaseUrl: "projects/my-project/secrets/rae-database-url"
```

### Monitoring & Observability

RAE provides comprehensive monitoring with Prometheus and Grafana.

**Enable Monitoring:**

```bash
helm install rae-memory ./helm/rae-memory \
  --set monitoring.enabled=true \
  --set monitoring.serviceMonitor.enabled=true \
  --set monitoring.grafanaDashboard.enabled=true
```

**Prometheus Metrics:**
- `rae_api_requests_total` - Total API requests
- `rae_api_request_duration_seconds` - Request latency
- `rae_memory_operations_total` - Memory operations
- `rae_llm_cost_total` - LLM API costs
- `rae_budget_remaining` - Remaining budget
- `rae_search_cache_hit_ratio` - Cache effectiveness

**Grafana Dashboard:**

The chart includes a pre-built Grafana dashboard with:
- Request rate and latency
- Memory operation metrics
- Cost tracking and budget status
- System health indicators

**Custom Alerting:**

```yaml
# values.yaml
monitoring:
  serviceMonitor:
    enabled: true
    relabelings:
      - sourceLabels: [__meta_kubernetes_pod_name]
        targetLabel: pod
```

### Celery Workers

RAE uses Celery for background task processing (reflections, evaluations, etc.).

**Configure Workers:**

```yaml
# values.yaml
celeryWorker:
  enabled: true
  replicaCount: 2
  concurrency: 4  # Tasks per worker
  maxTasksPerChild: 1000  # Restart after N tasks

  # Auto-scaling
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80
    targetMemoryUtilizationPercentage: 75
```

**Worker Behavior:**
- Scale-up: 100% increase per 30s (max 2 pods at once)
- Scale-down: 50% decrease per 60s (300s stabilization)
- Automatic restarts after 1000 tasks (prevents memory leaks)

**Monitor Workers:**

```bash
# Check worker status
kubectl get pods -l app.kubernetes.io/component=celery-worker

# View worker logs
kubectl logs -f deployment/rae-memory-celery-worker
```

## Upgrading

```bash
# Upgrade to new version
helm upgrade rae-memory ./helm/rae-memory \
  --namespace rae-memory \
  --values custom-values.yaml

# Rollback if needed
helm rollback rae-memory 1 -n rae-memory
```

## Uninstalling

```bash
# Uninstall release
helm uninstall rae-memory -n rae-memory

# Delete namespace
kubectl delete namespace rae-memory
```

## Monitoring

The chart includes ServiceMonitor for Prometheus:

```bash
# Enable monitoring
helm install rae-memory ./helm/rae-memory \
  --set monitoring.enabled=true \
  --set monitoring.serviceMonitor.enabled=true
```

## Security

### Network Policies

RAE includes comprehensive NetworkPolicies for pod-to-pod traffic isolation.

**Enable Network Policies:**

```yaml
# values.yaml
networkPolicy:
  enabled: true
  policyTypes:
    - Ingress
    - Egress
```

**Traffic Rules:**

**Memory API:**
- Ingress: From ingress-nginx namespace (port 8000)
- Ingress: From same namespace pods (ML service, Celery, etc.)
- Egress: To kube-system (DNS)
- Egress: To PostgreSQL (5432), Redis (6379), Qdrant (6333)
- Egress: To ML Service (8001), Reranker (8002)
- Egress: To internet (443) for LLM APIs

**ML Service:**
- Ingress: Only from API and Celery Worker (port 8001)
- Egress: To kube-system (DNS)
- Egress: To internet (443) for model downloads

**Database/Storage:**
- Ingress: Only from API, ML Service, Celery Worker
- No outbound internet access

**Test Network Policy:**

```bash
# Verify policy is active
kubectl get networkpolicy -n rae-memory

# Test connectivity from API pod
kubectl exec -it deployment/rae-memory-api -n rae-memory -- curl http://rae-memory-ml-service:8001/health
```

### Pod Security Standards

The chart enforces strict Pod Security Standards (Restricted profile):

**Security Context:**

```yaml
# values.yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
```

**Features:**
- Non-root user (UID 1000)
- Read-only root filesystem (with writable emptyDir volumes)
- No privilege escalation
- All capabilities dropped
- Seccomp profile enabled

### Secrets Management

**Option 1: Standard Kubernetes Secrets (Development)**

```bash
kubectl create secret generic rae-secrets \
  --from-literal=database-url='postgresql://...' \
  --from-literal=openai-api-key='sk-...' \
  -n rae-memory
```

**Option 2: External Secrets Operator (Production)**

```yaml
# values.yaml
externalSecrets:
  enabled: true
  secretStore: "aws-secrets-manager"
```

See [External Secrets](#external-secrets-operator) section above.

### TLS & Certificate Management

**Automatic TLS with cert-manager:**

```yaml
# values.yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: rae-api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: rae-tls
      hosts:
        - rae-api.example.com
```

**Prerequisites:**
- cert-manager installed in cluster
- ClusterIssuer configured (letsencrypt-prod)

### RBAC

The chart creates minimal RBAC permissions:

```yaml
# Automatically created by Helm
apiVersion: v1
kind: ServiceAccount
metadata:
  name: rae-memory-api

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: rae-memory-api
rules:
- apiGroups: [""]
  resources: ["secrets", "configmaps"]
  verbs: ["get", "list"]
```

**Custom RBAC:**

```yaml
# values.yaml
serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::ACCOUNT:role/rae-memory"
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n rae-memory
kubectl logs -f deployment/rae-memory-api -n rae-memory
```

### Check Service Connectivity

```bash
kubectl port-forward svc/rae-memory-api 8000:8000 -n rae-memory
curl http://localhost:8000/health
```

### Database Issues

```bash
# Check PostgreSQL
kubectl exec -it deployment/rae-memory-postgresql -n rae-memory -- psql -U rae -d rae_memory

# Check Redis
kubectl exec -it deployment/rae-memory-redis-master -n rae-memory -- redis-cli ping
```

## Support

- Documentation: https://github.com/dreamsoft-pro/RAE-agentic-memory/docs
- Issues: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
