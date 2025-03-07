Below is a Markdown-formatted version of the MetaTrader 5 Python integration documentation, based on the content from the official MQL5 website. citeturn0search0

---

# MetaTrader Module for Integration with Python

MQL5 is designed for the development of high-performance trading applications in the financial markets and is unparalleled among other specialized languages used in algorithmic trading. The syntax and speed of MQL5 programs are very close to C++; there is support for OpenCL and integration with MS Visual Studio. Additionally, libraries for statistics, fuzzy logic, and ALGLIB are available. The MetaEditor development environment features native support for .NET libraries with "smart" functions import, eliminating the need to develop special wrappers. Third-party C++ DLLs can also be used. C++ source code files (CPP and H) can be edited and compiled into DLLs directly from the editor, utilizing Microsoft Visual Studio installed on the user's PC.

Python is a modern high-level programming language for developing scripts and applications. It contains multiple libraries for machine learning, process automation, as well as data analysis and visualization.

The MetaTrader package for Python is designed for convenient and fast obtaining of exchange data via interprocessor communication directly from the MetaTrader 5 terminal. The data received this way can be further used for statistical calculations and machine learning.

## Installation

To install the MetaTrader5 package from the command line:

```bash
pip install MetaTrader5
```

To update the package:

```bash
pip install --upgrade MetaTrader5
```

## Functions for Integrating MetaTrader 5 and Python

| Function               | Action                                                                                     |
|------------------------|--------------------------------------------------------------------------------------------|
| `initialize`           | Establish a connection with the MetaTrader 5 terminal                                      |
| `login`                | Connect to a trading account using specified parameters                                    |
| `shutdown`             | Close the previously established connection to the MetaTrader 5 terminal                   |
| `version`              | Return the MetaTrader 5 terminal version                                                   |
| `last_error`           | Return data on the last error                                                              |
| `account_info`         | Get info on the current trading account                                                    |
| `terminal_info`        | Get status and parameters of the connected MetaTrader 5 terminal                           |
| `symbols_total`        | Get the number of all financial instruments in the MetaTrader 5 terminal                   |
| `symbols_get`          | Get all financial instruments from the MetaTrader 5 terminal                               |
| `symbol_info`          | Get data on the specified financial instrument                                             |
| `symbol_info_tick`     | Get the last tick for the specified financial instrument                                   |
| `symbol_select`        | Select a symbol in the MarketWatch window or remove a symbol from the window               |
| `market_book_add`      | Subscribe the MetaTrader 5 terminal to the Market Depth change events for a specified symbol |
| `market_book_get`      | Return a tuple from BookInfo featuring Market Depth entries for the specified symbol       |
| `market_book_release`  | Cancel subscription of the MetaTrader 5 terminal to the Market Depth change events for a specified symbol |
| `copy_rates_from`      | Get bars from the MetaTrader 5 terminal starting from the specified date                   |
| `copy_rates_from_pos`  | Get bars from the MetaTrader 5 terminal starting from the specified index                  |
| `copy_rates_range`     | Get bars in the specified date range from the MetaTrader 5 terminal                        |
| `copy_ticks_from`      | Get ticks from the MetaTrader 5 terminal starting from the specified date                  |
| `copy_ticks_range`     | Get ticks for the specified date range from the MetaTrader 5 terminal                      |
| `orders_total`         | Get the number of active orders                                                            |
| `orders_get`           | Get active orders with the ability to filter by symbol or ticket                           |
| `order_calc_margin`    | Return margin in the account currency to perform a specified trading operation             |
| `order_calc_profit`    | Return profit in the account currency after a specified trading operation is performed     |
| `order_check`          | Check if there is enough money to execute the specified trading operation                  |
| `order_send`           | Send a trade request to the server                                                         |
| `positions_total`      | Get the number of open positions                                                           |
| `positions_get`        | Get open positions with the ability to filter by symbol or ticket                          |
| `history_orders_total` | Get the number of orders in the history                                                    |
| `history_orders_get`   | Get orders from the history with the ability to filter by ticket, symbol, or position      |
| `history_deals_total`  | Get the number of deals in the history                                                     |
| `history_deals_get`    | Get deals from the history with the ability to filter by ticket, symbol, or position       |


---

# `initialize`

Establishes a connection with the MetaTrader 5 terminal. There are three ways to call this function:

1. **Without parameters:** The function automatically finds and connects to the terminal.

   ```python
   initialize()
   ```

2. **With the path to the MetaTrader 5 terminal:** Specify the path to the terminal's executable file.

   ```python
   initialize(path)  # path to the MetaTrader 5 terminal EXE file
   ```

3. **With the path and trading account parameters:** Specify the path along with account details.

   ```python
   initialize(
       path,           # path to the MetaTrader 5 terminal EXE file
       login=LOGIN,    # account number
       password="PASSWORD",  # password
       server="SERVER",      # server name as specified in the terminal
       timeout=TIMEOUT,      # timeout
       portable=False        # portable mode
   )
   ```

**Parameters:**

- `path` (optional): Path to the `metatrader.exe` or `metatrader64.exe` file. If not specified, the module attempts to find the executable file automatically.

- `login` (optional): Trading account number. If not specified, the last trading account is used.

- `password` (optional): Trading account password. If not set, the password saved in the terminal database for the specified trading account is applied automatically.

- `server` (optional): Trade server name. If not set, the server saved in the terminal database for the specified trading account is applied automatically.

- `timeout` (optional): Connection timeout in milliseconds. Default is 60,000 (60 seconds).

- `portable` (optional): Flag indicating if the terminal is launched in portable mode. Default is `False`.

**Return Value:**

Returns `True` if the connection to the MetaTrader 5 terminal is successful; otherwise, returns `False`.

**Note:**

If required, the MetaTrader 5 terminal is launched to establish a connection when executing the `initialize()` call.

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish MetaTrader 5 connection to a specified trading account
if not mt5.initialize(login=25115284, server="MetaQuotes-Demo", password="4zatlbqx"):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Display data on connection status, server name, and trading account
print(mt5.terminal_info())

# Display data on MetaTrader 5 version
print(mt5.version())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```



# `login`

Connects to a trading account using specified parameters.

```python
login(
   login,                 # account number
   password="PASSWORD",   # password
   server="SERVER",       # server name as specified in the terminal
   timeout=TIMEOUT        # timeout
)
```

**Parameters:**

- **`login`** (required): Trading account number.

- **`password`** (optional): Trading account password. If not set, the password saved in the terminal database is applied automatically.

- **`server`** (optional): Trade server name. If not set, the last used server is applied automatically.

- **`timeout`** (optional): Connection timeout in milliseconds. Default is 60,000 (60 seconds). If the connection is not established within the specified time, the call is forcibly terminated, and an exception is generated.

**Return Value:**

Returns `True` if the connection to the trade account is successful; otherwise, returns `False`.

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Display data on MetaTrader 5 version
print(mt5.version())

# Connect to the trade account without specifying a password and a server
account = 17221085
authorized = mt5.login(account)  # The terminal database password is applied if connection data is set to be remembered
if authorized:
    print("Connected to account #{}".format(account))
else:
    print("Failed to connect at account #{}, error code: {}".format(account, mt5.last_error()))

# Now connect to another trading account specifying the password
account = 25115284
authorized = mt5.login(account, password="gqrtz0lbdm")
if authorized:
    # Display trading account data 'as is'
    print(mt5.account_info())
    # Display trading account data in the form of a list
    print("Show account_info()._asdict():")
    account_info_dict = mt5.account_info()._asdict()
    for prop in account_info_dict:
        print("  {}={}".format(prop, account_info_dict[prop]))
else:
    print("Failed to connect at account #{}, error code: {}".format(account, mt5.last_error()))

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```



# `shutdown`

Closes the previously established connection to the MetaTrader 5 terminal.

```python
shutdown()
```

**Return Value:**

This function does not return any value.

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed")
    quit()

# Display data on connection status, server name, and trading account
print(mt5.terminal_info())

# Display data on MetaTrader 5 version
print(mt5.version())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```



# `version`

Returns the MetaTrader 5 terminal version, build, and release date.

```python
version()
```

**Return Value:**

A tuple containing three values:

1. **Version** (`int`): MetaTrader 5 terminal version number.
2. **Build** (`int`): Build number of the terminal.
3. **Release Date** (`str`): Release date of the build in 'DD MMM YYYY' format.

Returns `None` in case of an error. To obtain information about the error, use the `last_error()` function.

**Example:**

```python
import MetaTrader5 as mt5
import pandas as pd

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Display data on MetaTrader 5 version
print(mt5.version())

# Display data on connection status, server name, and trading account 'as is'
print(mt5.terminal_info())
print()

# Get properties in the form of a dictionary
terminal_info_dict = mt5.terminal_info()._asdict()
# Convert the dictionary into DataFrame and print
df = pd.DataFrame(list(terminal_info_dict.items()), columns=['property', 'value'])
print("terminal_info() as dataframe:")
print(df[:-1])

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```



# `last_error`

Retrieves information about the last error that occurred during the execution of MetaTrader 5 library functions.

```python
last_error()
```

**Return Value:**

Returns a tuple containing the last error code and its corresponding description.

**Note:**

The `last_error()` function allows you to obtain an error code when a MetaTrader 5 library function fails. It is similar to `GetLastError()` but uses its own set of error codes.

**Possible Error Codes:**

| Constant                   | Value   | Description                   |
|----------------------------|---------|-------------------------------|
| `RES_S_OK`                 | 1       | Generic success               |
| `RES_E_FAIL`               | -1      | Generic fail                  |
| `RES_E_INVALID_PARAMS`     | -2      | Invalid arguments/parameters  |
| `RES_E_NO_MEMORY`          | -3      | No memory condition           |
| `RES_E_NOT_FOUND`          | -4      | No history                    |
| `RES_E_INVALID_VERSION`    | -5      | Invalid version               |
| `RES_E_AUTH_FAILED`        | -6      | Authorization failed          |
| `RES_E_UNSUPPORTED`        | -7      | Unsupported method            |
| `RES_E_AUTO_TRADING_DISABLED` | -8   | Auto-trading disabled         |
| `RES_E_INTERNAL_FAIL`      | -10000  | Internal IPC general error    |
| `RES_E_INTERNAL_FAIL_SEND` | -10001  | Internal IPC send failed      |
| `RES_E_INTERNAL_FAIL_RECEIVE` | -10002 | Internal IPC receive failed   |
| `RES_E_INTERNAL_FAIL_INIT` | -10003  | Internal IPC initialization fail |
| `RES_E_INTERNAL_FAIL_CONNECT` | -10003 | Internal IPC no IPC           |
| `RES_E_INTERNAL_FAIL_TIMEOUT` | -10005 | Internal timeout              |

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```


# `account_info`

Retrieves information about the current trading account.

```python
account_info()
```

**Return Value:**

Returns account information as a named tuple (`namedtuple`). If an error occurs, it returns `None`. To obtain information about the error, use the `last_error()` function. 

**Note:**

This function consolidates data that can be individually obtained using `AccountInfoInteger`, `AccountInfoDouble`, and `AccountInfoString` into a single call. 

**Example:**

```python
import MetaTrader5 as mt5
import pandas as pd

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Connect to the trade account specifying a password and a server
authorized = mt5.login(25115284, password="gqz0343lbdm")
if authorized:
    account_info = mt5.account_info()
    if account_info is not None:
        # Display trading account data 'as is'
        print(account_info)
        # Display trading account data in the form of a dictionary
        print("Show account_info()._asdict():")
        account_info_dict = account_info._asdict()
        for prop in account_info_dict:
            print("  {}={}".format(prop, account_info_dict[prop]))
        print()

        # Convert the dictionary into a DataFrame and print
        df = pd.DataFrame(list(account_info_dict.items()), columns=['property', 'value'])
        print("account_info() as dataframe:")
        print(df)
else:
    print("failed to connect to trade account 25115284 with password=gqz0343lbdm, error code =", mt5.last_error())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```




# `terminal_info`

Retrieves the status and settings of the connected MetaTrader 5 client terminal.

```python
terminal_info()
```

**Return Value:**

Returns information as a named tuple (`namedtuple`). In case of an error, it returns `None`. To obtain information about the error, use the `last_error()` function. 

**Note:**

This function returns all data that can be obtained using `TerminalInfoInteger`, `TerminalInfoDouble`, and `TerminalInfoString` in a single call. 

**Example:**

```python
import MetaTrader5 as mt5
import pandas as pd

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Display data on MetaTrader 5 version
print(mt5.version())

# Display info on the terminal settings and status
terminal_info = mt5.terminal_info()
if terminal_info is not None:
    # Display the terminal data 'as is'
    print(terminal_info)
    # Display data in the form of a list
    print("Show terminal_info()._asdict():")
    terminal_info_dict = terminal_info._asdict()
    for prop in terminal_info_dict:
        print(f"  {prop}={terminal_info_dict[prop]}")
    print()
    # Convert the dictionary into DataFrame and print
    df = pd.DataFrame(list(terminal_info_dict.items()), columns=['property', 'value'])
    print("terminal_info() as dataframe:")
    print(df)
else:
    print("Failed to retrieve terminal information, error code =", mt5.last_error())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```


# `symbols_total`

Retrieves the total number of financial instruments available in the MetaTrader 5 terminal, including custom symbols and those not currently displayed in the Market Watch window.

```python
symbols_total()
```

**Return Value:**

Returns an integer representing the total number of financial instruments.

**Note:**

This function is similar to `SymbolsTotal()` in MQL5. However, `symbols_total()` returns the count of all symbols, including custom ones and those disabled in Market Watch. 

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Get the number of financial instruments
symbols = mt5.symbols_total()
if symbols > 0:
    print("Total symbols =", symbols)
else:
    print("symbols not found")

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```


# symbols_get

Retrieves all financial instruments from the MetaTrader 5 terminal.

```python
symbols_get(
   group="GROUP"      // symbol selection filter
)
```

**Parameters:**

- `group="GROUP"` (optional): A filter to arrange a group of necessary symbols. If specified, the function returns only symbols meeting the given criteria.

**Return Value:**

Returns symbols as a tuple. In case of an error, returns `None`. Error details can be obtained using `last_error()`.

**Notes:**

- The `group` parameter allows filtering symbols by name. The wildcard '*' can be used at the beginning and end of a string.
- The `group` parameter can be used as a named or unnamed parameter; both options function the same way. Using the named option (`group="GROUP"`) enhances code readability.
- The `group` parameter may contain multiple comma-separated conditions. A condition can be set as a mask using '*'. The logical negation symbol '!' can be used for exclusion. All conditions are applied sequentially, meaning inclusion conditions should be specified first, followed by exclusion conditions. For example, `group="*, !EUR"` means all symbols are selected first, and then those containing "EUR" in their names are excluded.
- Unlike `symbol_info()`, the `symbols_get()` function returns data on all requested symbols within a single call.

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Get all symbols
symbols = mt5.symbols_get()
print('Symbols: ', len(symbols))
count = 0
# Display the first five symbols
for s in symbols:
    count += 1
    print("{}. {}".format(count, s.name))
    if count == 5:
        break
print()

# Get symbols containing 'RU' in their names
ru_symbols = mt5.symbols_get("*RU*")
print('len(*RU*): ', len(ru_symbols))
for s in ru_symbols:
    print(s.name)
print()

# Get symbols whose names do not contain 'USD', 'EUR', 'JPY', and 'GBP'
group_symbols = mt5.symbols_get(group="*,!*USD*,!*EUR*,!*JPY*,!*GBP*")
print('len(*,!*USD*,!*EUR*,!*JPY*,!*GBP*):', len(group_symbols))
for s in group_symbols:
    print(s.name, ":", s)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Symbols: 84
1. EURUSD
2. GBPUSD
3. USDCHF
4. USDJPY
5. USDCNH

len(*RU*): 8
EURUSD
USDRUB
USDRUR
EURRUR
EURRUB
FORTS.RUB.M5
EURUSD_T20
EURUSD4

len(*,!*USD*,!*EUR*,!*JPY*,!*GBP*): 13
AUDCAD : SymbolInfo(custom=False, chart_mode=0, select=True, visible=True, session_deals=0, session_buy_orders=0, session_sell_orders=0, volume=0, volumehigh=0, volumelow=0, time=1585069682, digits=5, spread=39, spread_float=True, ticks_bookdepth=10, trade_calc_mode=0, trade_mode=4, start_time=0, expiration_time=0, trade_stops_level=0, trade_freeze_level=0, trade_exemode=1, swap_mode=1, swap_rollover3days=3, margin_hedged_use_leg=False, expiration_mode=7, filling_mode=1, order_mode=127, order_gtc_mode=0, option_mode=0, option_right=0, bid=0.9145, bidhigh=0.9155, bidlow=0.9135, ask=0.9147, askhigh=0.9157, asklow=0.9137, last=0.0, lasthigh=0.0, lastlow=0.0, volume_real=0.0, volumehigh_real=0.0, volumelow_real=0.0, option_strike=0.0, point=0.0001, trade_tick_value=0.1, trade_tick_value_profit=0.1, trade_tick_value_loss=0.1, trade_tick_size=0.0001, trade_contract_size=100000.0, trade_accrued_interest=0.0, trade_face_value=0.0, trade_liquidity_rate=0.0, volume_min=0.01, volume_max=100.0, volume_step=0.01, volume_limit=0.0, swap_long=-0.2, swap_short=-0.1, margin_initial=0.0, margin_maintenance=0.0, session_volume=0.0, session_turnover=0.0, session_interest=0.0, session_buy_orders_volume=0.0, session_sell_orders_volume=0.0, session_open=0.0, session_close=0.0, session_aw=0.0, session_price_settlement=0.0, session_price_limit_min=0.0, session_price_limit_max=0.0, margin_hedged=100000.0, price_change=0.0, price_volatility=0.0, price_theoretical=0.0, price_greeks_delta=0.0, price_greeks_theta=0.0, price_greeks_gamma=0.0, price_greeks_vega=0.0, price_greeks_rho=0.0, price_greeks_omega=0.0, price_sensitivity=0.0, basis=, category=, currency_base=AUD, currency_profit=CAD, currency_margin=AUD, bank=, description=Australian Dollar vs Canadian Dollar, exchange=, formula=, isin=, name=AUDCAD, page=http://www.google.com/finance?q=AUDCAD, path=Forex\AUDCAD)
AUDCHF : SymbolInfo(custom=False, chart_mode=0, select=False, visible=False, session_deals=0, session_buy_orders=0, session_sell_orders=0 
```


# symbol_info

Retrieves data on the specified financial instrument.

```python
symbol_info(
   symbol  // financial instrument name
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument.

**Return Value:**

Returns information as a named tuple structure (`namedtuple`). In case of an error, returns `None`. Error details can be obtained using `last_error()`.

**Notes:**

This function returns all data that can be obtained using `SymbolInfoInteger`, `SymbolInfoDouble`, and `SymbolInfoString` in a single call.

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Attempt to enable the display of the EURJPY symbol in MarketWatch
selected = mt5.symbol_select("EURJPY", True)
if not selected:
    print("Failed to select EURJPY")
    mt5.shutdown()
    quit()

# Display EURJPY symbol properties
symbol_info = mt5.symbol_info("EURJPY")
if symbol_info is not None:
    # Display the terminal data 'as is'
    print(symbol_info)
    print("EURJPY: spread =", symbol_info.spread, " digits =", symbol_info.digits)
    # Display symbol properties as a list
    print('Show symbol_info("EURJPY")._asdict():')
    symbol_info_dict = symbol_info._asdict()
    for prop in symbol_info_dict:
        print("  {}={}".format(prop, symbol_info_dict[prop]))

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
SymbolInfo(custom=False, chart_mode=0, select=True, visible=True, session_deals=0, session_buy_orders=0, session_sell_orders=0, ...)
EURJPY: spread = 17  digits = 3
Show symbol_info("EURJPY")._asdict():
  custom=False
  chart_mode=0
  select=True
  visible=True
  session_deals=0
  session_buy_orders=0
  session_sell_orders=0
  volume=0
  volumehigh=0
  volumelow=0
  time=1585069682
  digits=3
  spread=17
  spread_float=True
  ticks_bookdepth=10
  trade_calc_mode=0
  trade_mode=4
  start_time=0
  expiration_time=0
  trade_stops_level=0
  trade_freeze_level=0
  trade_exemode=1
  swap_mode=1
  swap_rollover3days=3
  margin_hedged_use_leg=False
  expiration_mode=7
  filling_mode=1
  order_mode=127
  order_gtc_mode=0
  option_mode=0
  option_right=0
  bid=120.024
  bidhigh=120.506
  bidlow=118.798
  ask=120.041
  askhigh=120.526
  asklow=118.828
  last=0.0
  lasthigh=0.0
  lastlow=0.0
  volume_real=0.0
  volumehigh_real=0.0
  volumelow_real=0.0
  option_strike=0.0
  point=0.001
  trade_tick_value=0.8977708350166538
  trade_tick_value_profit=0.8977708350166538
  trade_tick_value_loss=0.8978272580355541
  trade_tick_size=0.001
  trade_contract_size=100000.0
  trade_accrued_interest=0.0
  trade_face_value=0.0
  trade_liquidity_rate=0.0
  volume_min=0.01
  volume_max=500.0
  volume_step=0.01
  volume_limit=0.0
  swap_long=-0.2
  swap_short=-1.2
  margin_initial=0.0
  margin_maintenance=0.0
  session_volume=0.0
  session_turnover=0.0
  session_interest=0.0
  session_buy_orders_volume=0.0
  session_sell_orders_volume=0.0
  session_open=0.0
  session_close=0.0
  session_aw=0.0
  session_price_settlement=0.0
  session_price_limit_min=0.0
  session_price_limit_max=0.0
  margin_hedged=100000.0
  price_change=0.0
  price_volatility=0.0
  price_theoretical=0.0
  price_greeks_delta=0.0
  price_greeks_theta=0.0
  price_greeks_gamma=0.0
  price_greeks_vega=0.0
  price_greeks_rho=0.0
  price_greeks_omega=0.0
  price_sensitivity=0.0
  basis=
  category=
  currency_base=EUR
  currency_profit=JPY
  currency_margin=EUR
  bank=
  description=Euro vs Japanese Yen
  exchange=
  formula=
  isin=
  name=EURJPY
  page=http://www.google.com/finance?q=EURJPY
  path=Forex\EURJPY
```



# symbol_info_tick

Retrieves the latest tick data for the specified financial instrument.

```python
symbol_info_tick(
   symbol  // financial instrument name
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument.

**Return Value:**

Returns information as a tuple. In case of an error, returns `None`. Error details can be obtained using `last_error()`.

**Notes:**

This function is similar to `SymbolInfoTick`.

**Example:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Attempt to enable the display of the GBPUSD symbol in MarketWatch
selected = mt5.symbol_select("GBPUSD", True)
if not selected:
    print("Failed to select GBPUSD")
    mt5.shutdown()
    quit()

# Display the last GBPUSD tick
last_tick = mt5.symbol_info_tick("GBPUSD")
print(last_tick)

# Display tick field values in the form of a list
print('Show symbol_info_tick("GBPUSD")._asdict():')
symbol_info_tick_dict = last_tick._asdict()
for prop in symbol_info_tick_dict:
    print("  {}={}".format(prop, symbol_info_tick_dict[prop]))

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Tick(time=1585070338, bid=1.17264, ask=1.17279, last=0.0, volume=0, time_msc=1585070338728, flags=2, volume_real=0.0)
Show symbol_info_tick._asdict():
  time=1585070338
  bid=1.17264
  ask=1.17279
  last=0.0
  volume=0
  time_msc=1585070338728
  flags=2
  volume_real=0.0
```


# symbol_select

Selects a symbol in the MarketWatch window or removes a symbol from the window.

```python
symbol_select(
   symbol,      // financial instrument name
   enable=None  // enable or disable
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument.
- `enable` (optional): A boolean switch. If `False`, the symbol is removed from the MarketWatch window; if `True`, it is added. A symbol cannot be removed if there are open charts or positions associated with it.

**Return Value:**

Returns `True` if successful; otherwise, returns `False`.

**Notes:**

This function is similar to `SymbolSelect` in MQL5.

**Example:**

```python
import MetaTrader5 as mt5
import pandas as pd

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)
print()

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize(login=25115284, server="MetaQuotes-Demo", password="4zatlbqx"):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Attempt to enable the display of the EURCAD symbol in MarketWatch
selected = mt5.symbol_select("EURCAD", True)
if not selected:
    print("Failed to select EURCAD, error code =", mt5.last_error())
else:
    symbol_info = mt5.symbol_info("EURCAD")
    print(symbol_info)
    print("EURCAD: currency_base =", symbol_info.currency_base,
          " currency_profit =", symbol_info.currency_profit,
          " currency_margin =", symbol_info.currency_margin)
    print()

    # Get symbol properties in the form of a dictionary
    print('Show symbol_info()._asdict():')
    symbol_info_dict = symbol_info._asdict()
    for prop in symbol_info_dict:
        print("  {}={}".format(prop, symbol_info_dict[prop]))
    print()

    # Convert the dictionary into a DataFrame and print
    df = pd.DataFrame(list(symbol_info_dict.items()), columns=['property', 'value'])
    print("symbol_info_dict() as dataframe:")
    print(df)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
SymbolInfo(custom=False, chart_mode=0, select=True, visible=True, session_deals=0, session_buy_orders=0, session_sell_orders=0, volume=0, volumehigh=0, ...)
EURCAD: currency_base = EUR   currency_profit = CAD   currency_margin = EUR

Show symbol_info()._asdict():
  custom=False
  chart_mode=0
  select=True
  visible=True
  session_deals=0
  session_buy_orders=0
  session_sell_orders=0
  volume=0
  volumehigh=0
  volumelow=0
  time=1585217595
  digits=5
  spread=39
  spread_float=True
  ticks_bookdepth=10
  trade_calc_mode=0
  trade_mode=4
  start_time=0
  expiration_time=0
  trade_stops_level=0
  trade_freeze_level=0
  trade_exemode=1
  swap_mode=1
  swap_rollover3days=3
  margin_hedged_use_leg=False
  expiration_mode=7
  filling_mode=1
  order_mode=127
  order_gtc_mode=0
  option_mode=0
  option_right=0
  bid=1.55192
  bidhigh=1.55842
  bidlow=1.5419800000000001
  ask=1.5523099999999999
  askhigh=1.55915
  asklow=1.5436299999999998
  last=0.0
  lasthigh=0.0
  lastlow=0.0
  volume_real=0.0
  volumehigh_real=0.0
  volumelow_real=0.0
  option_strike=0.0
  point=1e-05
  trade_tick_value=0.1
  trade_tick_value_profit=0.1
  trade_tick_value_loss=0.1
  trade_tick_size=1e-05
  trade_contract_size=100000.0
  trade_accrued_interest=0.0
  trade_face_value=0.0
  trade_liquidity_rate=0.0
  volume_min=0.01
  volume_max=100.0
  volume_step=0.01
  volume_limit=0.0
  swap_long=-0.2
  swap_short=-0.1
  margin_initial=0.0
  margin_maintenance=0.0
  session_volume=0.0
  session_turnover=0.0
  session_interest=0.0
  session_buy_orders_volume=0.0
  session_sell_orders_volume=0.0
  session_open=0.0
  session_close=0.0
  session_aw=0.0
  session_price_settlement=0.0
  session_price_limit_min=0.0
  session_price_limit_max=0.0
  margin_hedged=100000.0
  price_change=0.0
  price_volatility=0.0
  price_theoretical=0.0
  price_greeks_delta=0.0
  price_greeks_theta=0.0
  price_greeks_gamma=0.0
  price_greeks_vega=0.0
  price_greeks_rho=0.0
  price_greeks_omega=0.0
  price_sensitivity=0.0
  basis=
  category=
  currency_base=EUR
  currency_profit=CAD
  currency_margin=EUR
  bank=
  description=Euro vs Canadian Dollar
  exchange=
  formula=
  isin=
  name=EURCAD
  page=http://www.google.com/finance?q=EURCAD
  path=Forex\EURCAD

symbol_info_dict() as dataframe:
                   property                              value
0                    custom                              False
1                chart_mode                                  0
2                    select                              True
3                   visible                              True
4             session_deals                                  0
5         session_buy_orders                                 0
6        session_sell_orders                                 0
7                    volume                                  0
8               volumehigh                                   0
 
```


# market_book_add

Subscribes the MetaTrader 5 terminal to the Market Depth (order book) change events for a specified symbol.

```python
market_book_add(
   symbol  // financial instrument name
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument.

**Return Value:**

Returns `True` if successful; otherwise, returns `False`.

**Notes:**

- This function is analogous to `MarketBookAdd` in MQL5.
- To retrieve the current Market Depth data after subscribing, use the `market_book_get` function.
- After completing work with the order book, the subscription should be canceled by calling `market_book_release`.

**Example:**

```python
import MetaTrader5 as mt5
import time

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Subscribe to Market Depth updates for EURUSD
if mt5.market_book_add('EURUSD'):
    # Get the Market Depth data 10 times in a loop
    for i in range(10):
        # Get the Market Depth content (Depth of Market)
        items = mt5.market_book_get('EURUSD')
        # Display the entire Market Depth 'as is' in a single string
        print(items)
        # Now display each order separately for more clarity
        if items:
            for it in items:
                # Order content
                print(it._asdict())
        # Pause for 5 seconds before the next request of the Market Depth data
        time.sleep(5)
    # Cancel the subscription to the Market Depth updates (Depth of Market)
    mt5.market_book_release('EURUSD')
else:
    print("mt5.market_book_add('EURUSD') failed, error code =", mt5.last_error())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
[BookInfo(type=1, price=1.10345, volume=1, volume_real=1.0), BookInfo(type=1, price=1.10344, volume=2, volume_real=2.0), ...]
{'type': 1, 'price': 1.10345, 'volume': 1, 'volume_real': 1.0}
{'type': 1, 'price': 1.10344, 'volume': 2, 'volume_real': 2.0}
```


# market_book_get

Retrieves the current Market Depth (order book) entries for the specified financial instrument.

```python
market_book_get(
   symbol  // financial instrument name
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument.

**Return Value:**

Returns the Market Depth content as a tuple of `BookInfo` entries, each containing order type, price, and volume in lots. In case of an error, returns `None`. Error details can be obtained using `last_error()`.

**Notes:**

- Before calling this function, subscribe to Market Depth change events using the `market_book_add()` function.
- This function is similar to `MarketBookGet` in MQL5.

**Example:**

```python
import MetaTrader5 as mt5
import time

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)
print("")

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    # Shut down connection to the MetaTrader 5 terminal
    mt5.shutdown()
    quit()

# Subscribe to market depth updates for EURUSD (Depth of Market)
if mt5.market_book_add('EURUSD'):
    # Get the market depth data 10 times in a loop
    for i in range(10):
        # Get the market depth content (Depth of Market)
        items = mt5.market_book_get('EURUSD')
        # Display the entire market depth 'as is' in a single string
        print(items)
        # Now display each order separately for more clarity
        if items:
            for it in items:
                # Order content
                print(it._asdict())
        # Pause for 5 seconds before the next request of the market depth data
        time.sleep(5)
    # Cancel the subscription to the market depth updates (Depth of Market)
    mt5.market_book_release('EURUSD')
else:
    print("mt5.market_book_add('EURUSD') failed, error code =", mt5.last_error())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.34

(BookInfo(type=1, price=1.20038, volume=250, volume_dbl=250.0), BookInfo(type=1, price=1.20032, volume=100, volume_dbl=100.0), ...)
{'type': 1, 'price': 1.20038, 'volume': 250, 'volume_dbl': 250.0}
{'type': 1, 'price': 1.20032, 'volume': 100, 'volume_dbl': 100.0}
```


# market_book_release

Cancels the subscription of the MetaTrader 5 terminal to the Market Depth (order book) change events for a specified symbol.

```python
market_book_release(
   symbol  // financial instrument name
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument.

**Return Value:**

Returns `True` if successful; otherwise, returns `False`.

**Notes:**

- This function is analogous to `MarketBookRelease` in MQL5.
- Before calling this function, ensure that you have subscribed to Market Depth change events using the `market_book_add()` function.

**Example:**

```python
import MetaTrader5 as mt5
import time

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Subscribe to Market Depth updates for EURUSD
if mt5.market_book_add('EURUSD'):
    # Get the Market Depth data 10 times in a loop
    for i in range(10):
        # Get the Market Depth content (Depth of Market)
        items = mt5.market_book_get('EURUSD')
        # Display the entire Market Depth 'as is' in a single string
        print(items)
        # Now display each order separately for more clarity
        if items:
            for it in items:
                # Order content
                print(it._asdict())
        # Pause for 5 seconds before the next request of the Market Depth data
        time.sleep(5)
    # Cancel the subscription to the Market Depth updates (Depth of Market)
    mt5.market_book_release('EURUSD')
else:
    print("mt5.market_book_add('EURUSD') failed, error code =", mt5.last_error())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
[BookInfo(type=1, price=1.10345, volume=1, volume_real=1.0), BookInfo(type=1, price=1.10344, volume=2, volume_real=2.0), ...]
{'type': 1, 'price': 1.10345, 'volume': 1, 'volume_real': 1.0}
{'type': 1, 'price': 1.10344, 'volume': 2, 'volume_real': 2.0}
```


# copy_rates_from

Retrieves bar data from the MetaTrader 5 terminal starting from the specified date.

```python
copy_rates_from(
   symbol,      // financial instrument name
   timeframe,   // timeframe
   date_from,   // initial bar open date
   count        // number of bars
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument, e.g., "EURUSD".
- `timeframe` (required): The timeframe for the requested bars, set using a value from the `TIMEFRAME` enumeration.
- `date_from` (required): The open date of the first bar in the requested sample, specified as a 'datetime' object or as the number of seconds elapsed since 1970.01.01.
- `count` (required): The number of bars to retrieve.

**Return Value:**

Returns a numpy array with columns: time, open, high, low, close, tick_volume, spread, and real_volume. Returns `None` in case of an error. Error details can be obtained using `last_error()`.

**Notes:**

- Only data with dates less than or equal to the specified `date_from` will be returned; the open time of any bar is always less than or equal to the specified date.
- The MetaTrader 5 terminal provides bars only within the available history on charts. The number of bars available is set in the "Max. bars in chart" parameter.
- When creating the 'datetime' object, Python uses the local time zone, while MetaTrader 5 stores tick and bar open times in UTC. Therefore, 'datetime' should be created in UTC time for functions that use time. Data received from the MetaTrader 5 terminal is in UTC.

**TIMEFRAME Enumeration:**

| Identifier       | Description |
|-------------------|-------------|
| TIMEFRAME_M1      | 1 minute    |
| TIMEFRAME_M2      | 2 minutes   |
| TIMEFRAME_M3      | 3 minutes   |
| TIMEFRAME_M4      | 4 minutes   |
| TIMEFRAME_M5      | 5 minutes   |
| TIMEFRAME_M6      | 6 minutes   |
| TIMEFRAME_M10     | 10 minutes  |
| TIMEFRAME_M12     | 12 minutes  |
| TIMEFRAME_M15     | 15 minutes  |
| TIMEFRAME_M20     | 20 minutes  |
| TIMEFRAME_M30     | 30 minutes  |
| TIMEFRAME_H1      | 1 hour      |
| TIMEFRAME_H2      | 2 hours     |
| TIMEFRAME_H3      | 3 hours     |
| TIMEFRAME_H4      | 4 hours     |
| TIMEFRAME_H6      | 6 hours     |
| TIMEFRAME_H8      | 8 hours     |
| TIMEFRAME_H12     | 12 hours    |
| TIMEFRAME_D1      | 1 day       |
| TIMEFRAME_W1      | 1 week      |
| TIMEFRAME_MN1     | 1 month     |

**Example:**

```python
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import pytz

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Set pandas display options
pd.set_option('display.max_columns', 500)  # number of columns to be displayed
pd.set_option('display.width', 1500)       # max table width to display

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Set time zone to UTC
timezone = pytz.timezone("Etc/UTC")
# Create 'datetime' object in UTC time zone to avoid local time zone offset
utc_from = datetime(2020, 1, 10, tzinfo=timezone)
# Get 10 EURUSD H4 bars starting from 2020.01.10 in UTC time zone
rates = mt5.copy_rates_from("EURUSD", mt5.TIMEFRAME_H4, utc_from, 10)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()

# Display obtained data 'as is'
print("Display obtained data 'as is'")
for rate in rates:
    print(rate)

# Create DataFrame out of the obtained data
rates_frame = pd.DataFrame(rates)
# Convert time in seconds into the datetime format
rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
# Display data
print("\nDisplay dataframe with data")
print(rates_frame)
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Display obtained data 'as is'
(1578614400, 1.112, 1.114, 1.111, 1.113, 158, 0, 0)
(1578616200, 1.113, 1.115, 1.112, 1.114, 162, 0, 0)
...
Display dataframe with data
                 time    open    high     low   close  tick_volume  spread  real_volume
0 2020-01-10 00:00:00  1.1120  1.1140  1.1110  1.1130          158       0            0
1 2020-01-10 04:00:00  1.1130  1.1150  1.1120  1.1140          162       0            0

```


# copy_rates_from_pos

Retrieves bar data from the MetaTrader 5 terminal starting from a specified index.

```python
copy_rates_from_pos(
   symbol,      // financial instrument name
   timeframe,   // timeframe
   start_pos,   // initial bar index
   count        // number of bars
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument, e.g., "EURUSD".
- `timeframe` (required): The timeframe for the requested bars, set using a value from the `TIMEFRAME` enumeration.
- `start_pos` (required): The initial index of the bar from which data is requested. Bar indexing starts from the present to the past, with the zero index representing the current bar.
- `count` (required): The number of bars to retrieve.

**Return Value:**

Returns a numpy array with columns: time, open, high, low, close, tick_volume, spread, and real_volume. Returns `None` in case of an error. Error details can be obtained using `last_error()`.

**Notes:**

- The MetaTrader 5 terminal provides bars only within the available history on charts. The number of bars available is set in the "Max. bars in chart" parameter.
- The `TIMEFRAME` enumeration includes various timeframe identifiers such as `TIMEFRAME_M1` (1 minute), `TIMEFRAME_H1` (1 hour), `TIMEFRAME_D1` (1 day), etc.

**Example:**

```python
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Set pandas display options
pd.set_option('display.max_columns', 500)  # number of columns to be displayed
pd.set_option('display.width', 1500)       # max table width to display

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Get 10 GBPUSD D1 bars from the current day
rates = mt5.copy_rates_from_pos("GBPUSD", mt5.TIMEFRAME_D1, 0, 10)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()

# Display each element of obtained data in a new line
print("Display obtained data 'as is'")
for rate in rates:
    print(rate)

# Create DataFrame out of the obtained data
rates_frame = pd.DataFrame(rates)
# Convert time in seconds into the datetime format
rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
# Display data
print("\nDisplay dataframe with data")
print(rates_frame)
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Display obtained data 'as is'
(1581552000, 1.29568, 1.30692, 1.29441, 1.30412, 68228, 0, 0)
(1581638400, 1.30385, 1.30631, 1.3001, 1.30471, 56498, 0, 0)
...
Display dataframe with data
         time     open     high      low    close  tick_volume  spread  real_volume
0 2020-02-13  1.29568  1.30692  1.29441  1.30412        68228       0            0
1 2020-02-14  1.30385  1.30631  1.30010  1.30471        56498       0            0

```


# copy_rates_range

Retrieves bar data from the MetaTrader 5 terminal within a specified date range.

```python
copy_rates_range(
   symbol,      // financial instrument name
   timeframe,   // timeframe
   date_from,   // start date
   date_to      // end date
)
```

**Parameters:**

- `symbol` (required): The name of the financial instrument, e.g., "EURUSD".
- `timeframe` (required): The timeframe for the requested bars, set using a value from the `TIMEFRAME` enumeration.
- `date_from` (required): The start date for the data retrieval, specified as a 'datetime' object or as the number of seconds elapsed since 1970.01.01. Bars with open times greater than or equal to `date_from` are returned.
- `date_to` (required): The end date for the data retrieval, specified similarly to `date_from`. Bars with open times less than or equal to `date_to` are returned.

**Return Value:**

Returns a numpy array with columns: time, open, high, low, close, tick_volume, spread, and real_volume. Returns `None` in case of an error. Error details can be obtained using `last_error()`.

**Notes:**

- The MetaTrader 5 terminal provides bars only within the available history on charts. The number of bars available is set in the "Max. bars in chart" parameter.
- When creating the 'datetime' object, Python uses the local time zone, while MetaTrader 5 stores tick and bar open times in UTC. Therefore, 'datetime' should be created in UTC time for functions that use time. Data received from the MetaTrader 5 terminal is in UTC.

**Example:**

```python
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import pytz

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Set pandas display options
pd.set_option('display.max_columns', 500)  # number of columns to be displayed
pd.set_option('display.width', 1500)       # max table width to display

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Set time zone to UTC
timezone = pytz.timezone("Etc/UTC")
# Create 'datetime' objects in UTC time zone to avoid local time zone offset
utc_from = datetime(2020, 1, 10, tzinfo=timezone)
utc_to = datetime(2020, 1, 11, hour=13, tzinfo=timezone)
# Get bars from USDJPY M5 within the interval of 2020.01.10 00:00 - 2020.01.11 13:00 in UTC time zone
rates = mt5.copy_rates_range("USDJPY", mt5.TIMEFRAME_M5, utc_from, utc_to)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()

# Display each element of obtained data in a new line
print("Display obtained data 'as is'")
counter = 0
for rate in rates:
    counter += 1
    if counter <= 10:
        print(rate)

# Create DataFrame out of the obtained data
rates_frame = pd.DataFrame(rates)
# Convert time in seconds into the 'datetime' format
rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
# Display data
print("\nDisplay dataframe with data")
print(rates_frame.head(10))
```

**Result:**

```
MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Display obtained data 'as is'
(1578614400, 109.54, 109.55, 109.53, 109.54, 100, 0, 0)
(1578614700, 109.54, 109.56, 109.53, 109.55, 150, 0, 0)
...
Display dataframe with data
                 time    open    high     low   close  tick_volume  spread  real_volume
0 2020-01-10 00:00:00  109.54  109.55  109.53  109.54          100       0            0
1 2020-01-10 00:05:00  109.54  109.56  109.53  109.55          150       0            0
...
```

# copy_ticks_from
The `copy_ticks_from` function in the MetaTrader 5 Python integration allows users to retrieve tick data from the MetaTrader 5 terminal starting from a specified date. This function is essential for analyzing historical tick data for financial instruments.

**Function Signature:**

```python
copy_ticks_from(
   symbol,     # symbol name
   date_from,  # date the ticks are requested from
   count,      # number of requested ticks
   flags       # combination of flags defining the type of requested ticks
)
```


**Parameters:**

- `symbol` (str): Name of the financial instrument, e.g., "EURUSD". This is a required parameter.

- `date_from` (datetime or int): The starting date and time from which ticks are requested. It can be set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is a required parameter.

- `count` (int): The number of ticks to retrieve. This is a required parameter.

- `flags` (int): A flag that defines the type of ticks to request. Possible values include:
  - `COPY_TICKS_INFO`: Ticks with Bid and/or Ask changes.
  - `COPY_TICKS_TRADE`: Ticks with changes in Last and Volume.
  - `COPY_TICKS_ALL`: All ticks.

Flag values are described in the `COPY_TICKS` enumeration.

**Return Value:**

The function returns ticks as a numpy array with the following named columns: `time`, `bid`, `ask`, `last`, and `flags`. The `flags` value can be a combination of flags from the `TICK_FLAG` enumeration. In case of an error, the function returns `None`. Error information can be obtained using `last_error()`.

**Important Notes:**

- When creating the `datetime` object, Python uses the local time zone, while MetaTrader 5 stores tick and bar open times in the UTC time zone (without any shift). Therefore, the `datetime` should be created in UTC time when executing functions that use time. Data received from the MetaTrader 5 terminal is in UTC time.

**Enumerations:**

- **COPY_TICKS**: Defines the types of ticks that can be requested using the `copy_ticks_from()` and `copy_ticks_range()` functions.

  | ID                | Description                                         |
  |-------------------|-----------------------------------------------------|
  | `COPY_TICKS_ALL`  | All ticks                                           |
  | `COPY_TICKS_INFO` | Ticks containing Bid and/or Ask price changes       |
  | `COPY_TICKS_TRADE`| Ticks containing Last and/or Volume price changes   |

- **TICK_FLAG**: Defines possible flags for ticks. These flags are used to describe ticks obtained by the `copy_ticks_from()` and `copy_ticks_range()` functions.

  | ID                | Description                   |
  |-------------------|-------------------------------|
  | `TICK_FLAG_BID`   | Bid price changed             |
  | `TICK_FLAG_ASK`   | Ask price changed             |
  | `TICK_FLAG_LAST`  | Last price changed            |
  | `TICK_FLAG_VOLUME`| Volume changed                |
  | `TICK_FLAG_BUY`   | Last Buy price changed        |
  | `TICK_FLAG_SELL`  | Last Sell price changed       |

**Example Usage:**

```python
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import pytz

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Import the 'pandas' module for displaying data obtained in tabular form
pd.set_option('display.max_columns', 500)  # number of columns to be displayed
pd.set_option('display.width', 1500)       # max table width to display

# Import pytz module for working with time zones
import pytz

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Set time zone to UTC
timezone = pytz.timezone("Etc/UTC")

# Create 'datetime' object in UTC time zone to avoid the implementation of a local time zone offset
utc_from = datetime(2020, 1, 10, tzinfo=timezone)

# Request 100,000 EURUSD ticks starting from 10.01.2020 in UTC time zone
ticks = mt5.copy_ticks_from("EURUSD", utc_from, 100000, mt5.COPY_TICKS_ALL)
print("Ticks received:", len(ticks))

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()

# Display data on each tick on a new line
print("Display obtained ticks 'as is'")
count = 0
for tick in ticks:
    count += 1
    print(tick)
    if count >= 10:
        break

# Create DataFrame out of the obtained data
ticks_frame = pd.DataFrame(ticks)

# Convert time in seconds into the datetime format
ticks_frame['time'] = pd.to_datetime(ticks_frame['time'], unit='s')

# Display data
print("\nDisplay dataframe with ticks")
print(ticks_frame.head(10))
```


**Result:**

```

MetaTrader5 package author:  MetaQuotes Software Corp.
MetaTrader5 package version:  5.0.29
Ticks received: 100000
Display obtained ticks 'as is'
(1578614400, 1.11051, 1.11069, 0.0, 0, 1578614400987, 134, 0.0)
(1578614402, 1.11049, 1.11067, 0.0, 0, 1578614402025, 134, 0.0)
(1578614404, 1.1105, 1.11066, 0.0, 0, 1578614404057, 134, 0.0)
(1578614404, 1.11049, 1.11067, 0.0, 0, 1578614404344, 134, 0.0)
(1578614412, 1.11052, 1.11064, 0.0, 0, 1578614412106, 134, 0.0)
(157861 
```

# copy_ticks_range
The `copy_ticks_range` function in the MetaTrader 5 Python integration enables users to retrieve tick data for a specified date range from the MetaTrader 5 terminal. This function is valuable for analyzing historical tick data over specific periods.

**Function Signature:**

```python
copy_ticks_range(
   symbol,     # symbol name
   date_from,  # date the ticks are requested from
   date_to,    # date up to which the ticks are requested
   flags       # combination of flags defining the type of requested ticks
)
```


**Parameters:**

- `symbol` (str): Name of the financial instrument, e.g., "EURUSD". This is a required parameter.

- `date_from` (datetime or int): The starting date and time from which ticks are requested. It can be set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is a required parameter.

- `date_to` (datetime or int): The ending date and time up to which ticks are requested. Similar to `date_from`, it can be set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is a required parameter.

- `flags` (int): A flag that defines the type of ticks to request. Possible values include:
  - `COPY_TICKS_INFO`: Ticks with Bid and/or Ask changes.
  - `COPY_TICKS_TRADE`: Ticks with changes in Last and Volume.
  - `COPY_TICKS_ALL`: All ticks.

Flag values are described in the `COPY_TICKS` enumeration.

**Return Value:**

The function returns ticks as a numpy array with the following named columns: `time`, `bid`, `ask`, `last`, and `flags`. The `flags` value can be a combination of flags from the `TICK_FLAG` enumeration. In case of an error, the function returns `None`. Error information can be obtained using `last_error()`.

**Important Notes:**

- When creating the `datetime` object, Python uses the local time zone, while MetaTrader 5 stores tick and bar open times in the UTC time zone (without any shift). Therefore, the `datetime` should be created in UTC time when executing functions that use time. Data received from the MetaTrader 5 terminal is in UTC time.

**Enumerations:**

- **COPY_TICKS**: Defines the types of ticks that can be requested using the `copy_ticks_from()` and `copy_ticks_range()` functions.

  | ID                | Description                                         |
  |-------------------|-----------------------------------------------------|
  | `COPY_TICKS_ALL`  | All ticks                                           |
  | `COPY_TICKS_INFO` | Ticks containing Bid and/or Ask price changes       |
  | `COPY_TICKS_TRADE`| Ticks containing Last and/or Volume price changes   |

- **TICK_FLAG**: Defines possible flags for ticks. These flags are used to describe ticks obtained by the `copy_ticks_from()` and `copy_ticks_range()` functions.

  | ID                | Description                   |
  |-------------------|-------------------------------|
  | `TICK_FLAG_BID`   | Bid price changed             |
  | `TICK_FLAG_ASK`   | Ask price changed             |
  | `TICK_FLAG_LAST`  | Last price changed            |
  | `TICK_FLAG_VOLUME`| Volume changed                |
  | `TICK_FLAG_BUY`   | Last Buy price changed        |
  | `TICK_FLAG_SELL`  | Last Sell price changed       |

**Example Usage:**

```python
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import pytz

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# Import the 'pandas' module for displaying data obtained in tabular form
pd.set_option('display.max_columns', 500)  # number of columns to be displayed
pd.set_option('display.width', 1500)       # max table width to display

# Import pytz module for working with time zones
import pytz

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Set time zone to UTC
timezone = pytz.timezone("Etc/UTC")

# Create 'datetime' objects in UTC time zone to avoid the implementation of a local time zone offset
utc_from = datetime(2020, 1, 10, tzinfo=timezone)
utc_to = datetime(2020, 1, 11, tzinfo=timezone)

# Request AUDUSD ticks within 11.01.2020 - 11.01.2020
ticks = mt5.copy_ticks_range("AUDUSD", utc_from, utc_to, mt5.COPY_TICKS_ALL)
print("Ticks received:", len(ticks))

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()

# Display data on each tick on a new line
print("Display obtained ticks 'as is'")
count = 0
for tick in ticks:
    count += 1
    print(tick)
    if count >= 10:
        break

# Create DataFrame out of the obtained data
ticks_frame = pd.DataFrame(ticks)

# Convert time in seconds into the datetime format
ticks_frame['time'] = pd.to_datetime(ticks_frame['time'], unit='s')

# Display data
print("\nDisplay dataframe with ticks")
print(ticks_frame.head(10))
```


**Result:**

```

MetaTrader5 package author:  MetaQuotes Software Corp.
MetaTrader5 package version:  5.0.29
Ticks received: 100000
Display obtained ticks 'as is'
(1578614400, 1.11051, 1.11069, 0.0, 0, 1578614400987, 134, 0.0)
(1578614402, 1.11049, 1.11067, 0.0, 0, 1578614402025, 134, 0.0)
(1578614404, 1.1105, 1.11066, 0.0, 0, 1578614404057, 134, 0.0)
(1578614404, 1.11049, 1.11067, 0.0, 
```


# orders_total

The `orders_total` function in the MetaTrader 5 Python integration retrieves the number of active orders currently present in the trading account. This function is analogous to the MQL5 `OrdersTotal` function.

**Function Signature:**

```python
orders_total() → int
```


**Return Value:**

An integer representing the total number of active orders.

**Example Usage:**

```python
import MetaTrader5 as mt5

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish a connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Retrieve the number of active orders
orders = mt5.orders_total()
if orders > 0:
    print("Total orders =", orders)
else:
    print("No active orders found")

# Shut down the connection to the MetaTrader 5 terminal
mt5.shutdown()
```


**Output:**

```

MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Total orders = 2
```


In this example, the script initializes a connection to the MetaTrader 5 terminal, retrieves the total number of active orders using `orders_total()`, and then prints the count. Finally, it shuts down the connection to the terminal.


# orders_get

The `orders_get` function in the MetaTrader 5 Python integration allows users to retrieve active orders with optional filtering by symbol, group, or ticket. This function is useful for managing and analyzing current orders in a trading account.

**Function Signatures:**

1. Retrieve all active orders:

   ```python
   orders_get()
   ```


2. Retrieve active orders for a specific symbol:

   ```python
   orders_get(symbol="SYMBOL")
   ```


3. Retrieve active orders for symbols matching a group filter:

   ```python
   orders_get(group="GROUP")
   ```


4. Retrieve an active order by its ticket number:

   ```python
   orders_get(ticket=TICKET)
   ```


**Parameters:**

- `symbol` (str, optional): The name of the financial instrument (e.g., "EURUSD"). If specified, the `ticket` parameter is ignored.

- `group` (str, optional): A filter to select orders based on symbol names. Wildcards (`*`) can be used at the beginning and/or end of the string. Multiple conditions can be separated by commas, and the logical negation symbol (`!`) can be used for exclusions.

- `ticket` (int, optional): The unique ticket number of the order.

**Return Value:**

The function returns a list of named tuples, each representing an active order with various attributes such as `ticket`, `time_setup`, `type`, `volume_current`, `price_open`, `symbol`, etc. In case of an error, it returns `None`. Error details can be obtained using `last_error()`.

**Example Usage:**

```python
import MetaTrader5 as mt5
import pandas as pd

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish a connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Retrieve active orders for GBPUSD
orders = mt5.orders_get(symbol="GBPUSD")
if orders is None:
    print("No orders on GBPUSD, error code =", mt5.last_error())
else:
    print("Total orders on GBPUSD:", len(orders))
    for order in orders:
        print(order)

# Retrieve active orders for symbols containing 'GBP'
gbp_orders = mt5.orders_get(group="*GBP*")
if gbp_orders is None:
    print('No orders with group="*GBP*", error code =', mt5.last_error())
else:
    print('orders_get(group="*GBP*") =', len(gbp_orders))
    # Display these orders as a table using pandas.DataFrame
    df = pd.DataFrame(list(gbp_orders), columns=gbp_orders[0]._asdict().keys())
    df.drop(['time_done', 'time_done_msc', 'position_id', 'position_by_id', 'reason', 'volume_initial', 'price_stoplimit'], axis=1, inplace=True)
    df['time_setup'] = pd.to_datetime(df['time_setup'], unit='s')
    print(df)

# Shut down the connection to the MetaTrader 5 terminal
mt5.shutdown()
```


**Output:**

```

MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Total orders on GBPUSD: 2
TradeOrder(ticket=123456789, time_setup=1617187200, type=0, volume_current=0.1, price_open=1.3800, symbol='GBPUSD', ...)
TradeOrder(ticket=987654321, time_setup=1617187300, type=1, volume_current=0.2, price_open=1.3810, symbol='GBPUSD', ...)

orders_get(group="*GBP*") = 4
       ticket         time_setup  type  volume_current  price_open  symbol
0  123456789 2021-03-31 12:00:00     0             0.1      1.3800  GBPUSD
1  987654321 2021-03-31 12:01:40     1             0.2      1.3810  GBPUSD
2  192837465 2021-03-31 12:05:20     0             0.1      0.8570  EURGBP
3  564738291 2021-03-31 12:10:00     1             0.2      0.8580  EURGBP
```

# order_calc_margin
The `order_calc_margin` function in the MetaTrader 5 Python integration calculates the margin required, in the account currency, to perform a specified trading operation. This function is useful for estimating the necessary margin for a particular order type without considering current pending orders and open positions.

**Function Signature:**

```python
order_calc_margin(
   action,  # order type (e.g., ORDER_TYPE_BUY or ORDER_TYPE_SELL)
   symbol,  # symbol name
   volume,  # volume
   price    # open price
)
```


**Parameters:**

- `action` (int): Order type, taking values from the `ORDER_TYPE` enumeration. Possible values include:
  - `ORDER_TYPE_BUY`: Market buy order
  - `ORDER_TYPE_SELL`: Market sell order
  - `ORDER_TYPE_BUY_LIMIT`: Buy Limit pending order
  - `ORDER_TYPE_SELL_LIMIT`: Sell Limit pending order
  - `ORDER_TYPE_BUY_STOP`: Buy Stop pending order
  - `ORDER_TYPE_SELL_STOP`: Sell Stop pending order
  - `ORDER_TYPE_BUY_STOP_LIMIT`: Upon reaching the order price, a Buy Limit pending order is placed at the StopLimit price
  - `ORDER_TYPE_SELL_STOP_LIMIT`: Upon reaching the order price, a Sell Limit pending order is placed at the StopLimit price
  - `ORDER_TYPE_CLOSE_BY`: Order for closing a position by an opposite one

- `symbol` (str): Name of the financial instrument (e.g., "EURUSD").

- `volume` (float): Trading operation volume (e.g., 0.1 for 0.1 lots).

- `price` (float): Open price for the order.

**Return Value:**

The function returns a real value representing the required margin if successful; otherwise, it returns `None`. Error information can be obtained using `last_error()`.

**Example Usage:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Get account currency
account_currency = mt5.account_info().currency
print("Account currency:", account_currency)

# List of symbols to check margin
symbols = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "EURJPY", "GBPJPY")
print("Symbols to check margin:", symbols)
action = mt5.ORDER_TYPE_BUY
lot = 0.1

for symbol in symbols:
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(symbol, "not found, skipped")
        continue
    if not symbol_info.visible:
        print(symbol, "is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print("symbol_select({}) failed, skipped".format(symbol))
            continue
    ask = mt5.symbol_info_tick(symbol).ask
    margin = mt5.order_calc_margin(action, symbol, lot, ask)
    if margin is not None:
        print("   {} buy {} lot margin: {} {}".format(symbol, lot, margin, account_currency))
    else:
        print("order_calc_margin failed, error code =", mt5.last_error())

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```


**Output:**

```

MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Account currency: USD
Symbols to check margin: ('EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY')
   EURUSD buy 0.1 lot margin: 109.91 USD
   GBPUSD buy 0.1 lot margin: 122.73 USD
   USDJPY buy 0.1 lot margin: 100.0 USD
   USDCHF buy 0.1 lot margin: 100.0 USD
   EURJPY buy 0.1 lot margin: 109.91 USD
   GBPJPY buy 0.1 lot margin: 122.73 USD
```


In this example, the script initializes a connection to the MetaTrader 5 terminal, retrieves the account currency, and calculates the required margin for a 0.1 lot buy order for each specified symbol. It then prints the required margin for each symbol and shuts down the connection to the terminal.

# order_calc_profit
The `order_calc_profit` function in the MetaTrader 5 Python integration calculates the profit or loss, in the account currency, for a specified trading operation. This function is useful for estimating the potential outcome of a trade based on the given parameters.

**Function Signature:**

```python
order_calc_profit(
   action,       # order type (ORDER_TYPE_BUY or ORDER_TYPE_SELL)
   symbol,       # symbol name
   volume,       # volume
   price_open,   # open price
   price_close   # close price
)
```


**Parameters:**

- `action` (int): Order type, which can be one of the following values:
  - `ORDER_TYPE_BUY`: Market buy order
  - `ORDER_TYPE_SELL`: Market sell order

- `symbol` (str): Name of the financial instrument (e.g., "EURUSD").

- `volume` (float): Trading operation volume (e.g., 1.0 for 1 lot).

- `price_open` (float): Open price of the trade.

- `price_close` (float): Close price of the trade.

**Return Value:**

The function returns a real value representing the profit or loss in the account currency if successful; otherwise, it returns `None`. Error information can be obtained using `last_error()`.

**Example Usage:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Get account currency
account_currency = mt5.account_info().currency
print("Account currency:", account_currency)

# List of symbols to check profit
symbols = ("EURUSD", "GBPUSD", "USDJPY")
print("Symbols to check profit:", symbols)

# Estimate profit for buying and selling
lot = 1.0
distance = 300  # distance in points
for symbol in symbols:
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(symbol, "not found, skipped")
        continue
    if not symbol_info.visible:
        print(symbol, "is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print("symbol_select({}) failed, skipped".format(symbol))
            continue
    point = mt5.symbol_info(symbol).point
    symbol_tick = mt5.symbol_info_tick(symbol)
    ask = symbol_tick.ask
    bid = symbol_tick.bid
    buy_profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, lot, ask, ask + distance * point)
    if buy_profit is not None:
        print("   buy {} {} lot: profit on {} points => {} {}".format(symbol, lot, distance, buy_profit, account_currency))
    else:
        print("order_calc_profit(ORDER_TYPE_BUY) failed, error code =", mt5.last_error())
    sell_profit = mt5.order_calc_profit(mt5.ORDER_TYPE_SELL, symbol, lot, bid, bid - distance * point)
    if sell_profit is not None:
        print("   sell {} {} lot: profit on {} points => {} {}".format(symbol, lot, distance, sell_profit, account_currency))
    else:
        print("order_calc_profit(ORDER_TYPE_SELL) failed, error code =", mt5.last_error())
    print()

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```


**Output:**

```

MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Account currency: USD
Symbols to check profit: ('EURUSD', 'GBPUSD', 'USDJPY')
   buy EURUSD 1.0 lot: profit on 300 points => 300.0 USD
   sell EURUSD 1.0 lot: profit on 300 points => 300.0 USD

   buy GBPUSD 1.0 lot: profit on 300 points => 300.0 USD
   sell GBPUSD 1.0 lot: profit on 300 points => 300.0 USD

   buy USDJPY 1.0 lot: profit on 300 points => 276.54 USD
   sell USDJPY 1.0 lot: profit on 300 points => 278.09 USD

```

# order_check
The `order_check` function in the MetaTrader 5 Python integration allows users to verify the sufficiency of funds and the correctness of parameters for a proposed trading operation before execution. This pre-check helps in assessing whether the trade can be successfully performed under current account conditions.

**Function Signature:**

```python
order_check(request) → MqlTradeCheckResult
```


**Parameters:**

- `request` (dict): A dictionary representing the trade request, containing fields that describe the desired trading action.

**Return Value:**

The function returns an `MqlTradeCheckResult` structure, which includes details such as:

- `retcode`: Return code indicating the result of the check.

- `balance`: Account balance after the trade.

- `equity`: Account equity after the trade.

- `profit`: Current profit after the trade.

- `margin`: Required margin for the trade.

- `margin_free`: Free margin remaining after the trade.

- `margin_level`: Margin level percentage after the trade.

- `comment`: Additional comments or error messages.


**Note**

Successful sending of a request does not entail that the requested trading operation will be executed successfully. The `order_check` function is similar to OrderCheck.

**TRADE_REQUEST_ACTIONS**

| ID                    | Description                                                        |
|-----------------------|--------------------------------------------------------------------|
| TRADE_ACTION_DEAL     | Place an order for an instant deal with the specified parameters (set a market order) |
| TRADE_ACTION_PENDING  | Place an order for performing a deal at specified conditions (pending order) |
| TRADE_ACTION_SLTP     | Change open position Stop Loss and Take Profit                     |
| TRADE_ACTION_MODIFY   | Change parameters of the previously placed trading order           |
| TRADE_ACTION_REMOVE   | Remove previously placed pending order                             |
| TRADE_ACTION_CLOSE_BY | Close a position by an opposite one                                |

**ORDER_TYPE_FILLING**

| ID                    | Description                                                        |
|-----------------------|--------------------------------------------------------------------|
| ORDER_FILLING_FOK     | This execution policy means that an order can be executed only in the specified volume. If the necessary amount of a financial instrument is currently unavailable in the market, the order will not be executed. The desired volume can be made up of several available offers. |
| ORDER_FILLING_IOC     | An agreement to execute a deal at the maximum volume available in the market within the volume specified in the order. If the request cannot be filled completely, an order with the available volume will be executed, and the remaining volume will be canceled. |
| ORDER_FILLING_RETURN  | This policy is used only for market (ORDER_TYPE_BUY and ORDER_TYPE_SELL), limit and stop limit orders (ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT, ORDER_TYPE_BUY_STOP_LIMIT, and ORDER_TYPE_SELL_STOP_LIMIT) and only for the symbols with Market or Exchange execution modes. If filled partially, a market or limit order with the remaining volume is not canceled and is processed further. During activation of the ORDER_TYPE_BUY_STOP_LIMIT and ORDER_TYPE_SELL_STOP_LIMIT orders, an appropriate limit order ORDER_TYPE_BUY_LIMIT/ORDER_TYPE_SELL_LIMIT with the ORDER_FILLING_RETURN type is created. |

**ORDER_TYPE_TIME**

| ID                      | Description                                                        |
|-------------------------|--------------------------------------------------------------------|
| ORDER_TIME_GTC          | The order stays in the queue until it is manually canceled         |
| ORDER_TIME_DAY          | The order is active only during the current trading day            |
| ORDER_TIME_SPECIFIED    | The order is active until the specified date                       |
| ORDER_TIME_SPECIFIED_DAY| The order is active until 23:59:59 of the specified day. If this time appears to be out of a trading session, the expiration is processed at the nearest trading time. |




**Example Usage:**

```python
import MetaTrader5 as mt5

# Display data on the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Get account currency
account_currency = mt5.account_info().currency
print("Account currency:", account_currency)

# Prepare the request structure
symbol = "USDJPY"
symbol_info = mt5.symbol_info(symbol)
if symbol_info is None:
    print(symbol, "not found, cannot call order_check()")
    mt5.shutdown()
    quit()

# If the symbol is unavailable in MarketWatch, add it
if not symbol_info.visible:
    print(symbol, "is not visible, trying to switch on")
    if not mt5.symbol_select(symbol, True):
        print("symbol_select({}) failed, exit".format(symbol))
        mt5.shutdown()
        quit()

# Prepare the request
point = mt5.symbol_info(symbol).point
price = mt5.symbol_info_tick(symbol).ask
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": 1.0,
    "type": mt5.ORDER_TYPE_BUY,
    "price": price,
    "sl": price - 100 * point,
    "tp": price + 100 * point,
    "deviation": 10,
    "magic": 234000,
    "comment": "python script",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_RETURN,
}

# Perform the check and display the result 'as is'
result = mt5.order_check(request)
print(result)

# Request the result as a dictionary and display it element by element
result_dict = result._asdict()
for field in result_dict.keys():
    print("  {}={}".format(field, result_dict[field]))

# If this is a trading request structure, display it element by element as well
if field == "request":
    traderequest_dict = result_dict[field]._asdict()
    for tradereq_field in traderequest_dict:
        print("  traderequest: {}={}".format(tradereq_field, traderequest_dict[tradereq_field]))

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```


**Output:**

```

MetaTrader5 package author: MetaQuotes Software Corp.
MetaTrader5 package version: 5.0.29
Account currency: USD
TradeCheckResult(retcode=0, balance=101300.53, equity=68319.53, profit=-32981.0, margin=51193.67, margin_free=17125.86, margin_level=133.45, comment='Done', request=TradeRequest(action=1, magic=234000, order=0, symbol='USDJPY', volume=1.0, price=110.25, stoplimit=0.0, sl=109.25, tp=111.25, deviation=10, type=0, type_filling=2, type_time=0, expiration=0, comment='python script', position=0, position_by=0))
  retcode=0
  balance=101300.53
  equity=68319.53
  profit=-32981.0
  margin=51193.67
  margin_free=17125.86
  margin_level=133.45
  comment=Done
  request=TradeRequest(action=1, magic=234000, order=0, symbol='USDJPY', volume=1.0, price=110.25, stoplimit=0.0, sl=109.25, tp=111.25, deviation=10, type=0, type_filling=2, type_time=0, expiration=0, comment='python script', position=0, position_by=0)
    traderequest: action=1
    traderequest: magic=234000
    traderequest: order=0
    traderequest: symbol=USDJPY
    traderequest: volume=1.0
    traderequest: price=110.25
    traderequest: stoplimit=0.0
    traderequest: sl=109.25
    traderequest: tp=111.25
    traderequest: deviation=10
    traderequest: type=0
    traderequest: type_filling=2
    traderequest: type_time=0
    traderequest: expiration=0
    traderequest: comment=python script
    traderequest: position=0
    traderequest: position_by=0
```



# order_send

Send a request to perform a trading operation from the terminal to the trade server. The function is similar to OrderSend.

```python
order_send(
   request      // request structure
);
```

**Parameters**

- `request` [in]: MqlTradeRequest type structure describing a required trading action. Required unnamed parameter. Example of filling in a request and the enumeration content are described below.

**Return Value**

Execution result as the MqlTradeResult structure. The `request` field in the answer contains the structure of a trading request passed to `order_send()`. The info on the error can be obtained using last_error().

**The MqlTradeRequest trading request structure**

| Field        | Description                                                                                                                                                                                                                  |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `action`     | Trading operation type. The value can be one of the values of the TRADE_REQUEST_ACTIONS enumeration                                                                                                                           |
| `magic`      | EA ID. Allows arranging the analytical handling of trading orders. Each EA can set a unique ID when sending a trading request                                                                                                |
| `order`      | Order ticket. Required for modifying pending orders                                                                                                                                                                          |
| `symbol`     | The name of the trading instrument, for which the order is placed. Not required when modifying orders and closing positions                                                                                                  |
| `volume`     | Requested volume of a deal in lots. A real volume when making a deal depends on an order execution type.                                                                                                                     |
| `price`      | Price at which an order should be executed. The price is not set in case of market orders for instruments of the "Market Execution" (SYMBOL_TRADE_EXECUTION_MARKET) type having the TRADE_ACTION_DEAL type                   |
| `stoplimit`  | A price a pending Limit order is set at when the price reaches the 'price' value (this condition is mandatory). The pending order is not passed to the trading system until that moment                                      |
| `sl`         | A price a Stop Loss order is activated at when the price moves in an unfavorable direction                                                                                                                                   |
| `tp`         | A price a Take Profit order is activated at when the price moves in a favorable direction                                                                                                                                    |
| `deviation`  | Maximum acceptable deviation from the requested price, specified in points                                                                                                                                                   |
| `type`       | Order type. The value can be one of the values of the ORDER_TYPE enumeration                                                                                                                                                 |
| `type_filling` | Order filling type. The value can be one of the ORDER_TYPE_FILLING values                                                                                                                                                  |
| `type_time`  | Order type by expiration. The value can be one of the ORDER_TYPE_TIME values                                                                                                                                                 |
| `expiration` | Pending order expiration time (for TIME_SPECIFIED type orders)                                                                                                                                                               |
| `comment`    | Comment to an order                                                                                                                                                                                                          |
| `position`   | Position ticket. Fill it when changing and closing a position for its clear identification. Usually, it is the same as the ticket of the order that opened the position.                                                     |
| `position_by`| Opposite position ticket. It is used when closing a position by an opposite one (opened at the same symbol but in the opposite direction).                                                                                   |

**Note**

A trading request passes several verification stages on the trade server. First, the validity of all the necessary request fields is checked. If there are no errors, the server accepts the order for further handling. See the OrderSend function description for the details about executing trading operations.

**Example:**

```python
import time
import MetaTrader5 as mt5

# display data on the MetaTrader 5 package
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)

# establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# prepare the buy request structure
symbol = "USDJPY"
symbol_info = mt5.symbol_info(symbol)
if symbol_info is None:
    print(symbol, "not found, cannot call order_check()")
    mt5.shutdown()
    quit()

# if the symbol is unavailable in MarketWatch, add it
if not symbol_info.visible:
    print(symbol, "is not visible, trying to switch on")
    if not mt5.symbol_select(symbol, True):
        print("symbol_select({}) failed, exit", symbol)
        mt5.shutdown()
        quit()

lot = 0.1
point = mt5.symbol_info(symbol).point
price = mt5.symbol_info_tick(symbol).ask
deviation = 20
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot,
    "type": mt5.ORDER_TYPE_BUY,
    "price": price,
    "sl": price - 100 * point,
    "tp": price + 100 * point,
    "deviation": deviation,
    "magic": 234000,
    "comment": "python script open",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_RETURN,
}

# send a trading request
result = mt5.order_send(request)
# check the execution result
print("1. order_send(): by {} {} lots at {} with deviation={} points".format(symbol, lot, price, deviation))
if result.retcode != mt5.TRADE_RETCODE_DONE:
    print("2. order_send failed, retcode={}".format(result.retcode))
else:
    print("2. order_send done, ", result)
    print("   opened position with POSITION_TICKET={}".format(result.order))
    print("   sleep 2 seconds before closing position #{}".format(result.order))
    time.sleep(2)
    position_id = result.order
    price = mt5.symbol_info_tick(symbol).bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "position": position_id,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "python script close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    # send a trading request to close the position
    result = mt5.order_send(request)
    # check the execution result
    print("3. close position #{}: sell {} {} lots at {} with deviation={} points".format(position_id, symbol, lot, price, deviation))
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("4. order_send failed, retcode={}".format(result.retcode))
    else:
        print("4. position #{} closed, {}".format(position_id, result))

# shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
Result
MetaTrader5 package author:  MetaQuotes Software Corp.
MetaTrader5 package version:  5.0.29
1. order_send(): by USDJPY 0.1 lots at 108.023 with deviation=20 points
2. order_send done,  OrderSendResult(retcode=10009, deal=535084512, order=557416535, volume=0.1, price=108.023, ...
   opened position with POSITION_TICKET=557416535
   sleep 2 seconds before closing position #557416535
3. close position #557416535: sell USDJPY 0.1 lots at 108.018 with deviation=20 points
4. position #557416535 closed, OrderSendResult(retcode=10009, deal=535084631, order=557416654, volume=0.1, price=...
   retcode=10009
   deal=535084631
   order=557416654
   volume=0.1
   price=108.015
   bid=108.015
   ask=108.02
   comment=Request executed
   request_id=55
   retcode_external=0
   request=TradeRequest(action=1, magic=234000, order=0, symbol='USDJPY', volume=0.1, price=108.018, stoplimit=0.0, ...
       traderequest: action=1
       traderequest: magic=234000
       traderequest: order=0
       traderequest: symbol=USDJPY
       traderequest: volume=0.1
       traderequest: price=108.018
       traderequest: stoplimit=0.0
       traderequest: sl=0.0
       traderequest: tp=0.0
       traderequest: deviation=20
       traderequest: type=1
       traderequest: type_filling=2
       traderequest: type_time=0
       traderequest: expiration=0
       traderequest: comment=python script close
       traderequest: position=557416535
       traderequest: position_by=0
```



# positions_total

Retrieve the number of open positions.

```python
positions_total()
```

**Return Value**

An integer representing the total number of open positions.

**Note**

This function is analogous to `PositionsTotal` in MQL5.

**Example:**

```python
import MetaTrader5 as mt5

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Check for open positions
positions_total = mt5.positions_total()
if positions_total > 0:
    print("Total positions =", positions_total)
else:
    print("No positions found")

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```



# positions_get

Retrieve open positions with optional filtering by symbol, group, or ticket.

```python
positions_get(
   symbol="SYMBOL",  // Optional: name of the symbol
   group="GROUP",    // Optional: filter for selecting positions by symbol group
   ticket=TICKET     // Optional: position ticket number
)
```

**Parameters**

- `symbol` (optional): Name of the symbol to filter positions. If specified, the `ticket` parameter is ignored.
- `group` (optional): Filter for selecting positions by symbol group. Supports masks using '*' and exclusions using '!'. For example, `group="*, !EUR"` selects positions for all symbols except those containing "EUR".
- `ticket` (optional): Position ticket number. If specified, retrieves the position with this ticket.

**Return Value**

Returns a list of named tuples, each representing an open position. Returns `None` in case of an error. To obtain error information, use `last_error()`.

**Note**

This function allows retrieving all open positions in a single call, similar to using `PositionsTotal` and `PositionSelect` in tandem.

**Example:**

```python
import MetaTrader5 as mt5
import pandas as pd

pd.set_option('display.max_columns', 500)  # Number of columns to display
pd.set_option('display.width', 1500)       # Max table width to display

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)
print()

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Get open positions on USDCHF
positions = mt5.positions_get(symbol="USDCHF")
if positions is None:
    print("No positions on USDCHF, error code =", mt5.last_error())
elif len(positions) > 0:
    print("Total positions on USDCHF =", len(positions))
    # Display all open positions
    for position in positions:
        print(position)

# Get the list of positions on symbols whose names contain "*USD*"
usd_positions = mt5.positions_get(group="*USD*")
if usd_positions is None:
    print('No positions with group="*USD*", error code =', mt5.last_error())
elif len(usd_positions) > 0:
    print('positions_get(group="*USD*") =', len(usd_positions))
    # Display these positions as a table using pandas.DataFrame
    df = pd.DataFrame(list(usd_positions), columns=usd_positions[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.drop(['time_update', 'time_msc', 'time_update_msc', 'external_id'], axis=1, inplace=True)
    print(df)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author:  MetaQuotes Software Corp.
MetaTrader5 package version:  5.0.29
 
positions_get(group="*USD*")=5
      ticket                time  type  magic  identifier  reason  volume  price_open       sl       tp  price_current  swap  profit  symbol comment
0  548297723 2020-03-18 15:00:55     1      0   548297723       3    0.01     1.09301  1.11490  1.06236        1.10104 -0.10   -8.03  EURUSD        
1  548655158 2020-03-18 20:31:26     0      0   548655158       3    0.01     1.08676  1.06107  1.12446        1.10099 -0.08   14.23  EURUSD        
2  548663803 2020-03-18 20:40:04     0      0   548663803       3    0.01     1.08640  1.06351  1.11833        1.10099 -0.08   14.59  EURUSD        
3  548847168 2020-03-19 01:10:05     0      0   548847168       3    0.01     1.09545  1.05524  1.15122        1.10099 -0.06    5.54  EURUSD        
4  548847194 2020-03-19 01:10:07     0      0   548847194       3    0.02     1.09536  1.04478  1.16587        1.10099 -0.08   11.26  EURUSD  
```



# history_orders_total

Retrieve the number of orders in the trading history within a specified time interval.

```python
history_orders_total(
   date_from,  # Date from which the orders are requested
   date_to     # Date up to which the orders are requested
)
```

**Parameters**

- `date_from` [in]: The start date for the order history retrieval. This can be set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is a required parameter.
- `date_to` [in]: The end date for the order history retrieval. Similar to `date_from`, it can be set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is also a required parameter.

**Return Value**

Returns an integer representing the total number of orders found in the trading history within the specified time interval.

**Note**

This function is analogous to `HistoryOrdersTotal` in MQL5.

**Example:**

```python
from datetime import datetime
import MetaTrader5 as mt5

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Define the time interval for the order history
from_date = datetime(2020, 1, 1)
to_date = datetime.now()

# Retrieve the number of orders in the specified history interval
history_orders = mt5.history_orders_total(from_date, to_date)
if history_orders > 0:
    print("Total history orders =", history_orders)
else:
    print("No orders found in history")

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```



# history_orders_get

Retrieve orders from the trading history with optional filtering by time interval, order ticket, or position ticket. There are three call options:

1. **Specify a time interval**: Returns all orders within the specified interval.

   ```python
   history_orders_get(
      date_from,        # Start date for the orders
      date_to,          # End date for the orders
      group="GROUP"     # Optional: filter for selecting orders by symbol group
   )
   ```

2. **Specify an order ticket**: Returns the order with the specified ticket.

   ```python
   history_orders_get(
      ticket=TICKET     # Order ticket number
   )
   ```

3. **Specify a position ticket**: Returns all orders associated with the specified position ticket (stored in the `ORDER_POSITION_ID` property).

   ```python
   history_orders_get(
      position=POSITION # Position ticket number
   )
   ```

**Parameters**

- `date_from` [in]: Start date for the orders. Set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is a required unnamed parameter when specifying a time interval.
- `date_to` [in]: End date for the orders. Similar to `date_from`, it is set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is also a required unnamed parameter when specifying a time interval.
- `group="GROUP"` [in]: Filter to select orders by symbol group. This is an optional named parameter. If specified, the function returns only orders that meet the criteria for the symbol name. The `group` parameter can contain multiple comma-separated conditions. A condition can be set as a mask using '*'. The logical negation symbol '!' can be used for exclusion. All conditions are applied sequentially, meaning inclusion conditions should be specified first, followed by exclusion conditions. For example, `group="*, !EUR"` means that orders for all symbols are selected first, and then those containing "EUR" in symbol names are excluded.
- `ticket=TICKET` [in]: Order ticket number to retrieve. This is an optional parameter. If not specified, the filter is not applied.
- `position=POSITION` [in]: Position ticket number (stored in `ORDER_POSITION_ID`) to retrieve all associated orders. This is an optional parameter. If not specified, the filter is not applied.

**Return Value**

Returns information in the form of a named tuple structure (`namedtuple`). Returns `None` in case of an error. Error information can be obtained using `last_error()`.

**Note**

This function allows retrieving all historical orders within a specified period in a single call, similar to using `HistoryOrdersTotal` and `HistoryOrderSelect` in tandem.

**Example:**

```python
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

pd.set_option('display.max_columns', 500)  # Number of columns to display
pd.set_option('display.width', 1500)       # Max table width to display

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)
print()

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Define the time interval for retrieving historical orders
from_date = datetime(2020, 1, 1)
to_date = datetime.now()

# Retrieve historical orders for symbols containing 'GBP' within the specified time interval
history_orders = mt5.history_orders_get(from_date, to_date, group="*GBP*")
if history_orders is None:
    print("No history orders with group=\"*GBP*\", error code =", mt5.last_error())
elif len(history_orders) > 0:
    print(f"history_orders_get({from_date}, {to_date}, group=\"*GBP*\") = {len(history_orders)}")
    print()

# Retrieve all historical orders associated with a specific position ticket
position_id = 530218319
position_history_orders = mt5.history_orders_get(position=position_id)
if position_history_orders is None:
    print(f"No orders with position #{position_id}")
    print("error code =", mt5.last_error())
elif len(position_history_orders) > 0:
    print(f"Total history orders on position #{position_id}: {len(position_history_orders)}")
    # Display all historical orders with the specified position ticket
    for position_order in position_history_orders:
        print(position_order)
    print()
    # Display these orders as a table using pandas.DataFrame
    df = pd.DataFrame(list(position_history_orders), columns=position_history_orders[0]._asdict().keys())
    df.drop(['time_expiration', 'type_time', 'state', 'position_by_id', 'reason', 'volume_current', 'price_stoplimit', 'sl', 'tp'], axis=1, inplace=True)
    df['time_setup'] = pd.to_datetime(df['time_setup'], unit='s')
    df['time_done'] = pd.to_datetime(df['time_done'], unit='s')
    print(df)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author:  MetaQuotes Software Corp.
MetaTrader5 package version:  5.0.29
 
history_orders_get(2020-01-01 00:00:00, 2020-03-25 17:17:32.058795, group="*GBP*")=14
 
Total history orders on position #530218319: 2
TradeOrder(ticket=530218319, time_setup=1582282114, time_setup_msc=1582282114681, time_done=1582303777, time_done_msc=1582303777582, time_expiration=0, ...
TradeOrder(ticket=535548147, time_setup=1583176242, time_setup_msc=1583176242265, time_done=1583176242, time_done_msc=1583176242265, time_expiration=0, ...
 
      ticket          time_setup  time_setup_msc           time_done  time_done_msc  type  type_filling  magic  position_id  volume_initial  price_open  price_current  symbol comment external_id
0  530218319 2020-02-21 10:48:34   1582282114681 2020-02-21 16:49:37  1582303777582     2             2      0    530218319            0.01     0.97898        0.97863  USDCHF                    
1  535548147 2020-03-02 19:10:42   1583176242265 2020-03-02 19:10:42  1583176242265     1             0      0    530218319            0.01     0.95758        0.95758  USDCHF 
```




# history_deals_total

Retrieve the number of deals in the trading history within a specified time interval.

```python
history_deals_total(
   date_from,  # Start date for the deals
   date_to     # End date for the deals
)
```

**Parameters**

- `date_from` [in]: The start date from which the deals are requested. This can be set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is a required unnamed parameter.
- `date_to` [in]: The end date up to which the deals are requested. Similar to `date_from`, it can be set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is also a required unnamed parameter.

**Return Value**

Returns an integer representing the total number of deals found in the trading history within the specified time interval.

**Note**

This function is analogous to `HistoryDealsTotal` in MQL5.

**Example:**

```python
from datetime import datetime
import MetaTrader5 as mt5

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Define the time interval for the deal history
from_date = datetime(2020, 1, 1)
to_date = datetime.now()

# Retrieve the number of deals in the specified history interval
deals = mt5.history_deals_total(from_date, to_date)
if deals > 0:
    print("Total deals =", deals)
else:
    print("Deals not found in history")

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```



# history_deals_get

Retrieve deals from the trading history with optional filtering by time interval, order ticket, or position ticket. There are three ways to call this function:

1. **Specify a time interval**: Returns all deals within the specified interval.

   ```python
   history_deals_get(
      date_from,        # Start date for the deals
      date_to,          # End date for the deals
      group="GROUP"     # Optional: filter for selecting deals by symbol group
   )
   ```

2. **Specify an order ticket**: Returns all deals associated with the specified order ticket.

   ```python
   history_deals_get(
      ticket=TICKET     # Order ticket number
   )
   ```

3. **Specify a position ticket**: Returns all deals associated with the specified position ticket.

   ```python
   history_deals_get(
      position=POSITION # Position ticket number
   )
   ```

**Parameters**

- `date_from` [in]: Start date for the deals. Set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is a required unnamed parameter when specifying a time interval.
- `date_to` [in]: End date for the deals. Similar to `date_from`, it is set using a `datetime` object or as the number of seconds elapsed since January 1, 1970. This is also a required unnamed parameter when specifying a time interval.
- `group="GROUP"` [in]: Filter to select deals by symbol group. This is an optional named parameter. If specified, the function returns only deals that meet the criteria for the symbol name. The `group` parameter can contain multiple comma-separated conditions. A condition can be set as a mask using '*'. The logical negation symbol '!' can be used for exclusion. All conditions are applied sequentially, meaning inclusion conditions should be specified first, followed by exclusion conditions. For example, `group="*, !EUR"` means that deals for all symbols are selected first, and then those containing "EUR" in symbol names are excluded.
- `ticket=TICKET` [in]: Order ticket number to retrieve all associated deals. This is an optional parameter. If not specified, the filter is not applied.
- `position=POSITION` [in]: Position ticket number to retrieve all associated deals. This is an optional parameter. If not specified, the filter is not applied.

**Return Value**

Returns information in the form of a named tuple structure (`namedtuple`). Returns `None` in case of an error. Error information can be obtained using `last_error()`.

**Note**

This function allows retrieving all historical deals within a specified period in a single call, similar to using `HistoryDealsTotal` and `HistoryDealSelect` in tandem.

**Example:**

```python
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

pd.set_option('display.max_columns', 500)  # Number of columns to display
pd.set_option('display.width', 1500)       # Max table width to display

# Display information about the MetaTrader 5 package
print("MetaTrader5 package author:", mt5.__author__)
print("MetaTrader5 package version:", mt5.__version__)
print()

# Establish connection to the MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Define the time interval for retrieving historical deals
from_date = datetime(2020, 1, 1)
to_date = datetime.now()

# Retrieve historical deals for symbols containing 'GBP' within the specified time interval
deals = mt5.history_deals_get(from_date, to_date, group="*GBP*")
if deals is None:
    print("No deals with group=\"*GBP*\", error code =", mt5.last_error())
elif len(deals) > 0:
    print(f"history_deals_get({from_date}, {to_date}, group=\"*GBP*\") = {len(deals)}")
    # Display all obtained deals 'as is'
    for deal in deals:
        print(" ", deal)
    print()
    # Display these deals as a table using pandas.DataFrame
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(df)

# Retrieve all deals related to the position #530218319
position_id = 530218319
position_deals = mt5.history_deals_get(position=position_id)
if position_deals is None:
    print(f"No deals with position #{position_id}")
    print("error code =", mt5.last_error())
elif len(position_deals) > 0:
    print(f"Deals with position id #{position_id}: {len(position_deals)}")
    # Display these deals as a table using pandas.DataFrame
    df = pd.DataFrame(list(position_deals), columns=position_deals[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(df)

# Shut down connection to the MetaTrader 5 terminal
mt5.shutdown()
```

**Result:**

```
MetaTrader5 package author:  MetaQuotes Software Corp.
MetaTrader5 package version:  5.0.29
 
history_deals_get(from_date, to_date, group="*GBP*") = 14
 
history_deals_get(from_date, to_date, group="*,!*EUR*,!*GBP*") = 7
   TradeDeal(ticket=506966741, order=0, time=1582202125, time_msc=1582202125419, type=2, entry=0, magic=0, position_id=0, reason=0, volume=0.0, pri ...
   TradeDeal(ticket=507962919, order=530218319, time=1582303777, time_msc=1582303777582, type=0, entry=0, magic=0, position_id=530218319, reason=0, ...
   TradeDeal(ticket=513149059, order=535548147, time=1583176242, time_msc=1583176242265, type=1, entry=1, magic=0, position_id=530218319, reason=0, ...
   TradeDeal(ticket=516943494, order=539349382, time=1583510003, time_msc=1583510003895, type=1, entry=0, magic=0, position_id=539349382, reason=0, ...
   TradeDeal(ticket=516943915, order=539349802, time=1583510025, time_msc=1583510025054, type=0, entry=0, magic=0, position_id=539349802, reason=0, ...
   TradeDeal(ticket=517139682, order=539557870, time=1583520201, time_msc=1583520201227, type=0, entry=1, magic=0, position_id=539349382, reason=0, ...
   TradeDeal(ticket=517139716, order=539557909, time=1583520202, time_msc=1583520202971, type=1, entry=1, magic=0, position_id=539349802, reason=0, ...
 
      ticket      order                time       time_msc  type  entry  magic  position_id  reason  volume    price  commission  swap     profit  fee  symbol comment external_id
0  506966741          0 2020-02-20 12:35:25  1582202125419     2      0      0            0       0    0.00  0.00000         0.0   0.0  100000.00  0.0                            
1  507962919  530218319 2020-02-21 16:49:37  1582303777582     0      0      0    530218319       0    0.01  0.97898         0.0   0.0       0.00  0.0  USDCHF                    
2  513149059  535548147 2020-03-02 19:10:42  1583176242265     1      1      0    530218319       0    0.01  0.95758         0.0   0.0     -22.35  0.0  USDCHF                    
3  516943494  539349382 2020-03-06 15:53:23  1583510003895     1      0      0    539349382       0    0.10  0.93475         0.0   0.0       0.00  0.0  USDCHF                    
4  516943915  539349802 2020-03-06 15:53:45  1583510025054     0      0      0    539349802       0    0.10  0.66336         0.0   0.0       0.00  0.0  AUDUSD                    
5  517139682  539557870 2020-03-06 18:43:21  1583520201227     0      1      0    539349382       0    0.10  0.93751         0.0   0.0     -29.44  0.0  USDCHF                    
6  517139716  539557909 2020-03-06 18:43:22  1583520202971     1      1      0    539349802       0    0.10  0.66327         0.0   0.0      -0.90  0.0  AUDUSD                    
 
Deals with position id #530218319: 2
      ticket      order                time       time_msc  type  entry  magic  position_id  reason  volume    price  commission  swap  profit  fee  symbol comment external_id
0  507962919  530218319 2020-02-21 16:49:37  1582303777582     0      0      0    530218319       0    0.01  0.97898         0.0   0.0    0.00  0.0  USDCHF                    
1  513149059  535548147 2020-03-02 19:10:42  1583176242265     1      1      0    530218319       0    0.01  0.95758         0.0   0.0  -22.35  0.0  USDCHF   
```