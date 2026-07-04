# RAE Helm Chart

Official Helm chart for deploying RAE (Reflective Agentic Memory Engine) on Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.8+
- PostgreSQL 13+ (external or in-cluster)
- Redis 6+ (external or in-cluster)
- Qdrant 1.0+ (external or in-cluster)

## Installation

### Quick Start

```bash
# Add the Helm repository (if published)
helm repo add rae https://charts.example.com/rae
helm repo update

# Install with default configuration
helm install my-rae rae/rae
```

### Local Installation

```bash
# Install from local chart directory
helm install my-rae ./charts/rae

# Or with custom values
helm install my-rae ./charts/rae -f my-values.yaml
```

### Installation with Dependencies

If you need to deploy PostgreSQL, Redis, and Qdrant along with RAE:

```bash
# Install PostgreSQL using Bitnami chart
helm install postgres bitnami/postgresql \
  --set auth.username=rae_user \
  --set auth.password=your-password \
  --set auth.database=rae_db

# Install Redis using Bitnami chart
helm install redis bitnami/redis \
  --set auth.enabled=false

# Install Qdrant (example)
helm install qdrant qdrant/qdrant

# Install RAE with correct connection details
helm install my-rae ./charts/rae \
  --set postgresql.host=postgres-postgresql.default.svc.cluster.local \
  --set redis.host=redis-master.default.svc.cluster.local \
  --set qdrant.host=qdrant.default.svc.cluster.local
```

## Configuration

### Essential Configuration

Create a `my-values.yaml` file:

```yaml
# Image configuration
image:
  repository: ghcr.io/dreamsoft-pro/rae-memory-api
  tag: "2.0.0-enterprise"

# Scaling
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10

# Database connections
postgresql:
  host: my-postgres.example.com
  database: rae_db
  user: rae_user
  existingSecret: rae-postgres-secret

redis:
  host: my-redis.example.com

qdrant:
  host: my-qdrant.example.com

# Security
config:
  enableApiKeyAuth: true
  enableRateLimiting: true

secrets:
  createFromValues: true
  apiKeys:
    - "my-secure-api-key-1"
    - "my-secure-api-key-2"

# Ingress
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: rae-api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: rae-api-tls
      hosts:
        - rae-api.example.com
```

Then install:

```bash
helm install my-rae ./charts/rae -f my-values.yaml
```

### Advanced Configuration

#### OpenTelemetry Tracing

```yaml
config:
  otelTracesEnabled: true
  otelExporterType: otlp
  otelExporterEndpoint: http://tempo.monitoring.svc.cluster.local:4317
```

#### Prometheus Monitoring

```yaml
monitoring:
  serviceMonitor:
    enabled: true
    interval: 30s
    labels:
      prometheus: kube-prometheus
```

#### High Availability Setup

```yaml
replicaCount: 3

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
                - rae
        topologyKey: kubernetes.io/hostname

podDisruptionBudget:
  enabled: true
  minAvailable: 2

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 60
```

## Configuration Parameters

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of RAE replicas | `2` |
| `image.repository` | RAE image repository | `ghcr.io/dreamsoft-pro/rae-memory-api` |
| `image.tag` | RAE image tag | `2.0.0-enterprise` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### Service Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Container port | `8000` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.annotations` | Ingress annotations | `{}` |
| `ingress.hosts` | Ingress hosts | `[]` |
| `ingress.tls` | Ingress TLS configuration | `[]` |

### Database Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.host` | PostgreSQL host | `postgres.default.svc.cluster.local` |
| `postgresql.port` | PostgreSQL port | `5432` |
| `postgresql.database` | Database name | `rae_db` |
| `postgresql.user` | Database user | `rae_user` |
| `postgresql.existingSecret` | Existing secret for password | `rae-postgres-secret` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.environment` | Environment (development/production) | `production` |
| `config.enableApiKeyAuth` | Enable API key authentication | `true` |
| `config.enableJwtAuth` | Enable JWT authentication | `false` |
| `config.enableRateLimiting` | Enable rate limiting | `true` |
| `config.rateLimitRequests` | Rate limit requests per window | `100` |
| `config.rateLimitWindow` | Rate limit window (seconds) | `60` |
| `config.otelTracesEnabled` | Enable OpenTelemetry tracing | `true` |
| `config.otelExporterEndpoint` | OTLP exporter endpoint | `http://tempo:4317` |

### Autoscaling Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `2` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU % | `70` |
| `autoscaling.targetMemoryUtilizationPercentage` | Target Memory % | `80` |

## Upgrading

```bash
# Upgrade to new version
helm upgrade my-rae ./charts/rae -f my-values.yaml

# Upgrade with specific values
helm upgrade my-rae ./charts/rae \
  --set image.tag=2.1.0-enterprise \
  --reuse-values
```

## Uninstalling

```bash
helm uninstall my-rae
```

## Secrets Management

### Using External Secrets Operator

```yaml
# values.yaml
secrets:
  createFromValues: false

postgresql:
  existingSecret: rae-postgres-secret-external

# Create ExternalSecret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: rae-postgres-secret-external
spec:
  secretStoreRef:
    name: aws-secrets-manager
  target:
    name: rae-postgres-secret-external
  data:
    - secretKey: password
      remoteRef:
        key: rae/postgres-password
```

### Using Sealed Secrets

```bash
# Create secret
kubectl create secret generic rae-secrets \
  --from-literal=postgres-password=my-password \
  --from-literal=api-keys=key1,key2 \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > rae-sealed-secret.yaml

# Apply sealed secret
kubectl apply -f rae-sealed-secret.yaml
```

## Monitoring and Observability

### Prometheus Metrics

Enable ServiceMonitor:

```yaml
monitoring:
  serviceMonitor:
    enabled: true
    labels:
      prometheus: kube-prometheus
```

Metrics available at `/metrics`:
- Request rate and latency
- Token usage
- Cost tracking
- Cache hit rates
- Error rates

### OpenTelemetry Tracing

Configure tracing backend:

```yaml
config:
  otelTracesEnabled: true
  otelExporterEndpoint: http://tempo:4317
```

Supported backends:
- Jaeger
- Tempo (Grafana)
- Elastic APM
- AWS X-Ray
- Google Cloud Trace

### Grafana Dashboards

Import dashboard from `docs/grafana-dashboard.json` or enable auto-provisioning:

```yaml
monitoring:
  grafanaDashboard:
    enabled: true
    labels:
      grafana_dashboard: "1"
```

## Troubleshooting

### Pods not starting

Check logs:
```bash
kubectl logs -l app.kubernetes.io/name=rae
kubectl describe pod <pod-name>
```

Common issues:
- Database connection failures (check secrets)
- Missing environment variables
- Insufficient resources

### Database connection issues

Test connection:
```bash
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h postgres-postgresql -U rae_user -d rae_db
```

### Rate limiting issues

Check configuration:
```bash
kubectl get configmap <release-name>-rae -o yaml
```

Adjust limits:
```yaml
config:
  rateLimitRequests: 200
  rateLimitWindow: 60
```

## Production Checklist

- [ ] Set `replicaCount` >= 3
- [ ] Enable `autoscaling`
- [ ] Configure `resources.limits` and `resources.requests`
- [ ] Enable `ingress` with TLS
- [ ] Use external secret management (not `createFromValues`)
- [ ] Configure `postgresql.existingSecret`
- [ ] Enable `monitoring.serviceMonitor`
- [ ] Enable `config.otelTracesEnabled`
- [ ] Set `config.environment: production`
- [ ] Configure `podDisruptionBudget`
- [ ] Set up `affinity` rules for pod distribution
- [ ] Enable `networkPolicy` if supported
- [ ] Configure backup for PostgreSQL
- [ ] Set up log aggregation (ELK, Loki, etc.)

## Examples

### Development Environment

```yaml
replicaCount: 1
autoscaling:
  enabled: false

resources:
  limits:
    cpu: 1000m
    memory: 2Gi

config:
  environment: development
  logLevel: DEBUG
  enableApiKeyAuth: false

ingress:
  enabled: false
```

### Production Environment

```yaml
replicaCount: 5
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

config:
  environment: production
  logLevel: INFO
  enableApiKeyAuth: true
  enableRateLimiting: true
  otelTracesEnabled: true

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: rae-api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: rae-api-tls
      hosts:
        - rae-api.example.com

monitoring:
  serviceMonitor:
    enabled: true

podDisruptionBudget:
  enabled: true
  minAvailable: 2
```

## Support

- GitHub: https://github.com/dreamsoft-pro/RAE-agentic-memory
- Issues: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- Documentation: https://github.com/dreamsoft-pro/RAE-agentic-memory/tree/main/docs
