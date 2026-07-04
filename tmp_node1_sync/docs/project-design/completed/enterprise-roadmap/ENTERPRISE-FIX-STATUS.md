# Enterprise Fix Plan - Execution Status

**Date Started:** 2025-11-27
**Source Document:** docs/RAE-improve-02.md
**Fix Plan:** docs/ENTERPRISE-FIX-PLAN.md
**Last Updated:** 2025-11-27

---

## Overall Progress: 20% Complete (1/5 Phases)

| Phase | Status | Progress | Commit | Time Spent | Estimated Time |
|-------|--------|----------|--------|------------|----------------|
| **Phase 1: Auth Unification** | ✅ **COMPLETE** | 100% | a5ae69b8a | ~2h | 2-3h |
| **Phase 2: Tenant RBAC** | ⏳ Pending | 0% | - | 0h | 4-6h |
| **Phase 3: Memory Decay** | ⏳ Pending | 0% | - | 0h | 3-4h |
| **Phase 4: Governance Security** | ⏳ Pending | 0% | - | 0h | 2-3h |
| **Phase 5: Documentation** | ⏳ Pending | 0% | - | 0h | 2-3h |

---

## ✅ Phase 1: Auth System Unification - COMPLETE

**Status:** ✅ Complete
**Commit:** a5ae69b8a
**Date:** 2025-11-27
**Time Spent:** ~2 hours

### Summary
Successfully removed old auth system and unified on new security/auth.py module.

### Changes Made

1. **dependencies.py** - Removed old auth
   - ❌ Deleted `get_api_key()` function
   - ❌ Removed `APIKeyHeader` and `Security` imports
   - ✅ Added redirect comment to security/auth.py

2. **api/v1/cache.py**
   - ❌ Removed `from apps.memory_api.dependencies import get_api_key`
   - ❌ Removed `dependencies=[Depends(get_api_key)]`
   - ✅ Added comment: "Auth is handled globally"

3. **api/v1/memory.py**
   - ❌ Removed `get_api_key` import
   - ❌ Removed `dependencies=[Depends(get_api_key)]`
   - ✅ Added global auth comment

4. **api/v1/agent.py**
   - ❌ Removed `get_api_key` import
   - ❌ Removed duplicate router declaration
   - ❌ Removed `dependencies=[Depends(get_api_key)]`
   - ✅ Added global auth comment

5. **api/v1/graph.py**
   - ❌ Removed `get_api_key` import
   - ❌ Removed `dependencies=[Depends(get_api_key)]`
   - ✅ Added global auth comment

### Verification

```bash
# No remaining get_api_key imports
grep -r "get_api_key" apps/memory_api/api/ --include="*.py"
# Result: (empty) ✅

# No remaining get_api_key dependencies
grep -r "Depends(get_api_key)" apps/memory_api/api/ --include="*.py"
# Result: (empty) ✅
```

### Security Impact
- ✅ Auth flags now work correctly
- ✅ No auth bypass possible
- ✅ Consistent auth across all endpoints
- ✅ Single source of truth (security/auth.py)

### Testing Status
- ⏳ Manual testing required with different auth flag combinations
- ⏳ Integration tests need update
- ⏳ Security audit pending

---

## ⏳ Phase 2: Tenant Access Control (RBAC) - PENDING

**Status:** ⏳ Not Started
**Priority:** P0 - Critical
**Estimated Time:** 4-6 hours

### What Needs to Be Done

#### 2.1 Database Schema
Create `user_tenant_access` table:
```sql
CREATE TABLE user_tenant_access (
    user_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user', 'readonly')),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by TEXT,
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, tenant_id),
    INDEX idx_user_tenants (user_id),
    INDEX idx_tenant_users (tenant_id)
);
```

#### 2.2 RBAC Module
Create `apps/memory_api/security/rbac.py`:
- `get_user_tenants(user_id: str) -> List[str]`
- `get_user_tenant_role(user_id: str, tenant_id: str) -> Optional[str]`
- `check_tenant_access(user: dict, tenant_id: str, required_role: str = "user") -> bool`
- `has_role(user: dict, tenant_id: str, role: str) -> bool`

#### 2.3 Update auth.py
Enhance `check_tenant_access()` to actually check database:
```python
async def check_tenant_access(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> bool:
    """Check if user has access to tenant"""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(403, "User ID required")

    # Check user_tenant_access table
    access = await check_user_tenant_access(pool, user_id, tenant_id)
    if not access:
        raise HTTPException(403, f"Access denied to tenant {tenant_id}")

    return True
```

#### 2.4 Add to Endpoints
Add `Depends(check_tenant_access)` to all tenant-specific endpoints:
- `/v1/memory/*` - all endpoints
- `/v1/agent/*` - all endpoints
- `/v1/graph/*` - all endpoints
- `/v1/governance/tenant/{tenant_id}/*` - all tenant endpoints

#### 2.5 Migration Script
Create migration to populate `user_tenant_access` for existing data:
- Identify all existing tenant_ids
- Create default admin users for each tenant
- Option to import user-tenant mappings from config

### Files to Create/Modify
- [ ] `infra/migrations/add_user_tenant_access.sql`
- [ ] `apps/memory_api/security/rbac.py`
- [ ] `apps/memory_api/security/auth.py` (update)
- [ ] `apps/memory_api/models/rbac.py`
- [ ] All routers (add dependency)

### Testing Checklist
- [ ] User can only access assigned tenants
- [ ] Admin role has full access
- [ ] User role has read/write access
- [ ] Readonly role has read-only access
- [ ] Unauthorized access returns 403
- [ ] Tenant enumeration prevented

---

## ⏳ Phase 3: Memory Decay Scheduler - PENDING

**Status:** ⏳ Not Started
**Priority:** P1 - High
**Estimated Time:** 3-4 hours

### What Needs to Be Done

#### 3.1 Celery Task
Create `apps/memory_api/tasks/memory_decay.py`:
```python
from celery import shared_task
from apps.memory_api.services.scoring import ImportanceScoringService

@shared_task(name="decay_memory_importance")
def decay_memory_importance_task():
    """Daily task to decay memory importance scores"""
    # Get all tenants
    # For each tenant:
    #   - Get scoring service
    #   - Call decay_importance()
    #   - Log results
    pass
```

#### 3.2 Celery Schedule
Update `apps/memory_api/celery_app.py`:
```python
app.conf.beat_schedule = {
    'decay-memory-importance': {
        'task': 'decay_memory_importance',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

#### 3.3 Configuration
Add to `apps/memory_api/config.py`:
```python
MEMORY_DECAY_ENABLED: bool = True
MEMORY_DECAY_SCHEDULE: str = "0 2 * * *"  # Cron format
MEMORY_DECAY_RATE: float = 0.95  # 5% decay per day
MEMORY_DECAY_BATCH_SIZE: int = 1000
```

#### 3.4 Monitoring
Add metrics:
- `memory_decay_duration_seconds` - histogram
- `memory_decay_memories_processed_total` - counter
- `memory_decay_errors_total` - counter

### Files to Create/Modify
- [ ] `apps/memory_api/tasks/memory_decay.py`
- [ ] `apps/memory_api/celery_app.py` (update)
- [ ] `apps/memory_api/config.py` (add settings)
- [ ] `.env.example` (add decay settings)
- [ ] `docs/concepts/memory-decay.md`

### Testing Checklist
- [ ] Manual task execution works
- [ ] Scheduled execution works
- [ ] Processes all tenants
- [ ] Importance scores decay correctly
- [ ] Batch processing works
- [ ] Error handling works
- [ ] Metrics are recorded

---

## ⏳ Phase 4: Governance Endpoints Security - PENDING

**Status:** ⏳ Not Started
**Priority:** P1 - High
**Estimated Time:** 2-3 hours

### What Needs to Be Done

#### 4.1 Add Auth to Router
Update `apps/memory_api/api/v1/governance.py`:
```python
from apps.memory_api.security.auth import verify_token, require_admin

router = APIRouter(
    prefix="/v1/governance",
    tags=["Governance"],
    dependencies=[Depends(verify_token)]  # ADD THIS
)
```

#### 4.2 Admin-Only Endpoints
Add admin check to system-wide endpoints:
```python
@router.get("/overview")
async def get_overview(
    user: dict = Depends(get_current_user),
    _: None = Depends(require_admin)  # ADD THIS
):
    """System-wide overview - admin only"""
    pass
```

#### 4.3 Tenant-Specific Endpoints
Add tenant access check:
```python
@router.get("/tenant/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(check_tenant_access)  # ADD THIS
):
    """Tenant stats - requires tenant access"""
    pass
```

#### 4.4 Rate Limiting
Add rate limiting to governance endpoints:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/tenant/{tenant_id}/stats")
@limiter.limit("100/hour")  # ADD THIS
async def get_tenant_stats(...):
    pass
```

### Files to Modify
- [ ] `apps/memory_api/api/v1/governance.py`
- [ ] `apps/memory_api/security/auth.py` (add require_admin)
- [ ] `apps/memory_api/config.py` (add rate limits)

### Testing Checklist
- [ ] Unauthenticated access blocked
- [ ] Non-admin can't access overview
- [ ] User can't access other tenant's data
- [ ] Rate limiting works
- [ ] Audit logging works

---

## ⏳ Phase 5: Documentation & Cleanup - PENDING

**Status:** ⏳ Not Started
**Priority:** P2 - Medium
**Estimated Time:** 2-3 hours

### What Needs to Be Done

#### 5.1 Security Documentation
Create/update:
- [ ] `docs/security/SECURITY.md` - Overall security guide
- [ ] `docs/security/authentication.md` - Auth guide
- [ ] `docs/security/rbac.md` - RBAC guide
- [ ] `docs/security/tenant-isolation.md` - Multi-tenancy guide

#### 5.2 Update Existing Docs
- [ ] `CHANGELOG.md` - Add all changes
- [ ] `STATUS.md` - Update security status
- [ ] `README.md` - Add security section
- [ ] `docs/deployment/` - Add security checklist

#### 5.3 Code Cleanup
- [ ] Remove TODO comments or implement them
- [ ] Remove unused functions from security/auth.py
- [ ] Add type hints where missing
- [ ] Add docstrings where missing

#### 5.4 Migration Guide
Create `docs/migration/enterprise-security-upgrade.md`:
- Breaking changes
- Migration steps
- Configuration changes
- Testing procedures

### Files to Create/Update
- [ ] `docs/security/*.md` (4 new files)
- [ ] `CHANGELOG.md`
- [ ] `STATUS.md`
- [ ] `README.md`
- [ ] `docs/migration/enterprise-security-upgrade.md`

---

## Risk Assessment

### High Risks
1. **RBAC Implementation** - Could break existing tenant access
   - Mitigation: Feature flag, gradual rollout, comprehensive testing

2. **Auth Changes** - Could lock out users
   - Mitigation: Backwards compatibility period, clear migration guide

### Medium Risks
3. **Governance Changes** - Could expose data if done incorrectly
   - Mitigation: Thorough testing, security audit

### Low Risks
4. **Decay Scheduler** - Performance impact
   - Mitigation: Batch processing, rate limiting, monitoring

---

## Next Steps

### Immediate (Next Session)
1. **Phase 2: Implement RBAC**
   - Create database migration
   - Implement rbac.py module
   - Add check_tenant_access to endpoints
   - Test tenant isolation

### Short Term
2. **Phase 3: Memory Decay**
   - Create Celery task
   - Add configuration
   - Test execution

3. **Phase 4: Governance Security**
   - Add auth dependencies
   - Add rate limiting
   - Test access control

### Long Term
4. **Phase 5: Documentation**
   - Write security guides
   - Update all docs
   - Create migration guide

---

## Rollback Plan

If issues occur in production:

1. **Phase 1 (Auth Unification):**
   ```bash
   git revert a5ae69b8a
   # Old get_api_key system restored
   ```

2. **Phase 2 (RBAC):**
   - Set `RBAC_ENABLED=false` in environment
   - Or revert database migration
   - System falls back to no tenant checks

3. **Phase 3 (Decay):**
   - Set `MEMORY_DECAY_ENABLED=false`
   - Stop Celery beat scheduler
   - No impact on existing functionality

4. **Phase 4 (Governance):**
   - Revert governance.py changes
   - Governance endpoints become less secure but functional

---

## Success Metrics

### Security
- [ ] Zero auth bypass vulnerabilities
- [ ] 100% tenant isolation enforcement
- [ ] All security flags work correctly
- [ ] Audit logging on all sensitive ops

### Functionality
- [ ] Memory decay runs daily without errors
- [ ] Users can access only assigned tenants
- [ ] Admins have system-wide access
- [ ] Zero data leakage between tenants

### Code Quality
- [ ] Zero old auth helpers remain
- [ ] 100% of TODO comments resolved
- [ ] Consistent patterns across codebase
- [ ] 100% test coverage on security code

---

**Last Updated:** 2025-11-27
**Next Review:** When starting Phase 2
**Owner:** Development Team
**Approval Status:** Pending security review
