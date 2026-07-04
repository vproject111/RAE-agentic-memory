"""
Simplified Reflection Engine Tests

Tests the actual reflection pipeline API with proper mocks.
"""

from datetime import datetime
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import numpy as np
import pytest

# Skip tests if sklearn is not installed (ML dependency)
sklearn = pytest.importorskip(
    "sklearn",
    reason="Requires scikit-learn – heavy ML dependency",
)

from apps.memory_api.models.reflection_models import (  # noqa: E402
    GenerateReflectionRequest,
    ReflectionType,
)
from apps.memory_api.services.reflection_pipeline import (  # noqa: E402
    ReflectionPipeline,
)


@pytest.fixture
def mock_pool():
    """Mock database connection pool"""
    pool = AsyncMock()
    return pool


@pytest.fixture
def sample_memories():
    """Sample memories for testing"""
    return [
        {
            "id": uuid4(),
            "content": "Machine learning is a subset of artificial intelligence",
            "importance": 0.8,
            "embedding": np.random.rand(384).tolist(),
            "created_at": datetime.now(),
        },
        {
            "id": uuid4(),
            "content": "Deep learning uses neural networks with multiple layers",
            "importance": 0.85,
            "embedding": np.random.rand(384).tolist(),
            "created_at": datetime.now(),
        },
    ]


@pytest.fixture
def mock_rae_service():
    """Mock RAECoreService"""
    service = AsyncMock()
    service.postgres_pool = AsyncMock()
    service.list_memories = AsyncMock(return_value=[])
    return service


@pytest.mark.asyncio
async def test_reflection_pipeline_initialization(mock_rae_service):
    """Test that ReflectionPipeline initializes correctly"""
    pipeline = ReflectionPipeline(mock_rae_service)

    assert pipeline.rae_service == mock_rae_service
    assert pipeline.llm_provider is not None
    assert pipeline.ml_client is not None


@pytest.mark.asyncio
async def test_generate_reflections_basic(mock_rae_service, sample_memories):
    """Test basic reflection generation"""
    # Setup mocks
    mock_rae_service.list_memories.return_value = sample_memories

    pipeline = ReflectionPipeline(mock_rae_service)

    # Mock LLM provider
    cast(Any, pipeline.llm_provider).generate = AsyncMock(return_value="Test insight")
    cast(Any, pipeline.llm_provider).generate_structured = AsyncMock(
        return_value={
            "novelty": 0.8,
            "importance": 0.9,
            "utility": 0.85,
            "confidence": 0.9,
        }
    )

    # Mock ML client
    cast(Any, pipeline.ml_client).generate_embeddings = AsyncMock(
        return_value={"embeddings": [np.random.rand(384).tolist()]}
    )

    request = GenerateReflectionRequest(
        tenant_id="test-tenant",
        project="test-project",
        reflection_type=ReflectionType.INSIGHT,
        max_memories=10,
    )

    reflections, stats = await pipeline.generate_reflections(request)

    assert isinstance(reflections, list)
    assert isinstance(stats, dict)
    assert "memories_processed" in stats


@pytest.mark.asyncio
async def test_generate_reflections_returns_stats(mock_pool):
    """Test that generate_reflections returns proper statistics"""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    mock_pool.acquire = AsyncMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()
        )
    )

    pipeline = ReflectionPipeline(mock_pool)

    request = GenerateReflectionRequest(
        tenant_id="test-tenant",
        project="test-project",
        reflection_type=ReflectionType.INSIGHT,
    )

    reflections, stats = await pipeline.generate_reflections(request)

    assert "memories_processed" in stats
    assert "clusters_found" in stats
    assert "insights_generated" in stats
    assert stats["memories_processed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
