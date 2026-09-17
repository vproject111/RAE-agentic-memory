"""Unit tests for RAEEngine search_evidence and strategy registration (Stage 1)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.engine import RAEEngine
from rae_core.models.evidence_package import EvidenceItem, EvidencePackage
from rae_core.search.adaptive_engine import AdaptiveSearchEngine
from rae_core.search.engine import HybridSearchEngine


@pytest.fixture
def mock_dependencies():
    storage = MagicMock()
    vector = MagicMock()
    embedding = MagicMock()
    embedding.providers = None
    graph = MagicMock()
    return storage, vector, embedding, graph


def test_rae_engine_registers_visual_and_graph_lite_strategies(mock_dependencies):
    storage, vector, embedding, graph = mock_dependencies

    engine = RAEEngine(
        memory_storage=storage,
        vector_store=vector,
        embedding_provider=embedding,
        graph_store=graph,
    )

    assert "visual" in engine.search_engine.strategies
    assert "graph_lite" in engine.search_engine.strategies
    assert "graph" in engine.search_engine.strategies
    assert "vector" in engine.search_engine.strategies
    assert "fulltext" in engine.search_engine.strategies


def test_rae_engine_omits_graph_lite_when_no_graph_store():
    storage = MagicMock()
    vector = MagicMock()
    embedding = MagicMock()
    embedding.providers = None

    engine = RAEEngine(
        memory_storage=storage,
        vector_store=vector,
        embedding_provider=embedding,
        graph_store=None,
    )

    assert "visual" in engine.search_engine.strategies
    assert "graph_lite" not in engine.search_engine.strategies
    assert "graph" not in engine.search_engine.strategies


def test_rae_engine_initializes_adaptive_search_engine_when_env_enabled(
    mock_dependencies,
):
    storage, vector, embedding, graph = mock_dependencies

    with patch.dict(os.environ, {"RAE_ADAPTIVE_2PASS_ENABLED": "true"}):
        engine = RAEEngine(
            memory_storage=storage,
            vector_store=vector,
            embedding_provider=embedding,
            graph_store=graph,
        )

        assert isinstance(engine.search_engine, AdaptiveSearchEngine)


def test_rae_engine_initializes_adaptive_search_engine_with_single_pass_by_default(
    mock_dependencies,
):
    storage, vector, embedding, graph = mock_dependencies

    with patch.dict(os.environ, {"RAE_ADAPTIVE_2PASS_ENABLED": "false"}):
        engine = RAEEngine(
            memory_storage=storage,
            vector_store=vector,
            embedding_provider=embedding,
            graph_store=graph,
        )

        assert isinstance(engine.search_engine, AdaptiveSearchEngine)
        assert isinstance(engine.search_engine, HybridSearchEngine)
        assert not engine.search_engine.is_2pass_enabled()


@pytest.mark.asyncio
async def test_rae_engine_force_2pass_triggers_adaptive_search_when_env_disabled():
    mock_search_engine = MagicMock(spec=AdaptiveSearchEngine)
    mock_search_engine.is_2pass_enabled.return_value = False
    expected_package = EvidencePackage(
        query="test query",
        tenant_id="tenant-123",
        items=[],
    )
    mock_search_engine.search_adaptive_evidence = AsyncMock(
        return_value=expected_package
    )

    engine = RAEEngine(
        memory_storage=MagicMock(),
        vector_store=MagicMock(),
        embedding_provider=MagicMock(),
        search_engine=mock_search_engine,
    )

    result = await engine.search_evidence(
        query="test query",
        tenant_id="tenant-123",
        force_2pass=True,
    )
    assert result == expected_package
    mock_search_engine.search_adaptive_evidence.assert_awaited_once()


@pytest.mark.asyncio
async def test_rae_engine_search_evidence_delegates_to_search_engine():
    mock_search_engine = MagicMock(spec=HybridSearchEngine)
    expected_package = EvidencePackage(
        query="test query",
        tenant_id="tenant-123",
        items=[
            EvidenceItem.from_memory_and_score(
                memory_id=uuid4(),
                content="test content",
                score=0.9,
            )
        ],
    )
    mock_search_engine.search_evidence = AsyncMock(return_value=expected_package)

    engine = RAEEngine(
        memory_storage=MagicMock(),
        vector_store=MagicMock(),
        embedding_provider=MagicMock(),
        search_engine=mock_search_engine,
    )

    result = await engine.search_evidence(
        query="test query",
        tenant_id="tenant-123",
        agent_id="agent-1",
        layer="episodic",
        top_k=5,
        auto_route=True,
    )

    assert result == expected_package
    mock_search_engine.search_evidence.assert_awaited_once()
    call_kwargs = mock_search_engine.search_evidence.await_args.kwargs
    assert call_kwargs["query"] == "test query"
    assert call_kwargs["tenant_id"] == "tenant-123"
    assert call_kwargs["agent_id"] == "agent-1"
    assert call_kwargs["limit"] == 5
    assert call_kwargs["auto_route"] is True
    assert call_kwargs["filters"]["layer"] == "episodic"


@pytest.mark.asyncio
async def test_rae_engine_search_evidence_uses_adaptive_when_forced():
    mock_adaptive_engine = MagicMock(spec=AdaptiveSearchEngine)
    mock_adaptive_engine.is_2pass_enabled.return_value = False
    expected_package = EvidencePackage(
        query="adaptive query",
        tenant_id="tenant-123",
        items=[],
    )
    mock_adaptive_engine.search_adaptive_evidence = AsyncMock(
        return_value=expected_package
    )

    engine = RAEEngine(
        memory_storage=MagicMock(),
        vector_store=MagicMock(),
        embedding_provider=MagicMock(),
        search_engine=mock_adaptive_engine,
    )

    result = await engine.search_evidence(
        query="adaptive query",
        tenant_id="tenant-123",
        force_2pass=True,
    )

    assert result == expected_package
    mock_adaptive_engine.search_adaptive_evidence.assert_awaited_once()
    call_kwargs = mock_adaptive_engine.search_adaptive_evidence.await_args.kwargs
    assert call_kwargs["force_2pass"] is True
