
import pandas as pd
from datetime import datetime, timedelta



import haruquant as hqt

def example_01_native_indicators():
    print("\n" + "="*50)
    print("--- 1. Native HaruQuant Indicators (EMA, SMA) ---")
    print("="*50)
    
    # Generate some data
    data = hqt.GBMData.generate("BTC", start_value=100, count=100, seed=42)
    
    print("Computing 3 EMAs at once using hqt.ema.run(data, [20, 50, 200]):")
    # Native indicators return a DataFrame with indicator columns added
    df = hqt.ema.run(data, [20, 50, 200])
    print(f"Columns: {df.columns.tolist()}")
    print(df[['ema_20', 'ema_50', 'ema_200']].tail())

def example_02_indicator_chaining():
    print("\n" + "="*50)
    print("--- 2. Multi-Indicator Chaining ---")
    print("="*50)
    
    data = hqt.GBMData.generate("ETH", start_value=2000, count=100, seed=123)
    
    # You can pass the result of one indicator to another
    df = hqt.sma.run(data, [10, 20])
    df = hqt.rsi.run(df, 14)
    df = hqt.bbands.run(df, 20)
    
    print("Columns after chaining SMA, RSI, and BBands:")
    print(df.columns.tolist())
    print("\nSample RSI and Bollinger Bands (Lower) values:")
    # Note: Column names for bbands are bb_lower_{period}_{std_dev}
    print(df[['rsi_14', 'bb_lower_20_2']].tail())

def example_03_pandas_ta_integration():
    print("\n" + "="*50)
    print("--- 3. Pandas TA Integration (hqt.ta) ---")
    print("="*50)
    
    try:
        data = hqt.GBMData.generate("SOL", start_value=50, count=100, seed=789)
        
        # hqt.ta provides a wrapper for common pandas_ta indicators
        # It handles conversion from hqt.Data/DataFrame to pandas_ta format automatically
        df_ta = hqt.ta.rsi(data, [14, 21])
        print("Pandas TA RSI columns added:")
        print([c for c in df_ta.columns if 'rsi' in c.lower()])
        
        # You can also use other indicators via hqt.ta
        df_macd = hqt.ta.macd(data)
        print("\nMACD columns:")
        print([c for c in df_macd.columns if 'macd' in c.lower()])
        
    except Exception as e:
        print(f"Pandas TA error: {e}")

def example_04_hurst_exponent():
    print("\n" + "="*50)
    print("--- 4. Hurst Exponent (Statistical) ---")
    print("="*50)
    
    # Generate random walk vs trending data
    print("Generating random walk data...")
    data_random = hqt.GBMData.generate("RAND", start_value=100, count=500, seed=42)
    
    print("Calculating Hurst exponent (window=100)...")
    # H < 0.5: Mean-reverting
    # H = 0.5: Random walk
    # H > 0.5: Trending
    df = hqt.hurst.run(data_random, 100)
    
    print("\nLast 10 Hurst exponent values:")
    print(df['hurst_100'].tail(10))
    
    avg_hurst = df['hurst_100'].mean()
    print(f"\nAverage Hurst: {avg_hurst:.4f}")
    
    if avg_hurst > 0.55:
        print("Market state: Trending (Persistent)")
    elif avg_hurst < 0.45:
        print("Market state: Mean-reverting (Anti-persistent)")
    else:
        print("Market state: Random Walk")

def example_05_smc_indicators():
    print("\n" + "="*50)
    print("--- 5. Smart Money Concepts (SMC) ---")
    print("="*50)
    
    try:
        # Download real data for SMC as it needs OHLC
        print("Downloading H1 data for EURUSD...")
        data = hqt.MT5Data.download("EURUSD", timeframe="H1", count=200)
        
        # 1. Fair Value Gap (FVG)
        print("\n--- 1. Fair Value Gap (FVG) ---")
        # hqt.fvg returns original data + FVG columns (fvg, fvg_top, fvg_bottom)
        df_fvg = hqt.fvg.run(data, period=0) # FVG doesn't use period, but run needs it
        print(f"FVG columns added: {[c for c in df_fvg.columns if 'fvg' in c]}")
        print(df_fvg[df_fvg['fvg'].notna()][['fvg', 'fvg_top', 'fvg_bottom']].tail())
        
        # 2. Order Blocks (OB)
        print("\n--- 2. Order Blocks (OB) ---")
        # period here maps to swing_length
        df_ob = hqt.ob.run(data, period=20) 
        print(f"OB columns added: {[c for c in df_ob.columns if 'ob' in c]}")
        print(df_ob[df_ob['ob'].notna()][['ob', 'ob_top', 'ob_bottom']].tail())
        
        # 3. Break of Structure (BOS) / Change of Character (CHOCH)
        print("\n--- 3. BOS & CHOCH ---")
        df_structure = hqt.bos_choch.run(data, period=20)
        print(f"Structure columns: {[c for c in df_structure.columns if 'bos' in c or 'choch' in c]}")
        print(df_structure[df_structure['bos'].notna() | df_structure['choch'].notna()][['bos', 'choch', 'structure_level']].tail())
        
        # 4. Previous High/Low (PHL)
        print("\n--- 4. Previous High/Low (1D) ---")
        # period here maps to timeframe string
        df_phl = hqt.phl.run(data, period="1D")
        print(f"PHL columns: {[c for c in df_phl.columns if 'previous' in c]}")
        print(df_phl[['previous_high', 'previous_low', 'broken_high', 'broken_low']].tail())
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"SMC Error: {e}")

def example_06_indicator_search():
    print("\n" + "="*50)
    print("--- 6. Indicator Search & Discovery ---")
    print("="*50)
    
    # List all available moving average indicators
    print("Searching for '*ma' indicators:")
    ma_indicators = hqt.list_indicators("*ma")
    print(ma_indicators)
    
    # Search for SMC related indicators
    print("\nSearching for structure-related indicators ('*bos*', '*ob*'):")
    structure_inds = hqt.list_indicators("*bos*") + hqt.list_indicators("*ob*")
    print(structure_inds)
    
    # Access an indicator dynamically
    print("\nAccessing 'ema' dynamically via hqt.indicator('ema'):")
    ema_ind = hqt.indicator("ema")
    print(f"Indicator object: {ema_ind}")
    
    # Access a pandas_ta indicator dynamically
    print("\nAccessing 'rsi' from pandas_ta via hqt.indicator('ta:rsi'):")
    try:
        ta_rsi = hqt.indicator("ta:rsi")
        print(f"Pandas TA Indicator: {ta_rsi}")
    except Exception as e:
        print(f"Error: {e}")

def example_07_indicators_for_ml():
    print("\n" + "="*50)
    print("--- 7. Indicators for Machine Learning ---")
    print("="*50)
    
    try:
        # Fetch some data
        data = hqt.MT5Data.download("EURUSD", timeframe="H1", count=100)
        
        # Run all native indicators at once (EMA, SMA, RSI, BBands, ATR, Hurst)
        print("Running all native indicators...")
        features_native = hqt.run_indicators(data, "native", period=20)
        print(f"Native features shape: {features_native.shape}")
        print(f"Columns: {features_native.columns.tolist()[-10:]}") # show last 10
        
        # Run all SMC indicators
        print("\nRunning all SMC indicators...")
        features_smc = hqt.run_indicators(data, "smc", period=20)
        print(f"SMC features shape: {features_smc.shape}")
        
        # Run a specific subset of indicators using a pattern
        print("\nRunning all 'ma' indicators...")
        features_ma = hqt.run_indicators(data, "*ma", period=20)
        print(f"MA features columns: {[c for c in features_ma.columns if 'ma' in c]}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ML Features Error: {e}")

def example_08_parallel_indicators():
    print("\n" + "="*50)
    print("--- 8. Parallel Indicator Execution ---")
    print("="*50)
    
    import time
    import numpy as np
    
    try:
        # Fetch data
        data = hqt.MT5Data.download("EURUSD", timeframe="M1", count=1000)
        
        # We want to run EMA for many periods (e.g., 2 to 50)
        periods = list(range(2, 51))
        
        # 1. Serial Execution
        start_serial = time.time()
        res_serial = hqt.ema.run(data, period=periods, engine="serial")
        end_serial = time.time()
        print(f"Serial execution time (50 periods): {end_serial - start_serial:.4f}s")
        
        # 2. Parallel Execution (ThreadPool)
        start_parallel = time.time()
        res_parallel = hqt.ema.run(data, period=periods, engine="threadpool", n_workers=4)
        end_parallel = time.time()
        print(f"Parallel execution time (ThreadPool, 4 workers): {end_parallel - start_parallel:.4f}s")
        
        print(f"Results shape: {res_parallel.shape}")
        
        # Verify columns
        ema_cols = [c for c in res_parallel.columns if "ema" in c]
        print(f"Number of EMA columns: {len(ema_cols)}")
        print(f"First 5 EMA columns: {ema_cols[:5]}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Parallel Execution Error: {e}")

if __name__ == "__main__":
    example_01_native_indicators()
    example_02_indicator_chaining()
    example_03_pandas_ta_integration()
    example_04_hurst_exponent()
    example_05_smc_indicators()
    example_06_indicator_search()
    example_07_indicators_for_ml()
    example_08_parallel_indicators()
