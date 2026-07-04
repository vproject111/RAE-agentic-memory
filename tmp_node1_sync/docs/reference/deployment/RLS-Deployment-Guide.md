# Row-Level Security (RLS) Deployment Guide

> **ISO/IEC 42001 Compliance** - RISK-001 (Data Leak) & RISK-006 (Tenant Contamination)

## 1. Overview

This guide covers deployment of PostgreSQL Row-Level Security (RLS) for multi-tenant isolation in RAE.

**What is RLS?**
Row-Level Security is a PostgreSQL feature that allows you to define policies to restrict which rows users can access. For RAE, this means:
- Even if application code has a bug, the database prevents cross-tenant access
- Defense-in-depth security (multiple layers of protection)
- Compliance with ISO/IEC 42001 risk mitigation requirements

**Status:** ✅ READY FOR DEPLOYMENT (Test thoroughly before production!)

---

## 2. Pre-Deployment Checklist

Before enabling RLS, ensure:

- [ ] **Backup database** - Take full backup before migration
- [ ] **Review tenant_id columns** - Ensure all tables have proper tenant_id columns with indexes
- [ ] **Test environment ready** - Have staging environment for testing
- [ ] **Application code updated** - Middleware changes deployed (see Section 5)
- [ ] **Monitoring configured** - Set up alerts for RLS-related errors
- [ ] **Downtime window** - Plan for brief downtime during migration (5-10 minutes)

---

## 3. Deployment Steps

### Step 1: Verify Prerequisites

```bash
# Connect to your PostgreSQL database
psql -U postgres -d rae_db

# Check that all critical tables have tenant_id column
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE column_name = 'tenant_id'
  AND table_schema = 'public'
ORDER BY table_name;

# Verify tenant_id is indexed (CRITICAL for performance)
SELECT
    t.tablename,
    i.indexname,
    array_agg(a.attname) as indexed_columns
FROM pg_indexes i
JOIN pg_class c ON c.relname = i.indexname
JOIN pg_attribute a ON a.attrelid = c.oid
JOIN pg_tables t ON t.tablename = i.tablename
WHERE t.schemaname = 'public'
  AND a.attname = 'tenant_id'
GROUP BY t.tablename, i.indexname;
```

**Expected output:** All tables should have tenant_id with an index.

If missing indexes, create them:
```sql
CREATE INDEX CONCURRENTLY idx_memories_tenant_id ON memories(tenant_id);
CREATE INDEX CONCURRENTLY idx_semantic_nodes_tenant_id ON semantic_nodes(tenant_id);
-- etc. for all tables
```

### Step 2: Run Migration Script

```bash
# Dry run (check syntax)
psql -U postgres -d rae_db -f migrations/006_enable_row_level_security.sql --dry-run

# REAL RUN (this enables RLS)
psql -U postgres -d rae_db -f migrations/006_enable_row_level_security.sql
```

**Expected output:**
```
ALTER TABLE
ALTER TABLE
...
CREATE POLICY
CREATE POLICY
...
CREATE FUNCTION
```

### Step 3: Verify RLS is Enabled

```sql
-- Check RLS is enabled on tables
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('memories', 'semantic_nodes', 'graph_triples', 'reflections')
ORDER BY tablename;
```

**Expected:** All tables should show `rowsecurity = true`

```sql
-- List all RLS policies
SELECT schemaname, tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

**Expected:** Should see `tenant_isolation_*` policies for each table.

### Step 4: Test RLS Enforcement

```sql
-- Test 1: Set tenant context and query
SELECT set_current_tenant('00000000-0000-0000-0000-000000000001');
SELECT COUNT(*) FROM memories;  -- Should only see tenant 1 data

-- Test 2: Change tenant and verify isolation
SELECT set_current_tenant('00000000-0000-0000-0000-000000000002');
SELECT COUNT(*) FROM memories;  -- Should only see tenant 2 data (different count)

-- Test 3: Verify cross-tenant access is blocked
SELECT clear_current_tenant();
SELECT COUNT(*) FROM memories;  -- Should return 0 or error (no tenant context)

-- Test 4: Superuser bypass
SET ROLE postgres;
SELECT COUNT(*) FROM memories;  -- Should see ALL data (superuser bypass)
RESET ROLE;
```

### Step 5: Deploy Application Code Changes

**Update main.py to include RLS middleware:**

```python
# apps/memory_api/main.py

from apps.memory_api.middleware.rls_context import RLSContextMiddleware

# ... existing imports ...

app = FastAPI(...)

# IMPORTANT: RLSContextMiddleware MUST come AFTER TenantContextMiddleware
app.add_middleware(TenantContextMiddleware)  # Existing
app.add_middleware(RLSContextMiddleware)     # NEW - Add this

# ... rest of app setup ...
```

**Restart application:**
```bash
docker compose restart memory-api
# or
kubectl rollout restart deployment/memory-api
```

### Step 6: Monitor and Validate

**Check application logs for RLS context:**
```bash
# Look for successful RLS context setting
grep "rls_context_set" /var/log/rae/memory-api.log

# Look for warnings/errors
grep "rls_context" /var/log/rae/memory-api.log | grep -E "WARNING|ERROR"
```

**Test via API:**
```bash
# Create memory as tenant 1
curl -X POST http://localhost:8000/v1/memories \
  -H "X-Tenant-ID: tenant-1" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory for tenant 1"}'

# Try to query as tenant 2 (should not see tenant 1 data)
curl http://localhost:8000/v1/memories \
  -H "X-Tenant-ID: tenant-2"
```

---

## 4. Performance Impact

**Expected:** Minimal impact (< 5% query overhead)

RLS adds a `WHERE tenant_id = 'xxx'` clause to every query. Since tenant_id should already be in your WHERE clauses, the impact is minimal.

**Monitoring:**
```sql
-- Check query performance before/after RLS
EXPLAIN ANALYZE
SELECT * FROM memories WHERE tenant_id = '00000000-0000-0000-0000-000000000001' LIMIT 10;
```

**If performance degrades:**
1. Verify tenant_id indexes exist
2. Update statistics: `ANALYZE memories;`
3. Check query plans: `EXPLAIN (ANALYZE, BUFFERS) <query>;`

---

## 5. Application Code Integration

### FastAPI Middleware (already done)

The `RLSContextMiddleware` automatically sets tenant context for each HTTP request.

**Order matters:**
```python
# Correct order:
app.add_middleware(TenantContextMiddleware)  # Sets request.state.tenant_id
app.add_middleware(RLSContextMiddleware)     # Uses tenant_id to set RLS context
```

### Background Tasks (Celery workers)

For background tasks, you must explicitly set RLS context:

```python
from apps.memory_api.middleware.rls_context import (
    set_rls_context_for_background_task,
    clear_rls_context_for_background_task,
)

@celery_app.task
def my_background_task(tenant_id: str):
    pool = await get_pool()

    try:
        # Set RLS context for this task
        await set_rls_context_for_background_task(pool, tenant_id)

        # Now all queries will be filtered by tenant_id
        result = await pool.fetch("SELECT * FROM memories")

        # Process result...

    finally:
        # Clean up RLS context
        await clear_rls_context_for_background_task(pool)
```

---

## 6. Rollback Procedure

If RLS causes issues, you can rollback:

### Quick Rollback (disable RLS but keep policies)

```sql
-- Disable RLS on all tables (queries still work normally)
ALTER TABLE memories DISABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_nodes DISABLE ROW LEVEL SECURITY;
ALTER TABLE graph_triples DISABLE ROW LEVEL SECURITY;
ALTER TABLE reflections DISABLE ROW LEVEL SECURITY;
ALTER TABLE cost_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE deletion_audit_log DISABLE ROW LEVEL SECURITY;
```

### Full Rollback (remove policies)

```sql
-- Drop all RLS policies
DROP POLICY IF EXISTS tenant_isolation_memories ON memories;
DROP POLICY IF EXISTS superuser_bypass_memories ON memories;
DROP POLICY IF EXISTS tenant_isolation_semantic_nodes ON semantic_nodes;
-- ... etc for all tables

-- Disable RLS
ALTER TABLE memories DISABLE ROW LEVEL SECURITY;
-- ... etc for all tables

-- Drop helper functions
DROP FUNCTION IF EXISTS set_current_tenant(uuid);
DROP FUNCTION IF EXISTS get_current_tenant();
DROP FUNCTION IF EXISTS clear_current_tenant();
```

### Rollback Application Code

Remove RLSContextMiddleware from main.py:
```python
# Comment out or remove:
# app.add_middleware(RLSContextMiddleware)
```

---

## 7. Troubleshooting

### Issue: "permission denied for table memories"

**Cause:** RLS is enabled but tenant context is not set.

**Solution:**
1. Check application logs for `rls_context_missing_tenant`
2. Verify TenantContextMiddleware is running before RLSContextMiddleware
3. Ensure X-Tenant-ID header is present in requests

### Issue: "current_setting() not found"

**Cause:** Migration script didn't run successfully.

**Solution:**
```sql
-- Re-run migration
\i migrations/006_enable_row_level_security.sql
```

### Issue: Queries return 0 rows (should return data)

**Cause:** Wrong tenant_id set in context.

**Solution:**
```sql
-- Check current tenant context
SELECT get_current_tenant();

-- Verify tenant exists
SELECT id, name FROM tenants WHERE id = get_current_tenant();
```

### Issue: Performance degradation

**Cause:** Missing indexes on tenant_id.

**Solution:**
```sql
-- Create indexes (CONCURRENTLY for zero downtime)
CREATE INDEX CONCURRENTLY idx_memories_tenant_id ON memories(tenant_id);
```

---

## 8. Security Verification

### Penetration Test Checklist

- [ ] **Cross-tenant access blocked** - Verify user cannot access other tenant's data
- [ ] **SQL injection hardened** - RLS policies prevent injection from bypassing tenant isolation
- [ ] **Superuser bypass works** - Verify admins can still access all data for maintenance
- [ ] **No data leakage in logs** - Check logs don't expose other tenant's data
- [ ] **Backup/restore tested** - Verify RLS works after restore

### Security Audit Query

```sql
-- Audit: Find any data without tenant_id (SHOULD BE EMPTY)
SELECT 'memories' as table_name, COUNT(*) as null_tenant_count
FROM memories WHERE tenant_id IS NULL
UNION ALL
SELECT 'semantic_nodes', COUNT(*) FROM semantic_nodes WHERE tenant_id IS NULL
UNION ALL
SELECT 'reflections', COUNT(*) FROM reflections WHERE tenant_id IS NULL;
```

**Expected:** All counts should be 0.

---

## 9. Compliance & Audit Trail

### ISO/IEC 42001 Mapping

| Requirement | Implementation | Evidence |
|-------------|----------------|----------|
| **RISK-001 Mitigation** | RLS prevents data leaks | Migration 006 + RLS policies |
| **RISK-006 Mitigation** | Tenant isolation enforced | RLS policies active |
| **Defense in Depth** | Database-level + application-level | Middleware + RLS |
| **Audit Trail** | All RLS context changes logged | Application logs |

### Audit Log Queries

```sql
-- List all active RLS policies (for compliance report)
SELECT * FROM pg_policies WHERE schemaname = 'public';

-- Verify RLS is enabled (for audit)
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
```

### Monitoring Queries

```sql
-- Count of RLS violations (should be 0)
-- Note: PostgreSQL doesn't track violations directly, but you can monitor errors in app logs

-- Verify RLS context is being set (check app logs)
-- grep "rls_context_set" /var/log/rae/memory-api.log | wc -l
```

---

## 10. Next Steps

After successful RLS deployment:

1. **Update Risk Register** - Mark RISK-001 and RISK-006 as FULLY MITIGATED
2. **Document in ISO 42001** - Update compliance status
3. **Schedule quarterly reviews** - Verify RLS policies are still active
4. **External security audit** - Have third party verify tenant isolation
5. **Automate verification** - Add RLS checks to CI/CD pipeline

---

## 11. Support & Contact

**Questions or issues?**
- **Technical Owner:** See docs/RAE-Roles.md
- **Security Contact:** See docs/RAE-Roles.md
- **Documentation:** This guide + docs/RAE-ISO_42001.md

**Emergency rollback decision tree:**
1. Data leak suspected? → Rollback immediately
2. Performance issue? → Investigate first, rollback if severe
3. Minor errors? → Fix in code, keep RLS enabled

---

## Appendix A: Migration Script Location

- **File:** `migrations/006_enable_row_level_security.sql`
- **Middleware:** `apps/memory_api/middleware/rls_context.py`
- **Tests:** `apps/memory_api/tests/test_rls_context.py` (to be created)

## Appendix B: Example RLS Policy

```sql
-- Example: Read-only policy for reporting users
CREATE POLICY reporting_readonly_memories ON memories
    FOR SELECT
    TO reporting_user
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```

This allows you to create specialized roles with limited permissions.
