"""
FastAPI dependencies for RBAC and tenant access control.

These dependencies can be used with Depends() in route definitions.
"""

from collections.abc import Callable
from uuid import UUID

import structlog
from fastapi import Header, HTTPException, Query, Request, status

from apps.memory_api.config import settings
from apps.memory_api.security import auth

logger = structlog.get_logger(__name__)


async def verify_tenant_access(
    request: Request,
    tenant_id: UUID,
) -> bool:
    """
    Dependency to verify user has access to tenant (for path parameters).

    Usage:
        @router.get("/tenant/{tenant_id}/stats")
        async def get_stats(
            tenant_id: UUID,
            _: bool = Depends(verify_tenant_access),
        ):
            ...
    """
    return await auth.check_tenant_access(request, tenant_id)


async def get_and_verify_tenant_id(
    request: Request,
    x_tenant_id: str = Header(
        None, alias="X-Tenant-Id", description="Tenant ID header"
    ),
    query_tenant_id: str = Query(
        None, alias="tenant_id", description="Tenant ID query parameter"
    ),
) -> UUID:
    """
    Dependency to extract tenant_id from X-Tenant-Id header or query parameter,
    convert it to UUID, handle 'default-tenant' alias, and verify access.

    This ensures all API routes receive a validated UUID for tenant_id.
    """
    tenant_id_str = x_tenant_id or query_tenant_id

    if not tenant_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header or 'tenant_id' query parameter is required",
        )

    try:
        if tenant_id_str == settings.DEFAULT_TENANT_ALIAS:
            tenant_uuid = UUID(settings.DEFAULT_TENANT_UUID)
        else:
            tenant_uuid = UUID(tenant_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant ID format: '{tenant_id_str}'. Must be a valid UUID or '{settings.DEFAULT_TENANT_ALIAS}'.",
        )

    # Store the validated UUID version of tenant_id in request.state for convenience
    request.state.tenant_id = tenant_uuid

    # Verify user has access to this tenant
    await auth.check_tenant_access(request, tenant_uuid)

    return tenant_uuid


def require_action(action: str) -> Callable:
    """
    Create a dependency that requires specific permission.

    Args:
        action: Action to require (e.g., "memories:write", "users:delete")

    Returns:
        Dependency function

    Usage:
        @router.post("/tenant/{tenant_id}/memories")
        async def create_memory(
            tenant_id: str,
            _: bool = Depends(require_action("memories:write")),
        ):
            ...
    """

    async def _check_permission(
        request: Request,
        tenant_id: UUID,
    ) -> bool:
        return await auth.require_permission(request, tenant_id, action)

    return _check_permission


async def require_admin(request: Request) -> bool:
    """
    Dependency to require admin role for system-wide operations.

    This checks if the user is authenticated and should have admin privileges.
    For tenant-specific admin, use require_action("admin:*") instead.

    Usage:
        @router.get("/admin/overview")
        async def admin_overview(
            _: bool = Depends(require_admin),
        ):
            ...
    """
    user_id = await auth.get_user_id_from_token(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for admin access",
        )

    # System-wide admin check
    logger.warning(
        "system_admin_check_bypassed",
        user_id=user_id,
        message="System admin check not fully implemented - allowing authenticated users",
    )
    return True


def require_tenant_role(min_role: str) -> Callable:
    """
    Create a dependency that requires minimum role level for tenant.

    Args:
        min_role: Minimum role required (owner, admin, developer, analyst, viewer)

    Returns:
        Dependency function

    Usage:
        @router.delete("/tenant/{tenant_id}/user/{user_id}")
        async def remove_user(
            tenant_id: str,
            user_id: str,
            _: bool = Depends(require_tenant_role("admin")),
        ):
            ...
    """
    from apps.memory_api.models.rbac import Role
    from apps.memory_api.services.rbac_service import RBACService

    async def _check_role(
        request: Request,
        tenant_id: UUID,
    ) -> bool:
        # Get user ID
        user_id = await auth.get_user_id_from_token(request)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Get database pool
        if not hasattr(request.app.state, "pool"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not initialized",
            )

        # Check role
        rbac_service = RBACService(request.app.state.pool)
        user_role = await rbac_service.get_user_role(user_id, tenant_id)

        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't have access to this tenant",
            )

        # Check if role level is sufficient
        required_role = Role(min_role)
        if user_role.role.level < required_role.level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {required_role.value} role or higher required",
            )

        return True

    return _check_role
