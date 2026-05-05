"""Coordinator for simulator session metadata, lease ownership, and runtimes."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Generic, Optional, TypeVar

from fastapi import HTTPException

from .session_backend import SessionMetadata, SessionRuntimeStore
from .session_manager import SimulatorSessionManager

SessionT = TypeVar("SessionT")


class SessionCoordinator(Generic[SessionT]):
    """Own active runtime lookup behind DB-backed ownership metadata."""

    def __init__(
        self,
        *,
        store: SessionRuntimeStore,
        runtimes: SimulatorSessionManager[SessionT],
        worker_id: Optional[str] = None,
        lease_ttl_seconds: int = 30,
    ) -> None:
        self._store = store
        self._runtimes = runtimes
        self.worker_id = worker_id or f"sim-worker-{os.getpid()}"
        self.lease_ttl_seconds = max(int(lease_ttl_seconds), 1)

    def get_metadata(self, session_id: int) -> Optional[SessionMetadata]:
        return self._store.get_metadata(int(session_id))

    def get_owned_metadata(self, session_id: int, user_id: int) -> SessionMetadata:
        metadata = self.get_metadata(session_id)
        if metadata is None or metadata.user_id != int(user_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return metadata

    def attach_runtime(self, session_id: int, runtime: SessionT) -> None:
        if not self._store.acquire_lease(
            int(session_id),
            self.worker_id,
            self.lease_ttl_seconds,
        ):
            raise HTTPException(
                status_code=409,
                detail="Session is active on another worker",
            )
        try:
            self._runtimes.put(int(session_id), runtime)
        except Exception:
            self._store.release_lease(int(session_id), self.worker_id)
            raise

    def get_runtime(self, session_id: int, *, renew: bool = True) -> Optional[SessionT]:
        runtime = self._runtimes.get(int(session_id))
        if runtime is None:
            return None
        metadata = self.get_metadata(session_id)
        if metadata is None:
            self._runtimes.remove(int(session_id))
            return None
        if metadata.runtime_owner and metadata.runtime_owner != self.worker_id:
            self._runtimes.remove(int(session_id))
            return None
        if renew and not self._store.renew_lease(
            int(session_id),
            self.worker_id,
            self.lease_ttl_seconds,
        ):
            self._runtimes.remove(int(session_id))
            return None
        return runtime

    def require_runtime(self, session_id: int) -> SessionT:
        runtime = self.get_runtime(int(session_id), renew=True)
        if runtime is None:
            raise HTTPException(status_code=400, detail="Session is not running")
        return runtime

    def release_runtime(self, session_id: int) -> Optional[SessionT]:
        runtime = self._runtimes.remove(int(session_id))
        self._store.release_lease(int(session_id), self.worker_id)
        return runtime

    def renew_lease(self, session_id: int) -> bool:
        return self._store.renew_lease(
            int(session_id),
            self.worker_id,
            self.lease_ttl_seconds,
        )

    def update_metadata(self, session_id: int, patch: dict[str, object]) -> None:
        self._store.update_metadata(int(session_id), patch)

    def is_owned_by_me(self, session_id: int) -> bool:
        metadata = self.get_metadata(session_id)
        if metadata is None:
            return False
        return metadata.runtime_owner == self.worker_id and not self.is_lease_expired(
            session_id
        )

    def is_lease_expired(self, session_id: int) -> bool:
        metadata = self.get_metadata(session_id)
        if metadata is None or metadata.lease_expires_at is None:
            return True
        expires_at = metadata.lease_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC)

    def get_runtime_owner(self, session_id: int) -> Optional[str]:
        metadata = self.get_metadata(session_id)
        if metadata is None:
            return None
        return metadata.runtime_owner

    def clear_expired_leases(self) -> int:
        return self._store.clear_expired_leases()
