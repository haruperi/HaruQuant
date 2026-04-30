'''
This is the adaptation of the original vectorbt basic and pro feature examples to work with HaruQuant.

The original vectorbt examples can be found here:
https://vectorbt.dev/
https://vectorbt.pro/
https://qubitquants.github.io/index.html

'''

import os
import sys
from datetime import datetime, timedelta
import time
import numpy as np
import pandas as pd

# Add project root to sys.path to allow importing haruquant
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import haruquant as hqt




def example_03_indicators():
    print("\n\n" + "="*50)
    print("      EXAMPLE 03: TECHNICAL INDICATORS (via hqt)      ")
    print("="*50)
    
    # Generate some data
    data = hqt.GBMData.generate("BTC", start_value=100, count=100, seed=42)
    
    print("\n--- 1. Native HaruQuant Indicators (hqt.ema, hqt.sma) ---")
    print("Computing 3 EMAs at once using hqt.ema.run(data, [20, 50, 200]):")
    data_with_ema = hqt.ema.run(data, [20, 50, 200])
    print(data_with_ema.columns)
    print(data_with_ema[['ema_20', 'ema_50', 'ema_200']].tail())
    
    print("\n--- 2. Multi-Indicator chaining ---")
    df = hqt.sma.run(data_with_ema, [10, 20])
    df = hqt.rsi.run(df, 14)
    print("Columns after chaining SMA and RSI:")
    print(df.columns)
    
    print("\n--- 3. Bollinger Bands (hqt.bbands) ---")
    df_bb = hqt.bbands.run(data, 20)
    print("Bollinger Bands columns:")
    # BBands usually adds bbands_upper_20, bbands_lower_20, etc.
    print([c for c in df_bb.columns if 'bbands' in c])

    print("\n--- 4. Pandas TA integration (hqt.ta) ---")
    try:
        # Using hqt.ta wrapper for pandas_ta
        df_ta = hqt.ta.rsi(data, [14, 21])
        print("Pandas TA RSI columns:")
        print([c for c in df_ta.columns if 'rsi' in c.lower()])
    except Exception as e:
        print(f"Pandas TA error: {e}")

def example_04_signals():
    print("\n\n" + "="*50)
    print("        EXAMPLE 04: SIGNAL GENERATION (via hqt)        ")
    print("="*50)
    
    # 1. Strategy Signal Generation
    print("\n--- 1. Strategy Signal Generation (hqt.TrendFollowingStrategy) ---")
    try:
        # Download some data
        data = hqt.MT5Data.download(symbol="EURUSD", timeframe="H1", count=200)
        
        # Instantiate strategy
        params = {
            'symbol': 'EURUSD',
            'fast_period': 20,
            'slow_period': 50,
            'filter_period': 200
        }
        trend_naive = hqt.TrendFollowingStrategy(params)
        
        # Run on_bar to get signals
        df_signals = trend_naive.run(data)
        
        print(f"Strategy run complete. Data columns: {df_signals.columns}")
        
        # Access signals directly
        entries = trend_naive.entries
        exits = trend_naive.exits
        
        print("\nEntries Summary:")
        print(entries.value_counts())
        
        print("\nExits Summary:")
        print(exits.value_counts())
        
        # Show some signal points
        signal_points = df_signals[df_signals['entry_signal'] != 0]
        if not signal_points.empty:
            print("\nLatest Entry Signals:")
            print(signal_points[['close', 'entry_signal']].tail())
        else:
            print("\nNo entry signals found in this data range.")

    except Exception as e:
        print(f"Strategy Signal error: {e}")

    # 2. Measurement utilities (Partition analysis)
    print("\n--- 2. Signal Partition Analysis ---")
    try:
        mask_sr = pd.Series([True, True, True, False, True, True])
        # We can implement signal utilities in hqt.signals later if needed
        # For now showing standard pandas way or keep vbt if user wants to compare
        print(f"Mask values: {mask_sr.values}")
        print("This mimics VectorBT's measurement of signal durations.")
    except Exception as e:
        print(f"Signal Analysis error: {e}")

def example_05_portfolio_random_signals():
    print("\n\n" + "="*50)
    print("      EXAMPLE 05: HARUQUANT RANDOM SIGNALS      ")
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
        import traceback; traceback.print_exc()

def example_06_portfolio_buy_and_hold():
    print("\n\n" + "="*50)
    print("      EXAMPLE 06: HARUQUANT PORTFOLIO BUY AND HOLD     ")
    print("="*50)
    
    try:
        print("Downloading BTC-USD data via YFData...")
        data = hqt.YFData.download("BTC-USD", period="1y")
        price = data.close
        
        print("\nBacktesting 1-year Buy & Hold on BTC-USD with $100...")
        pf = hqt.Portfolio.from_holding(price, init_cash=100)
        
        print(f"Initial Cash: $100.00")
        print(f"Final Profit: ${pf.total_profit():.2f}")
        print(f"Total Return: {pf.total_return():.2f}%")
        
    except Exception as e:
        print(f"Portfolio from holding error: {e}")
        import traceback; traceback.print_exc()

def example_07_portfolio_backtest():
    print("\n\n" + "="*50)
    print("      EXAMPLE 07: PORTFOLIO BACKTESTING     ")
    print("="*50)
    
    # 1. Run with 100% defaults
    print("\n--- 1. Running with 100% default configuration ---")
    portfolio = hqt.Portfolio.run()  # One-line execution encapsulating everything
    # print(f"Default Return: {portfolio.total_return():.2f}%")
    print(portfolio.summary())
    
    # 2. Run with partial overrides
    print("\n--- 2. Running with partial overrides (Change Symbol & Period) ---")
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




if __name__ == "__main__":
    example_02_resample_data()
    #example_03_indicators()
    #example_04_signals()
    #example_05_portfolio_random_signals()
    #example_06_portfolio_buy_and_hold()
    #example_07_portfolio_backtest()
