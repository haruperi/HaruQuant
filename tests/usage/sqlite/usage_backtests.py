"""
Usage examples for apps.sqlite.backtests.py

This module demonstrates:
- BacktestManager class for backtest operations
- Creating backtest runs
- Saving complete backtest results with 4-layer architecture
- Retrieving backtest data and metrics
"""

from apps.sqlite import SQLiteDatabase
from datetime import datetime


def example_create_backtest_run():
    """
    Example: Create a new backtest run (Layer 1: Run)

    A backtest run records the configuration and metadata for a backtest.
    """
    db = SQLiteDatabase(db_path="test_backtests.db")
    db.initialize_database()

    # Create user and strategy
    user_id = db.create_user(
        email="backtester@example.com",
        username="backtester",
        password="pass"
    )
    strategy_id = db.create_strategy(user_id=user_id, name="MA Crossover")
    version_id = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strategies/ma.py"
    )

    # Create backtest run
    backtest_id = db.create_backtest_run(
        strategy_name="MA Crossover",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="tick",
        config_hash="abc123",
        strategy_version_id=version_id,
        user_id=user_id,
        symbols=["EURUSD", "GBPUSD"],
        timeframes=["H1", "H4"],
        initial_balance=10000.0,
        alias="2023 Full Year Test",
        description="Testing MA crossover on major pairs"
    )

    print(f"Backtest run created with ID: {backtest_id}")
    print("  Status: pending")
    print("  Ready to execute backtest")


def example_save_backtest_result():
    """
    Example: Save complete backtest result

    This demonstrates saving a complete BacktestResult object
    with the 4-layer architecture:
    - Layer 1: Run metadata
    - Layer 2: Trades and equity curve
    - Layer 3: Finance metrics
    - Layer 4: Research data

    Note: This example simulates the BacktestResult structure.
    In practice, you would pass an actual BacktestResult object.
    """
    db = SQLiteDatabase(db_path="test_save_result.db")
    db.initialize_database()

    print("Note: This example shows the structure.")
    print("In practice, use: db.save_backtest_result(backtest_result)")
    print("\nBacktestResult should contain:")
    print("  - Strategy metadata")
    print("  - Date range and symbols")
    print("  - Initial and final balance")
    print("  - List of Trade objects")
    print("  - List of EquityPoint objects")
    print("  - comprehensive_summary() method")


def example_get_backtest_run():
    """
    Example: Retrieve a backtest run

    Get backtest configuration and status.
    """
    db = SQLiteDatabase(db_path="test_get_run.db")
    db.initialize_database()

    # Setup
    backtest_id = db.create_backtest_run(
        strategy_name="Test Strategy",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="tick",
        config_hash="test123",
        symbols=["EURUSD"],
        timeframes=["H1"],
        initial_balance=10000.0
    )

    # Retrieve backtest run
    run = db.get_backtest_run(backtest_id)
    print("\nBacktest Run Details:")
    print(f"  ID: {run['backtest_id']}")
    print(f"  Strategy: {run['strategy_name']} v{run['strategy_version']}")
    print(f"  Period: {run['start_date']} to {run['end_date']}")
    print(f"  Symbols: {run['symbols']}")
    print(f"  Timeframes: {run['timeframes']}")
    print(f"  Initial Balance: ${run['initial_balance']}")
    print(f"  Status: {run['status']}")


def example_get_all_backtests():
    """
    Example: Retrieve all backtests with filters

    Can filter by:
    - User ID
    - Strategy version ID
    - Status
    - Limit results
    """
    db = SQLiteDatabase(db_path="test_get_all.db")
    db.initialize_database()

    # Create user and strategy
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    strategy_id = db.create_strategy(user_id=user_id, name="Strategy")
    version_id = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strat.py"
    )

    # Create multiple backtests
    for i in range(5):
        db.create_backtest_run(
            strategy_name="Strategy",
            strategy_version="1.0.0",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            engine_type="event",
            data_resolution="tick",
            config_hash=f"hash{i}",
            strategy_version_id=version_id,
            user_id=user_id,
            alias=f"Test {i+1}"
        )

    # Get all backtests
    all_backtests = db.get_all_backtests(limit=10)
    print(f"Total backtests: {len(all_backtests)}")

    # Filter by user
    user_backtests = db.get_all_backtests(user_id=user_id)
    print(f"User backtests: {len(user_backtests)}")

    # Filter by strategy version
    version_backtests = db.get_all_backtests(strategy_version_id=version_id)
    print(f"Strategy version backtests: {len(version_backtests)}")

    # Filter by status
    pending_backtests = db.get_all_backtests(status="pending")
    print(f"Pending backtests: {len(pending_backtests)}")


def example_update_backtest_status():
    """
    Example: Update backtest status

    Status transitions:
    - pending -> running
    - running -> completed
    - running -> failed
    """
    db = SQLiteDatabase(db_path="test_status.db")
    db.initialize_database()

    # Create backtest
    backtest_id = db.create_backtest_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="tick",
        config_hash="test"
    )

    # Start backtest
    db.update_backtest_status(backtest_id, "running")
    print(f"Backtest {backtest_id} status: running")

    # Complete backtest
    db.update_backtest_status(
        backtest_id,
        "completed",
        final_balance=12500.0
    )
    print(f"Backtest {backtest_id} status: completed")
    print("  Final balance: $12,500")

    # Verify update
    run = db.get_backtest_run(backtest_id)
    print(f"\nVerified:")
    print(f"  Status: {run['status']}")
    print(f"  Final Balance: ${run['final_balance']}")
    print(f"  Completed At: {run['completed_at']}")


def example_get_backtest_trades():
    """
    Example: Retrieve trades for a backtest (Layer 2: Facts)

    Trades include detailed information:
    - Entry/exit details
    - Risk management
    - Performance metrics
    - Execution quality
    """
    db = SQLiteDatabase(db_path="test_trades.db")
    db.initialize_database()

    # Create backtest
    backtest_id = db.create_backtest_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="tick",
        config_hash="test"
    )

    # Note: In practice, trades are saved via save_backtest_result()
    # This example shows how to retrieve them

    # Retrieve trades
    trades = db.get_backtest_trades(backtest_id)

    print(f"Backtest {backtest_id} trades: {len(trades)}")
    print("\nTrade structure includes:")
    print("  - Entry: ticket, symbol, side, open_time, open_price, size")
    print("  - Exit: close_time, close_price, exit_reason")
    print("  - Risk: stop_loss_price, profit_target_price, risk_usd")
    print("  - Performance: pnl, pnl_pips, r_multiple")
    print("  - Excursion: mae_usd, mfe_usd, mae_pips, mfe_pips")


def example_get_equity_curve():
    """
    Example: Retrieve equity curve (Layer 2: Facts)

    Equity curve shows balance over time.
    """
    db = SQLiteDatabase(db_path="test_equity.db")
    db.initialize_database()

    # Create backtest
    backtest_id = db.create_backtest_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="tick",
        config_hash="test"
    )

    # Retrieve equity curve
    equity_curve = db.get_backtest_equity_curve(backtest_id)

    print(f"Equity curve points: {len(equity_curve)}")
    print("\nEquity point structure:")
    print("  - timestamp: Date/time of the point")
    print("  - equity: Current account equity")
    print("  - balance: Current account balance")
    print("  - drawdown: Current drawdown")
    print("  - exposure: Current market exposure")


def example_get_finance_metrics():
    """
    Example: Retrieve finance metrics (Layer 3: Derived)

    Finance metrics are derived from trades and organized into categories:
    - Trade metrics (win rate, profit factor, etc.)
    - Return metrics (CAGR, volatility, etc.)
    - Drawdown metrics (max DD, recovery factor, etc.)
    - Ratio metrics (Sharpe, Sortino, Calmar, etc.)
    - Risk metrics (VaR, CVaR, etc.)
    - Efficiency metrics (MFE/MAE, exit efficiency, etc.)
    """
    db = SQLiteDatabase(db_path="test_metrics.db")
    db.initialize_database()

    # Create backtest
    backtest_id = db.create_backtest_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="tick",
        config_hash="test"
    )

    # Note: Metrics are calculated and saved via save_backtest_result()

    # Retrieve all finance metrics
    metrics = db.get_backtest_finance_metrics(backtest_id)

    print("Finance Metrics Categories:")
    print("\n1. Trade Metrics:")
    if 'trade_metrics' in metrics:
        print("     - total_trades, winning_trades, losing_trades")
        print("     - win_rate, profit_factor, expectancy")
        print("     - avg_win, avg_loss, payoff_ratio")

    print("\n2. Return Metrics:")
    if 'return_metrics' in metrics:
        print("     - net_profit, total_return, CAGR")
        print("     - volatility, annualized_volatility")
        print("     - skew, kurtosis")

    print("\n3. Drawdown Metrics:")
    if 'drawdown_metrics' in metrics:
        print("     - max_drawdown, max_drawdown_pct")
        print("     - max_drawdown_duration")
        print("     - ulcer_index, pain_ratio")

    print("\n4. Ratio Metrics:")
    if 'ratio_metrics' in metrics:
        print("     - sharpe, sortino, calmar, omega")
        print("     - profit_to_mae_ratio, mfe_to_mae_ratio")

    print("\n5. Risk Metrics:")
    if 'risk_metrics' in metrics:
        print("     - var_95, cvar_95, var_99, cvar_99")
        print("     - risk_of_ruin, max_exposure")

    print("\n6. Efficiency Metrics:")
    if 'efficiency_metrics' in metrics:
        print("     - mfe_efficiency, mae_efficiency")
        print("     - exit_efficiency, time_efficiency")


def example_delete_backtest():
    """
    Example: Delete a backtest

    Cascade behavior:
    - Deletes backtest run
    - Deletes all trades
    - Deletes equity curve
    - Deletes all finance metrics
    """
    db = SQLiteDatabase(db_path="test_delete.db")
    db.initialize_database()

    # Create backtest
    backtest_id = db.create_backtest_run(
        strategy_name="Temporary Test",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="tick",
        config_hash="temp"
    )
    print(f"Backtest {backtest_id} created")

    # Verify exists
    run = db.get_backtest_run(backtest_id)
    print(f"Backtest exists: {run is not None}")

    # Delete backtest
    success = db.delete_backtest(backtest_id)
    print(f"\nBacktest deleted: {success}")

    # Verify deletion
    run = db.get_backtest_run(backtest_id)
    print(f"Backtest exists after deletion: {run is not None}")


def example_complete_backtest_workflow():
    """
    Example: Complete backtest workflow

    1. Create backtest run
    2. Update status to running
    3. Execute backtest (external)
    4. Save results
    5. Update status to completed
    6. Retrieve and analyze metrics
    """
    db = SQLiteDatabase(db_path="test_complete.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="workflow@example.com",
        username="workflow",
        password="pass"
    )
    strategy_id = db.create_strategy(user_id=user_id, name="Workflow Strategy")
    version_id = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strategies/workflow.py"
    )

    print("Step 1: Create backtest run")
    backtest_id = db.create_backtest_run(
        strategy_name="Workflow Strategy",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="bar",
        config_hash="workflow123",
        strategy_version_id=version_id,
        user_id=user_id,
        symbols=["EURUSD"],
        timeframes=["H1"],
        initial_balance=10000.0,
        alias="Production Test",
        commission_model="fixed",
        slippage_model="spread"
    )
    print(f"  Backtest ID: {backtest_id}")

    print("\nStep 2: Update status to running")
    db.update_backtest_status(backtest_id, "running")
    print("  Status: running")

    print("\nStep 3: Execute backtest")
    print("  (External: Run backtest engine)")
    print("  (Generate BacktestResult object)")

    print("\nStep 4: Save results")
    print("  Use: db.save_backtest_result(backtest_result)")
    print("  This saves:")
    print("    - Trades (Layer 2)")
    print("    - Equity curve (Layer 2)")
    print("    - Finance metrics (Layer 3)")

    print("\nStep 5: Update status to completed")
    db.update_backtest_status(backtest_id, "completed", final_balance=12000.0)
    print("  Status: completed")
    print("  Final balance: $12,000")

    print("\nStep 6: Retrieve and analyze")
    run = db.get_backtest_run(backtest_id)
    print(f"  Backtest: {run['alias']}")
    print(f"  Return: {((run['final_balance'] - run['initial_balance']) / run['initial_balance'] * 100):.2f}%")

    # In practice, you would also retrieve:
    # trades = db.get_backtest_trades(backtest_id)
    # equity = db.get_backtest_equity_curve(backtest_id)
    # metrics = db.get_backtest_finance_metrics(backtest_id)


if __name__ == "__main__":
    print("=" * 80)
    print("BacktestManager Usage Examples")
    print("=" * 80)

    print("\n1. Create Backtest Run")
    print("-" * 80)
    example_create_backtest_run()

    print("\n2. Save Backtest Result")
    print("-" * 80)
    example_save_backtest_result()

    print("\n3. Get Backtest Run")
    print("-" * 80)
    example_get_backtest_run()

    print("\n4. Get All Backtests")
    print("-" * 80)
    example_get_all_backtests()

    print("\n5. Update Backtest Status")
    print("-" * 80)
    example_update_backtest_status()

    print("\n6. Get Backtest Trades")
    print("-" * 80)
    example_get_backtest_trades()

    print("\n7. Get Equity Curve")
    print("-" * 80)
    example_get_equity_curve()

    print("\n8. Get Finance Metrics")
    print("-" * 80)
    example_get_finance_metrics()

    print("\n9. Delete Backtest")
    print("-" * 80)
    example_delete_backtest()

    print("\n10. Complete Backtest Workflow")
    print("-" * 80)
    example_complete_backtest_workflow()
