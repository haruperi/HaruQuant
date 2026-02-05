"""Usage examples for EdgeDiscoveryManager module."""

from datetime import datetime
from apps.sqlite import SQLiteDatabase


def main():
    """Demonstrate EdgeDiscoveryManager usage."""
    # Initialize database
    db = SQLiteDatabase(db_path="data/database/haruquant.db")
    db.initialize_database()

    print("=== EdgeDiscoveryManager Usage Examples ===\n")

    # Example 1: Save an edge discovery result
    print("1. Saving Edge Discovery Result")
    edge_result = {
        "symbol": "EURUSD",
        "timeframe": "H1",
        "eds_name": "EDS-1-MeanReversion",
        "config": {
            "data": {"start_pos": 0, "end_pos": 5000},
            "bootstrap": {"n_boot": 2000, "block_size": 20, "ci_level": 0.95},
            "perm": {"n_perm": 2000},
        },
        "stats": {
            "n_trades": 150,
            "expectancy_r": 0.45,
            "win_rate": 0.58,
            "profit_factor": 1.85,
            "median_mae_r": -0.15,
            "median_mfe_r": 0.65,
            "avg_hold_bars": 12,
            "ci_low": 0.32,
            "ci_high": 0.58,
            "p_value_perm": 0.023,
            "extras": {"strategy_type": "mean_reversion"},
        },
        "trades": [
            {
                "entry_time": "2023-01-05 10:00:00",
                "exit_time": "2023-01-05 22:00:00",
                "side": "BUY",
                "entry_price": 1.0850,
                "exit_price": 1.0880,
                "r_multiple": 1.2,
                "mae_r": -0.1,
                "mfe_r": 1.5,
                "hold_bars": 12,
                "meta": {"signal_strength": 0.8},
            },
            {
                "entry_time": "2023-01-10 14:00:00",
                "exit_time": "2023-01-11 02:00:00",
                "side": "SELL",
                "entry_price": 1.0920,
                "exit_price": 1.0905,
                "r_multiple": 0.6,
                "mae_r": -0.2,
                "mfe_r": 0.8,
                "hold_bars": 12,
                "meta": {"signal_strength": 0.6},
            },
        ],
    }

    run_id = db.save_edge_result(edge_result, user_id=1, save_trades=True)
    print(f"Saved edge discovery run with ID: {run_id}")
    print()

    # Example 2: Get edge run by ID
    print("2. Retrieving Edge Run by ID")
    run = db.get_edge_run(run_id)
    if run:
        print(f"Run ID: {run['run_id']}")
        print(f"Symbol: {run['symbol']}")
        print(f"Timeframe: {run['timeframe']}")
        print(f"EDS Name: {run['eds_name']}")
        print(f"EDS Type: {run['eds_type']}")
        print(f"Verdict: {run['verdict']}")
        print(f"Edge Confirmed: {bool(run['edge_confirmed'])}")
        print(f"Expectancy R: {run['expectancy_r']}")
        print(f"Win Rate: {run['win_rate']}")
        print(f"CI Low: {run['ci_low']}, CI High: {run['ci_high']}")
        print(f"P-Value: {run['p_value_perm']}")
    print()

    # Example 3: Get edge runs with filters
    print("3. Retrieving Edge Runs with Filters")
    runs = db.get_edge_runs(
        symbol="EURUSD", timeframe="H1", edge_confirmed_only=False, limit=10
    )
    print(f"Found {len(runs)} edge discovery runs for EURUSD H1")
    for r in runs[:3]:
        print(
            f"  - {r['eds_name']}: {r['verdict']} "
            f"(Exp: {r['expectancy_r']:.3f}, Win Rate: {r['win_rate']:.2%})"
        )
    print()

    # Example 4: Get confirmed edges only
    print("4. Retrieving Confirmed Edges Only")
    confirmed = db.get_confirmed_edges(symbol="EURUSD", limit=5)
    print(f"Found {len(confirmed)} confirmed edges for EURUSD")
    for edge in confirmed:
        print(
            f"  - {edge['eds_name']} on {edge['timeframe']}: "
            f"Exp={edge['expectancy_r']:.3f}, PF={edge['profit_factor']:.2f}"
        )
    print()

    # Example 5: Get edge trades
    print("5. Retrieving Edge Trades")
    trades = db.get_edge_trades(run_id)
    print(f"Found {len(trades)} trades for run {run_id}")
    for trade in trades[:3]:
        print(
            f"  - {trade['side']} at {trade['entry_price']:.4f} -> {trade['exit_price']:.4f}, "
            f"R={trade['r_multiple']:.2f}"
        )
    print()

    # Example 6: Get edge stats
    print("6. Retrieving Edge Stats")
    stats = db.get_edge_stats(run_id)
    if stats:
        print(f"Stats for run {run_id}:")
        print(f"  Trades: {stats['n_trades']}")
        print(f"  Expectancy R: {stats['expectancy_r']:.3f}")
        print(f"  Win Rate: {stats['win_rate']:.2%}")
        print(f"  Profit Factor: {stats['profit_factor']:.2f}")
        print(f"  Median MAE R: {stats['median_mae_r']:.3f}")
        print(f"  Median MFE R: {stats['median_mfe_r']:.3f}")
    print()

    # Example 7: Get edge summary rows (grouped by symbol/timeframe)
    print("7. Getting Edge Summary Rows")
    summary_rows = db.get_edge_summary_rows(symbol="EURUSD")
    print(f"Found {len(summary_rows)} symbol/timeframe combinations")
    for row in summary_rows[:2]:
        print(f"\n  {row['symbol']} {row['timeframe']}:")
        print(f"    Latest Run: {row['latest_run_id']}")
        print(f"    Verdict: {row['verdict']}")
        if row["mr"]:
            print(f"    MR Run: {row['mr']['eds_name']} - {row['mr']['verdict']}")
        if row["bo"]:
            print(f"    BO Run: {row['bo']['eds_name']} - {row['bo']['verdict']}")
    print()

    # Example 8: Get edge summary statistics
    print("8. Getting Edge Summary Statistics")
    summary = db.get_edge_summary()
    print(f"Total Runs: {summary['total_runs']}")
    print(f"Confirmed Edges: {summary['confirmed_count']}")
    print(f"Confirmation Rate: {summary['confirmation_rate']:.1%}")
    print(f"\nBy Verdict: {summary['by_verdict']}")
    print(f"By EDS Type: {summary['by_eds_type']}")
    print(f"By Symbol: {summary['by_symbol']}")
    print(f"Avg Expectancy (Confirmed): {summary['avg_expectancy_confirmed']:.3f}")
    print()

    # Example 9: Get run count with filters
    print("9. Getting Edge Run Count")
    count = db.get_edge_runs_count(symbol="EURUSD", edge_confirmed_only=True)
    print(f"Total confirmed edges for EURUSD: {count}")
    print()

    # Example 10: Delete an edge run
    print("10. Deleting Edge Run")
    # Create a test run first
    test_result = {
        "symbol": "GBPUSD",
        "timeframe": "M15",
        "eds_name": "EDS-0-Test",
        "config": {},
        "stats": {
            "n_trades": 10,
            "expectancy_r": -0.1,
            "win_rate": 0.4,
            "profit_factor": 0.8,
            "ci_low": -0.2,
            "ci_high": 0.1,
            "p_value_perm": 0.5,
        },
        "trades": [],
    }
    test_run_id = db.save_edge_result(test_result, save_trades=False)
    print(f"Created test run ID: {test_run_id}")

    deleted = db.delete_edge_run(test_run_id)
    print(f"Deleted: {deleted}")
    print()

    print("=== EdgeDiscoveryManager Examples Complete ===")


if __name__ == "__main__":
    main()
