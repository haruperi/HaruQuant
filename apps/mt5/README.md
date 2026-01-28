# MT5 Module

A comprehensive Python library for interacting with MetaTrader 5 terminal, providing connection management, market data retrieval, and real-time streaming capabilities.

## Overview

The `mt5` module provides a robust interface for connecting to and managing MetaTrader 5 terminal connections. It supports connection management, auto-reconnection, multi-account handling, event-driven architecture, and comprehensive market data retrieval.

## Key Features

- **Connection Management**: Robust connection handling with auto-reconnection
- **Multi-Account Support**: Manage and switch between multiple trading accounts
- **Event-Driven Architecture**: Subscribe to connection events and state changes
- **Market Data**: Retrieve OHLCV bars, ticks, and real-time streaming data
- **Configuration Management**: Save and load client configurations
- **Error Handling**: Comprehensive error tracking and diagnostics
- **Context Manager Support**: Use with Python's `with` statement for automatic cleanup

## Architecture

The module consists of two main components:
- **MT5Client**: Connection and account management
- **MT5Data**: Market data retrieval and streaming

```
┌──────────────────┐
│    MT5Client     │  ← Connection & Account Management
├──────────────────┤
│ ConnectionState  │  ← Connection state tracking
│ Event Handlers   │  ← Event-driven callbacks
│ Auto-Reconnect   │  ← Automatic reconnection
│ Multi-Account    │  ← Account switching
└──────────────────┘

┌──────────────────┐
│     MT5Data      │  ← Market Data Retrieval
├──────────────────┤
│ OHLCV Bars       │  ← Historical bar data
│ Tick Data        │  ← Tick-level data
│ Real-time Stream │  ← Live data streaming
│ Data Processing  │  ← Cleaning & formatting
└──────────────────┘
```

---

## 1. MT5Client Component

Main client class for MetaTrader 5 terminal interaction, providing connection management, authentication, auto-reconnection, multi-account support, and event handling.

### Classes

- **`MT5Client`** - Main client for MT5 terminal interaction
- **`ConnectionState`** - Enum for connection states

### Enums

**ConnectionState** - Connection state enumeration
- `DISCONNECTED` - Not connected to MT5 terminal
- `CONNECTED` - Successfully connected to MT5 terminal
- `FAILED` - Connection attempt failed
- `INITIALIZING` - Connection is being initialized
- `RECONNECTING` - Attempting to reconnect to MT5 terminal

### Methods

#### Initialization & Connection
- `__init__(timeout=60000, portable=False, user_id=1)` - Initialize MT5Client instance
- `connect()` - Connect to MT5 terminal
- `disconnect()` - Disconnect from MT5 terminal
- `shutdown()` - Shutdown MT5 terminal connection and clean up resources
- `is_connected()` - Check if client is currently connected
- `ping()` - Ping MT5 terminal to check connection health

#### Account Management
- `save_account(account_name, login, password, server, path="")` - Save account credentials
- `list_accounts()` - List all saved accounts
- `switch_account(account_name, login=None, password=None, server=None)` - Switch to different account
- `remove_account(account_name)` - Remove a saved account
- `fetch_account_info()` - Fetch account information from MT5

#### Auto-Reconnection
- `enable_auto_reconnect(retry_attempts=3, retry_delay=5)` - Enable automatic reconnection
- `disable_auto_reconnect()` - Disable automatic reconnection
- `reconnect()` - Manually trigger reconnection

#### Event Handling
- `on(event, callback)` - Register event callback
- `off(event, callback=None)` - Unregister event callback
- `trigger_event(event, **kwargs)` - Trigger an event

**Available Events:**
- `connect` - Fired when connection established
- `disconnect` - Fired when disconnected
- `error` - Fired when error occurs
- `reconnect` - Fired when reconnection starts
- `account_switch` - Fired when account switched

#### Configuration
- `configure(**kwargs)` - Configure client settings
- `get_config()` - Get current configuration
- `save_config(filepath=None)` - Save configuration to JSON file
- `load_config(filepath)` - Load configuration from JSON file

#### Data Retrieval
- `fetch_positions(symbol=None, group=None, ticket=None)` - Fetch positions from MT5
- `fetch_orders(symbol=None, group=None, ticket=None)` - Fetch active orders from MT5
- `fetch_symbol_info(symbol)` - Fetch symbol information from MT5
- `get_symbol_info(symbol, refresh=False)` - Get symbol info from cache or fetch

#### Status & Diagnostics
- `get_status()` - Get comprehensive client status
- `get_connection_statistics()` - Get connection statistics
- `get_error()` - Get last error
- `export_logs(filepath)` - Export logs to JSON file

#### Context Manager
- `__enter__()` - Enter context manager
- `__exit__(exc_type, exc_val, exc_tb)` - Exit context manager

### Example

```python
from apps.mt5 import MT5Client

# Basic connection
client = MT5Client()
if client.connect():
    print(f"Connected! Account: {client.account_login}")
    print(f"Server: {client.account_server}")
    client.shutdown()
```

**Context Manager:**

```python
from apps.mt5 import MT5Client

# Automatic cleanup
with MT5Client() as client:
    if client.connect():
        print("Connected!")
        status = client.get_status()
        print(f"Balance: {status['account_info']['balance']}")
# Client automatically shut down
```

**Auto-Reconnection:**

```python
from apps.mt5 import MT5Client

client = MT5Client()

# Enable auto-reconnection
client.enable_auto_reconnect(retry_attempts=5, retry_delay=10)

if client.connect():
    print("Connected with auto-reconnect enabled")
    # If connection drops, client will automatically reconnect

client.shutdown()
```

**Event Callbacks:**

```python
from apps.mt5 import MT5Client

def on_connect(**kwargs):
    print("📡 Connected to MT5!")

def on_disconnect(**kwargs):
    print("📡 Disconnected from MT5")

def on_error(**kwargs):
    error = kwargs.get("error")
    print(f"⚠️ Error: {error}")

# Create client and register callbacks
client = MT5Client()
client.on("connect", on_connect)
client.on("disconnect", on_disconnect)
client.on("error", on_error)

# Events will be triggered automatically
if client.connect():
    print("Connection established")

client.disconnect()
client.shutdown()
```

**Multi-Account Management:**

```python
from apps.mt5 import MT5Client

client = MT5Client()

# Save multiple accounts
client.save_account("demo_account", 12345, "password", "Demo-Server")
client.save_account("live_account", 67890, "password", "Live-Server")

# List saved accounts
accounts = client.list_accounts()
print(f"Saved accounts: {accounts}")

# Switch between accounts
if client.switch_account("demo_account"):
    print(f"Switched to: {client.current_account}")
    print(f"Account: {client.account_login}")

client.shutdown()
```

**Configuration Management:**

```python
from apps.mt5 import MT5Client

client = MT5Client()

# Configure settings
client.configure(
    timeout=30000,
    auto_reconnect_enabled=True,
    retry_attempts=5,
    retry_delay=10
)

# Get configuration
config = client.get_config()
print(f"Timeout: {config['timeout']}ms")
print(f"Auto-reconnect: {config['auto_reconnect_enabled']}")

# Save configuration to file
client.save_config("client_config.json")

# Load configuration from file
new_client = MT5Client()
new_client.load_config("client_config.json")

client.shutdown()
new_client.shutdown()
```

**Status & Diagnostics:**

```python
from apps.mt5 import MT5Client

client = MT5Client()

if client.connect():
    # Get comprehensive status
    status = client.get_status()
    print(f"Connection state: {status['connection_state']}")
    print(f"Account: {status['account_info']['login']}")
    print(f"Balance: {status['account_info']['balance']}")

    # Get connection statistics
    stats = client.get_connection_statistics()
    print(f"Total attempts: {stats['total_attempts']}")
    print(f"Success rate: {stats['success_rate']:.1%}")

    # Export logs
    client.export_logs("client_logs.json")

client.shutdown()
```

**Fetching Data:**

```python
from apps.mt5 import MT5Client

client = MT5Client()

if client.connect():
    # Fetch account information
    account_info = client.fetch_account_info()
    print(f"Balance: {account_info['balance']}")
    print(f"Equity: {account_info['equity']}")
    print(f"Margin: {account_info['margin']}")

    # Fetch positions
    positions = client.fetch_positions()
    for pos in positions:
        print(f"Position: {pos['symbol']} - {pos['type']}")
        print(f"  Volume: {pos['volume']}")
        print(f"  Profit: {pos['profit']}")

    # Fetch orders
    orders = client.fetch_orders()
    for order in orders:
        print(f"Order: {order['symbol']} - {order['type']}")
        print(f"  Price: {order['price_open']}")

    # Fetch symbol information
    symbol_info = client.fetch_symbol_info("EURUSD")
    print(f"Bid: {symbol_info['bid']}")
    print(f"Ask: {symbol_info['ask']}")
    print(f"Spread: {symbol_info['spread']}")

client.shutdown()
```

---

## 2. MT5Data Component

Market data retrieval and management class providing OHLCV bar data, tick data, real-time streaming, and data processing capabilities.

### Classes

- **`MT5Data`** - Market data retrieval and management
- **`TimeFrame`** - Enum for MT5 timeframes

### Enums

**TimeFrame** - MT5 timeframe enumeration
- `M1` - 1 minute
- `M5` - 5 minutes
- `M15` - 15 minutes
- `M30` - 30 minutes
- `H1` - 1 hour
- `H4` - 4 hours
- `D1` - 1 day
- `W1` - 1 week
- `MN1` - 1 month

**TimeFrame Methods:**
- `minutes()` - Get timeframe duration in minutes
- `from_string(timeframe_str)` - Convert string to TimeFrame enum
- `from_minutes(minutes)` - Get closest matching timeframe from minutes

### Methods

#### Initialization
- `__init__(client=None)` - Initialize MT5Data instance

#### OHLCV Bar Data
- `get_bars(symbol, timeframe, count=None, start=None, end=None, as_dataframe=True)` - Retrieve OHLCV bar data

**Parameters:**
- `symbol` - Trading symbol (e.g., "EURUSD")
- `timeframe` - TimeFrame enum or MT5 constant
- `count` - Number of bars to retrieve
- `start` - Start date (datetime or string)
- `end` - End date (datetime or string)
- `as_dataframe` - Return as DataFrame (True) or list of dicts (False)

**Returns:**
- pandas DataFrame or list of dictionaries with OHLCV data

#### Tick Data
- `get_ticks(symbol, count=None, start=None, end=None, flags=None, as_dataframe=True)` - Retrieve tick data

**Parameters:**
- `symbol` - Trading symbol
- `count` - Number of ticks to retrieve
- `start` - Start date
- `end` - End date
- `flags` - Tick flags (ALL, INFO, TRADE)
- `as_dataframe` - Return as DataFrame or list

**Returns:**
- pandas DataFrame or list of dictionaries with tick data

#### Real-time Streaming
- `start_stream(symbol, data_type, callback, interval=1.0, timeframe=None)` - Start real-time data stream
- `stop_stream(symbol)` - Stop data stream for symbol
- `stop_all_streams()` - Stop all active streams

**Parameters:**
- `symbol` - Trading symbol
- `data_type` - "ticks" or "bars"
- `callback` - Function to call with new data
- `interval` - Update interval in seconds
- `timeframe` - TimeFrame for bars (required if data_type="bars")

#### Data Processing
- `clean_data(df)` - Clean and process DataFrame
- `resample_bars(df, timeframe)` - Resample bars to different timeframe
- `add_indicators(df, indicators)` - Add technical indicators to DataFrame

#### Utility Methods
- `normalize_price(price, symbol)` - Normalize price to symbol's digits
- `get_symbol_digits(symbol)` - Get number of decimal places for symbol
- `validate_symbol(symbol)` - Check if symbol is valid

### Example

**Retrieving OHLCV Bars:**

```python
from apps.mt5 import MT5Client, MT5Data, TimeFrame

client = MT5Client()
client.connect()

data = MT5Data(client)

# Get last 1000 bars
bars = data.get_bars("EURUSD", TimeFrame.H1, count=1000)
print(f"Retrieved {len(bars)} bars")
print(bars.head())

# Get bars by date range
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

bars = data.get_bars("EURUSD", TimeFrame.H1, start=start_date, end=end_date)
print(f"Retrieved {len(bars)} bars for last 30 days")

client.shutdown()
```

**Retrieving Tick Data:**

```python
from apps.mt5 import MT5Client, MT5Data

client = MT5Client()
client.connect()

data = MT5Data(client)

# Get last 10000 ticks
ticks = data.get_ticks("EURUSD", count=10000)
print(f"Retrieved {len(ticks)} ticks")
print(ticks.head())

# Get ticks by date range
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(hours=1)

ticks = data.get_ticks("EURUSD", start=start_date, end=end_date)
print(f"Retrieved {len(ticks)} ticks for last hour")

client.shutdown()
```

**Real-time Data Streaming:**

```python
from apps.mt5 import MT5Client, MT5Data, TimeFrame
import time

def on_new_tick(tick_data):
    """Callback for new tick data."""
    print(f"New tick: {tick_data['time']} - Bid: {tick_data['bid']}, Ask: {tick_data['ask']}")

def on_new_bar(bar_data):
    """Callback for new bar data."""
    print(f"New bar: {bar_data['time']} - Close: {bar_data['close']}")

client = MT5Client()
client.connect()

data = MT5Data(client)

# Start tick stream
data.start_stream("EURUSD", "ticks", on_new_tick, interval=1.0)
print("Tick stream started...")

# Start bar stream
data.start_stream("GBPUSD", "bars", on_new_bar, interval=5.0, timeframe=TimeFrame.M1)
print("Bar stream started...")

# Let it run for 30 seconds
time.sleep(30)

# Stop streams
data.stop_all_streams()
print("All streams stopped")

client.shutdown()
```

**Data Processing:**

```python
from apps.mt5 import MT5Client, MT5Data, TimeFrame

client = MT5Client()
client.connect()

data = MT5Data(client)

# Get bars
bars = data.get_bars("EURUSD", TimeFrame.M5, count=1000)

# Clean data (remove duplicates, handle missing values)
clean_bars = data.clean_data(bars)

# Resample to different timeframe
h1_bars = data.resample_bars(clean_bars, TimeFrame.H1)
print(f"Resampled from {len(clean_bars)} M5 bars to {len(h1_bars)} H1 bars")

# Add technical indicators
indicators = {
    'sma_20': {'type': 'sma', 'period': 20},
    'ema_50': {'type': 'ema', 'period': 50},
    'rsi_14': {'type': 'rsi', 'period': 14}
}
bars_with_indicators = data.add_indicators(h1_bars, indicators)
print(bars_with_indicators[['close', 'sma_20', 'ema_50', 'rsi_14']].tail())

client.shutdown()
```

**TimeFrame Utilities:**

```python
from apps.mt5 import TimeFrame

# Convert string to TimeFrame
tf = TimeFrame.from_string("H1")
print(f"TimeFrame: {tf}")  # TimeFrame.H1

# Get timeframe in minutes
minutes = TimeFrame.H1.minutes()
print(f"H1 = {minutes} minutes")  # 60

# Get closest timeframe from minutes
tf = TimeFrame.from_minutes(240)
print(f"240 minutes = {tf}")  # TimeFrame.H4

# String representation
print(f"TimeFrame: {TimeFrame.M15}")  # M15
```

**Multiple Symbols:**

```python
from apps.mt5 import MT5Client, MT5Data, TimeFrame

client = MT5Client()
client.connect()

data = MT5Data(client)

symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]

for symbol in symbols:
    bars = data.get_bars(symbol, TimeFrame.D1, count=100)
    print(f"{symbol}: {len(bars)} bars")
    print(f"  Latest close: {bars.iloc[-1]['close']}")
    print(f"  High: {bars['high'].max()}")
    print(f"  Low: {bars['low'].min()}")

client.shutdown()
```

---

## Common Patterns

### Complete Workflow

```python
from apps.mt5 import MT5Client, MT5Data, TimeFrame

# 1. Create and configure client
client = MT5Client(timeout=30000)
client.enable_auto_reconnect(retry_attempts=3, retry_delay=5)

# 2. Register event callbacks
def on_connect(**kwargs):
    print("✓ Connected to MT5")

def on_error(**kwargs):
    print(f"✗ Error: {kwargs.get('error')}")

client.on("connect", on_connect)
client.on("error", on_error)

# 3. Initialize connection
if client.connect():
    # 4. Get account status
    status = client.get_status()
    print(f"Account: {status['account_info']['login']}")
    print(f"Balance: {status['account_info']['balance']}")

    # 5. Create data instance
    data = MT5Data(client)

    # 6. Retrieve market data
    bars = data.get_bars("EURUSD", TimeFrame.H1, count=100)
    print(f"Retrieved {len(bars)} bars")

    # 7. Get positions
    positions = client.fetch_positions()
    print(f"Open positions: {len(positions)}")

# 8. Cleanup
client.shutdown()
```

### Error Handling

```python
from apps.mt5 import MT5Client

client = MT5Client()

try:
    if not client.connect():
        error = client.get_error()
        if error:
            error_code, error_message = error
            print(f"Connection failed: {error_code} - {error_message}")

        # Get statistics
        stats = client.get_connection_statistics()
        print(f"Failed connections: {stats['failed_connections']}")
    else:
        # Successful connection
        print("Connected successfully")

except Exception as e:
    print(f"Exception occurred: {e}")

finally:
    client.shutdown()
```

### Using with Trading Module

```python
from apps.mt5 import MT5Client
from apps.trading import Trade, MT5TradeProvider, OrderType

# Initialize MT5 connection
client = MT5Client()
client.connect()

# Create trade provider
provider = MT5TradeProvider(client)
trade = Trade(provider)

# Execute trade
if trade.position_open(
    symbol="EURUSD",
    order_type=OrderType.BUY,
    volume=0.1,
    price=1.0952,
    sl=1.0900,
    tp=1.1000
):
    print(f"Position opened: #{trade.result_order()}")

# Cleanup
client.shutdown()
```

---

## Best Practices

1. **Always use context managers**: Use `with MT5Client() as client:` for automatic cleanup
2. **Enable auto-reconnection**: For production systems, enable auto-reconnection
3. **Handle errors gracefully**: Always check return values and handle errors
4. **Use event callbacks**: Subscribe to events for better monitoring
5. **Save configurations**: Save and load configurations for consistency
6. **Clean up resources**: Always call `shutdown()` when done
7. **Cache symbol info**: Use `get_symbol_info()` with caching for better performance
8. **Validate symbols**: Check if symbols are valid before requesting data
9. **Use appropriate timeframes**: Choose timeframes based on your strategy needs
10. **Monitor connection statistics**: Track connection health and success rates

## Configuration File Format

```json
{
    "timeout": 60000,
    "portable": false,
    "auto_reconnect_enabled": true,
    "retry_attempts": 5,
    "retry_delay": 10,
    "path": "C:/Program Files/MT5/terminal64.exe"
}
```

## Event Callback Signature

```python
def callback(**kwargs):
    """
    Event callback function.

    Args:
        **kwargs: Event-specific keyword arguments
            - client: MT5Client instance
            - error: Error tuple (code, message) for error events
            - account: Account name for account_switch events
    """
    pass
```

## All Examples

The `examples/mt5/` directory contains comprehensive examples:

- `client_example.py` - MT5Client usage examples including:
  - Basic connection
  - Context manager usage
  - Auto-reconnection
  - Event callbacks
  - Multi-account management
  - Configuration management
  - Status and diagnostics
  - Error handling
  - Complete workflows

Run the example:
```bash
python examples/mt5/client_example.py
```

## License

Copyright 2025, HaruQuant

## See Also

- `apps/trading/` - Trading module for executing trades
- `apps/strategy/` - Strategy framework
- `examples/mt5/` - Comprehensive examples
