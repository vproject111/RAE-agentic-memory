"""
Integration test fixtures with real database connections.

These fixtures provide real asyncpg pools for integration tests that need
to interact with an actual database.
"""

import asyncpg
import pytest_asyncio

from apps.memory_api.config import settings


@pytest_asyncio.fixture(scope="function")
async def mock_app_state_pool():
    """
    Override the mock_app_state_pool fixture for integration tests.

    This fixture provides a real asyncpg pool instead of a mock,
    allowing integration tests to execute actual database operations.

    Note: Tests using this fixture will interact with the real database.
    """
    # Create real pool (hardcode localhost for tests running outside Docker)
    pool = await asyncpg.create_pool(
        host="localhost",  # Always use localhost for local pytest runs
        port=5432,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        min_size=1,
        max_size=5,
    )

    yield pool

    # Cleanup
    await pool.close()
