# RAE Memory API - Security Overview

**Last Updated:** 2025-11-27
**Status:** Production-Ready (Phase 1-4 Complete)

---

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Multi-Tenancy & Isolation](#multi-tenancy--isolation)
4. [RBAC (Role-Based Access Control)](#rbac-role-based-access-control)
5. [Audit Logging](#audit-logging)
6. [Security Best Practices](#security-best-practices)
7. [Threat Model](#threat-model)
8. [Security Checklist](#security-checklist)

---

## Security Architecture

RAE Memory API implements defense-in-depth with multiple security layers:

```
┌─────────────────────────────────────────────────────┐
│                   API Gateway                        │
│              (Rate Limiting, CORS)                   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              Authentication Layer                    │
│         (API Key / JWT Token Verification)          │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│            Authorization Layer (RBAC)                │
│         (Tenant Access + Role Permissions)           │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              Business Logic Layer                    │
│         (API Endpoints, Services)                    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              Data Access Layer                       │
│      (Tenant Isolation, Query Filtering)             │
└─────────────────────────────────────────────────────┘
```

### Security Layers

1. **Network Layer**: HTTPS/TLS encryption, firewall rules
2. **Application Gateway**: Rate limiting, CORS, DDoS protection
3. **Authentication**: API key or JWT token verification
4. **Authorization**: RBAC with tenant-level and role-level access control
5. **Data Layer**: Tenant isolation, encrypted data at rest (optional)
6. **Audit Layer**: Comprehensive logging of all access attempts

---

## Authentication & Authorization

### Authentication Methods

RAE Memory API supports two authentication methods:

#### 1. API Key Authentication

**Use Case:** Service-to-service communication, backend integrations

```bash
# Enable in .env
ENABLE_API_KEY_AUTH=true
API_KEY=your-secret-api-key

# Request example
curl -H "X-API-Key: your-secret-api-key" \
     https://api.example.com/memory/query
```

**Configuration:**
- Set `ENABLE_API_KEY_AUTH=true`
- Define `API_KEY` in environment
- Include `X-API-Key` header in requests

**Security Notes:**
- Rotate API keys regularly (every 90 days recommended)
- Use different keys per environment (dev/staging/prod)
- Store keys in secret management systems (AWS Secrets Manager, Azure Key Vault)

#### 2. JWT Token Authentication

**Use Case:** User-facing applications, OAuth2/OIDC integrations

```bash
# Enable in .env
ENABLE_JWT_AUTH=true
SECRET_KEY=your-jwt-secret-key

# Request example
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
     https://api.example.com/memory/query
```

**Configuration:**
- Set `ENABLE_JWT_AUTH=true`
- Define `SECRET_KEY` for token signing
- Implement JWT verification in `security/auth.py`

**Token Structure:**
```json
{
  "sub": "user_123",          // User ID (subject)
  "email": "user@example.com",
  "exp": 1735689600,          // Expiration timestamp
  "iss": "your-auth-service", // Issuer
  "aud": "rae-memory-api"     // Audience
}
```

**Security Notes:**
- Use strong secret keys (256-bit minimum)
- Set appropriate token expiration (15-60 minutes recommended)
- Implement token refresh mechanism
- Verify issuer and audience claims

### Authentication Flow

```
┌─────────┐                ┌──────────────┐                ┌─────────┐
│ Client  │                │  RAE Memory  │                │   Auth  │
│         │                │     API      │                │ Service │
└────┬────┘                └──────┬───────┘                └────┬────┘
     │                            │                             │
     │ 1. Request with            │                             │
     │    API Key/JWT Token       │                             │
     ├───────────────────────────►│                             │
     │                            │                             │
     │                            │ 2. Verify Token             │
     │                            ├────────────────────────────►│
     │                            │                             │
     │                            │ 3. Token Valid + User Info  │
     │                            │◄────────────────────────────┤
     │                            │                             │
     │                            │ 4. Check RBAC               │
     │                            │    (Tenant Access + Role)   │
     │                            │                             │
     │ 5. Response                │                             │
     │◄───────────────────────────┤                             │
     │                            │                             │
```

---

## Multi-Tenancy & Isolation

RAE Memory API implements strict tenant isolation to prevent data leakage between tenants.

### Tenant Identification

Every request must include a tenant identifier:

```http
X-Tenant-Id: 550e8400-e29b-41d4-a716-446655440000
```

### Isolation Mechanisms

1. **Query-Level Filtering**: All database queries include `tenant_id` filter
2. **Access Control Checks**: User must have explicit access to tenant (via RBAC)
3. **Data Segregation**: Each tenant's data is logically isolated
4. **Audit Logging**: All cross-tenant access attempts are logged

### Tenant Access Verification

```python
# Automatic tenant access verification
@router.get("/tenant/{tenant_id}/stats")
async def get_stats(
    tenant_id: str,
    _: bool = Depends(verify_tenant_access),  # ← Enforces access check
):
    # User must have role in this tenant
    # Otherwise 403 Forbidden
    ...
```

### Security Considerations

- **No Tenant Enumeration**: Tenant IDs are UUIDs, not sequential integers
- **Explicit Access Required**: Users must be explicitly granted access to tenants
- **Role Expiration**: Tenant access can expire automatically
- **Audit Trail**: All access attempts are logged with IP and user agent

---

## RBAC (Role-Based Access Control)

See detailed guide: [RBAC Guide](rbac.md)

### Role Hierarchy

```
┌──────────────────────────────────────────────────┐
│  OWNER (Level 5)                                 │
│  - Full control including tenant deletion        │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│  ADMIN (Level 4)                                 │
│  - Manage users, settings, billing               │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│  DEVELOPER (Level 3)                             │
│  - Full API access, read/write memories          │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│  ANALYST (Level 2)                               │
│  - Analytics and read-only access                │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│  VIEWER (Level 1)                                │
│  - Read-only access to memories                  │
└──────────────────────────────────────────────────┘
```

### Permission Matrix

| Action                  | Owner | Admin | Developer | Analyst | Viewer |
|-------------------------|-------|-------|-----------|---------|--------|
| Delete Tenant           | ✅    | ❌    | ❌        | ❌      | ❌     |
| Manage Users            | ✅    | ✅    | ❌        | ❌      | ❌     |
| Manage Billing          | ✅    | ✅    | ❌        | ❌      | ❌     |
| Read/Write Memories     | ✅    | ✅    | ✅        | ❌      | ❌     |
| Delete Memories         | ✅    | ✅    | ✅        | ❌      | ❌     |
| View Analytics          | ✅    | ✅    | ✅        | ✅      | ❌     |
| Read Memories           | ✅    | ✅    | ✅        | ✅      | ✅     |

---

## Audit Logging

All security-relevant events are logged to the `access_logs` table.

### Logged Events

- ✅ Authentication attempts (success and failure)
- ✅ Tenant access checks
- ✅ Permission denials
- ✅ Role assignments and revocations
- ✅ Sensitive operations (user management, billing)

### Log Structure

```sql
CREATE TABLE access_logs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,           -- e.g., "memories:write"
    resource TEXT NOT NULL,         -- e.g., "memories"
    resource_id TEXT,               -- Specific resource ID
    allowed BOOLEAN NOT NULL,       -- Access granted or denied
    denial_reason TEXT,             -- Reason for denial
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB                  -- Additional context
);
```

### Example Log Entries

```json
// Successful access
{
  "user_id": "user_123",
  "tenant_id": "tenant_abc",
  "action": "memories:read",
  "allowed": true,
  "ip_address": "192.168.1.100",
  "timestamp": "2025-11-27T14:30:00Z"
}

// Access denied
{
  "user_id": "user_456",
  "tenant_id": "tenant_xyz",
  "action": "users:delete",
  "allowed": false,
  "denial_reason": "Role developer cannot perform users:delete",
  "ip_address": "192.168.1.101",
  "timestamp": "2025-11-27T14:31:00Z"
}
```

---

## Security Best Practices

### For Deployment

1. **Always Enable Authentication**
   ```bash
   ENABLE_API_KEY_AUTH=true  # or ENABLE_JWT_AUTH=true
   ```

2. **Use Strong Secrets**
   ```bash
   # Generate strong secrets
   openssl rand -hex 32
   ```

3. **Enable Rate Limiting**
   ```bash
   ENABLE_RATE_LIMITING=true
   RATE_LIMIT_REQUESTS=100
   RATE_LIMIT_WINDOW=60
   ```

4. **Restrict CORS Origins**
   ```bash
   ALLOWED_ORIGINS=["https://app.yourcompany.com"]
   ```

5. **Use HTTPS/TLS**
   - Always use TLS 1.2 or higher
   - Configure proper SSL certificates
   - Enable HSTS headers

6. **Secret Management**
   - Never commit secrets to version control
   - Use secret management systems (AWS Secrets Manager, Azure Key Vault)
   - Rotate secrets regularly

7. **Monitor and Alert**
   - Set up alerts for failed authentication attempts
   - Monitor access logs for unusual patterns
   - Track rate limit violations

### For Development

1. **Test Security Configurations**
   ```bash
   # Test with auth disabled (dev only)
   ENABLE_API_KEY_AUTH=false
   ENABLE_JWT_AUTH=false
   ```

2. **Use Separate Credentials**
   - Different API keys per environment
   - Different database credentials
   - Separate tenant IDs for testing

3. **Review Logs Regularly**
   ```sql
   -- Check for denied access attempts
   SELECT * FROM access_logs
   WHERE allowed = false
   ORDER BY timestamp DESC
   LIMIT 100;
   ```

---

## Threat Model

### Threats Mitigated

✅ **SQL Injection**: Parameterized queries, asyncpg protection
✅ **XSS**: API-only (no HTML rendering), content validation
✅ **CSRF**: API tokens, no cookie-based auth
✅ **Authentication Bypass**: Mandatory auth at gateway level
✅ **Authorization Bypass**: Explicit RBAC checks on all endpoints
✅ **Tenant Data Leakage**: Query-level filtering + RBAC
✅ **API Key Exposure**: Environment variables, secret management
✅ **Rate Limiting**: Configurable limits, DDoS protection

### Threats Requiring Additional Mitigation

⚠️ **JWT Token Verification**: Currently accepts any token when ENABLE_JWT_AUTH=true
⚠️ **System Admin Check**: Currently allows all authenticated users (governance endpoints)
⚠️ **Data Encryption at Rest**: Optional, not enabled by default
⚠️ **Network-Level DDoS**: Requires external WAF/CDN

---

## Security Checklist

### Pre-Production Checklist

- [ ] Authentication enabled (`ENABLE_API_KEY_AUTH=true` or `ENABLE_JWT_AUTH=true`)
- [ ] Strong secrets configured (256-bit minimum)
- [ ] Rate limiting enabled
- [ ] CORS origins restricted
- [ ] HTTPS/TLS enabled
- [ ] Secrets stored in secret management system
- [ ] Database credentials secured
- [ ] Audit logging enabled
- [ ] Monitoring and alerting configured
- [ ] Security review completed
- [ ] Penetration testing performed

### Runtime Monitoring

- [ ] Monitor failed authentication attempts
- [ ] Track rate limit violations
- [ ] Review audit logs for unauthorized access
- [ ] Monitor for unusual tenant access patterns
- [ ] Check for expired role assignments
- [ ] Verify API key rotation schedule

---

## Related Documentation

- [RBAC Guide](rbac.md) - Detailed role-based access control
- [Authentication Guide](authentication.md) - Authentication configuration
- [Tenant Isolation Guide](tenant-isolation.md) - Multi-tenancy architecture

---

**For security issues or questions, please refer to our security policy or contact the security team.**
