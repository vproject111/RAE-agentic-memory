import os
import pytest
import time
from rae_core.llm import CircuitBreaker, CircuitBreakerOpenException, StandaloneRateLimiter, redact_secrets

def test_redact_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-testkey1234567890abcdef")
    
    text = "Sending request with auth sk-proj-testkey1234567890abcdef"
    redacted = redact_secrets(text)
    assert "sk-proj-testkey1234567890abcdef" not in redacted
    assert "[REDACTED]" in redacted or "[REDACTED_API_KEY]" in redacted

def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    
    cb.check_request_allowed()
    
    cb.record_failure()
    cb.check_request_allowed()
    
    cb.record_failure()
    
    with pytest.raises(CircuitBreakerOpenException):
        cb.check_request_allowed()
        
    time.sleep(0.15)
    cb.check_request_allowed()
    assert cb.state == "HALF-OPEN"
    
    cb.record_success()
    assert cb.state == "CLOSED"

def test_rate_limiter():
    limiter = StandaloneRateLimiter(max_requests=2, period=1.0)
    
    assert limiter.allow_request() is True
    assert limiter.allow_request() is True
    assert limiter.allow_request() is False
    
    time.sleep(1.05)
    assert limiter.allow_request() is True
