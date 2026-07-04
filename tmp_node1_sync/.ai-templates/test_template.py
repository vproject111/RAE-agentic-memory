"""
Test Template - Use this as a starting point for writing tests.

INSTRUCTIONS FOR AI AGENTS:
1. Copy relevant sections from this template
2. Replace "Entity" with your entity/service name
3. Use appropriate pytest markers (@pytest.mark.unit or @pytest.mark.integration)
4. Follow AAA pattern (Arrange, Act, Assert)
5. Test behavior, not implementation
6. Keep tests focused and independent

WHY THESE PATTERNS:
- AAA Pattern: Clear test structure (Arrange-Act-Assert)
- Descriptive Names: Test names document expected behavior
- Fixtures: Reusable test data and setup
- Markers: Separate fast unit tests from slow integration tests
- Mocking: Isolate unit under test, test integration points separately
"""

from unittest.mock import AsyncMock, Mock

import pytest

from apps.memory_api.models import EntityInput

# Adjust imports based on what you're testing
from apps.memory_api.repositories.entity_repository import EntityRepository
from apps.memory_api.services.my_business_service import MyBusinessService

# ═══════════════════════════════════════════════════════════════
# FIXTURES (Reusable Test Data and Setup)
# WHY: DRY principle, consistent test data, easy to modify
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def sample_entity_input():
    """
    Sample valid entity input for testing.

    WHY: Centralize test data, easy to modify for all tests
    """
    return EntityInput(
        name="Test Entity",
        value=100,
        category="test",
        tags=["important", "test"],
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_entity_dict():
    """
    Sample entity dict (as returned from repository).

    WHY: Simulate database record format
    """
    return {
        "id": "entity_123",
        "tenant_id": "tenant_1",
        "name": "Test Entity",
        "value": 100,
        "category": "test",
        "tags": ["important", "test"],
        "score": 1.0,
        "created_at": "2025-12-04T10:00:00Z",
        "updated_at": None,
    }


@pytest.fixture
def mock_repository():
    """
    Mock repository for unit testing services.

    WHY: Isolate service logic from database
    WHY: Fast tests, no database required
    """
    return Mock(spec=EntityRepository)


# ═══════════════════════════════════════════════════════════════
# UNIT TESTS - Services (Fast, No External Dependencies)
# WHY: Test business logic in isolation
# WHY: Fast feedback during development
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
async def test_create_entity_validates_duplicate_name(
    mock_repository, sample_entity_input
):
    """
    Test that create_entity rejects duplicate names.

    WHY: Test business rule enforcement
    WHY: Test error handling
    """
    # Arrange: Mock repository to return existing entity
    mock_repository.get_by_name = AsyncMock(
        return_value={"id": "existing_id", "name": "Test Entity"}
    )

    service = MyBusinessService(entity_repo=mock_repository, pool=Mock())

    # Act & Assert: Should raise ValueError for duplicate
    with pytest.raises(ValueError, match="already exists"):
        await service.create_entity("tenant_1", sample_entity_input)

    # Verify repository was called
    mock_repository.get_by_name.assert_called_once_with("Test Entity", "tenant_1")


@pytest.mark.unit
async def test_create_entity_calculates_score_correctly(
    mock_repository, sample_entity_input, sample_entity_dict
):
    """
    Test that create_entity calculates score based on value.

    WHY: Test derived field calculation (business logic)
    WHY: Test successful path
    """
    # Arrange
    mock_repository.get_by_name = AsyncMock(return_value=None)  # No duplicate
    mock_repository.insert = AsyncMock(return_value=sample_entity_dict)

    service = MyBusinessService(entity_repo=mock_repository, pool=Mock())

    # Act
    result = await service.create_entity("tenant_1", sample_entity_input)

    # Assert: Score should be calculated
    assert result.score == 1.0

    # Verify repository insert was called with score
    mock_repository.insert.assert_called_once()
    insert_data = mock_repository.insert.call_args[0][0]
    assert "score" in insert_data
    assert insert_data["score"] == 1.0


@pytest.mark.unit
async def test_get_entity_returns_none_when_not_found(mock_repository):
    """
    Test that get_entity returns None for non-existent entity.

    WHY: Test not-found case
    WHY: Ensure consistent API behavior
    """
    # Arrange
    mock_repository.get_by_id = AsyncMock(return_value=None)

    service = MyBusinessService(entity_repo=mock_repository, pool=Mock())

    # Act
    result = await service.get_entity("nonexistent_id", "tenant_1")

    # Assert
    assert result is None
    mock_repository.get_by_id.assert_called_once_with("nonexistent_id", "tenant_1")


@pytest.mark.unit
async def test_delete_entity_prevents_deletion_with_dependencies(mock_repository):
    """
    Test that delete_entity enforces deletion policies.

    WHY: Test business rule (can't delete if has dependencies)
    WHY: Test error handling
    """
    # Arrange
    mock_repository.get_by_id = AsyncMock(return_value={"id": "entity_123"})

    service = MyBusinessService(entity_repo=mock_repository, pool=Mock())

    # Mock _can_delete_entity to return False
    service._can_delete_entity = AsyncMock(return_value=False)

    # Act & Assert
    with pytest.raises(ValueError, match="has dependencies"):
        await service.delete_entity("entity_123", "tenant_1")

    # Verify delete was NOT called
    mock_repository.delete.assert_not_called()


@pytest.mark.unit
def test_calculate_score_returns_correct_values():
    """
    Test score calculation algorithm.

    WHY: Test pure function (no async, no dependencies)
    WHY: Test boundary conditions
    """
    # Arrange
    service = MyBusinessService(Mock(), Mock())

    # Act & Assert: Test various inputs
    assert service._calculate_score(0) == 0.0
    assert service._calculate_score(50) == 0.5
    assert service._calculate_score(100) == 1.0
    assert service._calculate_score(200) == 1.0  # Capped at 1.0


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TESTS - Repository (With Real Database)
# WHY: Verify SQL queries work correctly
# WHY: Test database constraints and transactions
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
async def test_repository_insert_persists_entity(pool, test_tenant):
    """
    Test that repository insert persists entity to database.

    WHY: Verify database integration
    WHY: Test round-trip (insert → fetch)

    NOTE: Requires database fixture (pool)
    """
    # Arrange
    repo = EntityRepository(pool)

    entity_data = {
        "tenant_id": test_tenant,
        "name": "Integration Test Entity",
        "value": 150,
        "category": "test",
        "tags": ["integration"],
        "score": 1.0,
    }

    # Act: Insert
    created = await repo.insert(entity_data)

    # Assert: Created entity has ID
    assert created["id"] is not None
    assert created["name"] == "Integration Test Entity"
    assert created["value"] == 150

    # Act: Fetch by ID
    fetched = await repo.get_by_id(created["id"], test_tenant)

    # Assert: Fetched matches created
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["name"] == "Integration Test Entity"


@pytest.mark.integration
async def test_repository_enforces_tenant_isolation(pool):
    """
    Test that repository enforces Row Level Security.

    WHY: Critical security test
    WHY: Verify can't access other tenant's data
    """
    # Arrange
    repo = EntityRepository(pool)

    # Create entity for tenant A
    entity_data_a = {
        "tenant_id": "tenant_a",
        "name": "Entity A",
        "value": 100,
        "category": "test",
        "tags": [],
        "score": 1.0,
    }
    created = await repo.insert(entity_data_a)

    # Act: Try to fetch with tenant B credentials
    result = await repo.get_by_id(created["id"], "tenant_b")

    # Assert: Should NOT be able to access
    assert result is None  # ← Critical security assertion


@pytest.mark.integration
async def test_repository_update_modifies_entity(pool, test_tenant):
    """
    Test that repository update modifies existing entity.

    WHY: Verify update operations work correctly
    """
    # Arrange: Create entity
    repo = EntityRepository(pool)

    entity_data = {
        "tenant_id": test_tenant,
        "name": "Original Name",
        "value": 100,
        "category": "test",
        "tags": [],
        "score": 1.0,
    }
    created = await repo.insert(entity_data)

    # Act: Update entity
    updates = {"name": "Updated Name", "value": 200}
    updated = await repo.update(created["id"], test_tenant, updates)

    # Assert: Updates applied
    assert updated is not None
    assert updated["name"] == "Updated Name"
    assert updated["value"] == 200
    assert updated["id"] == created["id"]  # ID unchanged


@pytest.mark.integration
async def test_repository_delete_removes_entity(pool, test_tenant):
    """
    Test that repository delete removes entity.

    WHY: Verify deletion works correctly
    """
    # Arrange: Create entity
    repo = EntityRepository(pool)

    entity_data = {
        "tenant_id": test_tenant,
        "name": "To Be Deleted",
        "value": 100,
        "category": "test",
        "tags": [],
        "score": 1.0,
    }
    created = await repo.insert(entity_data)

    # Act: Delete
    deleted = await repo.delete(created["id"], test_tenant)

    # Assert: Deletion successful
    assert deleted is True

    # Verify entity no longer exists
    fetched = await repo.get_by_id(created["id"], test_tenant)
    assert fetched is None


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TESTS - Service + Repository
# WHY: Test service orchestration with real database
# WHY: Verify end-to-end flows
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
async def test_service_create_entity_end_to_end(pool, test_tenant):
    """
    Test complete create entity flow with real database.

    WHY: Verify service + repository integration
    WHY: Test real-world scenario
    """
    # Arrange
    repo = EntityRepository(pool)
    service = MyBusinessService(entity_repo=repo, pool=pool)

    input_data = EntityInput(
        name="End-to-End Test", value=75, category="test", tags=["e2e"]
    )

    # Act
    result = await service.create_entity(test_tenant, input_data)

    # Assert: Entity created successfully
    assert result.id is not None
    assert result.name == "End-to-End Test"
    assert result.value == 75
    assert result.score == 0.75  # Calculated by service

    # Verify in database
    fetched = await repo.get_by_id(result.id, test_tenant)
    assert fetched["name"] == "End-to-End Test"
    assert fetched["score"] == 0.75


# ═══════════════════════════════════════════════════════════════
# API ENDPOINT TESTS (Integration with FastAPI TestClient)
# WHY: Test HTTP layer (request validation, status codes, etc.)
# WHY: Verify API contracts
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
def test_api_create_entity_returns_201(test_client, auth_headers, test_tenant):
    """
    Test POST /entities returns 201 Created.

    WHY: Verify HTTP endpoint behavior
    WHY: Test authentication and authorization
    """
    # Arrange
    request_body = {
        "name": "API Test Entity",
        "value": 100,
        "category": "test",
        "tags": ["api-test"],
    }

    # Act
    response = test_client.post(
        "/api/v1/my-domain/entities", json=request_body, headers=auth_headers
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Test Entity"
    assert data["value"] == 100
    assert "id" in data
    assert "created_at" in data


@pytest.mark.integration
def test_api_get_entity_returns_404_for_nonexistent(test_client, auth_headers):
    """
    Test GET /entities/{id} returns 404 for non-existent entity.

    WHY: Verify error handling at HTTP layer
    """
    # Act
    response = test_client.get(
        "/api/v1/my-domain/entities/nonexistent-id", headers=auth_headers
    )

    # Assert
    assert response.status_code == 404
    error = response.json()
    assert "not found" in error["detail"].lower()


@pytest.mark.integration
def test_api_create_entity_returns_400_for_invalid_input(test_client, auth_headers):
    """
    Test POST /entities returns 400 for invalid input.

    WHY: Verify Pydantic validation at HTTP layer
    """
    # Arrange: Invalid request (missing required field)
    request_body = {
        "value": 100
        # Missing "name" (required)
    }

    # Act
    response = test_client.post(
        "/api/v1/my-domain/entities", json=request_body, headers=auth_headers
    )

    # Assert
    assert response.status_code == 422  # Unprocessable Entity (Pydantic validation)


@pytest.mark.integration
def test_api_requires_authentication(test_client):
    """
    Test that endpoints require authentication.

    WHY: Verify security (no access without JWT)
    """
    # Act: Call without auth headers
    response = test_client.get("/api/v1/my-domain/entities")

    # Assert: 401 Unauthorized
    assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# PARAMETRIZED TESTS (Test Multiple Cases Efficiently)
# WHY: Test multiple inputs with single test function
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected_score",
    [
        (0, 0.0),
        (25, 0.25),
        (50, 0.5),
        (75, 0.75),
        (100, 1.0),
        (200, 1.0),  # Capped at 1.0
        (1000, 1.0),  # Capped at 1.0
    ],
)
def test_calculate_score_parametrized(value, expected_score):
    """
    Test score calculation for multiple values.

    WHY: Test boundary conditions efficiently
    WHY: Easy to add new test cases
    """
    # Arrange
    service = MyBusinessService(Mock(), Mock())

    # Act
    score = service._calculate_score(value)

    # Assert
    assert score == expected_score


# ═══════════════════════════════════════════════════════════════
# ERROR CASE TESTS
# WHY: Test how code handles failures
# WHY: Verify graceful degradation
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
async def test_create_entity_handles_database_error(mock_repository):
    """
    Test that service handles database errors gracefully.

    WHY: Test error handling
    WHY: Verify appropriate exception is raised
    """
    # Arrange: Mock repository to raise database error
    mock_repository.get_by_name = AsyncMock(return_value=None)
    mock_repository.insert = AsyncMock(
        side_effect=Exception("Database connection lost")
    )

    service = MyBusinessService(entity_repo=mock_repository, pool=Mock())

    input_data = EntityInput(name="Test", value=100, category="test")

    # Act & Assert: Should raise RuntimeError (wrapped)
    with pytest.raises(RuntimeError, match="Failed to create entity"):
        await service.create_entity("tenant_1", input_data)


# ═══════════════════════════════════════════════════════════════
# FIXTURES FOR DATABASE TESTS (Example - Adapt to Your Setup)
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def pool():
    """
    Provide database connection pool for integration tests.

    NOTE: This is a placeholder - implement based on your setup
    """
    # Setup: Create pool, run migrations, etc.
    pool = await create_test_pool()  # noqa: F821

    yield pool

    # Teardown: Clean up
    await pool.close()


@pytest.fixture
def test_tenant():
    """Provide test tenant ID."""
    return "test_tenant_123"


@pytest.fixture
def test_client():
    """
    Provide FastAPI TestClient for API tests.

    NOTE: Placeholder - implement based on your app setup
    """
    from fastapi.testclient import TestClient

    from apps.memory_api.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers(test_tenant):
    """
    Provide authentication headers for API tests.

    NOTE: Placeholder - generate real JWT for your tests
    """
    return {"Authorization": f"Bearer test_jwt_token_for_{test_tenant}"}
