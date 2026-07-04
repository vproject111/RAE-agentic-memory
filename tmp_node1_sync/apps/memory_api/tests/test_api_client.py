"""
Tests for API Client - Resilience Patterns

Tests cover:
- Retry logic with exponential backoff
- Circuit breaker (CLOSED, OPEN, HALF_OPEN)
- Response caching
- Error classification
- Timeout handling
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from apps.memory_api.clients.rae_client import (
    CircuitBreaker,
    CircuitState,
    ErrorCategory,
    RAEClient,
    RAEClientError,
    ResponseCache,
    classify_error,
)


@pytest.fixture
def rae_client():
    return RAEClient(
        base_url="http://localhost:8000",
        api_key="test-key",
        tenant_id="test-tenant",
        project_id="test-project",
        max_retries=3,
        enable_circuit_breaker=True,
        enable_cache=True,
    )


@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(failure_threshold=3, success_threshold=2, timeout_seconds=30)


@pytest.fixture
def response_cache():
    return ResponseCache(default_ttl_seconds=60)


# Error Classification Tests
def test_classify_network_error():
    """Test network error classification"""
    error = httpx.NetworkError("Connection refused")
    category = classify_error(error)
    assert category == ErrorCategory.NETWORK


def test_classify_timeout_error():
    """Test timeout error classification"""
    error = httpx.TimeoutException("Request timeout")
    category = classify_error(error)
    assert category == ErrorCategory.TIMEOUT


def test_classify_rate_limit():
    """Test rate limit classification"""
    category = classify_error(Exception(), status_code=429)
    assert category == ErrorCategory.RATE_LIMIT


def test_classify_authentication_error():
    """Test authentication error classification"""
    category = classify_error(Exception(), status_code=401)
    assert category == ErrorCategory.AUTHENTICATION


# Circuit Breaker Tests
@pytest.mark.asyncio
async def test_circuit_breaker_closed_success(circuit_breaker):
    """Test circuit breaker in CLOSED state with success"""

    async def success_func():
        return "success"

    result = await circuit_breaker.call(success_func)
    assert result == "success"
    assert circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures(circuit_breaker):
    """Test circuit breaker opens after threshold failures"""

    async def failing_func():
        raise Exception("Service error")

    # Trigger failures up to threshold
    for i in range(circuit_breaker.failure_threshold):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

    # Circuit should now be OPEN
    assert circuit_breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open(circuit_breaker):
    """Test circuit breaker rejects calls when OPEN"""
    # Force circuit to OPEN state
    circuit_breaker.state = CircuitState.OPEN
    circuit_breaker.last_failure_time = datetime.now(timezone.utc)

    async def test_func():
        return "should not execute"

    with pytest.raises(RAEClientError, match="Circuit breaker is OPEN"):
        await circuit_breaker.call(test_func)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery(circuit_breaker):
    """Test circuit breaker transitions to HALF_OPEN and recovers"""
    # Force circuit to OPEN state but past timeout
    circuit_breaker.state = CircuitState.OPEN
    circuit_breaker.last_failure_time = datetime.now(timezone.utc) - timedelta(
        seconds=35
    )

    async def success_func():
        return "success"

    # First call should transition to HALF_OPEN
    result = await circuit_breaker.call(success_func)
    assert result == "success"
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    # After enough successes, should close
    for _ in range(circuit_breaker.success_threshold - 1):
        await circuit_breaker.call(success_func)

    assert circuit_breaker.state == CircuitState.CLOSED


# Response Cache Tests
def test_cache_set_and_get(response_cache):
    """Test caching response"""
    response = {"data": "test"}

    response_cache.set("GET", "/test", response)
    cached = response_cache.get("GET", "/test")

    assert cached == response


def test_cache_miss(response_cache):
    """Test cache miss"""
    cached = response_cache.get("GET", "/nonexistent")
    assert cached is None


def test_cache_expiration(response_cache):
    """Test cache expiration"""
    response = {"data": "test"}

    # Set with very short TTL (1 second)
    response_cache.set("GET", "/test", response, ttl_seconds=1)

    # Wait longer than TTL and try to get
    import time

    time.sleep(1.2)

    cached = response_cache.get("GET", "/test")
    assert cached is None


def test_cache_invalidation(response_cache):
    """Test cache invalidation"""
    response = {"data": "test"}

    response_cache.set("GET", "/test", response)
    response_cache.invalidate("GET", "/test")

    cached = response_cache.get("GET", "/test")
    assert cached is None


def test_cache_clear(response_cache):
    """Test clearing entire cache"""
    response_cache.set("GET", "/test1", {"data": "1"})
    response_cache.set("GET", "/test2", {"data": "2"})

    response_cache.clear()

    assert response_cache.get("GET", "/test1") is None
    assert response_cache.get("GET", "/test2") is None


# Retry Logic Tests
@pytest.mark.asyncio
async def test_retry_on_network_error(rae_client):
    """Test retry on network error"""
    mock_response = Mock()
    mock_response.json.return_value = {"success": True}
    mock_response.raise_for_status = Mock()

    # Fail twice, then succeed
    rae_client.client.request = AsyncMock(
        side_effect=[
            httpx.NetworkError("Connection failed"),
            httpx.NetworkError("Connection failed"),
            mock_response,
        ]
    )

    result = await rae_client.request("GET", "/test")

    assert result == {"success": True}
    assert rae_client.client.request.call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted(rae_client):
    """Test all retries exhausted"""
    rae_client.client.request = AsyncMock(
        side_effect=httpx.NetworkError("Connection failed")
    )

    with pytest.raises(RAEClientError):
        await rae_client.request("GET", "/test")

    # Should have tried max_retries + 1 times
    assert rae_client.client.request.call_count == rae_client.max_retries + 1


@pytest.mark.asyncio
async def test_no_retry_on_client_error(rae_client):
    """Test no retry on client errors (4xx)"""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad request"

    error = httpx.HTTPStatusError("Bad request", request=Mock(), response=mock_response)
    rae_client.client.request = AsyncMock(side_effect=error)

    with pytest.raises(RAEClientError):
        await rae_client.request("GET", "/test")

    # Should only try once (no retry for client errors)
    assert rae_client.client.request.call_count == 1


# Exponential Backoff Tests
@pytest.mark.asyncio
async def test_exponential_backoff():
    """Test exponential backoff calculation"""
    initial_backoff = 100
    multiplier = 2.0
    max_backoff = 10000

    backoff = initial_backoff
    for i in range(5):
        assert backoff <= max_backoff
        backoff = min(int(backoff * multiplier), max_backoff)


# Request Tests
@pytest.mark.asyncio
async def test_get_request(rae_client):
    """Test GET request"""
    mock_response = Mock()
    mock_response.json.return_value = {"data": "test"}
    mock_response.raise_for_status = Mock()

    rae_client.client.request = AsyncMock(return_value=mock_response)

    result = await rae_client.get("/test")

    assert result == {"data": "test"}
    rae_client.client.request.assert_called_once()


@pytest.mark.asyncio
async def test_post_request(rae_client):
    """Test POST request"""
    mock_response = Mock()
    mock_response.json.return_value = {"created": True}
    mock_response.raise_for_status = Mock()

    rae_client.client.request = AsyncMock(return_value=mock_response)

    result = await rae_client.post("/test", json_data={"name": "test"})

    assert result == {"created": True}


# Statistics Tests
def test_client_statistics(rae_client):
    """Test client statistics tracking"""
    rae_client.stats["total_requests"] = 100
    rae_client.stats["successful_requests"] = 95
    rae_client.stats["failed_requests"] = 5
    rae_client.stats["cache_hits"] = 30
    rae_client.stats["cache_misses"] = 70

    stats = rae_client.get_stats()

    assert stats["total_requests"] == 100
    assert stats["success_rate"] == 0.95
    assert stats["cache_hit_rate"] == 0.3


def test_reset_statistics(rae_client):
    """Test statistics reset"""
    rae_client.stats["total_requests"] = 100

    rae_client.reset_stats()

    assert rae_client.stats["total_requests"] == 0
