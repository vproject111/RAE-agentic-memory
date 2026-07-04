from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from apps.memory_api.repositories.cost_logs_repository import (
    CostStatistics,
    LLMCallLog,
    LogLLMCallParams,
    ModelBreakdown,
    get_cache_savings,
    get_cost_statistics,
    get_model_breakdown,
    get_recent_logs,
    log_llm_call,
)


# Fixtures for reusable mocks
@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    return pool


@pytest.fixture
def sample_log_params():
    return LogLLMCallParams(
        tenant_id="tenant-123",
        project_id="project-456",
        model="gpt-4o",
        provider="openai",
        operation="query",
        input_tokens=100,
        output_tokens=50,
        input_cost_per_million=5.0,
        output_cost_per_million=15.0,
        total_cost_usd=0.00125,
        cache_hit=False,
        request_id="req-789",
        user_id="user-001",
        latency_ms=500,
    )


@pytest.fixture
def sample_stats_record():
    return {
        "total_calls": 10,
        "successful_calls": 9,
        "failed_calls": 1,
        "total_input_tokens": 1000,
        "total_output_tokens": 500,
        "total_tokens": 1500,
        "total_cost_usd": 0.05,
        "avg_cost_per_call": 0.005,
        "cache_hits": 2,
        "total_tokens_saved": 200,
        "avg_latency_ms": 450.0,
    }


# Tests for log_llm_call
@pytest.mark.asyncio
async def test_log_llm_call_success(mock_pool, sample_log_params):
    # Setup mock return
    mock_pool.fetchrow.return_value = {"id": "log-uuid-123"}

    # Execute
    log_id = await log_llm_call(mock_pool, sample_log_params)

    # Verify
    assert log_id == "log-uuid-123"
    mock_pool.fetchrow.assert_called_once()

    # Check if arguments were passed correctly (checking a few key ones)
    args = mock_pool.fetchrow.call_args[0]
    assert args[1] == "tenant-123"  # tenant_id
    assert args[3] == "gpt-4o"  # model
    assert args[10] == 0.00125  # total_cost_usd


@pytest.mark.asyncio
async def test_log_llm_call_failure(mock_pool, sample_log_params):
    # Setup mock to raise exception
    mock_pool.fetchrow.side_effect = Exception("DB Connection Error")

    # Execute & Verify
    with pytest.raises(Exception) as excinfo:
        await log_llm_call(mock_pool, sample_log_params)
    assert "DB Connection Error" in str(excinfo.value)


# Tests for get_cost_statistics
@pytest.mark.asyncio
async def test_get_cost_statistics_success(mock_pool, sample_stats_record):
    # Setup mock
    mock_pool.fetchrow.return_value = sample_stats_record

    period_start = datetime.now(timezone.utc) - timedelta(days=1)
    period_end = datetime.now(timezone.utc)

    # Execute
    stats = await get_cost_statistics(
        mock_pool, "tenant-123", "project-456", period_start, period_end
    )

    # Verify
    assert isinstance(stats, CostStatistics)
    assert stats.total_calls == 10
    assert stats.total_cost_usd == 0.05
    assert stats.cache_hit_rate == 20.0  # 2/10 * 100
    assert stats.avg_latency_ms == 450.0


@pytest.mark.asyncio
async def test_get_cost_statistics_empty(mock_pool):
    # Setup mock for empty result (all None or 0)
    mock_pool.fetchrow.return_value = {
        "total_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "total_cost_usd": 0,
        "avg_cost_per_call": 0,
        "cache_hits": 0,
        "total_tokens_saved": 0,
        "avg_latency_ms": None,
    }

    # Execute
    stats = await get_cost_statistics(
        mock_pool, "t", "p", datetime.now(), datetime.now()
    )

    # Verify handles zeros correctly
    assert stats.total_calls == 0
    assert stats.cache_hit_rate == 0.0
    assert stats.total_cost_usd == 0.0


# Tests for get_model_breakdown
@pytest.mark.asyncio
async def test_get_model_breakdown(mock_pool):
    # Setup mock records
    records = [
        {
            "model": "gpt-4",
            "provider": "openai",
            "total_calls": 5,
            "total_tokens": 5000,
            "total_cost_usd": 0.15,
            "avg_cost_per_call": 0.03,
            "avg_latency_ms": 800.0,
        },
        {
            "model": "claude-3",
            "provider": "anthropic",
            "total_calls": 10,
            "total_tokens": 3000,
            "total_cost_usd": 0.05,
            "avg_cost_per_call": 0.005,
            "avg_latency_ms": 400.0,
        },
    ]
    mock_pool.fetch.return_value = records

    # Execute
    result = await get_model_breakdown(
        mock_pool, "t", "p", datetime.now(), datetime.now()
    )

    # Verify
    assert len(result) == 2
    assert isinstance(result[0], ModelBreakdown)
    assert result[0].model == "gpt-4"
    assert result[1].model == "claude-3"


# Tests for get_cache_savings
@pytest.mark.asyncio
async def test_get_cache_savings(mock_pool):
    # Setup mock
    record = {
        "total_calls": 100,
        "cache_hits": 25,
        "total_tokens_saved": 5000,
        "total_actual_cost": 10.0,
        "avg_cost_per_call": 0.1,  # Cost per call if not cached (avg)
    }
    mock_pool.fetchrow.return_value = record

    # Execute
    savings = await get_cache_savings(
        mock_pool, "t", "p", datetime.now(), datetime.now()
    )

    # Verify
    assert savings["cache_hits"] == 25
    assert savings["cache_hit_rate"] == 25.0  # 25/100 * 100
    # Estimated saved = hits * avg_cost = 25 * 0.1 = 2.5
    assert savings["estimated_cost_saved_usd"] == 2.5


# Tests for get_recent_logs
@pytest.mark.asyncio
async def test_get_recent_logs(mock_pool):
    # Setup mock
    mock_timestamp = datetime.now(timezone.utc)
    records = [
        {
            "id": "1",
            "tenant_id": "t",
            "project_id": "p",
            "model": "m",
            "provider": "pr",
            "operation": "op",
            "input_tokens": 10,
            "output_tokens": 10,
            "total_tokens": 20,
            "input_cost_per_million": 1,
            "output_cost_per_million": 1,
            "total_cost_usd": 0.01,
            "timestamp": mock_timestamp,
            "cache_hit": False,
            "cache_tokens_saved": 0,
            "error": False,
        }
    ]
    mock_pool.fetch.return_value = records

    # Execute
    logs = await get_recent_logs(mock_pool, "t", "p")

    # Verify
    assert len(logs) == 1
    assert isinstance(logs[0], LLMCallLog)
    assert logs[0].id == "1"
