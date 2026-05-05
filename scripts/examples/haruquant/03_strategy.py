from datetime import datetime
import pandas as pd
import numpy as np

import haruquant as hqt

def example_01_strategy_signals():
    print("\n\n" + "="*50)
    print("        EXAMPLE 01: SIGNAL GENERATION (via hqt)        ")
    print("="*50)
    
    # 1. Strategy Signal Generation
    print("\n--- 1. Strategy Signal Generation (hqt.TrendFollowingStrategy) ---")
    try:
        # Download some data
        print("Downloading EURUSD H1 data...")
        data = hqt.MT5Data.download(symbol="EURUSD", timeframe="H1", count=200)
        
        # Instantiate strategy
        params = {
            'symbol': 'EURUSD',
            'fast_period': 20,
            'slow_period': 50,
            'filter_period': 200
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
        signal_points = df_signals[df_signals['entry_signal'] != 0]
        if not signal_points.empty:
            print("\nLatest Entry Signals:")
            print(signal_points[['close', 'entry_signal']].tail())
        else:
            print("\nNo entry signals found in this data range.")

    except Exception as e:
        print(f"Strategy Signal error: {e}")

def example_02_portfolio_random_signals():
    print("\n\n" + "="*50)
    print("      EXAMPLE 02: HARUQUANT RANDOM SIGNALS      ")
    print("="*50)
    
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
    print("\n\n" + "="*50)
    print("      EXAMPLE 03: HARUQUANT PORTFOLIO BUY AND HOLD     ")
    print("="*50)
    
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
    print("\n\n" + "="*50)
    print("      EXAMPLE 04: PORTFOLIO BACKTESTING (One-Line)     ")
    print("="*50)
    
    # 1. Run with 100% defaults
    print("\n--- 1. Running with 100% default configuration ---")
    portfolio = hqt.Portfolio.run()  # One-line execution encapsulating everything
    print(portfolio.summary())
    
    # 2. Run with partial overrides
    print("\n--- 2. Running with partial overrides ---")
    overrides = {
        "data": {
            "symbols": ["EURUSD"],
            "start": datetime(2020,1,1),
            "end": datetime(2020,12,31),
            "warmup_start": datetime(2019,10,1)
        },
        "strategy": {
            "params": {
                "fast_period": 10,
                "slow_period": 20
            }
        }
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
    #print(portfolio.result())
    #print(portfolio.result()["trades"])

    # Analytics data
    # dict_keys(['metrics', 'returns', 'ratios', 'risks', 'drawdowns', 'distributions', 'efficiency', 'benchmark', 'summary'])
    #print(portfolio.analytics())
    # print(portfolio.analytics()["returns"])
    #print(portfolio.analytics()["metrics"]["all"]["avg_loss"])

    # Print summary using the new internal summary() method
    #print(portfolio.summary())
    
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
    print("\n\n" + "="*50)
    print("      EXAMPLE 05: SIMULATION RANGES (Slicing)      ")
    print("="*50)
    
    try:
        print("Running full-year backtest for 2020...")
        overrides = {
            "data": {
                "symbols": ["EURUSD"],
                "start": datetime(2020,1,1),
                "end": datetime(2020,12,31),
                "warmup_start": datetime(2019,10,1)
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

if __name__ == "__main__":
    example_01_strategy_signals()
    example_02_portfolio_random_signals()
    example_03_portfolio_buy_and_hold()
    example_04_portfolio_backtest()
    example_05_simulation_ranges()
