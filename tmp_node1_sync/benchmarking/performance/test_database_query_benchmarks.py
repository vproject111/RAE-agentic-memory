import os

import asyncpg
import pytest


# Fixture to provide a database connection pool
@pytest.fixture(scope="function")
async def db_pool():
    # Use environment variables or a config for connection details
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_rae"
    )
    pool = await asyncpg.create_pool(db_url)
    yield pool
    await pool.close()


@pytest.fixture(scope="function")
async def setup_db(db_pool):
    # Ensure table exists for benchmarking
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS benchmark_data (
                id SERIAL PRIMARY KEY,
                value TEXT
            );
        """
        )
        # Insert some initial data
        await conn.execute(
            "INSERT INTO benchmark_data (value) SELECT 'test_value_' || generate_series(1, 1000);"
        )
    yield
    # Clean up after tests (optional, depending on testing strategy)
    async with db_pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS benchmark_data;")


# @pytest.mark.performance
# @pytest.mark.asyncio
# async def test_database_read_latency(benchmark, db_pool, setup_db):
#     """
#     Benchmarks the latency of reading a single record from the database.
#     """
#     async def read_from_db():
#         async with db_pool.acquire() as conn:
#             await conn.fetchval("SELECT value FROM benchmark_data WHERE id = $1;", 1)
#
#     # Benchmark the async function
#     await benchmark.pedantic(read_from_db, setup=lambda: None, rounds=10, warmup_rounds=1) # Use pedantic for async
#
# @pytest.mark.performance
# @pytest.mark.asyncio
# async def test_database_insert_latency(benchmark, db_pool, setup_db):
#     """
#     Benchmarks the latency of inserting a single record into the database.
#     """
#     counter = 0
#     async def insert_into_db():
#         nonlocal counter
#         counter += 1
#         async with db_pool.acquire() as conn:
#             await conn.execute("INSERT INTO benchmark_data (value) VALUES ($1);", f"new_value_{counter}")
#
#     # Benchmark the async function
#     await benchmark.pedantic(insert_into_db, setup=lambda: None, rounds=10, warmup_rounds=1)
#
# # Temporarily commenting out database benchmarks due to persistent docker image database user issues.
# # This needs further investigation into the 'ankane/pgvector' image configuration or a switch to a standard PostgreSQL image.
