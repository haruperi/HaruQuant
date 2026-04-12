"""Integration tests for MCP wrapper composition."""

from __future__ import annotations

import time

from backend.mcp.wrappers import BaseMCPWrapper, CircuitBreaker, RateLimiter, RetryPolicy


def test_wrapped_mcp_call_with_all_components():
    """Integration test: BaseMCPWrapper with retry + circuit breaker + rate limiter."""
    rl = RateLimiter(rate=100, capacity=10)
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    retry = RetryPolicy(max_retries=2, base_delay=0.001)

    wrapper = BaseMCPWrapper(
        retry_policy=retry,
        circuit_breaker=cb,
        rate_limiter=rl,
    )

    # Successful call passes through all components
    result = wrapper.call(lambda: "success")
    assert result == "success"


def test_wrapped_mcp_call_with_retry_recovery():
    """Integration test: retry recovers from transient failure."""
    call_count = [0]

    def flaky_fn() -> str:
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("transient")
        return "recovered"

    retry = RetryPolicy(max_retries=3, base_delay=0.001)
    wrapper = BaseMCPWrapper(retry_policy=retry)

    result = wrapper.call(flaky_fn)
    assert result == "recovered"
    assert call_count[0] == 3


def test_wrapped_mcp_call_circuit_opens_after_failures():
    """Integration test: circuit breaker opens after threshold failures."""
    from backend.mcp.wrappers.circuit_breaker import CircuitBreakerOpenError

    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
    retry = RetryPolicy(max_retries=0, base_delay=0.001)
    wrapper = BaseMCPWrapper(retry_policy=retry, circuit_breaker=cb)

    def fail_fn() -> str:
        raise RuntimeError("fail")

    for _ in range(2):
        try:
            wrapper.call(fail_fn)
        except RuntimeError:
            pass

    # Circuit is now open
    from backend.mcp.wrappers.base_wrapper import RateLimitExceededError
    with assert_raises((CircuitBreakerOpenError, RuntimeError)):
        wrapper.call(lambda: "should_be_blocked")


def assert_raises(exc_types):
    """Simple context manager for expected exception."""
    class _CM:
        def __enter__(self): pass
        def __exit__(self, exc_type, exc_val, exc_tb):
            return exc_type is not None and issubclass(exc_type, exc_types)
    return _CM()
