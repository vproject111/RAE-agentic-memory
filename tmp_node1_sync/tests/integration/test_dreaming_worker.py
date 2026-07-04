"""
Integration tests for DreamingWorker - Background Reflection Generation

Tests the DreamingWorker with real database operations to ensure
pattern analysis and reflection generation work correctly.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.memory_api.models.reflection_v2_models import ReflectionResult
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.reflection_engine_v2 import ReflectionEngineV2
from apps.memory_api.workers.memory_maintenance import DreamingWorker


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_basic_cycle(mock_app_state_pool, mock_env_and_settings):
    """Test basic dreaming cycle generates reflections from high-importance memories."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())
    project_id = "default"

    # Enable dreaming
    with patch("apps.memory_api.config.settings.REFLECTIVE_MEMORY_ENABLED", True):
        with patch("apps.memory_api.config.settings.DREAMING_ENABLED", True):
            # Insert high-importance memories
            async with pool.acquire() as conn:
                for i in range(5):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Important event {i}: User encountered error and found solution",
                        0.8,  # High importance
                        project_id,
                        datetime.now().replace(tzinfo=None) - timedelta(hours=2),
                    )

            # Mock reflection engine
            mock_reflection_engine = MagicMock(spec=ReflectionEngineV2)
            mock_reflection_engine.generate_reflection = AsyncMock(
                return_value=ReflectionResult(
                    reflection_text="Pattern detected: Users frequently encounter errors in this area",
                    importance=0.85,
                    confidence=0.85,
                )
            )
            mock_reflection_engine.store_reflection = AsyncMock(
                return_value={
                    "reflection_id": uuid.uuid4(),
                    "strategy_id": None,
                }
            )

            # Create worker
            rae_service = RAECoreService(postgres_pool=pool)
            worker = DreamingWorker(
                rae_service=rae_service, reflection_engine=mock_reflection_engine
            )

            # Run dreaming cycle
            results = await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=24,
                min_importance=0.6,
                max_samples=20,
            )

            # Verify reflection was generated
            assert len(results) == 1, "Should generate one reflection"
            assert "reflection_id" in results[0], "Should have reflection_id"
            mock_reflection_engine.generate_reflection.assert_called_once()
            mock_reflection_engine.store_reflection.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_disabled(mock_app_state_pool):
    """Test that dreaming worker skips when disabled."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())

    # Disable dreaming
    with patch("apps.memory_api.config.settings.DREAMING_ENABLED", False):
        rae_service = RAECoreService(postgres_pool=pool)
        worker = DreamingWorker(rae_service=rae_service)

        # Run dreaming cycle
        results = await worker.run_dreaming_cycle(
            tenant_id=tenant_id,
            project_id="default",
            lookback_hours=24,
        )

        # Should return empty list
        assert results == [], "Should skip when disabled"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_insufficient_memories(
    mock_app_state_pool, mock_env_and_settings
):
    """Test that dreaming skips when there are insufficient memories."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())
    project_id = "default"

    with patch("apps.memory_api.config.settings.REFLECTIVE_MEMORY_ENABLED", True):
        with patch("apps.memory_api.config.settings.DREAMING_ENABLED", True):
            # Insert only 2 high-importance memories (below threshold of 3)
            async with pool.acquire() as conn:
                for i in range(2):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Important event {i}",
                        0.8,
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    )

            rae_service = RAECoreService(postgres_pool=pool)
            worker = DreamingWorker(rae_service=rae_service)

            # Run dreaming cycle
            results = await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=24,
                min_importance=0.6,
            )

            # Should skip due to insufficient memories
            assert results == [], "Should skip with < 3 memories"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_lookback_window(
    mock_app_state_pool, mock_env_and_settings
):
    """Test that dreaming only considers memories within lookback window."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())
    project_id = "default"

    with patch("apps.memory_api.config.settings.REFLECTIVE_MEMORY_ENABLED", True):
        with patch("apps.memory_api.config.settings.DREAMING_ENABLED", True):
            # Insert recent and old memories
            async with pool.acquire() as conn:
                # Recent memories (within lookback window)
                for i in range(3):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Recent memory {i}",
                        0.8,
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None)
                        - timedelta(hours=2),
                    )

                # Old memories (outside lookback window)
                for i in range(3):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Old memory {i}",
                        0.8,
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None)
                        - timedelta(hours=50),
                    )

            # Mock reflection engine
            mock_reflection_engine = MagicMock(spec=ReflectionEngineV2)
            # Create worker
            rae_service = RAECoreService(postgres_pool=pool)
            worker = DreamingWorker(
                rae_service=rae_service, reflection_engine=mock_reflection_engine
            )

            # Run with 24-hour lookback
            results = await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=24,
                min_importance=0.6,
            )

            # Should only analyze recent memories
            assert len(results) == 1, "Should generate reflection from recent memories"

            # Verify the context passed to generate_reflection
            call_args = mock_reflection_engine.generate_reflection.call_args[0][0]
            assert len(call_args.events) <= 3, "Should only use recent memories"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_importance_filter(
    mock_app_state_pool, mock_env_and_settings
):
    """Test that dreaming only considers high-importance memories."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())
    project_id = "default"

    with patch("apps.memory_api.config.settings.REFLECTIVE_MEMORY_ENABLED", True):
        with patch("apps.memory_api.config.settings.DREAMING_ENABLED", True):
            # Insert mix of high and low importance memories
            async with pool.acquire() as conn:
                # High importance
                for i in range(4):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"High importance memory {i}",
                        0.8,
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    )

                # Low importance (should be filtered out)
                for i in range(5):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Low importance memory {i}",
                        0.3,  # Below threshold
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    )

            # Mock reflection engine
            mock_reflection_engine = MagicMock(spec=ReflectionEngineV2)
            # Create worker
            rae_service = RAECoreService(postgres_pool=pool)
            worker = DreamingWorker(
                rae_service=rae_service, reflection_engine=mock_reflection_engine
            )

            # Run with importance threshold
            results = await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=24,
                min_importance=0.6,  # Filter out low-importance
                max_samples=20,
            )

            # Should only analyze high-importance memories
            assert len(results) == 1, "Should generate reflection"

            # Verify only high-importance memories were used
            call_args = mock_reflection_engine.generate_reflection.call_args[0][0]
            assert (
                len(call_args.events) == 4
            ), "Should only use 4 high-importance memories"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_max_samples_limit(
    mock_app_state_pool, mock_env_and_settings
):
    """Test that dreaming respects max_samples limit."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())
    project_id = "default"

    with patch("apps.memory_api.config.settings.REFLECTIVE_MEMORY_ENABLED", True):
        with patch("apps.memory_api.config.settings.DREAMING_ENABLED", True):
            # Insert many high-importance memories
            async with pool.acquire() as conn:
                for i in range(30):  # More than max_samples
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Memory {i}",
                        0.8,
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    )

            # Mock reflection engine
            mock_reflection_engine = MagicMock(spec=ReflectionEngineV2)
            mock_reflection_engine.generate_reflection = AsyncMock(
                return_value=ReflectionResult(
                    reflection_text="Pattern detected",
                    importance=0.85,
                    confidence=0.85,
                )
            )
            # Create worker
            rae_service = RAECoreService(postgres_pool=pool)
            worker = DreamingWorker(
                rae_service=rae_service, reflection_engine=mock_reflection_engine
            )

            # Run with max_samples limit
            await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=24,
                min_importance=0.6,
                max_samples=10,  # Limit to 10 samples
            )

            # Verify max_samples was respected
            call_args = mock_reflection_engine.generate_reflection.call_args[0][0]
            assert len(call_args.events) <= 10, "Should respect max_samples limit of 10"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_error_handling(
    mock_app_state_pool, mock_env_and_settings
):
    """Test that dreaming worker handles reflection generation errors gracefully."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())
    project_id = "default"

    with patch("apps.memory_api.config.settings.REFLECTIVE_MEMORY_ENABLED", True):
        with patch("apps.memory_api.config.settings.DREAMING_ENABLED", True):
            # Insert memories
            async with pool.acquire() as conn:
                for i in range(5):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Memory {i}",
                        0.8,
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    )

            # Mock reflection engine to raise error
            mock_reflection_engine = MagicMock(spec=ReflectionEngineV2)
            mock_reflection_engine.generate_reflection = AsyncMock(
                side_effect=Exception("LLM service unavailable")
            )

            # Create worker
            rae_service = RAECoreService(postgres_pool=pool)
            worker = DreamingWorker(
                rae_service=rae_service, reflection_engine=mock_reflection_engine
            )

            # Run dreaming cycle
            results = await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=24,
            )

            # Should handle error gracefully and return empty list
            assert results == [], "Should return empty list on error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dreaming_worker_no_recent_memories(
    mock_app_state_pool, mock_env_and_settings
):
    """Test dreaming when there are no recent memories."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())
    project_id = "default"

    with patch("apps.memory_api.config.settings.REFLECTIVE_MEMORY_ENABLED", True):
        with patch("apps.memory_api.config.settings.DREAMING_ENABLED", True):
            # Insert only old memories (outside lookback window)
            async with pool.acquire() as conn:
                for i in range(5):
                    await conn.execute(
                        """
                        INSERT INTO memories (tenant_id, content, importance, layer, agent_id, project, created_at, usage_count)
                        VALUES ($1, $2, $3, 'episodic', $4::text, $4::text, $5, 0)
                        """,
                        tenant_id,
                        f"Old memory {i}",
                        0.8,
                        project_id,
                        datetime.now(timezone.utc).replace(tzinfo=None)
                        - timedelta(days=10),
                    )

            rae_service = RAECoreService(postgres_pool=pool)
            worker = DreamingWorker(rae_service=rae_service)

            # Run with 24-hour lookback
            results = await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=24,
                min_importance=0.6,
            )

            # Should skip due to no recent memories
            assert results == [], "Should skip when no recent memories"
