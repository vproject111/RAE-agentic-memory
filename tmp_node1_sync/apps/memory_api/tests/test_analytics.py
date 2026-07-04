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
async def test_get_tenant_stats_cached(analytics_service):
    tenant_id = uuid4()
    period_days = 30

    # Mock cache hit
    analytics_service._get_from_cache = AsyncMock(return_value={"cached": True})

    stats = await analytics_service.get_tenant_stats(tenant_id, period_days)
    assert stats == {"cached": True}
    analytics_service._get_from_cache.assert_called_once()


@pytest.mark.asyncio
async def test_get_tenant_stats_uncached(analytics_service):
    tenant_id = uuid4()
    period_days = 30

    # Mock cache miss
    analytics_service._get_from_cache = AsyncMock(return_value=None)
    analytics_service._set_cache = AsyncMock()

    # Mock all internal data gathering methods
    analytics_service._get_memory_stats = AsyncMock(return_value={"total": 100})
    analytics_service._get_query_stats = AsyncMock(return_value={"total": 500})
    analytics_service._get_graph_stats = AsyncMock(return_value={"nodes": 50})
    analytics_service._get_reflection_stats = AsyncMock(return_value={"total": 10})
    analytics_service._get_api_usage_stats = AsyncMock(return_value={"requests": 1000})
    analytics_service._get_performance_stats = AsyncMock(return_value={"latency": 50})
    analytics_service._get_cost_stats = AsyncMock(return_value={"cost": 5.0})

    stats = await analytics_service.get_tenant_stats(tenant_id, period_days)

    assert stats["tenant_id"] == str(tenant_id)
    assert stats["memories"]["total"] == 100
    assert stats["queries"]["total"] == 500
    assert stats["knowledge_graph"]["nodes"] == 50

    analytics_service._set_cache.assert_called_once()


@pytest.mark.asyncio
async def test_get_memory_stats(analytics_service):
    tenant_id = uuid4()
    stats = await analytics_service._get_memory_stats(tenant_id, 30)
    assert "total" in stats
    assert "by_layer" in stats


@pytest.mark.asyncio
async def test_get_query_stats(analytics_service):
    tenant_id = uuid4()
    stats = await analytics_service._get_query_stats(tenant_id, 30)
    assert "total_queries" in stats
    assert "avg_latency_ms" in stats


@pytest.mark.asyncio
async def test_get_graph_stats(analytics_service):
    tenant_id = uuid4()

    analytics_service._count_graph_nodes = AsyncMock(return_value=10)
    analytics_service._count_graph_edges = AsyncMock(return_value=20)

    stats = await analytics_service._get_graph_stats(tenant_id)
    assert stats["nodes"] == 10
    assert stats["edges"] == 20
    assert stats["avg_connections_per_node"] == 2.0


@pytest.mark.asyncio
async def test_get_reflection_stats(analytics_service):
    tenant_id = uuid4()
    stats = await analytics_service._get_reflection_stats(tenant_id, 30)
    assert "total_generated" in stats


@pytest.mark.asyncio
async def test_get_api_usage_stats(analytics_service):
    tenant_id = uuid4()
    stats = await analytics_service._get_api_usage_stats(tenant_id, 30)
    assert "total_requests" in stats
    assert "by_endpoint" in stats


@pytest.mark.asyncio
async def test_get_performance_stats(analytics_service):
    tenant_id = uuid4()
    stats = await analytics_service._get_performance_stats(tenant_id, 30)
    assert "avg_response_time_ms" in stats


@pytest.mark.asyncio
async def test_get_cost_stats(analytics_service):
    tenant_id = uuid4()
    stats = await analytics_service._get_cost_stats(tenant_id, 30)
    assert "estimated_llm_cost_usd" in stats


@pytest.mark.asyncio
async def test_calculate_graph_density(analytics_service):
    tenant_id = uuid4()
    # 0 nodes -> 0
    assert await analytics_service._calculate_graph_density(tenant_id, 0, 0) == 0.0
    # 2 nodes, 1 edge -> 1.0
    assert await analytics_service._calculate_graph_density(tenant_id, 2, 1) == 1.0
    # 3 nodes, 3 edges -> 1.0 (complete graph)
    # Max edges = 3*2/2 = 3
    assert await analytics_service._calculate_graph_density(tenant_id, 3, 3) == 1.0
    # 3 nodes, 0 edges -> 0.0
    assert await analytics_service._calculate_graph_density(tenant_id, 3, 0) == 0.0


@pytest.mark.asyncio
async def test_cache_operations(analytics_service):
    # _get_from_cache (mocked redis)
    await analytics_service._get_from_cache("key")
    analytics_service.rae_service.redis_client.get.assert_called_once_with("key")

    # _set_cache
    await analytics_service._set_cache("key", {"a": 1}, 300)
    analytics_service.rae_service.redis_client.set.assert_called_once()

    # In-memory fallback check
    analytics_service.rae_service = None
    await analytics_service._set_cache("key2", {"a": 1}, 300)
    assert analytics_service._cache["key2"] == {"a": 1}
    assert await analytics_service._get_from_cache("key2") == {"a": 1}


@pytest.mark.asyncio
async def test_generate_report(analytics_service):
    tenant_id = uuid4()
    analytics_service.get_tenant_stats = AsyncMock(return_value={"data": 1})

    # JSON
    report = await analytics_service.generate_report(tenant_id, format="json")
    assert report == {"data": 1}

    # CSV
    report = await analytics_service.generate_report(tenant_id, format="csv")
    assert isinstance(report, str)

    # PDF
    report = await analytics_service.generate_report(tenant_id, format="pdf")
    assert isinstance(report, bytes)

    # Invalid
    with pytest.raises(ValueError):
        await analytics_service.generate_report(tenant_id, format="invalid")


@pytest.mark.asyncio
async def test_get_real_time_metrics(analytics_service):
    tenant_id = uuid4()
    metrics = await analytics_service.get_real_time_metrics(tenant_id)
    assert metrics["tenant_id"] == str(tenant_id)
    assert "current_active_requests" in metrics


@pytest.mark.asyncio
async def test_get_usage_alerts(analytics_service):
    tenant_id = uuid4()
    alerts = await analytics_service.get_usage_alerts(tenant_id)
    assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_mock_db_methods(analytics_service):
    # Just to cover the placeholder methods
    tenant_id = uuid4()
    assert await analytics_service._count_memories(tenant_id) == 0
    assert (await analytics_service._count_by_layer(tenant_id))["episodic"] == 0
    assert await analytics_service._calculate_growth_rate(tenant_id, 30) == 0.0
