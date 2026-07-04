from uuid import uuid4

import pytest

from rae_adapters.sqlite.graph import SQLiteGraphStore


@pytest.fixture
async def graph_store(tmp_path):
    db_path = str(tmp_path / "test_graph.db")
    store = SQLiteGraphStore(db_path=db_path)
    await store.initialize()
    yield store
    # close not implemented explicitly but uses context


class TestSQLiteGraphStore:
    @pytest.mark.asyncio
    async def test_create_node(self, graph_store):
        node_id = uuid4()
        success = await graph_store.create_node(
            node_id, "Person", "t1", {"name": "Alice"}
        )
        assert success is True

        # Verify idempotency/update
        success = await graph_store.create_node(
            node_id, "Person", "t1", {"name": "Alice Updated"}
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_create_edge(self, graph_store):
        id1, id2 = uuid4(), uuid4()
        await graph_store.create_node(id1, "P", "t1")
        await graph_store.create_node(id2, "P", "t1")

        success = await graph_store.create_edge(id1, id2, "KNOWS", "t1", weight=0.8)
        assert success is True

    @pytest.mark.asyncio
    async def test_get_neighbors(self, graph_store):
        id1, id2, id3 = uuid4(), uuid4(), uuid4()
        await graph_store.create_node(id1, "P", "t1")
        await graph_store.create_node(id2, "P", "t1")
        await graph_store.create_node(id3, "P", "t1")

        await graph_store.create_edge(id1, id2, "KNOWS", "t1")
        await graph_store.create_edge(id3, id1, "KNOWS", "t1")

        # Both directions
        neighbors = await graph_store.get_neighbors(id1, "t1")
        assert len(neighbors) == 2
        assert id2 in neighbors
        assert id3 in neighbors

        # Out direction
        neighbors = await graph_store.get_neighbors(id1, "t1", direction="out")
        assert len(neighbors) == 1
        assert id2 in neighbors

        # In direction
        neighbors = await graph_store.get_neighbors(id1, "t1", direction="in")
        assert len(neighbors) == 1
        assert id3 in neighbors

    @pytest.mark.asyncio
    async def test_delete_node(self, graph_store):
        node_id = uuid4()
        await graph_store.create_node(node_id, "P", "t1")
        assert await graph_store.delete_node(node_id, "t1") is True
        assert await graph_store.delete_node(node_id, "t1") is False

    @pytest.mark.asyncio
    async def test_delete_edge(self, graph_store):
        id1, id2 = uuid4(), uuid4()
        await graph_store.create_node(id1, "P", "t1")
        await graph_store.create_node(id2, "P", "t1")
        await graph_store.create_edge(id1, id2, "E", "t1")

        assert await graph_store.delete_edge(id1, id2, "E", "t1") is True
        assert (await graph_store.get_neighbors(id1, "t1")) == []

    @pytest.mark.asyncio
    async def test_shortest_path(self, graph_store):
        # Path: A -> B -> C
        id_a, id_b, id_c = uuid4(), uuid4(), uuid4()
        await graph_store.create_node(id_a, "P", "t1")
        await graph_store.create_node(id_b, "P", "t1")
        await graph_store.create_node(id_c, "P", "t1")

        await graph_store.create_edge(id_a, id_b, "E", "t1")
        await graph_store.create_edge(id_b, id_c, "E", "t1")

        path = await graph_store.shortest_path(id_a, id_c, "t1")
        assert path == [id_a, id_b, id_c]

        # No path
        id_d = uuid4()
        await graph_store.create_node(id_d, "P", "t1")
        assert await graph_store.shortest_path(id_a, id_d, "t1") is None

    @pytest.mark.asyncio
    async def test_get_subgraph(self, graph_store):
        id1, id2 = uuid4(), uuid4()
        await graph_store.create_node(id1, "P", "t1", {"n": 1})
        await graph_store.create_node(id2, "P", "t1", {"n": 2})
        await graph_store.create_edge(id1, id2, "E", "t1")

        subgraph = await graph_store.get_subgraph([id1, id2], "t1")
        assert len(subgraph["nodes"]) == 2
        assert len(subgraph["edges"]) == 1
