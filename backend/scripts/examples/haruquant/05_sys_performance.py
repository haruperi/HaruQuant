import os
import sys
from pathlib import Path

# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import numpy as np
import pandas as pd
import haruquant as hqt
import time
from datetime import datetime

def example_01_benchmark_rolling_mean():
    print("\n" + "="*50)
    print("Example 01: System Performance - Parallel Numba")
    print("="*50)

    # 1. Generate large dataset (1000 assets, 1000 bars)
    print("Generating random data (1000 assets x 1000 bars)...")
    df = pd.DataFrame(np.random.uniform(size=(1000, 1000)))
    window = 10

    # 2. Benchmark Pandas
    print("\nBenchmarking Pandas rolling mean...")
    start = time.time()
    for _ in range(10):
        pd_res = df.rolling(window).mean()
    end = time.time()
    pandas_time = (end - start) / 10
    print(f"Pandas average time: {pandas_time*1000:.2f} ms")

    # 3. Benchmark HaruQuant (Numba Jitted)
    print("\nBenchmarking HaruQuant rolling mean (Numba, single-threaded)...")
    # First run to compile
    df.hqt.rolling_mean(window)
    
    start = time.time()
    for _ in range(10):
        hqt_res = df.hqt.rolling_mean(window)
    end = time.time()
    hqt_time = (end - start) / 10
    print(f"HaruQuant (Jitted) average time: {hqt_time*1000:.2f} ms")
    print(f"Speedup vs Pandas: {pandas_time/hqt_time:.1f}x")

    # 4. Benchmark HaruQuant (Numba Parallel)
    print("\nBenchmarking HaruQuant rolling mean (Numba, Parallel)...")
    # First run to compile
    df.hqt.rolling_mean(window, jitted={'parallel': True})
    
    start = time.time()
    for _ in range(10):
        hqt_parallel_res = df.hqt.rolling_mean(window, jitted={'parallel': True})
    end = time.time()
    hqt_parallel_time = (end - start) / 10
    print(f"HaruQuant (Parallel) average time: {hqt_parallel_time*1000:.2f} ms")
    print(f"Speedup vs Pandas: {pandas_time/hqt_parallel_time:.1f}x")
    print(f"Speedup vs Jitted: {hqt_time/hqt_parallel_time:.1f}x")

    # Verify results are same
    print("\nVerifying correctness...")
    # Fill NaN for comparison
    pd_val = pd_res.fillna(0).values
    hqt_val = hqt_res.fillna(0).values
    if np.allclose(pd_val, hqt_val):
        print("Success: Results are identical!")
    else:
        print("Warning: Results differ slightly.")

def example_02_benchmark_multithreading():
    print("\n" + "="*50)
    print("Example 02: System Performance - Multithreading")
    print("="*50)

    # 1. Setup data
    print("Generating price data (1000 bars)...")
    price = pd.Series(np.random.uniform(100, 110, size=1000), name="Close")
    
    # 2. Sequential execution
    num_sims = 100
    print(f"\nRunning {num_sims} random portfolios sequentially...")
    start = time.time()
    portfolios_seq = hqt.Portfolio.from_random_signals(price, n=[10] * num_sims)
    sequential_time = time.time() - start
    print(f"Sequential time: {sequential_time*1000:.2f} ms")

    # 3. Multithreaded execution
    print(f"\nRunning {num_sims} random portfolios with ThreadPool...")
    start = time.time()
    portfolios_thread = hqt.Portfolio.from_random_signals(price, n=[10] * num_sims, chunked="threadpool")
    thread_time = time.time() - start
    print(f"ThreadPool time: {thread_time*1000:.2f} ms")
    
    print(f"\nMultithreading Speedup: {sequential_time/thread_time:.1f}x")
    print(f"Total portfolios generated: {len(portfolios_thread)}")

# Define a slow function at module level for pickling (for multiprocessing)
def bubble_sort_base(items):
    # Pure Python bubble sort - very slow
    arr = items.flatten().copy()
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr.reshape(-1, 1)

def example_03_benchmark_multiprocessing():
    '''
    IMPORTANT
    Performance Note: Multiprocessing on Windows has significant startup overhead because each child process re-imports the entire application environment. 
    This feature is most effective for tasks that take several seconds or longer per chunk.
    '''

    print("\n" + "="*50)
    print("Example 03: System Performance - Multiprocessing")
    print("="*50)

    # 1. Setup data (1000 items, 8 columns)
    print("Generating data (1000 items x 8 columns)...")
    items = np.random.uniform(size=(1000, 8))
    
    # Create chunked version
    bubble_sort_chunked = hqt.chunked(size=1, engine="sequential")(bubble_sort_base)

    # 2. Sequential execution
    print("\nRunning bubble sort on 8 columns sequentially...")
    start = time.time()
    res_seq = bubble_sort_chunked(items)
    sequential_time = time.time() - start
    print(f"Sequential time: {sequential_time*1000:.2f} ms")

    # 3. Multiprocessing execution
    print("\nRunning bubble sort on 8 columns with ProcessPool...")
    start = time.time()
    res_proc = bubble_sort_chunked(items, _execute_kwargs=dict(engine="processpool"))
    process_time = time.time() - start
    print(f"ProcessPool time: {process_time*1000:.2f} ms")
    
    print(f"\nMultiprocessing Speedup: {sequential_time/process_time:.1f}x")

if __name__ == "__main__":
    # example_01_benchmark_rolling_mean()
    # example_02_benchmark_multithreading()
    example_03_benchmark_multiprocessing()
