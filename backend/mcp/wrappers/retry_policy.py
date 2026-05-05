"""Retry policy with exponential backoff and jitter."""

from __future__ import annotations

import random
import time
from typing import Any, Callable, Optional, TypeVar

from services.utils.logger import logger

T = TypeVar("T")


class RetryPolicy:
    """Retry with exponential backoff, configurable max retries, and jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self.max_retries = max(max_retries, 0)
        self.base_delay = max(base_delay, 0.0)
        self.max_delay = max(max_delay, 0.0)
        self.exponential_base = max(exponential_base, 1.0)
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def execute(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute fn with retry logic."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except self.retryable_exceptions as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    logger.warning(
                        f"RetryPolicy: all {self.max_retries + 1} attempts failed"
                    )
                    raise
                delay = self._compute_delay(attempt)
                logger.info(
                    f"RetryPolicy: attempt {attempt + 1}/{self.max_retries + 1} "
                    f"failed ({exc}), retrying in {delay:.2f}s"
                )
                time.sleep(delay)
        raise last_exc  # pragma: no cover

    async def execute_async(
        self, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute async fn with retry logic."""
        import asyncio

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except self.retryable_exceptions as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    logger.warning(
                        f"RetryPolicy: all {self.max_retries + 1} attempts failed"
                    )
                    raise
                delay = self._compute_delay(attempt)
                logger.info(
                    f"RetryPolicy: attempt {attempt + 1}/{self.max_retries + 1} "
                    f"failed ({exc}), retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)
        raise last_exc  # pragma: no cover

    def _compute_delay(self, attempt: int) -> float:
        """Compute delay with exponential backoff and optional jitter."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return min(delay, self.max_delay)
