from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.memory_api.services.llm.base import LLMResult, LLMResultUsage
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.reflection_engine import ReflectionEngine, Triples


@pytest.fixture
def mock_rae_service():
    """Mock for RAECoreService."""
    service = AsyncMock(spec=RAECoreService)
    # Configure mock behavior as needed for these tests
    service.list_memories.return_value = [{"id": "1", "content": "Event"}]
    service.store_memory.return_value = "mock-reflection-id"
    return service


@pytest.mark.asyncio
async def test_reflection_flow(mock_rae_service):
    mock_pool = MagicMock()
    # We don't need detailed DB mocks if we mock RAECoreService properly
    # But ReflectionEngine constructor takes pool, so we pass a mock.

    engine = ReflectionEngine(mock_pool, rae_service=mock_rae_service)

    # Mock LLM Provider
    engine.llm_provider = MagicMock()
    engine.llm_provider.generate = AsyncMock(
        return_value=LLMResult(
            text="Insight",
            usage=LLMResultUsage(prompt_tokens=1, candidates_tokens=1, total_tokens=2),
            model_name="gpt",
            finish_reason="stop",
        )
    )
    # Return a Triples model instance
    engine.llm_provider.generate_structured = AsyncMock(
        return_value=Triples(triples=[])
    )

    with patch("apps.memory_api.services.reflection_engine.settings") as mock_settings:
        mock_settings.API_KEY = "key"
        mock_settings.MEMORY_API_URL = "http://mem"
        mock_settings.RAE_LLM_MODEL_DEFAULT = "gpt"

        # Mock GraphRepository if it's initialized inside ReflectionEngine
        # Actually ReflectionEngine takes graph_repository in init, or creates one.
        # We can pass a mock graph repository.
        mock_graph_repo = AsyncMock()
        mock_graph_repo.store_graph_triples.return_value = {
            "nodes_created": 0,
            "edges_created": 0,
        }
        engine.graph_repo = mock_graph_repo

        res = await engine.generate_reflection("p1", "t1")

        # Result should contain project name and be a string
        # The generate_reflection method returns: f"Generated reflection for project {project}: ..."
        assert isinstance(res, str)
        assert "p1" in res

        # Verify RAECoreService was used to fetch episodes
        mock_rae_service.list_memories.assert_called_with(
            tenant_id="t1", layer="episodic", project="p1", limit=10
        )
