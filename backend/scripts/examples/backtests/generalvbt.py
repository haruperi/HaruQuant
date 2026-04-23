import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from numba import njit
import time

# Add the 'backend' directory to sys.path so we can import the local vectorbt folder
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
project_root = os.path.abspath(os.path.join(backend_dir, '..'))

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import haruquant as hqt

# Initialize engine to connect to MT5
from backend.services.simulation.engine import Engine

engine = Engine(backend="mt5")
client = engine.client

@njit
def zscore_nb(x):
    return (x[-1] - np.mean(x)) / np.std(x)

@njit
def vbt_zscore_nb(i, col, x):
    return zscore_nb(x)

def example_01_pandas():
    print("\n" + "="*50)
    print("Example 01: VectorBT Pandas Extensions")
    print("="*50)
    
    print("\n--- 1. Pandas Acceleration with Numba ---")
    print("Generating a 1000x1000 random DataFrame...")
    big_ts = pd.DataFrame(np.random.uniform(size=(1000, 1000)))
    
    # Warm up Numba compilation so it doesn't skew the benchmark
    print("Compiling Numba functions (warmup)...")
    _ = big_ts.iloc[:5, :5].rolling(2).apply(zscore_nb, raw=True)
    _ = big_ts.iloc[:5, :5].vbt.rolling_apply(2, vbt_zscore_nb)

    print("Running standard Pandas rolling.apply (this might take a moment)...")
    start_time = time.time()
    _ = big_ts.rolling(2).apply(zscore_nb, raw=True)
    pandas_time = time.time() - start_time
    print(f"Pandas rolling.apply time: {pandas_time:.4f} seconds")

    print("Running VectorBT vbt.rolling_apply...")
    start_time = time.time()
    _ = big_ts.vbt.rolling_apply(2, vbt_zscore_nb)
    vbt_time = time.time() - start_time
    print(f"VectorBT vbt.rolling_apply time: {vbt_time:.4f} seconds")
    
    if vbt_time > 0:
        speedup = pandas_time / vbt_time
        print(f"VectorBT is {speedup:.2f}x faster!")

    print("\n--- 2. Flexible Broadcasting ---")
    sr = pd.Series([1, 2, 3], index=['x', 'y', 'z'])
    df = pd.DataFrame([[4, 5, 6]], index=['x', 'y', 'z'], columns=['a', 'b', 'c'])

    print("Standard Pandas (sr + df):")
    print(sr + df)

    print("\nVectorBT Broadcasting (sr.vbt + df):")
    print(sr.vbt + df)
    
    print("\n--- 3. Pandas Utilities ---")
    print("Build a symmetric matrix from pd.Series([1, 2, 3]).vbt.make_symmetric():")
    print(pd.Series([1, 2, 3]).vbt.make_symmetric())



def example_02_data():
    print("\n" + "="*50)
    print("Example 02: Data Acquisition (via HaruQuant hqt)")
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

def example_03_indicators():
    print("\n\n" + "="*50)
    print("      EXAMPLE 03: TECHNICAL INDICATORS       ")
    print("="*50)
    
    price = pd.Series([1, 2, 3, 4, 5], dtype=float)
    
    print("\n--- 1. VectorBT Native Indicators (Numba Accelerated) ---")
    print("Computing 2 moving averages at once using vbt.MA:")
    ma_result = vbt.MA.run(price, [2, 3])
    print(ma_result.ma)
    
    print("\n--- 2. TA-Lib integration via VectorBT ---")
    try:
        # Note: vbt.ta requires the 'ta' module (Technical Analysis Library in Python)
        ta_sma = vbt.ta('SMAIndicator').run(price, [2, 3]).sma_indicator
        print(ta_sma)
    except Exception as e:
        print(f"TA-Lib (via 'ta' package) error: {e}")
        
    print("\n--- 3. Pandas TA integration via VectorBT ---")
    try:
        # Note: vbt.pandas_ta requires the 'pandas_ta' module
        pta_sma = vbt.pandas_ta('SMA').run(price, [2, 3]).sma
        print(pta_sma)
    except Exception as e:
        print(f"Pandas TA error: {e}")

    print("\n--- 4. Local HaruQuant Indicators Integration ---")
    try:
        from backend.services.indicators.trend.sma import sma as haru_sma
        
        # HaruQuant local SMA expects a DataFrame with a 'close' column
        df = pd.DataFrame({'close': [1, 2, 3, 4, 5]}, dtype=float)
        
        print("Running native HaruQuant SMA (window=2):")
        hq_result = haru_sma(df, window=2)
        print(hq_result)
        
        # We can wrap local indicators into VectorBT's IndicatorFactory
        # so they accept multiple parameters instantly (e.g. Cartesian products)!
        def apply_hq_sma(close, window):
            # VectorBT passes a 2D numpy array even for single columns
            res = np.empty_like(close, dtype=float)
            for col in range(close.shape[1]):
                temp_df = pd.DataFrame({'close': close[:, col]})
                df_res = haru_sma(temp_df, window=window)
                res[:, col] = df_res[f'sma_{window}'].values
            return res
            
        HQ_SMA = vbt.IndicatorFactory(
            class_name='HQSMA',
            input_names=['close'],
            param_names=['window'],
            output_names=['sma']
        ).from_apply_func(apply_hq_sma)
        
        print("\nRunning HaruQuant SMA vectorized via VectorBT (window=[2, 3]):")
        hq_vbt_result = HQ_SMA.run(df['close'], window=[2, 3])
        print(hq_vbt_result.sma)
        
    except Exception as e:
        print(f"HaruQuant Local Indicator error: {e}")

def example_04_signals():
    print("\n\n" + "="*50)
    print("        EXAMPLE 04: SIGNAL GENERATION        ")
    print("="*50)
    
    # 1. Signal analysis
    print("\n--- 1. Signal Analysis ---")
    print("Measure duration of True value partitions:")
    try:
        mask_sr = pd.Series([True, True, True, False, True, True])
        durations = mask_sr.vbt.signals.partition_ranges().duration.values
        print(f"Mask:\n{mask_sr.values}")
        print(f"Durations of True partitions: {durations}")
    except Exception as e:
        print(f"Signal Analysis error: {e}")

    # 2. Signal generators
    print("\n--- 2. Signal Generators ---")
    print("Generate random entries and exits using probabilities:")
    try:
        rprobnx = vbt.RPROBNX.run(
            input_shape=(5,),
            entry_prob=[0.5, 1.],
            exit_prob=[0.5, 1.],
            param_product=True,
            seed=42
        )
        print("Entries:\n", rprobnx.entries)
        print("\nExits:\n", rprobnx.exits)
    except Exception as e:
        print(f"Signal Generator error: {e}")

    # 3. Signal factory
    print("\n--- 3. Signal Factory ---")
    print("Custom signal factory based on IndicatorFactory for iterative generation:")
    try:
        from numba import njit
        
        @njit
        def entry_choice_func(from_i, to_i, col):
            return np.array([col])

        @njit
        def exit_choice_func(from_i, to_i, col):
            return np.array([to_i - 1])

        MySignals = vbt.SignalFactory().from_choice_func(
            entry_choice_func=entry_choice_func,
            exit_choice_func=exit_choice_func,
            entry_kwargs=dict(wait=1),
            exit_kwargs=dict(wait=0)
        )

        my_sig = MySignals.run(input_shape=(3, 3))
        print("Entries:\n", my_sig.entries)
        print("\nExits:\n", my_sig.exits)
    except Exception as e:
        print(f"Signal Factory error: {e}")

def example_05_modelling():
    print("\n\n" + "="*50)
    print("        EXAMPLE 05: PORTFOLIO MODELING       ")
    print("="*50)
    
    print("\nBacktesting the Golden Cross on BTC-USD...")
    try:
        # Download data
        price = vbt.YFData.download('BTC-USD', start='2018-01-01').get('Close')
        
        # Explicitly set frequency to bypass pandas offset 'Day' bug in VectorBT Plotting
        price.index = price.index.tz_localize(None) # Sometimes YFData returns timezone-aware which complicates freq
        price.index.freq = '1d' # Or we can just pass freq='1d' to Portfolio
        
        # Calculate moving averages
        fast_ma = vbt.MA.run(price, 50, short_name='fast_ma')
        slow_ma = vbt.MA.run(price, 200, short_name='slow_ma')
        
        # Generate signals
        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)
        
        # Build portfolio (passing freq explicitly helps VectorBT internal properties)
        pf = vbt.Portfolio.from_signals(price, entries, exits, fees=0.005, freq='1d')
        
        print("\nOrder Records:")
        print(pf.orders.records_readable)
        
        # Plotting
        print("\nGenerating interactive Plotly visualization for the Golden Cross strategy...")
        fig = price.vbt.plot(trace_kwargs=dict(name='Close'))
        fast_ma.ma.vbt.plot(trace_kwargs=dict(name='Fast MA'), fig=fig)
        slow_ma.ma.vbt.plot(trace_kwargs=dict(name='Slow MA'), fig=fig)
        
        # Overlay positions
        pf.positions.plot(close_trace_kwargs=dict(visible=False), fig=fig)
        
        # Show figure
        if hasattr(fig, "show"):
            fig.show()
            
    except Exception as e:
        print(f"Portfolio Modeling error: {e}")

def example_06_analysis():
    print("\n\n" + "="*50)
    print("        EXAMPLE 06: PERFORMANCE ANALYSIS     ")
    print("="*50)
    
    print("\nVisualizing performance using QuantStats integration...")
    try:
        import matplotlib.pyplot as plt
        
        # Download data (limiting date range slightly to speed up computation)
        price = vbt.YFData.download('BTC-USD', start='2020-01-01').get('Close')
        
        # Explicitly set frequency to bypass pandas offset 'Day' bug in VectorBT QuantStats
        price.index = price.index.tz_localize(None)
        price.index.freq = '1d'
        
        # Calculate returns using VectorBT
        returns = price.vbt.to_returns()
        
        # QuantStats snapshot
        print("Generating QuantStats snapshot plot...")
        fig = returns.vbt.returns.qs.plot_snapshot()
        
        # QuantStats plots use matplotlib natively, so we ensure it displays
        if fig is not None and hasattr(fig, 'show'):
            fig.show()
        else:
            plt.show()
            
        # 1. Stats builder
        print("\n--- 1. Stats Builder ---")
        index = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(7)]
        mask = pd.Series([False, True, True, True, False, True, False])
        print("Signal Distribution Stats:")
        print(mask.vbt.signals(freq='d').stats())

        # 2. Records and Mapped Arrays
        print("\n--- 2. Records and Mapped Arrays ---")
        print("Parsing 5 highest slippage values from logs...")
        # (Using our already downloaded price to speed things up)
        slippage = np.random.uniform(0, 0.005, size=price.shape[0])
        logs = vbt.Portfolio.from_random_signals(price, n=5, slippage=slippage, log=True).logs
        
        req_price_ma = logs.map_field('req_price')
        res_price_ma = logs.map_field('res_price')
        slippage_ma = (res_price_ma - req_price_ma) / req_price_ma
        slippage_ma = slippage_ma.replace(arr=np.abs(slippage_ma.values))
        top_slippage_pd = slippage_ma.top_n(5).to_pd()
        print("Top 5 Slippage Values:")
        print(top_slippage_pd[~top_slippage_pd.isnull()])

        # 3. Trade analysis
        print("\n--- 3. Trade Analysis ---")
        print("Projected return of each entry trade...")
        entry_trades = vbt.Portfolio.from_random_signals(price, n=5).entry_trades
        returns_pd = entry_trades.returns.to_pd()
        print("Entry Trade Returns:")
        print(returns_pd[~returns_pd.isnull()])

        # 4. Drawdown analysis
        print("\n--- 4. Drawdown Analysis ---")
        print("Plotting 3 deepest price dips (opening interactive window)...")
        drawdown_fig = price.vbt.drawdowns.plot(top_n=3)
        if hasattr(drawdown_fig, "show"):
            drawdown_fig.show()
            
    except Exception as e:
        print(f"Analysis error: {e}")

def example_07_plotting():
    print("\n\n" + "="*50)
    print("        EXAMPLE 07: DATA VISUALIZATION       ")
    print("="*50)
    
    # 1. Data Visualization
    print("\n--- 1. Data Visualization ---")
    print("Plotting time series against each other...")
    try:
        sr1 = pd.Series(np.cumprod(np.random.normal(0, 0.01, 100) + 1))
        sr2 = pd.Series(np.cumprod(np.random.normal(0, 0.01, 100) + 1))
        fig1 = sr1.vbt.plot_against(sr2)
        if hasattr(fig1, "show"):
            fig1.show()
    except Exception as e:
        print(f"Data Visualization error: {e}")

    # 2. Figures and widgets
    print("\n--- 2. Figures and Widgets ---")
    print("Plotting a 3D volume using vbt.plotting.Volume...")
    try:
        volume_widget = vbt.plotting.Volume(
            data=np.random.randint(1, 10, size=(3, 3, 3)),
            x_labels=['a', 'b', 'c'],
            y_labels=['d', 'e', 'f'],
            z_labels=['g', 'h', 'i']
        )
        if hasattr(volume_widget.fig, "show"):
            volume_widget.fig.show()
    except Exception as e:
        print(f"Figures and widgets error: {e}")

    # 3. Plots builder
    print("\n--- 3. Plots Builder ---")
    print("Plotting various portfolio balances (cash, assets, value)...")
    try:
        price = vbt.YFData.download('BTC-USD', start='2020-01-01').get('Close')
        
        # Explicit frequency fix to prevent Day offset bug
        price.index = price.index.tz_localize(None)
        
        # Use pd.Timedelta instead of string '1d' to bypass the pandas 2.2 VectorBT Day offset bug
        pf = vbt.Portfolio.from_random_signals(price, n=5, freq=pd.Timedelta(days=1))
        
        # We use .show() instead of .show_svg() for standard python scripts to trigger the browser
        fig3 = pf.plot(subplots=['cash', 'assets', 'value'])
        if hasattr(fig3, "show"):
            fig3.show()
    except Exception as e:
        print(f"Plots builder error: {e}")

def example_08_extras():
    print("\n\n" + "="*50)
    print("           EXAMPLE 08: EXTRAS                ")
    print("="*50)
    
    # 1. Notifications
    print("\n--- 1. Notifications ---")
    print("VectorBT supports Telegram bots natively. (Skipped instantiation to avoid blocking execution)")
    # Code would look like this:
    # from telegram.ext import CommandHandler
    # class BinanceTickerBot(vbt.TelegramBot): ...
    # bot = BinanceTickerBot(token='YOUR_TOKEN')
    # bot.start()

    # 2. General utilities
    print("\n--- 2. General Utilities (Scheduling) ---")
    try:
        import ccxt
        from vectorbt.utils.datetime_ import datetime_to_ms, to_tzaware_datetime, get_utc_tz
        
        exchange = ccxt.binance()
        
        def job_func():
            print("Fetching latest BTC/USDT trades from Binance...")
            since = datetime_to_ms(to_tzaware_datetime('1 minute ago UTC', tz=get_utc_tz()))
            trades = exchange.fetch_trades('BTC/USDT', since)
            if len(trades) > 0:
                price = pd.Series({t['datetime']: t['price'] for t in trades})
                print(f"Fetched {len(price)} trades. Latest price: {price.iloc[-1]}")
            else:
                print("No recent trades found.")
            
        print("Running the job once manually to demonstrate:")
        job_func()
        
        # scheduler = vbt.ScheduleManager()
        # scheduler.every(10, 'seconds').do(job_func)
        # scheduler.start()
        print("(Note: To run continuously every 10 seconds, use vbt.ScheduleManager().start())")
    except Exception as e:
        print(f"Utilities error: {e}")

    # 3. Caching
    print("\n--- 3. Caching ---")
    try:
        import time
        start = time.time()
        
        class MyClass:
            @vbt.cached_method
            def get_elapsed(self):
                return time.time() - start
                
        my_inst = MyClass()
        val1 = my_inst.get_elapsed()
        print(f"First call (computed): {val1:.4f}s")
        
        time.sleep(0.5)
        val2 = my_inst.get_elapsed()
        print(f"Second call (cached): {val2:.4f}s (should be exactly the same)")
        
        # Disable cache globally for this method
        print("Disabling cache for 'get_elapsed' via vbt.settings.caching['blacklist']...")
        get_elapsed_cond = vbt.CacheCondition(instance=my_inst, func='get_elapsed')
        vbt.settings.caching['blacklist'].append(get_elapsed_cond)
        
        time.sleep(0.5)
        val3 = my_inst.get_elapsed()
        print(f"Third call (re-computed): {val3:.4f}s (should be different)")
        
    except Exception as e:
        print(f"Caching error: {e}")

    # 4. Persistence
    print("\n--- 4. Persistence ---")
    try:
        import os
        price = vbt.YFData.download('BTC-USD', start='2020-01-01').get('Close')
        price.index = price.index.tz_localize(None)
        
        pf = vbt.Portfolio.from_random_signals(price, n=5, freq=pd.Timedelta(days=1))
        
        filename = 'my_pf.pkl'
        print(f"Saving portfolio to {filename}...")
        pf.save(filename)
        
        print("Loading portfolio back from disk...")
        pf_loaded = vbt.Portfolio.load(filename)
        
        print("Total Return (loaded from disk):")
        print(pf_loaded.total_return())
        
        # Clean up
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Cleaned up temporary file: {filename}")
            
    except Exception as e:
        print(f"Persistence error: {e}")

def example_09_buy_and_hold():
    print("\n\n" + "="*50)
    print("        EXAMPLE 09: BUY AND HOLD STRATEGY     ")
    print("="*50)
    
    try:
        price = vbt.YFData.download('BTC-USD', start='2017-01-01').get('Close')
        pf = vbt.Portfolio.from_holding(price, init_cash=10000)
        print(pf.total_profit())
        
    except Exception as e:
        print(f"Buy and Hold error: {e}")

def example_10_random_signals():
    print("\n\n" + "="*50)
    print("        EXAMPLE 10: RANDOM SIGNALS STRATEGY     ")
    print("="*50)
    
    try:
        symbols = ["BTC-USD", "ETH-USD"]
        raw = vbt.YFData.download(symbols, missing_index='drop').get('Close')
        
        # After HaruQuant engine init, some numpy arrays are marked read-only globally.
        # Force writability by reconstructing values through np.array with a fresh allocation.
        vals = np.array(raw.values, dtype=np.float64, order='C')
        vals.flags.writeable = True
        price = pd.DataFrame(vals, index=raw.index.copy(), columns=raw.columns.copy())
        
        n = np.random.randint(10, 101, size=1000).tolist()
        pf = vbt.Portfolio.from_random_signals(price, n=n, init_cash=100, seed=42)
        mean_expectancy = pf.trades.expectancy().groupby(['randnx_n', 'symbol']).mean()
        fig = mean_expectancy.unstack().vbt.scatterplot(xaxis_title='randnx_n', yaxis_title='mean_expectancy')
        fig.show()
        
    except Exception as e:
        print(f"Random Signals error: {e}")
        import traceback; traceback.print_exc()


def example_11_simple_ma_strategy():
    # Prepare data
    start = datetime(2019, 1, 1)
    end = datetime(2020, 1, 1)

    print("Downloading EURUSD data from MT5...")
    data = client.get_bars(
        symbol="EURUSD",
        timeframe="D1",
        date_from=start,
        date_to=end
    )

    if data is None or data.empty:
        print("Failed to fetch data. Make sure MT5 is running and EURUSD is available.")
        sys.exit(1)

    eurusd_price = data['close']

    print("Data downloaded successfully!")
    print(eurusd_price.head())
    print(eurusd_price.tail())

    print("\n--- Running Moving Average Strategy ---")
    fast_ma = vbt.MA.run(eurusd_price, 10, short_name='fast')
    slow_ma = vbt.MA.run(eurusd_price, 20, short_name='slow')

    entries = fast_ma.ma_crossed_above(slow_ma)
    print("\nEntries Summary:")
    print(entries.value_counts())

    exits = fast_ma.ma_crossed_below(slow_ma)
    print("\nExits Summary:")
    print(exits.value_counts())

    pf = vbt.Portfolio.from_signals(eurusd_price, entries, exits)
    print("\nTotal Return:", pf.total_return())


def example_12_multiple_strategies_and_instruments():
    print("\n" + "="*50)
    print("Example 12: Multiple Strategies and Instruments")
    print("="*50)
    
    start = datetime(2019, 1, 1)
    end = datetime(2020, 1, 1)

    print("Downloading EURUSD data from MT5...")
    eurusd_data = client.get_bars(
        symbol="EURUSD",
        timeframe="D1",
        date_from=start,
        date_to=end
    )
    
    print("Downloading GBPUSD data from MT5...")
    gbpusd_data = client.get_bars(
        symbol="GBPUSD",
        timeframe="D1",
        date_from=start,
        date_to=end
    )

    if eurusd_data is None or eurusd_data.empty or gbpusd_data is None or gbpusd_data.empty:
        print("Failed to fetch data for EURUSD or GBPUSD. Make sure MT5 is running.")
        return

    eurusd_price = eurusd_data['close']
    gbpusd_price = gbpusd_data['close']

    # Combine the prices
    comb_price = eurusd_price.vbt.concat(
        gbpusd_price,
        keys=pd.Index(['EURUSD', 'GBPUSD'], name='symbol')
    )
    
    # Depending on how the index is formed, drop_levels might fail if there's only 1 level.
    try:
        comb_price.vbt.drop_levels(-1, inplace=True)
    except Exception:
        pass
        
    print("\nCombined Price Data:")
    print(comb_price.head())
    
    print("\n--- Running Multi-Moving Average Strategy ---")
    fast_ma = vbt.MA.run(comb_price, [10, 20], short_name='fast')
    slow_ma = vbt.MA.run(comb_price, [30, 30], short_name='slow')

    entries = fast_ma.ma_crossed_above(slow_ma)
    print("\nEntries Summary:")
    print(entries.value_counts())

    exits = fast_ma.ma_crossed_below(slow_ma)
    print("\nExits Summary:")
    print(exits.value_counts())

    pf = vbt.Portfolio.from_signals(comb_price, entries, exits)
    print("\nTotal Return:")
    print(pf.total_return())

def example_13_hyperparameter_optimization():
    print("\n\n" + "="*50)
    print("   EXAMPLE 13: HYPERPARAMETER OPTIMIZATION    ")
    print("="*50)
    print("\nTesting 10,000 window combinations of dual SMA crossover on BTC, ETH, LTC...")
    
    try:
        symbols = ["BTC-USD", "ETH-USD", "LTC-USD"]
        raw = vbt.YFData.download(symbols, missing_index='drop').get('Close')
        
        # Ensure writable arrays (same fix as example_10)
        vals = np.array(raw.values, dtype=np.float64, order='C')
        vals.flags.writeable = True
        price = pd.DataFrame(vals, index=raw.index.copy(), columns=raw.columns.copy())
        
        windows = np.arange(2, 101)
        fast_ma, slow_ma = vbt.MA.run_combs(price, window=windows, r=2, short_names=['fast', 'slow'])
        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)
        
        pf_kwargs = dict(size=np.inf, fees=0.001, freq='1D')
        pf = vbt.Portfolio.from_signals(price, entries, exits, **pf_kwargs)
        
        print("Rendering heatmap of total returns across all window combinations...")
        fig = pf.total_return().vbt.heatmap(
            x_level='fast_window', y_level='slow_window', slider_level='symbol', symmetric=True,
            trace_kwargs=dict(colorbar=dict(title='Total return', tickformat='%'))
        )
        fig.show()
        
        # Drill into a specific strategy config using pandas-style indexing
        print("\nDrilling into (fast=10, slow=20, ETH-USD) configuration:")
        pf_eth = pf[(10, 20, 'ETH-USD')]
        
        print("\nStats:")
        print(pf_eth.stats())
        
        print("\nOpening individual strategy plot...")
        pf_eth.plot().show()
        
    except Exception as e:
        print(f"Hyperparameter Optimization error: {e}")
        import traceback; traceback.print_exc()

def example_14_bbands_animation():
    print("\n\n" + "="*50)
    print("   EXAMPLE 14: BOLLINGER BANDS ANIMATION      ")
    print("="*50)
    print("\nGenerating animated GIF of %B and Bandwidth across BTC, ETH, ADA...")
    
    try:
        symbols = ["BTC-USD", "ETH-USD", "ADA-USD"]
        price = vbt.YFData.download(symbols, period='6mo', missing_index='drop').get('Close')
        bbands = vbt.BBANDS.run(price)

        def plot(index, bbands):
            bbands_loc = bbands.loc[index]
            fig = vbt.make_subplots(
                rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15,
                subplot_titles=('%B', 'Bandwidth'))
            fig.update_layout(template='vbt_dark', showlegend=False, width=750, height=400)
            bbands_loc.percent_b.vbt.ts_heatmap(
                trace_kwargs=dict(zmin=0, zmid=0.5, zmax=1, colorscale='Spectral', colorbar=dict(
                    y=(fig.layout.yaxis.domain[0] + fig.layout.yaxis.domain[1]) / 2, len=0.5
                )), add_trace_kwargs=dict(row=1, col=1), fig=fig)
            bbands_loc.bandwidth.vbt.ts_heatmap(
                trace_kwargs=dict(colorbar=dict(
                    y=(fig.layout.yaxis2.domain[0] + fig.layout.yaxis2.domain[1]) / 2, len=0.5
                )), add_trace_kwargs=dict(row=2, col=1), fig=fig)
            return fig

        output_path = 'bbands.gif'
        vbt.save_animation(output_path, bbands.wrapper.index, plot, bbands, delta=90, step=3)
        print(f"GIF saved to: {output_path}")
        
    except Exception as e:
        print(f"Bollinger Bands Animation error: {e}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    # example_01_pandas()
    example_02_data()
    # example_03_indicators()
    # example_04_signals()
    # example_05_modelling()
    # example_06_analysis()
    # example_07_plotting()
    # example_08_extras()
    # example_09_buy_and_hold()
    # example_10_random_signals()
    # example_11_simple_ma_strategy()
    # example_12_multiple_strategies_and_instruments()
    # example_13_hyperparameter_optimization()
    # example_14_bbands_animation()
    
    
    