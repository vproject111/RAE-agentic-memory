"""
Role-Based Access Control (RBAC) models
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    """User roles in order of privilege"""

    OWNER = "owner"  # Full access, can delete tenant
    ADMIN = "admin"  # Manage users, settings, billing
    DEVELOPER = "developer"  # Full API access, read/write memories
    ANALYST = "analyst"  # Analytics and read-only access
    VIEWER = "viewer"  # Read-only access

    @property
    def level(self) -> int:
        """Get numeric privilege level"""
        levels = {
            Role.OWNER: 5,
            Role.ADMIN: 4,
            Role.DEVELOPER: 3,
            Role.ANALYST: 2,
            Role.VIEWER: 1,
        }
        return levels[self]

    def can_perform(self, action: str) -> bool:
        """Check if role can perform action"""
        permissions = {
            Role.OWNER: ["*"],  # All actions
            Role.ADMIN: [
                "users:read",
                "users:write",
                "users:delete",
                "settings:read",
                "settings:write",
                "billing:read",
                "billing:write",
                "memories:read",
                "memories:write",
                "memories:delete",
                "analytics:read",
            ],
            Role.DEVELOPER: [
                "memories:read",
                "memories:write",
                "memories:delete",
                "graph:read",
                "graph:write",
                "reflections:read",
                "reflections:write",
                "analytics:read",
            ],
            Role.ANALYST: ["memories:read", "analytics:read", "graph:read"],
            Role.VIEWER: ["memories:read"],
        }

        role_perms = permissions.get(self, [])

        # Owner has all permissions
        if "*" in role_perms:
            return True

        return action in role_perms or action.split(":")[0] + ":*" in role_perms


class Permission(BaseModel):
    """Individual permission"""

    resource: str = Field(
        ..., description="Resource type (memories, users, settings, etc.)"
    )
    action: str = Field(..., description="Action (read, write, delete)")

    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"


class UserRole(BaseModel):
    """User role assignment"""

    id: UUID
    user_id: str = Field(..., description="User identifier")
    tenant_id: UUID = Field(..., description="Tenant this role applies to")
    role: Role = Field(..., description="Assigned role")

    # Scope restrictions (optional)
    project_ids: List[str] = Field(
        default_factory=list, description="Restrict to specific projects (empty = all)"
    )

    # Metadata
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_by: Optional[str] = Field(None, description="Who assigned this role")
    expires_at: Optional[datetime] = Field(
        None, description="Role expiration (optional)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user_123",
                "tenant_id": "tenant_abc",
                "role": "developer",
                "project_ids": [],
            }
        }
    )

    def is_expired(self) -> bool:
        """Check if role assignment has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def has_access_to_project(self, project_id: str) -> bool:
        """Check if user has access to specific project"""
        # Empty list means access to all projects
        if not self.project_ids:
            return True
        return project_id in self.project_ids

    def can_perform(self, action: str, project_id: Optional[str] = None) -> bool:
        """Check if user can perform action"""
        # Check expiration
        if self.is_expired():
            return False

        # Check project access
        if project_id and not self.has_access_to_project(project_id):
            return False

        # Check role permissions
        return self.role.can_perform(action)


class RoleHierarchy:
    """Helper class for role hierarchy checks"""

    @staticmethod
    def is_higher_or_equal(role1: Role, role2: Role) -> bool:
        """Check if role1 >= role2 in hierarchy"""
        return role1.level >= role2.level

    @staticmethod
    def can_assign_role(assigner_role: Role, target_role: Role) -> bool:
        """Check if assigner can assign target role"""
        # Owners can assign any role
        if assigner_role == Role.OWNER:
            return True

        # Admins can assign roles below them
        if assigner_role == Role.ADMIN:
            return target_role.level < Role.ADMIN.level

        # Others cannot assign roles
        return False

    @staticmethod
    def can_modify_user(modifier_role: Role, target_user_role: Role) -> bool:
        """Check if modifier can modify target user"""
        # Can only modify users with lower role
        return modifier_role.level > target_user_role.level


class AccessLog(BaseModel):
    """Audit log entry for access control"""

    id: UUID
    tenant_id: UUID
    user_id: str
    action: str
    resource: str
    resource_id: Optional[str] = None

    # Result
    allowed: bool
    denial_reason: Optional[str] = None

    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    metadata: dict = Field(default_factory=dict)
