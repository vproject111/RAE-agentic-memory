# Security & Multi-Tenancy Reference

**Status**: "Almost Enterprise" - Production Ready with Documented Limitations
**Version**: 2.0-enterprise
**Last Updated**: 2025-11-28

## Executive Summary

RAE implements **enterprise-grade multi-tenant isolation** with comprehensive authentication and authorization mechanisms. This document provides an **honest assessment** of what is implemented, what is not, and what deployment patterns are safe for production.

**TL;DR**: RAE is suitable for **internal tools, PoCs, and controlled environments**. For public internet deployment, use behind a reverse proxy with TLS termination and API gateway.

---

## What IS Implemented ✅

### 1. Multi-Tenant Isolation

#### Database-Level Row-Level Security (RLS)

**Implementation**: PostgreSQL RLS policies enforce tenant isolation at the database level.

```sql
-- Example from migrations
CREATE POLICY tenant_isolation_policy ON memories
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Protection**:
- ✅ Cross-tenant reads are **impossible** even with SQL injection
- ✅ Queries automatically scoped to current tenant
- ✅ No application-layer tenant filtering bugs possible

**Code References**:
- `infra/migrations/003_tenant_isolation.sql` - RLS policies
- `apps/memory_api/repositories/memory_repository.py` - Tenant-scoped queries

---

#### Application-Level Tenant Guards

**All memory endpoints enforce tenant checks**:

```python
# Example from memory API
@router.post("/store")
async def store_memory(
    req: StoreMemoryRequest,
    tenant_id: str = Depends(get_and_verify_tenant_id)  # ✅ Required
):
    # tenant_id is ALWAYS verified before any operation
    ...
```

**Protected Endpoints**:
- ✅ `/v1/memory/*` - All memory operations
- ✅ `/v1/agent/*` - Agent execution
- ✅ `/v1/governance/*` - Cost tracking & audits
- ✅ `/v1/graph/*` - Knowledge graph operations
- ✅ `/v1/cache/*` - Context cache management

**Code References**:
- `apps/memory_api/security/dependencies.py:get_and_verify_tenant_id` - Tenant verification
- `apps/memory_api/api/v1/` - All API routers use tenant guards

---

### 2. Authentication Mechanisms

RAE supports **two authentication modes**:

#### A. API Key Authentication

**Configuration**:
```bash
export ENABLE_API_KEY_AUTH=True
export API_KEY=your-secret-key-here
```

**Behavior**:
- Requests must include `X-API-Key` header
- Single shared key for all requests
- Suitable for: Internal services, server-to-server communication

**Limitations**:
- ⚠️ No per-user attribution
- ⚠️ Key rotation requires restart
- ⚠️ Not suitable for multi-user applications

---

#### B. JWT Token Authentication

**Configuration**:
```bash
export ENABLE_JWT_AUTH=True
export JWT_SECRET=your-jwt-secret
export JWT_ALGORITHM=HS256
```

**Behavior**:
- Requests must include `Authorization: Bearer <token>` header
- Tokens contain user ID and tenant assignments
- Supports role-based access control (RBAC)

**Token Claims**:
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "roles": ["admin", "developer"],
  "exp": 1234567890
}
```

**Suitable for**: Multi-user applications, external APIs

**Code References**:
- `apps/memory_api/security/auth.py:verify_token` - JWT verification
- `apps/memory_api/security/rbac.py` - Role-based access control

---

### 3. Role-Based Access Control (RBAC)

**5-Tier Role Hierarchy**:

| Role | Permissions | Typical Users |
|------|------------|--------------|
| **Owner** | Full system access, user management | System admins, founders |
| **Admin** | Tenant management, governance | Team leads, managers |
| **Developer** | Memory operations, agent execution | Engineers, data scientists |
| **Analyst** | Read-only access, analytics | Business analysts, auditors |
| **Viewer** | Read-only memory access | Stakeholders, observers |

**Permission Enforcement**:

```python
# Example: Only admins can access governance
@router.get("/governance/overview")
async def get_overview(
    current_user: dict = Depends(require_admin)  # ✅ RBAC check
):
    ...
```

**Protected Operations**:
- ✅ Governance endpoints - Admin only
- ✅ Tenant management - Admin/Owner only
- ✅ Memory operations - Developer+ required
- ✅ Agent execution - Developer+ required

**Code References**:
- `apps/memory_api/models/rbac.py` - Role definitions
- `apps/memory_api/services/rbac_service.py` - RBAC logic
- `apps/memory_api/security/dependencies.py:require_admin` - Permission checks

---

### 4. Audit Logging

**All access is logged**:

```python
# Automatic logging for all authenticated requests
{
  "event": "memory_accessed",
  "user_id": "uuid",
  "tenant_id": "uuid",
  "resource": "/v1/memory/query",
  "timestamp": "2025-11-28T10:00:00Z",
  "result": "success"
}
```

**Logged Events**:
- ✅ Authentication attempts (success/failure)
- ✅ Memory access (read/write)
- ✅ Governance operations
- ✅ Permission denials

**Storage**: `access_logs` table

**Code References**:
- `apps/memory_api/services/rbac_service.py:log_access` - Audit logging
- `infra/migrations/002_rbac_tables.sql` - Access logs schema

---

### 5. Cost Governance

**Per-Tenant Budget Enforcement**:

```python
# Cost tracking and enforcement
@router.post("/agent/execute")
@cost_guard()  # ✅ Enforces daily/monthly limits
async def execute(req: AgentExecuteRequest):
    ...
```

**Tracked Metrics**:
- ✅ LLM token usage (input/output)
- ✅ Daily and monthly costs per tenant
- ✅ Budget violations and rejections

**Enforcement**:
- Requests exceeding budget are rejected with 429 status
- Prometheus metrics track all costs
- Governance API provides cost visibility

**Code References**:
- `apps/memory_api/middleware/cost_guard.py` - Budget enforcement
- `apps/memory_api/metrics.py` - Cost metrics

---

## What is NOT Implemented ❌

### 1. TLS/HTTPS Termination

**Status**: ❌ Not implemented inside RAE

**Current Behavior**:
- RAE listens on HTTP (port 8000)
- No built-in TLS certificate management
- No automatic HTTPS redirect

**Production Workaround**:
```
Internet → [Nginx/Traefik/ALB with TLS] → RAE HTTP:8000
```

**Recommendation**: **REQUIRED** for production - use reverse proxy for TLS termination.

---

### 2. External Secrets Manager Integration

**Status**: ❌ Not implemented

**Current Behavior**:
- Secrets passed via environment variables
- No integration with HashiCorp Vault, AWS Secrets Manager, etc.
- Secrets visible in process environment

**Production Workaround**:
```bash
# Use external secret injection
docker run -e API_KEY=$(vault kv get -field=key secret/rae/api-key) rae-api
```

**Recommendation**: Use container orchestrator secret injection (Kubernetes Secrets, Docker Secrets, etc.)

---

### 3. Rate Limiting (Beyond Cost Guard)

**Status**: ⚠️ Partial implementation

**What exists**:
- ✅ Cost-based rate limiting (token budgets)
- ✅ SlowAPI integration for basic rate limiting

**What's missing**:
- ❌ Per-IP rate limiting
- ❌ Distributed rate limiting (Redis-based)
- ❌ Adaptive rate limiting

**Production Workaround**: Use API gateway (Kong, Tyk, AWS API Gateway) for comprehensive rate limiting.

---

### 4. Formal Security Audit

**Status**: ❌ Not performed

**What's missing**:
- ❌ No third-party penetration testing
- ❌ No formal security certification (SOC 2, ISO 27001)
- ❌ No vulnerability scanning in CI/CD
- ❌ No OWASP Top 10 compliance verification

**Mitigation**: Internal code review and standard security practices followed.

---

### 5. Data Encryption at Rest

**Status**: ⚠️ Depends on infrastructure

**Current Behavior**:
- Database encryption depends on PostgreSQL/Qdrant configuration
- No application-level field encryption
- No envelope encryption for sensitive fields

**Production Recommendation**:
```bash
# Use encrypted storage at infrastructure level
- AWS RDS with encryption enabled
- Qdrant with disk encryption
- Encrypted EBS volumes
```

---

## Deployment Patterns

### ✅ SAFE for Production

#### 1. Internal Corporate Network

```
Deployment: Behind corporate VPN/firewall
Authentication: JWT with SSO integration
Network: Private VPC, no public internet exposure
TLS: Corporate proxy handles TLS
```

**Suitable for**:
- Internal tools and dashboards
- Team knowledge bases
- Development environments

---

#### 2. Controlled Cloud Environment

```
Deployment: AWS/GCP/Azure private network
Load Balancer: ALB/NLB with TLS termination
Authentication: JWT with OAuth2 provider
Database: RDS with encryption enabled
Secrets: AWS Secrets Manager / Parameter Store
```

**Suitable for**:
- Multi-tenant SaaS (controlled beta)
- Enterprise PoCs
- Production with known user base

**Example Architecture**:
```
┌──────────────────────────────────────────────────────┐
│ Internet (HTTPS only)                                 │
└────────────────┬─────────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │  ALB + WAF     │ ← TLS termination
         │  + Rate Limit  │ ← DDoS protection
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │  RAE API       │ ← JWT auth
         │  (HTTP:8000)   │ ← RLS enabled
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │  RDS Postgres  │ ← Encrypted at rest
         │  + Qdrant      │ ← Private subnet
         └────────────────┘
```

---

### ⚠️ USE WITH CAUTION

#### 1. Public Internet (With Precautions)

```
Deployment: Public internet with proper gateway
Requirements:
  - ✅ Reverse proxy with TLS (Nginx/Traefik)
  - ✅ WAF (Web Application Firewall)
  - ✅ API Gateway with rate limiting
  - ✅ JWT authentication (not API key)
  - ✅ Strong JWT secrets (256-bit minimum)
  - ✅ Monitoring and alerting
```

**Suitable for**: Limited public API, invite-only beta

---

### ❌ NOT RECOMMENDED

#### 1. Direct Public Internet Exposure

```
DON'T DO THIS:
┌──────────────┐
│  Internet    │
└──────┬───────┘
       │
       │ HTTP:8000 (no TLS, no gateway)
       │
   ┌───▼──────┐
   │ RAE API  │ ← ❌ Exposed directly
   └──────────┘
```

**Why not**:
- ❌ No TLS encryption
- ❌ No DDoS protection
- ❌ No rate limiting beyond cost guard
- ❌ Attack surface not minimized

---

#### 2. Single API Key for Multi-User Application

```
DON'T DO THIS:
- Shared API key among multiple external users
- API key embedded in client-side code
- API key in public repositories
```

**Why not**:
- ❌ No user attribution
- ❌ Cannot revoke individual user access
- ❌ Audit logs meaningless
- ❌ Security breach affects all users

---

## Security Checklist for Production

### Before Deploying

- [ ] **TLS enabled** via reverse proxy or load balancer
- [ ] **JWT authentication** configured (not API key for multi-user)
- [ ] **Strong secrets** (256-bit minimum for JWT_SECRET)
- [ ] **Database encryption** enabled at infrastructure level
- [ ] **RLS policies** verified in PostgreSQL
- [ ] **Audit logging** enabled and monitored
- [ ] **Cost governance** limits configured per tenant
- [ ] **Backup strategy** in place for database
- [ ] **Monitoring** (Prometheus/Grafana) configured
- [ ] **Alerting** for failed auth attempts, budget violations

### Ongoing

- [ ] **Regular secret rotation** (JWT secrets, API keys)
- [ ] **Audit log review** (monthly minimum)
- [ ] **Cost monitoring** (detect anomalies)
- [ ] **Dependency updates** (security patches)
- [ ] **Access review** (remove stale users/tenants)

---

## Incident Response

### Suspected Security Breach

1. **Immediate**:
   - Rotate all secrets (JWT_SECRET, API_KEY)
   - Check audit logs for unauthorized access
   - Disable affected user accounts

2. **Investigation**:
   - Review `access_logs` table for anomalies
   - Check Prometheus metrics for unusual patterns
   - Examine database for cross-tenant leaks (should be impossible with RLS)

3. **Remediation**:
   - Patch vulnerabilities
   - Notify affected tenants (if data exposure confirmed)
   - Update security procedures

### Contact

**Security Issues**: Open issue at https://github.com/dreamsoft-pro/RAE-agentic-memory/issues with `[SECURITY]` prefix

**Critical Vulnerabilities**: Email maintainers directly (see README.md)

---

## Compliance & Certifications

### Current Status

| Standard | Status | Notes |
|----------|--------|-------|
| **SOC 2 Type II** | ❌ Not certified | Self-assessment: ~70% compliant |
| **ISO 27001** | ❌ Not certified | Standard security practices followed |
| **GDPR** | ⚠️ Partial | Tenant isolation + audit logs present, no DPO |
| **HIPAA** | ❌ Not compliant | No BAA, no encryption at rest guarantee |
| **PCI DSS** | ❌ Not applicable | Do not store payment card data |

### Recommendations by Compliance Requirement

**GDPR (EU Users)**:
- ✅ Tenant isolation prevents data mixing
- ✅ Audit logs support DSAR (Data Subject Access Requests)
- ⚠️ Appoint DPO if processing EU data at scale
- ⚠️ Implement data retention policies
- ⚠️ Add explicit user consent mechanisms

**HIPAA (Healthcare Data)**:
- ❌ **Not recommended** without extensive additional controls
- Required: Encryption at rest (all fields), BAA with cloud provider, extensive audit logging
- Use dedicated HIPAA-compliant infrastructure

**General Corporate Use**:
- ✅ Suitable with documented limitations
- ✅ Internal tools, team knowledge bases
- ✅ Non-sensitive data processing

---

## "Almost Enterprise" - Honest Assessment

### What "Almost Enterprise" Means

**We ARE enterprise-ready for**:
- ✅ Multi-tenant isolation (RLS-backed)
- ✅ Role-based access control
- ✅ Audit logging and governance
- ✅ Cost tracking and enforcement
- ✅ Scalable architecture

**We are NOT enterprise-ready for**:
- ❌ Public internet without additional infrastructure
- ❌ Highly regulated industries (healthcare, finance) without additional controls
- ❌ Environments requiring formal security certification
- ❌ Zero-downtime deployments (not tested at scale)

### Use Case Suitability

| Use Case | Suitability | Notes |
|----------|-------------|-------|
| **Internal corporate tools** | ✅ Excellent | Deploy behind VPN/firewall |
| **Team knowledge base** | ✅ Excellent | JWT + private network |
| **Controlled SaaS beta** | ✅ Good | Use proper gateway + TLS |
| **Public API (invite-only)** | ⚠️ Acceptable | Requires API gateway + monitoring |
| **Open public access** | ❌ Not recommended | Additional hardening required |
| **Healthcare/Finance data** | ❌ Not recommended | Compliance gaps exist |

---

## Related Documentation

- [RBAC Models](../apps/memory_api/models/rbac.py) - Role definitions
- [Authentication](../apps/memory_api/security/auth.py) - Auth implementation
- [Cost Guard](../apps/memory_api/middleware/cost_guard.py) - Budget enforcement
- [Configuration](./CONFIG_REFLECTIVE_MEMORY.md) - Feature flags

---

**Last Security Review**: 2025-11-28
**Next Review**: 2026-Q1 or before v2.0 release
**Responsible Team**: Core maintainers

---

**Honest Statement**: RAE is production-ready for internal and controlled environments with documented security practices. For public internet deployment or regulated industries, additional infrastructure and controls are required. We prioritize honesty about limitations over marketing claims.
