from datetime import datetime, timezone
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.workers.memory_maintenance import (
    DecayWorker,
    DreamingWorker,
    MaintenanceScheduler,
    SessionSummaryResponse,
    SummarizationWorker,
)


@pytest.fixture
def mock_pool():
    pool = MagicMock()

    # pool.acquire() returns an async context manager
    # We need a mock that has __aenter__ and __aexit__
    acquire_context = MagicMock()
    conn = AsyncMock()
    acquire_context.__aenter__.return_value = conn
    acquire_context.__aexit__.return_value = None

    pool.acquire.return_value = acquire_context

    return pool


@pytest.fixture
def mock_settings(mocker):
    settings = mocker.patch("apps.memory_api.workers.memory_maintenance.settings")
    settings.SUMMARIZATION_ENABLED = True
    settings.SUMMARIZATION_MIN_EVENTS = 10
    settings.RAE_LLM_MODEL_DEFAULT = "gpt-4"
    settings.REFLECTIVE_MEMORY_ENABLED = True
    settings.DREAMING_ENABLED = True
    settings.REFLECTIVE_MEMORY_MODE = "balanced"
    settings.DREAMING_LOOKBACK_HOURS = 24
    settings.DREAMING_MIN_IMPORTANCE = 0.6
    settings.DREAMING_MAX_SAMPLES = 20
    settings.MEMORY_BASE_DECAY_RATE = 0.01
    settings.MEMORY_ACCESS_COUNT_BOOST = True
    return settings


@pytest.fixture
def mock_rae_service():
    """Mock for RAECoreService."""
    service = AsyncMock(spec=RAECoreService)
    pool = MagicMock()
    # Setup acquire() as an async context manager
    connection = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    service.postgres_pool = pool

    service.list_memories.return_value = []  # Default empty list for sessions
    service.store_memory.return_value = "mock-summary-id"  # For storing summary
    return service


# --- DecayWorker Tests ---


@pytest.mark.asyncio
async def test_decay_worker_run_decay_cycle(mock_pool, mock_settings, mock_rae_service):
    mock_scoring_service = AsyncMock()
    mock_scoring_service.decay_importance.return_value = 5
    worker = DecayWorker(
        rae_service=mock_rae_service, scoring_service=mock_scoring_service
    )

    # Mock getting tenant IDs with valid UUIDs
    tenant1 = str(uuid4())
    tenant2 = str(uuid4())
    cast(Any, worker)._get_all_tenant_ids = AsyncMock(return_value=[tenant1, tenant2])

    stats = await worker.run_decay_cycle(decay_rate=0.05, consider_access_stats=False)

    assert stats["total_tenants"] == 2
    assert stats["total_updated"] == 10
    assert mock_scoring_service.decay_importance.call_count == 2


@pytest.mark.asyncio
async def test_decay_worker_run_decay_cycle_error(
    mock_pool, mock_settings, mock_rae_service
):
    mock_scoring_service = AsyncMock()
    mock_scoring_service.decay_importance.side_effect = Exception("Decay failed")

    worker = DecayWorker(
        rae_service=mock_rae_service, scoring_service=mock_scoring_service
    )
    cast(Any, worker)._get_all_tenant_ids = AsyncMock(return_value=[str(uuid4())])

    stats = await worker.run_decay_cycle(decay_rate=0.05)

    assert stats["total_updated"] == 0
    # Should catch exception and continue/finish
    assert stats["total_tenants"] == 1


@pytest.mark.asyncio
async def test_hourly_maintenance(mock_pool, mock_settings, mock_rae_service):
    scheduler = MaintenanceScheduler(rae_service=mock_rae_service)
    stats = await scheduler.run_hourly_maintenance()
    assert "started_at" in stats
    assert "completed_at" in stats


# --- SummarizationWorker Tests ---


@pytest.mark.asyncio
async def test_summarize_session_success(mock_pool, mock_settings, mock_rae_service):
    session_id_val = uuid4()  # Capture the session_id

    # Mock memories to include metadata with session_id
    memories = [
        {
            "id": i,
            "content": f"event {i}",
            "importance": 0.5,
            "metadata": {"session_id": str(session_id_val)},
        }
        for i in range(12)
    ]
    mock_rae_service.list_memories.return_value = memories

    mock_rae_service.store_memory.return_value = "summary_id"

    worker = SummarizationWorker(rae_service=mock_rae_service)
    worker.llm_provider = AsyncMock()

    response_obj = SessionSummaryResponse(
        summary="Summary text", key_topics=["topic"], sentiment="neutral"
    )
    worker.llm_provider.generate_structured.return_value = response_obj

    result = await worker.summarize_session(
        tenant_id="tenant1",
        project_id="proj1",
        session_id=session_id_val,
        min_events=10,
    )

    assert result is not None
    assert result["id"] == "summary_id"
    mock_rae_service.store_memory.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_session_insufficient_events(
    mock_pool, mock_settings, mock_rae_service
):
    mock_rae_service.list_memories.return_value = [{"id": 1}]

    worker = SummarizationWorker(rae_service=mock_rae_service)

    result = await worker.summarize_session(
        tenant_id="tenant1", project_id="proj1", session_id=uuid4(), min_events=10
    )

    assert result is None
    mock_rae_service.store_memory.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_session_disabled(mock_pool, mock_settings, mock_rae_service):
    mock_settings.SUMMARIZATION_ENABLED = False
    worker = SummarizationWorker(rae_service=mock_rae_service)

    result = await worker.summarize_session(
        tenant_id="tenant1", project_id="proj1", session_id=uuid4()
    )

    assert result is None


@pytest.mark.asyncio
async def test_summarize_long_sessions(mock_pool, mock_settings, mock_rae_service):
    worker = SummarizationWorker(rae_service=mock_rae_service)

    # Mock summarize_session
    cast(Any, worker).summarize_session = AsyncMock(return_value={"id": "summary"})

    # Mock return of long sessions
    session_id = str(uuid4())
    mock_rae_service.list_long_sessions.return_value = [
        {"session_id": session_id, "event_count": 150}
    ]

    summaries = await worker.summarize_long_sessions(
        tenant_id="tenant1", project_id="proj1", event_threshold=100
    )

    # Verify results
    assert len(summaries) == 1
    cast(Any, worker).summarize_session.assert_called_once()


# --- DreamingWorker Tests ---


@pytest.mark.asyncio
async def test_dreaming_cycle_success(mock_pool, mock_settings, mock_rae_service):
    mock_reflection_engine = AsyncMock()
    mock_reflection_engine.generate_reflection.return_value = MagicMock()
    mock_reflection_engine.store_reflection.return_value = {"reflection_id": "ref1"}

    worker = DreamingWorker(
        rae_service=mock_rae_service, reflection_engine=mock_reflection_engine
    )

    # Mock return of high importance memories
    records = [
        {
            "id": uuid4(),
            "content": "high importance",
            "importance": 0.9,
            "created_at": datetime.now(timezone.utc),
            "tags": [],
        }
        for _ in range(5)
    ]
    mock_rae_service.list_memories.return_value = records

    results = await worker.run_dreaming_cycle(tenant_id="tenant1", project_id="proj1")

    assert len(results) == 1
    assert results[0]["reflection_id"] == "ref1"


@pytest.mark.asyncio
async def test_dreaming_cycle_disabled(mock_pool, mock_settings, mock_rae_service):
    mock_settings.DREAMING_ENABLED = False
    worker = DreamingWorker(rae_service=mock_rae_service)

    results = await worker.run_dreaming_cycle(tenant_id="t1", project_id="p1")
    assert results == []


@pytest.mark.asyncio
async def test_dreaming_cycle_insufficient_memories(
    mock_pool, mock_settings, mock_rae_service
):
    mock_rae_service.postgres_pool = mock_pool
    worker = DreamingWorker(rae_service=mock_rae_service)

    mock_pool._test_conn.fetch.return_value = []  # No memories

    results = await worker.run_dreaming_cycle(tenant_id="t1", project_id="p1")
    assert results == []


# --- MaintenanceScheduler Tests ---


@pytest.mark.asyncio
async def test_daily_maintenance(mock_pool, mock_settings, mock_rae_service):
    scheduler = MaintenanceScheduler(rae_service=mock_rae_service)

    # Mock workers
    scheduler.decay_worker = AsyncMock()
    scheduler.decay_worker.run_decay_cycle.return_value = {"total_updated": 10}
    scheduler.decay_worker._get_all_tenant_ids.return_value = ["t1"]

    scheduler.dreaming_worker = AsyncMock()
    scheduler.dreaming_worker.run_dreaming_cycle.return_value = [{"ref_id": 1}]

    stats = await scheduler.run_daily_maintenance()

    assert stats["decay"]["total_updated"] == 10
    assert stats["dreaming"]["reflections_generated"] == 1

    scheduler.decay_worker.run_decay_cycle.assert_called_once()
    scheduler.dreaming_worker.run_dreaming_cycle.assert_called_once()


@pytest.mark.asyncio
async def test_daily_maintenance_dreaming_disabled(
    mock_pool, mock_settings, mock_rae_service
):
    mock_settings.DREAMING_ENABLED = False
    scheduler = MaintenanceScheduler(rae_service=mock_rae_service)

    scheduler.decay_worker = AsyncMock()
    scheduler.decay_worker.run_decay_cycle.return_value = {}
    scheduler.dreaming_worker = AsyncMock()

    stats = await scheduler.run_daily_maintenance()

    assert stats["dreaming"]["skipped"] is True
    scheduler.dreaming_worker.run_dreaming_cycle.assert_not_called()
