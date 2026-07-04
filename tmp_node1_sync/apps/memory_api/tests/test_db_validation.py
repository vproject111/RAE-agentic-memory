from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest

from apps.memory_api.core.contract_definition import RAE_MEMORY_CONTRACT_V1
from rae_adapters.postgres_adapter import PostgresAdapter


@pytest.mark.asyncio
async def test_postgres_connect_success():
    pool = MagicMock()
    conn = AsyncMock()
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__.return_value = conn
    acquire_ctx.__aexit__.return_value = None
    pool.acquire.return_value = acquire_ctx
    conn.fetchval.return_value = 1  # Simulate successful query

    adapter = PostgresAdapter(pool)
    await adapter.connect()
    pool.acquire.assert_called_once()
    conn.fetchval.assert_called_once_with("SELECT 1")


@pytest.mark.asyncio
async def test_postgres_connect_fail():
    pool = MagicMock()
    pool.acquire.side_effect = asyncpg.exceptions.PostgresError("Connection refused")

    adapter = PostgresAdapter(pool)
    with pytest.raises(asyncpg.exceptions.PostgresError, match="Connection refused"):
        await adapter.connect()
    pool.acquire.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_report_success():
    pool = MagicMock()
    conn = AsyncMock()
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__.return_value = conn
    acquire_ctx.__aexit__.return_value = None
    pool.acquire.return_value = acquire_ctx

    conn.fetchval.side_effect = [
        "rae_db",  # current_database()
        "test_user",  # current_user
        "PostgreSQL 14.5",  # SHOW server_version
    ]
    pool.get_size.return_value = 10
    pool.get_free.return_value = 5

    adapter = PostgresAdapter(pool)
    report = await adapter.report()

    assert report["status"] == "connected"
    assert report["database_name"] == "rae_db"
    assert report["user"] == "test_user"
    assert report["server_version"] == "PostgreSQL 14.5"
    assert report["pool_size"] == 10
    assert report["pool_free"] == 5
    assert conn.fetchval.call_count == 3
    pool.get_size.assert_called_once()
    pool.get_free.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_report_fail():
    pool = MagicMock()
    pool.acquire.side_effect = asyncpg.exceptions.PostgresError(
        "Report generation failed"
    )

    adapter = PostgresAdapter(pool)
    report = await adapter.report()
    assert report["status"] == "error"
    assert "Report generation failed" in report["details"]
    pool.acquire.assert_called_once()


@pytest.mark.asyncio
async def test_validation_success():
    # Mock pool and connection
    # Mock pool and connection
    pool = MagicMock()
    conn = AsyncMock()

    # Setup pool.acquire() context manager
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__.return_value = conn
    acquire_ctx.__aexit__.return_value = None
    pool.acquire.return_value = acquire_ctx

    # Mock tables query
    conn.fetch.side_effect = [
        # 1. get_tables -> [{'table_name': 'memories'}]
        [{"table_name": "memories"}],
        # 2. get_columns for 'memories'
        # Must match RAE_MEMORY_CONTRACT_V1
        [
            {"column_name": "id", "data_type": "uuid", "udt_name": "uuid"},
            {"column_name": "tenant_id", "data_type": "uuid", "udt_name": "uuid"},
            {"column_name": "content", "data_type": "text", "udt_name": "text"},
            {"column_name": "source", "data_type": "text", "udt_name": "text"},
            {
                "column_name": "importance",
                "data_type": "double precision",
                "udt_name": "float8",
            },
            {"column_name": "layer", "data_type": "text", "udt_name": "text"},
            {"column_name": "tags", "data_type": "ARRAY", "udt_name": "_text"},
            {
                "column_name": "timestamp",
                "data_type": "timestamp without time zone",
                "udt_name": "timestamp",
            },
            {"column_name": "project", "data_type": "text", "udt_name": "text"},
            {"column_name": "memory_type", "data_type": "text", "udt_name": "text"},
            {"column_name": "session_id", "data_type": "text", "udt_name": "text"},
            {"column_name": "metadata", "data_type": "jsonb", "udt_name": "jsonb"},
            {
                "column_name": "created_at",
                "data_type": "timestamp without time zone",
                "udt_name": "timestamp",
            },
            {
                "column_name": "last_accessed_at",
                "data_type": "timestamp without time zone",
                "udt_name": "timestamp",
            },
            {"column_name": "usage_count", "data_type": "integer", "udt_name": "int4"},
            {
                "column_name": "strength",
                "data_type": "double precision",
                "udt_name": "float8",
            },
            {
                "column_name": "embedding",
                "data_type": "USER-DEFINED",
                "udt_name": "vector",
            },
        ],
    ]

    validator = PostgresAdapter(pool)
    result = await validator.validate(RAE_MEMORY_CONTRACT_V1)

    assert result.valid is True
    assert len(result.violations) == 0


@pytest.mark.asyncio
async def test_validation_fail_missing_table():
    # Mock pool and connection
    pool = MagicMock()
    conn = AsyncMock()

    # Setup pool.acquire() context manager
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__.return_value = conn
    acquire_ctx.__aexit__.return_value = None
    pool.acquire.return_value = acquire_ctx

    # Empty tables (first call returns empty list)
    conn.fetch.return_value = []

    validator = PostgresAdapter(pool)
    result = await validator.validate(RAE_MEMORY_CONTRACT_V1)

    assert result.valid is False
    assert any(v.issue_type == "MISSING_TABLE" for v in result.violations)


@pytest.mark.asyncio
async def test_validation_fail_type_mismatch():
    # Mock pool and connection
    pool = MagicMock()
    conn = AsyncMock()

    # Setup pool.acquire() context manager
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__.return_value = conn
    acquire_ctx.__aexit__.return_value = None
    pool.acquire.return_value = acquire_ctx

    conn.fetch.side_effect = [
        [{"table_name": "memories"}],
        [
            # id is integer instead of uuid
            {"column_name": "id", "data_type": "integer", "udt_name": "int4"},
        ],
    ]

    validator = PostgresAdapter(pool)
    result = await validator.validate(RAE_MEMORY_CONTRACT_V1)

    assert result.valid is False
    # Check for TYPE_MISMATCH on 'id'
    # And MISSING_COLUMN for everything else (since we only returned 1 column)

    type_mismatches = [v for v in result.violations if v.issue_type == "TYPE_MISMATCH"]
    assert len(type_mismatches) > 0
    assert "id" in type_mismatches[0].details
    assert "UUID" in type_mismatches[0].details
    assert "int4" in type_mismatches[0].details
