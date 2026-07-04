"""
Repository Template - Use this as a starting point for new repositories.

INSTRUCTIONS FOR AI AGENTS:
1. Copy this template
2. Replace "Entity" with your entity name (e.g., "User", "Order", "Memory")
3. Replace "entities" with your table name (e.g., "users", "orders", "memories")
4. Add your specific CRUD methods
5. Keep the structure and patterns intact
6. Add tests in apps/memory_api/tests/repositories/test_[entity]_repository.py

WHY THIS PATTERN:
- Single Responsibility: One repository per entity
- Testability: Easy to mock in service tests
- Database Agnostic: Business logic doesn't depend on SQL
- RLS: Consistent tenant isolation
- Type Safety: Clear interfaces for data access
"""

from typing import Any, Dict, List, Optional

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class EntityRepository:
    """
    Repository for [Entity] data access operations.

    Handles all SQL queries related to [Entity] CRUD operations.
    Implements Row Level Security (RLS) for multi-tenancy.

    Example Usage:
        >>> repo = EntityRepository(pool)
        >>> entity = await repo.get_by_id("entity_123", "tenant_1")
        >>> new_entity = await repo.insert({...})
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize entity repository.

        Args:
            pool: AsyncPG connection pool for database operations
        """
        self.pool = pool

    async def get_by_id(
        self, entity_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve entity by ID.

        WHY: Single source of truth for fetching entities
        WHY: Enforces tenant isolation (RLS)

        Args:
            entity_id: Unique identifier for the entity
            tenant_id: Tenant identifier for RLS

        Returns:
            Entity dict or None if not found

        Raises:
            asyncpg.PostgresError: If database query fails
        """
        query = """
            SELECT *
            FROM entities
            WHERE id = $1 AND tenant_id = $2
        """

        async with self.pool.acquire() as conn:
            try:
                record = await conn.fetchrow(query, entity_id, tenant_id)
                return dict(record) if record else None
            except asyncpg.PostgresError as e:
                logger.error(
                    "db_get_error",
                    entity_id=entity_id,
                    tenant_id=tenant_id,
                    error=str(e),
                )
                raise

    async def get_all(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all entities for a tenant (paginated).

        Args:
            tenant_id: Tenant identifier for RLS
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of entity dicts
        """
        query = """
            SELECT *
            FROM entities
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        async with self.pool.acquire() as conn:
            try:
                records = await conn.fetch(query, tenant_id, limit, offset)
                return [dict(record) for record in records]
            except asyncpg.PostgresError as e:
                logger.error(
                    "db_get_all_error",
                    tenant_id=tenant_id,
                    limit=limit,
                    offset=offset,
                    error=str(e),
                )
                raise

    async def insert(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new entity.

        WHY: Centralized insertion logic
        WHY: Handles dynamic fields and returns full record

        Args:
            entity_data: Dictionary containing entity fields
                Required: tenant_id, name, ...
                Optional: metadata, tags, ...

        Returns:
            Newly created entity dict with generated ID and timestamps

        Raises:
            asyncpg.PostgresError: If insertion fails
            KeyError: If required fields are missing
        """
        # Validate required fields
        required_fields = ["tenant_id", "name"]  # ← Customize for your entity
        for field in required_fields:
            if field not in entity_data:
                raise KeyError(f"Missing required field: {field}")

        # Build dynamic INSERT query
        # WHY: Flexible for different field combinations
        columns = list(entity_data.keys())
        placeholders = [f"${i + 1}" for i in range(len(columns))]
        values = [entity_data[col] for col in columns]

        query = f"""
            INSERT INTO entities ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
            RETURNING *
        """

        async with self.pool.acquire() as conn:
            try:
                record = await conn.fetchrow(query, *values)
                logger.info(
                    "entity_inserted",
                    entity_id=record["id"],
                    tenant_id=entity_data["tenant_id"],
                )
                return dict(record)
            except asyncpg.PostgresError as e:
                logger.error(
                    "db_insert_error",
                    tenant_id=entity_data.get("tenant_id"),
                    error=str(e),
                )
                raise

    async def update(
        self, entity_id: str, tenant_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing entity.

        WHY: Partial updates without overwriting entire record
        WHY: Enforces tenant isolation

        Args:
            entity_id: ID of entity to update
            tenant_id: Tenant identifier for RLS
            updates: Dictionary of fields to update

        Returns:
            Updated entity dict or None if not found

        Raises:
            asyncpg.PostgresError: If update fails
        """
        if not updates:
            # Nothing to update, fetch and return current state
            return await self.get_by_id(entity_id, tenant_id)

        # Build dynamic UPDATE query
        set_clauses = [f"{col} = ${i + 2}" for i, col in enumerate(updates.keys())]
        values = [entity_id, tenant_id] + list(updates.values())

        query = f"""
            UPDATE entities
            SET {", ".join(set_clauses)}, updated_at = NOW()
            WHERE id = $1 AND tenant_id = $2
            RETURNING *
        """

        async with self.pool.acquire() as conn:
            try:
                record = await conn.fetchrow(query, *values)
                if record:
                    logger.info(
                        "entity_updated",
                        entity_id=entity_id,
                        tenant_id=tenant_id,
                        fields_updated=list(updates.keys()),
                    )
                return dict(record) if record else None
            except asyncpg.PostgresError as e:
                logger.error(
                    "db_update_error",
                    entity_id=entity_id,
                    tenant_id=tenant_id,
                    error=str(e),
                )
                raise

    async def delete(self, entity_id: str, tenant_id: str) -> bool:
        """
        Delete an entity.

        WHY: Soft delete vs hard delete can be configured here
        WHY: Enforces tenant isolation

        Args:
            entity_id: ID of entity to delete
            tenant_id: Tenant identifier for RLS

        Returns:
            True if deleted, False if not found

        Raises:
            asyncpg.PostgresError: If deletion fails
        """
        # Option 1: Hard delete
        query = """
            DELETE FROM entities
            WHERE id = $1 AND tenant_id = $2
        """

        # Option 2: Soft delete (uncomment if preferred)
        # query = """
        #     UPDATE entities
        #     SET deleted_at = NOW()
        #     WHERE id = $1 AND tenant_id = $2 AND deleted_at IS NULL
        # """

        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute(query, entity_id, tenant_id)
                # Result format: "DELETE N" or "UPDATE N"
                rows_affected = int(result.split()[-1])

                if rows_affected > 0:
                    logger.info(
                        "entity_deleted", entity_id=entity_id, tenant_id=tenant_id
                    )
                    return True
                return False

            except asyncpg.PostgresError as e:
                logger.error(
                    "db_delete_error",
                    entity_id=entity_id,
                    tenant_id=tenant_id,
                    error=str(e),
                )
                raise

    async def count(self, tenant_id: str) -> int:
        """
        Count total entities for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Number of entities
        """
        query = """
            SELECT COUNT(*) FROM entities
            WHERE tenant_id = $1
        """

        async with self.pool.acquire() as conn:
            try:
                count = await conn.fetchval(query, tenant_id)
                return count or 0
            except asyncpg.PostgresError as e:
                logger.error("db_count_error", tenant_id=tenant_id, error=str(e))
                raise

    # Add your custom query methods here
    # Examples:
    #
    # async def get_by_name(self, name: str, tenant_id: str) -> Optional[Dict]:
    #     """Find entity by name."""
    #     ...
    #
    # async def search(self, query: str, tenant_id: str) -> List[Dict]:
    #     """Full-text search entities."""
    #     ...


# TESTING NOTES:
# - Test with real database (integration tests)
# - Use pytest fixtures for database setup/teardown
# - Test tenant isolation (can't access other tenant's data)
# - Test error cases (connection failures, constraint violations)
#
# Example test:
#
# @pytest.mark.integration
# async def test_get_by_id_returns_entity(pool, test_tenant):
#     repo = EntityRepository(pool)
#
#     # Arrange: Create test entity
#     entity_data = {
#         'tenant_id': test_tenant,
#         'name': 'Test Entity',
#         'value': 123
#     }
#     created = await repo.insert(entity_data)
#
#     # Act: Fetch by ID
#     result = await repo.get_by_id(created['id'], test_tenant)
#
#     # Assert
#     assert result is not None
#     assert result['id'] == created['id']
#     assert result['name'] == 'Test Entity'
#
# @pytest.mark.integration
# async def test_get_by_id_enforces_tenant_isolation(pool, test_tenant):
#     repo = EntityRepository(pool)
#
#     # Arrange: Create entity for tenant A
#     entity_data = {'tenant_id': 'tenant_a', 'name': 'Entity A'}
#     created = await repo.insert(entity_data)
#
#     # Act: Try to fetch with tenant B
#     result = await repo.get_by_id(created['id'], 'tenant_b')
#
#     # Assert: Should NOT be able to access
#     assert result is None
