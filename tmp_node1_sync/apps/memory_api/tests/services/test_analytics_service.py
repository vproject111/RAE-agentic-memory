from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.memory_api.services.analytics import AnalyticsService


@pytest.fixture
def mock_rae_service():
    service = AsyncMock()
    service.redis_client = AsyncMock()
    service.count_memories = AsyncMock(return_value=0)
    return service


@pytest.fixture
def analytics_service(mock_rae_service):
    return AnalyticsService(rae_service=mock_rae_service)


@pytest.mark.asyncio
async def test_get_tenant_stats_structure(analytics_service):
    # Test that the method returns the expected dictionary structure
    tenant_id = uuid4()

    # Mock internal cache logic to avoid redis calls for this test
    analytics_service._get_from_cache = AsyncMock(return_value=None)
    analytics_service._set_cache = AsyncMock()

    stats = await analytics_service.get_tenant_stats(tenant_id, period_days=30)

    assert str(tenant_id) == stats["tenant_id"]
    assert "period" in stats
    assert "memories" in stats
    assert "queries" in stats
    assert "costs" in stats

    # Verify basic mock values are returned
    assert stats["memories"]["total"] == 0
    assert stats["queries"]["total_queries"] == 0


@pytest.mark.asyncio
async def test_get_tenant_stats_caching(analytics_service):
    tenant_id = uuid4()
    cache_key = f"analytics:{tenant_id}:30"
    cached_data = {"cached": "true"}

    # 1. Test Cache Hit
    # Set up cache get
    analytics_service._get_from_cache = AsyncMock(return_value=cached_data)

    result = await analytics_service.get_tenant_stats(tenant_id, period_days=30)
    assert result == cached_data
    analytics_service._get_from_cache.assert_called_with(cache_key)

    # 2. Test Cache Miss
    analytics_service._get_from_cache = AsyncMock(return_value=None)
    analytics_service._set_cache = AsyncMock()

    result = await analytics_service.get_tenant_stats(tenant_id, period_days=30)
    assert "cached" not in result
    analytics_service._set_cache.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report_json(analytics_service):
    tenant_id = uuid4()
    analytics_service.get_tenant_stats = AsyncMock(return_value={"data": "test"})

    report = await analytics_service.generate_report(tenant_id, format="json")
    assert report == {"data": "test"}


@pytest.mark.asyncio
async def test_generate_report_unsupported(analytics_service):
    tenant_id = uuid4()
    with pytest.raises(ValueError):
        await analytics_service.generate_report(tenant_id, format="xml")


@pytest.mark.asyncio
async def test_get_real_time_metrics(analytics_service):
    tenant_id = uuid4()
    metrics = await analytics_service.get_real_time_metrics(tenant_id)

    assert metrics["tenant_id"] == str(tenant_id)
    assert "requests_per_second" in metrics
    assert "cpu_usage_percent" in metrics


@pytest.mark.asyncio
async def test_internal_helpers_execution(analytics_service):
    # This verifies that the internal methods run without error,
    # even if they just return mock data for now.
    tenant_id = uuid4()

    # Call individual helpers directly or via get_tenant_stats
    # We'll use get_tenant_stats to cover all of them
    analytics_service._get_from_cache = AsyncMock(return_value=None)
    analytics_service._set_cache = AsyncMock()

    stats = await analytics_service.get_tenant_stats(tenant_id)

    # Check a few deep keys to ensure helpers ran
    assert "by_layer" in stats["memories"]
    assert "density" in stats["knowledge_graph"]
    assert "error_rate" in stats["api_usage"]
