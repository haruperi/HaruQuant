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



def example_01_data():
    print("\n" + "="*50)
    print("Example 01: Data Acquisition (via HaruQuant hqt)")
    print("="*50)

    # 1. Yahoo Finance
    print("\n--- 1. Yahoo Finance (hqt.YFData) ---")
    try:
        yf_data = hqt.YFData.download('BTC-USD', period='7d', interval='1d')
        print("Yahoo Finance BTC-USD:")
        print(yf_data.close.head())
    except Exception as e:
        print(f"YFData error: {e}")

    # 2. Binance
    print("\n--- 2. Binance (hqt.BinanceData) ---")
    try:
        # Binance needs public data, using short interval for demo
        binance_data = hqt.BinanceData.download('BTCUSDT', start='24 hours ago UTC', interval='1h')
        print("Binance BTCUSDT:")
        print(binance_data.close.head())
    except Exception as e:
        print(f"BinanceData error: {e}")

    # 3. CCXT
    print("\n--- 3. CCXT (hqt.CCXTData) ---")
    try:
        ccxt_data = hqt.CCXTData.download('BTC/USDT', exchange='binance', limit=5, timeframe='1h')
        print("CCXT Binance BTC/USDT:")
        print(ccxt_data.close.head())
    except Exception as e:
        print(f"CCXTData error: {e}")

    # 4. MT5
    print("\n--- 4. MT5 (hqt.MT5Data) ---")
    try:
        mt5_data = hqt.MT5Data.download(symbol="EURUSD", timeframe="D1", count=10)
        print("MT5 EURUSD:")
        print(mt5_data.close.head())
    except Exception as e:
        print(f"MT5 Data error: {e}")

    # 5. Dukascopy
    print("\n--- 5. Dukascopy (hqt.DukascopyData) ---")
    try:
        dukascopy_data = hqt.DukascopyData.download(symbol="EURUSD", timeframe="D1", count=10)
        print("Dukascopy EURUSD:")
        print(dukascopy_data.close.head())
    except Exception as e:
        print(f"Dukascopy Data error: {e}")

    # 6. Data Generation (GBM)
    print("\n--- 6. Geometric Brownian Motion (hqt.GBMData) ---")
    try:
        gbm_data = hqt.GBMData.generate(
            "SYNTHTIC",
            start='2020-01-01',
            end='2020-01-10',
            mu=0.0001,
            sigma=0.02,
            seed=42
        )
        print("GBM Data successfully generated:")
        print(gbm_data.df.head())
    except Exception as e:
        print(f"GBM Data error: {e}")

    # 7. Scheduled Data Updates
    print("\n--- 7. Scheduled Data Updates (hqt.ScheduledDataUpdater) ---")
    try:
        # Define a mock update function for demonstration
        def mt5_update_func(current_data):
            # In real scenario, this would call MT5Data.download with latest timestamps
            print("Requesting latest bars from MT5...")
            return hqt.MT5Data.download(symbol="EURUSD", timeframe="M1", count=1)

        print("Initializing MT5 Data for updates...")
        initial_data = hqt.MT5Data.download(symbol="EURUSD", timeframe="M1", count=5)
        updater = hqt.ScheduledDataUpdater(initial_data, mt5_update_func, interval_sec=5)
        
        # We run it once manually to demonstrate
        print("Running one manual update:")
        updater.update()
        
        print("\nNote: To run continuously, use updater.start()")
    except Exception as e:
        print(f"ScheduledDataUpdater error: {e}")

    # 9. Data Preparation and Splitting
    print("\n--- 9. Data Preparation and Splitting (hqt.DataSplitter) ---")
    try:
        index = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(10)]
        sr = pd.Series(np.arange(len(index)), index=index)
        
        splits = hqt.DataSplitter.rolling_split(
            sr,
            window_len=5, 
            set_lens=(3, 2), # 3 for train, 2 for test
            left_to_right=True
        )
        
        print(f"Successfully generated {len(splits)} rolling splits!")
        first_split = splits[0]
        print(f"First split - Train rows: {len(first_split['train'])}, Test rows: {len(first_split['test'])}")
        print("Train start:", first_split['train'].index[0])
        print("Test end:", first_split['test'].index[-1])

    except Exception as e:
        print(f"Rolling split error: {e}")

    # 10. Labeling for ML
    print("\n--- 10. Labeling for ML (hqt.Labeler) ---")
    try:
        print("Generating random price path and identifying local extrema...")
        # Using GBM for a more realistic price path
        price_data = hqt.GBMData.generate("BTC", start_value=100, mu=0, sigma=0.05, count=100)
        
        labels = hqt.Labeler.lexlb(price_data, up_threshold=0.05, down_threshold=0.05)
        print("Successfully generated local extrema labels for ML training!")
        
        peaks = labels[labels == 1]
        troughs = labels[labels == -1]
        print(f"Found {len(peaks)} peaks and {len(troughs)} troughs in 100 bars.")
        
    except Exception as e:
        print(f"Labeling for ML error: {e}")

def example_02_resample_data():
    print("\n\n" + "="*50)
    print("      EXAMPLE 02: DATA RESAMPLING & MULTI-TIMEFRAME      ")
    print("="*50)
    
    try:
        # 1. Download 5-minute data
        print("Downloading 5-minute data for EURUSD...")
        data_m5 = hqt.MT5Data.download("EURUSD", timeframe="M5", count=1000)
        print(f"Original M5 Data: {len(data_m5.df)} bars")
        
        # 2. Downsampling (M5 -> H1)
        print("\n--- 1. Downsampling (M5 -> H1) ---")
        # Simplified API: hqt.resample(data, rule)
        data_h1 = hqt.resample(data_m5, "H1")
        print(f"Downsampled H1 Data: {len(data_h1.df)} bars")
        print(data_h1.df.head())
        
        # 3. Merging Timeframes (M5 and H1)
        print("\n--- 2. Merging Timeframes (M5 + H1) ---")
        # Simplified API: hqt.merge(lower, higher)
        merged_data = hqt.merge(data_m5, data_h1, suffix="_H1")
        print(f"Merged Data Columns: {list(merged_data.df.columns)}")
        print(merged_data.df[['close', 'close_H1']].head(15))
        
        # 4. Concatenating different instruments (Same Timeframe)
        print("\n--- 3. Concatenating Instruments (EURUSD + GBPUSD) ---")
        print("Downloading GBPUSD H1 data...")
        # We'll use the same count as data_h1 for alignment in the example
        data_gbp_h1 = hqt.MT5Data.download("GBPUSD", timeframe="H1", count=len(data_h1.df))
        
        # Combine EURUSD (from data_h1) and GBPUSD into one MultiIndex Data object
        combined = hqt.concat([data_h1, data_gbp_h1], keys=['EURUSD', 'GBPUSD'])
        print(f"Combined MultiIndex Columns: {combined.df.columns}")
        # Accessing just the 'close' prices across both symbols
        if isinstance(combined.df.columns, pd.MultiIndex):
            print("\nClose prices for both symbols:")
            print(combined.df.xs('close', axis=1, level=1).head())
        
    except Exception as e:
        print(f"Resampling/Concat error: {e}")
        import traceback; traceback.print_exc()

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
    #example_01_data()
    example_02_resample_data()
    #example_03_indicators()
    #example_04_signals()
    #example_05_portfolio_random_signals()
    #example_06_portfolio_buy_and_hold()
    #example_07_portfolio_backtest()
