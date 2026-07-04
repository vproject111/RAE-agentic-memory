from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from apps.memory_api.services.context_builder import ContextBuilder, ContextConfig
from apps.memory_api.services.rae_core_service import RAECoreService


@pytest.fixture
def mock_rae_service():
    service = AsyncMock(spec=RAECoreService)
    service.list_memories.return_value = []
    return service


@pytest.mark.unit
async def test_context_builder_uses_v3_when_enabled(mock_rae_service):
    # Setup
    # repo = MagicMock() # no longer needed, replaced by rae_service
    reflection_engine = MagicMock()

    # Mock repository return values (now on mock_rae_service)
    # Using side_effect to return items for the first call (episodic) and empty for others (semantic, etc)
    mock_rae_service.list_memories.side_effect = [
        [
            {
                "id": "1",
                "content": "test",
                "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "layer": "episodic",
                "importance": 0.5,
            }
        ],
        [],  # Second call (e.g. semantic) returns empty
    ]
    # No direct mocking for get_semantic_memories, assuming list_memories with filters covers it

    reflection_engine.query_reflections = AsyncMock(return_value=[])

    # Pass mock_rae_service instead of repo
    builder = ContextBuilder(
        mock_rae_service,
        reflection_engine,
        config=ContextConfig(enable_scoring_v3=True),
    )

    # Act
    ctx = await builder.build_context(
        tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        project_id="p1",
        query="test query",
    )

    # Assert
    assert len(ctx.ltm_items) == 1


@pytest.mark.unit
async def test_context_builder_v3_integration_mock(mock_rae_service):
    """Verify V3 is actually called using patch"""
    from unittest.mock import patch

    # repo = MagicMock() # no longer needed
    reflection_engine = MagicMock()

    # Mock return values for rae_service.list_memories
    mock_rae_service.list_memories.side_effect = [
        [
            {
                "id": "1",
                "content": "test",
                "created_at": datetime.now(timezone.utc),
                "layer": "episodic",
            }
        ],
        [],
    ]
    reflection_engine.query_reflections = AsyncMock(return_value=[])

    # Pass mock_rae_service instead of repo
    builder = ContextBuilder(
        mock_rae_service,
        reflection_engine,
        config=ContextConfig(enable_scoring_v3=True),
    )

    with patch(
        "apps.memory_api.services.context_builder.compute_batch_scores_v3"
    ) as mock_v3:
        # Mock return value to match structure expected by rank_memories_by_score
        mock_res = MagicMock()
        mock_res.final_score = 0.9
        mock_v3.return_value = [mock_res]

        await builder.build_context(
            UUID("00000000-0000-0000-0000-000000000001"), "p1", "q"
        )

        mock_v3.assert_called_once()
