# RAE Memory API - RBAC (Role-Based Access Control) Guide

**Last Updated:** 2025-11-27
**Version:** 1.0 (Phase 2 Implementation)

---

## Table of Contents

1. [Overview](#overview)
2. [Role Hierarchy](#role-hierarchy)
3. [Permission System](#permission-system)
4. [User Role Management](#user-role-management)
5. [API Endpoint Protection](#api-endpoint-protection)
6. [Implementation Examples](#implementation-examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

RAE Memory API implements a comprehensive Role-Based Access Control (RBAC) system that provides:

- **Tenant-level isolation**: Users can only access tenants they're explicitly assigned to
- **Role hierarchy**: 5 levels of access (Owner → Admin → Developer → Analyst → Viewer)
- **Permission granularity**: Action-level permissions (read, write, delete, manage)
- **Audit trail**: All access attempts are logged
- **Time-bound access**: Roles can expire automatically
- **Project-level restrictions**: Optional fine-grained access control

### Key Components

```
┌─────────────────────────────────────────────────────────┐
│  User Authentication (JWT / API Key)                    │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│  Tenant Access Check (check_tenant_access)              │
│  - User must have role in tenant                        │
│  - Role must not be expired                             │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│  Permission Check (require_permission)                  │
│  - User role must allow action                          │
│  - Optional: Project-level access                       │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│  Access Granted → Execute Request                        │
└─────────────────────────────────────────────────────────┘
```

---

## Role Hierarchy

### Role Levels

RAE Memory API defines 5 role levels with increasing privileges:

| Role      | Level | Description                                    | Typical Users        |
|-----------|-------|------------------------------------------------|----------------------|
| Owner     | 5     | Full control including tenant deletion         | Tenant creators      |
| Admin     | 4     | Manage users, settings, billing                | Team leads           |
| Developer | 3     | Full API access, read/write operations         | Engineers            |
| Analyst   | 2     | Analytics, read-only access, dashboard         | Data analysts        |
| Viewer    | 1     | Read-only access to memories                   | External stakeholders|

### Role Capabilities

#### 🔴 Owner (Level 5)

**Full Control:**
- Delete tenant
- Transfer ownership
- All admin capabilities

**Use Cases:**
- Tenant creator/founder
- Account owner
- Single point of authority

**Python Definition:**
```python
from apps.memory_api.models.rbac import Role

Role.OWNER  # level=5
```

#### 🟠 Admin (Level 4)

**Management:**
- Add/remove users
- Assign/revoke roles
- Configure tenant settings
- Manage billing and quotas
- View all analytics

**Cannot:**
- Delete tenant
- Change ownership

**Use Cases:**
- Team managers
- Operations staff
- Account administrators

**Python Definition:**
```python
Role.ADMIN  # level=4
```

#### 🟡 Developer (Level 3)

**API Access:**
- Create/update/delete memories
- Query memories
- Execute agent workflows
- Extract knowledge graphs
- Generate reflections

**Cannot:**
- Manage users
- Change settings
- View billing

**Use Cases:**
- Software engineers
- Integration developers
- API consumers

**Python Definition:**
```python
Role.DEVELOPER  # level=3
```

#### 🟢 Analyst (Level 2)

**Read-Only + Analytics:**
- View all memories (read-only)
- Access analytics dashboard
- View governance statistics
- Query historical data

**Cannot:**
- Modify any data
- Execute write operations

**Use Cases:**
- Data analysts
- Business intelligence
- Reporting staff

**Python Definition:**
```python
Role.ANALYST  # level=2
```

#### 🔵 Viewer (Level 1)

**Basic Read:**
- View memories
- Basic queries

**Cannot:**
- Modify data
- Access analytics
- View sensitive information

**Use Cases:**
- External auditors
- Temporary access
- Read-only integrations

**Python Definition:**
```python
Role.VIEWER  # level=1
```

---

## Permission System

### Permission Structure

Permissions follow the format: `resource:action`

**Resources:**
- `memories` - Memory records
- `users` - User management
- `settings` - Tenant configuration
- `billing` - Billing and quotas
- `analytics` - Analytics and reports
- `admin` - Administrative operations

**Actions:**
- `read` - View data
- `write` - Create/update data
- `delete` - Delete data
- `manage` - Full management (includes all actions)

### Permission Matrix

| Permission              | Owner | Admin | Developer | Analyst | Viewer |
|-------------------------|-------|-------|-----------|---------|--------|
| **Tenant Management**   |       |       |           |         |        |
| `tenant:delete`         | ✅    | ❌    | ❌        | ❌      | ❌     |
| `tenant:manage`         | ✅    | ✅    | ❌        | ❌      | ❌     |
| **User Management**     |       |       |           |         |        |
| `users:read`            | ✅    | ✅    | ❌        | ❌      | ❌     |
| `users:write`           | ✅    | ✅    | ❌        | ❌      | ❌     |
| `users:delete`          | ✅    | ✅    | ❌        | ❌      | ❌     |
| **Memory Operations**   |       |       |           |         |        |
| `memories:read`         | ✅    | ✅    | ✅        | ✅      | ✅     |
| `memories:write`        | ✅    | ✅    | ✅        | ❌      | ❌     |
| `memories:delete`       | ✅    | ✅    | ✅        | ❌      | ❌     |
| **Analytics**           |       |       |           |         |        |
| `analytics:read`        | ✅    | ✅    | ✅        | ✅      | ❌     |
| **Settings**            |       |       |           |         |        |
| `settings:read`         | ✅    | ✅    | ❌        | ❌      | ❌     |
| `settings:write`        | ✅    | ✅    | ❌        | ❌      | ❌     |
| **Billing**             |       |       |           |         |        |
| `billing:read`          | ✅    | ✅    | ❌        | ❌      | ❌     |
| `billing:write`         | ✅    | ✅    | ❌        | ❌      | ❌     |

### Permission Checking

```python
# apps/memory_api/models/rbac.py

class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    VIEWER = "viewer"

    @property
    def level(self) -> int:
        """Numeric level for comparison"""
        return {
            "owner": 5,
            "admin": 4,
            "developer": 3,
            "analyst": 2,
            "viewer": 1,
        }[self.value]

    def can_perform(self, action: str) -> bool:
        """Check if role can perform action"""
        permissions = {
            "owner": ["*"],  # All permissions
            "admin": [
                "tenant:manage", "users:*", "settings:*",
                "billing:*", "memories:*", "analytics:*"
            ],
            "developer": [
                "memories:*", "analytics:read"
            ],
            "analyst": [
                "memories:read", "analytics:*"
            ],
            "viewer": [
                "memories:read"
            ]
        }

        role_perms = permissions[self.value]

        # Wildcard match
        if "*" in role_perms:
            return True

        # Exact match or wildcard resource
        resource, perm = action.split(":")
        return (
            action in role_perms or
            f"{resource}:*" in role_perms
        )
```

---

## User Role Management

### Database Schema

```sql
CREATE TABLE user_tenant_roles (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    tenant_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'developer', 'analyst', 'viewer')),

    -- Optional restrictions
    project_ids TEXT[],  -- Empty = access all projects

    -- Metadata
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by TEXT,
    expires_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT user_tenant_roles_unique UNIQUE (user_id, tenant_id)
);
```

### Assigning Roles

#### Using RBACService

```python
from uuid import UUID
from apps.memory_api.services.rbac_service import RBACService
from apps.memory_api.models.rbac import Role

# Initialize service
rbac_service = RBACService(pool)

# Assign role
user_role = await rbac_service.assign_role(
    user_id="user_123",
    tenant_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
    role=Role.DEVELOPER,
    assigned_by="admin_456",
    project_ids=[],  # Empty = access all projects
    expires_at=None  # None = never expires
)

print(f"Assigned {user_role.role.value} to {user_role.user_id}")
```

#### Time-Limited Access

```python
from datetime import datetime, timedelta, timezone

# Grant 30-day access
expires_at = datetime.now(timezone.utc) + timedelta(days=30)

user_role = await rbac_service.assign_role(
    user_id="contractor_789",
    tenant_id=tenant_uuid,
    role=Role.ANALYST,
    assigned_by="admin_456",
    expires_at=expires_at
)
```

#### Project-Restricted Access

```python
# Grant access only to specific projects
user_role = await rbac_service.assign_role(
    user_id="external_user",
    tenant_id=tenant_uuid,
    role=Role.VIEWER,
    assigned_by="admin_456",
    project_ids=["project_alpha", "project_beta"]  # Limited scope
)
```

### Revoking Roles

```python
# Remove user from tenant
await rbac_service.revoke_role(
    user_id="user_123",
    tenant_id=tenant_uuid
)
```

### Listing Tenant Users

```python
# Get all users with roles in tenant
users = await rbac_service.list_tenant_users(tenant_uuid)

for user_role in users:
    print(f"{user_role.user_id}: {user_role.role.value}")
    if user_role.expires_at:
        print(f"  Expires: {user_role.expires_at}")
    if user_role.project_ids:
        print(f"  Projects: {', '.join(user_role.project_ids)}")
```

---

## API Endpoint Protection

### Protecting Endpoints with Dependencies

#### 1. Tenant Access Verification

```python
from fastapi import APIRouter, Depends
from apps.memory_api.security.dependencies import verify_tenant_access

router = APIRouter()

@router.get("/tenant/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: str,
    _: bool = Depends(verify_tenant_access),  # ← Enforces tenant access
):
    """
    User must have ANY role in this tenant to access.
    Returns 403 if user has no role or role is expired.
    """
    return {"tenant_id": tenant_id, "stats": "..."}
```

#### 2. Header-Based Tenant ID

```python
from apps.memory_api.security.dependencies import get_and_verify_tenant_id

@router.post("/memories")
async def create_memory(
    tenant_id: str = Depends(get_and_verify_tenant_id),  # ← Extracts from X-Tenant-Id header
):
    """
    Automatically extracts tenant_id from X-Tenant-Id header
    and verifies user has access.
    """
    return {"tenant_id": tenant_id}
```

#### 3. Permission-Based Protection

```python
from apps.memory_api.security.dependencies import require_action

@router.delete("/tenant/{tenant_id}/memories/{memory_id}")
async def delete_memory(
    tenant_id: str,
    memory_id: str,
    _: bool = Depends(require_action("memories:delete")),  # ← Requires specific permission
):
    """
    Only users with memories:delete permission can access.
    Owner, Admin, Developer: ✅
    Analyst, Viewer: ❌ (403 Forbidden)
    """
    return {"deleted": memory_id}
```

#### 4. Role-Level Protection

```python
from apps.memory_api.security.dependencies import require_tenant_role

@router.post("/tenant/{tenant_id}/users")
async def add_user(
    tenant_id: str,
    _: bool = Depends(require_tenant_role("admin")),  # ← Requires admin or higher
):
    """
    Only Owner and Admin can access.
    Developer, Analyst, Viewer: ❌ (403 Forbidden)
    """
    return {"message": "User added"}
```

#### 5. System Admin Protection

```python
from apps.memory_api.security.dependencies import require_admin

@router.get("/admin/overview")
async def admin_overview(
    _: bool = Depends(require_admin),  # ← System-wide admin check
):
    """
    Reserved for system administrators.
    Checks system-level admin status (not tenant-specific).
    """
    return {"overview": "..."}
```

### Router-Level Protection

Apply authentication to all endpoints in a router:

```python
from apps.memory_api.security import auth

router = APIRouter(
    prefix="/governance",
    tags=["Governance"],
    dependencies=[Depends(auth.verify_token)],  # ← All endpoints require auth
)
```

---

## Implementation Examples

### Example 1: Complete Endpoint Protection

```python
from fastapi import APIRouter, Depends, Request
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import (
    get_and_verify_tenant_id,
    require_action,
)

router = APIRouter(
    prefix="/memory",
    tags=["memory-protocol"],
    dependencies=[Depends(auth.verify_token)],  # All endpoints require auth
)

@router.post("/store")
async def store_memory(
    request: Request,
    tenant_id: str = Depends(get_and_verify_tenant_id),  # Verify tenant access
):
    """
    1. Auth check (router level)
    2. Tenant access check (dependency)
    3. Permission check (implicit via role)
    """
    # User is authenticated and has access to tenant
    # Store memory logic...
    return {"status": "stored", "tenant_id": tenant_id}


@router.delete("/delete")
async def delete_memory(
    memory_id: str,
    request: Request,
    tenant_id: str = Depends(get_and_verify_tenant_id),
    _: bool = Depends(require_action("memories:delete")),  # Explicit permission
):
    """
    1. Auth check (router level)
    2. Tenant access check (get_and_verify_tenant_id)
    3. Permission check (require_action)

    Only Developer+ can delete memories.
    """
    # Delete memory logic...
    return {"deleted": memory_id}
```

### Example 2: User Management Endpoint

```python
from apps.memory_api.security.dependencies import require_tenant_role

@router.delete("/tenant/{tenant_id}/user/{user_id}")
async def remove_user(
    tenant_id: str,
    user_id: str,
    _: bool = Depends(require_tenant_role("admin")),  # Admin or Owner only
):
    """
    Remove user from tenant.
    Requires admin role or higher.
    """
    rbac_service = RBACService(request.app.state.pool)

    await rbac_service.revoke_role(
        user_id=user_id,
        tenant_id=UUID(tenant_id)
    )

    return {"message": f"User {user_id} removed from tenant"}
```

### Example 3: Programmatic Access Check

```python
async def check_user_access(request: Request, tenant_id: str, action: str):
    """
    Programmatic access check within business logic
    """
    from apps.memory_api.security import auth

    # Get user ID
    user_id = await auth.get_user_id_from_token(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Check permission
    try:
        await auth.require_permission(request, tenant_id, action)
        return True
    except HTTPException:
        return False
```

---

## Best Practices

### 1. Principle of Least Privilege

Grant the minimum role necessary for users to perform their tasks:

```python
# ✅ Good: Specific role for task
await rbac_service.assign_role(
    user_id="analyst_user",
    tenant_id=tenant_uuid,
    role=Role.ANALYST  # Read-only + analytics
)

# ❌ Bad: Excessive permissions
await rbac_service.assign_role(
    user_id="analyst_user",
    tenant_id=tenant_uuid,
    role=Role.ADMIN  # Unnecessary admin access
)
```

### 2. Use Time-Limited Access for Contractors

```python
# 90-day contractor access
expires_at = datetime.now(timezone.utc) + timedelta(days=90)

await rbac_service.assign_role(
    user_id="contractor",
    tenant_id=tenant_uuid,
    role=Role.DEVELOPER,
    expires_at=expires_at
)
```

### 3. Project-Level Restrictions for Sensitive Data

```python
# Restrict external user to non-sensitive projects
await rbac_service.assign_role(
    user_id="external_partner",
    tenant_id=tenant_uuid,
    role=Role.VIEWER,
    project_ids=["public_project"]  # Cannot access other projects
)
```

### 4. Audit Role Changes

```python
# Always include assigned_by for audit trail
await rbac_service.assign_role(
    user_id="new_dev",
    tenant_id=tenant_uuid,
    role=Role.DEVELOPER,
    assigned_by=current_user_id  # ← Track who made the change
)
```

### 5. Regular Access Reviews

```sql
-- Query: Find users with expiring roles (next 7 days)
SELECT user_id, tenant_id, role, expires_at
FROM user_tenant_roles
WHERE expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'
ORDER BY expires_at;

-- Query: Find users who haven't accessed tenant in 90 days
SELECT utr.user_id, utr.tenant_id, utr.role,
       MAX(al.timestamp) as last_access
FROM user_tenant_roles utr
LEFT JOIN access_logs al ON utr.user_id = al.user_id
                         AND utr.tenant_id = al.tenant_id
GROUP BY utr.user_id, utr.tenant_id, utr.role
HAVING MAX(al.timestamp) < NOW() - INTERVAL '90 days'
   OR MAX(al.timestamp) IS NULL;
```

---

## Troubleshooting

### Common Issues

#### 1. "Access denied: You don't have access to this tenant"

**Cause:** User has no role in the tenant

**Solution:**
```python
# Assign role to user
await rbac_service.assign_role(
    user_id="user_123",
    tenant_id=tenant_uuid,
    role=Role.DEVELOPER,
    assigned_by="admin"
)
```

#### 2. "Access denied: Your access to this tenant has expired"

**Cause:** Role assignment has expired

**Solution:**
```python
# Extend expiration or remove expiration
await rbac_service.assign_role(
    user_id="user_123",
    tenant_id=tenant_uuid,
    role=Role.DEVELOPER,
    assigned_by="admin",
    expires_at=None  # Never expires
)
```

#### 3. "Permission denied: Role developer cannot perform users:delete"

**Cause:** User's role doesn't have required permission

**Solution:**
```python
# Upgrade role if appropriate
await rbac_service.assign_role(
    user_id="user_123",
    tenant_id=tenant_uuid,
    role=Role.ADMIN,  # Admin can manage users
    assigned_by="owner"
)
```

#### 4. "Invalid tenant ID format"

**Cause:** Tenant ID is not a valid UUID

**Solution:**
```python
from uuid import UUID

# Ensure tenant_id is valid UUID
try:
    tenant_uuid = UUID(tenant_id)
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid tenant ID format")
```

### Debugging Access Issues

```sql
-- Check user's role in tenant
SELECT * FROM user_tenant_roles
WHERE user_id = 'user_123'
AND tenant_id = '550e8400-e29b-41d4-a716-446655440000';

-- Check recent access logs for user
SELECT * FROM access_logs
WHERE user_id = 'user_123'
ORDER BY timestamp DESC
LIMIT 20;

-- Find all denied access attempts
SELECT * FROM access_logs
WHERE allowed = false
AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

---

## Related Documentation

- [Security Overview](SECURITY.md) - Complete security architecture
- [Authentication Guide](authentication.md) - Authentication configuration
- [API Reference](../api-reference.md) - Endpoint documentation

---

**For RBAC questions or issues, please refer to the security team or file an issue in the repository.**
