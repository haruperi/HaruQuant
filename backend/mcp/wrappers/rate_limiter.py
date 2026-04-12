"""Rate limiter with token bucket algorithm."""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int) -> None:
        """
        Args:
            rate: Tokens added per second.
            capacity: Maximum token bucket capacity.
        """
        self.rate = max(rate, 0.0)
        self.capacity = max(capacity, 1)
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait(self, tokens: int = 1, timeout: float = 0.0) -> bool:
        """Wait until tokens are available or timeout.

        Args:
            tokens: Number of tokens to acquire.
            timeout: Max seconds to wait (0 = no wait).
        Returns:
            True if tokens acquired, False if timeout.
        """
        deadline = time.monotonic() + timeout if timeout > 0 else 0
        while True:
            if self.acquire(tokens):
                return True
            if timeout > 0 and time.monotonic() >= deadline:
                return False
            time.sleep(0.01)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.capacity,
            self._tokens + elapsed * self.rate,
        )
        self._last_refill = now

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens
