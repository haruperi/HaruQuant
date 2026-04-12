# MT5 Module

This module provides a robust Python wrapper for the MetaTrader 5 (MT5) terminal interaction.

## Files

### 1. `client.py`

**Purpose**
The main client module for connecting to and interacting with the MetaTrader 5 terminal. It handles connection management, authentication, auto-reconnection, multi-account support, and event handling.

**Classes**

* **`MT5Api`**: Thin wrapper around the `MetaTrader5` module with connection tracking.

  * `initialize(*args, **kwargs) -> bool`: Initialize MT5 terminal connection.
  * `shutdown() -> bool`: Shutdown MT5 terminal connection.
  * `last_error() -> Any`: Return last MT5 error.
  * `is_initialized() -> bool`: Return whether initialize() succeeded in this process.
* **`ConnectionState(Enum)`**: Enumeration representing the connection state (`DISCONNECTED`, `CONNECTED`, `FAILED`, `INITIALIZING`, `RECONNECTING`).
* **`MT5Client`**:  Main client class.

  * `__init__(timeout: int = 60000, portable: bool = False)`: Initialize the client.
  * `connect(path: str, login: int, password: str, server: str) -> bool`: Connect to MT5 terminal and login.
  * `is_connected() -> bool`: Check if client is currently connected.
  * `shutdown() -> None`: Shutdown the MT5 terminal connection and clean up resources.
  * `get_bars(symbol: str, timeframe: str, count: int = 100, start_pos: int = 0, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> pd.DataFrame`: Get OHLCVS bars from MT5.
  * `get_ticks(symbol: str, count: int = 100, start: Optional[datetime] = None, end: Optional[datetime] = None, flags: int = mt5.COPY_TICKS_ALL, as_dataframe: bool = True) -> Union[pd.DataFrame, List[Dict[str, Any]], None]`: Get ticks from MT5.
  * `start_streaming(symbol: str, data_type: str, callback: Callable[[Any], None], interval: float = 1.0, timeframe: Optional[str] = None) -> bool`: Start streaming real-time data.
  * `stop_streaming(symbol: str, data_type: str) -> bool`: Stop streaming data for a symbol.

### 2. `util.py`

**Purpose**
Provides utility functions for working with MT5 data, including time operations, price/volume conversions, data formatting, file operations, and calculations.

**Classes**

* **`MT5Utils`**: Static utility class.
  * **Time Operations**
    * `convert_time(time_value: Union[datetime, int, float, str], output_format: str = "datetime") -> Union[datetime, int, float, str]`: Convert time between different formats.
    * `get_time(time_type: str = "now", timezone_offset: int = 0, format_str: Optional[str] = None) -> Union[datetime, str]`: Get current or specific time.
  * **Price Operations**
    * `convert_price(price: Union[float, int], from_digits: int, to_digits: int) -> float`: Convert price between different digit precisions.
    * `format_price(price: Union[float, int], digits: int = 5, include_currency: bool = False, currency_symbol: str = "") -> str`: Format price for display.
    * `round_price(price: Union[float, int], tick_size: float, direction: str = "nearest") -> float`: Round price to valid tick size.
    * `add_pips_to_price(price: float, pips: float, symbol_info: Any, direction: int = 1) -> float`: Add pips to a price.
  * **Volume Operations**
    * `convert_volume(volume: Union[float, int], from_unit: str = "lots", to_unit: str = "units", contract_size: int = 100000) -> float`: Convert volume between different units.
    * `round_volume(volume: Union[float, int], volume_step: float, direction: str = "nearest") -> float`: Round volume to valid step size.
  * **Data Formatting**
    * `to_dict(data: Any, exclude_none: bool = False, exclude_private: bool = True) -> Dict[str, Any]`: Convert data to dictionary format.
    * `to_dataframe(data: Union[List, tuple, Dict], columns: Optional[List[str]] = None) -> pd.DataFrame`: Convert data to pandas DataFrame.
  * **File Operations**
    * `save(data: Any, filepath: Union[str, Path], format: str = "json", **kwargs) -> bool`: Save data to file.
    * `load(filepath: Union[str, Path], format: str = "json", **kwargs) -> Any`: Load data from file.
  * **Calculations**
    * `calculate(operation: str, *args, **kwargs) -> Union[float, int, Any]`: Perform various calculations ('pip_value', 'profit', 'margin', 'percent', 'percent_change').
    * `get_filling_mode(symbol: str) -> int`: Get the correct filling mode for a symbol.
  * **Type Conversions**
    * `convert_type(value: Any, target_type: str) -> Any`: Convert value to target type.

## Usage Examples

For full usage examples, please refer to the `tests/usage/trade` directory.

### Basic Connection

```python
from datetime import datetime
from apps.sqlite.users import UserManager
from backend.common.logger import logger
from apps.mt5 import MT5Client
from apps.mt5 import get_mt5_api
mt5 = get_mt5_api()


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds

# Get credentials from database
creds = get_mt5_credentials()

# Initialize MT5 client (needed for Option 1)
client = MT5Client()
connected = client.connect(
    login=creds["login"],
    password=creds["password"],
    server=creds["server"],
    path=creds["path"]
)

if not connected:
        logger.error("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

eurusd = "EURUSD"
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 12, 31)

data = client.get_bars(symbol=eurusd, timeframe="H1", date_from=start_date, date_to=end_date)
```

### Advanced Usage (Streaming & Data)

This allows fetching bars, ticks, and streaming real-time data.

```python
# Fetch bars
df = client.get_bars("EURUSD", "H1", count=100)
print(df.head())

# Stream ticks
def on_tick(tick):
    print(f"Tick: {tick}")

client.start_streaming("EURUSD", "ticks", on_tick)
```

