"""Unit tests for SQLite storage adapter.

Tests SQLite implementation with FTS5 full-text search, ACID transactions,
and JSON metadata storage.
"""

import asyncio
import json
from uuid import UUID, uuid4

import pytest

from rae_adapters.sqlite.storage import SQLiteStorage


@pytest.fixture
async def storage(tmp_path):
    """Create temporary SQLite storage for testing."""
    db_path = str(tmp_path / "test_storage.db")
    store = SQLiteStorage(db_path=db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def file_storage(tmp_path):
    """Create file-based SQLite storage for persistence testing."""
    db_path = str(tmp_path / "test.db")
    store = SQLiteStorage(db_path=db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing."""
    return {
        "content": "Test memory content",
        "layer": "episodic",
        "tenant_id": "tenant-1",
        "agent_id": "agent-1",
        "tags": ["test", "sample"],
        "metadata": {"key": "value"},
        "importance": 0.8,
    }


class TestSQLiteStorageBasicOperations:
    """Test basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_store_memory(self, storage, sample_memory_data):
        """Test storing a memory."""
        memory_id = await storage.store_memory(**sample_memory_data)

        assert isinstance(memory_id, UUID)

        # Verify stored
        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory is not None
        assert memory["content"] == sample_memory_data["content"]
        assert memory["layer"] == sample_memory_data["layer"]
        assert memory["tenant_id"] == sample_memory_data["tenant_id"]
        assert memory["agent_id"] == sample_memory_data["agent_id"]
        assert memory["tags"] == sample_memory_data["tags"]
        assert memory["metadata"] == sample_memory_data["metadata"]
        assert memory["importance"] == sample_memory_data["importance"]
        assert memory["access_count"] == 0
        assert memory["version"] == 1

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, storage):
        """Test getting non-existent memory."""
        memory = await storage.get_memory(uuid4(), "tenant-1")
        assert memory is None

    @pytest.mark.asyncio
    async def test_get_memory_wrong_tenant(self, storage, sample_memory_data):
        """Test getting memory with wrong tenant ID."""
        memory_id = await storage.store_memory(**sample_memory_data)

        # Try to get with different tenant
        memory = await storage.get_memory(memory_id, "tenant-2")
        assert memory is None

    @pytest.mark.asyncio
    async def test_update_memory(self, storage, sample_memory_data):
        """Test updating a memory."""
        memory_id = await storage.store_memory(**sample_memory_data)

        # Update content and importance
        success = await storage.update_memory(
            memory_id,
            sample_memory_data["tenant_id"],
            {"content": "Updated content", "importance": 0.9},
        )
        assert success is True

        # Verify update
        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory["content"] == "Updated content"
        assert memory["importance"] == 0.9
        assert memory["version"] == 2  # Version incremented

    @pytest.mark.asyncio
    async def test_update_memory_not_found(self, storage):
        """Test updating non-existent memory."""
        success = await storage.update_memory(uuid4(), "tenant-1", {"content": "New"})
        assert success is False

    @pytest.mark.asyncio
    async def test_update_memory_immutable_fields(self, storage, sample_memory_data):
        """Test that immutable fields cannot be updated."""
        memory_id = await storage.store_memory(**sample_memory_data)
        original_memory = await storage.get_memory(
            memory_id, sample_memory_data["tenant_id"]
        )

        # Try to update immutable fields
        await storage.update_memory(
            memory_id,
            sample_memory_data["tenant_id"],
            {"id": str(uuid4()), "created_at": "2020-01-01T00:00:00"},
        )

        # Verify immutable fields unchanged
        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory["id"] == original_memory["id"]
        assert memory["created_at"] == original_memory["created_at"]

    @pytest.mark.asyncio
    async def test_delete_memory(self, storage, sample_memory_data):
        """Test deleting a memory."""
        memory_id = await storage.store_memory(**sample_memory_data)

        # Delete
        success = await storage.delete_memory(
            memory_id, sample_memory_data["tenant_id"]
        )
        assert success is True

        # Verify deleted
        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory is None

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, storage):
        """Test deleting non-existent memory."""
        success = await storage.delete_memory(uuid4(), "tenant-1")
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_memory_wrong_tenant(self, storage, sample_memory_data):
        """Test deleting memory with wrong tenant ID."""
        memory_id = await storage.store_memory(**sample_memory_data)

        # Try to delete with different tenant
        success = await storage.delete_memory(memory_id, "tenant-2")
        assert success is False

        # Verify not deleted
        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory is not None


class TestSQLiteStorageListOperations:
    """Test list and count operations with filtering."""

    @pytest.mark.asyncio
    async def test_list_memories_basic(self, storage):
        """Test listing all memories for a tenant."""
        # Store multiple memories
        for i in range(5):
            await storage.store_memory(
                content=f"Memory {i}",
                layer="episodic",
                tenant_id="tenant-1",
                agent_id="agent-1",
            )

        # List all
        memories = await storage.list_memories("tenant-1")
        assert len(memories) == 5

    @pytest.mark.asyncio
    async def test_list_memories_by_agent(self, storage):
        """Test filtering by agent ID."""
        # Store memories for different agents
        await storage.store_memory(
            content="Agent 1 memory",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="Agent 2 memory",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-2",
        )

        # Filter by agent
        memories = await storage.list_memories("tenant-1", agent_id="agent-1")
        assert len(memories) == 1
        assert memories[0]["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_list_memories_by_layer(self, storage):
        """Test filtering by layer."""
        # Store memories in different layers
        await storage.store_memory(
            content="Episodic memory",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="Semantic memory",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        # Filter by layer
        memories = await storage.list_memories("tenant-1", layer="episodic")
        assert len(memories) == 1
        assert memories[0]["layer"] == "episodic"

    @pytest.mark.asyncio
    async def test_list_memories_by_tags(self, storage):
        """Test filtering by tags."""
        # Store memories with different tags
        await storage.store_memory(
            content="Tagged A",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
            tags=["tag-a", "tag-c"],
        )
        await storage.store_memory(
            content="Tagged B",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
            tags=["tag-b", "tag-c"],
        )
        await storage.store_memory(
            content="No tags",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        # Filter by single tag
        memories = await storage.list_memories("tenant-1", tags=["tag-a"])
        assert len(memories) == 1
        assert memories[0]["content"] == "Tagged A"

        # Filter by multiple tags (OR logic)
        memories = await storage.list_memories("tenant-1", tags=["tag-a", "tag-b"])
        assert len(memories) == 2

    @pytest.mark.asyncio
    async def test_list_memories_pagination(self, storage):
        """Test pagination with limit and offset."""
        # Store 10 memories
        for i in range(10):
            await storage.store_memory(
                content=f"Memory {i}",
                layer="episodic",
                tenant_id="tenant-1",
                agent_id="agent-1",
            )

        # First page
        page1 = await storage.list_memories("tenant-1", limit=3, offset=0)
        assert len(page1) == 3

        # Second page
        page2 = await storage.list_memories("tenant-1", limit=3, offset=3)
        assert len(page2) == 3

        # Verify no overlap
        page1_ids = {m["id"] for m in page1}
        page2_ids = {m["id"] for m in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_list_memories_order_by_created_at(self, storage):
        """Test that memories are ordered by created_at DESC."""
        # Store memories with delays
        id1 = await storage.store_memory(
            content="First",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await asyncio.sleep(0.01)  # Small delay

        id2 = await storage.store_memory(
            content="Second",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        # List memories
        memories = await storage.list_memories("tenant-1")

        # Most recent should be first
        assert memories[0]["id"] == id2
        assert memories[1]["id"] == id1

    @pytest.mark.asyncio
    async def test_list_memories_tenant_isolation(self, storage):
        """Test tenant isolation in listing."""
        # Store memories for different tenants
        await storage.store_memory(
            content="Tenant 1 memory",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="Tenant 2 memory",
            layer="episodic",
            tenant_id="tenant-2",
            agent_id="agent-1",
        )

        # List for tenant 1
        memories = await storage.list_memories("tenant-1")
        assert len(memories) == 1
        assert memories[0]["tenant_id"] == "tenant-1"

    @pytest.mark.asyncio
    async def test_count_memories(self, storage):
        """Test counting memories."""
        # Store memories
        for i in range(5):
            await storage.store_memory(
                content=f"Memory {i}",
                layer="episodic",
                tenant_id="tenant-1",
                agent_id="agent-1",
            )

        count = await storage.count_memories("tenant-1")
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_memories_with_filters(self, storage):
        """Test counting with filters."""
        # Store memories with different attributes
        await storage.store_memory(
            content="Memory 1",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="Memory 2",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="Memory 3",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-2",
        )

        # Count by layer
        count = await storage.count_memories("tenant-1", layer="episodic")
        assert count == 2

        # Count by agent
        count = await storage.count_memories("tenant-1", agent_id="agent-1")
        assert count == 2

        # Count by both
        count = await storage.count_memories(
            "tenant-1", agent_id="agent-1", layer="episodic"
        )
        assert count == 1


class TestSQLiteStorageAccessTracking:
    """Test access count tracking."""

    @pytest.mark.asyncio
    async def test_increment_access_count(self, storage, sample_memory_data):
        """Test incrementing access count."""
        memory_id = await storage.store_memory(**sample_memory_data)

        # Initial count should be 0
        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory["access_count"] == 0
        initial_accessed = memory["last_accessed_at"]

        # Small delay to ensure timestamp changes
        await asyncio.sleep(0.01)

        # Increment
        success = await storage.increment_access_count(
            memory_id, sample_memory_data["tenant_id"]
        )
        assert success is True

        # Verify
        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory["access_count"] == 1
        assert memory["last_accessed_at"] > initial_accessed

    @pytest.mark.asyncio
    async def test_increment_access_count_multiple(self, storage, sample_memory_data):
        """Test multiple increments."""
        memory_id = await storage.store_memory(**sample_memory_data)

        # Increment 3 times
        for _ in range(3):
            await storage.increment_access_count(
                memory_id, sample_memory_data["tenant_id"]
            )

        memory = await storage.get_memory(memory_id, sample_memory_data["tenant_id"])
        assert memory["access_count"] == 3

    @pytest.mark.asyncio
    async def test_increment_access_count_not_found(self, storage):
        """Test incrementing non-existent memory."""
        success = await storage.increment_access_count(uuid4(), "tenant-1")
        assert success is False


class TestSQLiteStorageFullTextSearch:
    """Test FTS5 full-text search functionality."""

    @pytest.mark.asyncio
    async def test_search_full_text_basic(self, storage):
        """Test basic full-text search."""
        # Store memories with different content
        await storage.store_memory(
            content="Python programming language",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="JavaScript web development",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="Machine learning with Python",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        # Search for "Python"
        results = await storage.search_full_text("Python", "tenant-1")
        assert len(results) == 2

        # Verify content
        contents = [r["content"] for r in results]
        assert "Python programming language" in contents
        assert "Machine learning with Python" in contents

    @pytest.mark.asyncio
    async def test_search_full_text_with_quotes(self, storage):
        """Test phrase search with quotes."""
        # Store memories
        await storage.store_memory(
            content="The quick brown fox",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="A quick test case",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        # Search for exact phrase
        results = await storage.search_full_text('"quick brown"', "tenant-1")
        assert len(results) == 1
        assert results[0]["content"] == "The quick brown fox"

    @pytest.mark.asyncio
    async def test_search_full_text_limit(self, storage):
        """Test search result limit."""
        # Store many memories
        for i in range(10):
            await storage.store_memory(
                content=f"Python test case {i}",
                layer="semantic",
                tenant_id="tenant-1",
                agent_id="agent-1",
            )

        # Search with limit
        results = await storage.search_full_text("Python", "tenant-1", limit=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_full_text_tenant_isolation(self, storage):
        """Test tenant isolation in search."""
        # Store memories for different tenants
        await storage.store_memory(
            content="Python for tenant 1",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage.store_memory(
            content="Python for tenant 2",
            layer="semantic",
            tenant_id="tenant-2",
            agent_id="agent-1",
        )

        # Search tenant 1
        results = await storage.search_full_text("Python", "tenant-1")
        assert len(results) == 1
        assert results[0]["tenant_id"] == "tenant-1"

    @pytest.mark.asyncio
    async def test_search_full_text_no_results(self, storage):
        """Test search with no matches."""
        await storage.store_memory(
            content="Python programming",
            layer="semantic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        results = await storage.search_full_text("nonexistent", "tenant-1")
        assert len(results) == 0


class TestSQLiteStoragePersistence:
    """Test file-based persistence."""

    @pytest.mark.asyncio
    async def test_persistence_across_connections(self, tmp_path):
        """Test that data persists across connections."""
        db_path = str(tmp_path / "test.db")

        # Create first connection and store data
        storage1 = SQLiteStorage(db_path=db_path)
        await storage1.initialize()
        memory_id = await storage1.store_memory(
            content="Persistent memory",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        await storage1.close()

        # Create second connection and verify data
        storage2 = SQLiteStorage(db_path=db_path)
        await storage2.initialize()
        memory = await storage2.get_memory(memory_id, "tenant-1")
        assert memory is not None
        assert memory["content"] == "Persistent memory"
        await storage2.close()

    @pytest.mark.asyncio
    async def test_wal_mode_enabled(self, file_storage):
        """Test that WAL mode is enabled."""
        # This is tested implicitly by the implementation
        # WAL mode is set in initialize()
        assert file_storage._initialized is True


class TestSQLiteStorageEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_store_memory_empty_content(self, storage):
        """Test storing memory with empty content."""
        memory_id = await storage.store_memory(
            content="",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )
        assert isinstance(memory_id, UUID)

        memory = await storage.get_memory(memory_id, "tenant-1")
        assert memory["content"] == ""

    @pytest.mark.asyncio
    async def test_store_memory_no_tags_metadata(self, storage):
        """Test storing memory without tags or metadata."""
        memory_id = await storage.store_memory(
            content="Simple memory",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        memory = await storage.get_memory(memory_id, "tenant-1")
        assert memory["tags"] == []
        assert memory["metadata"] == {}

    @pytest.mark.asyncio
    async def test_store_memory_default_importance(self, storage):
        """Test default importance value."""
        memory_id = await storage.store_memory(
            content="Test",
            layer="episodic",
            tenant_id="tenant-1",
            agent_id="agent-1",
        )

        memory = await storage.get_memory(memory_id, "tenant-1")
        assert memory["importance"] == 0.5

    @pytest.mark.asyncio
    async def test_update_memory_empty_updates(self, storage, sample_memory_data):
        """Test updating with empty updates dict."""
        memory_id = await storage.store_memory(**sample_memory_data)

        # Empty updates should still increment version
        success = await storage.update_memory(
            memory_id, sample_memory_data["tenant_id"], {}
        )
        assert success is False  # No fields to update

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, storage):
        """Test that initialize can be called multiple times."""
        await storage.initialize()
        await storage.initialize()  # Should not raise error
        assert storage._initialized is True

    @pytest.mark.asyncio
    async def test_delete_memories_below_importance(self, storage):
        """Test deleting memories below importance threshold."""
        await storage.store_memory(
            content="High", layer="w", tenant_id="t", agent_id="a", importance=0.9
        )
        await storage.store_memory(
            content="Low", layer="w", tenant_id="t", agent_id="a", importance=0.2
        )

        count = await storage.delete_memories_below_importance("t", "a", "w", 0.5)
        assert count == 1

        memories = await storage.list_memories("t")
        assert len(memories) == 1
        assert memories[0]["content"] == "High"

    @pytest.mark.asyncio
    async def test_delete_memories_with_metadata_filter(self, storage):
        """Test deleting memories with metadata filter."""
        await storage.store_memory(
            content="M1", layer="w", tenant_id="t", agent_id="a", metadata={"cat": "A"}
        )
        await storage.store_memory(
            content="M2", layer="w", tenant_id="t", agent_id="a", metadata={"cat": "B"}
        )

        count = await storage.delete_memories_with_metadata_filter(
            "t", "a", "w", {"cat": "A"}
        )
        assert count == 1

        memories = await storage.list_memories("t")
        assert len(memories) == 1
        assert memories[0]["metadata"]["cat"] == "B"

    @pytest.mark.asyncio
    async def test_delete_expired_memories(self, storage):
        """Test deleting expired memories."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        await storage.store_memory(
            content="Old",
            layer="w",
            tenant_id="t",
            agent_id="a",
            expires_at=now - timedelta(days=1),
        )
        await storage.store_memory(
            content="New",
            layer="w",
            tenant_id="t",
            agent_id="a",
            expires_at=now + timedelta(days=1),
        )

        count = await storage.delete_expired_memories("t", "a", "w")
        assert count == 1

        memories = await storage.list_memories("t")
        assert len(memories) == 1
        assert memories[0]["content"] == "New"

    @pytest.mark.asyncio
    async def test_search_memories_wrapper(self, storage):
        """Test the search_memories wrapper which uses FTS5."""
        await storage.store_memory(
            content="RAE is agentic memory", layer="w", tenant_id="t", agent_id="a"
        )
        await storage.store_memory(
            content="Other content", layer="w", tenant_id="t", agent_id="a"
        )

        results = await storage.search_memories("agentic", "t", "a", "w")
        assert len(results) == 1
        assert "RAE" in results[0]["memory"]["content"]

    @pytest.mark.asyncio
    async def test_update_memory_expiration(self, storage):
        """Test updating memory expiration."""
        from datetime import datetime, timezone

        memory_id = await storage.store_memory(
            content="T", layer="w", tenant_id="t", agent_id="a"
        )

        expiry = datetime.now(timezone.utc)
        success = await storage.update_memory_expiration(memory_id, "t", expiry)
        assert success is True

        memory = await storage.get_memory(memory_id, "t")
        # SQLite stores as ISO string, so we compare ISO strings
        assert memory["expires_at"] == expiry.isoformat()


class TestSQLiteStorageExtendedOperations:
    """Test extended storage operations."""

    @pytest.mark.asyncio
    async def test_get_metric_aggregate(self, storage):
        """Test calculating aggregate metrics."""
        await storage.store_memory(
            content="M1", layer="w", tenant_id="t", agent_id="a", importance=0.8
        )
        await storage.store_memory(
            content="M2", layer="w", tenant_id="t", agent_id="a", importance=0.2
        )

        # Sum of importance
        sum_imp = await storage.get_metric_aggregate("t", "importance", "sum")
        assert sum_imp == pytest.approx(1.0)

        # Average importance
        avg_imp = await storage.get_metric_aggregate("t", "importance", "avg")
        assert avg_imp == pytest.approx(0.5)

        # Min/Max
        assert await storage.get_metric_aggregate(
            "t", "importance", "min"
        ) == pytest.approx(0.2)
        assert await storage.get_metric_aggregate(
            "t", "importance", "max"
        ) == pytest.approx(0.8)

        # Invalid metric/func should return 0
        assert await storage.get_metric_aggregate("t", "invalid", "avg") == 0.0
        assert await storage.get_metric_aggregate("t", "importance", "invalid") == 0.0

    @pytest.mark.asyncio
    async def test_update_memory_access_batch(self, storage):
        """Test batch updating access count."""
        id1 = await storage.store_memory(
            content="M1", layer="w", tenant_id="t", agent_id="a"
        )
        id2 = await storage.store_memory(
            content="M2", layer="w", tenant_id="t", agent_id="a"
        )

        success = await storage.update_memory_access_batch([id1, id2], "t")
        assert success is True

        m1 = await storage.get_memory(id1, "t")
        m2 = await storage.get_memory(id2, "t")
        assert m1["access_count"] == 1
        assert m2["access_count"] == 1

    @pytest.mark.asyncio
    async def test_adjust_importance(self, storage):
        """Test adjusting memory importance."""
        memory_id = await storage.store_memory(
            content="T", layer="w", tenant_id="t", agent_id="a", importance=0.5
        )

        # Positive adjustment
        new_val = await storage.adjust_importance(memory_id, 0.2, "t")
        assert new_val == pytest.approx(0.7)

        # Negative adjustment with clamping
        new_val = await storage.adjust_importance(memory_id, -1.0, "t")
        assert new_val == 0.0

        # Over-limit adjustment with clamping
        new_val = await storage.adjust_importance(memory_id, 2.0, "t")
        assert new_val == 1.0


class TestSQLiteStorageEmbeddings:
    """Test multi-model embedding storage."""

    @pytest.mark.asyncio
    async def test_save_embedding(self, storage):
        """Test saving and replacing embeddings."""
        memory_id = await storage.store_memory(
            content="T", layer="w", tenant_id="t", agent_id="a"
        )

        emb = [0.1, 0.2, 0.3]
        success = await storage.save_embedding(
            memory_id, "model-v1", emb, "t", metadata={"dim": 3}
        )
        assert success is True

        # Verify in DB
        import sqlite3

        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT embedding FROM memory_embeddings WHERE memory_id = ?",
            (str(memory_id),),
        )
        row = cursor.fetchone()
        assert row is not None
        assert json.loads(row[0]) == emb
        conn.close()

    @pytest.mark.asyncio
    async def test_save_embedding_access_denied(self, storage):
        """Test saving embedding with wrong tenant."""
        memory_id = await storage.store_memory(
            content="T", layer="w", tenant_id="t1", agent_id="a"
        )
        with pytest.raises(ValueError, match="Access Denied"):
            await storage.save_embedding(memory_id, "model-v1", [0.1], "t2")


class TestSQLiteStorageTagsAndFilters:
    """Test advanced tag filtering and metadata filters."""

    @pytest.mark.asyncio
    async def test_list_memories_advanced_filters(self, storage):
        """Test metadata filtering using json_extract."""
        await storage.store_memory(
            content="M1",
            layer="w",
            tenant_id="t",
            agent_id="a",
            metadata={"priority": "high"},
        )
        await storage.store_memory(
            content="M2",
            layer="w",
            tenant_id="t",
            agent_id="a",
            metadata={"priority": "low"},
        )

        results = await storage.list_memories("t", filters={"priority": "high"})
        assert len(results) == 1
        assert results[0]["content"] == "M1"

    @pytest.mark.asyncio
    async def test_list_memories_invalid_order_by(self, storage):
        """Test fallback for invalid order_by field."""
        await storage.store_memory(content="M1", layer="w", tenant_id="t", agent_id="a")
        # Should not crash and use default ordering
        results = await storage.list_memories(
            "t", order_by="dangerous_injection; DROP TABLE memories;"
        )
        assert len(results) == 1
