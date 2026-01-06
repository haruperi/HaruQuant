# MT5 Client Usage Examples

This directory contains comprehensive usage examples for the MT5Client class from `apps.mt5.client`.

## Overview

The MT5Client provides a robust interface for connecting to and interacting with MetaTrader 5 terminals, including:
- Connection management with auto-reconnection
- Account and terminal information retrieval
- Symbol information and market data
- Position and order management
- Historical data (bars, ticks, orders, deals)

## Examples

### 01_basic_connection.py
Basic connection management examples:
- Simple connection and shutdown
- Using context manager for automatic cleanup
- Manual reconnection
- Connection status checking

**Run:**
```bash
python tests/usage/mt5/01_basic_connection.py
```

### 02_account_info.py
Account and terminal information examples:
- Retrieving account information (balance, equity, margin, etc.)
- Retrieving terminal information (build, company, paths, etc.)
- Accessing cached data
- Connection statistics

**Run:**
```bash
python tests/usage/mt5/02_account_info.py
```

### 03_symbol_info.py
Symbol information and properties:
- Retrieving symbol information (bid, ask, spread, etc.)
- Working with multiple symbols
- Accessing symbol trading properties
- Understanding initial symbols in watchlist

**Run:**
```bash
python tests/usage/mt5/03_symbol_info.py
```

### 04_positions_orders.py
Position and order management:
- Retrieving open positions
- Retrieving active orders
- Filtering by symbol, group, or ticket
- Position summary statistics
- Querying specific positions/orders

**Run:**
```bash
python tests/usage/mt5/04_positions_orders.py
```

### 05_historical_data.py
Historical data retrieval:
- Fetching OHLCV bars for different timeframes
- Retrieving tick data
- Using date ranges
- Getting historical orders and deals
- Calculating statistics from historical data

**Run:**
```bash
python tests/usage/mt5/05_historical_data.py
```

### 06_advanced_usage.py
Advanced features and patterns:
- Connection state management
- Auto-reconnection configuration
- Error handling patterns
- Connection statistics tracking
- Data analysis examples
- Multi-symbol monitoring

**Run:**
```bash
python tests/usage/mt5/06_advanced_usage.py
```

## Prerequisites

Before running these examples, you need:

1. **MetaTrader 5 installed** on your system
2. **MT5 account credentials stored in database**:
   - User account created in HaruQuant database
   - MT5 credentials linked to your user account
3. **Python packages**:
   ```bash
   pip install MetaTrader5 pandas
   ```

## Configuration

All examples automatically retrieve credentials from the database using the UserManager:

```python
def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    user_manager.db_path = "data/database/haruquant.db"

    username = "haruperi"  # Change this to your username
    user = user_manager.get_user(username=username)
    if not user:
        logger.error(f"User {username} not found")
        sys.exit(1)

    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        logger.error(f"No default broker credentials found for {username}")
        sys.exit(1)

    logger.info(f"Using credentials for account: {creds['login']} on {creds['server']}")
    return creds
```

**To use the examples:**
1. Update the `username` variable in each file's `get_mt5_credentials()` function
2. Ensure your user account and MT5 credentials are stored in the database
3. Run the example scripts

## Features Demonstrated

### Connection Management
- Initialize and connect to MT5 terminal
- Check connection status
- Manual and automatic reconnection
- Proper shutdown and cleanup
- Context manager usage

### Data Retrieval
- Account information (balance, equity, margin, etc.)
- Terminal information (build, company, settings)
- Symbol information (prices, spreads, trading specs)
- Open positions and active orders
- Historical bars (OHLCV data)
- Tick data (bid/ask prices)
- Historical orders and deals

### Advanced Features
- Auto-reconnection with retry logic
- Connection state tracking
- Error handling
- Data caching
- Multi-symbol monitoring
- Statistical analysis

## Common Patterns

### Context Manager (Recommended)
```python
# Get credentials from database
creds = get_mt5_credentials()

with MT5Client(
    login=creds["login"],
    password=creds["password"],
    server=creds["server"],
    path=creds["path"]
) as client:
    if client.is_connected():
        # Do your work here
        data = client.get_bars("EURUSD", "H1", count=100)
# Automatic cleanup when done
```

### Manual Management
```python
# Get credentials from database
creds = get_mt5_credentials()

client = MT5Client(
    login=creds["login"],
    password=creds["password"],
    server=creds["server"],
    path=creds["path"]
)
try:
    if client.is_connected():
        # Do your work
        data = client.get_bars("EURUSD", "H1", count=100)
finally:
    client.shutdown()  # Always cleanup
```

### Error Handling
```python
# Get credentials from database
creds = get_mt5_credentials()

with MT5Client(
    login=creds["login"],
    password=creds["password"],
    server=creds["server"],
    path=creds["path"]
) as client:
    if not client.is_connected():
        raise ConnectionError("Failed to connect to MT5")

    # Safe data retrieval
    account_info = client.get_account_info()
    if account_info:
        print(f"Balance: {account_info['balance']}")
    else:
        print("Failed to get account info")
```

## Supported Timeframes

- **Minutes**: M1, M2, M3, M4, M5, M6, M10, M12, M15, M20, M30
- **Hours**: H1, H2, H3, H4, H6, H8, H12
- **Days/Weeks/Months**: D1, W1, MN1

## Tips

1. **Always use context manager** or ensure `shutdown()` is called
2. **Check connection status** before making requests
3. **Handle None returns** - methods return None on failure
4. **Use caching** - info data is cached after first retrieval
5. **Enable auto-reconnection** for production systems
6. **Monitor connection statistics** for debugging
7. **Use date ranges** for specific historical data periods

## Troubleshooting

If examples don't work:

1. **Verify MT5 is installed** and running
2. **Check credentials** are correct
3. **Ensure terminal allows** API access
4. **Check firewall settings** if connection fails
5. **Enable logging** for detailed error messages
6. **Review MT5 error codes** in the logs

## Additional Resources

- MT5 Client source: `apps/mt5/client.py`
- MT5 Python documentation: https://www.mql5.com/en/docs/python_metatrader5
- Logger usage: `tests/usage/logger/`

## License

Part of the HaruQuant trading system.
