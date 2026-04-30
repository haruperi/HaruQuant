"""
Example 01: Data Acquisition (via HaruQuant hqt)
"""

import os
import sys
from datetime import datetime, timedelta
import time
import numpy as np
import pandas as pd
from pathlib import Path

# Add project root to sys.path to allow importing haruquant
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import haruquant as hqt

def example_01_yahoo():
    print("\n" + "="*50)
    print("--- 1. Yahoo Finance (hqt.YFData) ---")
    print("="*50)
    try:
        yf_data = hqt.YFData.download('BTC-USD', period='7d', interval='1d')
        print("Yahoo Finance BTC-USD:")
        print(yf_data.close.head())
    except Exception as e:
        print(f"YFData error: {e}")

def example_02_binance():
    print("\n" + "="*50)
    print("--- 2. Binance (hqt.BinanceData) ---")
    print("="*50)
    try:
        binance_data = hqt.BinanceData.download('BTCUSDT', start='24 hours ago UTC', interval='1h')
        print("Binance BTCUSDT:")
        print(binance_data.close.head())
    except Exception as e:
        print(f"BinanceData error: {e}")

def example_03_ccxt():
    print("\n" + "="*50)
    print("--- 3. CCXT (hqt.CCXTData) ---")
    print("="*50)
    try:
        ccxt_data = hqt.CCXTData.download('BTC/USDT', exchange='binance', limit=5, timeframe='1h')
        print("CCXT Binance BTC/USDT:")
        print(ccxt_data.close.head())
    except Exception as e:
        print(f"CCXTData error: {e}")

def example_04_mt5():
    print("\n" + "="*50)
    print("--- 4. MT5 (hqt.MT5Data) ---")
    print("="*50)
    try:
        mt5_data = hqt.MT5Data.download(symbol="EURUSD", timeframe="D1", count=10)
        print("MT5 EURUSD:")
        print(mt5_data.close.head())
    except Exception as e:
        print(f"MT5 Data error: {e}")

def example_05_dukascopy():
    print("\n" + "="*50)
    print("--- 5. Dukascopy (hqt.DukascopyData) ---")
    print("="*50)
    try:
        dukascopy_data = hqt.DukascopyData.download(symbol="EURUSD", timeframe="D1", count=10)
        print("Dukascopy EURUSD:")
        print(dukascopy_data.close.head())
    except Exception as e:
        print(f"Dukascopy Data error: {e}")

def example_06_gbm_generate_data():
    print("\n" + "="*50)
    print("--- 6. Geometric Brownian Motion (hqt.GBMData) ---")
    print("="*50)
    try:
        gbm_data = hqt.GBMData.generate(
            "SYNTHTIC",
            start='2020-01-01',
            end='2020-01-10',
            interval='H1',
            mu=0.0001,
            sigma=0.02,
            seed=42
        )
        print("GBM Data successfully generated:")
        print(gbm_data.df.head())
    except Exception as e:
        print(f"GBM Data error: {e}")

def example_07_csv():
    print("\n" + "="*50)
    print("--- 7. CSV Data (hqt.CSVData) ---")
    print("="*50)
    try:
        # Construct path to the sample file
        # It's in backend/data/market_data/eurusd_sample.csv
        # project_root is HaruQuant/
        csv_path = os.path.join(project_root, 'backend', 'data', 'market_data', 'eurusd_sample.csv')
        print(f"Loading CSV from: {csv_path}")
        csv_data = hqt.CSVData.load(csv_path)
        print("CSV EURUSD Sample:")
        print(csv_data.close.head())
    except Exception as e:
        print(f"CSV Data error: {e}")

def example_08_parquet():
    print("\n" + "="*50)
    print("--- 8. Parquet Data (hqt.ParquetData) ---")
    print("="*50)
    try:
        # Construct path to the sample file
        parquet_path = os.path.join(project_root, 'backend', 'data', 'market_data', 'eurusd_sample.parquet')
        print(f"Loading Parquet from: {parquet_path}")
        parquet_data = hqt.ParquetData.load(parquet_path)
        print("Parquet EURUSD Sample:")
        print(parquet_data.close.head())
    except Exception as e:
        print(f"Parquet Data error: {e}")

def example_09_scheduled_updates():
    print("\n" + "="*50)
    print("--- 9. Data Saver & Scheduled Updates ---")
    print("="*50)
    try:
        symbol = "EURUSD"
        tf = "M1"
        
        # Check if we already have a saved file
        if hqt.CSVDataSaver.file_exists(symbol=symbol, timeframe=tf):
            print(f"Loading existing CSV saver for {symbol} {tf}...")
            csv_saver = hqt.CSVDataSaver.load(symbol=symbol, timeframe=tf)
            csv_saver.update()
            init_save = False
        else:
            print(f"Downloading fresh data for new CSV saver ({symbol} {tf})...")
            data = hqt.MT5Data.download(symbol=symbol, timeframe=tf, count=10)
            csv_saver = hqt.CSVDataSaver(data)
            init_save = True
            
        # In a real scenario, you'd call:
        # csv_saver.update_every(1, "minute", init_save=init_save)
        # But for this example, we'll just manually update and save
        if not init_save:
            print("Manual update performed.")
            
        csv_saver.save(is_initial=init_save)
        print(f"CSV saved to: {csv_saver.path}")
        
        # Parquet example
        print("\nTesting ParquetDataSaver...")
        pq_saver = hqt.ParquetDataSaver(csv_saver.data)
        pq_saver.save()
        print(f"Parquet saved to: {pq_saver.path}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Scheduled updates error: {e}")

def example_10_caching():
    print("\n" + "="*50)
    print("--- 10. Data Caching ---")
    print("="*50)
    try:
        print("Clearing cache to ensure a fresh download...")
        hqt.DataCache.clear()
        
        print("First request - downloading and caching...")
        start_time = time.time()
        data1 = hqt.YFData.download('ETH-USD', period='7d', interval='1d', cache=True)
        print(f"First request took: {time.time() - start_time:.4f} seconds")
        
        print("Second request - loading from cache...")
        start_time = time.time()
        data2 = hqt.YFData.download('ETH-USD', period='7d', interval='1d', cache=True)
        print(f"Second request took: {time.time() - start_time:.4f} seconds")
        
    except Exception as e:
        print(f"Data Caching error: {e}")

def example_11_data_splitter():
    print("\n" + "="*50)
    print("--- 11. Data Preparation and Splitting (hqt.DataSplitter) ---")
    print("="*50)
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

def example_12_labeler():
    print("\n" + "="*50)
    print("--- 12. Labeling for ML (hqt.Labeler) ---")
    print("="*50)
    try:
        print("Generating random price path and identifying local extrema...")
        price_data = hqt.GBMData.generate("BTC", start_value=100, mu=0, sigma=0.05, count=100)
        
        labels = hqt.Labeler.lexlb(price_data, up_threshold=0.05, down_threshold=0.05)
        print("Successfully generated local extrema labels for ML training!")
        
        peaks = labels[labels == 1]
        troughs = labels[labels == -1]
        print(f"Found {len(peaks)} peaks and {len(troughs)} troughs in 100 bars.")
        
    except Exception as e:
        print(f"Labeling for ML error: {e}")

def example_13_symbol_search():
    print("\n" + "="*50)
    print("--- 13. Symbol Search (list_symbols) ---")
    print("="*50)
    try:
        print("Searching Binance for 'XRP*':")
        binance_symbols = hqt.BinanceData.list_symbols("XRP*")
        print(binance_symbols[:10], "... total:", len(binance_symbols))
        
        print("\nSearching MT5 for 'XAU*':")
        mt5_symbols = hqt.MT5Data.list_symbols("XAU*")
        print(mt5_symbols)
        
        print("\nSearching Dukascopy for 'EUR*':")
        duka_symbols = hqt.DukascopyData.list_symbols("EUR*")
        print(duka_symbols[:5], "... total:", len(duka_symbols))
        
    except Exception as e:
        print(f"Symbol search error: {e}")

def example_14_symbol_classes():
    print("\n" + "="*50)
    print("--- 14. Symbol Classes (Metadata) ---")
    print("="*50)
    try:
        # 1. Define classes mapping
        classes = hqt.symbol_dict({
            "EURUSD": dict(sector="USDPairs", asset_class="Forex"),
            "GBPUSD": dict(sector="USDPairs", asset_class="Forex"),
            "USDJPY": dict(sector="JPYPairs", asset_class="Forex"),
            "XAUUSD": dict(sector="Metals", asset_class="Commodities"),
        })
        
        print(f"Downloading data for symbols: {list(classes.keys())}")
        
        # 2. Download with classes
        data = hqt.MT5Data.download(
            list(classes.keys()),
            timeframe="H1",
            count=100,
            classes=classes
        )
        
        print("\nMultiIndex Columns:")
        print(data.df.columns)
        
        print("\nClose Prices (Multi-column DataFrame):")
        close_df = data.close
        print(close_df.tail())
        
        # Accessing by sector (level 0 of MultiIndex)
        print("\nAccessing USDPairs sector:")
        usd_pairs = data.df.xs("USDPairs", axis=1, level=0)
        print(usd_pairs.columns.get_level_values(0).unique())
        
    except Exception as e:
        print(f"Symbol classes error: {e}")

def example_15_resampling():
    print("\n" + "="*50)
    print("--- 15. Data Resampling (hqt.resample) ---")
    print("="*50)
    try:
        # Download 5-minute data
        print("Downloading 5-minute data for EURUSD...")
        data_m5 = hqt.MT5Data.download("EURUSD", timeframe="M5", count=1000)
        print(f"Original M5 Data: {len(data_m5.df)} bars")
        
        # Downsampling (M5 -> H1)
        # Supports MT5-style strings (H1) and standard pandas rules (1h)
        data_h1 = hqt.resample(data_m5, "H1")
        print(f"Downsampled H1 Data: {len(data_h1.df)} bars")
        print(data_h1.df.head())
    except Exception as e:
        print(f"Resampling error: {e}")

def example_16_merging_timeframes():
    print("\n" + "="*50)
    print("--- 16. Merging Timeframes (hqt.merge) ---")
    print("="*50)
    try:
        print("Downloading M5 and H1 data for EURUSD...")
        data_m5 = hqt.MT5Data.download("EURUSD", timeframe="M5", count=500)
        data_h1 = hqt.MT5Data.download("EURUSD", timeframe="H1", count=100)
        
        # Merge higher timeframe into lower timeframe
        # Higher timeframe data is automatically forward-filled to match lower timeframe index
        merged_data = hqt.merge(data_m5, data_h1, suffix="_H1")
        print(f"Merged Data Columns: {list(merged_data.df.columns)}")
        print(merged_data.df[['close', 'close_H1']].head(15))
    except Exception as e:
        print(f"Merging error: {e}")

def example_17_concatenating_instruments():
    print("\n" + "="*50)
    print("--- 17. Concatenating Instruments (hqt.concat) ---")
    print("="*50)
    try:
        print("Downloading H1 data for EURUSD and GBPUSD...")
        data_eur = hqt.MT5Data.download("EURUSD", timeframe="H1", count=100)
        data_gbp = hqt.MT5Data.download("GBPUSD", timeframe="H1", count=100)
        
        # Combine into one MultiIndex Data object
        combined = hqt.concat([data_eur, data_gbp], keys=['EURUSD', 'GBPUSD'])
        print(f"Combined MultiIndex Columns: {combined.df.columns}")
        
        # Accessing just the 'close' prices across both symbols
        # Note: hqt.Data.get is updated to handle MultiIndex
        close_df = combined.close
        print("\nClose prices tail:")
        print(close_df.tail())
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Concatenation error: {e}")

if __name__ == "__main__":
    # example_01_yahoo()
    # example_02_binance()
    # example_03_ccxt()
    # example_04_mt5()
    # example_05_dukascopy()
    # example_06_gbm_generate_data()
    # example_07_csv()
    # example_08_parquet()
    # example_09_scheduled_updates()
    # example_10_caching()
    # example_11_data_splitter()
    # example_12_labeler()
    # example_13_symbol_search()
    # example_14_symbol_classes()
    example_15_resampling()
    example_16_merging_timeframes()
    example_17_concatenating_instruments()
