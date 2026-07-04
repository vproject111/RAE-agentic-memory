"""
Tests for Circuit Breaker Pattern - ISO/IEC 42001 Graceful Degradation
"""

import asyncio

import pytest

from apps.memory_api.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    DegradedModeService,
)

pytestmark = pytest.mark.iso42001


@pytest.fixture(autouse=True)
def mock_logger(mocker):
    """Mock logger to avoid structured logging issues"""
    mocker.patch("apps.memory_api.utils.circuit_breaker.logger")


class TestCircuitBreaker:
    """Tests for CircuitBreaker class"""

    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        """Circuit breaker should start in CLOSED state"""
        cb = CircuitBreaker(name="test_breaker")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Successful calls should go through and update metrics"""
        cb = CircuitBreaker(name="test_breaker")

        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.total_successes == 1
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_failed_call(self):
        """Failed calls should increment failure count"""
        cb = CircuitBreaker(name="test_breaker", failure_threshold=3)

        async def failing_func():
            raise Exception("Test failure")

        with pytest.raises(Exception, match="Test failure"):
            await cb.call(failing_func)

        assert cb.failure_count == 1
        assert cb.total_failures == 1
        assert cb.state == CircuitState.CLOSED  # Still closed (below threshold)

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        """Circuit should open after exceeding failure threshold"""
        cb = CircuitBreaker(name="test_breaker", failure_threshold=3)

        async def failing_func():
            raise Exception("Test failure")

        # Trigger 3 failures to reach threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3
        assert cb.opened_at is not None

    @pytest.mark.asyncio
    async def test_fails_fast_when_open(self):
        """Circuit breaker should fail fast when open"""
        cb = CircuitBreaker(name="test_breaker", failure_threshold=2)

        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Next call should fail fast without executing function
        async def should_not_execute():
            pytest.fail("Function should not be executed when circuit is open")

        with pytest.raises(CircuitBreakerError, match="OPEN"):
            await cb.call(should_not_execute)

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery timeout"""
        cb = CircuitBreaker(
            name="test_breaker",
            failure_threshold=2,
            recovery_timeout=0,
            success_threshold=1,  # Immediate, 1 success to close
        )

        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout (immediate in this case)
        await asyncio.sleep(0.1)

        # Next call should transition to HALF_OPEN and then CLOSED after 1 success
        async def success_func():
            return "recovered"

        result = await cb.call(success_func)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED  # Closed after 1 successful recovery

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Successful calls in HALF_OPEN should close circuit after success_threshold"""
        cb = CircuitBreaker(
            name="test_breaker",
            failure_threshold=2,
            recovery_timeout=0,
            success_threshold=2,
        )

        async def failing_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.1)

        # First successful call transitions to HALF_OPEN
        await cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.success_count == 1

        # Second successful call should close circuit
        await cb.call(success_func)
        assert cb.state == CircuitState.CLOSED
        assert cb.success_count == 0  # Reset after closing

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Failure in HALF_OPEN should immediately reopen circuit"""
        cb = CircuitBreaker(
            name="test_breaker", failure_threshold=2, recovery_timeout=0
        )

        async def failing_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.1)

        # Success transitions to HALF_OPEN
        await cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN

        # Failure should immediately reopen
        with pytest.raises(Exception):
            await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_get_state_returns_metrics(self):
        """get_state should return comprehensive state information"""
        cb = CircuitBreaker(name="test_breaker")

        async def success_func():
            return "success"

        await cb.call(success_func)
        await cb.call(success_func)

        state = cb.get_state()
        assert state["name"] == "test_breaker"
        assert state["state"] == CircuitState.CLOSED
        assert state["metrics"]["total_calls"] == 2
        assert state["metrics"]["total_successes"] == 2
        assert state["metrics"]["total_failures"] == 0
        assert state["metrics"]["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_reset_clears_all_state(self):
        """reset should clear all state and return to CLOSED"""
        cb = CircuitBreaker(name="test_breaker", failure_threshold=2)

        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 2

        # Reset
        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None
        assert cb.opened_at is None

    @pytest.mark.asyncio
    async def test_custom_exception_type(self):
        """Circuit breaker should only catch specified exception type"""
        cb = CircuitBreaker(
            name="test_breaker", failure_threshold=2, expected_exception=ValueError
        )

        async def value_error_func():
            raise ValueError("Value error")

        async def runtime_error_func():
            raise RuntimeError("Runtime error")

        # ValueError should be caught and counted
        with pytest.raises(ValueError):
            await cb.call(value_error_func)

        assert cb.failure_count == 1

        # RuntimeError should not be caught (will propagate)
        with pytest.raises(RuntimeError):
            await cb.call(runtime_error_func)

        # Failure count should not increase for RuntimeError
        assert cb.failure_count == 1

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self):
        """Success rate should be calculated correctly"""
        cb = CircuitBreaker(name="test_breaker", failure_threshold=10)

        async def success_func():
            return "success"

        async def failing_func():
            raise Exception("failure")

        # 7 successes
        for _ in range(7):
            await cb.call(success_func)

        # 3 failures
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        state = cb.get_state()
        assert state["metrics"]["total_calls"] == 10
        assert state["metrics"]["total_successes"] == 7
        assert state["metrics"]["total_failures"] == 3
        assert state["metrics"]["success_rate"] == 0.7


class TestDegradedModeService:
    """Tests for DegradedModeService class"""

    def test_initial_state_normal(self):
        """Service should start in normal (non-degraded) mode"""
        service = DegradedModeService()
        assert service.degraded_mode is False
        assert service.is_degraded() is False

    def test_enter_degraded_mode(self):
        """Should be able to enter degraded mode"""
        service = DegradedModeService()
        service.enter_degraded_mode(reason="Database connection lost")

        assert service.degraded_mode is True
        assert service.is_degraded() is True
        assert service.reason == "Database connection lost"
        assert service.entered_at is not None

    def test_exit_degraded_mode(self):
        """Should be able to exit degraded mode"""
        service = DegradedModeService()
        service.enter_degraded_mode(reason="Test reason")
        assert service.is_degraded() is True

        service.exit_degraded_mode()
        assert service.degraded_mode is False
        assert service.is_degraded() is False
        assert service.reason is None
        assert service.entered_at is None

    def test_get_status_degraded(self):
        """get_status should return degraded mode information"""
        service = DegradedModeService()
        service.enter_degraded_mode(reason="Circuit breaker open")

        status = service.get_status()
        assert status["degraded"] is True
        assert status["reason"] == "Circuit breaker open"
        assert status["entered_at"] is not None
        assert status["duration_seconds"] >= 0

    def test_get_status_normal(self):
        """get_status should return normal mode information"""
        service = DegradedModeService()
        status = service.get_status()

        assert status["degraded"] is False
        assert status["reason"] is None
        assert status["entered_at"] is None
        assert status["duration_seconds"] == 0

    def test_duration_calculation(self):
        """Duration should be calculated correctly"""
        service = DegradedModeService()
        service.enter_degraded_mode(reason="Test")

        import time

        time.sleep(0.1)  # Wait 100ms

        status = service.get_status()
        assert status["duration_seconds"] >= 0.1

    def test_exit_when_not_degraded(self):
        """Exiting when not degraded should be safe (no-op)"""
        service = DegradedModeService()
        service.exit_degraded_mode()  # Should not raise exception
        assert service.is_degraded() is False


class TestGlobalCircuitBreakers:
    """Tests for global circuit breaker instances"""

    def test_global_breakers_exist(self):
        """Global circuit breakers should be defined"""
        from apps.memory_api.utils.circuit_breaker import rae_circuit_breakers

        assert "database" in rae_circuit_breakers
        assert "vector_store" in rae_circuit_breakers
        assert "llm_service" in rae_circuit_breakers

    def test_database_breaker_config(self):
        """Database circuit breaker should have correct configuration"""
        from apps.memory_api.utils.circuit_breaker import rae_circuit_breakers

        db_breaker = rae_circuit_breakers["database"]
        assert db_breaker.name == "rae_database"
        assert db_breaker.failure_threshold == 5
        assert db_breaker.recovery_timeout == 30

    def test_vector_store_breaker_config(self):
        """Vector store circuit breaker should have correct configuration"""
        from apps.memory_api.utils.circuit_breaker import rae_circuit_breakers

        vs_breaker = rae_circuit_breakers["vector_store"]
        assert vs_breaker.name == "rae_vector_store"
        assert vs_breaker.failure_threshold == 3
        assert vs_breaker.recovery_timeout == 60

    def test_llm_service_breaker_config(self):
        """LLM service circuit breaker should have correct configuration"""
        from apps.memory_api.utils.circuit_breaker import rae_circuit_breakers

        llm_breaker = rae_circuit_breakers["llm_service"]
        assert llm_breaker.name == "rae_llm_service"
        assert llm_breaker.failure_threshold == 5
        assert llm_breaker.recovery_timeout == 120

    def test_global_degraded_mode_service(self):
        """Global degraded mode service should exist"""
        from apps.memory_api.utils.circuit_breaker import degraded_mode_service

        assert isinstance(degraded_mode_service, DegradedModeService)
        assert degraded_mode_service.is_degraded() is False


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker pattern"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete circuit breaker lifecycle"""
        cb = CircuitBreaker(
            name="integration_test",
            failure_threshold=3,
            recovery_timeout=1,  # 1 second to test fail-fast behavior
            success_threshold=2,
        )

        async def unstable_func(should_fail=False):
            if should_fail:
                raise Exception("Service unavailable")
            return "success"

        # Phase 1: CLOSED state - successful calls
        for _ in range(5):
            result = await cb.call(unstable_func, should_fail=False)
            assert result == "success"
        assert cb.state == CircuitState.CLOSED

        # Phase 2: CLOSED state - failures accumulate
        for i in range(3):
            with pytest.raises(Exception):
                await cb.call(unstable_func, should_fail=True)
            if i < 2:
                assert cb.state == CircuitState.CLOSED
            else:
                assert cb.state == CircuitState.OPEN

        # Phase 3: OPEN state - fail fast
        with pytest.raises(CircuitBreakerError):
            await cb.call(unstable_func, should_fail=False)

        # Phase 4: Wait for recovery timeout
        await asyncio.sleep(1.1)  # Wait longer than recovery_timeout

        # Phase 5: HALF_OPEN state - test recovery
        await cb.call(unstable_func, should_fail=False)
        assert cb.state == CircuitState.HALF_OPEN

        # Phase 6: HALF_OPEN -> CLOSED after success threshold
        await cb.call(unstable_func, should_fail=False)
        assert cb.state == CircuitState.CLOSED

        # Verify metrics
        state = cb.get_state()
        assert state["metrics"]["total_calls"] == 11  # Includes fail-fast call
        assert state["metrics"]["total_successes"] == 7
        assert state["metrics"]["total_failures"] == 3
