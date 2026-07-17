from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.engine import RAEEngine


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
async def test_init_vector_strategy_simple(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
    )
    # Line 102-104 coverage
    strategy = engine._init_vector_strategy()
    assert strategy is not None


@pytest.mark.asyncio
async def test_search_memories_filters_coverage(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        search_engine=mock_infra["search"],
        math_controller=mock_infra["math_ctrl"],
    )
    mock_infra["math_ctrl"].get_retrieval_weights.return_value = {
        "vector": 1.0,
        "_params": {},
    }
    mock_infra["search"].search.return_value = []
    mock_infra["storage"].get_neighbors_batch.return_value = {}

    # Line 127, 129, 131 coverage
    await engine.search_memories("q", "t1", agent_id="a1", project="p1", layer="l1")

    call_args = mock_infra["search"].search.call_args[1]
    filters = call_args["filters"]
    assert filters["agent_id"] == "a1"
    assert filters["project"] == "p1"
    assert filters["layer"] == "l1"


@pytest.mark.asyncio
async def test_search_memories_memory_type_fallback(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        search_engine=mock_infra["search"],
        math_controller=mock_infra["math_ctrl"],
    )
    mock_infra["math_ctrl"].get_retrieval_weights.return_value = {
        "vector": 1.0,
        "_params": {},
    }
    mem_id = uuid4()
    mock_infra["search"].search.return_value = [(mem_id, 0.9, 0.5, {"tier": 1})]

    # Line 244 coverage: memory is not to_dict and not dict
    class CustomMemory:
        def __init__(self, data):
            self.data = data

        def __iter__(self):
            return iter(self.data.items())

    mock_infra["storage"].get_memory.return_value = CustomMemory(
        {"id": mem_id, "content": "test"}
    )
    mock_infra["math_ctrl"].score_memory.return_value = 0.9

    results = await engine.search_memories("q", "t1")
    assert results[0]["content"] == "test"


@pytest.mark.asyncio
async def test_search_memories_resonance_induction_types_and_error(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        search_engine=mock_infra["search"],
        math_controller=mock_infra["math_ctrl"],
        resonance_engine=mock_infra["resonance"],
    )
    mock_infra["math_ctrl"].get_retrieval_weights.return_value = {
        "vector": 1.0,
        "_params": {},
    }
    mem_id = uuid4()
    mock_infra["search"].search.return_value = [(mem_id, 0.9, 0.5, {"tier": 1})]
    mock_infra["math_ctrl"].score_memory.return_value = 0.9

    induced_id1 = str(uuid4())
    induced_id2 = str(uuid4())
    induced_id3 = str(uuid4())

    mock_infra["storage"].get_neighbors_batch.return_value = {
        str(mem_id): [(induced_id1, 0.8), (induced_id2, 0.8), (induced_id3, 0.8)]
    }

    # Mock resonance to induce
    mock_infra["resonance"].compute_resonance.return_value = (
        [
            {
                "id": mem_id,
                "content": "main",
                "math_score": 0.9,
                "audit_trail": {"tier": 1},
            }
        ],
        {induced_id1: 0.9, induced_id2: 0.9, induced_id3: 0.9},
    )
    mock_infra["math_ctrl"].get_resonance_threshold.return_value = 0.1

    # induced_id1: normal dict
    # induced_id2: not to_dict, not dict (Line 304-307)
    # induced_id3: raises Exception (Line 317-318)

    class CustomMemory:
        def __init__(self, data):
            self.data = data

        def __iter__(self):
            return iter(self.data.items())

    async def get_mem_side_effect(mid, tid):
        if str(mid) == str(mem_id):
            return {"id": mid, "content": "main"}
        if str(mid) == induced_id1:
            return {"id": mid, "content": "ind1"}
        if str(mid) == induced_id2:
            return CustomMemory({"id": mid, "content": "ind2"})
        if str(mid) == induced_id3:
            raise Exception("Induction error")
        return None

    mock_infra["storage"].get_memory.side_effect = get_mem_side_effect

    results = await engine.search_memories("q", "t1")
    # Should have main + ind1 + ind2
    contents = [r.get("content") for r in results]
    assert "main" in contents
    assert "ind1" in contents
    assert "ind2" in contents


@pytest.mark.asyncio
async def test_search_memories_szubar_reranker(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
        math_controller=mock_infra["math_ctrl"],
        search_engine=mock_infra["search"],
    )

    mem_id = uuid4()
    mock_infra["search"].search.return_value = [(mem_id, 0.5, 0.5, {"tier": 2})]
    mock_infra["storage"].get_memory.return_value = {"id": mem_id, "content": "low"}
    mock_infra["math_ctrl"].score_memory.return_value = 0.5
    mock_infra["math_ctrl"].get_retrieval_weights.return_value = {
        "vector": 1.0,
        "_params": {},
    }

    recruited_id = uuid4()
    mock_infra["storage"].get_neighbors_batch.return_value = {
        mem_id: [(recruited_id, 0.9)]
    }
    mock_infra["storage"].get_memories_batch.return_value = [
        {"id": recruited_id, "content": "recruited", "metadata": {}}
    ]

    gateway = MagicMock()
    gateway._apply_mathematical_logic.return_value = (2.0, {"logic": "boost"})
    gateway.sigmoid.return_value = 0.85

    # Line 369-372: Szubar with reranker
    mock_reranker = MagicMock()
    mock_reranker.predict.return_value = [0.5]
    gateway.reranker = mock_reranker

    engine.search_engine.fusion_strategy = MagicMock()
    engine.search_engine.fusion_strategy.gateway = gateway

    # Mock resonance to avoid errors
    engine.resonance_engine = MagicMock()
    engine.resonance_engine.compute_resonance.return_value = (
        [{"id": mem_id, "content": "low", "audit_trail": {"tier": 2}}],
        {},
    )

    await engine.search_memories("q", "t1", enable_reranking=True)
    assert mock_reranker.predict.called


@pytest.mark.asyncio
async def test_store_memory_no_chunks(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
    )

    mock_pipeline = MagicMock()
    mock_pipeline.process = AsyncMock(return_value=([], None, [], "POLICY_STANDARD"))

    with patch(
        "rae_core.ingestion.pipeline.UniversalIngestPipeline",
        return_value=mock_pipeline,
    ):
        # Line 419 coverage
        res = await engine.store_memory(content="empty", tenant_id="t1")
        assert res is None


@pytest.mark.asyncio
async def test_embed_and_store_vector_content_in_kwargs(mock_infra):
    engine = RAEEngine(
        memory_storage=mock_infra["storage"],
        vector_store=mock_infra["vector"],
        embedding_provider=mock_infra["embedding"],
    )
    mock_infra["embedding"].embed_text.return_value = [0.1] * 128
    # Mock generate_all_embeddings to return a dict for Line 490 coverage
    mock_infra["embedding"].generate_all_embeddings.return_value = {
        "dense": [[0.1] * 128]
    }

    # Line 498 coverage
    await engine._embed_and_store_vector(
        uuid4(), "content", "t1", metadata_extra="extra"
    )

    call_args = mock_infra["vector"].store_vector.call_args[1]
    assert "metadata_extra" in call_args["metadata"]
