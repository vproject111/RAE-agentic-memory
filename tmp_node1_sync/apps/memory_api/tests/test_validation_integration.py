import os

import asyncpg
import pytest

from apps.memory_api.core.contract_definition import RAE_MEMORY_CONTRACT_V1
from rae_adapters.postgres_adapter import PostgresAdapter

# Only run this if we are in an environment that supports integration tests
# (e.g., has a DB connection string)
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://rae:rae_password@localhost:5432/rae"
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_database_matches_contract():
    """
    CRITICAL INTEGRATION TEST:
    Verifies that the ACTUAL running PostgreSQL database schema
    matches the RAE Memory Contract.

    This test connects to the real DB (not a mock) and runs the validator.
    If this fails, it means our Alembic migrations are out of sync with our code contract.
    """
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
    except Exception as e:
        pytest.skip(f"Could not connect to database at {DATABASE_URL}: {e}")
        return

    try:
        adapter = PostgresAdapter(pool)

        # 1. Check connection
        await adapter.connect()

        # 2. Run full validation against the V1 contract
        result = await adapter.validate(RAE_MEMORY_CONTRACT_V1)

        # 3. Assert validity
        error_messages = "\n".join(
            [f"- {v.issue_type}: {v.details}" for v in result.violations]
        )
        assert (
            result.valid is True
        ), f"Database Schema Violation Detected!\n{error_messages}"

    finally:
        await pool.close()
