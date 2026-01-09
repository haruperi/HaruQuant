# Utils Module

A comprehensive collection of utility functions and classes for data management, validation, security, and concurrent execution in the HaruQuant trading platform.

## Overview

The `utils` module provides essential utilities for working with market data, ensuring data quality, managing security, and enabling concurrent task execution. It consists of five main components that handle different aspects of the trading platform's infrastructure.

## Key Features

- **Data Management**: Load and cache market data from multiple sources
- **Data Validation**: Comprehensive quality checks for market data
- **Data Manipulation**: Timeframe resampling and bar aggregation
- **Security**: Password hashing and data encryption
- **Multitasking**: Concurrent execution with thread/process pools

## Architecture

The module consists of five independent utility components:

```
┌──────────────────┐
│  Data Getters    │  ← Load data from MT5/Dukascopy
├──────────────────┤
│  Data Validator  │  ← Validate data quality
├──────────────────┤
│  Data Manipulator│  ← Resample & aggregate bars
├──────────────────┤
│  Security        │  ← Hash passwords & encrypt data
├──────────────────┤
│  Multitasking    │  ← Concurrent task execution
└──────────────────┘
```

---

## 1. Security Utilities

Password hashing and data encryption utilities using industry-standard algorithms.

### Functions

- **`hash_password()`** - Hash passwords using bcrypt
- **`verify_password()`** - Verify password against hash
- **`get_encryption_key()`** - Generate encryption key
- **`encrypt_data()`** - Encrypt string data
- **`decrypt_data()`** - Decrypt encrypted data

### hash_password()

Hash a password using bcrypt.

**Function Signature:**
```python
hash_password(password: str) -> str
```

**Parameters:**
- `password: str` - Plain text password to hash

**Returns:**
- `str` - Hashed password

**Example:**
```python
from apps.utils.security import hash_password

hashed = hash_password("my_secure_password")
print(hashed)  # $2b$12$...
```

### verify_password()

Verify a plain password against a hashed password.

**Function Signature:**
```python
verify_password(plain_password: str, hashed_password: str) -> bool
```

**Parameters:**
- `plain_password: str` - Plain text password
- `hashed_password: str` - Hashed password to verify against

**Returns:**
- `bool` - True if password matches, False otherwise

**Example:**
```python
from apps.utils.security import hash_password, verify_password

hashed = hash_password("my_password")
is_valid = verify_password("my_password", hashed)  # True
is_invalid = verify_password("wrong_password", hashed)  # False
```

### get_encryption_key()

Generate a new Fernet encryption key.

**Function Signature:**
```python
get_encryption_key() -> bytes
```

**Returns:**
- `bytes` - Encryption key

**Example:**
```python
from apps.utils.security import get_encryption_key

key = get_encryption_key()
# Store this key securely - you'll need it to decrypt data
```

### encrypt_data()

Encrypt string data using Fernet symmetric encryption.

**Function Signature:**
```python
encrypt_data(data: str, key: bytes) -> str
```

**Parameters:**
- `data: str` - String data to encrypt
- `key: bytes` - Encryption key

**Returns:**
- `str` - Encrypted data (URL-safe base64 encoded)

**Example:**
```python
from apps.utils.security import get_encryption_key, encrypt_data

key = get_encryption_key()
encrypted = encrypt_data("sensitive_data", key)
print(encrypted)  # gAAAAABh...
```

### decrypt_data()

Decrypt an encrypted string token.

**Function Signature:**
```python
decrypt_data(token: str, key: bytes) -> str
```

**Parameters:**
- `token: str` - Encrypted string token
- `key: bytes` - Encryption key (same key used for encryption)

**Returns:**
- `str` - Decrypted string data

**Example:**
```python
from apps.utils.security import get_encryption_key, encrypt_data, decrypt_data

key = get_encryption_key()
encrypted = encrypt_data("secret_message", key)
decrypted = decrypt_data(encrypted, key)
print(decrypted)  # "secret_message"
```

### Security Example

**Complete Authentication Flow:**

```python
from apps.utils.security import hash_password, verify_password, get_encryption_key, encrypt_data, decrypt_data

# User registration
password = "user_password123"
hashed_password = hash_password(password)

# Generate encryption key for user
encryption_key = get_encryption_key()

# Store sensitive data
api_key = "mt5_api_key_12345"
encrypted_api_key = encrypt_data(api_key, encryption_key)

# User login
login_password = "user_password123"
if verify_password(login_password, hashed_password):
    print("Login successful")

    # Decrypt sensitive data
    decrypted_api_key = decrypt_data(encrypted_api_key, encryption_key)
    print(f"API Key: {decrypted_api_key}")
```

---

## 2. Data Getters

Load and cache market data from multiple sources (MT5, Dukascopy, Parquet files).

### Functions

- **`load_mt5()`** - Load data from MT5 terminal
- **`load_dukascopy()`** - Load data from Dukascopy API
- **`load_parquet()`** - Load data from Parquet file
- **`get_data_dir()`** - Get path to data directory
- **`clear_data_cache()`** - Clear data cache

### load_mt5()

Load data from MT5 connection with automatic fallback to Dukascopy.

**Function Signature:**
```python
load_mt5(symbol: str, timeframe: str = "H1", start_date: Optional[Union[str, datetime]] = None, end_date: Optional[Union[str, datetime]] = None, count: Optional[int] = 0) -> pd.DataFrame
```

**Parameters:**
- `symbol: str` - Trading symbol (e.g., "EURUSD")
- `timeframe: str = "H1"` - Timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
- `start_date: Optional[Union[str, datetime]] = None` - Start date
- `end_date: Optional[Union[str, datetime]] = None` - End date
- `count: Optional[int] = 0` - Number of bars (if dates not specified)

**Returns:**
- `pd.DataFrame` - OHLCV data

**Example:**
```python
from apps.utils.data_getters import load_mt5

# Load last 1000 bars
data = load_mt5("EURUSD", timeframe="H1", count=1000)

# Load by date range
data = load_mt5("EURUSD", timeframe="H1", start_date="2024-01-01", end_date="2024-12-31")
```

### load_dukascopy()

Download data from Dukascopy API.

**Function Signature:**
```python
load_dukascopy(symbol: str, timeframe: Optional[str] = "H1", start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame
```

**Parameters:**
- `symbol: str` - Trading symbol
- `timeframe: Optional[str] = "H1"` - Timeframe
- `start_date: Optional[str] = None` - Start date (YYYY-MM-DD)
- `end_date: Optional[str] = None` - End date (YYYY-MM-DD)

**Returns:**
- `pd.DataFrame` - OHLCV data

**Example:**
```python
from apps.utils.data_getters import load_dukascopy

data = load_dukascopy("EURUSD", timeframe="H1", start_date="2024-01-01", end_date="2024-12-31")
```

### load_parquet()

Load Parquet file with caching.

**Function Signature:**
```python
load_parquet(file_path: Union[str, Path]) -> pd.DataFrame
```

**Parameters:**
- `file_path: Union[str, Path]` - Path to Parquet file

**Returns:**
- `pd.DataFrame` - Loaded data

**Example:**
```python
from apps.utils.data_getters import load_parquet

data = load_parquet("data/eurusd_h1.parquet")
```

---

## 3. Data Validator

Comprehensive data quality validation for market data.

### Class: DataValidator

**Constructor:**
```python
DataValidator(z_score_threshold: float = 3.0, iqr_multiplier: float = 1.5)
```

**Parameters:**
- `z_score_threshold: float = 3.0` - Z-score threshold for spike detection
- `iqr_multiplier: float = 1.5` - IQR multiplier for outlier detection

### Methods

#### prepare_data()

Prepare data for backtesting (standardize column names, add spread).

**Function Signature:**
```python
DataValidator.prepare_data(df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `df: pd.DataFrame` - Raw OHLCV data

**Returns:**
- `pd.DataFrame` - Standardized data with columns: open, high, low, close, volume, spread

**Example:**
```python
from apps.utils.data_validator import DataValidator

validator = DataValidator()
raw_data = load_mt5("EURUSD", "H1", count=1000)
clean_data = validator.prepare_data(raw_data)
```

#### validate_price_sanity()

Validate price sanity checks for OHLCV data.

**Function Signature:**
```python
validate_price_sanity(data: pd.DataFrame, mark_invalid: bool = False) -> Tuple[bool, pd.DataFrame, List[str]]
```

**Parameters:**
- `data: pd.DataFrame` - OHLCV data
- `mark_invalid: bool = False` - Add 'invalid' column marking bad rows

**Returns:**
- `Tuple[bool, pd.DataFrame, List[str]]` - (all_valid, dataframe, issues_list)

**Checks:**
- High >= Low
- Close within [Low, High]
- Open within [Low, High]
- No negative prices
- No zero prices

**Example:**
```python
from apps.utils.data_validator import DataValidator

validator = DataValidator()
all_valid, df, issues = validator.validate_price_sanity(data, mark_invalid=True)

if not all_valid:
    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue}")
```

#### detect_gaps()

Detect gaps in time series data.

**Function Signature:**
```python
detect_gaps(data: pd.DataFrame, expected_frequency: Optional[Union[str, timedelta]] = None, tolerance: float = 1.5) -> Tuple[pd.DataFrame, List[Dict]]
```

**Parameters:**
- `data: pd.DataFrame` - Data with datetime index or time column
- `expected_frequency: Optional[Union[str, timedelta]] = None` - Expected frequency (auto-detected if None)
- `tolerance: float = 1.5` - Tolerance multiplier for gap detection

**Returns:**
- `Tuple[pd.DataFrame, List[Dict]]` - (gaps_dataframe, gap_info_list)

**Example:**
```python
from apps.utils.data_validator import DataValidator

validator = DataValidator()
gaps_df, gap_info = validator.detect_gaps(data, expected_frequency="1H")

print(f"Found {len(gap_info)} gaps")
for gap in gap_info:
    print(f"Gap from {gap['start']} to {gap['end']}: {gap['missing_bars']} bars")
```

#### detect_spikes()

Detect spikes and anomalies in price data.

**Function Signature:**
```python
detect_spikes(data: pd.DataFrame, columns: Optional[List[str]] = None, method: str = "zscore", mark_anomalies: bool = True) -> Tuple[pd.DataFrame, List[Dict]]
```

**Parameters:**
- `data: pd.DataFrame` - Price data
- `columns: Optional[List[str]] = None` - Columns to check (default: all OHLC)
- `method: str = "zscore"` - Detection method ('zscore', 'iqr', or 'both')
- `mark_anomalies: bool = True` - Add anomaly columns to dataframe

**Returns:**
- `Tuple[pd.DataFrame, List[Dict]]` - (dataframe_with_marks, anomaly_list)

**Example:**
```python
from apps.utils.data_validator import DataValidator

validator = DataValidator(z_score_threshold=3.0)
df_marked, anomalies = validator.detect_spikes(data, method="zscore")

print(f"Found {len(anomalies)} anomalies")
for anomaly in anomalies:
    print(f"{anomaly['column']} spike at {anomaly['timestamp']}: {anomaly['value']}")
```

---

## 4. Data Manipulator

Timeframe resampling and bar aggregation utilities.

### Class: TimeframeManager

**Methods:**

#### resample()

Resample OHLCV data to a different timeframe.

**Function Signature:**
```python
resample(data: pd.DataFrame, target_timeframe: str, source_timeframe: Optional[str] = None) -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - OHLCV data with DatetimeIndex
- `target_timeframe: str` - Target timeframe (M5, H1, D1, etc.)
- `source_timeframe: Optional[str] = None` - Source timeframe (auto-detected if None)

**Returns:**
- `pd.DataFrame` - Resampled data

**Example:**
```python
from apps.utils.data_manipulator import TimeframeManager

manager = TimeframeManager()

# Resample M1 data to H1
m1_data = load_mt5("EURUSD", "M1", count=10000)
h1_data = manager.resample(m1_data, "H1")

# Resample to multiple timeframes
m5_data = manager.resample(m1_data, "M5")
h4_data = manager.resample(m1_data, "H4")
d1_data = manager.resample(m1_data, "D1")
```

### Class: BarAggregator

Incremental bar aggregator for live trading.

**Constructor:**
```python
BarAggregator(target_timeframe: str)
```

**Parameters:**
- `target_timeframe: str` - Target timeframe for aggregated bars

**Methods:**

#### add_tick()

Add a tick to the aggregator.

**Function Signature:**
```python
add_tick(timestamp: datetime, bid: float, ask: float, volume: float = 0) -> Optional[Dict]
```

**Parameters:**
- `timestamp: datetime` - Tick timestamp
- `bid: float` - Bid price
- `ask: float` - Ask price
- `volume: float = 0` - Tick volume

**Returns:**
- `Optional[Dict]` - Completed bar if bar finished, None otherwise

**Example:**
```python
from apps.utils.data_manipulator import BarAggregator
from datetime import datetime

aggregator = BarAggregator("M5")

# Add ticks
completed_bar = aggregator.add_tick(datetime.now(), 1.0950, 1.0952, 100)
if completed_bar:
    print(f"Bar completed: {completed_bar}")
```

---

## 5. Multitasking Utilities

Concurrent task execution with thread/process pools.

### Functions

- **`@task`** - Decorator to make function asynchronous
- **`createPool()`** - Create execution pool
- **`set_max_threads()`** - Set maximum concurrent threads
- **`wait_for_tasks()`** - Wait for all tasks to complete
- **`get_active_tasks()`** - Get currently running tasks

### @task Decorator

Convert a function into an asynchronous task.

**Example:**
```python
from apps.utils.multitasking import task, wait_for_tasks

@task
def process_symbol(symbol):
    data = load_mt5(symbol, "H1", count=1000)
    # Process data...
    return f"Processed {symbol}"

# Run tasks concurrently
process_symbol("EURUSD")
process_symbol("GBPUSD")
process_symbol("USDJPY")

# Wait for all to complete
wait_for_tasks()
```

### createPool()

Create a new execution pool.

**Function Signature:**
```python
createPool(name: str = "main", threads: Optional[int] = None, engine: Optional[str] = None) -> None
```

**Parameters:**
- `name: str = "main"` - Pool name
- `threads: Optional[int] = None` - Max concurrent threads (default: CPU count)
- `engine: Optional[str] = None` - Engine type ("thread" or "process")

**Example:**
```python
from apps.utils.multitasking import createPool, task, wait_for_tasks

# Create pool with 4 threads
createPool("data_processing", threads=4, engine="thread")

@task
def download_data(symbol):
    return load_dukascopy(symbol, "H1", "2024-01-01", "2024-12-31")

# Process multiple symbols
symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
for symbol in symbols:
    download_data(symbol)

wait_for_tasks()
```

---

## Common Patterns

### Complete Data Pipeline

```python
from apps.utils.data_getters import load_mt5
from apps.utils.data_validator import DataValidator
from apps.utils.data_manipulator import TimeframeManager

# 1. Load data
data = load_mt5("EURUSD", "M1", count=100000)

# 2. Validate data
validator = DataValidator()
clean_data = validator.prepare_data(data)

all_valid, df, issues = validator.validate_price_sanity(clean_data)
if not all_valid:
    print(f"Data quality issues: {len(issues)}")

# 3. Detect anomalies
df_marked, anomalies = validator.detect_spikes(df, method="zscore")
print(f"Found {len(anomalies)} anomalies")

# 4. Resample to multiple timeframes
manager = TimeframeManager()
h1_data = manager.resample(df_marked, "H1")
h4_data = manager.resample(df_marked, "H4")
d1_data = manager.resample(df_marked, "D1")
```

### Concurrent Data Processing

```python
from apps.utils.multitasking import createPool, task, wait_for_tasks
from apps.utils.data_getters import load_dukascopy
from apps.utils.data_validator import DataValidator

# Create processing pool
createPool("data_download", threads=8)

@task
def process_symbol(symbol):
    # Download data
    data = load_dukascopy(symbol, "H1", "2024-01-01", "2024-12-31")

    # Validate
    validator = DataValidator()
    clean_data = validator.prepare_data(data)

    # Check quality
    all_valid, df, issues = validator.validate_price_sanity(clean_data)

    return {
        "symbol": symbol,
        "rows": len(df),
        "valid": all_valid,
        "issues": len(issues)
    }

# Process multiple symbols concurrently
symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
for symbol in symbols:
    process_symbol(symbol)

# Wait for completion
wait_for_tasks()
```

### Secure Credential Management

```python
from apps.utils.security import hash_password, get_encryption_key, encrypt_data, decrypt_data
from apps.sqlite import DatabaseManager

# Initialize database
db = DatabaseManager()

# Create user with hashed password
password = "user_password"
hashed_password = hash_password(password)
encryption_key = get_encryption_key()

user_id = db.create_user(
    email="trader@example.com",
    username="trader",
    password=password,  # Will be hashed automatically
    encryption_key=encryption_key
)

# Encrypt sensitive credentials
mt5_password = "mt5_password123"
encrypted_mt5_password = encrypt_data(mt5_password, encryption_key)

# Store encrypted credentials
db.update_user_settings(
    user_id=user_id,
    broker_credentials={
        "mt5_account": "12345",
        "mt5_password": encrypted_mt5_password,
        "mt5_server": "Demo-Server"
    }
)

# Later: Retrieve and decrypt
user = db.get_user(user_id=user_id)
settings = db.get_user_settings(user_id)
encrypted_password = settings["broker_credentials"]["mt5_password"]
decrypted_password = decrypt_data(encrypted_password, user["encryption_key"])
```

---

## Best Practices

### Data Management
1. **Use caching**: Load data once and cache it
2. **Validate early**: Always validate data before processing
3. **Handle missing data**: Check for gaps and missing timestamps
4. **Resample carefully**: Only resample to larger timeframes
5. **Monitor quality**: Regularly check for spikes and anomalies

### Security
1. **Never store plain passwords**: Always use `hash_password()`
2. **Secure encryption keys**: Store keys securely (environment variables, secrets manager)
3. **Use same key**: Use the same encryption key for encrypt/decrypt
4. **Rotate keys**: Periodically rotate encryption keys
5. **Validate inputs**: Always validate user inputs before hashing/encrypting

### Multitasking
1. **Choose appropriate pool size**: Don't exceed CPU count for CPU-bound tasks
2. **Use threads for I/O**: Use thread pools for network/disk operations
3. **Use processes for CPU**: Use process pools for computation-heavy tasks
4. **Wait for completion**: Always call `wait_for_tasks()` before exiting
5. **Handle errors**: Wrap task functions in try-except blocks

## License

Copyright 2025, HaruQuant

## See Also

- `apps/mt5/` - MT5 client for data retrieval
- `apps/dukascopy_api/` - Dukascopy API client
- `apps/sqlite/` - Database management
- `apps/indicator/` - Technical indicators
