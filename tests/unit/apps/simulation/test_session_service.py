from __future__ import annotations

from types import SimpleNamespace

from apps.simulation import session_service


class DummyActiveSessions:
    def __init__(self, active=None) -> None:
        self.active = active
        self.put_calls: list[tuple[int, object]] = []
        self.remove_calls: list[int] = []

    def get(self, session_id: int):
        return self.active

    def put(self, session_id: int, session) -> None:
        self.put_calls.append((session_id, session))

    def remove(self, session_id: int):
        self.remove_calls.append(session_id)
        active = self.active
        self.active = None
        return active


class DummyDb:
    def __init__(self) -> None:
        self.updated: list[tuple[int, dict]] = []
        self.deleted: list[int] = []

    def update_simulation_session(self, session_id: int, **kwargs):
        self.updated.append((session_id, kwargs))

    def delete_simulation_session(self, session_id: int):
        self.deleted.append(session_id)


def test_resume_or_restore_session_resumes_existing_active():
    active = SimpleNamespace(resume_called=False)

    def resume():
        active.resume_called = True

    active.resume = resume
    result = session_service.resume_or_restore_session(
        db_manager=DummyDb(),
        active_sessions=DummyActiveSessions(active),
        session_id=9,
        session_data={"config": {}, "current_bar_index": 3},
        user_id=42,
    )

    assert result == {"session_id": 9, "status": "running"}
    assert active.resume_called is True


def test_delete_session_runtime_stops_active_before_delete():
    stopped: list[str] = []
    active = SimpleNamespace(stop=lambda: stopped.append("stopped"))
    db = DummyDb()

    result = session_service.delete_session_runtime(
        db_manager=db,
        active_sessions=DummyActiveSessions(active),
        session_id=15,
    )

    assert result == {"session_id": 15, "status": "deleted"}
    assert stopped == ["stopped"]
    assert db.deleted == [15]
