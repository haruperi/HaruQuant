"""Rate limiting and concurrency controls for HaruQuant AI chat."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import threading
import time
from typing import Dict, List

from services.utils.logger import logger


@dataclass
class UserRateState:
    concurrent_requests: int = 0
    request_timestamps: List[float] = None

    def __post_init__(self):
        if self.request_timestamps is None:
            self.request_timestamps = []


class ChatRateLimiter:
    """Simple in-memory rate limiter and concurrency controller."""

    def __init__(
        self,
        *,
        max_concurrent: int = 2,
        max_per_minute: int = 10,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.max_per_minute = max_per_minute
        self._states: Dict[str, UserRateState] = {}
        self._lock = threading.Lock()

    def acquire(self, user_id: str | int, wait: bool = False, timeout: float = 10.0) -> bool:
        """
        Attempt to acquire a request slot for a user.
        If wait=True, blocks until a slot is available or timeout.
        Returns True if allowed, False if rate-limited or timeout.
        """
        user_key = str(user_id)
        start_time = datetime.now(timezone.utc).timestamp()
        
        while True:
            now = datetime.now(timezone.utc).timestamp()
            with self._lock:
                state = self._states.setdefault(user_key, UserRateState())
                
                # Clean up old timestamps
                state.request_timestamps = [
                    ts for ts in state.request_timestamps 
                    if now - ts < 60
                ]
                
                # Check concurrency and rate
                allowed = (
                    state.concurrent_requests < self.max_concurrent and
                    len(state.request_timestamps) < self.max_per_minute
                )
                
                if allowed:
                    state.concurrent_requests += 1
                    state.request_timestamps.append(now)
                    return True
            
            if not wait or (now - start_time) > timeout:
                return False
            
            # Wait a bit before retrying
            time.sleep(0.5)

    def release(self, user_id: str | int) -> None:
        """Release a concurrency slot for a user."""
        user_key = str(user_id)
        with self._lock:
            state = self._states.get(user_key)
            if state and state.concurrent_requests > 0:
                state.concurrent_requests -= 1
