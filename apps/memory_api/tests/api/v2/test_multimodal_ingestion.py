"""Unit and integration tests for Multimodal Ingestion and Visual Search (Phase 5)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from apps.memory_api.services.rae_core_service import RAECoreService
from rae_core.engine import RAEEngine
from rae_core.models.multimodal import MultimodalArtifact
from rae_core.search.adaptive_engine import AdaptiveSearchEngine
from rae_core.search.strategies.visual import VisualSearchStrategy


@pytest.mark.asyncio
async def test_multimodal_memory_ingestion_registers_in_visual_strategy():
    visual_strat = VisualSearchStrategy()
    adaptive_engine = AdaptiveSearchEngine(
        strategies={"visual": visual_strat},
    )

    mock_storage = AsyncMock()
    stored_mem_id = uuid4()
    mock_storage.store_memory.return_value = stored_mem_id

    mock_engine = MagicMock(spec=RAEEngine)
    mock_engine.search_engine = adaptive_engine
    mock_engine.store_memory = AsyncMock(return_value=stored_mem_id)

    rae_service = RAECoreService(
        postgres_pool=None, qdrant_client=None, redis_client=None
    )
    rae_service.engine = mock_engine

    # Ingest sensory memory with screenshot and OCR text
    meta = {
        "screenshot_url": "https://artifacts.dreamsoft.pro/screenshots/auth_err.png",
        "ocr_text": "FATAL: Payment Gateway Timeout after 30000ms at checkout",
        "task_id": "task-ui-debug-99",
    }

    mem_id = await rae_service.store_memory(
        tenant_id="tenant-alpha",
        project="dreamsoft",
        content="Screenshot of error during checkout",
        source="playwright_ui_agent",
        layer="sensory",
        metadata=meta,
    )

    assert mem_id == str(stored_mem_id)
    # Check that VisualSearchStrategy received the registered artifact
    assert UUID(mem_id) in visual_strat._artifacts
    artifact: MultimodalArtifact = visual_strat._artifacts[UUID(mem_id)]
    assert artifact.artifact_type == "screenshot"
    assert "Payment Gateway Timeout" in (artifact.ocr_extracted_text or "")
    assert (
        artifact.image_uri == "https://artifacts.dreamsoft.pro/screenshots/auth_err.png"
    )

    # Search using visual strategy
    results = await visual_strat.search(
        query="Payment Gateway Timeout",
        tenant_id="tenant-alpha",
        limit=5,
    )

    assert len(results) == 1
    assert results[0][0] == UUID(mem_id)
    assert results[0][1] > 0.0
