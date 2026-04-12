# Utils Module

A comprehensive collection of utility functions and classes for data management, validation, security, file operations, and concurrent execution in the HaruQuant algorithmic trading platform.

## Overview

The `utils` module provides essential utilities for all aspects of the trading platform, from data loading and validation to security management and concurrent processing. It consists of independent components that handle different infrastructure concerns.

### Key Features

- **Security**: Password hashing and encryption using industry-standard algorithms (bcrypt, Fernet)
- **Data Loading**: Multi-source data retrieval from MT5, Dukascopy, and Parquet files
- **Data Validation**: Comprehensive quality checks for market data (gaps, spikes, sanity)
- **Data Manipulation**: Timeframe resampling and real-time bar aggregation
- **Multitasking**: Concurrent task execution with thread/process pools
- **File Operations**: Batch file renaming with regex and pattern matching
- **Data Comparison**: DataFrame comparison utilities for testing and validation
- **Error Handling**: MT5 error code descriptions and lookups
- **Trade Validation**: Comprehensive trading parameter validation
- **Task Scheduling**: Background job scheduling with cron triggers for automated maintenance
- **Logging**: Structured logging with terminal output and default rotating file sinks

## Architecture

### Module Structure

```
apps/utils/
├── __init__.py             # Package exports
├── security.py             # Password hashing & encryption
├── data_getters.py         # Multi-source data loading
├── data_validator.py       # Data quality validation
├── data_manipulator.py     # Timeframe resampling & aggregation
├── multitasking.py         # Concurrent execution utilities
├── file_renamer.py         # Batch file renaming
├── data_comparator.py      # DataFrame comparison
├── error_description.py    # MT5 error code descriptions
├── validate.py             # Trading parameter validation
├── logger.py               # Structured logging adapter and sink management
└── scheduler.py            # Background job scheduling
```

### Component Overview

```
┌─────────────────────┐
│  Security           │  ← Password hashing & encryption
├─────────────────────┤
│  Data Getters       │  ← Load from MT5/Dukascopy/Parquet
├─────────────────────┤
│  Data Validator     │  ← Quality checks & validation
├─────────────────────┤
│  Data Manipulator   │  ← Resample & aggregate bars
├─────────────────────┤
│  Multitasking       │  ← Concurrent execution
├─────────────────────┤
│  File Renamer       │  ← Batch file operations
├─────────────────────┤
│  Data Comparator    │  ← DataFrame comparison
├─────────────────────┤
│  Error Description  │  ← MT5 error lookups
├─────────────────────┤
│  Validate           │  ← Trading param validation
├─────────────────────┤
│  Scheduler          │  ← Background job scheduling
└─────────────────────┘
```

## Installation & Setup

### Basic Setup

```python
# Import individual modules
from backend.common.security import hash_password, encrypt_data
from backend.services.market_data.data_getters import load_mt5, load_dukascopy
from backend.services.market_data.data_validator import DataValidator
from backend.services.market_data.data_manipulator import TimeframeManager
from backend.common.multitasking import task, wait_for_tasks

# Ready to use - no initialization needed
validator = DataValidator()
tf_manager = TimeframeManager()
```

## Components

### 1. Security (`security.py`)

**Purpose**: Cryptographic functions for password hashing and data encryption using bcrypt and Fernet.

**Key Functions**:

| Function                 | Signature                             | Description                    |
| ------------------------ | ------------------------------------- | ------------------------------ |
| `hash_password()`      | `(password: str) -> str`            | Hash password with bcrypt      |
| `verify_password()`    | `(plain: str, hashed: str) -> bool` | Verify password against hash   |
| `get_encryption_key()` | `() -> bytes`                       | Generate Fernet encryption key |
| `encrypt_data()`       | `(data: str, key: bytes) -> str`    | Encrypt string data            |
| `decrypt_data()`       | `(token: str, key: bytes) -> str`   | Decrypt encrypted data         |

**Usage**:

```python
from backend.common.security import hash_password, verify_password, get_encryption_key, encrypt_data, decrypt_data

# Hash password
hashed = hash_password("my_password")

# Verify password
is_valid = verify_password("my_password", hashed)  # True

# Encrypt sensitive data
key = get_encryption_key()
encrypted = encrypt_data("api_key_12345", key)
decrypted = decrypt_data(encrypted, key)  # "api_key_12345"
```

For detailed examples, see [`tests/usage/utils/usage_security.py`](../../../tests/usage/utils/usage_security.py).

---

### 2. Data Getters (`data_getters.py`)

**Purpose**: Load and cache market data from multiple sources (MT5, Dukascopy API, Parquet files).

**Key Functions**:

| Function               | Signature                                                                      | Description                |
| ---------------------- | ------------------------------------------------------------------------------ | -------------------------- |
| `load_mt5()`         | `(symbol: str, timeframe: str, start_date, end_date, count) -> pd.DataFrame` | Load from MT5 terminal     |
| `load_dukascopy()`   | `(symbol: str, timeframe: str, start_date, end_date) -> pd.DataFrame`        | Load from Dukascopy API    |
| `load_parquet()`     | `(file_path: Union[str, Path]) -> pd.DataFrame`                              | Load from Parquet file     |
| `get_data_dir()`     | `() -> Path`                                                                 | Get path to data directory |
| `clear_data_cache()` | `() -> None`                                                                 | Clear cached data          |

**Usage**:

```python
from backend.services.market_data.data_getters import load_mt5, load_dukascopy, load_parquet

# Load from MT5 (last 1000 bars)
data = load_mt5("EURUSD", timeframe="H1", count=1000)

# Load by date range
data = load_mt5("EURUSD", "H1", start_date="2024-01-01", end_date="2024-12-31")

# Load from Dukascopy API
data = load_dukascopy("EURUSD", "H1", "2024-01-01", "2024-12-31")

# Load from Parquet file (with caching)
data = load_parquet("backend/data/raw/eurusd_h1.parquet")
```

For detailed examples, see [`tests/usage/utils/usage_data_getters.py`](../../../tests/usage/utils/usage_data_getters.py).

---

### 3. Data Validator (`data_validator.py`)

**Purpose**: Comprehensive data quality validation for OHLCV market data.

**Class: DataValidator**

**Constructor**:

```python
DataValidator(z_score_threshold: float = 3.0, iqr_multiplier: float = 1.5)
```

**Key Methods**:

| Method                      | Signature                                                                                    | Description                         |
| --------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------- |
| `prepare_data()`          | `(df: pd.DataFrame) -> pd.DataFrame`                                                       | Standardize column names and format |
| `validate_price_sanity()` | `(data: pd.DataFrame, mark_invalid: bool) -> Tuple[bool, pd.DataFrame, List[str]]`         | Validate OHLC relationships         |
| `detect_gaps()`           | `(data: pd.DataFrame, expected_frequency, tolerance) -> Tuple[pd.DataFrame, List[Dict]]`   | Detect missing timestamps           |
| `detect_spikes()`         | `(data: pd.DataFrame, columns, method, mark_anomalies) -> Tuple[pd.DataFrame, List[Dict]]` | Detect price anomalies              |

**Validation Checks**:

- **Price Sanity**: High >= Low, Close/Open within [Low, High], no negatives/zeros
- **Gaps**: Missing timestamps based on expected frequency
- **Spikes**: Statistical anomalies using Z-score or IQR methods

**Usage**:

```python
from backend.services.market_data.data_validator import DataValidator

validator = DataValidator(z_score_threshold=3.0, iqr_multiplier=1.5)

# Prepare and standardize data
clean_data = validator.prepare_data(raw_data)

# Validate price sanity
all_valid, df, issues = validator.validate_price_sanity(clean_data, mark_invalid=True)
if not all_valid:
    print(f"Found {len(issues)} price issues")

# Detect gaps
gaps_df, gap_info = validator.detect_gaps(df, expected_frequency="1H")
print(f"Found {len(gap_info)} gaps")

# Detect spikes
df_marked, anomalies = validator.detect_spikes(df, method="zscore")
print(f"Found {len(anomalies)} anomalies")
```

For detailed examples, see [`tests/usage/utils/usage_data_validator.py`](../../../tests/usage/utils/usage_data_validator.py).

---

### 4. Data Manipulator (`data_manipulator.py`)

**Purpose**: Timeframe resampling and real-time bar aggregation for multi-timeframe analysis.

**Class: TimeframeManager**

**Key Methods**:

| Method         | Signature                                                                         | Description                     |
| -------------- | --------------------------------------------------------------------------------- | ------------------------------- |
| `resample()` | `(data: pd.DataFrame, target_timeframe: str, source_timeframe) -> pd.DataFrame` | Resample to different timeframe |

**Class: BarAggregator**

**Constructor**:

```python
BarAggregator(target_timeframe: str)
```

**Key Methods**:

| Method                | Signature                                                                          | Description                    |
| --------------------- | ---------------------------------------------------------------------------------- | ------------------------------ |
| `add_tick()`        | `(timestamp: datetime, bid: float, ask: float, volume: float) -> Optional[Dict]` | Add tick and get completed bar |
| `get_current_bar()` | `() -> Optional[Dict]`                                                           | Get current incomplete bar     |
| `reset()`           | `() -> None`                                                                     | Reset aggregator state         |

**Supported Timeframes**: M1, M5, M15, M30, H1, H4, D1, W1, MN1

**Usage**:

```python
from backend.services.market_data.data_manipulator import TimeframeManager, BarAggregator

# Resample M1 data to H1
manager = TimeframeManager()
m1_data = load_mt5("EURUSD", "M1", count=10000)
h1_data = manager.resample(m1_data, "H1")
h4_data = manager.resample(m1_data, "H4")

# Real-time bar aggregation for live trading
aggregator = BarAggregator("M5")

# Add ticks
completed_bar = aggregator.add_tick(datetime.now(), 1.0950, 1.0952, 100)
if completed_bar:
    print(f"M5 bar completed: {completed_bar}")
```

For detailed examples, see [`tests/usage/utils/usage_data_manipulator.py`](../../../tests/usage/utils/usage_data_manipulator.py).

---

### 5. Multitasking (`multitasking.py`)

**Purpose**: Concurrent task execution with thread and process pools for parallel processing.

**Key Functions**:

| Function               | Signature                                          | Description                    |
| ---------------------- | -------------------------------------------------- | ------------------------------ |
| `@task`              | Decorator                                          | Convert function to async task |
| `createPool()`       | `(name: str, threads: int, engine: str) -> None` | Create execution pool          |
| `set_max_threads()`  | `(threads: int) -> None`                         | Set max concurrent threads     |
| `wait_for_tasks()`   | `() -> None`                                     | Wait for all tasks to complete |
| `get_active_tasks()` | `() -> List`                                     | Get currently running tasks    |

**Engines**: `"thread"` (I/O-bound), `"process"` (CPU-bound)

**Usage**:

```python
from backend.common.multitasking import task, createPool, wait_for_tasks

# Create pool
createPool("data_processing", threads=4, engine="thread")

# Define async task
@task
def process_symbol(symbol):
    data = load_mt5(symbol, "H1", count=1000)
    # Process data...
    return f"Processed {symbol}"

# Execute tasks concurrently
symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
for symbol in symbols:
    process_symbol(symbol)

# Wait for completion
wait_for_tasks()
```

For detailed examples, see [`tests/usage/utils/usage_multitasking.py`](../../../tests/usage/utils/usage_multitasking.py).

---

### 6. File Renamer (`file_renamer.py`)

**Purpose**: Batch file renaming utilities with pattern matching, regex, and various transformations.

**Key Functions**:

| Function                          | Signature                                                                                                | Description                 |
| --------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------- |
| `rename_file()`                 | `(old_path, new_path, overwrite, dry_run) -> bool`                                                     | Rename single file          |
| `rename_with_pattern()`         | `(directory, pattern, replacement, regex, recursive, extensions, dry_run) -> Dict`                     | Pattern-based renaming      |
| `add_prefix()`                  | `(directory, prefix, recursive, extensions, dry_run) -> Dict`                                          | Add prefix to filenames     |
| `add_suffix()`                  | `(directory, suffix, recursive, extensions, dry_run) -> Dict`                                          | Add suffix before extension |
| `rename_with_numbering()`       | `(directory, base_name, start_number, padding, recursive, extensions, dry_run) -> Dict`                | Sequential numbering        |
| `normalize_filenames()`         | `(directory, lowercase, replace_spaces, remove_special_chars, recursive, extensions, dry_run) -> Dict` | Normalize filenames         |
| `change_extension()`            | `(directory, old_extension, new_extension, recursive, dry_run) -> Dict`                                | Change file extensions      |
| `rename_with_custom_function()` | `(directory, rename_function, recursive, extensions, dry_run) -> Dict`                                 | Custom renaming logic       |

**Usage**:

```python
from backend.scripts.tools.file_renamer import rename_with_pattern, add_prefix, normalize_filenames

# Pattern-based renaming with regex
renamed = rename_with_pattern(
    directory="backend/data/raw/",
    pattern=r"(.+)_dukascopy-H1-No Session\.csv",
    replacement=r"\1_H1.csv",
    regex=True,
    dry_run=False
)

# Add prefix to all CSV files
renamed = add_prefix("backend/data/raw/processed/", "backtest_", extensions=[".csv"])

# Normalize filenames (lowercase, replace spaces, remove special chars)
renamed = normalize_filenames("backend/data/", lowercase=True, replace_spaces="_")
```

For detailed examples, see [`tests/usage/utils/usage_file_renamer.py`](../../../tests/usage/utils/usage_file_renamer.py).

---

### 7. Data Comparator (`data_comparator.py`)

**Purpose**: DataFrame comparison utilities for testing data equality and validating transformations.

**Key Functions**:

| Function                           | Signature                                                                           | Description                        |
| ---------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------- |
| `compare_dataframes()`           | `(df1, df2, columns, tolerance, check_index, align_by_datetime, verbose) -> bool` | Compare DataFrames with tolerance  |
| `align_dataframes_by_datetime()` | `(df1, df2, verbose) -> Tuple[pd.DataFrame, pd.DataFrame]`                        | Align DataFrames by datetime index |
| `compare_ohlcv()`                | `(df1, df2, **kwargs) -> bool`                                                    | Compare OHLCV columns              |
| `compare_ohlc()`                 | `(df1, df2, **kwargs) -> bool`                                                    | Compare OHLC columns               |

**Features**:

- Tolerance-based floating point comparison
- Datetime index alignment
- Partial column comparison
- Detailed difference reporting

**Usage**:

```python
from backend.services.market_data.data_comparator import compare_dataframes, compare_ohlcv, align_dataframes_by_datetime

# Compare specific columns with tolerance
is_equal = compare_dataframes(
    df1, df2,
    columns=['Open', 'High', 'Low', 'Close'],
    tolerance=1e-5,
    verbose=True
)

# Compare OHLCV data
is_equal = compare_ohlcv(df1, df2, tolerance=1e-5, align_by_datetime=True, verbose=True)

# Align by datetime before comparison
df1_aligned, df2_aligned = align_dataframes_by_datetime(df1, df2, verbose=True)
```

For detailed examples, see [`tests/usage/utils/usage_data_comparator.py`](../../../tests/usage/utils/usage_data_comparator.py).

---

### 8. Error Description (`error_description.py`)

**Purpose**: MT5 error code descriptions and lookup for debugging trading operations.

**Class: TradeErrorDescriptions**

**Key Methods**:

| Method                  | Signature                  | Description                    |
| ----------------------- | -------------------------- | ------------------------------ |
| `error_description()` | `(err_code: int) -> str` | Get error description for code |

**Error Categories**:

- **Runtime Errors** (0-14): Internal errors, memory issues
- **Chart Errors** (4001-4015): Chart operations
- **Symbol Errors** (4301-4305): Symbol not found, MarketWatch issues
- **Trade Errors** (4701-4707, 10004-10036): Trading operations
- **File Errors** (5001-5026): File operations
- **Technical Errors** (4401-5613): History, indicators, OpenCL

**Usage**:

```python
from backend.common.error_descriptions import TradeErrorDescriptions

error_desc = TradeErrorDescriptions()

# Get error description
desc = error_desc.error_description(10019)  # "There is not enough money to complete the request"
desc = error_desc.error_description(4301)   # "Unknown symbol"
desc = error_desc.error_description(10013)  # "Invalid request"
```

For detailed examples, see [`tests/usage/utils/usage_error_description.py`](../../../tests/usage/utils/usage_error_description.py).

---

### 9. Validate (`validate.py`)

**Purpose**: Comprehensive trading parameter validation for MT5 trading operations.

**Class: TradeValidator**

**Constructor**:

```python
TradeValidator(client=None, logger_instance=None, mt5_instance=None)
```

**Key Methods**:

| Method                       | Signature                                                            | Description              |
| ---------------------------- | -------------------------------------------------------------------- | ------------------------ |
| `validate()`               | `(validation_type: str, value: Any, **kwargs) -> Tuple[bool, str]` | Master validation method |
| `validate_multiple()`      | `(validations: List[Dict]) -> Tuple[bool, List[str]]`              | Batch validation         |
| `get_validation_rules()`   | `() -> Dict`                                                       | Get validation rules     |
| `update_validation_rule()` | `(rule_type, rule_name, value) -> None`                            | Update validation rule   |

**Validation Types**:

- `symbol` - Trading symbol
- `volume` - Trade volume with symbol limits
- `price` - Price value and tick alignment
- `stop_loss` - SL level validation
- `take_profit` - TP level validation
- `order_type` - Order type (BUY, SELL, LIMIT, STOP)
- `magic` - Magic number
- `deviation` - Price deviation
- `expiration` - Order expiration time
- `timeframe` - Timeframe validity
- `date_range` - Date range validation
- `trade_request` - Complete trade request
- `credentials` - MT5 credentials
- `margin` - Margin sufficiency
- `ticket` - Ticket number
- `freeze_level` - Freeze level constraints
- `max_orders` - Order limit
- `symbol_volume` - Per-symbol volume limit

**Usage**:

```python
from backend.services.execution.trade_validators import TradeValidator

validator = TradeValidator()

# Validate symbol
valid, msg = validator.validate('symbol', 'EURUSD')

# Validate volume with symbol limits
valid, msg = validator.validate('volume', 0.1, symbol='EURUSD')

# Validate stop loss
valid, msg = validator.validate('stop_loss', 1.0820, entry_price=1.0850, order_type='BUY', symbol='EURUSD')

# Validate complete trade request
request = {
    'action': 'BUY',
    'symbol': 'EURUSD',
    'volume': 0.1,
    'type': 'BUY',
    'price': 1.0850,
    'sl': 1.0820,
    'tp': 1.0910
}
valid, msg = validator.validate('trade_request', request)

# Batch validation
validations = [
    {'type': 'symbol', 'value': 'EURUSD'},
    {'type': 'volume', 'value': 0.1, 'symbol': 'EURUSD'},
    {'type': 'price', 'value': 1.0850, 'symbol': 'EURUSD'}
]
all_valid, errors = validator.validate_multiple(validations)
```

For detailed examples, see [`tests/usage/utils/usage_validate.py`](../../../tests/usage/utils/usage_validate.py).

---

### 10. Scheduler (`scheduler.py`)

**Purpose**: Background job scheduling using APScheduler for automated maintenance tasks like database cleanup.

**Key Functions**:

| Function                 | Signature      | Description                                         |
| ------------------------ | -------------- | --------------------------------------------------- |
| `start_scheduler()`    | `() -> None` | Start the background scheduler with configured jobs |
| `shutdown_scheduler()` | `() -> None` | Gracefully stop the background scheduler            |

**Scheduler Configuration**:

The scheduler is configured with the following background jobs:

| Job ID                          | Function                               | Schedule         | Description                                   |
| ------------------------------- | -------------------------------------- | ---------------- | --------------------------------------------- |
| `cleanup_simulation_sessions` | `_cleanup_old_simulation_sessions()` | Daily at 3:00 AM | Deletes simulation sessions older than 7 days |

**Features**:

- **AsyncIO Integration**: Works seamlessly with FastAPI's async framework
- **Cron Triggers**: Flexible scheduling using cron expressions
- **Idempotent Operations**: Safe to call `start_scheduler()` multiple times
- **Graceful Shutdown**: Properly stops all jobs on shutdown
- **Automatic Cleanup**: Prevents database bloat from old simulation data

**Import Note**: Due to circular dependency prevention, scheduler must be imported directly from the module:

```python
# Direct import (required to avoid circular dependencies)
from backend.api.legacy.scheduler import start_scheduler, shutdown_scheduler

# NOT from the package: from backend.api.legacy import start_scheduler  # This won't work
```

**Usage**:

```python
from backend.api.legacy.scheduler import start_scheduler, shutdown_scheduler

# Start the scheduler (typically on application startup)
start_scheduler()
# Scheduler is now running and will execute jobs on schedule

# Shutdown the scheduler (typically on application shutdown)
shutdown_scheduler()
```

**FastAPI Integration**:

```python
from fastapi import FastAPI
from backend.api.legacy.scheduler import start_scheduler, shutdown_scheduler

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    shutdown_scheduler()
```

**Adding Custom Jobs** (modify scheduler.py):

```python
from apscheduler.triggers.cron import CronTrigger

def _my_custom_job():
    """Your custom background job."""
    # Job logic here
    pass

def start_scheduler():
    if _scheduler.running:
        return

    # Add custom job
    _scheduler.add_job(
        _my_custom_job,
        CronTrigger(hour=12, minute=0),  # Run at noon
        id="my_custom_job",
        replace_existing=True,
    )

    _scheduler.start()
```

**Common Cron Patterns**:

```python
# Every hour
CronTrigger(minute=0)

# Every 30 minutes
CronTrigger(minute='*/30')

# Weekdays at noon
CronTrigger(day_of_week='mon-fri', hour=12)

# First day of month
CronTrigger(day=1, hour=0, minute=0)

# Multiple times per day
CronTrigger(hour='6,12,18', minute=0)
```

**Scheduled Cleanup Details**:

- **Target**: Simulation sessions table in SQLite database
- **Retention**: 7 days (configurable)
- **Execution Time**: 3:00 AM server time (off-peak hours)
- **Logging**: Logs number of deleted sessions
- **Error Handling**: Failed jobs don't crash the scheduler

**Production Considerations**:

1. **Timezone**: Ensure server timezone is correctly configured
2. **Single Instance**: Only run one scheduler instance in multi-server deployments
3. **Monitoring**: Log all job executions and monitor for failures
4. **Performance**: Schedule resource-intensive jobs during off-peak hours
5. **Database Locks**: Cleanup jobs should handle database locks gracefully


### 11. Logger (`logger.py`)

**Purpose**: Unified logger adapter for Python modules with structured records, redaction, runtime sink management, and default file persistence.

**Default Outputs**:

- Terminal output via `stderr`
- File outputs under `backend/logs/`:
  - `app.log` (`INFO` and above)
  - `debug.log` (`DEBUG` and above)
  - `errors.log` (`ERROR` and above)
  - `access.log` (`INFO` and above; access/http-style records)

**Rotation Policy**:

- Rotates at UTC midnight or 50 MB, whichever comes first
- Keeps 30 rotated backups per file

**Core APIs**:

- `logger.debug/info/success/warning/error/critical/exception(...)`
- `logger.bind(**fields)` and `logger.contextualize(**fields)`
- `logger.add(sink, ...)` and `logger.remove(handler_id=None)`
- `logger.set_min_level(level)` and `logger.set_component_level(component, level)`
- `logger.flush()`

**Usage**:

```python
from backend.common.logger import logger

logger.info("service started", component="app")
logger.error("trade rejected", component="risk", order_id=12345)

access_logger = logger.bind(component="access", method="GET", path="/health")
access_logger.info("request served", status_code=200)
```

For operational details, see [`docs/haruquant/usage/ops/logging.md`](../../../docs/haruquant/usage/ops/logging.md).

---

## Common Patterns

### Complete Data Pipeline

```python
from backend.services.market_data.data_getters import load_mt5
from backend.services.market_data.data_validator import DataValidator
from backend.services.market_data.data_manipulator import TimeframeManager

# 1. Load data
data = load_mt5("EURUSD", "M1", count=100000)

# 2. Validate data
validator = DataValidator()
clean_data = validator.prepare_data(data)
all_valid, df, issues = validator.validate_price_sanity(clean_data)

# 3. Detect anomalies
df_marked, anomalies = validator.detect_spikes(df, method="zscore")

# 4. Resample to multiple timeframes
manager = TimeframeManager()
h1_data = manager.resample(df_marked, "H1")
h4_data = manager.resample(df_marked, "H4")
d1_data = manager.resample(df_marked, "D1")
```

### Concurrent Data Processing

```python
from backend.common.multitasking import createPool, task, wait_for_tasks
from backend.services.market_data.data_getters import load_dukascopy
from backend.services.market_data.data_validator import DataValidator

createPool("data_download", threads=8, engine="thread")

@task
def process_symbol(symbol):
    data = load_dukascopy(symbol, "H1", "2024-01-01", "2024-12-31")
    validator = DataValidator()
    clean_data = validator.prepare_data(data)
    all_valid, df, issues = validator.validate_price_sanity(clean_data)
    return {"symbol": symbol, "rows": len(df), "valid": all_valid}

symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
for symbol in symbols:
    process_symbol(symbol)

wait_for_tasks()
```

### Secure Credential Management

```python
from backend.common.security import hash_password, get_encryption_key, encrypt_data, decrypt_data

# Hash password
hashed_password = hash_password("user_password")

# Encrypt API credentials
encryption_key = get_encryption_key()
mt5_password = "mt5_password123"
encrypted_mt5_password = encrypt_data(mt5_password, encryption_key)

# Store encrypted credentials (in database or config)
credentials = {
    "mt5_account": "12345",
    "mt5_password": encrypted_mt5_password,
    "mt5_server": "Demo-Server"
}

# Later: Retrieve and decrypt
decrypted_password = decrypt_data(credentials["mt5_password"], encryption_key)
```

### Trade Validation Pipeline

```python
from backend.services.execution.trade_validators import TradeValidator

validator = TradeValidator()

# Validate all trade parameters before sending
trade_params = {
    'symbol': 'EURUSD',
    'volume': 0.1,
    'order_type': 'BUY',
    'price': 1.0850,
    'sl': 1.0820,
    'tp': 1.0910
}

# Batch validation
validations = [
    {'type': 'symbol', 'value': trade_params['symbol']},
    {'type': 'volume', 'value': trade_params['volume'], 'symbol': trade_params['symbol']},
    {'type': 'price', 'value': trade_params['price'], 'symbol': trade_params['symbol']},
    {'type': 'stop_loss', 'value': trade_params['sl'], 'entry_price': trade_params['price'],
     'order_type': trade_params['order_type'], 'symbol': trade_params['symbol']},
    {'type': 'take_profit', 'value': trade_params['tp'], 'entry_price': trade_params['price'],
     'order_type': trade_params['order_type'], 'symbol': trade_params['symbol']}
]

all_valid, errors = validator.validate_multiple(validations)
if all_valid:
    # Execute trade
    pass
else:
    print(f"Validation failed: {errors}")
```

## Usage Examples

Comprehensive usage examples are available in `tests/usage/utils/`:

- `usage_security.py`: Security utilities (hashing, encryption)
- `usage_data_getters.py`: Data loading from multiple sources
- `usage_data_validator.py`: Data quality validation
- `usage_data_manipulator.py`: Timeframe resampling and aggregation
- `usage_multitasking.py`: Concurrent task execution
- `usage_file_renamer.py`: Batch file renaming operations
- `usage_data_comparator.py`: DataFrame comparison utilities
- `usage_error_description.py`: MT5 error code lookups
- `../logger/*`: Logger behavior and sink usage examples

## Best Practices

### Data Management

1. **Validate Early**: Always validate data before processing
2. **Use Caching**: Load data once and cache it
3. **Handle Gaps**: Check for and address missing timestamps
4. **Resample Wisely**: Only resample to larger timeframes
5. **Monitor Quality**: Regularly check for spikes and anomalies

### Security

1. **Never Store Plain Passwords**: Always use `hash_password()`
2. **Secure Keys**: Store encryption keys in environment variables or secrets manager
3. **Consistent Keys**: Use same encryption key for encrypt/decrypt
4. **Rotate Keys**: Periodically rotate encryption keys
5. **Validate Inputs**: Always validate before hashing/encrypting

### Multitasking

1. **Right Pool Size**: Don't exceed CPU count for CPU-bound tasks
2. **Thread vs Process**: Use threads for I/O, processes for CPU-intensive work
3. **Wait for Completion**: Always call `wait_for_tasks()` before exiting
4. **Handle Errors**: Wrap task functions in try-except blocks
5. **Monitor Resources**: Use `get_active_tasks()` to monitor execution

### Validation

1. **Validate Before Trade**: Always validate parameters before MT5 operations
2. **Batch Validation**: Use `validate_multiple()` for efficiency
3. **Check Margins**: Always validate margin before opening positions
4. **Respect Freeze Levels**: Check freeze level constraints for pending orders
5. **Handle Errors Gracefully**: Log validation errors for debugging

## Testing

### Unit Testing

Run individual usage examples:

```bash
python backend/scripts/examples/usage_security.py
python backend/scripts/examples/utils/usage_data_getters.py
python backend/scripts/examples/utils/usage_data_validator.py
# ... etc
```

### Integration Testing

See `backend/scripts/examples/utils/` for comprehensive integration examples.

## License

Copyright 2025, HaruQuant

## See Also

- `apps/mt5/` - MT5 client for data retrieval
- `apps/dukascopy_api/` - Dukascopy API client
- `apps/sqlite/` - Database management
- `apps/indicator/` - Technical indicators
- `apps/backtest/` - Backtesting engine


