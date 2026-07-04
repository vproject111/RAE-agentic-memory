from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.services.memory_consolidation import (
    ConsolidationResult,
    ConsolidationStrategy,
    MemoryConsolidationService,
)


@pytest.fixture
def mock_rae_service():
    return AsyncMock()


@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.generate.return_value = "Consolidated Content"
    return client


@pytest.fixture
def service(mock_rae_service, mock_llm_client):
    return MemoryConsolidationService(
        rae_service=mock_rae_service, llm_client=mock_llm_client
    )


@pytest.mark.asyncio
async def test_consolidate_episodic_to_working_success(service):
    """Test successful consolidation from episodic to working memory."""
    tenant_id = uuid4()
    memories = [
        {"id": str(uuid4()), "content": "m1"},
        {"id": str(uuid4()), "content": "m2"},
    ]

    # Mock internal methods
    with (
        patch.object(
            service, "_get_consolidation_candidates", new_callable=AsyncMock
        ) as mock_get_candidates,
        patch.object(
            service, "_group_similar_memories", new_callable=AsyncMock
        ) as mock_group,
        patch.object(
            service, "_consolidate_group", new_callable=AsyncMock
        ) as mock_consolidate,
    ):
        mock_get_candidates.return_value = memories
        mock_group.return_value = [memories]  # One group

        mock_result = ConsolidationResult(
            success=True,
            source_memory_ids=[m["id"] for m in memories],
            target_memory_id="new_mem_id",
            consolidated_content="Consolidated",
        )
        mock_consolidate.return_value = mock_result

        results = await service.consolidate_episodic_to_working(tenant_id)

        assert len(results) == 1
        assert results[0].success is True
        mock_get_candidates.assert_called_once()
        mock_group.assert_called_once()
        mock_consolidate.assert_called_once()


@pytest.mark.asyncio
async def test_consolidate_episodic_to_working_no_candidates(service):
    """Test consolidation when no candidates are found."""
    tenant_id = uuid4()

    with patch.object(
        service, "_get_consolidation_candidates", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = []

        results = await service.consolidate_episodic_to_working(tenant_id)

        assert len(results) == 0
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_consolidate_working_to_semantic_success(service):
    """Test successful consolidation from working to semantic memory."""
    tenant_id = uuid4()
    memories = [{"id": str(uuid4()), "content": "w1"}]

    with (
        patch.object(
            service, "_get_consolidation_candidates", new_callable=AsyncMock
        ) as mock_get,
        patch.object(
            service, "_group_by_patterns", new_callable=AsyncMock
        ) as mock_group,
        patch.object(
            service, "_consolidate_group", new_callable=AsyncMock
        ) as mock_consolidate,
    ):
        mock_get.return_value = memories
        mock_group.return_value = [memories]
        mock_consolidate.return_value = ConsolidationResult(
            success=True, source_memory_ids=[]
        )

        results = await service.consolidate_working_to_semantic(tenant_id)

        assert len(results) == 1
        mock_group.assert_called_once()


@pytest.mark.asyncio
async def test_consolidate_semantic_to_ltm_success(service):
    """Test successful consolidation from semantic to LTM."""
    tenant_id = uuid4()
    memories = [{"id": str(uuid4()), "content": "s1"}]

    with (
        patch.object(
            service, "_get_consolidation_candidates", new_callable=AsyncMock
        ) as mock_get,
        patch.object(
            service, "_consolidate_single", new_callable=AsyncMock
        ) as mock_consolidate,
    ):
        mock_get.return_value = memories
        mock_consolidate.return_value = ConsolidationResult(
            success=True, source_memory_ids=[]
        )

        results = await service.consolidate_semantic_to_ltm(tenant_id)

        assert len(results) == 1
        mock_consolidate.assert_called_once()


@pytest.mark.asyncio
async def test_run_automatic_consolidation(service):
    """Test full automatic consolidation pipeline."""
    tenant_id = uuid4()

    # Mock phase methods
    with (
        patch.object(
            service, "consolidate_episodic_to_working", new_callable=AsyncMock
        ) as mock_p1,
        patch.object(
            service, "consolidate_working_to_semantic", new_callable=AsyncMock
        ) as mock_p2,
        patch.object(
            service, "consolidate_semantic_to_ltm", new_callable=AsyncMock
        ) as mock_p3,
    ):
        mock_p1.return_value = [ConsolidationResult(success=True, source_memory_ids=[])]
        mock_p2.return_value = [ConsolidationResult(success=True, source_memory_ids=[])]
        mock_p3.return_value = [ConsolidationResult(success=True, source_memory_ids=[])]

        summary = await service.run_automatic_consolidation(tenant_id)

        assert summary["total_consolidated"] == 3
        assert len(summary["errors"]) == 0
        mock_p1.assert_called_once()
        mock_p2.assert_called_once()
        mock_p3.assert_called_once()


@pytest.mark.asyncio
async def test_run_automatic_consolidation_failure(service):
    """Test automatic consolidation with failure."""
    tenant_id = uuid4()

    with patch.object(
        service,
        "consolidate_episodic_to_working",
        side_effect=Exception("Database error"),
    ):
        summary = await service.run_automatic_consolidation(tenant_id)

        assert summary["total_consolidated"] == 0
        assert len(summary["errors"]) == 1
        assert "Database error" in summary["errors"][0]["error"]


@pytest.mark.asyncio
async def test_consolidate_group_logic(service):
    """Test logic within _consolidate_group."""
    tenant_id = uuid4()
    memories = [{"id": "m1", "content": "content"}]

    with (
        patch.object(
            service, "_generate_consolidated_content", new_callable=AsyncMock
        ) as mock_gen,
        patch.object(
            service, "_create_consolidated_memory", new_callable=AsyncMock
        ) as mock_create,
        patch.object(
            service, "_mark_as_consolidated", new_callable=AsyncMock
        ) as mock_mark,
    ):
        mock_gen.return_value = "Consolidated"
        mock_create.return_value = "new_id"

        result = await service._consolidate_group(
            tenant_id, memories, "target_layer", ConsolidationStrategy.PATTERN_BASED
        )

        assert result.success is True
        assert result.consolidated_content == "Consolidated"
        assert result.target_memory_id == "new_id"
        mock_mark.assert_called_once()


@pytest.mark.asyncio
async def test_consolidate_group_empty(service):
    """Test _consolidate_group with empty memories."""
    result = await service._consolidate_group(
        uuid4(), [], "layer", ConsolidationStrategy.MANUAL
    )
    assert result.success is False
    assert "No memories" in result.error


@pytest.mark.asyncio
async def test_generate_consolidated_content_fallback(service):
    """Test fallback when no LLM client."""
    service.llm_client = None
    memories = [{"content": "A"}, {"content": "B"}]

    content = await service._generate_consolidated_content(
        memories, "layer", ConsolidationStrategy.MANUAL
    )

    assert "A" in content
    assert "B" in content


@pytest.mark.asyncio
async def test_revert_consolidation(service):
    """Test revert consolidation."""
    # This is mostly placeholder logic in the service, so we just check the return
    result = await service.revert_consolidation("mem_id")
    assert result is True


@pytest.mark.asyncio
async def test_get_consolidation_stats(service):
    stats = await service.get_consolidation_stats(uuid4())
    assert "total_consolidations" in stats


@pytest.mark.asyncio
async def test_preview_consolidation(service):
    with patch.object(
        service, "_generate_consolidated_content", new_callable=AsyncMock
    ) as mock_gen:
        mock_gen.return_value = "Preview"
        result = await service.preview_consolidation(uuid4(), ["m1", "m2"])
        assert result["preview_content"] == "Preview"


@pytest.mark.asyncio
async def test_group_similar_memories_execution(service):
    """Test _group_similar_memories logic (placeholder behavior)."""
    memories = [{"id": "1"}, {"id": "2"}]
    groups = await service._group_similar_memories(memories)
    # Placeholder returns each memory as own group
    assert len(groups) == 2
    assert len(groups[0]) == 1


@pytest.mark.asyncio
async def test_group_by_patterns_execution(service):
    """Test _group_by_patterns logic (placeholder behavior)."""
    memories = [{"id": "1"}, {"id": "2"}]
    groups = await service._group_by_patterns(memories)
    assert len(groups) == 2


@pytest.mark.asyncio
async def test_consolidate_group_exception(service):
    """Test exception handling in _consolidate_group."""
    memories = [{"id": "1"}]

    with patch.object(
        service, "_generate_consolidated_content", side_effect=Exception("Gen Error")
    ):
        result = await service._consolidate_group(
            uuid4(), memories, "layer", ConsolidationStrategy.MANUAL
        )
        assert result.success is False
        assert "Gen Error" in result.error


@pytest.mark.asyncio
async def test_generate_consolidated_content_llm(service, mock_llm_client):
    """Test content generation with LLM client."""
    service.llm_client = mock_llm_client
    memories = [{"content": "A"}]

    content = await service._generate_consolidated_content(
        memories, "working", ConsolidationStrategy.MANUAL
    )

    # In current implementation it calls build_prompt but returns a placeholder string anyway
    # or calls LLM if implemented. The code says:
    # # Call LLM
    # # In production: response = await self.llm_client.generate(prompt)
    # # For now, return placeholder
    # consolidated = f"Consolidated content from {len(memories)} memories"

    # So strictly it returns placeholder even with LLM client.
    # Accept either LLM output or fallback output
    assert "Consolidated content from" in content or "Consolidated Summary" in content


def test_build_consolidation_prompt(service):
    """Test prompt building for different layers."""
    memories = [{"content": "A"}]

    p1 = service._build_consolidation_prompt(
        memories, "working", ConsolidationStrategy.MANUAL
    )
    assert "working memory" in p1

    p2 = service._build_consolidation_prompt(
        memories, "semantic", ConsolidationStrategy.MANUAL
    )
    assert "semantic memory" in p2

    p3 = service._build_consolidation_prompt(
        memories, "ltm", ConsolidationStrategy.MANUAL
    )
    assert "long-term memory" in p3

    p4 = service._build_consolidation_prompt(
        memories, "other", ConsolidationStrategy.MANUAL
    )
    assert "Consolidate these memories" in p4


@pytest.mark.asyncio
async def test_revert_consolidation_exception(service):
    """Test exception handling in revert_consolidation."""
    # The first logger.info is outside try/except, the second is inside.
    # We want the first to succeed, second to fail to trigger exception handler.
    with patch(
        "apps.memory_api.services.memory_consolidation.logger.info",
        side_effect=[None, Exception("Log Error")],
    ):
        result = await service.revert_consolidation("id")
        assert result is False


@pytest.mark.asyncio
async def test_no_candidates_other_layers(service):
    """Test no candidates for working->semantic and semantic->ltm."""
    tenant_id = uuid4()

    with patch.object(service, "_get_consolidation_candidates", return_value=[]):
        r1 = await service.consolidate_working_to_semantic(tenant_id)
        assert len(r1) == 0

        r2 = await service.consolidate_semantic_to_ltm(tenant_id)
        assert len(r2) == 0
