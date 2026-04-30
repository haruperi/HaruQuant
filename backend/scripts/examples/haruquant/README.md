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
- *In progress...*

### 3. Analysis (`03_analysis.py`)
- *In progress...*

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

