import logging
from typing import Any, Dict, List, Set

import asyncpg

from apps.memory_api.adapters.base import MemoryAdapter
from apps.memory_api.core.contract import (
    DataType,
    EntityContract,
    MemoryContract,
    ValidationResult,
    ValidationViolation,
)

logger = logging.getLogger(__name__)


class PostgresAdapter(MemoryAdapter):
    """
    Validates that a Postgres database schema matches the abstract MemoryContract.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def connect(self) -> None:
        """
        Establishes a connection to the Postgres database by acquiring and releasing from the pool.
        Raises an exception if connection fails.
        """
        async with self.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("Postgres connection successful.")

    async def report(self) -> Dict[str, Any]:
        """
        Generates a report on the current state and configuration of the Postgres database.
        """
        try:
            async with self.pool.acquire() as conn:
                db_name = await conn.fetchval("SELECT current_database()")
                db_user = await conn.fetchval("SELECT current_user")
                server_version = await conn.fetchval("SHOW server_version")
                return {
                    "status": "connected",
                    "database_name": db_name,
                    "user": db_user,
                    "server_version": server_version,
                    "pool_size": self.pool.get_size(),
                    "pool_free": self.pool.get_free(),
                }
        except Exception as e:
            logger.error(f"Postgres report generation failed: {e}")
            return {"status": "error", "details": str(e)}

    async def validate(self, contract: MemoryContract) -> ValidationResult:
        violations: List[ValidationViolation] = []

        try:
            async with self.pool.acquire() as conn:
                existing_tables = await self._get_tables(conn)

                for entity in contract.entities:
                    if entity.name not in existing_tables:
                        violations.append(
                            ValidationViolation(
                                entity=entity.name,
                                issue_type="MISSING_TABLE",
                                details=f"Table '{entity.name}' is missing.",
                            )
                        )
                        continue

                    # Validate Columns
                    columns = await self._get_columns(conn, entity.name)
                    entity_violations = self._validate_columns(entity, columns)
                    violations.extend(entity_violations)

            return ValidationResult(valid=len(violations) == 0, violations=violations)
        except Exception as e:
            logger.error(f"Postgres validation failed with exception: {e}")
            return ValidationResult(
                valid=False,
                violations=[
                    ValidationViolation(
                        entity="postgres",
                        issue_type="CONNECTION_ERROR",
                        details=str(e),
                    )
                ],
            )

    async def _get_tables(self, conn: asyncpg.Connection) -> Set[str]:
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """
        rows = await conn.fetch(query)
        return {row["table_name"] for row in rows}

    async def _get_columns(
        self, conn: asyncpg.Connection, table_name: str
    ) -> Dict[str, str]:
        """Returns a dict of column_name -> data_type (or udt_name)"""
        query = """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = $1 AND table_schema = 'public'
        """
        rows = await conn.fetch(query, table_name)
        # Use udt_name for specific types like vector or distinct user types
        # For arrays, data_type is 'ARRAY', udt_name is '_text' (for text[])
        return {
            row["column_name"]: row["udt_name"] if row["udt_name"] else row["data_type"]
            for row in rows
        }

    def _validate_columns(
        self, entity: EntityContract, existing_columns: Dict[str, str]
    ) -> List[ValidationViolation]:
        violations = []
        for field in entity.fields:
            if field.name not in existing_columns:
                violations.append(
                    ValidationViolation(
                        entity=entity.name,
                        issue_type="MISSING_COLUMN",
                        details=f"Column '{field.name}' is missing in table '{entity.name}'.",
                    )
                )
                continue

            actual_type = existing_columns[field.name].lower()
            if not self._check_type_compatibility(field.data_type, actual_type):
                violations.append(
                    ValidationViolation(
                        entity=entity.name,
                        issue_type="TYPE_MISMATCH",
                        details=f"Column '{field.name}' expected {field.data_type.value}, found '{actual_type}'.",
                    )
                )

        return violations

    def _check_type_compatibility(self, expected: DataType, actual: str) -> bool:
        # Simple compatibility map. Can be expanded.
        mapping = {
            DataType.TEXT: ["text", "varchar", "char", "name"],
            DataType.INTEGER: ["int4", "int8", "serial", "bigserial", "integer"],
            DataType.FLOAT: [
                "float4",
                "float8",
                "numeric",
                "real",
                "double precision",
            ],
            DataType.BOOLEAN: ["bool", "boolean"],
            DataType.TIMESTAMP: [
                "timestamp",
                "timestamptz",
                "date",
                "timestamp with time zone",
                "timestamp without time zone",
            ],
            DataType.JSONB: ["json", "jsonb"],
            DataType.UUID: ["uuid"],
            DataType.VECTOR: ["vector"],
            DataType.ARRAY_TEXT: ["_text", "text[]", "_varchar"],
        }

        compatible_types = mapping.get(expected, [])
        return actual in compatible_types
