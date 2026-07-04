"""
Row-Level Security (RLS) Context Middleware - ISO/IEC 42001 Compliance

Sets PostgreSQL session context for Row-Level Security policies to enforce
tenant isolation at the database level.

This middleware MUST be called for every request to ensure proper tenant isolation.
If tenant_id is not set, RLS policies will block all data access (fail-safe).

ISO/IEC 42001 alignment:
- Mitigates RISK-001: Wyciek danych wrażliwych (defense in depth)
- Mitigates RISK-006: Mieszanie wiedzy z wielu tenantów
- Section 6: Risk management (technical controls)
- Section 8: Information security (data segregation)
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RLSContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set PostgreSQL RLS context for tenant isolation

    Sets app.current_tenant_id session variable in PostgreSQL which is
    used by Row-Level Security policies to filter queries per tenant.

    CRITICAL: This middleware must run AFTER TenantContextMiddleware
    so that request.state.tenant_id is already set.
    """

    async def dispatch(self, request: Request, call_next):
        """Set RLS context for the request"""

        tenant_id: Optional[str] = getattr(request.state, "tenant_id", None)

        # Skip RLS for certain endpoints (health checks, public endpoints)
        skip_paths = ["/health", "/docs", "/openapi.json", "/metrics"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # If no tenant_id, log warning and continue (RLS will block access)
        if not tenant_id:
            logger.warning(
                "rls_context_missing_tenant",
                path=request.url.path,
                method=request.method,
                message="No tenant_id in request state. RLS will block data access.",
            )
            # Continue anyway - RLS will enforce security
            return await call_next(request)

        # Validate tenant_id is a valid UUID
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, AttributeError) as e:
            logger.error(
                "rls_context_invalid_tenant",
                tenant_id=tenant_id,
                error=str(e),
                message="Invalid tenant_id format. RLS will block data access.",
            )
            # Continue anyway - RLS will enforce security
            return await call_next(request)

        # Get database pool from app state
        pool: Optional[asyncpg.Pool] = getattr(request.app.state, "db_pool", None)

        if not pool:
            logger.warning(
                "rls_context_no_pool",
                message="Database pool not available. Cannot set RLS context.",
            )
            return await call_next(request)

        # Set RLS context in PostgreSQL session
        try:
            async with pool.acquire() as conn:
                # Store connection in request state so it can be reused
                # This ensures RLS context persists for the entire request
                request.state.db_connection = conn

                # Set tenant context using our helper function
                await conn.execute("SELECT set_current_tenant($1)", tenant_uuid)

                logger.debug(
                    "rls_context_set",
                    tenant_id=str(tenant_uuid),
                    path=request.url.path,
                    method=request.method,
                )

                # Process request
                response = await call_next(request)

                # Clear tenant context after request (cleanup)
                try:
                    await conn.execute("SELECT clear_current_tenant()")
                except Exception as e:
                    logger.warning(
                        "rls_context_clear_failed",
                        error=str(e),
                        message="Failed to clear RLS context. Not critical.",
                    )

                return response

        except Exception as e:
            logger.error(
                "rls_context_error",
                tenant_id=str(tenant_uuid),
                error=str(e),
                message="Failed to set RLS context. Request will fail-safe (no data access).",
            )
            # Continue anyway - RLS will block access as fail-safe
            return await call_next(request)


async def set_rls_context_for_background_task(pool: asyncpg.Pool, tenant_id: str):
    """
    Set RLS context for background tasks (Celery workers)

    Background tasks don't have HTTP request context, so we need to
    set RLS context explicitly for each task.

    Usage in Celery task:
        pool = await get_pool()
        await set_rls_context_for_background_task(pool, tenant_id)
        # Now all queries will be filtered by tenant_id

    Args:
        pool: Database connection pool
        tenant_id: Tenant UUID as string

    Raises:
        ValueError: If tenant_id is invalid
        Exception: If database operation fails
    """
    try:
        tenant_uuid = UUID(tenant_id)
    except (ValueError, AttributeError) as e:
        logger.error(
            "rls_background_invalid_tenant",
            tenant_id=tenant_id,
            error=str(e),
        )
        raise ValueError(f"Invalid tenant_id: {tenant_id}") from e

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_current_tenant($1)", tenant_uuid)
        logger.debug("rls_background_context_set", tenant_id=str(tenant_uuid))


async def clear_rls_context_for_background_task(pool: asyncpg.Pool):
    """
    Clear RLS context for background tasks

    Should be called at the end of background task to clean up.

    Args:
        pool: Database connection pool
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT clear_current_tenant()")
            logger.debug("rls_background_context_cleared")
    except Exception as e:
        logger.warning(
            "rls_background_clear_failed",
            error=str(e),
            message="Failed to clear RLS context. Not critical.",
        )


async def verify_rls_enabled(pool: asyncpg.Pool) -> dict:
    """
    Verify that RLS is enabled on critical tables

    Returns dict with table names and RLS status for monitoring/alerting.

    Usage:
        status = await verify_rls_enabled(pool)
        if not all(status.values()):
            alert("RLS not enabled on all tables!")

    Returns:
        dict mapping table name to RLS enabled status (bool)
    """
    critical_tables = [
        "memories",
        "semantic_nodes",
        "graph_triples",
        "reflections",
        "cost_logs",
        "audit_logs",
        "deletion_audit_log",
    ]

    status = {}

    async with pool.acquire() as conn:
        for table in critical_tables:
            try:
                result = await conn.fetchrow(
                    """
                    SELECT rowsecurity
                    FROM pg_tables
                    WHERE schemaname = 'public' AND tablename = $1
                    """,
                    table,
                )

                if result:
                    status[table] = result["rowsecurity"]
                else:
                    status[table] = None  # Table doesn't exist
            except Exception as e:
                logger.warning(
                    "rls_verify_failed",
                    table=table,
                    error=str(e),
                )
                status[table] = False

    return status


async def list_rls_policies(pool: asyncpg.Pool) -> list:
    """
    List all RLS policies for auditing

    Returns list of policy details for compliance reporting.

    Returns:
        list of dicts with policy information
    """
    async with pool.acquire() as conn:
        policies = await conn.fetch(
            """
            SELECT
                schemaname,
                tablename,
                policyname,
                permissive,
                roles,
                cmd,
                qual,
                with_check
            FROM pg_policies
            WHERE schemaname = 'public'
            ORDER BY tablename, policyname
            """
        )

        return [dict(policy) for policy in policies]
