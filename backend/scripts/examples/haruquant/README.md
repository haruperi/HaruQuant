# HaruQuant Examples

This directory contains examples based on the adaptation of VectorBT's basic and pro features. 

The examples demonstrate the use of HaruQuant's centralized system, which encapsulates complex implementations and operations into simple, one-line calls. This approach streamlines backtesting, data fetching, indicator calculation, and strategy execution workflows.

## Features

Features are illustrated and classified into:

### 1. Data (`01_data.py`)
- **Multi-Channel Downloaders**: One-line data fetching from MT5, Binance, CCXT, Dukascopy, and Yahoo Finance.
- **Synthetic Data Generation**: Create GBM (Geometric Brownian Motion) datasets with specific intervals (H1, M5, etc.).
- **Data Savers & Persistence**: `CSVDataSaver` and `ParquetDataSaver` for robust data storage and retrieval.
- **Scheduled Updates**: Automatically pull and merge new data from sources, resuming seamlessly from saved state.
- **Disk Caching**: Integrated LMDB caching to minimize redundant API calls and speed up research.
- **Symbol Search**: Globbing and regex-based symbol discovery across local and remote providers.
- **Symbol Classes (Metadata)**: Advanced MultiIndex support for hierarchical data (e.g., grouping by Sector or Asset Class).
- **Timeframe Resampling**: Easily downsample data (e.g., M5 -> H1) using MT5-style naming conventions.
- **Multi-Timeframe Merging**: Merge higher timeframe data into lower timeframe indices with automatic forward-filling.
- **Instrument Concatenation**: Combine multiple symbols into a single, unified Data object for vectorized analysis.
- **Data Preprocessing**: Utilities for splitting data into Train/Test sets and labeling for machine learning.

### 2. Indicators (`02_indicators.py`)
- **Native Indicator Suite**: Built-in implementations for SMA, EMA, WMA, RSI, ATR, BBands, and more.
- **Smart Money Concepts (SMC)**: Institutional order flow tools including Fair Value Gaps (FVG), Order Blocks (OB), Market Structure (BOS/CHOCH), and Previous High/Low (PHL) tracking.
- **Statistical Analysis**: Advanced indicators like the **Hurst Exponent** for identifying trending vs. mean-reverting market regimes.
- **Indicator Discovery**: Search for indicators using globbing patterns via `hqt.list_indicators("*ma")` and access them dynamically with `hqt.indicator()`.
- **Bulk Feature Generation**: Generate dozens of features for Machine Learning in a single call using `hqt.run_indicators(data, "native")` or `hqt.run_indicators(data, "smc")`.
- **Pandas TA Integration**: Seamless wrapper for the `pandas_ta` library, allowing any of its 130+ indicators to be used within the `hqt` pipeline (e.g., `hqt.ta.zlema.run()`).
- **Parallel Execution**: High-performance parameter sweeps using `engine="threadpool"` or `engine="processpool"` to distribute calculations across multiple CPU cores.
- **Vectorized Chaining**: Effortlessly chain indicators (e.g., `hqt.rsi.run(hqt.ema.run(data))`) for complex technical signals.
- **Indicator Packages**: Run entire indicator packages (e.g., TALIB) on a data instance in a single call using `data.run("talib")`.
- **Parallelizable Indicators**: Process parameter combinations efficiently by distributing the indicator factory across multiple threads or processes.

### 3. Strategy (`03_strategy.py`)
- **Signal Generation**: One-line strategy execution using `hqt.TrendFollowingStrategy` to generate entry and exit signals.
- **Random Backtesting**: Generate and backtest random signals for strategy benchmarking using `hqt.Portfolio.from_random_signals()`.
- **Buy & Hold Analysis**: Evaluate benchmark performance using the one-line `hqt.Portfolio.from_holding()` method.
- **Unified Portfolio Backtesting**: Complete end-to-end backtesting with overrides (symbols, periods, parameters) using the powerful `hqt.Portfolio.run()` method.
- **Simulation Range Slicing**: Isolate and analyze specific market regimes or time windows (e.g., Q1 performance) instantly using `portfolio.slice(start, end)`.
- **Comprehensive Reporting**: Generate detailed performance reports with trade-by-trade analysis and All/Long/Short breakdowns via `portfolio.summary()`.

### 4. Optimization (`04_optimization.py`)
- *In progress...*

### 5. Performance (`05_performance.py`)
- *In progress...*

### 6. Portfolio (`06_portfolio.py`)
- *In progress...*

### 7. Productivity (`07_productivity.py`)
- *In progress...*

### 8. Intelligence (`08_intelligence.py`)
- *In progress...*

