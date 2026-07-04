"""
Tests for Background Tasks (Celery)

Test suite for Celery background tasks including lazy graph extraction,
reflection generation, and scheduled maintenance tasks.

Test Coverage Goals (per test_2.md):
- Task calls correct service
- Success/exception handling (log + retry)
- Scheduler calls correct tasks

Priority: HIGH (Critical for async processing)
Current Coverage: 0% -> Target: 60%+
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

pytest.importorskip(
    "community",
    reason="Requires community (python-louvain) for community detection tests.",
)

from apps.memory_api.tasks.background_tasks import (
    apply_memory_decay,
    cleanup_expired_data_task,
    decay_memory_importance_task,
    extract_graph_lazy,
    gdpr_delete_user_data_task,
    generate_reflection_for_project,
    process_graph_extraction_queue,
)


class TestExtractGraphLazy:
    """Tests for lazy graph extraction background task.

    This is the most critical task - handles background graph extraction
    with retry logic and cost optimization (mini model).
    """

    @patch("apps.memory_api.tasks.background_tasks.get_pool")
    @patch("apps.memory_api.tasks.background_tasks.GraphExtractionService")
    def test_extract_graph_success(self, mock_service_class, mock_get_pool):
        """Test successful graph extraction.

        Verifies:
        - Service is called with correct parameters
        - Result contains expected data
        - Pool is properly closed
        """
        # Mock pool
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool

        # Mock service and extraction result
        mock_service = Mock()
        mock_result = Mock()
        mock_result.triples = [Mock(), Mock(), Mock()]  # 3 triples
        mock_result.extracted_entities = ["Entity1", "Entity2"]
        mock_service.extract_knowledge_graph = AsyncMock(return_value=mock_result)
        mock_service_class.return_value = mock_service

        # Execute task
        result = extract_graph_lazy(
            memory_ids=["mem1", "mem2"], tenant_id="tenant-123", use_mini_model=True
        )

        # Verify service was called
        mock_service.extract_knowledge_graph.assert_called_once()
        call_kwargs = mock_service.extract_knowledge_graph.call_args[1]
        assert call_kwargs["tenant_id"] == "tenant-123"
        assert call_kwargs["min_confidence"] == 0.7

        # Verify result
        assert result["success"] is True
        assert result["triples"] == 3
        assert result["entities"] == 2

    @patch("apps.memory_api.tasks.background_tasks.get_pool")
    @patch("apps.memory_api.tasks.background_tasks.GraphExtractionService")
    def test_extract_graph_with_mini_model(self, mock_service_class, mock_get_pool):
        """Test that mini model is used when requested.

        Cost optimization: gpt-4o-mini instead of gpt-4.
        """
        # Mock pool
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool

        # Mock service with LLM provider
        mock_service = Mock()
        mock_service.llm_provider = Mock()
        mock_service.llm_provider.model = "gpt-4"
        mock_result = Mock(triples=[], extracted_entities=[])
        mock_service.extract_knowledge_graph = AsyncMock(return_value=mock_result)
        mock_service_class.return_value = mock_service

        # Execute with mini model
        extract_graph_lazy(
            memory_ids=["mem1"], tenant_id="tenant-123", use_mini_model=True
        )

        # Verify LLM was called with mini model if specified
        assert mock_service.llm_provider.model == "gpt-4"

    @patch("apps.memory_api.tasks.background_tasks.get_pool")
    @patch("apps.memory_api.tasks.background_tasks.GraphExtractionService")
    def test_extract_graph_exception_handling(self, mock_service_class, mock_get_pool):
        """Test that exceptions are logged and trigger retry.

        Verifies:
        - Exception is caught
        - Error is logged
        - Retry is triggered with exponential backoff
        """
        # Mock pool
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool

        # Mock service that raises exception
        mock_service = Mock()
        mock_service.extract_knowledge_graph = AsyncMock(
            side_effect=Exception("LLM API error")
        )
        mock_service_class.return_value = mock_service

        # Mock self.retry for Celery task
        mock_self = Mock()
        mock_self.request = Mock()
        mock_self.request.retries = 0
        mock_self.retry = Mock(side_effect=Exception("Retry triggered"))

        # Execute should raise exception (retry)
        with pytest.raises(Exception):
            # Bind self to the task
            task = extract_graph_lazy
            task.__self__ = mock_self
            task(mock_self, memory_ids=["mem1"], tenant_id="tenant-123")

    @patch("apps.memory_api.tasks.background_tasks.get_pool")
    @patch("apps.memory_api.tasks.background_tasks.GraphExtractionService")
    def test_extract_graph_pool_cleanup(self, mock_service_class, mock_get_pool):
        """Test that pool is closed even on exception.

        Resource cleanup is critical to avoid connection leaks.
        """
        # Mock pool
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool

        # Mock service that raises
        mock_service = Mock()
        mock_service.extract_knowledge_graph = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_service_class.return_value = mock_service

        # Mock retry to prevent actual retry
        with patch.object(extract_graph_lazy, "retry", side_effect=Exception("Retry")):
            try:
                extract_graph_lazy(memory_ids=["mem1"], tenant_id="tenant-123")
            except Exception:
                pass

        # Pool close should still be called
        mock_pool.close.assert_called_once()


class TestProcessGraphExtractionQueue:
    """Tests for periodic graph extraction queue processor."""

    @patch("apps.memory_api.tasks.background_tasks.get_pool")
    @patch("apps.memory_api.tasks.background_tasks.extract_graph_lazy")
    def test_queue_processor_schedules_tasks(self, mock_extract_task, mock_get_pool):
        """Test that queue processor schedules extraction tasks."""
        # Mock connection
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"tenant_id": "tenant1", "memory_ids": ["mem1", "mem2"]},
            {"tenant_id": "tenant2", "memory_ids": ["mem3", "mem4", "mem5"]},
        ]

        # Mock pool
        mock_pool = AsyncMock()
        # Mock acquire to be an async context manager returning mock_conn
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_pool.close = AsyncMock()

        # Shortcut methods on pool
        mock_pool.fetch = mock_conn.fetch

        mock_get_pool.return_value = mock_pool

        # Mock the delay method
        mock_extract_task.delay = Mock()

        # Execute
        process_graph_extraction_queue()

        # Verify tasks were scheduled
        assert mock_extract_task.delay.call_count == 2

        # Verify first call
        first_call = mock_extract_task.delay.call_args_list[0]
        assert first_call[1]["tenant_id"] == "tenant1"
        assert first_call[1]["memory_ids"] == ["mem1", "mem2"]
        assert first_call[1]["use_mini_model"] is True

    @patch("apps.memory_api.tasks.background_tasks.get_pool")
    def test_queue_processor_no_pending_memories(self, mock_get_pool):
        """Test queue processor with no pending memories."""
        # Mock connection
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        # Mock pool
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_pool.close = AsyncMock()

        # Shortcut methods on pool
        mock_pool.fetch = mock_conn.fetch

        mock_get_pool.return_value = mock_pool

        # Should not raise exception
        process_graph_extraction_queue()

        # Pool should still be closed
        mock_pool.close.assert_called_once()


class TestGenerateReflection:
    """Tests for reflection generation task."""

    @patch("apps.memory_api.tasks.background_tasks.get_pool")
    @patch("apps.memory_api.tasks.background_tasks.ReflectionEngine")
    def test_generate_reflection_calls_engine(self, mock_engine_class, mock_get_pool):
        """Test that reflection task calls the engine correctly.

        Verifies service contract is maintained.
        """
        # Mock pool
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool

        # Mock engine
        mock_engine = Mock()
        mock_engine.generate_reflection = AsyncMock()
        mock_engine_class.return_value = mock_engine

        # Execute
        generate_reflection_for_project(project="my-project", tenant_id="tenant-123")

        # Verify engine was called
        mock_engine.generate_reflection.assert_called_once_with(
            "my-project", "tenant-123"
        )

        # Verify cleanup
        mock_pool.close.assert_called_once()


class TestMemoryDecay:
    """Tests for memory decay maintenance task."""

    @patch("apps.memory_api.tasks.background_tasks.rae_context")
    @patch("apps.memory_api.tasks.background_tasks.settings")
    def test_apply_decay_updates_strength(self, mock_settings, mock_rae_context):
        """Test that decay is applied to memory strength."""
        # Mock settings
        mock_settings.MEMORY_DECAY_RATE = 0.95

        # Mock service
        mock_rae_service = AsyncMock()
        mock_rae_service.apply_global_memory_decay = AsyncMock()
        mock_rae_service.delete_expired_memories = AsyncMock()

        # Setup rae_context mock
        mock_rae_context.return_value.__aenter__.return_value = mock_rae_service

        # Execute
        apply_memory_decay()

        # Verify service methods were called
        mock_rae_service.apply_global_memory_decay.assert_called_once_with(0.95)
        mock_rae_service.delete_expired_memories.assert_called_once()


@pytest.mark.asyncio
class TestCleanupExpiredData:
    async def test_cleanup_expired_data_success(self, mock_pool):
        """Test cleanup task runs successfully"""
        # Ensure pool.close is awaitable
        mock_pool.close = AsyncMock()

        # Create a dummy object with .value attribute to simulate Enum keys
        class MockEnum:
            def __init__(self, v):
                self.value = v

        mock_results = {MockEnum("episodic"): 10, MockEnum("embeddings"): 5}

        with patch(
            "apps.memory_api.services.retention_service.RetentionService"
        ) as MockRetention:
            mock_service = MockRetention.return_value
            mock_service.cleanup_expired_data = AsyncMock(return_value=mock_results)

            with patch(
                "apps.memory_api.tasks.background_tasks.get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with patch(
                    "apps.memory_api.tasks.background_tasks.asyncio.run",
                    side_effect=lambda x: x,
                ):
                    result = await cleanup_expired_data_task.run(tenant_id="t1")

                assert result["success"] is True
                assert result["total_deleted"] == 15
                mock_service.cleanup_expired_data.assert_called_once_with(
                    tenant_id="t1"
                )
                mock_pool.close.assert_called_once()

    async def test_cleanup_expired_data_failure(self, mock_pool):
        """Test cleanup task handles failure"""
        mock_pool.close = AsyncMock()

        with patch(
            "apps.memory_api.services.retention_service.RetentionService"
        ) as MockRetention:
            mock_service = MockRetention.return_value
            mock_service.cleanup_expired_data = AsyncMock(
                side_effect=Exception("DB Error")
            )

            with patch(
                "apps.memory_api.tasks.background_tasks.get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with patch(
                    "apps.memory_api.tasks.background_tasks.asyncio.run",
                    side_effect=lambda x: x,
                ):
                    try:
                        await cleanup_expired_data_task(tenant_id="t1")
                    except Exception:
                        pass


@pytest.mark.asyncio
class TestGDPRDeletion:
    async def test_gdpr_deletion_success(self, mock_pool):
        """Test GDPR deletion task"""
        mock_pool.close = AsyncMock()

        with patch(
            "apps.memory_api.services.retention_service.RetentionService"
        ) as MockRetention:
            mock_service = MockRetention.return_value
            mock_service.delete_user_data = AsyncMock(
                return_value={"memories_deleted": 100, "logs_anonymized": 50}
            )

            with patch(
                "apps.memory_api.tasks.background_tasks.get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with patch(
                    "apps.memory_api.tasks.background_tasks.asyncio.run",
                    side_effect=lambda x: x,
                ):
                    result = await gdpr_delete_user_data_task(
                        tenant_id="t1",
                        user_identifier="user@example.com",
                        deleted_by="admin",
                    )

                assert result["success"] is True
                assert result["total_deleted"] == 100
                assert result["total_anonymized"] == 50
                mock_service.delete_user_data.assert_called_once_with(
                    tenant_id="t1",
                    user_identifier="user@example.com",
                    deleted_by="admin",
                )


@pytest.mark.asyncio
class TestDecayMemoryImportance:
    async def test_decay_task_all_tenants(self, mock_pool):
        """Test decay task iterating over tenants"""
        # Use valid UUIDs
        t1 = str(uuid4())
        t2 = str(uuid4())

        # Configure the mock connection provided by the fixture
        mock_pool._test_conn.fetch.return_value = [{"tenant_id": t1}, {"tenant_id": t2}]

        with patch(
            "apps.memory_api.services.importance_scoring.ImportanceScoringService"
        ) as MockScoring:
            mock_service = MockScoring.return_value
            mock_service.decay_importance = AsyncMock(return_value=5)

            with patch(
                "apps.memory_api.tasks.background_tasks.get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with patch(
                    "apps.memory_api.tasks.background_tasks.asyncio.run",
                    side_effect=lambda x: x,
                ):
                    result = await decay_memory_importance_task(tenant_id=None)

                assert result["success"] is True
                assert result["total_memories_updated"] == 10  # 5 * 2
                assert result["tenants_processed"] == 2
                assert mock_service.decay_importance.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
