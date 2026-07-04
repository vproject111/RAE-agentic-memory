"""
Service Template - Use this as a starting point for new services.

INSTRUCTIONS FOR AI AGENTS:
1. Copy this template
2. Replace "Entity" with your domain (e.g., "User", "Order", "Payment")
3. Replace "MyBusiness" with your business logic name
4. Add your specific business methods
5. Inject dependencies in __init__
6. Use Pydantic models for input/output
7. Add tests in apps/memory_api/tests/services/test_[service].py

WHY THIS PATTERN:
- Business Logic Centralization: All domain rules in one place
- Testability: Easy to mock dependencies and test in isolation
- Reusability: Services can be composed together
- Clear Interfaces: Pydantic models define contracts
- Dependency Injection: Loosely coupled, easy to test and swap implementations
"""

from typing import Any, Dict, List, Optional

import asyncpg
import structlog
from pydantic import BaseModel, Field

from apps.memory_api.repositories.entity_repository import EntityRepository

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# INPUT/OUTPUT MODELS (Pydantic)
# WHY: Type safety, automatic validation, clear API contracts
# ═══════════════════════════════════════════════════════════════


class EntityInput(BaseModel):
    """
    Input model for creating/updating entities.

    WHY: Validates input before it reaches business logic
    WHY: Automatic OpenAPI documentation generation
    """

    name: str = Field(..., min_length=1, max_length=200, description="Entity name")
    value: int = Field(..., ge=0, description="Entity value (must be >= 0)")
    category: str = Field(default="default", description="Entity category")
    tags: List[str] = Field(default_factory=list, description="Optional tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Example Entity",
                "value": 100,
                "category": "test",
                "tags": ["important", "active"],
                "metadata": {"source": "api"},
            }
        }


class EntityOutput(BaseModel):
    """
    Output model for entity responses.

    WHY: Consistent response format
    WHY: Hides internal fields (like password hashes)
    """

    id: str = Field(..., description="Unique entity identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    name: str
    value: int
    category: str
    tags: List[str]
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True  # Allow creation from database records


class EntitySearchResult(BaseModel):
    """Result model for search operations."""

    entities: List[EntityOutput]
    total_count: int
    page: int
    page_size: int


# ═══════════════════════════════════════════════════════════════
# SERVICE LAYER (Business Logic)
# ═══════════════════════════════════════════════════════════════


class MyBusinessService:
    """
    Service for [Business Domain] operations.

    Handles business logic for [specific domain], orchestrating
    operations across repositories and external services.

    Features:
    - Entity lifecycle management (create, update, delete)
    - Business rule validation
    - Complex multi-step operations
    - Integration with other services
    - Full Dependency Injection for testability

    Example Usage:
        >>> service = MyBusinessService(entity_repo, other_service, pool)
        >>> entity = await service.create_entity(tenant_id, input_data)
        >>> results = await service.search_entities(tenant_id, query)
    """

    def __init__(
        self,
        entity_repo: EntityRepository,
        # other_service: OtherService,  # ← Inject other services if needed
        pool: asyncpg.Pool,  # ← If you need direct DB access for complex queries
    ):
        """
        Initialize service with dependencies.

        WHY: Dependency Injection allows easy testing with mocks
        WHY: Loosely coupled - can swap implementations

        Args:
            entity_repo: Repository for entity data access
            pool: Database connection pool (for complex operations)
        """
        self.entity_repo = entity_repo
        # self.other_service = other_service
        self.pool = pool
        self.logger = logger

    # ═══════════════════════════════════════════════════════════════
    # PUBLIC METHODS (Business Operations)
    # ═══════════════════════════════════════════════════════════════

    async def create_entity(
        self,
        tenant_id: str,
        input_data: EntityInput,
    ) -> EntityOutput:
        """
        Create a new entity with business validation.

        WHY: Encapsulates creation logic and validation
        WHY: Consistent entry point for creating entities

        Business Rules:
        1. Name must be unique within tenant
        2. Value must be positive
        3. Category must exist (validated)
        4. Audit trail is created

        Args:
            tenant_id: Tenant identifier for multi-tenancy
            input_data: Validated input data (Pydantic model)

        Returns:
            EntityOutput: Created entity

        Raises:
            ValueError: If business rules are violated
            DatabaseError: If persistence fails
        """
        self.logger.info(
            "create_entity_started", tenant_id=tenant_id, entity_name=input_data.name
        )

        try:
            # Step 1: Validate business rules
            await self._validate_create_rules(tenant_id, input_data)

            # Step 2: Check for duplicates
            existing = await self._check_duplicate_name(tenant_id, input_data.name)
            if existing:
                raise ValueError(f"Entity with name '{input_data.name}' already exists")

            # Step 3: Apply business logic
            entity_data = self._prepare_entity_data(tenant_id, input_data)

            # Step 4: Calculate derived fields
            entity_data["score"] = self._calculate_score(input_data.value)

            # Step 5: Persist to database
            created = await self.entity_repo.insert(entity_data)

            # Step 6: Post-creation actions
            # await self.other_service.notify_created(created['id'])
            # await self._create_audit_log(tenant_id, "entity_created", created['id'])

            self.logger.info(
                "create_entity_completed", tenant_id=tenant_id, entity_id=created["id"]
            )

            return EntityOutput(**created)

        except ValueError as e:
            self.logger.warning(
                "create_entity_validation_failed", tenant_id=tenant_id, error=str(e)
            )
            raise

        except Exception as e:
            self.logger.exception(
                "create_entity_failed", tenant_id=tenant_id, error=str(e)
            )
            raise RuntimeError(f"Failed to create entity: {e}")

    async def get_entity(
        self,
        entity_id: str,
        tenant_id: str,
    ) -> Optional[EntityOutput]:
        """
        Retrieve entity by ID.

        WHY: Single entry point for fetching entities
        WHY: Can add caching, access control, etc.

        Args:
            entity_id: Entity identifier
            tenant_id: Tenant identifier for RLS

        Returns:
            EntityOutput or None if not found
        """
        entity = await self.entity_repo.get_by_id(entity_id, tenant_id)

        if not entity:
            return None

        # Apply post-fetch business logic if needed
        # e.g., calculate dynamic fields, check access, etc.

        return EntityOutput(**entity)

    async def update_entity(
        self,
        entity_id: str,
        tenant_id: str,
        updates: EntityInput,
    ) -> Optional[EntityOutput]:
        """
        Update entity with business validation.

        WHY: Ensures updates follow business rules
        WHY: Centralizes update logic

        Args:
            entity_id: Entity to update
            tenant_id: Tenant identifier
            updates: New values (Pydantic validated)

        Returns:
            Updated entity or None if not found

        Raises:
            ValueError: If business rules violated
        """
        self.logger.info(
            "update_entity_started", entity_id=entity_id, tenant_id=tenant_id
        )

        # Validate entity exists
        existing = await self.entity_repo.get_by_id(entity_id, tenant_id)
        if not existing:
            return None

        # Validate business rules for update
        await self._validate_update_rules(tenant_id, entity_id, updates)

        # Prepare update data
        update_data = updates.dict(exclude_unset=True)

        # Recalculate derived fields if needed
        if "value" in update_data:
            update_data["score"] = self._calculate_score(update_data["value"])

        # Persist update
        updated = await self.entity_repo.update(entity_id, tenant_id, update_data)

        if updated:
            self.logger.info(
                "update_entity_completed", entity_id=entity_id, tenant_id=tenant_id
            )

        return EntityOutput(**updated) if updated else None

    async def delete_entity(
        self,
        entity_id: str,
        tenant_id: str,
    ) -> bool:
        """
        Delete entity with cascading cleanup.

        WHY: Ensures proper cleanup of related resources
        WHY: Enforces deletion policies

        Args:
            entity_id: Entity to delete
            tenant_id: Tenant identifier

        Returns:
            True if deleted, False if not found
        """
        self.logger.info(
            "delete_entity_started", entity_id=entity_id, tenant_id=tenant_id
        )

        # Check if entity can be deleted (business rules)
        can_delete = await self._can_delete_entity(entity_id, tenant_id)
        if not can_delete:
            raise ValueError("Entity cannot be deleted - has dependencies")

        # Delete related resources first (cascade)
        # await self._delete_related_resources(entity_id, tenant_id)

        # Delete entity
        deleted = await self.entity_repo.delete(entity_id, tenant_id)

        if deleted:
            self.logger.info(
                "delete_entity_completed", entity_id=entity_id, tenant_id=tenant_id
            )

        return deleted

    async def search_entities(
        self,
        tenant_id: str,
        query: str,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> EntitySearchResult:
        """
        Search entities with filters and pagination.

        WHY: Complex search logic centralized
        WHY: Consistent search behavior across API

        Args:
            tenant_id: Tenant identifier
            query: Search query string
            category: Optional category filter
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            EntitySearchResult with pagination info
        """
        offset = (page - 1) * page_size

        # Get entities (simplified - extend with actual search logic)
        entities = await self.entity_repo.get_all(
            tenant_id=tenant_id, limit=page_size, offset=offset
        )

        # Get total count for pagination
        total_count = await self.entity_repo.count(tenant_id)

        return EntitySearchResult(
            entities=[EntityOutput(**e) for e in entities],
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    # ═══════════════════════════════════════════════════════════════
    # PRIVATE METHODS (Internal Business Logic)
    # WHY: Keep public API clean, hide implementation details
    # ═══════════════════════════════════════════════════════════════

    async def _validate_create_rules(self, tenant_id: str, input_data: EntityInput):
        """
        Validate business rules for entity creation.

        WHY: Centralized validation logic
        WHY: Easy to extend with new rules

        Raises:
            ValueError: If validation fails
        """
        # Example rule: Value must be within tenant's limit
        # tenant_limit = await self._get_tenant_limit(tenant_id)
        # if input_data.value > tenant_limit:
        #     raise ValueError(f"Value exceeds tenant limit: {tenant_limit}")

        # Example rule: Category must exist
        # valid_categories = await self._get_valid_categories()
        # if input_data.category not in valid_categories:
        #     raise ValueError(f"Invalid category: {input_data.category}")

        pass

    async def _validate_update_rules(
        self, tenant_id: str, entity_id: str, updates: EntityInput
    ):
        """Validate business rules for updates."""
        # Similar to _validate_create_rules
        pass

    async def _check_duplicate_name(self, tenant_id: str, name: str) -> Optional[Dict]:
        """
        Check if entity with name already exists.

        WHY: Enforce uniqueness constraint at business logic level
        """
        # Implement using repository method:
        # return await self.entity_repo.get_by_name(name, tenant_id)
        return None  # Placeholder

    def _prepare_entity_data(
        self, tenant_id: str, input_data: EntityInput
    ) -> Dict[str, Any]:
        """
        Prepare data for persistence.

        WHY: Transform API input to database format
        WHY: Add system fields (tenant_id, timestamps, etc.)
        """
        return {
            "tenant_id": tenant_id,
            **input_data.dict(),
            # Add computed fields here
        }

    def _calculate_score(self, value: int) -> float:
        """
        Calculate derived score based on value.

        WHY: Business logic for scoring
        WHY: Reusable across create/update operations
        """
        # Example calculation
        return min(value / 100.0, 1.0)

    async def _can_delete_entity(self, entity_id: str, tenant_id: str) -> bool:
        """
        Check if entity can be deleted.

        WHY: Enforce deletion policies (e.g., can't delete if has dependencies)
        """
        # Check for dependencies
        # has_dependencies = await self.other_service.has_references(entity_id)
        # return not has_dependencies
        return True  # Placeholder


# ═══════════════════════════════════════════════════════════════
# TESTING NOTES
# ═══════════════════════════════════════════════════════════════

# Unit tests (fast, mock repositories):
#
# @pytest.mark.unit
# async def test_create_entity_validates_duplicate_name():
#     # Arrange
#     mock_repo = Mock(EntityRepository)
#     mock_repo.get_by_name = AsyncMock(return_value={'id': 'existing'})
#
#     service = MyBusinessService(entity_repo=mock_repo, pool=Mock())
#
#     input_data = EntityInput(name="Duplicate", value=100)
#
#     # Act & Assert
#     with pytest.raises(ValueError, match="already exists"):
#         await service.create_entity("tenant_1", input_data)
#
#     mock_repo.get_by_name.assert_called_once_with("Duplicate", "tenant_1")
#
#
# @pytest.mark.unit
# def test_calculate_score():
#     service = MyBusinessService(Mock(), Mock())
#
#     assert service._calculate_score(0) == 0.0
#     assert service._calculate_score(50) == 0.5
#     assert service._calculate_score(100) == 1.0
#     assert service._calculate_score(200) == 1.0  # Capped at 1.0
#
#
# Integration tests (with real database):
#
# @pytest.mark.integration
# async def test_create_entity_persists_to_database(pool, test_tenant):
#     repo = EntityRepository(pool)
#     service = MyBusinessService(entity_repo=repo, pool=pool)
#
#     input_data = EntityInput(name="Test Entity", value=75)
#
#     # Act
#     result = await service.create_entity(test_tenant, input_data)
#
#     # Assert
#     assert result.id is not None
#     assert result.name == "Test Entity"
#     assert result.value == 75
#     assert result.score == 0.75
#
#     # Verify in database
#     fetched = await repo.get_by_id(result.id, test_tenant)
#     assert fetched['name'] == "Test Entity"
