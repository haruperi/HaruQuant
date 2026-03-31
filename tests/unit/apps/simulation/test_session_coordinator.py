from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from apps.simulation.session_backend import SessionMetadata
from apps.simulation.session_coordinator import SessionCoordinator
from apps.simulation.session_manager import SimulatorSessionManager


@dataclass
class DummyRuntime:
    name: str


class DummyStore:
    def __init__(self) -> None:
        self.metadata: dict[int, SessionMetadata] = {
            42: SessionMetadata(
                session_id=42,
                user_id=7,
                status="running",
                config={},
                current_bar_index=0,
                total_bars=None,
                runtime_owner=None,
                lease_expires_at=None,
                last_heartbeat_at=None,
                raw={"session_id": 42, "user_id": 7, "config": {}, "status": "running"},
            )
        }

    def get_metadata(self, session_id: int):
        return self.metadata.get(int(session_id))

    def create_metadata(self, metadata: SessionMetadata) -> None:
        self.metadata[int(metadata.session_id)] = metadata

    def update_metadata(self, session_id: int, patch: dict[str, object]) -> None:
        current = self.metadata[int(session_id)]
        raw = current.as_record()
        raw.update(patch)
        self.metadata[int(session_id)] = SessionMetadata.from_record(raw)

    def acquire_lease(self, session_id: int, worker_id: str, ttl_seconds: int) -> bool:
        current = self.metadata[int(session_id)]
        now = datetime.now(UTC)
        if (
            current.runtime_owner
            and current.runtime_owner != worker_id
            and current.lease_expires_at
            and current.lease_expires_at > now
        ):
            return False
        self.update_metadata(
            session_id,
            {
                "runtime_owner": worker_id,
                "lease_expires_at": now + timedelta(seconds=ttl_seconds),
                "last_heartbeat_at": now,
            },
        )
        return True

    def renew_lease(self, session_id: int, worker_id: str, ttl_seconds: int) -> bool:
        return self.acquire_lease(session_id, worker_id, ttl_seconds)

    def release_lease(self, session_id: int, worker_id: str) -> None:
        current = self.metadata[int(session_id)]
        if current.runtime_owner and current.runtime_owner != worker_id:
            return
        self.update_metadata(
            session_id,
            {
                "runtime_owner": None,
                "lease_expires_at": None,
            },
        )


def test_session_coordinator_attaches_gets_and_releases_runtime():
    store = DummyStore()
    runtimes = SimulatorSessionManager[DummyRuntime]()
    coordinator = SessionCoordinator(
        store=store,
        runtimes=runtimes,
        worker_id="worker-a",
        lease_ttl_seconds=15,
    )
    runtime = DummyRuntime(name="demo")

    coordinator.attach_runtime(42, runtime)

    assert coordinator.get_runtime(42) is runtime
    assert store.get_metadata(42).runtime_owner == "worker-a"

    removed = coordinator.release_runtime(42)

    assert removed is runtime
    assert coordinator.get_runtime(42) is None
    assert store.get_metadata(42).runtime_owner is None


def test_session_coordinator_rejects_conflicting_worker_lease():
    store = DummyStore()
    store.acquire_lease(42, "worker-b", 15)
    coordinator = SessionCoordinator(
        store=store,
        runtimes=SimulatorSessionManager[DummyRuntime](),
        worker_id="worker-a",
        lease_ttl_seconds=15,
    )

    with pytest.raises(HTTPException) as exc:
        coordinator.attach_runtime(42, DummyRuntime(name="demo"))

    assert exc.value.status_code == 409
    assert exc.value.detail == "Session is active on another worker"


def test_session_coordinator_reports_owner_and_expiry():
    store = DummyStore()
    coordinator = SessionCoordinator(
        store=store,
        runtimes=SimulatorSessionManager[DummyRuntime](),
        worker_id="worker-a",
        lease_ttl_seconds=15,
    )

    assert coordinator.get_runtime_owner(42) is None
    assert coordinator.is_lease_expired(42) is True

    store.acquire_lease(42, "worker-a", 15)

    assert coordinator.get_runtime_owner(42) == "worker-a"
    assert coordinator.is_owned_by_me(42) is True
    assert coordinator.is_lease_expired(42) is False
