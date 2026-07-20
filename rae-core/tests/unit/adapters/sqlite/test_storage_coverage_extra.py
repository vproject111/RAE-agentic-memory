from uuid import uuid4

import aiosqlite
import pytest

from rae_core.adapters.sqlite.storage import SQLiteStorage


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    return str(path)


class TestSQLiteStorageCoverage:
    @pytest.mark.asyncio
    async def test_get_memories_batch(self, db_path):
        storage = SQLiteStorage(db_path)
        m1 = await storage.store_memory(
            content="m1", layer="w", tenant_id="t1", agent_id="a1"
        )
        m2 = await storage.store_memory(
            content="m2", layer="w", tenant_id="t1", agent_id="a1"
        )

        results = await storage.get_memories_batch([m1, m2], "t1")
        assert len(results) == 2
        ids = [r["id"] for r in results]
        assert m1 in ids
        assert m2 in ids

    @pytest.mark.asyncio
    async def test_list_memories_offset(self, db_path):
        storage = SQLiteStorage(db_path)
        await storage.store_memory(
            content="m1", layer="w", tenant_id="t1", agent_id="a1"
        )
        await storage.store_memory(
            content="m2", layer="w", tenant_id="t1", agent_id="a1"
        )

        results = await storage.list_memories("t1", limit=1, offset=1)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_full_text_empty(self, db_path):
        storage = SQLiteStorage(db_path)
        results = await storage.search_full_text("", "t1")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_full_text_fallback(self, monkeypatch, db_path):
        storage = SQLiteStorage(db_path)
        await storage.store_memory(
            content="test content", layer="w", tenant_id="t1", agent_id="a1"
        )

        real_execute = aiosqlite.Connection.execute

        call_count = 0

        def mock_execute(self_conn, sql, parameters=None):
            nonlocal call_count
            if "MATCH" in sql:
                call_count += 1
                # We need to return something that when awaited or used in async with, raises OperationalError
                # Actually, aiosqlite.Connection.execute returns a CursorContextManager.
                # If we want it to fail immediately, we can just raise it if it's not async.
                # But aiosqlite calls it and THEN awaits the result if it's a coroutine? No.
                raise aiosqlite.OperationalError("Mocked FTS failure")
            return real_execute(self_conn, sql, parameters)

        monkeypatch.setattr(aiosqlite.Connection, "execute", mock_execute)

        results = await storage.search_full_text("test", "t1")
        assert len(results) == 1
        assert results[0]["content"] == "test content"
        assert call_count > 0

    @pytest.mark.asyncio
    async def test_get_metric_aggregate_exception(self, monkeypatch, db_path):
        storage = SQLiteStorage(db_path)
        await storage.initialize()  # Ensure initialized first

        real_execute = aiosqlite.Connection.execute

        def mock_execute(self_conn, sql, parameters=None):
            if "SELECT" in sql and "FROM memories" in sql:
                raise Exception("Explosion")
            return real_execute(self_conn, sql, parameters)

        monkeypatch.setattr(aiosqlite.Connection, "execute", mock_execute)

        val = await storage.get_metric_aggregate("t1", "importance", "AVG")
        assert val == 0.0

    @pytest.mark.asyncio
    async def test_adjust_importance_missing(self, db_path):
        storage = SQLiteStorage(db_path)
        val = await storage.adjust_importance(uuid4(), 0.1, "t1")
        assert val == 0.0

    @pytest.mark.asyncio
    async def test_save_embedding_missing(self, db_path):
        storage = SQLiteStorage(db_path)
        res = await storage.save_embedding(uuid4(), "model", [0.1], "t1")
        assert res is False

    @pytest.mark.asyncio
    async def test_save_embedding_tenant_mismatch(self, db_path):
        storage = SQLiteStorage(db_path)
        m_id = await storage.store_memory(
            content="m", layer="w", tenant_id="t1", agent_id="a1"
        )

        with pytest.raises(ValueError, match="Access Denied"):
            await storage.save_embedding(m_id, "model", [0.1], "wrong_tenant")

    @pytest.mark.asyncio
    async def test_update_memory_no_updates(self, db_path):
        storage = SQLiteStorage(db_path)
        m_id = await storage.store_memory(
            content="m", layer="w", tenant_id="t1", agent_id="a1"
        )
        res = await storage.update_memory(m_id, "t1", {})
        assert res is False

    @pytest.mark.asyncio
    async def test_update_memory_invalid_fields(self, db_path):
        storage = SQLiteStorage(db_path)
        m_id = await storage.store_memory(
            content="m", layer="w", tenant_id="t1", agent_id="a1"
        )
        res = await storage.update_memory(m_id, "t1", {"invalid": "field"})
        assert res is False

    @pytest.mark.asyncio
    async def test_list_memories_invalid_order_direction(self, db_path):
        storage = SQLiteStorage(db_path)
        await storage.store_memory(
            content="m1", layer="w", tenant_id="t1", agent_id="a1"
        )
        results = await storage.list_memories("t1", order_direction="invalid_dir")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_decay_importance(self, db_path):
        storage = SQLiteStorage(db_path)
        res = await storage.decay_importance("t1", 0.5)
        assert res == 0

    @pytest.mark.asyncio
    async def test_clear_tenant(self, db_path):
        storage = SQLiteStorage(db_path)
        await storage.store_memory(
            content="m1", layer="w", tenant_id="t1", agent_id="a1"
        )
        await storage.store_memory(
            content="m2", layer="w", tenant_id="t2", agent_id="a1"
        )

        count = await storage.clear_tenant("t1")
        assert count == 1

        res1 = await storage.list_memories("t1")
        assert len(res1) == 0
        res2 = await storage.list_memories("t2")
        assert len(res2) == 1
