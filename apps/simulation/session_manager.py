"""Thread-safe in-memory simulator session store."""

from __future__ import annotations

from threading import RLock
from typing import Generic, Optional, TypeVar

SessionT = TypeVar("SessionT")


class SimulatorSessionManager(Generic[SessionT]):
    """Own in-process simulator sessions behind a small locked API."""

    def __init__(self) -> None:
        self._sessions: dict[int, SessionT] = {}
        self._lock = RLock()

    def get(self, session_id: int) -> Optional[SessionT]:
        with self._lock:
            return self._sessions.get(int(session_id))

    def put(self, session_id: int, session: SessionT) -> None:
        with self._lock:
            self._sessions[int(session_id)] = session

    def remove(self, session_id: int) -> Optional[SessionT]:
        with self._lock:
            return self._sessions.pop(int(session_id), None)
