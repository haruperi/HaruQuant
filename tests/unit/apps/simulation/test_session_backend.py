from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from services.simulation.session_backend import SQLiteSessionRuntimeStore
from backend.data.database.sqlite.database_operations import DatabaseManager


def test_sqlite_session_runtime_store_lease_lifecycle():
    tmp_dir = Path("build/tmp/test_session_backend") / str(uuid4())
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        db = DatabaseManager(db_path=str(tmp_dir / "sim.db"))
        assert db.initialize_database() is True
        session_id = db.create_simulation_session(
            user_id=7,
            config={"symbol": "EURUSD", "timeframe": "M1"},
        )
        store = SQLiteSessionRuntimeStore(db)

        assert store.acquire_lease(session_id, "worker-a", 30) is True
        metadata = store.get_metadata(session_id)
        assert metadata is not None
        assert metadata.runtime_owner == "worker-a"
        assert metadata.last_heartbeat_at is not None

        assert store.acquire_lease(session_id, "worker-b", 30) is False

        store.release_lease(session_id, "worker-a")
        metadata = store.get_metadata(session_id)
        assert metadata is not None
        assert metadata.runtime_owner is None
        assert metadata.lease_expires_at is None
        assert metadata.last_heartbeat_at is None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_sqlite_session_runtime_store_clears_expired_leases_and_pauses_running():
    tmp_dir = Path("build/tmp/test_session_backend") / str(uuid4())
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        db = DatabaseManager(db_path=str(tmp_dir / "sim.db"))
        assert db.initialize_database() is True
        session_id = db.create_simulation_session(
            user_id=7,
            config={"symbol": "EURUSD", "timeframe": "M1", "status": "running"},
        )
        expired_at = datetime.now(UTC) - timedelta(seconds=5)
        db.update_simulation_session(
            session_id,
            status="running",
            runtime_owner="dead-worker",
            lease_expires_at=expired_at,
            last_heartbeat_at=expired_at,
        )
        store = SQLiteSessionRuntimeStore(db)

        cleared = store.clear_expired_leases()

        assert cleared == 1
        metadata = store.get_metadata(session_id)
        assert metadata is not None
        assert metadata.runtime_owner is None
        assert metadata.lease_expires_at is None
        assert metadata.last_heartbeat_at is None
        assert metadata.status == "paused"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
