# Security Best Practices

This guide covers security best practices for deploying and operating RAE in production environments.

## Table of Contents

- [Authentication & Authorization](#authentication--authorization)
- [API Security](#api-security)
- [Data Protection](#data-protection)
- [Network Security](#network-security)
- [Secrets Management](#secrets-management)
- [Input Validation](#input-validation)
- [Monitoring & Auditing](#monitoring--auditing)
- [Compliance](#compliance)

## Authentication & Authorization

### API Key Authentication

RAE supports API key authentication for simple, secure access control.

**Enable API Key Auth:**
```env
# .env
ENABLE_API_KEY_AUTH=true
API_KEY=your-secure-random-key-here
```

**Generate Secure API Key:**
```bash
# Generate a 32-byte secure random key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: kJ8dF3mN9pQ2wR5tY7uH0jK3lM6nP9qS2vT5wX8zA1b

# Or use OpenSSL
openssl rand -base64 32
```

**Using API Key:**
```bash
curl -X POST https://api.yourdomain.com/v1/memory/store \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"content": "test", "layer": "episodic"}'
```

### JWT Token Authentication

For more advanced use cases, enable JWT authentication:

```env
# .env
ENABLE_JWT_AUTH=true
SECRET_KEY=your-jwt-secret-key  # Generate with: openssl rand -hex 32
```

**JWT Token Structure:**
```json
{
  "sub": "user_123",
  "tenant_id": "tenant_abc",
  "exp": 1735689600,
  "iat": 1735603200
}
```

### Multi-Tenancy Security

RAE implements Row Level Security (RLS) for tenant isolation:

```sql
-- Enable RLS on memories table
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation
CREATE POLICY tenant_isolation ON memories
  FOR ALL
  TO authenticated_user
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

**Best Practices:**
- Always pass tenant_id in headers: `X-Tenant-ID`
- Never allow cross-tenant queries
- Validate tenant_id against authenticated user
- Log all cross-tenant access attempts

## API Security

### Rate Limiting

Protect against abuse with rate limiting:

```env
# .env
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100  # Max requests per window
RATE_LIMIT_WINDOW=60     # Time window in seconds
```

**Rate Limit Response:**
```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1735603260
Retry-After: 60

{
  "error": "Rate limit exceeded",
  "limit": 100,
  "window": 60,
  "reset_at": 1735603260
}
```

**Customizing Rate Limits:**
```python
# Per-endpoint rate limiting
@app.get("/v1/memory/expensive-operation")
@limiter.limit("10/minute")
async def expensive_operation():
    ...
```

### CORS Configuration

Restrict CORS to trusted origins only:

```env
# .env - DO NOT use "*" in production!
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### HTTPS/TLS

**Always use HTTPS in production!**

**Nginx SSL Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Strong SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

**Let's Encrypt (Free SSL):**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renew
sudo certbot renew --dry-run
```

### Security Headers

Add security headers to all responses:

```nginx
# nginx.conf
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

## Data Protection

### Encryption at Rest

**Database Encryption:**
```bash
# PostgreSQL with encryption
docker run -d \
  -e POSTGRES_INITDB_ARGS="--data-checksums" \
  -v /encrypted-volume:/var/lib/postgresql/data \
  ankane/pgvector:latest
```

**Volume Encryption (Linux):**
```bash
# Create encrypted volume
cryptsetup luksFormat /dev/sdb
cryptsetup open /dev/sdb encrypted_volume

# Format and mount
mkfs.ext4 /dev/mapper/encrypted_volume
mount /dev/mapper/encrypted_volume /mnt/encrypted
```

### Encryption in Transit

All API communication should use TLS:

```python
# Force HTTPS redirect
@app.middleware("http")
async def force_https(request: Request, call_next):
    if request.url.scheme != "https" and settings.FORCE_HTTPS:
        url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(url))
    return await call_next(request)
```

### Sensitive Data Handling

**Never log sensitive data:**
```python
# BAD
logger.info(f"Storing memory: {memory.content}")

# GOOD
logger.info("Storing memory", memory_id=memory.id, layer=memory.layer)
```

**Redact sensitive fields:**
```python
def redact_sensitive(data: dict) -> dict:
    """Redact sensitive fields from logs."""
    sensitive_fields = ['password', 'api_key', 'token', 'secret']

    for field in sensitive_fields:
        if field in data:
            data[field] = '***REDACTED***'

    return data
```

### Data Retention & Deletion

Implement data retention policies:

```python
# Automatic cleanup of old episodic memories
@celery.task
def cleanup_old_memories():
    """Delete episodic memories older than retention period."""
    retention_days = settings.MEMORY_RETENTION_DAYS

    await db.execute("""
        DELETE FROM memories
        WHERE layer = 'episodic'
        AND timestamp < NOW() - INTERVAL '%s days'
    """, (retention_days,))
```

**GDPR Right to Deletion:**
```python
@app.delete("/v1/user/{user_id}/data")
async def delete_user_data(user_id: str):
    """Delete all user data (GDPR compliance)."""
    # Delete memories
    await db.execute(
        "DELETE FROM memories WHERE metadata->>'user_id' = $1",
        user_id
    )

    # Delete from cache
    await redis.delete(f"user:{user_id}:*")

    # Audit log
    await audit_log("user_data_deleted", user_id=user_id)

    return {"status": "deleted"}
```

## Network Security

### Firewall Rules

**Only expose necessary ports:**
```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH (restrict to specific IPs)
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Block direct database access from outside
sudo ufw deny 5432/tcp  # PostgreSQL
sudo ufw deny 6379/tcp  # Redis
sudo ufw deny 6333/tcp  # Qdrant
```

### VPC/Private Networks

Deploy services in private subnets:

```
┌─────────────────────────────────────────┐
│            Public Subnet                │
│  ┌──────────────────────────────────┐  │
│  │   Load Balancer (HTTPS only)     │  │
│  └──────────────┬───────────────────┘  │
└─────────────────┼───────────────────────┘
                  │
┌─────────────────┼───────────────────────┐
│            Private Subnet               │
│  ┌──────────────▼───────────────────┐  │
│  │        RAE API Servers           │  │
│  └──────────────┬───────────────────┘  │
│                 │                       │
│  ┌──────────────▼───────────────────┐  │
│  │  Database, Redis, Qdrant         │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### DDoS Protection

Use Cloudflare or similar:

```nginx
# Rate limiting at edge
# Cloudflare automatically provides DDoS protection

# Additional nginx rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
```

## Secrets Management

### Never Commit Secrets

**Add to `.gitignore`:**
```gitignore
.env
.env.production
.env.staging
.env.local
*.pem
*.key
*.crt
secrets/
```

### Use Environment Variables

```bash
# BAD - hardcoded in code
API_KEY = "sk-abc123"

# GOOD - from environment
API_KEY = os.getenv("API_KEY")

# BETTER - validation
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is required")
```

### Secrets Rotation

Rotate secrets regularly:

```bash
# 1. Generate new API key
NEW_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Update in secrets manager
aws secretsmanager update-secret \
  --secret-id rae/api-key \
  --secret-string "$NEW_API_KEY"

# 3. Rolling restart
kubectl rollout restart deployment/rae-api

# 4. Verify old key is no longer accepted
curl -H "X-API-Key: old-key" https://api.yourdomain.com/health
# Should return 403 Forbidden
```

### Secret Scanning

Prevent secrets from being committed:

```bash
# Install git-secrets
brew install git-secrets  # macOS
sudo apt install git-secrets  # Ubuntu

# Configure
cd your-repo
git secrets --install
git secrets --register-aws
```

## Input Validation

RAE implements comprehensive input validation:

### Content Validation

```python
from apps.memory_api.security.validation import validate_content

# Validates:
# - Not empty
# - Max length (50KB)
# - No XSS patterns (<script>, javascript:, etc.)
# - No null bytes
content = validate_content(user_input)
```

### Tag Validation

```python
from apps.memory_api.security.validation import validate_tags

# Validates:
# - Max 20 tags
# - Each tag max 50 chars
# - Alphanumeric + underscore + hyphen only
# - No dangerous characters
tags = validate_tags(["user-pref", "coding_style"])
```

### SQL Injection Prevention

**Always use parameterized queries:**

```python
# GOOD - parameterized query
await conn.fetch(
    "SELECT * FROM memories WHERE tenant_id = $1 AND tags && $2",
    tenant_id,
    tags
)

# BAD - string interpolation (SQL injection!)
await conn.fetch(
    f"SELECT * FROM memories WHERE tenant_id = '{tenant_id}'"
)
```

### NoSQL Injection Prevention

For MongoDB/document databases:

```python
# GOOD
result = collection.find({"tenant_id": tenant_id})

# BAD - allows injection
result = collection.find(eval(user_input))
```

## Monitoring & Auditing

### Audit Logging

Log security-relevant events:

```python
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Log all API requests for audit trail."""

    # Extract metadata
    user_id = request.state.user.get("user_id") if hasattr(request.state, "user") else None
    tenant_id = request.headers.get("X-Tenant-ID")

    # Log request
    logger.info(
        "api_request",
        method=request.method,
        path=request.url.path,
        user_id=user_id,
        tenant_id=tenant_id,
        ip=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    response = await call_next(request)

    # Log response
    logger.info(
        "api_response",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        user_id=user_id
    )

    return response
```

### Security Monitoring

Monitor for suspicious activity:

```python
# Failed authentication attempts
@app.exception_handler(HTTPException)
async def log_failed_auth(request: Request, exc: HTTPException):
    if exc.status_code in [401, 403]:
        logger.warning(
            "authentication_failed",
            path=request.url.path,
            ip=request.client.host,
            status=exc.status_code
        )
        # Alert if many failures from same IP
        await check_brute_force(request.client.host)
```

### Anomaly Detection

```python
async def check_brute_force(ip: str):
    """Detect brute force attempts."""
    key = f"failed_auth:{ip}"
    count = await redis.incr(key)
    await redis.expire(key, 300)  # 5 minute window

    if count > 10:
        logger.error("possible_brute_force", ip=ip, attempts=count)
        # Block IP
        await redis.setex(f"blocked:{ip}", 3600, "1")
        # Send alert
        await send_alert(f"Possible brute force from {ip}")
```

## Compliance

### GDPR Compliance

**Data Subject Rights:**
- Right to access
- Right to deletion
- Right to portability
- Right to rectification

**Implementation:**
```python
@app.get("/v1/user/{user_id}/data")
async def export_user_data(user_id: str):
    """Export all user data (GDPR compliance)."""
    memories = await get_user_memories(user_id)
    return {
        "user_id": user_id,
        "data": memories,
        "exported_at": datetime.utcnow().isoformat()
    }
```

### SOC 2 Compliance

For SOC 2 compliance, implement:

1. **Access Controls**: Role-based access control (RBAC)
2. **Encryption**: Data encrypted at rest and in transit
3. **Monitoring**: Comprehensive logging and alerting
4. **Change Management**: Audit trail for all changes
5. **Incident Response**: Security incident procedures

### HIPAA Compliance (Healthcare)

Additional requirements for healthcare data:

- **Encryption**: FIPS 140-2 validated encryption
- **Access Logs**: Detailed audit trails
- **Data Minimization**: Only store necessary data
- **Business Associate Agreement**: Required for vendors

## Security Checklist

### Development

- [ ] Input validation on all user inputs
- [ ] Parameterized database queries
- [ ] No hardcoded secrets in code
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Logging sanitizes sensitive data

### Deployment

- [ ] API authentication enabled
- [ ] Strong passwords for all services
- [ ] Database backups encrypted
- [ ] Firewall rules configured
- [ ] Services in private network
- [ ] SSL/TLS certificates valid
- [ ] Security monitoring enabled
- [ ] Incident response plan documented

### Operations

- [ ] Regular security updates
- [ ] Secrets rotated quarterly
- [ ] Access reviews monthly
- [ ] Penetration testing annually
- [ ] Security training for team
- [ ] Incident response drills
- [ ] Compliance audits current

## Incident Response

### Preparation

1. **Document procedures**: Create runbook
2. **Define roles**: Who responds to what
3. **Set up alerting**: Immediate notification
4. **Prepare tools**: Investigation and remediation
5. **Practice**: Regular drills

### Response Plan

```
┌─────────────────────────────────────────┐
│  1. Detection & Alert                   │
│  - Monitoring detects anomaly            │
│  - Alert sent to security team          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  2. Containment                         │
│  - Isolate affected systems             │
│  - Block malicious IPs                  │
│  - Rotate compromised credentials       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  3. Investigation                       │
│  - Analyze logs                         │
│  - Determine scope                      │
│  - Identify root cause                  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  4. Remediation                         │
│  - Apply fixes                          │
│  - Restore from backups if needed       │
│  - Verify security restored             │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  5. Post-Incident                       │
│  - Document findings                    │
│  - Improve processes                    │
│  - Notify affected parties if required  │
└─────────────────────────────────────────┘
```

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Controls](https://www.cisecurity.org/controls)
- [GDPR Compliance](https://gdpr.eu/)

---

**Related Guides:**
- [Production Deployment](production-deployment.md)
- [Monitoring & Observability](../observability.md)
- [API Reference](../api/rest-api.md)
