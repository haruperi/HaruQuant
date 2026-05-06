from datetime import datetime

import haruquant as hqt


def _print_backtest_trades(portfolio, limit=12):
    trades = list(getattr(portfolio, "trades", []) or [])
    print(f"\nTrades: showing first {min(len(trades), limit)} of {len(trades)}")
    for index, trade in enumerate(trades[:limit], start=1):
        side = getattr(trade, "side", getattr(trade, "type", ""))
        size = getattr(trade, "size", getattr(trade, "volume", ""))
        pnl = getattr(
            trade,
            "profit_loss",
            getattr(trade, "profit", getattr(trade, "pnl", "")),
        )
        close_type = getattr(trade, "close_type", "")
        print(
            f"trade[{index}] ticket={getattr(trade, 'ticket', '')} "
            f"symbol={getattr(trade, 'symbol', '')} side={side} "
            f"size={size} pnl={pnl} close_type={close_type}"
        )


def _run_stateful_strategy_backtest(
    strategy_name,
    params,
    *,
    timeframe="H1",
    start=datetime(2025, 1, 2),
    end=datetime(2025, 3, 31, 23),
    warmup_start=datetime(2024, 12, 1),
):
    overrides = {
        "engine_type": "event_driven",
        "backend": "sim",
        "account": {
            "initial_balance": 10000.0,
            "commission": 0.0,
        },
        "data": {
            "source": "metatrader",
            "symbols": ["EURUSD"],
            "timeframe": timeframe,
            "start": start,
            "end": end,
            "warmup_start": warmup_start,
        },
        "strategy": {
            "name": strategy_name,
            "params": {
                "symbol": "EURUSD",
                **params,
            },
        },
        "execution": {
            "tick_model": "timeframe_ticks",
            "spread_model": "fixed_spread",
            "spread_points": 2.0,
            "position_size": {
                "type": "fixed_lot",
                "lot_size": 0.1,
            },
        },
        "risk_controls": {
            "enabled": True,
            "max_open_positions_per_strategy": 20,
            "max_layers_per_setup": 6,
            "max_martingale_step": 6,
            "max_total_lots": 5.0,
            "max_symbol_exposure": 3.0,
            "max_strategy_drawdown": 1000.0,
            "allow_multiple_action_batches_per_event": False,
        },
    }

    print("Running {0} on MT5 EURUSD {1} data...".format(strategy_name, timeframe))
    portfolio = hqt.Portfolio.run(overrides)
    print(portfolio.summary())
    _print_backtest_trades(portfolio)
    return portfolio


def example_01_strategy_signals():
    print("\n\n" + "=" * 50)
    print("        EXAMPLE 01: SIGNAL GENERATION (via hqt)        ")
    print("=" * 50)

    # 1. Strategy Signal Generation
    print("\n--- 1. Strategy Signal Generation (hqt.TrendFollowingStrategy) ---")
    try:
        # Download some data
        print("Downloading EURUSD H1 data...")
        data = hqt.MT5Data.download(symbol="EURUSD", timeframe="H1", count=200)

        # Instantiate strategy
        params = {
            "symbol": "EURUSD",
            "fast_period": 20,
            "slow_period": 50,
            "filter_period": 200,
        }
        trend_naive = hqt.TrendFollowingStrategy(params)

        # Run strategy to get signals
        df_signals = trend_naive.run(data)

        print(f"Strategy run complete. Data columns: {df_signals.columns.tolist()}")

        # Access signals directly
        entries = trend_naive.entries
        exits = trend_naive.exits

        print("\nEntries Summary:")
        print(entries.value_counts())

        # Show some signal points
        signal_points = df_signals[df_signals["entry_signal"] != 0]
        if not signal_points.empty:
            print("\nLatest Entry Signals:")
            print(signal_points[["close", "entry_signal"]].tail())
        else:
            print("\nNo entry signals found in this data range.")

    except Exception as e:
        print(f"Strategy Signal error: {e}")


def example_02_portfolio_random_signals():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 02: HARUQUANT RANDOM SIGNALS      ")
    print("=" * 50)

    try:
        print("Downloading BTC-USD data...")
        data = hqt.YFData.download("BTC-USD", period="1mo")

        print("\nRunning random backtest (10 signals) on BTC-USD...")
        pf = hqt.Portfolio.from_random_signals(data.close, n=10, seed=42)

        print(pf.summary())
        print("\nGenerated Random Trades:")
        pf.print_trades()

    except Exception as e:
        print(f"Random signals error: {e}")


def example_03_portfolio_buy_and_hold():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 03: HARUQUANT PORTFOLIO BUY AND HOLD     ")
    print("=" * 50)

    try:
        print("Downloading BTC-USD data...")
        data = hqt.YFData.download("BTC-USD", period="1y")
        price = data.close

        print("\nBacktesting 1-year Buy & Hold on BTC-USD with $100...")
        pf = hqt.Portfolio.from_holding(price, init_cash=100)

        print(f"Initial Cash: $100.00")
        print(f"Final Profit: ${pf.total_profit():.2f}")
        print(f"Total Return: {pf.total_return():.2f}%")

    except Exception as e:
        print(f"Portfolio from holding error: {e}")


def example_04_portfolio_backtest():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 04: PORTFOLIO BACKTESTING (One-Line)     ")
    print("=" * 50)

    # 1. Run with 100% defaults
    print("\n--- 1. Running with 100% default configuration ---")
    portfolio = hqt.Portfolio.run()  # One-line execution encapsulating everything
    print(portfolio.summary())

    # 2. Run with partial overrides
    print("\n--- 2. Running with partial overrides ---")
    overrides = {
        "data": {
            "symbols": ["EURUSD"],
            "start": datetime(2020, 1, 1),
            "end": datetime(2020, 12, 31),
            "warmup_start": datetime(2019, 10, 1),
        },
        "strategy": {"params": {"fast_period": 10, "slow_period": 20}},
    }

    portfolio = hqt.Portfolio.run(overrides)
    print(portfolio.summary())

    # Metadata
    # dict_keys(['engine_type', 'account', 'data', 'strategy', 'execution', 'reporting', 'prepared', 'warnings'])

    # 'processed_ticks', 'trade_count', 'equity_points', 'final_balance', 'final_equity', '', '', ''])
    # print(portfolio.metadata())
    # print(portfolio.metadata()["reporting"])    # Get a specific attribute from the config dictionary

    # Prepared Data
    # dict_keys(['ticks', 'signal_bars_by_symbol', 'tick_counts_by_symbol', 'metadata'])
    # print(portfolio.prepared())
    # print(portfolio.prepared()["ticks"])

    # Result Data
    # dict_keys(['trades', 'equity_curve'])
    # print(portfolio.result())
    # print(portfolio.result()["trades"])

    # Analytics data
    # dict_keys(['metrics', 'returns', 'ratios', 'risks', 'drawdowns', 'distributions', 'efficiency', 'benchmark', 'summary'])
    # print(portfolio.analytics())
    # print(portfolio.analytics()["returns"])
    # print(portfolio.analytics()["metrics"]["all"]["avg_loss"])

    # Print summary using the new internal summary() method
    # print(portfolio.summary())

    # Demonstrate new helper functions
    # print("\n--- Detailed Trade List ---")
    # portfolio.print_trades()

    # print("\n--- Equity Curve (First 5 Points) ---")
    # Access raw curve if needed or use print helper
    # print(f"Total equity points: {len(portfolio.equity_curve)}")
    # # We'll just show the first few to avoid flooding the console
    # for p in portfolio.equity_curve[:5]:
    #     print(f"{p.timestamp}: {p.equity:.2f}")


def example_05_simulation_ranges():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 05: SIMULATION RANGES (Slicing)      ")
    print("=" * 50)

    try:
        print("Running full-year backtest for 2020...")
        overrides = {
            "data": {
                "symbols": ["EURUSD"],
                "start": datetime(2020, 1, 1),
                "end": datetime(2020, 12, 31),
                "warmup_start": datetime(2019, 10, 1),
            }
        }
        pf_full = hqt.Portfolio.run(overrides)
        print(f"Full Year Return: {pf_full.total_return():.2f}%")

        # Now slice for Q1 2020 only
        print("\nSlicing for Q1 2020 (Jan 1 to Mar 31)...")
        pf_q1 = pf_full.slice(start="2020-01-01", end="2020-03-31")

        print("Q1 Summary:")
        print(pf_q1.summary())

        # Slice for a specific month
        print("\nSlicing for December 2020...")
        pf_dec = pf_full.slice(start="2020-12-01", end="2020-12-31")
        print(f"December Profit: ${pf_dec.total_profit():.2f}")
        print(f"December Trades: {len(pf_dec.trades)}")

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Simulation Range Error: {e}")


def example_06_rsi_martingale_strategy():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 06: STATEFUL RSI MARTINGALE      ")
    print("=" * 50)

    _run_stateful_strategy_backtest(
        "RsiMartingaleStrategy",
        {
            "rsi_period": 3,
            "rsi_oversold": 45,
            "rsi_overbought": 55,
            "initial_lot": 0.1,
            "multiplier": 1.5,
            "min_step_pips": 5,
            "target_profit_usd": 3.0,
            "max_lot": 1.0,
            "max_steps": 6,
            # Optional strategy-local override. These merge over the top-level
            # risk_controls block for this strategy only.
            "risk_controls": {
                "max_martingale_step": 6,
                "max_total_lots": 3.0,
                "max_symbol_exposure": 2.0,
            },
        },
    )


def example_07_pyramiding_strategy():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 07: STATEFUL PYRAMIDING      ")
    print("=" * 50)

    _run_stateful_strategy_backtest(
        "PyramidingStrategy",
        {
            "fast_ma_period": 3,
            "slow_ma_period": 8,
            "initial_lot": 0.1,
            "lot_divisor": 2.0,
            "min_step_pips": 5,
            "trailing_sl_pips": 3,
            "max_positions_per_side": 4,
            "risk_controls": {
                "max_layers_per_setup": 4,
                "max_open_positions_per_strategy": 8,
                "max_total_lots": 2.0,
            },
        },
    )


def example_08_trade_decomposition_strategy():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 08: STATEFUL TRADE DECOMPOSITION      ")
    print("=" * 50)

    _run_stateful_strategy_backtest(
        "TradeDecompositionStrategy",
        {
            "rsi_period": 3,
            "os_level": 45,
            "ob_level": 55,
            "initial_lot": 0.06,
            "vol_increase": 0.06,
            "vol_decrease": 0.02,
            "trade_distance": 5,
            "trail_points": 5,
            "risk_controls": {
                "max_layers_per_setup": 50,
                "max_open_positions_per_strategy": 100,
                "max_total_lots": 20.0,
                "max_symbol_exposure": 20.0,
                "max_strategy_drawdown": None,
            },
        },
    )


def example_09_rsi_averaging_pyramid_strategy():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 09: STATEFUL RSI AVERAGING PYRAMID      ")
    print("=" * 50)

    _run_stateful_strategy_backtest(
        "RsiAveragingPyramidStrategy",
        {
            "rsi_period": 3,
            "os_level": 45,
            "ob_level": 55,
            "balance_increase": 2000.0,
            "volume_increase": 0.01,
            "initial_lot": 0.01,
            "min_lot": 0.01,
            "max_lot": 0.5,
            "cost_averaging_distance_pips": 5,
            "pyramiding_distance_pips": 5,
            "lot_divisor": 2.0,
            "sl_displacement_pips": 3,
            "risk_controls": {
                "max_layers_per_setup": 12,
                "max_open_positions_per_strategy": 24,
                "max_total_lots": 3.0,
                "max_symbol_exposure": 2.0,
                "max_strategy_drawdown": 1500.0,
            },
        },
    )


def example_10_structure_hedge_trail_strategy():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 10: STATEFUL STRUCTURE HEDGE TRAIL      ")
    print("=" * 50)

    _run_stateful_strategy_backtest(
        "StructureHedgeTrailStrategy",
        {
            "higher_timeframe": "H1",
            "lower_timeframe": "M5",
            "ht_min_distance_pips": 5,
            "lt_min_distance_pips": 2,
            "take_profit_pips": 30,
            "stop_loss_pips": 5,
            "when_to_trail_pips": 10,
            "balance_increase": 3000.0,
            "volume_increase": 0.01,
            "initial_lot": 0.01,
            "min_lot": 0.01,
            "max_lot": 0.5,
            "risk_controls": {
                "max_layers_per_setup": 4,
                "max_open_positions_per_strategy": 12,
                "max_total_lots": 2.0,
                "max_symbol_exposure": 1.5,
                "max_strategy_drawdown": 1000.0,
            },
        },
        timeframe="M5",
        start=datetime(2025, 1, 2),
        end=datetime(2025, 1, 31, 23),
        warmup_start=datetime(2024, 12, 15),
    )


def example_11_rsi_decomposing_reentry_strategy():
    print("\n\n" + "=" * 50)
    print("      EXAMPLE 11: STATEFUL RSI DECOMPOSING REENTRY      ")
    print("=" * 50)

    _run_stateful_strategy_backtest(
        "RsiDecomposingReentryStrategy",
        {
            "rsi_period": 3,
            "os_level": 45,
            "ob_level": 55,
            "balance_increase": 3000.0,
            "volume_increase": 0.01,
            "volume_decrease": 0.005,
            "when_to_trail_pips": 2,
            "trail_by_pips": 1,
            "trade_distance_pips": 3,
            "initial_lot": 0.01,
            "min_lot": 0.01,
            "max_lot": 0.5,
            "lot_step": 0.01,
            "risk_controls": {
                "max_layers_per_setup": 20,
                "max_open_positions_per_strategy": 40,
                "max_total_lots": 10.0,
                "max_symbol_exposure": 8.0,
                "max_strategy_drawdown": 1500.0,
            },
        },
        timeframe="M5",
        start=datetime(2025, 1, 2),
        end=datetime(2025, 1, 31, 23),
        warmup_start=datetime(2024, 12, 15),
    )


if __name__ == "__main__":
    # example_01_strategy_signals()
    # example_02_portfolio_random_signals()
    # example_03_portfolio_buy_and_hold()
    # example_04_portfolio_backtest()
    # example_05_simulation_ranges()
    # example_06_rsi_martingale_strategy()
    # example_07_pyramiding_strategy()
    # example_08_trade_decomposition_strategy()
    example_09_rsi_averaging_pyramid_strategy()
    example_10_structure_hedge_trail_strategy()
    example_11_rsi_decomposing_reentry_strategy()
