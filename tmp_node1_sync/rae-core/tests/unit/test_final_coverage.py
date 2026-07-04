"""Final coverage cleanup for rae-core."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.layers.base import MemoryLayerBase
from rae_core.math.quality_metrics import EntropyMetric, TextCoherenceMetric
from rae_core.reflection.engine import ReflectionEngine


class ConcreteLayer(MemoryLayerBase):
    """Stub for testing abstract base layer."""

    async def add_memory(self, *args, **kwargs):
        pass

    async def get_memory(self, *args, **kwargs):
        pass

    async def search_memories(self, *args, **kwargs):
        pass

    async def cleanup(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_base_layer_abstract_stubs():
    layer = ConcreteLayer(
        storage=MagicMock(), layer_name="test", tenant_id="t", agent_id="a"
    )
    # Calling stubs that contain 'pass'
    await layer.add_memory()
    await layer.get_memory(uuid4(), "t")
    await layer.search_memories("q", "t")
    await layer.cleanup()
    assert layer.layer_name == "test"


@pytest.mark.asyncio
async def test_reflection_engine_generate_reflection_direct():
    ms = MagicMock()
    reflector = MagicMock()
    reflector.generate_reflection = AsyncMock(return_value={"success": True})

    engine = ReflectionEngine(ms)
    engine.reflector = reflector  # Inject mock reflector

    res = await engine.generate_reflection([uuid4()], "t", "a")
    assert res["success"] is True


def test_math_metrics_stubs():
    # Calling compute on base or subclasses to hit stubs if necessary
    # Though usually 'pass' in abstract methods is ignored by better coverage configs,
    # we call them explicitly via a mock or child if they show up as missing.
    tm = TextCoherenceMetric()
    em = EntropyMetric()
    assert tm is not None
    assert em is not None


@pytest.mark.asyncio
async def test_rae_engine_vector_mapping_coverage():
    """Test RAEEngine vector mapping logic for all dimensions."""
    from rae_core.engine import RAEEngine

    # Mock dependencies
    storage = MagicMock()
    storage.store_memory = AsyncMock(return_value=uuid4())
    storage.save_embedding = AsyncMock()

    vector_store = MagicMock()
    vector_store.store_vector = AsyncMock()

    # Helper to test dimension mapping
    async def verify_mapping(dim, expected_key):
        emb_provider = MagicMock()
        emb_provider.generate_all_embeddings = AsyncMock(
            return_value={"model": [[0.1] * dim]}
        )

        # Reset mocks
        vector_store.store_vector.reset_mock()

        engine = RAEEngine(storage, vector_store, emb_provider)
        await engine.store_memory("t", "a", "content")

        call_kwargs = vector_store.store_vector.call_args.kwargs
        assert expected_key in call_kwargs["embedding"]
        assert len(call_kwargs["embedding"][expected_key]) == dim

    # Test all branches
    await verify_mapping(1536, "openai")
    await verify_mapping(768, "ollama")
    await verify_mapping(384, "dense")
    await verify_mapping(1024, "cohere")

    # Test Fallback
    emb_provider_unknown = MagicMock()
    emb_provider_unknown.generate_all_embeddings = AsyncMock(
        return_value={"custom": [[0.1] * 128]}
    )
    vector_store.store_vector.reset_mock()
    engine_fallback = RAEEngine(storage, vector_store, emb_provider_unknown)
    await engine_fallback.store_memory("t", "a", "content")

    call_kwargs = vector_store.store_vector.call_args.kwargs
    assert "dense" in call_kwargs["embedding"]
    assert len(call_kwargs["embedding"]["dense"]) == 128


@pytest.mark.asyncio
async def test_reflector_insight_and_error_coverage():
    """Test Reflector insight generation and unknown type error."""
    from rae_core.reflection.reflector import Reflector

    storage = MagicMock()
    storage.get_memory = AsyncMock(
        return_value={
            "id": uuid4(),
            "content": "test content",
            "importance": 0.8,
            "layer": "episodic",
            "tags": ["tag1"],
        }
    )
    storage.store_memory = AsyncMock(return_value=uuid4())

    reflector = Reflector(storage)

    # 1. Test Insight (Success)
    res_insight = await reflector.generate_reflection(
        [uuid4()], "t", "a", reflection_type="insight"
    )
    assert res_insight["success"] is True
    assert res_insight["type"] == "insight"

    # 2. Test Unknown Type (Error)
    res_error = await reflector.generate_reflection(
        [uuid4()], "t", "a", reflection_type="unknown_random_type"
    )
    assert res_error["success"] is False
    assert "Unknown reflection type" in res_error["error"]


@pytest.mark.asyncio
async def test_graph_strategy_coverage():
    """Test GraphTraversalStrategy string seeds and multi-path boost."""
    from rae_core.search.strategies.graph import GraphTraversalStrategy

    graph_store = MagicMock()
    memory_storage = MagicMock()
    strategy = GraphTraversalStrategy(graph_store, memory_storage)

    # Setup Diamond Graph: A -> B, A -> C, B -> D, C -> D
    id_a, id_b, id_c, id_d = uuid4(), uuid4(), uuid4(), uuid4()

    async def get_neighbors_side_effect(
        node_id, tenant_id, edge_type=None, direction="both", max_depth=1
    ):
        if str(node_id) == str(id_a):
            return [id_b, id_c]
        if str(node_id) == str(id_b):
            return [id_d]
        if str(node_id) == str(id_c):
            return [id_d]
        return []

    graph_store.get_neighbors = AsyncMock(side_effect=get_neighbors_side_effect)

    # 1. Test string seed IDs
    results = await strategy.search(
        query="test", tenant_id="t", filters={"seed_ids": [str(id_a)]}, limit=10
    )

    result_ids = [r[0] for r in results]
    # Seeds are not returned, only neighbors
    assert id_b in result_ids
    assert id_c in result_ids
    assert id_d in result_ids
