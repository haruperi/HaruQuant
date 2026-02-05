"""Usage examples for SimulatorManager module."""

from datetime import datetime, timedelta
from apps.sqlite import SQLiteDatabase


def main():
    """Demonstrate SimulatorManager usage."""
    # Initialize database
    db = SQLiteDatabase(db_path="data/database/haruquant.db")
    db.initialize_database()

    print("=== SimulatorManager Usage Examples ===\n")

    # Example 1: Create a simulation session
    print("1. Creating Simulation Session")

    session_config = {
        "session_name": "EURUSD Manual Trading Practice",
        "mode": "manual",
        "status": "running",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "start_time": "2023-01-01T00:00:00",
        "end_time": "2023-12-31T23:59:59",
        "initial_balance": 10000.0,
        "speed_multiplier": 1.0,
        "current_bar_index": 0,
        "total_bars": 8760,
        "replay_source": "historical_data",
        "replay_backtest_id": None,
        "replay_file_name": "EURUSD_H1_2023.csv",
    }

    session_id = db.create_simulation_session(user_id=1, config=session_config)
    print(f"Created simulation session ID: {session_id}")
    print(f"  Symbol: {session_config['symbol']}")
    print(f"  Timeframe: {session_config['timeframe']}")
    print(f"  Mode: {session_config['mode']}")
    print(f"  Initial Balance: ${session_config['initial_balance']:.2f}")
    print()

    # Example 2: Save simulation trades
    print("2. Saving Simulation Trades")

    trade1 = {
        "time": "2023-01-05T10:30:00",
        "symbol": "EURUSD",
        "side": "BUY",
        "price": 1.0850,
        "volume": 0.1,
        "sl": 1.0820,
        "tp": 1.0910,
        "pnl": 60.0,
        "reason": "Manual entry on support level",
        "source": "manual",
    }

    trade_id1 = db.save_trade(session_id, trade1)
    print(f"Saved trade ID: {trade_id1}")
    print(f"  {trade1['side']} {trade1['volume']} lots at {trade1['price']}")
    print(f"  P/L: ${trade1['pnl']:.2f}")

    trade2 = {
        "time": "2023-01-10T14:15:00",
        "symbol": "EURUSD",
        "side": "SELL",
        "price": 1.0920,
        "volume": 0.15,
        "sl": 1.0950,
        "tp": 1.0870,
        "pnl": 75.0,
        "reason": "Resistance rejection",
        "source": "manual",
    }

    trade_id2 = db.save_trade(session_id, trade2)
    print(f"Saved trade ID: {trade_id2}")
    print(f"  {trade2['side']} {trade2['volume']} lots at {trade2['price']}")
    print(f"  P/L: ${trade2['pnl']:.2f}")
    print()

    # Example 3: Get simulation session
    print("3. Retrieving Simulation Session")
    session = db.get_simulation_session(session_id)
    if session:
        print(f"Session ID: {session['session_id']}")
        print(f"Name: {session['session_name']}")
        print(f"Symbol: {session['symbol']}")
        print(f"Status: {session['status']}")
        print(f"Current Bar Index: {session['current_bar_index']}")
        print(f"Total Bars: {session['total_bars']}")
        print(
            f"Progress: {session['current_bar_index'] / session['total_bars'] * 100:.1f}%"
        )
    print()

    # Example 4: Get simulation trades
    print("4. Retrieving Simulation Trades")
    trades = db.get_simulation_trades(session_id)
    print(f"Found {len(trades)} trades for session {session_id}")
    for trade in trades:
        print(
            f"  - {trade['time']}: {trade['side']} {trade['volume']} @ {trade['price']}, "
            f"P/L: ${trade['pnl']:.2f}"
        )
    print()

    # Example 5: Update simulation session
    print("5. Updating Simulation Session")
    updated = db.update_simulation_session(
        session_id,
        current_bar_index=500,
        speed_multiplier=2.0,
    )
    print(f"Updated session: {updated}")

    session = db.get_simulation_session(session_id)
    print(f"  New Bar Index: {session['current_bar_index']}")
    print(f"  New Speed Multiplier: {session['speed_multiplier']}")
    print()

    # Example 6: Save simulation state (for resume)
    print("6. Saving Simulation State")
    saved = db.save_simulation_state(session_id, current_bar_index=750)
    print(f"Saved state at bar index 750: {saved}")
    print()

    # Example 7: Update session status to paused
    print("7. Pausing Simulation Session")
    paused = db.update_session_status(session_id, status="paused")
    print(f"Paused session: {paused}")

    session = db.get_simulation_session(session_id)
    print(f"  Status: {session['status']}")
    print()

    # Example 8: List simulation sessions
    print("8. Listing Simulation Sessions")
    sessions = db.list_simulation_sessions(user_id=1, limit=10)
    print(f"Found {len(sessions)} sessions for user 1")
    for sess in sessions:
        print(
            f"  - {sess['session_name']} ({sess['symbol']} {sess['timeframe']}): {sess['status']}"
        )
    print()

    # Example 9: Get paused sessions
    print("9. Getting Paused Sessions")
    paused_sessions = db.get_paused_simulation_sessions(user_id=1)
    print(f"Found {len(paused_sessions)} paused sessions")
    for sess in paused_sessions:
        print(
            f"  - {sess['session_name']}: Bar {sess['current_bar_index']}/{sess['total_bars']}"
        )
    print()

    # Example 10: Resume session (update status)
    print("10. Resuming Simulation Session")
    resumed = db.update_session_status(session_id, status="running")
    print(f"Resumed session: {resumed}")

    session = db.get_simulation_session(session_id)
    print(f"  Status: {session['status']}")
    print()

    # Example 11: Complete a session
    print("11. Completing Simulation Session")
    completed = db.update_session_status(session_id, status="completed")
    print(f"Completed session: {completed}")

    session = db.get_simulation_session(session_id)
    print(f"  Status: {session['status']}")
    print(f"  Completed At: {session['completed_at']}")
    print()

    # Example 12: Save simulator deals (low-level deal data)
    print("12. Saving Simulator Deals")

    deal1 = {
        "time": "2023-01-05T10:30:00",
        "magic": 12345,
        "symbol": "EURUSD",
        "type": "DEAL_TYPE_BUY",
        "direction": "IN",
        "volume": 0.1,
        "price": 1.0850,
        "spread": 2,
        "sl": 1.0820,
        "tp": 1.0910,
        "commission": -0.50,
        "margin_required": 100.0,
        "fee": 0.0,
        "swap": 0.0,
        "profit": 0.0,
        "comment": "Entry at support",
        "reason": "Signal detected",
        "entry_reason": "Price bounced from support",
        "session_id": session_id,
    }

    db.save_simulator_deal(deal1)
    print(f"Saved deal: {deal1['type']} {deal1['volume']} @ {deal1['price']}")

    deal2 = {
        "time": "2023-01-05T22:15:00",
        "magic": 12345,
        "symbol": "EURUSD",
        "type": "DEAL_TYPE_SELL",
        "direction": "OUT",
        "volume": 0.1,
        "price": 1.0910,
        "spread": 2,
        "sl": 0.0,
        "tp": 0.0,
        "commission": -0.50,
        "margin_required": 0.0,
        "fee": 0.0,
        "swap": -0.25,
        "profit": 60.0,
        "comment": "TP hit",
        "reason": "Take profit",
        "entry_reason": "Price bounced from support",
        "session_id": session_id,
    }

    db.save_simulator_deal(deal2)
    print(f"Saved deal: {deal2['type']} {deal2['volume']} @ {deal2['price']}")
    print(f"  Profit: ${deal2['profit']:.2f}")
    print()

    # Example 13: Load simulator deals
    print("13. Loading Simulator Deals")
    start_time = datetime(2023, 1, 1)
    end_time = datetime(2023, 12, 31)
    deals = db.load_simulator_deals(start_time, end_time)
    print(f"Found {len(deals)} deals between {start_time.date()} and {end_time.date()}")
    for deal in deals[:5]:
        print(
            f"  - {deal['time']}: {deal['type']} {deal['volume']} @ {deal['price']}, "
            f"Profit: ${deal['profit']:.2f}"
        )
    print()

    # Example 14: Create another session for deletion example
    print("14. Creating Test Session for Deletion")
    test_config = {
        "session_name": "Test Session",
        "mode": "replay",
        "symbol": "GBPUSD",
        "timeframe": "M15",
        "initial_balance": 5000.0,
    }

    test_session_id = db.create_simulation_session(user_id=1, config=test_config)
    print(f"Created test session ID: {test_session_id}")
    print()

    # Example 15: Delete simulation session
    print("15. Deleting Simulation Session")
    deleted = db.delete_simulation_session(test_session_id)
    print(f"Deleted session {test_session_id}: {deleted}")

    # Verify deletion
    deleted_session = db.get_simulation_session(test_session_id)
    print(f"Verification - Session exists: {deleted_session is not None}")
    print()

    # Example 16: Delete old sessions
    print("16. Deleting Old Sessions (older than 30 days)")
    # Create an old session by manually setting created_at (for demo purposes)
    # In practice, this would be sessions that are actually old
    old_count = db.delete_simulation_sessions_older_than(days=30)
    print(f"Deleted {old_count} sessions older than 30 days")
    print()

    print("=== SimulatorManager Examples Complete ===")


if __name__ == "__main__":
    main()
