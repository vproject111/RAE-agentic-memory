# Multi-Tenancy Architecture

## Overview

RAE is built as a **multi-tenant system** from the ground up, providing complete data isolation and tenant-specific configurations for enterprise deployments.

## Key Features

- **Row-Level Security (RLS)**: PostgreSQL RLS policies enforce tenant data isolation
- **Tenant ID in All Tables**: Every record includes `tenant_id` for filtering
- **Isolated Configurations**: Per-tenant LLM profiles, budgets, retention policies
- **API-Level Filtering**: All queries automatically filter by tenant
- **Audit Trail**: Per-tenant audit logs for compliance

## Architecture

### Tenant Identification

Tenants are identified using UUIDs stored in the `tenant_id` column across all tables:

| Table | Tenant Isolation |
|-------|------------------|
| `memories` | `tenant_id` column + RLS policy |
| `graph_nodes` | `tenant_id` column |
| `graph_triples` | `tenant_id` column |
| `cost_logs` | `tenant_id` column |
| `retention_policies` | `tenant_id` column |
| `llm_profiles` | `tenant_id` column |
| `trigger_rules` | `tenant_id` column |

### Row-Level Security (RLS)

PostgreSQL RLS policies enforce data boundaries:

```sql
-- Example RLS policy on memories table
CREATE POLICY tenant_isolation ON memories
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant')::UUID);

ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
```

Application sets tenant context per connection:

```python
async with pool.acquire() as conn:
    await conn.execute("SET app.current_tenant = $1", tenant_id)
    # All queries now automatically filtered by tenant_id
```

## API Usage

### Setting Tenant Context

#### Via Header (Recommended)

```http
GET /api/v1/memories
X-Tenant-ID: 123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
```

#### Via SDK

```python
from rae_memory_sdk import MemoryClient

client = MemoryClient(
    base_url="https://rae.example.com",
    api_key="your-api-key",
    tenant_id="123e4567-e89b-12d3-a456-426614174000"
)

# All operations scoped to this tenant
client.store_memory(content="...", ...)
```

### Creating Tenants

```python
from apps.memory_api.repositories.tenant_repository import TenantRepository

repo = TenantRepository(pool)

tenant = await repo.create_tenant(
    name="Acme Corp",
    plan="enterprise",
    metadata={
        "industry": "finance",
        "region": "us-east",
        "contact_email": "admin@acme.com"
    }
)

# Returns:
# {
#   "tenant_id": "uuid-123",
#   "name": "Acme Corp",
#   "plan": "enterprise",
#   "created_at": "2025-12-01T...",
#   "settings": {...}
# }
```

## Tenant-Specific Configurations

### LLM Profiles

Each tenant can have custom LLM configurations:

```python
{
  "tenant_id": "tenant-123",
  "llm_profile": {
    "default_model": "gpt-4o",
    "fallback_chain": ["gpt-4o", "gpt-4o-mini", "local-llama3"],
    "budget_usd_monthly": 500,
    "enable_caching": true
  }
}
```

### Retention Policies

Per-tenant data retention:

```python
{
  "tenant_id": "tenant-123",
  "retention_policies": {
    "episodic_memories_days": 90,
    "semantic_memories_days": 365,
    "reflective_memories_days": 730,
    "cost_logs_days": 2555  # 7 years for financial records
  }
}
```

### Cost Budgets

Per-tenant cost limits with alerts:

```python
{
  "tenant_id": "tenant-123",
  "cost_budget": {
    "monthly_limit_usd": 500,
    "alert_thresholds": [0.8, 0.9, 0.95],
    "action_on_exceed": "block"  # or "alert_only"
  }
}
```

## Roles and Permissions

Tenant-scoped roles for access control:

| Role | Permissions |
|------|-------------|
| `tenant_admin` | Full access to tenant data, configure policies |
| `tenant_user` | Read/write memories, queries, reflections |
| `tenant_viewer` | Read-only access to memories and dashboards |
| `service_account` | API access for integrations |

See: `docs/RAE-Roles.md` for complete RACI matrix.

## Data Boundaries

### Query Filtering

All repository queries include tenant filtering:

```python
async def get_memories(self, tenant_id: str, project: str, ...):
    query = """
        SELECT * FROM memories
        WHERE tenant_id = $1
          AND project = $2
          AND ...
    """
    return await self.pool.fetch(query, tenant_id, project, ...)
```

### Background Workers

Workers process tenants in isolation:

```python
# Decay worker processes each tenant separately
for tenant_id in tenant_ids:
    await decay_worker.run_decay_cycle(
        tenant_ids=[tenant_id],
        ...
    )
```

## Security

### Authentication

- **API Keys**: Per-tenant API keys with scoped permissions
- **JWT Tokens**: Include `tenant_id` claim for verification
- **OAuth Integration**: Tenant-aware OAuth flows

### Authorization

- **Tenant Verification**: Every request validates `tenant_id` matches token
- **Cross-Tenant Access Prevention**: RLS blocks cross-tenant queries
- **Audit Logging**: All tenant operations logged for compliance

### Encryption

- **At Rest**: Tenant data encrypted in PostgreSQL
- **In Transit**: TLS for all API communication
- **Secrets**: Per-tenant secrets stored in secure vault

## Monitoring

### Per-Tenant Metrics

```python
# Prometheus metrics include tenant_id label
rae_memories_stored_total{tenant_id="tenant-123"}
rae_cost_usd_total{tenant_id="tenant-123"}
rae_api_requests_total{tenant_id="tenant-123", endpoint="/memories"}
```

### Tenant Dashboards

Each tenant has isolated monitoring:
- Memory usage statistics
- Cost tracking and budgets
- API usage and quotas
- Performance metrics

## Scaling

### Horizontal Scaling

- **Stateless API**: Scale API servers independently
- **Tenant Sharding**: Large tenants can have dedicated DB shards
- **Cache Isolation**: Per-tenant cache namespaces in Redis

### Resource Limits

Per-tenant quotas:

```python
{
  "tenant_id": "tenant-123",
  "quotas": {
    "max_memories": 1000000,
    "max_api_calls_per_minute": 1000,
    "max_storage_gb": 100
  }
}
```

## Deployment Modes

### Shared Infrastructure (Standard)

All tenants share DB, API, workers:
- Cost-effective for many small tenants
- RLS provides isolation
- Resource limits prevent noisy neighbors

### Dedicated Infrastructure (Enterprise)

Large tenants get dedicated resources:
- Dedicated DB instance
- Dedicated API pods
- Dedicated worker queues
- Full resource isolation

## Migration and Onboarding

### New Tenant Onboarding

```bash
# CLI command for tenant setup
rae tenant create \
  --name "Acme Corp" \
  --plan enterprise \
  --admin-email admin@acme.com

# Creates:
# - Tenant record
# - Default project
# - API keys
# - Default policies
# - Monitoring dashboards
```

### Data Migration

```python
# Migrate tenant from old system
await migration_service.migrate_tenant(
    source_tenant_id="old-tenant-123",
    target_tenant_id="new-tenant-456",
    include_memories=True,
    include_graphs=True
)
```

## Related Documentation

- [RAE Roles](./RAE-Roles.md) - Role-based access control
- [ISO 42001 Implementation](./ISO42001_IMPLEMENTATION_MAP.md) - Compliance per tenant
- [Cost Guard](./LLM_PROFILES_AND_COST_GUARD.md) - Per-tenant budgets
