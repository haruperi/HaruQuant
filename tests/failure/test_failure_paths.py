"""Failure-path tests for timeout, malformed output, stale context, etc. (Playbook §19)."""

from __future__ import annotations

import pytest

from backend_retiring.mcp.wrappers.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from backend_retiring.mcp.wrappers.rate_limiter import RateLimiter
from backend_retiring.mcp.wrappers.retry_policy import RetryPolicy
from backend_retiring.orchestration.context_engineering.eviction import ContextEviction
from backend_retiring.orchestration.context_engineering.validator import ContextValidator


def test_retry_exhaustion():
    policy = RetryPolicy(max_retries=2, base_delay=0.001)
    with pytest.raises(ValueError):
        policy.execute(lambda: (_ for _ in ()).throw(ValueError("always")))


def test_circuit_breaker_opens():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
    with pytest.raises(RuntimeError):
        cb.execute(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    with pytest.raises(CircuitBreakerOpenError):
        cb.execute(lambda: 1)


def test_rate_limiter_blocks():
    rl = RateLimiter(rate=0, capacity=1)
    assert rl.acquire() is True
    assert rl.acquire() is False


def test_stale_context_eviction():
    ev = ContextEviction(ttl_seconds=0.01)
    ev.put("k", "v")
    import time; time.sleep(0.02)
    assert ev.get("k") is None


def test_invalid_context_rejected():
    v = ContextValidator()
    issues = v.validate({})
    assert "context is empty" in issues


def test_timeout_scenario():
    """Simulate timeout by testing circuit breaker recovery."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
    with pytest.raises(RuntimeError):
        cb.execute(lambda: (_ for _ in ()).throw(RuntimeError("timeout")))
    import time; time.sleep(0.02)
    assert cb.state.value == "half_open"
    result = cb.execute(lambda: "recovered")
    assert result == "recovered"
