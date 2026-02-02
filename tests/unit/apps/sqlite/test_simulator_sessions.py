"""Tests for simulator session database operations."""

from apps.sqlite import SQLiteDatabase


def test_simulator_session_crud(tmp_path):
    db_path = tmp_path / "simulator.db"
    db = SQLiteDatabase(db_path=str(db_path))
    assert db.initialize_database()

    session_id = db.create_simulation_session(
        user_id=1,
        config={
            "session_name": "Test Session",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "status": "paused",
        },
    )
    assert session_id > 0

    session = db.get_simulation_session(session_id)
    assert session is not None
    assert session["symbol"] == "EURUSD"

    db.update_simulation_session(session_id, status="running", current_bar_index=5)
    updated = db.get_simulation_session(session_id)
    assert updated is not None
    assert updated["status"] == "running"
    assert updated["current_bar_index"] == 5

    trade_id = db.save_trade(
        session_id,
        {"symbol": "EURUSD", "side": "buy", "price": 1.1, "volume": 0.1},
    )
    assert trade_id > 0
    trades = db.get_simulation_trades(session_id)
    assert len(trades) == 1

    paused = db.get_paused_simulation_sessions(user_id=1)
    assert isinstance(paused, list)

    assert db.delete_simulation_session(session_id)
    assert db.get_simulation_session(session_id) is None
