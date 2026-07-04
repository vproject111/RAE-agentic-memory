"""
RBAC Service - Role-Based Access Control

Database-backed service for managing user roles and permissions.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import asyncpg
import structlog

from apps.memory_api.models.rbac import AccessLog, Role, UserRole

logger = structlog.get_logger(__name__)


class RBACService:
    """Service for managing roles and permissions using PostgreSQL"""

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize RBAC service with database connection pool.

        Args:
            pool: AsyncPG connection pool
        """
        self.pool = pool

    async def get_user_role(self, user_id: str, tenant_id: UUID) -> Optional[UserRole]:
        """
        Get user's role for tenant from database.

        Args:
            user_id: User identifier
            tenant_id: Tenant UUID

        Returns:
            UserRole if found, None otherwise
        """
        record = await self.pool.fetchrow(
            """
            SELECT id, user_id, tenant_id, role, project_ids,
                   assigned_at, assigned_by, expires_at
            FROM user_tenant_roles
            WHERE user_id = $1 AND tenant_id = $2
            """,
            user_id,
            str(tenant_id),
        )

        if not record:
            return None

        return UserRole(
            id=record["id"],
            user_id=record["user_id"],
            tenant_id=record["tenant_id"],
            role=Role(record["role"]),
            project_ids=record["project_ids"] or [],
            assigned_at=record["assigned_at"],
            assigned_by=record["assigned_by"],
            expires_at=record["expires_at"],
        )

    async def assign_role(
        self,
        user_id: str,
        tenant_id: UUID,
        role: Role,
        assigned_by: str,
        project_ids: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> UserRole:
        """
        Assign role to user in database.

        Args:
            user_id: User identifier
            tenant_id: Tenant UUID
            role: Role to assign
            assigned_by: Who is assigning the role
            project_ids: Optional list of project IDs for restricted access
            expires_at: Optional expiration timestamp

        Returns:
            Created UserRole
        """
        role_id = uuid4()
        assigned_at = datetime.now(timezone.utc)
        project_ids = project_ids or []

        await self.pool.execute(
            """
            INSERT INTO user_tenant_roles
            (id, user_id, tenant_id, role, project_ids, assigned_at, assigned_by, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, tenant_id)
            DO UPDATE SET
                role = EXCLUDED.role,
                project_ids = EXCLUDED.project_ids,
                assigned_at = EXCLUDED.assigned_at,
                assigned_by = EXCLUDED.assigned_by,
                expires_at = EXCLUDED.expires_at
            """,
            role_id,
            user_id,
            str(tenant_id),
            role.value,
            project_ids,
            assigned_at,
            assigned_by,
            expires_at,
        )

        logger.info(
            "role_assigned",
            user_id=user_id,
            tenant_id=str(tenant_id),
            role=role.value,
            assigned_by=assigned_by,
            expires_at=expires_at,
        )

        return UserRole(
            id=role_id,
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            project_ids=project_ids,
            assigned_at=assigned_at,
            assigned_by=assigned_by,
            expires_at=expires_at,
        )

    async def revoke_role(self, user_id: str, tenant_id: UUID):
        """
        Revoke user's role from database.

        Args:
            user_id: User identifier
            tenant_id: Tenant UUID
        """
        result = await self.pool.execute(
            """
            DELETE FROM user_tenant_roles
            WHERE user_id = $1 AND tenant_id = $2
            """,
            user_id,
            str(tenant_id),
        )

        logger.info(
            "role_revoked", user_id=user_id, tenant_id=str(tenant_id), result=result
        )

    async def list_tenant_users(self, tenant_id: UUID) -> List[UserRole]:
        """
        List all users with roles in tenant from database.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of UserRole objects
        """
        records = await self.pool.fetch(
            """
            SELECT id, user_id, tenant_id, role, project_ids,
                   assigned_at, assigned_by, expires_at
            FROM user_tenant_roles
            WHERE tenant_id = $1
            ORDER BY assigned_at DESC
            """,
            str(tenant_id),
        )

        return [
            UserRole(
                id=record["id"],
                user_id=record["user_id"],
                tenant_id=record["tenant_id"],
                role=Role(record["role"]),
                project_ids=record["project_ids"] or [],
                assigned_at=record["assigned_at"],
                assigned_by=record["assigned_by"],
                expires_at=record["expires_at"],
            )
            for record in records
        ]

    async def log_access(
        self,
        tenant_id: UUID,
        user_id: str,
        action: str,
        resource: str,
        allowed: bool,
        denial_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AccessLog:
        """
        Log access attempt for audit in database.

        Args:
            tenant_id: Tenant UUID
            user_id: User identifier
            action: Action attempted (e.g., "memories:read")
            resource: Resource type (e.g., "memories")
            allowed: Whether access was granted
            denial_reason: Reason for denial if applicable
            ip_address: Client IP address
            user_agent: Client user agent
            resource_id: Specific resource ID
            metadata: Additional metadata

        Returns:
            AccessLog entry
        """
        log_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        metadata = metadata or {}

        await self.pool.execute(
            """
            INSERT INTO access_logs
            (id, tenant_id, user_id, action, resource, resource_id,
             allowed, denial_reason, ip_address, user_agent, timestamp, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            log_id,
            str(tenant_id),
            user_id,
            action,
            resource,
            resource_id,
            allowed,
            denial_reason,
            ip_address,
            user_agent,
            timestamp,
            json.dumps(metadata),
        )

        logger.info(
            "access_logged",
            tenant_id=str(tenant_id),
            user_id=user_id,
            action=action,
            allowed=allowed,
            denial_reason=denial_reason,
        )

        return AccessLog(
            id=log_id,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            allowed=allowed,
            denial_reason=denial_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=timestamp,
            metadata=metadata,
        )
