"""
Permission checking logic.
Separated from models to avoid circular dependencies and keep models pure.
"""

from typing import Any, Optional, cast
from uuid import UUID


async def check_permission(
    user_id: str, tenant_id: UUID, action: str, project_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Check if user has permission to perform action.

    Returns:
        (allowed, denial_reason)
    """
    # Import here to avoid circular dependency
    from apps.memory_api.services.rbac_service import RBACService

    service = cast(Any, RBACService)(None)
    user_role = await service.get_user_role(user_id, tenant_id)

    if not user_role:
        return False, "User has no role in this tenant"

    if user_role.is_expired():
        return False, "Role assignment has expired"

    if project_id and not user_role.has_access_to_project(project_id):
        return False, f"No access to project {project_id}"

    if not user_role.can_perform(action):
        return False, f"Role {user_role.role.value} cannot perform {action}"

    return True, None


async def require_permission(
    user_id: str, tenant_id: UUID, action: str, project_id: Optional[str] = None
):
    """
    Decorator/function to require permission.
    Raises HTTPException if permission denied.
    """
    from fastapi import HTTPException, status

    allowed, reason = await check_permission(user_id, tenant_id, action, project_id)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission denied: {reason}"
        )
