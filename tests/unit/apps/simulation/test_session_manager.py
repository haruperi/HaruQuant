from apps.simulation.session_manager import SimulatorSessionManager


def test_session_manager_put_get_remove_round_trip():
    manager = SimulatorSessionManager[object]()
    session = object()

    assert manager.get(42) is None

    manager.put(42, session)
    assert manager.get(42) is session

    removed = manager.remove(42)
    assert removed is session
    assert manager.get(42) is None
