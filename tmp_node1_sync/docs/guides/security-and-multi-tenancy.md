# Security and Multi-Tenancy Guide

This guide explains RAE's security model, authentication mechanisms, and multi-tenancy implementation.

## Table of Contents

- [Authentication](#authentication)
- [Multi-Tenancy](#multi-tenancy)
- [Row Level Security (RLS)](#row-level-security-rls)
- [API Security](#api-security)
- [Rate Limiting](#rate-limiting)
- [Production Best Practices](#production-best-practices)

## Authentication

RAE supports two authentication methods that can be enabled independently or together:

### 1. API Key Authentication

Simple token-based authentication using a shared secret.

**Configuration:**
```env
ENABLE_API_KEY_AUTH=true
SECRET_KEY=your-secret-key-here
```

**Usage:**
```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "X-API-Key: your-secret-key-here" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

**Best for:**
- Internal services
- Development environments
- Simple single-tenant deployments

### 2. JWT Token Authentication (OAuth2)

Enterprise-grade authentication using JSON Web Tokens.

**Configuration:**
```env
ENABLE_JWT_AUTH=true
OAUTH_ENABLED=true
OAUTH_DOMAIN=your-tenant.us.auth0.com
OAUTH_AUDIENCE=https://your-api.com
```

**Supported Providers:**
- Auth0
- AWS Cognito
- Azure AD
- Google Identity Platform
- Custom OAuth2 providers

**Usage:**
```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{...}'
```

**Token validation includes:**
- Signature verification (RSA/ECDSA)
- Expiration checking
- Audience validation
- Issuer validation

**Best for:**
- Production deployments
- Multi-tenant SaaS applications
- Enterprise integrations

## Multi-Tenancy

RAE is built as a multi-tenant system from the ground up. Each tenant's data is completely isolated using PostgreSQL Row Level Security.

### Tenant Isolation

Every request must include a `X-Tenant-ID` header:

```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "X-Tenant-ID: acme-corp" \
  -H "X-Project-ID: project-alpha" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Tenant Hierarchy

```
Tenant (Organization)
  └─ Project 1
      ├─ Memories
      ├─ Knowledge Graph
      └─ Reflections
  └─ Project 2
      ├─ Memories
      └─ ...
```

### Tenant Configuration

```env
TENANCY_ENABLED=true  # Enforce tenant isolation
```

When `TENANCY_ENABLED=false` (development only):
- `X-Tenant-ID` header is optional
- Uses default tenant: `default-tenant`
- **WARNING:** Never disable in production

### Tenant Models

```python
# Example tenant configuration (stored in database)
{
  "tenant_id": "acme-corp",
  "name": "Acme Corporation",
  "tier": "enterprise",  # free, pro, enterprise
  "features": [
    "graphrag",
    "reflection",
    "custom_embeddings"
  ],
  "limits": {
    "max_memories": 1000000,
    "max_projects": 100,
    "requests_per_minute": 1000
  },
  "settings": {
    "llm_provider": "openai",
    "embedding_model": "text-embedding-3-small"
  }
}
```

## Row Level Security (RLS)

RAE uses PostgreSQL's Row Level Security to enforce data isolation at the database level.

### How It Works

1. **Middleware sets tenant context:**
   ```python
   @app.middleware("http")
   async def tenant_middleware(request: Request, call_next):
       tenant_id = request.headers.get("X-Tenant-ID")
       request.state.tenant_id = tenant_id

       # Set PostgreSQL session variable
       async with db.connection() as conn:
           await conn.execute(
               "SET LOCAL app.current_tenant = $1",
               tenant_id
           )
       return await call_next(request)
   ```

2. **RLS policies enforce isolation:**
   ```sql
   -- Enable RLS on memories table
   ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

   -- Create policy
   CREATE POLICY tenant_isolation_policy ON memories
       FOR ALL
       USING (tenant_id = current_setting('app.current_tenant')::uuid);
   ```

3. **Result:**
   - Queries automatically filtered by tenant
   - No way to accidentally access other tenants' data
   - Works at database level (not application level)

### Protected Tables

All tenant-specific tables are protected by RLS:
- `memories`
- `memory_tags`
- `kg_entities` (knowledge graph entities)
- `kg_relationships`
- `reflections`
- `tenant_configs`

## API Security

### CORS Configuration

```env
ALLOWED_ORIGINS=https://app.example.com,https://dashboard.example.com
```

In code:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Input Validation

All requests are validated using Pydantic models:

```python
class StoreMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    layer: str = Field(..., pattern="^(episodic|working|semantic|longterm)$")
    tags: List[str] = Field(default_factory=list, max_items=20)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### PII Protection

RAE includes automatic PII (Personally Identifiable Information) scrubbing:

```python
# PII patterns detected:
- Email addresses
- Phone numbers
- Credit card numbers
- Social security numbers
- IP addresses
- Custom patterns (configurable)
```

**Configuration:**
```env
ENABLE_PII_SCRUBBING=true
PII_SCRUB_MODE=mask  # mask, redact, or hash
```

## Rate Limiting

Protect your API from abuse with Redis-based rate limiting:

```env
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100  # Max requests
RATE_LIMIT_WINDOW=60     # Time window in seconds
```

### Per-Tenant Limits

```python
# Custom limits per tenant tier
RATE_LIMITS = {
    "free": {"requests": 100, "window": 60},
    "pro": {"requests": 1000, "window": 60},
    "enterprise": {"requests": 10000, "window": 60}
}
```

### Implementation

```python
from redis import Redis

async def check_rate_limit(identifier: str, limit: int, window: int):
    key = f"rate_limit:{identifier}"
    count = await redis.incr(key)

    if count == 1:
        await redis.expire(key, window)

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
```

## Production Best Practices

### 1. Enable All Security Features

```env
# Authentication
ENABLE_API_KEY_AUTH=false  # Use JWT in production
ENABLE_JWT_AUTH=true
OAUTH_ENABLED=true

# Authorization
TENANCY_ENABLED=true

# Protection
ENABLE_RATE_LIMITING=true
ENABLE_PII_SCRUBBING=true

# TLS/SSL
# Use reverse proxy (nginx) for HTTPS termination
```

### 2. Secure Secrets Management

**DO NOT** store secrets in `.env` files in production. Use:

- **AWS Secrets Manager**
- **HashiCorp Vault**
- **Azure Key Vault**
- **Kubernetes Secrets**

Example with AWS Secrets Manager:
```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Load at startup
settings.SECRET_KEY = get_secret('rae/secret-key')
```

### 3. Network Security

```yaml
# kubernetes/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rae-api-policy
spec:
  podSelector:
    matchLabels:
      app: rae-api
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - port: 5432
```

### 4. Database Security

```sql
-- Create dedicated roles
CREATE ROLE rae_api_role;
CREATE ROLE rae_readonly_role;

-- Grant minimal permissions
GRANT SELECT, INSERT, UPDATE ON memories TO rae_api_role;
GRANT SELECT ON memories TO rae_readonly_role;

-- Revoke dangerous permissions
REVOKE DELETE ON memories FROM rae_api_role;
REVOKE TRUNCATE ON ALL TABLES IN SCHEMA public FROM rae_api_role;
```

### 5. Audit Logging

Enable detailed audit logs:

```python
# Log all sensitive operations
logger.info(
    "memory_accessed",
    memory_id=memory.id,
    tenant_id=tenant.id,
    user_id=user.id,
    action="read",
    ip_address=request.client.host,
    timestamp=datetime.utcnow()
)
```

### 6. Security Headers

```python
from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.example.com"]
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

### 7. Regular Security Audits

- Review access logs weekly
- Update dependencies monthly
- Scan for vulnerabilities with `safety check`
- Penetration testing quarterly
- Review RLS policies after schema changes

## Compliance

### GDPR Compliance

RAE provides tools for GDPR compliance:

```python
# Right to erasure
DELETE /v1/tenants/{tenant_id}/memories?user_id={user_id}

# Right to access
GET /v1/tenants/{tenant_id}/export?user_id={user_id}

# Data portability
GET /v1/tenants/{tenant_id}/export?format=json
```

### SOC 2 Considerations

- Audit logging (all operations)
- Access controls (RBAC)
- Data encryption (at rest and in transit)
- Backup and disaster recovery
- Incident response procedures

## Troubleshooting

### Common Issues

**1. "Unauthorized" errors:**
- Check JWT token expiration
- Verify `OAUTH_AUDIENCE` matches
- Ensure `Authorization` header format: `Bearer <token>`

**2. "Forbidden" - RLS blocking access:**
- Verify `X-Tenant-ID` header is set
- Check tenant exists in database
- Verify RLS policies are correctly configured

**3. Rate limit errors:**
- Implement exponential backoff in client
- Request rate limit increase for tenant tier
- Check Redis connection

## Further Reading

- [API Reference](../api/rest-api.md)
- [Architecture Overview](../concepts/architecture.md)
- [Deployment Guide](production-deployment.md)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
