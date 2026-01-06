"""
Usage examples for apps.sqlite.live_trading.py

This module demonstrates:
- LiveTradingManager class for live trading operations
- Creating and managing live trading sessions
- Managing strategies in sessions
- Handling signals and positions
- Position event tracking
- Session logging
"""

from apps.sqlite import SQLiteDatabase
from datetime import datetime


def example_create_live_session():
    """
    Example: Create a live trading session

    Sessions configure risk management and trading parameters:
    - Mode (paper/live)
    - Position limits
    - Risk parameters
    - Trading hours
    """
    db = SQLiteDatabase(db_path="test_live_trading.db")
    db.initialize_database()

    # Create user
    user_id = db.create_user(
        email="livetrader@example.com",
        username="livetrader",
        password="pass"
    )

    # Create paper trading session
    session_id = db.create_live_session(
        user_id=user_id,
        session_name="Paper Trading Session",
        mode="paper",
        max_total_risk_pct=2.0,  # Max 2% account risk
        max_positions=5,  # Max 5 concurrent positions
        max_correlation=0.7,  # Max 0.7 correlation between pairs
        max_drawdown_pct=10.0,  # Kill switch at 10% DD
        trading_hours_start="09:00",
        trading_hours_end="17:00",
        allowed_days=[1, 2, 3, 4, 5]  # Monday-Friday
    )
    print(f"Paper trading session created: ID {session_id}")

    # Create live trading session
    live_session_id = db.create_live_session(
        user_id=user_id,
        session_name="Live Trading Session",
        mode="live",
        max_total_risk_pct=1.0,  # More conservative for live
        max_positions=3,
        max_correlation=0.6,
        max_drawdown_pct=5.0  # Tighter stop for live
    )
    print(f"Live trading session created: ID {live_session_id}")


def example_manage_session():
    """
    Example: Managing session status and settings

    Sessions can be:
    - Started/stopped
    - Updated with new parameters
    - Monitored with heartbeat
    """
    db = SQLiteDatabase(db_path="test_manage_session.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    session_id = db.create_live_session(
        user_id=user_id,
        session_name="Test Session",
        mode="paper"
    )

    print(f"Session {session_id} created")

    # Start session
    db.update_live_session(
        session_id,
        status="running",
        started_at=datetime.now()
    )
    print("  Status: running")

    # Update heartbeat (session is alive)
    db.update_live_session(
        session_id,
        last_heartbeat=datetime.now()
    )
    print("  Heartbeat updated")

    # Update risk parameters
    db.update_live_session(
        session_id,
        max_positions=4,
        max_total_risk_pct=1.5
    )
    print("  Risk parameters updated")

    # Stop session
    db.update_live_session(
        session_id,
        status="stopped",
        stopped_at=datetime.now()
    )
    print("  Status: stopped")

    # Get session details
    session = db.get_live_session(session_id)
    print(f"\nSession details:")
    print(f"  Name: {session['session_name']}")
    print(f"  Status: {session['status']}")
    print(f"  Mode: {session['mode']}")


def example_add_strategies_to_session():
    """
    Example: Add strategies to a live trading session

    Multiple strategies can run in one session, each with:
    - Specific symbols and timeframes
    - Risk per trade settings
    - Position sizing configuration
    - Custom parameters
    """
    db = SQLiteDatabase(db_path="test_session_strategies.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    session_id = db.create_live_session(
        user_id=user_id,
        session_name="Multi-Strategy Session"
    )

    # Create strategies
    strategy1_id = db.create_strategy(
        user_id=user_id,
        name="Trend Following"
    )
    version1_id = db.create_strategy_version(
        strategy_id=strategy1_id,
        version="1.0.0",
        file_path="strategies/trend.py"
    )

    strategy2_id = db.create_strategy(
        user_id=user_id,
        name="Mean Reversion"
    )
    version2_id = db.create_strategy_version(
        strategy_id=strategy2_id,
        version="1.0.0",
        file_path="strategies/mean_reversion.py"
    )

    # Add trend following strategy
    db.add_strategy_to_session(
        session_id=session_id,
        strategy_version_id=version1_id,
        symbols=["EURUSD", "GBPUSD"],
        timeframes=["H4", "D1"],
        max_risk_per_trade_pct=1.0,
        position_size_type="risk",
        position_size_value=1.0
    )
    print("Trend following strategy added to session")

    # Add mean reversion strategy
    db.add_strategy_to_session(
        session_id=session_id,
        strategy_version_id=version2_id,
        symbols=["USDJPY", "AUDUSD"],
        timeframes=["H1"],
        max_risk_per_trade_pct=0.5,
        position_size_type="fixed",
        position_size_value=0.1,  # 0.1 lots
        strategy_params={"rsi_period": 14, "oversold": 30, "overbought": 70}
    )
    print("Mean reversion strategy added to session")

    # Get all strategies in session
    strategies = db.get_session_strategies(session_id)
    print(f"\nTotal strategies in session: {len(strategies)}")
    for s in strategies:
        print(f"  - {s['strategy_name']} v{s['version']}")
        print(f"    Symbols: {s['symbols']}")
        print(f"    Timeframes: {s['timeframes']}")


def example_signal_management():
    """
    Example: Managing trading signals

    Signals are detected by strategies and can be:
    - Pending: Waiting for validation
    - Approved: Ready to execute
    - Rejected: Failed validation
    - Executed: Turned into position
    """
    db = SQLiteDatabase(db_path="test_signals.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    session_id = db.create_live_session(user_id=user_id, session_name="Test")
    strategy_id = db.create_strategy(user_id=user_id, name="Strategy")
    version_id = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strat.py"
    )
    db.add_strategy_to_session(
        session_id, version_id,
        symbols=["EURUSD"],
        timeframes=["H1"]
    )

    # Create a buy signal
    signal_id = db.create_live_signal(
        session_id=session_id,
        strategy_version_id=version_id,
        symbol="EURUSD",
        timeframe="H1",
        signal_type="BUY",
        signal_time=datetime.now().isoformat(),
        entry_price=1.0850,
        stop_loss=1.0820,
        take_profit=1.0910,
        risk_pips=30,
        risk_usd=100,
        position_size=0.1,
        reward_risk_ratio=2.0,
        signal_reason="MA crossover + RSI confirmation"
    )
    print(f"Signal created: ID {signal_id}")

    # Approve signal
    db.update_live_signal(signal_id, "approved")
    print("  Status: approved")

    # Execute signal (create position)
    position_id = db.create_live_position(
        session_id=session_id,
        signal_id=signal_id,
        mt5_ticket=123456,
        symbol="EURUSD",
        type="BUY",
        open_time=datetime.now().isoformat(),
        open_price=1.0851,
        position_size=0.1,
        initial_stop_loss=1.0820,
        initial_take_profit=1.0910
    )
    print(f"Position created: ID {position_id}")

    # Update signal with position reference
    db.update_live_signal(
        signal_id,
        "executed",
        position_id=position_id
    )
    print("  Status: executed")


def example_position_management():
    """
    Example: Managing open positions

    Track position lifecycle:
    - Entry
    - Updates (price, profit, SL/TP changes)
    - Trade management (breakeven, trailing stop)
    - Exit
    """
    db = SQLiteDatabase(db_path="test_positions.db")
    db.initialize_database()

    # Setup (simplified)
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    session_id = db.create_live_session(user_id=user_id, session_name="Test")

    # Create position
    position_id = db.create_live_position(
        session_id=session_id,
        signal_id=None,
        mt5_ticket=789012,
        symbol="GBPUSD",
        type="SELL",
        open_time=datetime.now().isoformat(),
        open_price=1.2650,
        position_size=0.15,
        initial_stop_loss=1.2680,
        initial_take_profit=1.2590
    )
    print(f"Position opened: ID {position_id}")

    # Update current price and profit
    db.update_live_position(
        position_id,
        current_price=1.2630,
        current_profit=30.0,
        current_profit_pct=0.15
    )
    print("  Updated: Price 1.2630, Profit $30")

    # Move stop loss to breakeven
    db.update_live_position(
        position_id,
        current_stop_loss=1.2650,
        breakeven_activated=True
    )
    print("  Breakeven activated")

    # Activate trailing stop
    db.update_live_position(
        position_id,
        current_stop_loss=1.2640,
        trailing_stop_activated=True
    )
    print("  Trailing stop activated")

    # Close position at profit
    db.update_live_position(
        position_id,
        status="closed",
        close_reason="take_profit",
        close_time=datetime.now().isoformat(),
        close_price=1.2590,
        final_profit=90.0,
        final_profit_pct=0.60
    )
    print("  Position closed: $90 profit")


def example_position_events():
    """
    Example: Track position events

    Events create an audit trail of position management:
    - Entry
    - Stop loss adjustments
    - Take profit adjustments
    - Partial closes
    - Final exit
    """
    db = SQLiteDatabase(db_path="test_events.db")
    db.initialize_database()

    # Setup (simplified)
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    session_id = db.create_live_session(user_id=user_id, session_name="Test")
    position_id = db.create_live_position(
        session_id=session_id,
        signal_id=None,
        mt5_ticket=111222,
        symbol="EURUSD",
        type="BUY",
        open_time=datetime.now().isoformat(),
        open_price=1.0900,
        position_size=0.2
    )

    # Entry event
    db.create_position_event(
        position_id=position_id,
        event_type="entry",
        price=1.0900,
        size=0.2,
        stop_loss=1.0870,
        take_profit=1.0960,
        reason="Signal triggered"
    )
    print(f"Event: entry at 1.0900")

    # Breakeven event
    db.create_position_event(
        position_id=position_id,
        event_type="stop_loss_update",
        stop_loss=1.0900,
        reason="Moved to breakeven"
    )
    print(f"Event: SL moved to breakeven")

    # Partial close event
    db.create_position_event(
        position_id=position_id,
        event_type="partial_close",
        price=1.0945,
        size=0.1,
        profit=45.0,
        reason="Take partial profit"
    )
    print(f"Event: Partial close, 0.1 lots at 1.0945")

    # Trailing stop event
    db.create_position_event(
        position_id=position_id,
        event_type="stop_loss_update",
        stop_loss=1.0930,
        reason="Trailing stop adjusted"
    )
    print(f"Event: Trailing stop moved to 1.0930")

    # Exit event
    db.create_position_event(
        position_id=position_id,
        event_type="exit",
        price=1.0950,
        size=0.1,
        profit=50.0,
        reason="Take profit hit"
    )
    print(f"Event: Final exit at 1.0950")


def example_session_logging():
    """
    Example: Session logging

    Log important events:
    - Signal detection
    - Risk checks
    - Position management
    - Errors and warnings
    """
    db = SQLiteDatabase(db_path="test_logs.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    session_id = db.create_live_session(user_id=user_id, session_name="Test")

    # Log session start
    db.create_session_log(
        session_id=session_id,
        log_level="INFO",
        log_category="session",
        message="Session started",
        details={"mode": "paper", "max_positions": 5}
    )
    print("Logged: Session started")

    # Log signal detection
    db.create_session_log(
        session_id=session_id,
        log_level="INFO",
        log_category="signal",
        message="Signal detected",
        details={
            "symbol": "EURUSD",
            "type": "BUY",
            "entry": 1.0850,
            "sl": 1.0820,
            "tp": 1.0910
        }
    )
    print("Logged: Signal detected")

    # Log risk check
    db.create_session_log(
        session_id=session_id,
        log_level="WARNING",
        log_category="risk",
        message="Signal rejected: Max positions reached",
        details={"current_positions": 5, "max_positions": 5}
    )
    print("Logged: Risk check warning")

    # Log error
    db.create_session_log(
        session_id=session_id,
        log_level="ERROR",
        log_category="execution",
        message="Failed to open position",
        details={
            "error": "Insufficient margin",
            "required": 500,
            "available": 400
        }
    )
    print("Logged: Execution error")

    # Retrieve logs
    logs = db.get_session_logs(session_id, limit=10)
    print(f"\nTotal logs: {len(logs)}")

    # Filter by level
    errors = db.get_session_logs(session_id, log_level="ERROR")
    print(f"Errors: {len(errors)}")

    # Filter by category
    risk_logs = db.get_session_logs(session_id, log_category="risk")
    print(f"Risk logs: {len(risk_logs)}")


def example_complete_live_trading_workflow():
    """
    Example: Complete live trading workflow

    1. Create session
    2. Add strategies
    3. Start session
    4. Detect signals
    5. Execute trades
    6. Manage positions
    7. Track events
    8. Log activities
    9. Stop session
    """
    db = SQLiteDatabase(db_path="test_live_workflow.db")
    db.initialize_database()

    print("Step 1: Create session")
    user_id = db.create_user(
        email="workflow@example.com",
        username="workflow",
        password="pass"
    )
    session_id = db.create_live_session(
        user_id=user_id,
        session_name="Production Session",
        mode="paper",
        max_positions=3
    )
    print(f"  Session ID: {session_id}")

    print("\nStep 2: Add strategies")
    strategy_id = db.create_strategy(user_id=user_id, name="Strategy")
    version_id = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strat.py"
    )
    db.add_strategy_to_session(
        session_id, version_id,
        symbols=["EURUSD"],
        timeframes=["H1"]
    )
    print("  Strategy added")

    print("\nStep 3: Start session")
    db.update_live_session(session_id, status="running", started_at=datetime.now())
    db.create_session_log(
        session_id, "INFO", "session",
        "Session started"
    )
    print("  Status: running")

    print("\nStep 4: Detect signal")
    signal_id = db.create_live_signal(
        session_id=session_id,
        strategy_version_id=version_id,
        symbol="EURUSD",
        timeframe="H1",
        signal_type="BUY",
        signal_time=datetime.now().isoformat(),
        entry_price=1.0850
    )
    db.create_session_log(
        session_id, "INFO", "signal",
        "Signal detected", {"signal_id": signal_id}
    )
    print(f"  Signal ID: {signal_id}")

    print("\nStep 5: Execute trade")
    position_id = db.create_live_position(
        session_id=session_id,
        signal_id=signal_id,
        mt5_ticket=123456,
        symbol="EURUSD",
        type="BUY",
        open_time=datetime.now().isoformat(),
        open_price=1.0851,
        position_size=0.1
    )
    db.update_live_signal(signal_id, "executed", position_id=position_id)
    print(f"  Position ID: {position_id}")

    print("\nStep 6: Manage position")
    db.create_position_event(
        position_id, "entry",
        price=1.0851, size=0.1
    )
    print("  Position opened")

    print("\nStep 7: Update and close")
    db.update_live_position(
        position_id,
        status="closed",
        close_price=1.0890,
        final_profit=39.0
    )
    db.create_position_event(
        position_id, "exit",
        price=1.0890, profit=39.0
    )
    print("  Position closed: $39 profit")

    print("\nStep 8: Stop session")
    db.update_live_session(session_id, status="stopped", stopped_at=datetime.now())
    db.create_session_log(
        session_id, "INFO", "session",
        "Session stopped"
    )
    print("  Status: stopped")

    print("\nWorkflow complete!")


if __name__ == "__main__":
    print("=" * 80)
    print("LiveTradingManager Usage Examples")
    print("=" * 80)

    print("\n1. Create Live Session")
    print("-" * 80)
    example_create_live_session()

    print("\n2. Manage Session")
    print("-" * 80)
    example_manage_session()

    print("\n3. Add Strategies to Session")
    print("-" * 80)
    example_add_strategies_to_session()

    print("\n4. Signal Management")
    print("-" * 80)
    example_signal_management()

    print("\n5. Position Management")
    print("-" * 80)
    example_position_management()

    print("\n6. Position Events")
    print("-" * 80)
    example_position_events()

    print("\n7. Session Logging")
    print("-" * 80)
    example_session_logging()

    print("\n8. Complete Live Trading Workflow")
    print("-" * 80)
    example_complete_live_trading_workflow()
