"""Usage examples for SQXManager module."""

import pandas as pd
from apps.sqlite import SQLiteDatabase


def main():
    """Demonstrate SQXManager usage."""
    # Initialize database
    db = SQLiteDatabase(db_path="data/database/haruquant.db")
    db.initialize_database()

    print("=== SQXManager Usage Examples ===\n")

    # Example 1: Merge SQX export with column mapping
    print("1. Merging SQX Export Data")

    # Sample SQX export data (simulating CSV from StrategyQuant X)
    sqx_data = pd.DataFrame(
        {
            "Strategy Name": ["MA_Cross_v1", "BB_Reversal_v2", "RSI_Trend_v1"],
            "Symbol (IS)": ["EURUSD", "GBPUSD", "USDJPY"],
            "TimeFrame (IS)": ["H1", "M15", "H4"],
            "Profit Factor (IS)": [1.85, 2.10, 1.65],
            "Net Profit (IS)": [12500.0, 8750.0, 15200.0],
            "# Trades (IS)": [150, 220, 95],
            "Max DD % (IS)": [12.5, 8.3, 15.2],
            "Annual Return % (IS)": [45.2, 38.5, 52.1],
            "Avg Win %": [62.5, 58.3, 65.0],
        }
    )

    # Define column mapping (canonical -> CSV column names)
    column_mapping = {
        "strategy_name": "Strategy Name",
        "symbol": "Symbol (IS)",
        "timeframe": "TimeFrame (IS)",
        "profit_factor": "Profit Factor (IS)",
        "net_profit": "Net Profit (IS)",
        "trades": "# Trades (IS)",
        "max_drawdown_pct": "Max DD % (IS)",
        "annual_return_pct": "Annual Return % (IS)",
        "win_percent": "Avg Win %",
    }

    # Merge the data into the database
    rows_merged = db.merge_sqx_export(
        df=sqx_data,
        mapping=column_mapping,
        stage="CORE",
        import_name="initial_import_2024_01",
        purge_missing=False,
    )

    print(f"Merged {rows_merged} strategies into sqx_strategy_edge table")
    print()

    # Example 2: Merge with stage-specific metrics
    print("2. Merging Stage-Specific Data (A1_OOS2)")

    # A1 stage data with out-of-sample metrics
    a1_data = pd.DataFrame(
        {
            "Strategy Name": ["MA_Cross_v1", "BB_Reversal_v2"],
            "Symbol": ["EURUSD", "GBPUSD"],
            "TimeFrame": ["H1", "M15"],
            "Profit Factor (OOS2)": [1.65, 1.95],
            "Net Profit (OOS2)": [9500.0, 7200.0],
            "# Trades (OOS2)": [75, 110],
            "Max DD % (OOS2)": [14.2, 9.5],
            "Annual Return % (OOS2)": [38.5, 32.1],
            "Ret/DD": [2.71, 3.38],
        }
    )

    a1_mapping = {
        "strategy_name": "Strategy Name",
        "symbol": "Symbol",
        "timeframe": "TimeFrame",
        "profit_factor": "Profit Factor (OOS2)",
        "net_profit": "Net Profit (OOS2)",
        "trades": "# Trades (OOS2)",
        "max_drawdown_pct": "Max DD % (OOS2)",
        "annual_return_pct": "Annual Return % (OOS2)",
        "ret_dd_ratio": "Ret/DD",
    }

    rows_merged = db.merge_sqx_export(
        df=a1_data,
        mapping=a1_mapping,
        stage="A1_OOS2",
        import_name="a1_stage_2024_01",
        purge_missing=False,
    )

    print(
        f"Merged {rows_merged} A1 strategies (stage-specific metrics will have 'a1_' prefix)"
    )
    print()

    # Example 3: Retrieve SQX strategies
    print("3. Retrieving SQX Strategies")
    strategies = db.get_sqx_strategies(symbol="EURUSD")
    print(f"Found {len(strategies)} strategies for EURUSD")
    for strat in strategies[:3]:
        print(f"\n  Strategy: {strat['strategy_name']}")
        print(f"    Symbol: {strat['symbol']}")
        print(f"    Timeframe: {strat['timeframe']}")
        print(f"    Profit Factor: {strat.get('profit_factor', 'N/A')}")
        print(f"    Annual Return %: {strat.get('annual_return_pct', 'N/A')}")
        if strat.get("a1_profit_factor"):
            print(f"    A1 Profit Factor: {strat['a1_profit_factor']}")
    print()

    # Example 4: Update strategy scores
    print("4. Updating Strategy Scores")

    # Calculate custom scores for strategies
    score_data = pd.DataFrame(
        {
            "strategy_name": ["MA_Cross_v1", "BB_Reversal_v2", "RSI_Trend_v1"],
            "edge_score": [0.85, 0.92, 0.78],
            "robust_score": [0.75, 0.88, 0.70],
            "stability_score": [0.80, 0.85, 0.72],
            "risk_score": [0.70, 0.82, 0.65],
            "simple_score": [0.90, 0.75, 0.88],
            "fragility_penalty": [0.05, 0.03, 0.08],
            "base_score_0_1": [0.77, 0.84, 0.71],
            "final_score": [0.732, 0.813, 0.656],
            "rank_in_symbol": [2, 1, 3],
            "rejected": [False, False, False],
        }
    )

    updated_count = db.update_strategy_scores(score_data)
    print(f"Updated scores for {updated_count} strategies")
    print()

    # Example 5: Verify updated scores
    print("5. Verifying Updated Scores")
    strategies = db.get_sqx_strategies()
    for strat in strategies[:3]:
        if strat.get("final_score"):
            print(f"\n  {strat['strategy_name']}:")
            print(f"    Edge Score: {strat.get('edge_score', 'N/A')}")
            print(f"    Robust Score: {strat.get('robust_score', 'N/A')}")
            print(f"    Final Score: {strat.get('final_score', 'N/A')}")
            print(f"    Rank in Symbol: {strat.get('rank_in_symbol', 'N/A')}")
            print(f"    Rejected: {strat.get('rejected', False)}")
    print()

    # Example 6: Merge with purge_missing flag
    print("6. Merging with Purge Missing Strategies")

    # New data with only 2 strategies (simulating removed strategies)
    purge_data = pd.DataFrame(
        {
            "Strategy Name": ["MA_Cross_v1", "BB_Reversal_v2"],
            "Symbol": ["EURUSD", "GBPUSD"],
            "TimeFrame": ["H1", "M15"],
            "Profit Factor": [1.90, 2.15],
            "Net Profit": [13000.0, 9000.0],
        }
    )

    purge_mapping = {
        "strategy_name": "Strategy Name",
        "symbol": "Symbol",
        "timeframe": "TimeFrame",
        "profit_factor": "Profit Factor",
        "net_profit": "Net Profit",
    }

    # This will remove strategies not in this import for the same symbols
    rows_merged = db.merge_sqx_export(
        df=purge_data,
        mapping=purge_mapping,
        stage="UPDATE",
        import_name="purge_test_2024_01",
        purge_missing=True,
    )

    print(
        f"Merged {rows_merged} strategies (purge_missing=True removes strategies not in this import)"
    )
    print()

    # Example 7: Symbol canonicalization
    print("7. Symbol Canonicalization")
    print("SQXManager automatically canonicalizes symbols:")
    print("  EURUSD_dukascopy -> EURUSD")
    print("  GBPUSD_oanda -> GBPUSD")
    print("  USDJPY_fxcm_suffix -> USDJPY")
    print()

    # Example 8: Win percent normalization
    print("8. Win Percent Normalization")
    print("SQXManager automatically normalizes win_percent:")
    print("  If median > 1.0 (e.g., 62.5), converts to 0-1 scale (0.625)")
    print("  If already 0-1 scale (e.g., 0.625), leaves unchanged")
    print()

    print("=== SQXManager Examples Complete ===")


if __name__ == "__main__":
    main()
