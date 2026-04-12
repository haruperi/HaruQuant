"""Tests for MCP wrapper components."""

from __future__ import annotations

import time

import pytest

from backend.mcp.wrappers import BaseMCPWrapper, CircuitBreaker, RateLimiter, RetryPolicy
from backend.mcp.wrappers.base_wrapper import RateLimitExceededError
from backend.mcp.wrappers.circuit_breaker import CircuitBreakerOpenError, CircuitState


class TestRetryPolicy:
    def test_success_no_retry(self) -> None:
        policy = RetryPolicy(max_retries=3)
        assert policy.execute(lambda: 42) == 42

    def test_retry_on_failure(self) -> None:
        calls = [0]

        def flaky() -> int:
            calls[0] += 1
            if calls[0] < 3:
                raise ValueError("fail")
            return 99

        policy = RetryPolicy(max_retries=3, base_delay=0.001)
        assert policy.execute(flaky) == 99
        assert calls[0] == 3

    def test_exhausted_retries(self) -> None:
        policy = RetryPolicy(max_retries=2, base_delay=0.001)
        with pytest.raises(ValueError):
            policy.execute(lambda: (_ for _ in ()).throw(ValueError("always")))

    def test_non_retryable_exception(self) -> None:
        policy = RetryPolicy(
            max_retries=3, base_delay=0.001,
            retryable_exceptions=(ValueError,),
        )
        with pytest.raises(TypeError):
            policy.execute(lambda: (_ for _ in ()).throw(TypeError("nope")))


class TestCircuitBreaker:
    def test_closed_allows_calls(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.execute(lambda: 1) == 1

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        def fail() -> int:
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            cb.execute(fail)
        with pytest.raises(RuntimeError):
            cb.execute(fail)

        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitBreakerOpenError):
            cb.execute(lambda: 1)

    def test_half_open_recovery(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        def fail() -> int:
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            cb.execute(fail)
        assert cb.state == CircuitState.OPEN

        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        result = cb.execute(lambda: 42)
        assert result == 42
        assert cb.state == CircuitState.CLOSED

    def test_reset(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)

        def fail() -> int:
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            cb.execute(fail)
        cb.reset()
        assert cb.state == CircuitState.CLOSED


class TestRateLimiter:
    def test_acquire_within_capacity(self) -> None:
        rl = RateLimiter(rate=10, capacity=5)
        for _ in range(5):
            assert rl.acquire() is True

    def test_acquire_exceeds_capacity(self) -> None:
        rl = RateLimiter(rate=0, capacity=1)
        assert rl.acquire() is True
        assert rl.acquire() is False

    def test_wait_timeout(self) -> None:
        rl = RateLimiter(rate=0, capacity=1)
        rl.acquire()
        assert rl.wait(timeout=0.01) is False


class TestBaseMCPWrapper:
    def test_call_success(self) -> None:
        wrapper = BaseMCPWrapper()
        assert wrapper.call(lambda: "ok") == "ok"

    def test_call_rate_limit_exceeded(self) -> None:
        rl = RateLimiter(rate=0, capacity=1)
        wrapper = BaseMCPWrapper(rate_limiter=rl)
        wrapper.call(lambda: "first")
        with pytest.raises(RateLimitExceededError):
            wrapper.call(lambda: "second")

    def test_call_circuit_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        retry = RetryPolicy(max_retries=0, base_delay=0.001)
        wrapper = BaseMCPWrapper(
            retry_policy=retry, circuit_breaker=cb,
        )

        with pytest.raises(RuntimeError):
            wrapper.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        with pytest.raises(CircuitBreakerOpenError):
            wrapper.call(lambda: "blocked")

    def test_reset(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        retry = RetryPolicy(max_retries=0, base_delay=0.001)
        wrapper = BaseMCPWrapper(retry_policy=retry, circuit_breaker=cb)

        with pytest.raises(RuntimeError):
            wrapper.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        wrapper.reset()
        assert wrapper.call(lambda: "ok") == "ok"
