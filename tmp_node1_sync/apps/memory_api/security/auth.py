"""
Authentication and Authorization Module

Provides API key authentication and optional JWT token verification.
"""

from typing import Optional, cast
from uuid import UUID

import structlog
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from apps.memory_api.config import settings

logger = structlog.get_logger(__name__)

# Security schemes
security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[str]:
    """
    Verify API key from X-API-Key header.

    Args:
        api_key: API key from header

    Returns:
        API key if valid, None if API key authentication is disabled

    Raises:
        HTTPException: If API key is invalid or missing when required
    """
    # If API key authentication is disabled, skip verification
    if not settings.ENABLE_API_KEY_AUTH:
        return None

    # If API key is missing
    if not api_key:
        logger.warning("missing_api_key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is required. Please provide X-API-Key header.",
        )

    # Verify API key
    if api_key != settings.API_KEY:
        logger.warning("invalid_api_key", provided_key=api_key[:10] + "...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
        )

    return api_key


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    api_key: Optional[str] = Security(api_key_header),
) -> dict:
    """
    Verify authentication token (Bearer token or API key).

    Supports two authentication methods:
    1. Bearer token (JWT) in Authorization header
    2. API key in X-API-Key header

    Args:
        credentials: Bearer token credentials
        api_key: API key from header

    Returns:
        User information dictionary

    Raises:
        HTTPException: If authentication fails
    """
    # Try API key first
    if api_key:
        try:
            await verify_api_key(api_key)
            return {"authenticated": True, "method": "api_key"}
        except HTTPException:
            pass

    # Try Bearer token
    if credentials:
        token = credentials.credentials

        # If JWT auth is disabled, we can still use the token for non-verified identity
        if not settings.ENABLE_JWT_AUTH:
            return {"authenticated": True, "method": "bearer", "token": token}

        # --- JWT Verification Logic ---
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
        from jose import JWTError, jwt

        # 1. Try Google OIDC token verification
        try:
            # The audience should be set in the .env file as OAUTH_AUDIENCE.
            # This is typically the OAuth client ID of your application.
            # If not set, audience validation is skipped (less secure).
            audience = settings.OAUTH_AUDIENCE if settings.OAUTH_AUDIENCE else None
            decoded_token = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=audience,
                clock_skew_in_seconds=10,
            )

            if "sub" not in decoded_token:
                raise ValueError("Google token is missing 'sub' (subject) claim.")

            logger.info(
                "google_jwt_verification_succeeded", user_id=decoded_token["sub"]
            )
            return {
                "authenticated": True,
                "method": "google_jwt",
                "user_id": decoded_token["sub"],
                "email": decoded_token.get("email"),
                "token": token,
                "claims": decoded_token,
            }
        except ValueError as e:
            # This catches failures from id_token.verify_oauth2_token
            logger.debug("google_jwt_verification_failed", error=str(e), exc_info=True)
            # If Google token verification fails, fall through to internal verification
            pass
        except Exception as e:
            logger.error("unexpected_google_auth_error", error=str(e), exc_info=True)
            # Fall through for safety, in case of unexpected google lib errors

        # 2. Try internal JWT verification (using SECRET_KEY)
        try:
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

            if "sub" not in decoded:
                raise JWTError("Internal token missing 'sub' (subject) claim.")

            logger.info("internal_jwt_verification_succeeded", user_id=decoded["sub"])
            return {
                "authenticated": True,
                "method": "internal_jwt",
                "user_id": decoded["sub"],
                "email": decoded.get("email"),
                "token": token,
                "claims": decoded,
            }
        except JWTError as e:
            logger.warning("internal_jwt_verification_failed", error=str(e))
            # If both Google and internal JWT verification fail, raise the final error
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # If both API key and token authentication are disabled, allow access but as unauthenticated
    if not settings.ENABLE_API_KEY_AUTH and not settings.ENABLE_JWT_AUTH:
        return {"authenticated": False, "method": "none"}

    # No valid authentication method was provided (no API key, no Bearer token)
    logger.warning("authentication_required_no_credentials")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either a Bearer token or an X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(request: Request) -> dict:
    """
    Get current authenticated user from request state.

    Args:
        request: FastAPI request object

    Returns:
        User information dictionary
    """
    if hasattr(request.state, "user"):
        return cast(dict, request.state.user)

    return {"authenticated": False}


async def get_user_id_from_token(request: Request) -> Optional[str]:
    """
    Extract user ID from authentication token.

    Args:
        request: FastAPI request object

    Returns:
        User ID if authenticated, None otherwise
    """
    # Try to get from request state first
    if hasattr(request.state, "user"):
        user = cast(dict, request.state.user)
        if user.get("user_id"):
            return str(user["user_id"])

    # Try to extract from token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

        # If JWT is enabled, decode it to get the real user_id
        if settings.ENABLE_JWT_AUTH:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token
            from jose import JWTError, jwt

            # 1. Try Google OIDC token to extract user ID
            try:
                audience = settings.OAUTH_AUDIENCE if settings.OAUTH_AUDIENCE else None
                decoded_token = id_token.verify_oauth2_token(
                    token,
                    google_requests.Request(),
                    audience=audience,
                    clock_skew_in_seconds=10,
                )
                user_id_val = decoded_token.get("sub")
                if user_id_val:
                    return str(user_id_val)
            except ValueError:
                # If Google token verification fails, fall through to internal verification
                pass
            except Exception:
                # Catch any other unexpected errors from Google's lib and fall through
                pass

            # 2. Try internal JWT to extract user ID
            try:
                decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id_val = decoded.get("sub")
                return str(user_id_val) if user_id_val is not None else None
            except JWTError:
                return None  # Both Google and internal JWT failed

        # Fallback for testing/non-JWT mode: use token hash
        import hashlib

        return cast(str, hashlib.sha256(token.encode()).hexdigest()[:32])

    # Try API key as user identifier
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey_{api_key[:20]}"

    # Fallback to X-User-Id header for dev/testing
    user_id_header = request.headers.get("X-User-Id")
    if user_id_header:
        return user_id_header

    return None


async def check_tenant_access(
    request: Request,
    tenant_id: UUID,
) -> bool:
    """
    Check if user has access to specific tenant using RBAC.

    Args:
        request: FastAPI request object
        tenant_id: Tenant ID to check access for

    Returns:
        True if user has access

    Raises:
        HTTPException: If user doesn't have access
    """
    # If tenancy is disabled, allow access
    if not settings.TENANCY_ENABLED:
        logger.debug(
            "check_tenant_access_bypassed_tenancy_disabled", tenant_id=tenant_id
        )
        return True

    from apps.memory_api.services.rbac_service import RBACService

    # Get user ID from authentication
    user_id = await get_user_id_from_token(request)
    if not user_id:
        logger.warning("check_tenant_access_no_user_id", tenant_id=tenant_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access tenant",
        )

    # Get database pool from app state
    if not hasattr(request.app.state, "pool"):
        logger.error("check_tenant_access_no_pool", tenant_id=tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )

    # Check RBAC
    rbac_service = RBACService(request.app.state.pool)
    logger.info(
        "checking_rbac_role",
        user_id=user_id,
        tenant_id=tenant_id,
    )
    user_role = await rbac_service.get_user_role(user_id, tenant_id)

    if not user_role:
        logger.warning(
            "check_tenant_access_denied",
            user_id=user_id,
            tenant_id=tenant_id,
            reason="no_role",
        )
        # Log access attempt
        await rbac_service.log_access(
            tenant_id=tenant_id,
            user_id=user_id,
            action="tenant:access",
            resource="tenant",
            allowed=False,
            denial_reason="User has no role in this tenant",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't have access to this tenant",
        )

    # Check if role is expired
    if user_role.is_expired():
        logger.warning(
            "check_tenant_access_denied",
            user_id=user_id,
            tenant_id=tenant_id,
            reason="role_expired",
        )
        await rbac_service.log_access(
            tenant_id=tenant_id,
            user_id=user_id,
            action="tenant:access",
            resource="tenant",
            allowed=False,
            denial_reason="Role assignment has expired",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Your access to this tenant has expired",
        )

    # Log successful access
    await rbac_service.log_access(
        tenant_id=tenant_id,
        user_id=user_id,
        action="tenant:access",
        resource="tenant",
        allowed=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(
        "check_tenant_access_granted",
        user_id=user_id,
        tenant_id=tenant_id,
        role=user_role.role.value,
    )

    return True


async def require_permission(
    request: Request,
    tenant_id: UUID,
    action: str,
    project_id: Optional[str] = None,
) -> bool:
    """
    Check if user has specific permission to perform action.

    Args:
        request: FastAPI request object
        tenant_id: Tenant ID
        action: Action to check (e.g., "memories:write", "users:delete")
        project_id: Optional project ID for project-scoped permissions

    Returns:
        True if permission granted

    Raises:
        HTTPException: If permission denied
    """
    from apps.memory_api.services.rbac_service import RBACService

    # Get user ID from authentication
    user_id = await get_user_id_from_token(request)
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

    # Check permission
    rbac_service = RBACService(request.app.state.pool)
    user_role = await rbac_service.get_user_role(user_id, tenant_id)

    if not user_role:
        await rbac_service.log_access(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=action.split(":")[0],
            allowed=False,
            denial_reason="User has no role in this tenant",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't have access to this tenant",
        )

    # Check if can perform action
    if not user_role.can_perform(action, project_id):
        denial_reason = f"Role {user_role.role.value} cannot perform {action}"
        if project_id and not user_role.has_access_to_project(project_id):
            denial_reason = f"No access to project {project_id}"

        await rbac_service.log_access(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=action.split(":")[0],
            allowed=False,
            denial_reason=denial_reason,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {denial_reason}",
        )

    # Log successful access
    await rbac_service.log_access(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource=action.split(":")[0],
        allowed=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(
        "permission_granted",
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        role=user_role.role.value,
    )

    return True
