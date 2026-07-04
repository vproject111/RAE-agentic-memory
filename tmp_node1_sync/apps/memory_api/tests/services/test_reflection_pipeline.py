from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.models.reflection_models import (
    GenerateReflectionRequest,
    ReflectionScoring,
    ReflectionType,
    ReflectionUnit,
)
from apps.memory_api.services.reflection_pipeline import ReflectionPipeline

# Mock data
TENANT_ID = "test-tenant"
PROJECT_ID = "test-project"


@pytest.fixture
def mock_pool():
    pool = AsyncMock()

    # Configure acquire to return a context manager that yields a connection
    conn_mock = MagicMock()
    conn_mock.fetch = AsyncMock(return_value=[])
    conn_mock.fetchrow = AsyncMock(return_value=None)

    mock_context_manager = MagicMock()

    async def aenter(*args, **kwargs):
        return conn_mock

    mock_context_manager.__aenter__ = AsyncMock(side_effect=aenter)

    async def aexit(*args, **kwargs):
        return None

    mock_context_manager.__aexit__ = AsyncMock(side_effect=aexit)

    pool.acquire.return_value = mock_context_manager
    pool._conn_mock = conn_mock

    return pool


@pytest.fixture
def mock_rae_service(mock_pool):
    service = MagicMock()
    service.postgres_pool = mock_pool
    service.list_memories = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_llm_provider():
    provider = AsyncMock()
    # Default text response
    text_response = MagicMock()
    text_response.text = "Test Insight Content"
    text_response.usage.total_tokens = 100
    text_response.cost_usd = 0.001
    provider.generate.return_value = text_response

    # Default structured response (scoring)
    score_response = MagicMock()
    score_response.novelty = 0.8
    score_response.importance = 0.7
    score_response.utility = 0.9
    score_response.confidence = 0.8
    provider.generate_structured.return_value = score_response

    return provider


@pytest.fixture
def mock_ml_client():
    client = AsyncMock()
    client.get_embedding.return_value = [0.1] * 1536
    return client


@pytest.fixture
def pipeline(mock_rae_service, mock_llm_provider, mock_ml_client):
    # Patch dependencies using parenthesized context managers
    with (
        patch(
            "apps.memory_api.services.reflection_pipeline.get_llm_provider",
            return_value=mock_llm_provider,
        ),
        patch(
            "apps.memory_api.services.reflection_pipeline.MLServiceClient",
            return_value=mock_ml_client,
        ),
    ):
        pipeline = ReflectionPipeline(mock_rae_service)
        # Ensure mocks are attached
        pipeline.llm_provider = mock_llm_provider
        pipeline.ml_client = mock_ml_client
        return pipeline


@pytest.mark.asyncio
async def test_fetch_memories_filters(pipeline, mock_rae_service):
    """Test _fetch_memories calls rae_service.list_memories correctly."""
    mock_rae_service.list_memories.return_value = []

    filters = {"layer": "episodic", "tags": ["important"]}
    since = datetime(2024, 1, 1)

    await pipeline._fetch_memories(TENANT_ID, PROJECT_ID, 10, filters, since)

    # Check arguments passed to list_memories
    mock_rae_service.list_memories.assert_called_once_with(
        tenant_id=TENANT_ID,
        project=PROJECT_ID,
        layer="episodic",
        tags=["important"],
        filters={"since": since},
        limit=10,
    )


@pytest.mark.asyncio
async def test_generate_reflections_no_memories(pipeline, mock_pool):
    """Test pipeline behavior when no memories are found."""
    # Mock fetch to return empty list via the patched _fetch_memories method or pool mock
    # Since we test private method separately, we can mock the method itself to isolate higher level logic
    with patch.object(
        pipeline, "_fetch_memories", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = []

        request = GenerateReflectionRequest(
            tenant_id=TENANT_ID,
            project=PROJECT_ID,
            reflection_type=ReflectionType.INSIGHT,
        )

        reflections, stats = await pipeline.generate_reflections(request)

        assert len(reflections) == 0
        assert stats["memories_processed"] == 0
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_generate_reflections_with_clusters(pipeline):
    """Test full pipeline flow with clusters found."""
    # Mock memories
    memories = [{"id": str(uuid4()), "content": "m1", "embedding": [0.1] * 384}]

    # Mock internal methods to isolate pipeline logic from clustering/LLM details
    with (
        patch.object(pipeline, "_fetch_memories", new_callable=AsyncMock) as mock_fetch,
        patch.object(
            pipeline, "_cluster_memories", new_callable=AsyncMock
        ) as mock_cluster,
        patch.object(
            pipeline, "_generate_cluster_insight", new_callable=AsyncMock
        ) as mock_gen_insight,
    ):
        mock_fetch.return_value = memories
        mock_cluster.return_value = {"cluster_1": memories}

        # Mock generated insight
        mock_insight = ReflectionUnit(
            id=uuid4(),
            content="Insight",
            tenant_id=TENANT_ID,
            project_id=PROJECT_ID,
            type=ReflectionType.INSIGHT,
            reflection_type=ReflectionType.INSIGHT,
            score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_accessed_at=datetime.now(),
        )
        mock_insight.telemetry = MagicMock(generation_cost_usd=0.002)
        mock_gen_insight.return_value = mock_insight

        request = GenerateReflectionRequest(
            tenant_id=TENANT_ID,
            project=PROJECT_ID,
            reflection_type=ReflectionType.INSIGHT,
            min_cluster_size=1,
        )

        reflections, stats = await pipeline.generate_reflections(request)

        assert len(reflections) == 1
        assert reflections[0] == mock_insight
        assert stats["memories_processed"] == 1
        assert stats["clusters_found"] == 1
        assert stats["insights_generated"] == 1
        assert stats["total_cost_usd"] == 0.002


@pytest.mark.asyncio
async def test_generate_cluster_insight(pipeline, mock_pool, mock_llm_provider):
    """Test generation of a single cluster insight."""
    cluster_id = "c1"
    memories = [
        {"id": str(uuid4()), "content": "Memory A", "created_at": datetime.now()},
        {"id": str(uuid4()), "content": "Memory B", "created_at": datetime.now()},
    ]

    # Mock repository creation
    with patch(
        "apps.memory_api.repositories.reflection_repository.create_reflection",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_reflection = MagicMock()
        mock_reflection.id = uuid4()
        mock_reflection.score = 0.85
        mock_create.return_value = mock_reflection

        await pipeline._generate_cluster_insight(
            TENANT_ID, PROJECT_ID, cluster_id, memories
        )

        # Verify LLM was called
        mock_llm_provider.generate.assert_called_once()
        args = mock_llm_provider.generate.call_args
        assert "Memory A" in args.kwargs["prompt"] or "Memory A" in args.args[1]

        # Verify scoring was called
        mock_llm_provider.generate_structured.assert_called_once()

        # Verify DB creation
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["content"] == "Test Insight Content"
        assert call_kwargs["tenant_id"] == TENANT_ID
        assert len(call_kwargs["source_memory_ids"]) == 2


@pytest.mark.asyncio
async def test_generate_meta_insight(pipeline, mock_llm_provider):
    """Test meta-insight generation from multiple insights."""
    insights = [
        MagicMock(id=uuid4(), content="Insight 1"),
        MagicMock(id=uuid4(), content="Insight 2"),
        MagicMock(id=uuid4(), content="Insight 3"),
    ]

    with patch(
        "apps.memory_api.repositories.reflection_repository.create_reflection",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_reflection = MagicMock()
        mock_reflection.id = uuid4()
        mock_reflection.score = 0.9
        mock_create.return_value = mock_reflection

        await pipeline._generate_meta_insight(TENANT_ID, PROJECT_ID, insights)

        # Verify LLM prompt contains insights
        mock_llm_provider.generate.assert_called_once()
        args = mock_llm_provider.generate.call_args
        prompt = args.kwargs.get("prompt") or args.args[1]
        assert "Insight 1" in prompt
        assert "Insight 2" in prompt

        # Verify create call
        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["reflection_type"] == ReflectionType.META


@pytest.mark.asyncio
async def test_cluster_memories_fallback_kmeans(pipeline):
    """Test clustering fallback to KMeans when HDBSCAN fails or is missing."""
    memories = [
        {"id": "1", "embedding": [0.1, 0.2]},
        {"id": "2", "embedding": [0.15, 0.25]},
        {"id": "3", "embedding": [0.9, 0.9]},  # Distinct
        {"id": "4", "embedding": [0.95, 0.95]},
    ]

    # Mock sklearn KMeans using parenthesized context manager
    with (
        patch(
            "apps.memory_api.services.reflection_pipeline.HDBSCAN",
            side_effect=Exception("HDBSCAN missing"),
        ),
        patch("apps.memory_api.services.reflection_pipeline.KMeans") as MockKMeans,
        patch(
            "apps.memory_api.services.reflection_pipeline.StandardScaler"
        ) as MockScaler,
        patch("apps.memory_api.services.reflection_pipeline.SKLEARN_AVAILABLE", True),
    ):
        # Configure KMeans mock
        kmeans_instance = MockKMeans.return_value
        kmeans_instance.fit_predict.return_value = [0, 0, 1, 1]  # 2 clusters

        # Mock Scaler
        scaler_instance = MockScaler.return_value
        scaler_instance.fit_transform.return_value = [
            [0.1, 0.2],
            [0.15, 0.25],
            [0.9, 0.9],
            [0.95, 0.95],
        ]

        clusters = await pipeline._cluster_memories(memories, min_cluster_size=2)

        assert len(clusters) == 2
        assert "cluster_0" in clusters
        assert "cluster_1" in clusters
        assert len(clusters["cluster_0"]) == 2


@pytest.mark.asyncio
async def test_score_reflection_fallback(pipeline, mock_llm_provider):
    """Test scoring fallback to defaults on error."""
    mock_llm_provider.generate_structured.side_effect = Exception("LLM Error")

    score = await pipeline._score_reflection("Some content")

    assert score.novelty_score == 0.5
    assert score.confidence_score == 0.5


def test_calculate_priority(pipeline):
    """Test priority calculation logic."""
    scoring = ReflectionScoring(
        novelty_score=0.8, importance_score=0.8, utility_score=0.8, confidence_score=0.8
    )  # Composite (avg) = 0.8. Score priority = 0.8 * 5 = 4.

    # Cluster size 20 -> bonus 1.0. Total = 5.
    p1 = pipeline._calculate_priority(20, scoring)
    assert p1 == 5

    # Small cluster -> bonus 0.2. Total = 4.2 -> 4
    p2 = pipeline._calculate_priority(2, scoring)
    assert p2 == 4


@pytest.mark.asyncio
async def test_fetch_memories_full_filters(pipeline, mock_rae_service):
    """Test _fetch_memories with all filter options."""
    mock_rae_service.list_memories.return_value = []

    filters = {"layer": "episodic", "tags": ["tag1", "tag2"]}
    since = datetime(2024, 1, 1)

    await pipeline._fetch_memories(TENANT_ID, PROJECT_ID, 10, filters, since)

    # Verify list_memories call
    mock_rae_service.list_memories.assert_called_once_with(
        tenant_id=TENANT_ID,
        project=PROJECT_ID,
        layer="episodic",
        tags=["tag1", "tag2"],
        filters={"since": since},
        limit=10,
    )


@pytest.mark.asyncio
async def test_clustering_noise_handling(pipeline):
    """Test clustering handles noise (-1 labels) correctly."""
    memories = [
        {"id": "1", "embedding": [0.1]},
        {"id": "2", "embedding": [0.9]},  # Noise
    ]

    with (
        patch("apps.memory_api.services.reflection_pipeline.HDBSCAN") as MockHDBSCAN,
        patch("apps.memory_api.services.reflection_pipeline.StandardScaler"),
        patch("apps.memory_api.services.reflection_pipeline.SKLEARN_AVAILABLE", True),
    ):
        hdbscan_instance = MockHDBSCAN.return_value
        # Label 0 for memory 1, Label -1 (noise) for memory 2
        hdbscan_instance.fit_predict.return_value = [0, -1]

        clusters = await pipeline._cluster_memories(memories, min_cluster_size=1)

        # Only cluster 0 should exist, noise ignored
        assert len(clusters) == 1
        assert "cluster_0" in clusters
        assert len(clusters["cluster_0"]) == 1
        assert clusters["cluster_0"][0]["id"] == "1"


@pytest.mark.asyncio
async def test_embedding_generation_failure(pipeline, mock_ml_client):
    """Test fallback when embedding generation fails."""
    mock_ml_client.get_embedding.side_effect = Exception("ML Error")

    embedding = await pipeline._generate_embedding("text")

    assert embedding == [0.0] * 1536


@pytest.mark.asyncio
async def test_generate_reflections_exception_handling(pipeline):
    """Test exception handling in main generation loop."""
    memories = [{"id": "1", "embedding": [0.1]}]

    with (
        patch.object(pipeline, "_fetch_memories", new_callable=AsyncMock) as mock_fetch,
        patch.object(
            pipeline, "_cluster_memories", new_callable=AsyncMock
        ) as mock_cluster,
        patch.object(
            pipeline,
            "_generate_cluster_insight",
            side_effect=Exception("Insight Error"),
        ),
        patch.object(
            pipeline, "_generate_meta_insight", side_effect=Exception("Meta Error")
        ),
    ):
        mock_fetch.return_value = memories
        # Two clusters to trigger potential meta-insight logic if it weren't for errors
        mock_cluster.return_value = {"c1": memories, "c2": memories, "c3": memories}

        reflections, stats = await pipeline.generate_reflections(
            GenerateReflectionRequest(
                tenant_id=TENANT_ID,
                project=PROJECT_ID,
                reflection_type=ReflectionType.INSIGHT,
            )
        )

        # Should return empty list but not crash
        assert len(reflections) == 0
        assert stats["insights_generated"] == 0
        # Should try to generate insights for all 3 clusters
        assert pipeline._generate_cluster_insight.call_count == 3
