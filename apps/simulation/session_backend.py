"""Session metadata and lease backend abstractions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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

    def clear_expired_leases(self) -> int: ...


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
        return self._upsert_lease(
            session_id=session_id,
            worker_id=worker_id,
            ttl_seconds=ttl_seconds,
            allow_current_owner=True,
        )

    def renew_lease(
        self,
        session_id: int,
        worker_id: str,
        ttl_seconds: int,
    ) -> bool:
        return self._upsert_lease(
            session_id=session_id,
            worker_id=worker_id,
            ttl_seconds=ttl_seconds,
            allow_current_owner=True,
        )

    def release_lease(self, session_id: int, worker_id: str) -> None:
        conn = sqlite3.connect(self._db_manager.db_path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                UPDATE simulation_sessions
                SET runtime_owner = NULL,
                    lease_expires_at = NULL,
                    last_heartbeat_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                  AND (runtime_owner IS NULL OR runtime_owner = ?)
                """,
                (int(session_id), str(worker_id)),
            )
            conn.commit()
        finally:
            conn.close()

    def clear_expired_leases(self) -> int:
        now_text = self._format_timestamp(datetime.now(UTC))
        conn = sqlite3.connect(self._db_manager.db_path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                UPDATE simulation_sessions
                SET runtime_owner = NULL,
                    lease_expires_at = NULL,
                    last_heartbeat_at = NULL,
                    status = CASE
                        WHEN status = 'running' THEN 'paused'
                        ELSE status
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE lease_expires_at IS NOT NULL
                  AND lease_expires_at <= ?
                """,
                (now_text,),
            )
            conn.commit()
            return int(cursor.rowcount or 0)
        finally:
            conn.close()

    def _upsert_lease(
        self,
        *,
        session_id: int,
        worker_id: str,
        ttl_seconds: int,
        allow_current_owner: bool,
    ) -> bool:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=max(int(ttl_seconds), 1))
        now_text = self._format_timestamp(now)
        expires_text = self._format_timestamp(expires_at)
        params = [
            str(worker_id),
            expires_text,
            now_text,
            int(session_id),
            str(worker_id),
            now_text,
        ]
        owner_clause = "OR runtime_owner = ?" if allow_current_owner else ""
        conn = sqlite3.connect(self._db_manager.db_path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                f"""
                UPDATE simulation_sessions
                SET runtime_owner = ?,
                    lease_expires_at = ?,
                    last_heartbeat_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                  AND (
                        runtime_owner IS NULL
                        {owner_clause}
                        OR lease_expires_at IS NULL
                        OR lease_expires_at <= ?
                  )
                """,
                params,
            )
            conn.commit()
            return int(cursor.rowcount or 0) == 1
        finally:
            conn.close()

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        normalized = value.astimezone(UTC).replace(tzinfo=None)
        return normalized.isoformat()
