from __future__ import annotations

from backend.agents import SessionManager, SessionState


def test_session_manager_tracks_lifecycle_and_workflow_binding() -> None:
    manager = SessionManager()

    created = manager.create_session(metadata={"operator_id": "op_001"})
    activated = manager.activate_session(created.session_id)
    bound = manager.bind_workflow(session_id=created.session_id, workflow_id="wf_001")
    closed = manager.close_session(created.session_id)

    assert created.state == SessionState.CREATED
    assert activated.state == SessionState.ACTIVE
    assert bound.workflow_ids == ("wf_001",)
    assert closed.state == SessionState.CLOSED
    assert manager.get_session(created.session_id) == closed


def test_session_manager_avoids_duplicate_workflow_binding_and_requires_existing_session() -> None:
    manager = SessionManager()
    session = manager.create_session(session_id="sess_001")

    first = manager.bind_workflow(session_id="sess_001", workflow_id="wf_001")
    second = manager.bind_workflow(session_id="sess_001", workflow_id="wf_001")

    assert first.workflow_ids == ("wf_001",)
    assert second.workflow_ids == ("wf_001",)

    missing_failed = False
    try:
        manager.activate_session("missing_session")
    except LookupError:
        missing_failed = True

    assert missing_failed is True
