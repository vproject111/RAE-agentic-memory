from unittest.mock import AsyncMock, MagicMock

import pytest

from rae_core.adapters.postgres_db import PostgresDatabaseProvider


class TestPostgresDatabaseProvider:
    @pytest.fixture
    def mock_pool(self):
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
    def provider(self, mock_pool):
        return PostgresDatabaseProvider(mock_pool)

    @pytest.mark.asyncio
    async def test_fetchrow(self, provider, mock_pool):
        mock_pool.fetchrow.return_value = {"id": 1, "name": "test"}
        result = await provider.fetchrow("SELECT * FROM table WHERE id = $1", 1)
        assert result == {"id": 1, "name": "test"}
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetchrow_none(self, provider, mock_pool):
        mock_pool.fetchrow.return_value = None
        result = await provider.fetchrow("SELECT * FROM table")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch(self, provider, mock_pool):
        mock_pool.fetch.return_value = [{"id": 1}, {"id": 2}]
        result = await provider.fetch("SELECT id FROM table")
        assert result == [{"id": 1}, {"id": 2}]
        mock_pool.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetchval(self, provider, mock_pool):
        mock_pool.fetchval.return_value = 42
        result = await provider.fetchval("SELECT count(*) FROM table")
        assert result == 42
        mock_pool.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute(self, provider, mock_pool):
        mock_pool.execute.return_value = "UPDATE 1"
        result = await provider.execute("UPDATE table SET name = $1", "new")
        assert result == "UPDATE 1"
        mock_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_executemany(self, provider, mock_pool):
        mock_pool.executemany.return_value = "INSERT 2"
        result = await provider.executemany("INSERT INTO table VALUES ($1)", [1, 2])
        assert result == "INSERT 2"
        mock_pool.executemany.assert_called_once()

    def test_acquire(self, provider, mock_pool):
        provider.acquire()
        mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, provider, mock_pool):
        await provider.close()
        mock_pool.close.assert_called_once()
