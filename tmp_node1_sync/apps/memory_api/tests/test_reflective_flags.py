"""
Tests for Reflective Memory Feature Flags

These tests ensure that feature flags actually affect system behavior.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from apps.memory_api.services.context_builder import ContextBuilder
from apps.memory_api.workers.memory_maintenance import (
    DreamingWorker,
    MaintenanceScheduler,
    SummarizationWorker,
)


class TestReflectiveMemoryFlags:
    """Test that REFLECTIVE_MEMORY_ENABLED flag controls reflection behavior"""

    @pytest.mark.asyncio
    @patch("apps.memory_api.services.context_builder.settings")
    async def test_reflective_memory_disabled_no_reflections(self, mock_settings):
        """When REFLECTIVE_MEMORY_ENABLED=False, no reflections should be retrieved"""
        # Arrange
        mock_settings.REFLECTIVE_MEMORY_ENABLED = False

        mock_reflection_engine = AsyncMock()
        mock_rae_service = AsyncMock()
        context_builder = ContextBuilder(rae_service=mock_rae_service)

        # Act
        reflections = await context_builder._retrieve_reflections(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            project_id="test_project",
            query="test query",
        )

        # Assert
        assert reflections == []
        # Verify reflection engine was NOT called
        mock_reflection_engine.query_reflections.assert_not_called()

    @pytest.mark.asyncio
    @patch("apps.memory_api.services.context_builder.settings")
    async def test_reflective_memory_enabled_retrieves_reflections(self, mock_settings):
        """When REFLECTIVE_MEMORY_ENABLED=True, reflections should be retrieved"""
        # Arrange
        mock_settings.REFLECTIVE_MEMORY_ENABLED = True
        mock_settings.REFLECTIVE_MAX_ITEMS_PER_QUERY = 5
        mock_settings.REFLECTION_MIN_IMPORTANCE_THRESHOLD = 0.5

        mock_reflection_engine = AsyncMock()
        mock_reflection_engine.query_reflections = AsyncMock(
            return_value=[
                {
                    "id": "refl1",
                    "content": "Test reflection",
                    "importance": 0.8,
                    "tags": ["test"],
                    "created_at": "2025-01-01",
                }
            ]
        )
        mock_rae_service = AsyncMock()

        context_builder = ContextBuilder(rae_service=mock_rae_service)

        # Act
        reflections = await context_builder._retrieve_reflections(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            project_id="test_project",
            query="test query",
        )

        # Assert
        assert len(reflections) == 1
        assert reflections[0].type == "reflection"
        assert reflections[0].content == "Test reflection"
        mock_reflection_engine.query_reflections.assert_called_once()


class TestReflectiveMemoryMode:
    """Test that REFLECTIVE_MEMORY_MODE affects limits"""

    @pytest.mark.asyncio
    @patch("apps.memory_api.services.context_builder.settings")
    async def test_lite_mode_uses_lower_limits(self, mock_settings):
        """Lite mode should use lower retrieval limits"""
        # Arrange
        mock_settings.REFLECTIVE_MEMORY_ENABLED = True
        mock_settings.REFLECTIVE_MEMORY_MODE = "lite"
        mock_settings.REFLECTIVE_MAX_ITEMS_PER_QUERY = 3  # Lower in lite mode
        mock_settings.REFLECTION_MIN_IMPORTANCE_THRESHOLD = 0.5

        mock_reflection_engine = AsyncMock()
        mock_reflection_engine.query_reflections = AsyncMock(return_value=[])
        mock_rae_service = AsyncMock()

        context_builder = ContextBuilder(rae_service=mock_rae_service)

        # Act
        await context_builder._retrieve_reflections(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            project_id="test_project",
            query="test query",
        )

        # Assert
        mock_reflection_engine.query_reflections.assert_called_once_with(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            project_id="test_project",
            query_text="test query",
            k=3,  # Lite mode limit
            min_importance=0.5,
        )

    @pytest.mark.asyncio
    @patch("apps.memory_api.services.context_builder.settings")
    async def test_full_mode_uses_higher_limits(self, mock_settings):
        """Full mode should use higher retrieval limits"""
        # Arrange
        mock_settings.REFLECTIVE_MEMORY_ENABLED = True
        mock_settings.REFLECTIVE_MEMORY_MODE = "full"
        mock_settings.REFLECTIVE_MAX_ITEMS_PER_QUERY = 5  # Higher in full mode
        mock_settings.REFLECTION_MIN_IMPORTANCE_THRESHOLD = 0.5

        mock_reflection_engine = AsyncMock()
        mock_reflection_engine.query_reflections = AsyncMock(return_value=[])
        mock_rae_service = AsyncMock()

        context_builder = ContextBuilder(rae_service=mock_rae_service)

        # Act
        await context_builder._retrieve_reflections(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            project_id="test_project",
            query="test query",
        )

        # Assert
        mock_reflection_engine.query_reflections.assert_called_once_with(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            project_id="test_project",
            query_text="test query",
            k=5,  # Full mode limit
            min_importance=0.5,
        )


class TestDreamingEnabled:
    """Test that DREAMING_ENABLED flag controls dreaming worker"""

    @pytest.mark.asyncio
    @patch("apps.memory_api.workers.memory_maintenance.settings")
    async def test_dreaming_disabled_no_dreaming(self, mock_settings):
        """When DREAMING_ENABLED=False, dreaming should be skipped"""
        # Arrange
        mock_settings.DREAMING_ENABLED = False
        mock_rae_service = AsyncMock()
        worker = DreamingWorker(rae_service=mock_rae_service)

        # Act
        results = await worker.run_dreaming_cycle(
            tenant_id=str(UUID("00000000-0000-0000-0000-000000000001")),
            project_id="test_project",
        )

        # Assert
        assert results == []

    @pytest.mark.asyncio
    @patch("apps.memory_api.workers.memory_maintenance.settings")
    async def test_dreaming_enabled_runs_dreaming(self, mock_settings):
        """When DREAMING_ENABLED=True, dreaming should run"""
        # Arrange
        mock_settings.REFLECTIVE_MEMORY_ENABLED = True
        mock_settings.DREAMING_ENABLED = True
        mock_settings.DREAMING_LOOKBACK_HOURS = 24
        mock_settings.DREAMING_MIN_IMPORTANCE = 0.6
        mock_settings.DREAMING_MAX_SAMPLES = 20

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])  # No memories

        # Create async context manager for pool.acquire()
        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_rae_service = AsyncMock()
        mock_rae_service.postgres_pool.acquire = mock_acquire

        dreaming_worker = DreamingWorker(rae_service=mock_rae_service)

        # Act
        results = await dreaming_worker.run_dreaming_cycle(
            tenant_id=str(UUID("00000000-0000-0000-0000-000000000001")),
            project_id="test_project",
        )

        # Assert - dreaming attempted to fetch memories
        assert results == []  # No memories, so no results
        mock_conn.fetch.assert_called_once()


class TestSummarizationEnabled:
    """Test that SUMMARIZATION_ENABLED flag controls summarization"""

    @pytest.mark.asyncio
    @patch("apps.memory_api.workers.memory_maintenance.settings")
    async def test_summarization_disabled_no_summary(self, mock_settings):
        """When SUMMARIZATION_ENABLED=False, summarization should be skipped"""
        # Arrange
        mock_settings.SUMMARIZATION_ENABLED = False
        mock_rae_service = AsyncMock()
        worker = SummarizationWorker(rae_service=mock_rae_service)
        from uuid import uuid4

        # Act
        result = await worker.summarize_session(
            tenant_id=str(UUID("00000000-0000-0000-0000-000000000001")),
            project_id="test_project",
            session_id=uuid4(),
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    @patch("apps.memory_api.workers.memory_maintenance.settings")
    async def test_summarization_enabled_creates_summary(self, mock_settings):
        """When SUMMARIZATION_ENABLED=True, summarization should run"""
        # Arrange
        mock_settings.SUMMARIZATION_ENABLED = True
        mock_settings.SUMMARIZATION_MIN_EVENTS = 10

        mock_rae_service = AsyncMock()
        mock_rae_service.list_memories.return_value = ["Event 1", "Event 2"]
        mock_rae_service.store_memory.return_value = "summary-id"

        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = MagicMock(
            summary="Session Summary",
            key_topics=["topic1"],
            sentiment="positive",
            user_intent="test",
            suggested_actions=[],
        )

        worker = SummarizationWorker(rae_service=mock_rae_service)
        worker.llm_provider = mock_llm

        from uuid import uuid4

        # Act
        result = await worker.summarize_session(
            tenant_id=str(UUID("00000000-0000-0000-0000-000000000001")),
            project_id="test-project",
            session_id=uuid4(),
            min_events=1,
        )

        # Assert
        assert result is not None
        # Verify call to service
        mock_rae_service.store_memory.assert_called_once()


class TestMaintenanceScheduler:
    """Test that MaintenanceScheduler respects all flags"""

    @pytest.mark.asyncio
    @patch("apps.memory_api.workers.memory_maintenance.settings")
    async def test_maintenance_with_all_flags_disabled(self, mock_settings):
        """When all flags disabled, only decay should run"""
        # Arrange
        mock_settings.REFLECTIVE_MEMORY_ENABLED = False
        mock_settings.DREAMING_ENABLED = False
        mock_settings.SUMMARIZATION_ENABLED = False
        mock_settings.MEMORY_BASE_DECAY_RATE = 0.01
        mock_settings.MEMORY_ACCESS_COUNT_BOOST = True

        mock_decay_worker = AsyncMock()
        mock_decay_worker.run_decay_cycle = AsyncMock(return_value={"updated": 100})
        mock_decay_worker._get_all_tenant_ids = AsyncMock(return_value=["tenant1"])

        mock_rae_service = AsyncMock()
        scheduler = MaintenanceScheduler(rae_service=mock_rae_service)
        scheduler.decay_worker = mock_decay_worker

        # Act
        stats = await scheduler.run_daily_maintenance(tenant_ids=["tenant1"])

        # Assert
        assert stats["decay"]["updated"] == 100
        assert stats["dreaming"]["skipped"] is True
        assert stats["config"]["reflective_enabled"] is False
        assert stats["config"]["dreaming_enabled"] is False

    @pytest.mark.asyncio
    @patch("apps.memory_api.workers.memory_maintenance.settings")
    async def test_maintenance_with_all_flags_enabled(self, mock_settings):
        """When all flags enabled, all workers should run"""
        # Arrange
        mock_settings.REFLECTIVE_MEMORY_ENABLED = True
        mock_settings.DREAMING_ENABLED = True
        mock_settings.SUMMARIZATION_ENABLED = True
        mock_settings.MEMORY_BASE_DECAY_RATE = 0.01
        mock_settings.MEMORY_ACCESS_COUNT_BOOST = True
        mock_settings.DREAMING_LOOKBACK_HOURS = 24
        mock_settings.DREAMING_MIN_IMPORTANCE = 0.6
        mock_settings.DREAMING_MAX_SAMPLES = 20

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_decay_worker = AsyncMock()
        mock_decay_worker.run_decay_cycle = AsyncMock(return_value={"updated": 100})
        mock_decay_worker._get_all_tenant_ids = AsyncMock(return_value=["tenant1"])

        mock_rae_service = AsyncMock()
        scheduler = MaintenanceScheduler(rae_service=mock_rae_service)
        scheduler.decay_worker = mock_decay_worker

        # Act
        stats = await scheduler.run_daily_maintenance(tenant_ids=["tenant1"])

        # Assert
        assert stats["decay"]["updated"] == 100
        assert "skipped" not in stats["dreaming"] or not stats["dreaming"].get(
            "skipped"
        )
        assert stats["config"]["reflective_enabled"] is True
        assert stats["config"]["dreaming_enabled"] is True
