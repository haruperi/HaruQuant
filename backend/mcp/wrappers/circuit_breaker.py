"""Circuit breaker with closed/open/half-open states."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from backend.common.logger import logger

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker with closed/open/half-open state machine."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.failure_threshold = max(failure_threshold, 1)
        self.recovery_timeout = max(recovery_timeout, 0.0)
        self.half_open_max_calls = max(half_open_max_calls, 1)

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, with automatic transition from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def execute(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute fn through the circuit breaker."""
        current_state = self.state

        if current_state == CircuitState.OPEN:
            logger.warning("CircuitBreaker: circuit is OPEN, rejecting call")
            raise CircuitBreakerOpenError("Circuit breaker is open")

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                logger.warning(
                    "CircuitBreaker: half-open max calls reached, rejecting"
                )
                raise CircuitBreakerOpenError("Circuit breaker half-open limit reached")
            self._half_open_calls += 1

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info("CircuitBreaker: success in half-open, closing circuit")
            self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None

    def _on_failure(self) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(
                "CircuitBreaker: failure in half-open, opening circuit"
            )
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            logger.warning(
                f"CircuitBreaker: {self._failure_count} failures, opening circuit"
            )
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
