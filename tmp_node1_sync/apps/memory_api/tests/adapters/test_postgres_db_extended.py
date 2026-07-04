from unittest.mock import AsyncMock, MagicMock

import pytest

from rae_adapters.postgres_db import (
    PostgresAcquireContext,
    PostgresDatabaseConnection,
    PostgresDatabaseProvider,
    PostgresTransaction,
)


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    pool.fetchrow = AsyncMock()
    pool.fetch = AsyncMock()
    pool.fetchval = AsyncMock()
    pool.execute = AsyncMock()
    pool.executemany = AsyncMock()
    pool.acquire = MagicMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    conn.executemany = AsyncMock()
    conn.transaction = MagicMock()
    return conn


@pytest.fixture
def provider(mock_pool):
    return PostgresDatabaseProvider(mock_pool)


class TestPostgresDatabaseConnection:
    @pytest.mark.asyncio
    async def test_connection_methods(self, mock_conn):
        conn_wrapper = PostgresDatabaseConnection(mock_conn)

        mock_conn.fetchrow.return_value = {"id": 1}
        assert await conn_wrapper.fetchrow("query") == {"id": 1}

        mock_conn.fetch.return_value = [{"id": 1}]
        assert await conn_wrapper.fetch("query") == [{"id": 1}]

        mock_conn.fetchval.return_value = 1
        assert await conn_wrapper.fetchval("query") == 1

        mock_conn.execute.return_value = "OK"
        assert await conn_wrapper.execute("query") == "OK"

        mock_conn.executemany.return_value = "OK"
        assert await conn_wrapper.executemany("query", []) == "OK"

        mock_conn.transaction.return_value = MagicMock()
        assert isinstance(conn_wrapper.transaction(), PostgresTransaction)


class TestPostgresTransaction:
    @pytest.mark.asyncio
    async def test_transaction_methods(self):
        mock_tx = MagicMock()
        mock_tx.__aenter__ = AsyncMock()
        mock_tx.__aexit__ = AsyncMock()
        mock_tx.commit = AsyncMock()
        mock_tx.rollback = AsyncMock()

        tx_wrapper = PostgresTransaction(mock_tx)

        async with tx_wrapper:
            pass

        mock_tx.__aenter__.assert_called_once()
        mock_tx.__aexit__.assert_called_once()

        await tx_wrapper.commit()
        mock_tx.commit.assert_called_once()

        await tx_wrapper.rollback()
        mock_tx.rollback.assert_called_once()


class TestPostgresAcquireContext:
    @pytest.mark.asyncio
    async def test_acquire_context(self, mock_pool, mock_conn):
        mock_acq = MagicMock()
        mock_acq.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acq.__aexit__ = AsyncMock()
        mock_pool.acquire.return_value = mock_acq

        context = PostgresAcquireContext(mock_pool)

        async with context as conn:
            assert isinstance(conn, PostgresDatabaseConnection)
            assert conn._connection == mock_conn

        mock_acq.__aenter__.assert_called_once()
        mock_acq.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_provider_acquire_returns_context(provider, mock_pool):
    ctx = provider.acquire()
    assert isinstance(ctx, PostgresAcquireContext)
