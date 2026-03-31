"""Session metadata and lease backend abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, Protocol


@dataclass(frozen=True)
class SessionMetadata:
    """Persistent simulator session identity and ownership metadata."""

    session_id: int
    user_id: int
    status: str
    config: dict[str, Any]
    current_bar_index: int
    total_bars: Optional[int]
    runtime_owner: Optional[str]
    lease_expires_at: Optional[datetime]
    last_heartbeat_at: Optional[datetime]
    raw: dict[str, Any]

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SessionMetadata":
        return cls(
            session_id=int(record["session_id"]),
            user_id=int(record["user_id"]),
            status=str(record.get("status") or ""),
            config=dict(record.get("config") or {}),
            current_bar_index=int(record.get("current_bar_index") or 0),
            total_bars=(
                int(record["total_bars"])
                if record.get("total_bars") is not None
                else None
            ),
            runtime_owner=(
                str(record.get("runtime_owner"))
                if record.get("runtime_owner")
                else None
            ),
            lease_expires_at=_parse_optional_datetime(record.get("lease_expires_at")),
            last_heartbeat_at=_parse_optional_datetime(record.get("last_heartbeat_at")),
            raw=dict(record),
        )

    def as_record(self) -> dict[str, Any]:
        return dict(self.raw)


def _parse_optional_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


class SessionRuntimeStore(Protocol):
    """Backend abstraction for session metadata and active-runtime leases."""

    def get_metadata(self, session_id: int) -> Optional[SessionMetadata]: ...

    def create_metadata(self, metadata: SessionMetadata) -> None: ...

    def update_metadata(self, session_id: int, patch: dict[str, Any]) -> None: ...

    def acquire_lease(
        self,
        session_id: int,
        worker_id: str,
        ttl_seconds: int,
    ) -> bool: ...

    def renew_lease(
        self,
        session_id: int,
        worker_id: str,
        ttl_seconds: int,
    ) -> bool: ...

    def release_lease(self, session_id: int, worker_id: str) -> None: ...


class SQLiteSessionRuntimeStore:
    """SQLite-backed metadata and lease manager for simulator sessions."""

    def __init__(self, db_manager: Any) -> None:
        self._db_manager = db_manager

    def get_metadata(self, session_id: int) -> Optional[SessionMetadata]:
        record = self._db_manager.get_simulation_session(int(session_id))
        if not record:
            return None
        return SessionMetadata.from_record(record)

    def create_metadata(self, metadata: SessionMetadata) -> None:
        patch = {
            "status": metadata.status,
            "current_bar_index": metadata.current_bar_index,
            "total_bars": metadata.total_bars,
            "config": metadata.config,
            "runtime_owner": metadata.runtime_owner,
            "lease_expires_at": metadata.lease_expires_at,
            "last_heartbeat_at": metadata.last_heartbeat_at,
        }
        self.update_metadata(metadata.session_id, patch)

    def update_metadata(self, session_id: int, patch: dict[str, Any]) -> None:
        if not patch:
            return
        self._db_manager.update_simulation_session(int(session_id), **patch)

    def acquire_lease(
        self,
        session_id: int,
        worker_id: str,
        ttl_seconds: int,
    ) -> bool:
        metadata = self.get_metadata(session_id)
        if metadata is None:
            return False
        now = datetime.utcnow()
        if (
            metadata.runtime_owner
            and metadata.runtime_owner != worker_id
            and metadata.lease_expires_at is not None
            and metadata.lease_expires_at > now
        ):
            return False
        return self.renew_lease(session_id, worker_id, ttl_seconds)

    def renew_lease(
        self,
        session_id: int,
        worker_id: str,
        ttl_seconds: int,
    ) -> bool:
        metadata = self.get_metadata(session_id)
        if metadata is None:
            return False
        now = datetime.utcnow()
        if (
            metadata.runtime_owner
            and metadata.runtime_owner != worker_id
            and metadata.lease_expires_at is not None
            and metadata.lease_expires_at > now
        ):
            return False
        expires_at = now + timedelta(seconds=max(int(ttl_seconds), 1))
        self.update_metadata(
            session_id,
            {
                "runtime_owner": worker_id,
                "lease_expires_at": expires_at,
                "last_heartbeat_at": now,
            },
        )
        return True

    def release_lease(self, session_id: int, worker_id: str) -> None:
        metadata = self.get_metadata(session_id)
        if metadata is None:
            return
        if metadata.runtime_owner and metadata.runtime_owner != worker_id:
            return
        self.update_metadata(
            session_id,
            {
                "runtime_owner": None,
                "lease_expires_at": None,
            },
        )
