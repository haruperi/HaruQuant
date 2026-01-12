# Data Integration Examples

This folder contains examples demonstrating how to load and prepare data for backtesting from various sources.

## Overview

The HaruQuant backtesting system supports multiple data sources:

- **Dukascopy**: Historical tick/M1 data stored in parquet files
- **MetaTrader 5 (MT5)**: Real-time and historical data via MT5 connection
- **Custom Sources**: CSV files, APIs, or any custom data format

All examples use `apps.utils.data_getters` for unified data loading.

## Examples

### 01_load_dukascopy.py

Learn how to load historical data from Dukascopy parquet files:

- Load specific date ranges
- Use memory caching for performance
- Load multiple symbols
- Validate data quality
- Handle missing files

### 02_load_mt5_realtime.py

Connect to MetaTrader 5 for real-time data:

- Setup MT5 connection
- Fetch different timeframes
- Handle connection errors
- Automatic fallback to Dukascopy
- Best practices for live data

### 03_data_preprocessing.py

Clean and prepare data for backtesting:

- Handle missing values
- Detect and remove outliers
- Standardize column names
- Validate data integrity
- Fill gaps in data

### 04_multi_timeframe.py

Use multiple timeframes in strategies:

- Load H1 and D1 data
- Filter signals with higher timeframe trend
- Resample data between timeframes
- Align different timeframe data
- Multi-timeframe strategy example

### 05_custom_data_source.py

Integrate custom data sources:

- Load from CSV files
- Fetch from REST APIs
- Convert custom formats
- Use `DataValidator.prepare_data()` helper
- Best practices for data integration

## Data Format Requirements

All data must have the following columns (lowercase):

- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume
- `spread`: Bid-ask spread (or 0 if not available)

The index must be a `DatetimeIndex` sorted in ascending order.

## Quick Start

```python
from apps.utils.data_getters import load_dukascopy, load_mt5
from apps.utils.data_validator import DataValidator
from apps.backtest import Backtest, Strategy

# Load data from Dukascopy
data = load_dukascopy('EURUSD', start_date='2024-01-01', end_date='2024-12-31')

# Or load from MT5
data = load_mt5('EURUSD', timeframe='H1', count=1000)

# Run backtest
class MyStrategy(Strategy):
    def next(self):
        if self.crossover(self.data.close, self.sma(20)):
            self.buy()

bt = Backtest(data, MyStrategy, cash=10000)
result = bt.run()
print(result.stats)
```

## Loading Best Practices

### 1. Use Caching

```python
# First load - reads from disk
data = load_dukascopy('EURUSD', cache=True)

# Second load - uses memory cache (much faster)
data = load_dukascopy('EURUSD', cache=True)
```

### 2. Filter Date Ranges

```python
# Only load what you need
data = load_dukascopy(
    'EURUSD',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### 3. Validate Data

```python
# Always check data quality
print(f"Loaded {len(data):,} bars")
print(f"Date range: {data.index[0]} to {data.index[-1]}")
print(f"Missing values: {data.isnull().sum().sum()}")
```

### 4. Handle Errors

```python
try:
    data = load_mt5('EURUSD', timeframe='H1', count=1000)
except Exception as e:
    print(f"MT5 failed: {e}")
    # Fallback is automatic in load_mt5()
```

## Troubleshooting

### FileNotFoundError: Data file not found

**Problem**: Dukascopy parquet file doesn't exist.

**Solution**:

1. Check available files in `data/dukascopy/`
2. Download data using the data downloader
3. Verify symbol name matches file name (e.g., 'EURUSD.parquet')

### MT5 Connection Failed

**Problem**: Cannot connect to MetaTrader 5.

**Solution**:

1. Ensure MT5 terminal is running
2. Check credentials in `settings/config.ini`
3. Verify section name: `[MT5-Pepperstone-demo]`
4. The system automatically falls back to Dukascopy

### Missing Required Columns

**Problem**: Data doesn't have required columns.

**Solution**:

```python
from apps.utils.data_validator import DataValidator

# This will standardize columns and add missing ones
data = DataValidator.prepare_data(raw_data)
```

### DatetimeIndex Error

**Problem**: Index is not a DatetimeIndex.

**Solution**:

```python
import pandas as pd

# Convert time column to index
data.index = pd.DatetimeIndex(data['time'])
data = data.drop(columns=['time'])

# Or use DataValidator.prepare_data()
data = DataValidator.prepare_data(data)
```

### Data Not Sorted

**Problem**: Backtest fails because data is not chronologically sorted.

**Solution**:

```python
# Always sort by index
data = data.sort_index()

# Or use DataValidator.prepare_data() which does this automatically
data = DataValidator.prepare_data(data)
```

## Data Sources

### Dukascopy

- **Location**: `data/dukascopy/*.parquet`
- **Format**: Parquet files with M1 tick data
- **Symbols**: Major forex pairs (EURUSD, GBPUSD, USDJPY, etc.)
- **Coverage**: Historical data (varies by symbol)

### MetaTrader 5

- **Connection**: Via MT5 terminal
- **Timeframes**: M1, M5, M15, M30, H1, H4, D1, W1, MN1
- **Symbols**: All symbols available in your MT5 account
- **Coverage**: Real-time + historical (broker-dependent)

### Custom Sources

- **CSV**: Use `pd.read_csv()` + `DataValidator.prepare_data()`
- **API**: Fetch data + convert to DataFrame + `DataValidator.prepare_data()`
- **Database**: Query + convert to DataFrame + `DataValidator.prepare_data()`

## Performance Tips

1. **Use parquet files** for large datasets (faster than CSV)
2. **Enable caching** when loading the same data multiple times
3. **Filter date ranges** to load only what you need
4. **Resample to higher timeframes** if you don't need M1 resolution
5. **Store processed data** to avoid repeated preprocessing

## Support

- **Documentation**: `docs/apps/backtest_user_guide.md`
- **API Reference**: `docs/apps/backtest_api.md`
- **Examples**: `examples/backtest/`
- **Issues**: GitHub Issues
