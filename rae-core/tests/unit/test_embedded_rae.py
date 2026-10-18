"""Unit tests for EmbeddedRAE (Zero-Docker Single-File In-Process Engine)."""

import pytest

from rae_core.embedded import EmbeddedRAE


@pytest.mark.asyncio
async def test_embedded_rae_open_in_memory():
    rae = await EmbeddedRAE.open(":memory:")
    assert rae is not None
    assert rae.storage is not None
    assert rae.vector_store is not None
    await rae.close()


@pytest.mark.asyncio
async def test_embedded_rae_store_and_query():
    rae = await EmbeddedRAE.open(":memory:", tenant_id="tenant_test", project="project_alpha")

    # Store episodic and semantic memories
    mem1_id = await rae.store(
        content="Antigravity uses MCP servers for tool delegation and execution.",
        layer="semantic",
        importance=0.8,
        tags=["antigravity", "mcp"],
    )
    assert mem1_id is not None

    mem2_id = await rae.store(
        content="PostgreSQL database connection pool was tuned to 20 connections.",
        layer="episodic",
        importance=0.7,
        tags=["postgres", "performance"],
    )
    assert mem2_id is not None

    # Query with semantic relevance
    results = await rae.query("How does Antigravity delegate tools?", top_k=5)
    assert len(results) > 0
    contents = [r["content"] for r in results]
    assert any("Antigravity" in c for c in contents)

    await rae.close()


@pytest.mark.asyncio
async def test_embedded_rae_evidence_search():
    rae = await EmbeddedRAE.open(":memory:")

    await rae.store(
        content="Hard Frames mode programmatically blocks RESTRICTED info outside Working layer.",
        layer="semantic",
        importance=0.9,
        tags=["security", "iso42001"],
    )

    evidence_pkg = await rae.search_evidence("security rules for restricted data", limit=5)
    assert evidence_pkg is not None
    assert len(evidence_pkg.items) > 0
    assert any("RESTRICTED" in item.content for item in evidence_pkg.items)

    await rae.close()


@pytest.mark.asyncio
async def test_embedded_rae_consolidation():
    rae = await EmbeddedRAE.open(":memory:")

    # Store similar memories that should be clustered and consolidated
    await rae.store("Qdrant collection dimension mismatch error occurred on vector sync.", layer="episodic", importance=0.6)
    await rae.store("Vector dimension mismatch in Qdrant collection during initialization.", layer="episodic", importance=0.7)

    consolidation_result = await rae.consolidate()
    assert consolidation_result["clusters"] >= 1

    await rae.close()


@pytest.mark.asyncio
async def test_embedded_rae_file_persistence(tmp_path):
    db_file = tmp_path / "agent_memory.db"
    rae1 = await EmbeddedRAE.open(str(db_file), tenant_id="t1", project="p1")

    await rae1.store("Critical fact saved to persistent SQLite file.", layer="semantic", importance=0.95)
    await rae1.close()

    # Reopen same SQLite file and verify persistence
    rae2 = await EmbeddedRAE.open(str(db_file), tenant_id="t1", project="p1")
    results = await rae2.query("persistent SQLite file", top_k=5)
    assert len(results) > 0
    assert "Critical fact" in results[0]["content"]

    await rae2.close()


@pytest.mark.asyncio
async def test_embedded_rae_crud_lifecycle():
    rae = await EmbeddedRAE.open(":memory:", tenant_id="t_crud", project="p_crud")

    # 1. Store
    mem_id = await rae.store(
        content="Testing EmbeddedRAE CRUD lifecycle operations.",
        layer="episodic",
        importance=0.85,
        tags=["crud", "test"],
    )
    assert mem_id is not None

    # 2. Get
    item = await rae.get(mem_id)
    assert item is not None
    assert item["content"] == "Testing EmbeddedRAE CRUD lifecycle operations."
    assert item["layer"] == "episodic"

    # 3. List
    items = await rae.list(layer="episodic")
    assert len(items) >= 1
    assert any(str(i["id"]) == str(mem_id) for i in items)

    # 4. Delete
    deleted = await rae.delete(mem_id)
    assert deleted is True

    # 5. Verify deleted
    item_after = await rae.get(mem_id)
    assert item_after is None

    await rae.close()
