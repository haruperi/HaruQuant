"""Base MCP wrapper composing retry, circuit breaker, and rate limiter."""

from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar

from services.utils.logger import logger
from backend.mcp.wrappers.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from backend.mcp.wrappers.rate_limiter import RateLimiter
from backend.mcp.wrappers.retry_policy import RetryPolicy

T = TypeVar("T")


class BaseMCPWrapper:
    """Composes RetryPolicy, CircuitBreaker, and RateLimiter for MCP calls."""

    def __init__(
        self,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.rate_limiter = rate_limiter

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute fn through rate limiter, circuit breaker, and retry policy."""
        # 1. Rate limit check
        if self.rate_limiter is not None:
            if not self.rate_limiter.acquire():
                logger.warning("BaseMCPWrapper: rate limit exceeded")
                raise RateLimitExceededError("Rate limit exceeded")

        # 2. Execute through circuit breaker and retry
        def _execute() -> T:
            return self.circuit_breaker.execute(fn, *args, **kwargs)

        return self.retry_policy.execute(_execute)

    async def call_async(
        self, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Async version of call."""
        if self.rate_limiter is not None:
            if not self.rate_limiter.acquire():
                logger.warning("BaseMCPWrapper: rate limit exceeded")
                raise RateLimitExceededError("Rate limit exceeded")

        async def _execute() -> Any:
            return await self.circuit_breaker.execute(fn, *args, **kwargs)

        return await self.retry_policy.execute_async(_execute)

    def reset(self) -> None:
        """Reset all components."""
        self.circuit_breaker.reset()


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    pass
