from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.engine import RAEEngine
from rae_core.math.structure import ScoringWeights


@pytest.fixture
def mock_infra():
    infra = {
        "storage": MagicMock(),
        "vector": MagicMock(),
        "embedding": MagicMock(),
        "llm": MagicMock(),
        "cache": MagicMock(),
        "search": MagicMock(),
        "math_ctrl": MagicMock(),
        "resonance": MagicMock(),
    }
    # Set up AsyncMocks
    infra["storage"].store_memory = AsyncMock()
    infra["storage"].get_memory = AsyncMock()
    infra["storage"].get_memories_batch = AsyncMock()
    infra["storage"].get_neighbors_batch = AsyncMock()
    infra["storage"].count_memories = AsyncMock()
    infra["vector"].store_vector = AsyncMock()
    infra["embedding"].embed_text = AsyncMock()
    infra["embedding"].generate_all_embeddings = AsyncMock()
    infra["llm"].generate_text = AsyncMock()
    infra["cache"].get = AsyncMock()
    infra["cache"].set = AsyncMock()
    infra["search"].search = AsyncMock()

    return infra


@pytest.mark.asyncio
async def test_engine_init_variants(mock_infra):
    # Test with search_engine and resonance_engine provided
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        search_engine=mock_infra["search"],
        resonance_engine=mock_infra["resonance"],
    )
    assert engine.search_engine == mock_infra["search"]
    assert engine.resonance_engine == mock_infra["resonance"]

    # Test with EmbeddingManager
    class MockEmbeddingManager:
        def __init__(self):
            self.providers = {"p1": MagicMock()}

    with patch("rae_core.embedding.manager.EmbeddingManager", MockEmbeddingManager):
        mock_emb_manager = MockEmbeddingManager()
        engine2 = RAEEngine(
            memory_storage=mock_infra["storage"],
            vector_store=mock_infra["vector"],
            embedding_provider=mock_emb_manager,
        )
        assert any("vector_p1" in k for k in engine2.search_engine.strategies.keys())


@pytest.mark.asyncio
async def test_init_vector_strategy_embedding_manager(mock_infra):
    class MockEmbeddingManager:
        def __init__(self):
            self.providers = {"p1": MagicMock()}

    with patch("rae_core.embedding.manager.EmbeddingManager", MockEmbeddingManager):
        with patch(
            "rae_core.search.strategies.multi_vector.MultiVectorSearchStrategy",
            MagicMock(),
        ):
            mock_emb_manager = MockEmbeddingManager()
            engine = RAEEngine(
                memory_storage=mock_infra["storage"],
                vector_store=mock_infra["vector"],
                embedding_provider=mock_emb_manager,
            )
            strategy = engine._init_vector_strategy()
            assert strategy is not None


@pytest.mark.asyncio
async def test_search_memories_complex_paths(mock_infra):
    mock_infra["math_ctrl"].get_retrieval_weights.return_value = {
        "vector": 0.5,
        "fulltext": 0.5,
        "_params": {"resonance_factor": 0.6, "rerank_gate": 0.3, "limit": 50},
        "_arm_id": "arm_test",
    }
    mock_infra["math_ctrl"].get_engine_param.return_value = 50
    mock_infra["math_ctrl"].get_resonance_threshold.return_value = 0.1

    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        math_controller=mock_infra["math_ctrl"],
        resonance_engine=mock_infra["resonance"],
        search_engine=mock_infra["search"],
    )

    mem_id = uuid4()
    mock_infra["search"].search.return_value = [
        (mem_id, 0.9, 0.5, {"sic_boost": True, "tier": 1})
    ]

    memory_obj = MagicMock()
    # Ensure id is present in the dictionary returned by to_dict
    memory_obj.to_dict.return_value = {"id": mem_id, "content": "test"}
    mock_infra["storage"].get_memory.return_value = memory_obj

    # Mock resonance to trigger induction
    mock_infra["storage"].get_neighbors_batch.return_value = {
        str(mem_id): [(str(uuid4()), 0.8)]
    }
    # Resonance engine expects edges as a list of (source, target, weight)
    edges_list = [(str(mem_id), str(uuid4()), 0.8)]
    mock_infra["resonance"].compute_resonance.return_value = (
        [
            {
                "id": mem_id,
                "content": "test",
                "audit_trail": {"sic_boost": True, "tier": 1},
            }
        ],
        {str(uuid4()): 0.9},
    )
    mock_infra["math_ctrl"].score_memory.return_value = 0.9

    results = await engine.search_memories("query", "t1", enable_reranking=True)
    assert len(results) > 0
    assert engine.resonance_engine.resonance_factor == 0.6


@pytest.mark.asyncio
async def test_search_memories_szubar_loop(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        math_controller=mock_infra["math_ctrl"],
        search_engine=mock_infra["search"],
    )

    mem_id = uuid4()
    # Low score to trigger Szubar
    mock_infra["search"].search.return_value = [(mem_id, 0.5, 0.5, {"tier": 2})]
    mock_infra["storage"].get_memory.return_value = {
        "id": mem_id,
        "content": "low score",
        "importance": 0.5,
    }
    mock_infra["math_ctrl"].score_memory.return_value = 0.5

    recruited_id = uuid4()
    # Search engine expects edges for resonance, but engine.py also uses it for Szubar
    # Szubar expects edges as {seed_id: [(neighbor_id, weight), ...]}
    mock_infra["storage"].get_neighbors_batch.return_value = {
        mem_id: [(recruited_id, 0.9)]
    }
    mock_infra["storage"].get_memories_batch.return_value = [
        {"id": recruited_id, "content": "recruited", "metadata": {}}
    ]

    # Mock search_engine.fusion_strategy.gateway
    gateway = MagicMock()
    gateway._apply_mathematical_logic.return_value = (2.0, {"logic": "boost"})
    gateway.sigmoid.return_value = 0.85
    gateway.reranker = None
    engine.search_engine.fusion_strategy = MagicMock()
    engine.search_engine.fusion_strategy.gateway = gateway

    # We need to mock resonance_engine to NOT fail or return something useful
    engine.resonance_engine = MagicMock()
    engine.resonance_engine.compute_resonance.return_value = (
        [{"id": mem_id, "content": "low score", "audit_trail": {"tier": 2}}],
        {},
    )

    results = await engine.search_memories("query", "t1")
    assert any(m.get("audit_trail", {}).get("szubar_recruited") for m in results)


@pytest.mark.asyncio
async def test_store_memory_duplicate_and_operational(mock_infra):
    mock_infra["cache"].get.return_value = "hash1"
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        cache_provider=mock_infra["cache"],
    )

    # Mock pipeline
    mock_pipeline = MagicMock()
    mock_chunk = MagicMock()
    mock_chunk.content = "content"
    mock_chunk.metadata = {"content_hash": "hash1"}
    mock_pipeline.process = AsyncMock(
        return_value=([mock_chunk], "sig", [], "POLICY_STANDARD")
    )

    with patch(
        "rae_core.ingestion.pipeline.UniversalIngestPipeline",
        return_value=mock_pipeline,
    ):
        res = await engine.store_memory(content="content", tenant_id="t1")
        assert res is None  # Duplicate skipped

        # Test operational/fallback
        mock_pipeline.process.return_value = (
            [mock_chunk],
            "sig",
            [MagicMock()],
            "POLICY_FALLBACK",
        )
        mock_chunk.metadata = {"content_hash": "hash2"}
        mock_infra["cache"].get.return_value = None

        res = await engine.store_memory(content="content", tenant_id="t1")
        assert res is not None
        # Vector store should NOT be called for operational
        assert not mock_infra["vector"].store_vector.called


@pytest.mark.asyncio
async def test_generate_text_no_provider(mock_infra):
    engine = RAEEngine(
        mock_infra["storage"], mock_infra["vector"], mock_infra["embedding"]
    )
    engine.llm_provider = None
    with pytest.raises(RuntimeError, match="LLM provider not configured"):
        await engine.generate_text("hi")


@pytest.mark.asyncio
async def test_get_statistics(mock_infra):
    mock_infra["storage"].count_memories.return_value = 10
    engine = RAEEngine(
        mock_infra["storage"], mock_infra["vector"], mock_infra["embedding"]
    )
    stats = await engine.get_statistics("t1")
    assert stats["total_count"] == 10
    assert stats["layer_counts"]["working"] == 10


@pytest.mark.asyncio
async def test_get_statistics_error(mock_infra):
    mock_infra["storage"].count_memories.side_effect = Exception("error")
    engine = RAEEngine(
        mock_infra["storage"], mock_infra["vector"], mock_infra["embedding"]
    )
    stats = await engine.get_statistics("t1")
    assert stats["total_count"] == 0


@pytest.mark.asyncio
async def test_reflection_placeholders(mock_infra):
    engine = RAEEngine(
        mock_infra["storage"], mock_infra["vector"], mock_infra["embedding"]
    )
    res = await engine.run_reflection_cycle()
    assert res["status"] == "completed"
    res2 = await engine.generate_reflections("t1", "p1")
    assert res2 == []


@pytest.mark.asyncio
async def test_search_memories_custom_weights_object(mock_infra):
    engine = RAEEngine(
        mock_infra["storage"],
        mock_infra["vector"],
        mock_infra["embedding"],
        search_engine=mock_infra["search"],
        math_controller=mock_infra["math_ctrl"],
    )
    weights = ScoringWeights(alpha=1.0)
    mock_infra["search"].search.return_value = [(uuid4(), 0.9, 0.5, {"tier": 1})]
    mock_infra["storage"].get_memory.return_value = {"id": uuid4(), "content": "test"}
    # Mock retrieval weights to avoid real math controller calls if any
    mock_infra["math_ctrl"].get_retrieval_weights.return_value = {
        "vector": 1.0,
        "_params": {},
    }
    mock_infra["math_ctrl"].score_memory.return_value = 0.9

    await engine.search_memories("q", "t1", custom_weights=weights)
    mock_infra["math_ctrl"].score_memory.assert_called()


@pytest.mark.asyncio
async def test_embed_and_store_vector_all_embeddings(mock_infra):
    mock_infra["embedding"].generate_all_embeddings.return_value = {"p1": [[0.1] * 128]}
    engine = RAEEngine(
        mock_infra["storage"],
        mock_infra["vector"],
        mock_infra["embedding"],
        math_controller=mock_infra["math_ctrl"],
    )
    await engine._embed_and_store_vector(uuid4(), "content", "t1")
    mock_infra["vector"].store_vector.assert_called()


@pytest.mark.asyncio
async def test_search_memories_win_feature_logging(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        math_controller=mock_infra["math_ctrl"],
        search_engine=mock_infra["search"],
    )
    mem_id = uuid4()
    mock_infra["search"].search.return_value = [
        (mem_id, 0.9, 0.5, {"hard_lock": True, "tier": 1})
    ]
    mock_infra["storage"].get_memory.return_value = {"id": mem_id, "content": "test"}
    mock_infra["math_ctrl"].score_memory.return_value = 0.9
    mock_infra["math_ctrl"].get_retrieval_weights.return_value = {
        "vector": 1.0,
        "_params": {},
    }

    await engine.search_memories("q", "t1")
    # Verify it hits different win features
    for feature in ["anchor_hit", "cat_boost", "quant_boost"]:
        mock_infra["search"].search.return_value = [
            (mem_id, 0.9, 0.5, {feature: True, "tier": 1})
        ]
        await engine.search_memories("q", "t1")
