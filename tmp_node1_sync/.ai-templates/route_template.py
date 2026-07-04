"""
API Route Template - Use this as a starting point for new API endpoints.

INSTRUCTIONS FOR AI AGENTS:
1. Copy this template
2. Replace "my-domain" with your API domain (e.g., "users", "orders")
3. Replace "MyBusiness" with your service name
4. Add your specific endpoints
5. Use Pydantic models for request/response validation
6. Register router in apps/memory_api/api/v1/__init__.py
7. Add tests in apps/memory_api/tests/api/v1/test_[domain].py

WHY THIS PATTERN:
- Input Validation: Automatic via Pydantic models
- Documentation: OpenAPI/Swagger docs generated automatically
- Security: Centralized auth/authz with Depends()
- HTTP Concerns: Status codes, headers separate from business logic
- Testability: Easy to test endpoints with TestClient
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from apps.memory_api.models import (  # Import your Pydantic models here
    EntityInput,
    EntityOutput,
)
from apps.memory_api.repositories.entity_repository import EntityRepository
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.my_business_service import MyBusinessService

# WHY: Router with prefix groups related endpoints
# WHY: Tags organize endpoints in Swagger UI
# WHY: Dependencies apply to all routes in this router
router = APIRouter(
    prefix="/my-domain",
    tags=["my-domain"],
    dependencies=[Depends(auth.verify_token)],  # All endpoints require auth
)

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# CREATE (POST)
# ═══════════════════════════════════════════════════════════════


@router.post(
    "/entities",
    response_model=EntityOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new entity",
    description="Creates a new entity with validation and business rules.",
)
async def create_entity(
    input_data: EntityInput,  # ← Pydantic validates automatically
    request: Request,  # ← Access to app state (pool, etc.)
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),  # ← RBAC
):
    """
    Create a new entity.

    This endpoint creates a new entity after validating:
    - Input data format (automatic via Pydantic)
    - Authentication (via verify_token dependency)
    - Authorization (via get_and_verify_tenant_id)
    - Business rules (via service layer)

    **Security:** Requires authentication and tenant access.

    **Request Body:**
    ```json
    {
        "name": "My Entity",
        "value": 100,
        "category": "test",
        "tags": ["important"]
    }
    ```

    **Response (201 Created):**
    ```json
    {
        "id": "uuid-here",
        "tenant_id": "tenant_1",
        "name": "My Entity",
        "value": 100,
        "created_at": "2025-12-04T10:00:00Z"
    }
    ```

    Args:
        input_data: Entity data (Pydantic validated)
        request: FastAPI request object
        verified_tenant_id: Tenant ID from RBAC

    Returns:
        EntityOutput: Created entity

    Raises:
        HTTPException 400: If business rules violated
        HTTPException 401: If not authenticated
        HTTPException 403: If not authorized for tenant
        HTTPException 500: If creation fails
    """
    tenant_id = verified_tenant_id

    logger.info(
        "api_create_entity",
        tenant_id=tenant_id,
        entity_name=input_data.name,
        method=request.method,
        path=request.url.path,
    )

    try:
        # Initialize service with dependencies
        # WHY: Service instantiated per-request (fresh state)
        service = MyBusinessService(
            entity_repo=EntityRepository(request.app.state.pool),
            pool=request.app.state.pool,
        )

        # Delegate to service layer
        # WHY: Business logic in service, not in route
        result = await service.create_entity(tenant_id, input_data)

        logger.info(
            "api_create_entity_success", tenant_id=tenant_id, entity_id=result.id
        )

        return result

    except ValueError as e:
        # Business rule violation → 400 Bad Request
        # WHY: ValueError indicates client error (bad input)
        logger.warning(
            "api_create_entity_validation_error", tenant_id=tenant_id, error=str(e)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        # Unexpected error → 500 Internal Server Error
        # WHY: Don't expose internal details to client
        logger.exception("api_create_entity_error", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create entity",
        )


# ═══════════════════════════════════════════════════════════════
# READ (GET)
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/entities/{entity_id}",
    response_model=EntityOutput,
    summary="Get entity by ID",
)
async def get_entity(
    entity_id: str,  # ← Path parameter
    request: Request,
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),
):
    """
    Retrieve entity by ID.

    **Security:** Requires authentication and tenant access.

    Args:
        entity_id: Unique entity identifier
        request: FastAPI request object
        verified_tenant_id: Tenant ID from RBAC

    Returns:
        EntityOutput: Entity data

    Raises:
        HTTPException 404: If entity not found
        HTTPException 403: If entity belongs to different tenant
    """
    tenant_id = verified_tenant_id

    logger.info("api_get_entity", tenant_id=tenant_id, entity_id=entity_id)

    try:
        service = MyBusinessService(
            entity_repo=EntityRepository(request.app.state.pool),
            pool=request.app.state.pool,
        )

        result = await service.get_entity(entity_id, tenant_id)

        if not result:
            # WHY: 404 for resource not found
            logger.warning(
                "api_get_entity_not_found", tenant_id=tenant_id, entity_id=entity_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        logger.info("api_get_entity_success", tenant_id=tenant_id, entity_id=entity_id)

        return result

    except HTTPException:
        # Re-raise HTTP exceptions (already have correct status code)
        raise

    except Exception as e:
        logger.exception(
            "api_get_entity_error",
            tenant_id=tenant_id,
            entity_id=entity_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity",
        )


@router.get(
    "/entities",
    response_model=list[EntityOutput],  # ← List response
    summary="List all entities",
)
async def list_entities(
    request: Request,
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),
    page: int = 1,  # ← Query parameter with default
    page_size: int = 20,
):
    """
    List all entities for tenant (paginated).

    **Security:** Requires authentication.

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20, max: 100)

    Returns:
        List[EntityOutput]: List of entities
    """
    # Validate pagination parameters
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be >= 1"
        )

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be between 1 and 100",
        )

    tenant_id = verified_tenant_id

    logger.info(
        "api_list_entities", tenant_id=tenant_id, page=page, page_size=page_size
    )

    try:
        service = MyBusinessService(
            entity_repo=EntityRepository(request.app.state.pool),
            pool=request.app.state.pool,
        )

        result = await service.search_entities(
            tenant_id=tenant_id,
            query="",  # Empty query = list all
            page=page,
            page_size=page_size,
        )

        logger.info(
            "api_list_entities_success", tenant_id=tenant_id, count=len(result.entities)
        )

        return result.entities

    except Exception as e:
        logger.exception("api_list_entities_error", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list entities",
        )


# ═══════════════════════════════════════════════════════════════
# UPDATE (PATCH)
# WHY: PATCH for partial updates, PUT for full replacement
# ═══════════════════════════════════════════════════════════════


@router.patch(
    "/entities/{entity_id}",
    response_model=EntityOutput,
    summary="Update entity",
)
async def update_entity(
    entity_id: str,
    updates: EntityInput,  # ← Pydantic validates updates
    request: Request,
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),
):
    """
    Update entity (partial update).

    **Security:** Requires authentication and tenant access.

    Args:
        entity_id: Entity to update
        updates: Fields to update
        request: FastAPI request
        verified_tenant_id: Tenant ID from RBAC

    Returns:
        EntityOutput: Updated entity

    Raises:
        HTTPException 404: If entity not found
        HTTPException 400: If update violates business rules
    """
    tenant_id = verified_tenant_id

    logger.info("api_update_entity", tenant_id=tenant_id, entity_id=entity_id)

    try:
        service = MyBusinessService(
            entity_repo=EntityRepository(request.app.state.pool),
            pool=request.app.state.pool,
        )

        result = await service.update_entity(entity_id, tenant_id, updates)

        if not result:
            logger.warning(
                "api_update_entity_not_found", tenant_id=tenant_id, entity_id=entity_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        logger.info(
            "api_update_entity_success", tenant_id=tenant_id, entity_id=entity_id
        )

        return result

    except ValueError as e:
        logger.warning(
            "api_update_entity_validation_error",
            tenant_id=tenant_id,
            entity_id=entity_id,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            "api_update_entity_error",
            tenant_id=tenant_id,
            entity_id=entity_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entity",
        )


# ═══════════════════════════════════════════════════════════════
# DELETE (DELETE)
# ═══════════════════════════════════════════════════════════════


@router.delete(
    "/entities/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete entity",
)
async def delete_entity(
    entity_id: str,
    request: Request,
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),
):
    """
    Delete entity.

    **Security:** Requires authentication and tenant access.

    Args:
        entity_id: Entity to delete
        request: FastAPI request
        verified_tenant_id: Tenant ID from RBAC

    Returns:
        204 No Content on success

    Raises:
        HTTPException 404: If entity not found
        HTTPException 400: If entity cannot be deleted
    """
    tenant_id = verified_tenant_id

    logger.info("api_delete_entity", tenant_id=tenant_id, entity_id=entity_id)

    try:
        service = MyBusinessService(
            entity_repo=EntityRepository(request.app.state.pool),
            pool=request.app.state.pool,
        )

        deleted = await service.delete_entity(entity_id, tenant_id)

        if not deleted:
            logger.warning(
                "api_delete_entity_not_found", tenant_id=tenant_id, entity_id=entity_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        logger.info(
            "api_delete_entity_success", tenant_id=tenant_id, entity_id=entity_id
        )

        # WHY: 204 No Content for successful DELETE (no body)
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    except ValueError as e:
        logger.warning(
            "api_delete_entity_error",
            tenant_id=tenant_id,
            entity_id=entity_id,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            "api_delete_entity_error",
            tenant_id=tenant_id,
            entity_id=entity_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete entity",
        )


# ═══════════════════════════════════════════════════════════════
# TESTING NOTES
# ═══════════════════════════════════════════════════════════════

# Use FastAPI TestClient for endpoint tests:
#
# from fastapi.testclient import TestClient
#
# def test_create_entity_returns_201(test_client, auth_headers, test_tenant):
#     response = test_client.post(
#         "/api/v1/my-domain/entities",
#         json={
#             "name": "Test Entity",
#             "value": 100,
#             "category": "test"
#         },
#         headers=auth_headers
#     )
#
#     assert response.status_code == 201
#     data = response.json()
#     assert data['name'] == "Test Entity"
#     assert data['value'] == 100
#     assert 'id' in data
#
#
# def test_get_entity_returns_404_for_nonexistent(test_client, auth_headers):
#     response = test_client.get(
#         "/api/v1/my-domain/entities/nonexistent-id",
#         headers=auth_headers
#     )
#
#     assert response.status_code == 404
#     assert "not found" in response.json()['detail'].lower()
#
#
# def test_create_entity_returns_400_for_invalid_input(test_client, auth_headers):
#     response = test_client.post(
#         "/api/v1/my-domain/entities",
#         json={
#             "name": "",  # Invalid: empty name
#             "value": -1   # Invalid: negative value
#         },
#         headers=auth_headers
#     )
#
#     assert response.status_code == 400
