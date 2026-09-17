"""Unit tests for VisualSearchStrategy and MultimodalArtifact (Iteration 8)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from rae_core.models.envelope import ContextEnvelope
from rae_core.models.multimodal import MultimodalArtifact
from rae_core.search.strategies.visual import VisualSearchStrategy


@pytest.mark.asyncio
async def test_visual_search_ocr_matching():
    strategy = VisualSearchStrategy()

    mem_id1 = uuid4()
    art1 = MultimodalArtifact(
        artifact_id="art-1",
        artifact_type="screenshot",
        image_uri="/tmp/screenshots/error_sidebar.png",
        ocr_extracted_text="Error: Navigation sidebar menu failed to load on mobile viewport",
        envelope=ContextEnvelope(source_type="test", project="dreamsoft"),
    )
    strategy.register_artifact(mem_id1, art1)

    mem_id2 = uuid4()
    art2 = MultimodalArtifact(
        artifact_id="art-2",
        artifact_type="architecture_diagram",
        image_uri="/tmp/diagrams/fusion.png",
        ocr_extracted_text="Hybrid search fusion logic gateway pipeline",
        envelope=ContextEnvelope(source_type="architecture", project="rae_suite"),
    )
    strategy.register_artifact(mem_id2, art2)

    # Search for sidebar menu error
    results = await strategy.search(
        query="sidebar menu error",
        tenant_id="tenant-1",
    )

    assert len(results) > 0
    assert results[0][0] == mem_id1
    assert results[0][1] >= 0.5


@pytest.mark.asyncio
async def test_visual_search_embedding_similarity():
    strategy = VisualSearchStrategy()

    mem_id = uuid4()
    art = MultimodalArtifact(
        artifact_id="art-emb",
        artifact_type="screenshot",
        image_uri="/tmp/screen.png",
        visual_embedding=[0.6, 0.8, 0.0],
    )
    strategy.register_artifact(mem_id, art)

    # Identical query visual vector -> cosine similarity 1.0
    results = await strategy.search(
        query="irrelevant text",
        tenant_id="tenant-1",
        visual_embedding=[0.6, 0.8, 0.0],
    )

    assert len(results) == 1
    assert results[0][0] == mem_id
    assert results[0][1] == pytest.approx(1.0, rel=1e-3)


@pytest.mark.asyncio
async def test_visual_search_project_filtering():
    strategy = VisualSearchStrategy()

    mem_id = uuid4()
    art = MultimodalArtifact(
        artifact_id="art-proj",
        artifact_type="screenshot",
        image_uri="/tmp/screen.png",
        ocr_extracted_text="broken button in shopping cart",
        envelope=ContextEnvelope(source_type="test", project="dreamsoft"),
    )
    strategy.register_artifact(mem_id, art)

    # Filter for non-matching project -> 0 results
    results = await strategy.search(
        query="broken button",
        tenant_id="tenant-1",
        project="screenwatcher",
    )
    assert len(results) == 0

    # Filter for matching project -> 1 result
    results_match = await strategy.search(
        query="broken button",
        tenant_id="tenant-1",
        project="dreamsoft",
    )
    assert len(results_match) == 1
