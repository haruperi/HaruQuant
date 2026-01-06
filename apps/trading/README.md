# Trading Module

A platform-agnostic trading framework inspired by MetaTrader 5's trading infrastructure, designed to work with any trading platform through adapter patterns.

## Overview

The `trading` module provides a unified interface for trading operations, account management, and market data access. It supports both **live trading** (via MT5) and **backtesting** through provider-based architecture, allowing you to write trading logic once and run it in multiple environments.

## Key Features

- **Platform-Agnostic Design**: Write trading logic once, run anywhere
- **Provider Pattern**: Easily switch between live trading and backtesting
- **MT5-Compatible API**: Familiar interface for MT5 developers
- **Type-Safe**: Full type hints and enum-based constants
- **Comprehensive**: Account, positions, orders, deals, symbols, and terminal info

## Architecture

The module uses a **Provider Pattern** where each component has:

- **Info Class**: High-level, platform-agnostic interface
- **Data Provider Protocol**: Interface that providers must implement
- **MT5 Provider**: Live trading implementation using MT5Client
- **Backtest Provider**: Simulation implementation for backtesting

```
┌─────────────────┐
│   Info Class    │  ← Your trading logic uses this
├─────────────────┤
│ Data Provider   │  ← Protocol interface
├─────────────────┤
│  MT5 Provider   │  ← Live trading
│Backtest Provider│  ← Backtesting
└─────────────────┘
```

---

## 1. Trade Component

Execute trading operations including market orders, pending orders, and position management.

### Classes

- **`Trade`** - Main trading class for executing operations
- **`MT5TradeProvider`** - Live trading implementation via MT5 (use with `Trade`)
- **`BacktestTradeProvider`** - Simulated trading for backtesting
- **`TradeProvider`** - Protocol interface for providers

**Notes**

- Use `Trade(MT5TradeProvider(mt5_client))` for live MT5 trading (legacy.
- `MT5TradeProvider.get_symbol_info` and `get_account_info` accept MT5 property names (e.g., `SYMBOL_VOLUME_MAX`, `MARGIN_MODE`).
- `CLOSE_BY` is supported via `TradeAction.CLOSE_BY` and `OrderType.CLOSE_BY` mapping.

### Enums

**TradeAction** - Trade action types

- `DEAL` - Place a trade (market execution)
- `PENDING` - Place a pending order
- `SLTP` - Modify stop loss and take profit
- `MODIFY` - Modify pending order parameters
- `REMOVE` - Delete pending order
- `CLOSE_BY` - Close position by an opposite one

**TradeRetcode** - Trade operation return codes

- Success: `DONE`, `DONE_PARTIAL`, `PLACED`
- Rejection: `REQUOTE`, `REJECT`, `CANCEL`
- Errors: `ERROR`, `TIMEOUT`, `INVALID`, `INVALID_VOLUME`, `INVALID_PRICE`, `INVALID_STOPS`, `TRADE_DISABLED`, `MARKET_CLOSED`, `NO_MONEY`, `PRICE_CHANGED`, `PRICE_OFF`, `INVALID_EXPIRATION`, `ORDER_CHANGED`, `TOO_MANY_REQUESTS`, `NO_CHANGES`, `SERVER_DISABLES_AT`, `CLIENT_DISABLES_AT`, `LOCKED`, `FROZEN`, `INVALID_FILL`, `CONNECTION`, `ONLY_REAL`, `LIMIT_ORDERS`, `LIMIT_VOLUME`, `INVALID_ORDER`, `POSITION_CLOSED`, `CLOSE_ORDER_EXIST`, `LIMIT_POSITIONS`

**LogLevel** - Logging levels

- `NO` - No logging
- `ERRORS` - Log only errors
- `ALL` - Log all operations

### Data Structures

**TradeRequest** - Trade request parameters

- `action: TradeAction` - Trade action
- `magic: int` - Magic number
- `order: int` - Order ticket
- `symbol: str` - Trading symbol
- `volume: float` - Volume in lots
- `price: float` - Execution price
- `stoplimit: float` - Stop limit price
- `sl: float` - Stop loss
- `tp: float` - Take profit
- `deviation: int` - Maximum price deviation
- `type: OrderType` - Order type
- `type_filling: OrderTypeFilling` - Filling type
- `type_time: OrderTypeTime` - Time type
- `expiration: datetime` - Expiration time
- `comment: str` - Order comment
- `position: int` - Position ticket
- `position_by: int` - Opposite position ticket

**TradeResult** - Trade execution result

- `retcode: TradeRetcode` - Return code
- `deal: int` - Deal ticket
- `order: int` - Order ticket
- `volume: float` - Executed volume
- `price: float` - Execution price
- `bid: float` - Bid price
- `ask: float` - Ask price
- `comment: str` - Result comment
- `request_id: int` - Request ID
- `retcode_external: int` - External return code

**TradeCheckResult** - Trade validation result

- `retcode: TradeRetcode` - Return code
- `balance: float` - Balance after trade
- `equity: float` - Equity after trade
- `profit: float` - Profit after trade
- `margin: float` - Margin after trade
- `margin_free: float` - Free margin after trade
- `margin_level: float` - Margin level after trade
- `comment: str` - Check comment

### Methods

#### Configuration

- `set_async_mode(mode: bool)` - Set asynchronous trading mode
- `set_expert_magic_number(magic: int)` - Set expert magic number
- `set_deviation_in_points(deviation: int)` - Set maximum price deviation
- `set_type_filling(filling: OrderTypeFilling)` - Set order filling type
- `set_log_level(log_level: LogLevel)` - Set logging level

#### Position Management

- `position_open(symbol, order_type, volume, price, sl=0.0, tp=0.0, comment="")` - Open position
- `position_modify(symbol=None, ticket=None, sl=0.0, tp=0.0)` - Modify position SL/TP
- `position_close(symbol=None, ticket=None, deviation=None)` - Close position
- `position_close_partial(symbol, volume, deviation=None)` - Partially close position
- `position_close_by(ticket, ticket_by)` - Close by opposite position
- `buy(volume, symbol=None, price=0.0, sl=0.0, tp=0.0, comment="")` - Quick buy
- `sell(volume, symbol=None, price=0.0, sl=0.0, tp=0.0, comment="")` - Quick sell

#### Order Management

- `order_open(symbol, order_type, volume, limit_price, price, sl=0.0, tp=0.0, type_time=GTC, expiration=None, comment="")` - Place pending order
- `order_modify(ticket, price, sl=0.0, tp=0.0, type_time=GTC, expiration=None)` - Modify order
- `order_delete(ticket)` - Delete pending order

#### Request Access

- `request_action()` - Get request action
- `request_magic()` - Get request magic number
- `request_order()` - Get request order ticket
- `request_position()` - Get request position ticket
- `request_symbol()` - Get request symbol
- `request_volume()` - Get request volume
- `request_price()` - Get request price
- `request_sl()` - Get request stop loss
- `request_tp()` - Get request take profit
- `request_type()` - Get request order type
- `request_type_filling()` - Get request filling type
- `request_comment()` - Get request comment

#### Result Access

- `result_retcode()` - Get return code
- `result_retcode_description()` - Get return code as string
- `result_deal()` - Get deal ticket
- `result_order()` - Get order ticket
- `result_volume()` - Get executed volume
- `result_price()` - Get execution price
- `result_bid()` - Get bid price at execution
- `result_ask()` - Get ask price at execution
- `result_comment()` - Get result comment
- `result_request_id()` - Get request ID
- `result_retcode_external()` - Get external return code

#### Check Result Access

- `check_result_retcode()` - Get check result return code
- `check_result_balance()` - Get check result balance
- `check_result_equity()` - Get check result equity
- `check_result_profit()` - Get check result profit
- `check_result_margin()` - Get check result margin
- `check_result_margin_free()` - Get check result free margin
- `check_result_margin_level()` - Get check result margin level
- `check_result_comment()` - Get check result comment

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import Trade, MT5TradeProvider, OrderType

# Initialize MT5 connection
client = MT5Client()
client.initialize()

# Create trade instance with MT5 provider
provider = MT5TradeProvider(client)
trade = Trade(provider)

# Configure settings
trade.set_expert_magic_number(12345)
trade.set_deviation_in_points(10)

# Open a position
if trade.position_open(
    symbol="EURUSD",
    order_type=OrderType.BUY,
    volume=0.1,
    price=1.0952,
    sl=1.0900,
    tp=1.1000,
    comment="My first trade"
):
    print(f"Position opened: #{trade.result_order()}")
    print(f"Deal: #{trade.result_deal()}")
    print(f"Price: {trade.result_price()}")
else:
    print(f"Failed: {trade.result_retcode_description()}")

# Modify position
if trade.position_modify(symbol="EURUSD", sl=1.0920, tp=1.1020):
    print("Position modified")

# Close the position
if trade.position_close(symbol="EURUSD"):
    print(f"Position closed at {trade.result_price()}")

# Cleanup
client.shutdown()
```

**Backtesting Example:**

```python
from apps.trading import Trade, BacktestTradeProvider, OrderType

# Create backtest provider
provider = BacktestTradeProvider(initial_balance=10000.0)
provider.set_symbol_price("EURUSD", bid=1.0950, ask=1.0952)

# Create trade instance (same API!)
trade = Trade(provider)
trade.set_expert_magic_number(12345)

# Execute trades
if trade.position_open(
    symbol="EURUSD",
    order_type=OrderType.BUY,
    volume=0.1,
    price=1.0952,
    sl=1.0900,
    tp=1.1000
):
    print(f"Backtest position opened: #{trade.result_order()}")
```

---

## 2. AccountInfo Component

Access account information and perform trading calculations.

### Classes

- **`AccountInfo`** - Account information interface
- **`MT5AccountProvider`** - Live account data from MT5
- **`BacktestAccountProvider`** - Simulated account for backtesting
- **`AccountDataProvider`** - Protocol interface for providers

### Enums

**AccountTradeMode** - Account trade mode

- `DEMO` - Demo account
- `CONTEST` - Contest account
- `REAL` - Real account
- `UNKNOWN` - Unknown mode

**AccountStopoutMode** - Stopout calculation mode

- `PERCENT` - Stopout level in percentage
- `MONEY` - Stopout level in money
- `UNKNOWN` - Unknown mode

**AccountMarginMode** - Margin calculation mode

- `RETAIL_NETTING` - Retail netting mode
- `EXCHANGE` - Exchange mode
- `RETAIL_HEDGING` - Retail hedging mode
- `UNKNOWN` - Unknown mode

### Methods

#### Account Properties

- `login()` - Account number/ID
- `name()` - Account holder name
- `server()` - Server name
- `company()` - Broker company name
- `currency()` - Account currency (USD, EUR, etc.)
- `leverage()` - Account leverage (e.g., 100 for 1:100)
- `trade_mode()` - Account trade mode (enum)
- `trade_mode_description()` - Trade mode as string
- `margin_mode()` - Margin calculation mode (enum)
- `margin_mode_description()` - Margin mode as string
- `stopout_mode()` - Stopout mode (enum)
- `stopout_mode_description()` - Stopout mode as string

#### Permissions & Limits

- `trade_allowed()` - Check if trading is allowed
- `trade_expert()` - Check if expert advisors are allowed
- `limit_orders()` - Maximum allowed limit orders (0 = unlimited)

#### Balance & Equity

- `balance()` - Account balance
- `credit()` - Account credit
- `profit()` - Current unrealized profit/loss
- `equity()` - Account equity (balance + credit + profit)
- `margin()` - Used margin from open positions
- `free_margin()` - Free margin available for trading
- `margin_level()` - Margin level percentage (equity/margin * 100)
- `margin_call()` - Margin call level
- `margin_stopout()` - Margin stopout level

#### Trading Calculations

- `margin_check(symbol, order_type, volume, price)` - Calculate required margin
- `free_margin_check(symbol, order_type, volume, price, stop_loss=0.0)` - Check if sufficient margin
- `order_profit_check(symbol, order_type, volume, price_open, price_close)` - Calculate potential profit
- `max_lot_check(symbol, order_type, price, percent)` - Calculate maximum lot size

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import AccountInfo, MT5AccountProvider, OrderType

client = MT5Client()
client.initialize()

# Create account info with MT5 provider
provider = MT5AccountProvider(client)
account = AccountInfo(provider)

# Display account information
print(f"Login: {account.login()}")
print(f"Balance: {account.balance():.2f} {account.currency()}")
print(f"Equity: {account.equity():.2f}")
print(f"Free Margin: {account.free_margin():.2f}")
print(f"Margin Level: {account.margin_level():.2f}%")
print(f"Leverage: 1:{account.leverage()}")
print(f"Mode: {account.trade_mode_description()}")

# Perform trading checks
margin_required = account.margin_check("EURUSD", OrderType.BUY, 1.0, 1.1000)
print(f"Margin required for 1 lot: {margin_required:.2f}")

profit_estimate = account.order_profit_check(
    "EURUSD", OrderType.BUY, 1.0, 1.1000, 1.1050
)
print(f"Estimated profit (50 pips): {profit_estimate:.2f}")

has_margin = account.free_margin_check("EURUSD", OrderType.BUY, 1.0, 1.1000)
print(f"Sufficient margin: {'Yes' if has_margin else 'No'}")

max_lots = account.max_lot_check("EURUSD", OrderType.BUY, 1.1000, 50)
print(f"Max lots (50% equity): {max_lots}")

client.shutdown()
```

**Backtest Account Matching MT5:**

```python
from apps.mt5 import MT5Client
from apps.trading import AccountInfo, BacktestAccountProvider

client = MT5Client()
client.initialize()

# Create backtest account matching MT5 settings
provider = BacktestAccountProvider.from_mt5_account(
    client,
    initial_balance=10000,  # Optional override
    symbols=["EURUSD", "GBPUSD", "XAUUSD"]
)

account = AccountInfo(provider)
# Now you have a backtest account with the same leverage,
# margin mode, and symbol specs as your MT5 account!

print(f"Backtest account: {account.balance():.2f} {account.currency()}")
print(f"Leverage: 1:{account.leverage()}")
print(f"Margin mode: {account.margin_mode_description()}")

client.shutdown()
```

---

## 3. PositionInfo Component

Access and manage open positions.

### Classes

- **`PositionInfo`** - Position information interface
- **`MT5PositionProvider`** - Live positions from MT5
- **`BacktestPositionProvider`** - Simulated positions
- **`PositionDataProvider`** - Protocol interface for providers

### Enums

**PositionType** - Position direction

- `BUY` - Buy position (long)
- `SELL` - Sell position (short)
- `UNKNOWN` - Unknown type

### Methods

#### Position Selection

- `select(symbol)` - Select position by symbol (netting mode)
- `select_by_magic(symbol, magic)` - Select by symbol and magic number
- `select_by_ticket(ticket)` - Select by ticket (hedging mode)
- `select_by_index(index)` - Select by index
- `total()` - Get total number of open positions

#### Position Properties (Integer)

- `ticket()` - Position ticket/ID
- `time()` - Position open time (datetime)
- `time_msc()` - Position open time in milliseconds
- `time_update()` - Position last update time (datetime)
- `time_update_msc()` - Position last update time in milliseconds
- `type()` - Position type (PositionType.BUY or PositionType.SELL)
- `magic()` - Magic number
- `identifier()` - Position identifier

#### Position Properties (Double)

- `volume()` - Position volume in lots
- `price_open()` - Position open price
- `price_current()` - Current market price
- `stop_loss()` - Stop loss level
- `take_profit()` - Take profit level
- `profit()` - Current profit/loss
- `swap()` - Accumulated swap
- `commission()` - Commission charged

#### Position Properties (String)

- `symbol()` - Trading symbol
- `comment()` - Position comment
- `external_id()` - External position ID

#### Helper Methods

- `type_description()` - Position type as string ("Buy" or "Sell")
- `format_position()` - Format position as readable string
- `select_history_by_position(position_id)` - Select historical orders for position

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import PositionInfo, MT5PositionProvider

client = MT5Client()
client.initialize()

provider = MT5PositionProvider(client)
position = PositionInfo(provider)

# Iterate through all open positions
print(f"Total positions: {position.total()}")
for i in range(position.total()):
    if position.select_by_index(i):
        print(f"\nPosition #{position.ticket()}")
        print(f"  Symbol: {position.symbol()}")
        print(f"  Type: {position.type_description()}")
        print(f"  Volume: {position.volume()}")
        print(f"  Open Price: {position.price_open()}")
        print(f"  Current Price: {position.price_current()}")
        print(f"  Profit: {position.profit():.2f}")
        print(f"  Swap: {position.swap():.2f}")
        print(f"  SL: {position.stop_loss()}")
        print(f"  TP: {position.take_profit()}")
        print(f"  Magic: {position.magic()}")

# Select specific position
if position.select("EURUSD"):
    print(f"\nEURUSD position: {position.format_position()}")

client.shutdown()
```

---

## 4. OrderInfo Component

Access active (pending) orders.

### Classes

- **`OrderInfo`** - Order information interface
- **`MT5OrderProvider`** - Live orders from MT5
- **`BacktestOrderProvider`** - Simulated orders
- **`OrderDataProvider`** - Protocol interface for providers

### Enums

**OrderType** - Order types

- `BUY` - Market buy
- `SELL` - Market sell
- `BUY_LIMIT` - Buy limit order
- `SELL_LIMIT` - Sell limit order
- `BUY_STOP` - Buy stop order
- `SELL_STOP` - Sell stop order
- `BUY_STOP_LIMIT` - Buy stop limit order
- `SELL_STOP_LIMIT` - Sell stop limit order
- `CLOSE_BY` - Close by opposite position
- `UNKNOWN` - Unknown type

**OrderState** - Order states

- `STARTED` - Order started
- `PLACED` - Order placed
- `CANCELED` - Order canceled
- `PARTIAL` - Order partially filled
- `FILLED` - Order filled
- `REJECTED` - Order rejected
- `EXPIRED` - Order expired
- `REQUEST_ADD` - Request to add order
- `REQUEST_MODIFY` - Request to modify order
- `REQUEST_CANCEL` - Request to cancel order
- `UNKNOWN` - Unknown state

**OrderTypeFilling** - Order filling types

- `FOK` - Fill or Kill
- `IOC` - Immediate or Cancel
- `RETURN` - Return (partial fills allowed)
- `UNKNOWN` - Unknown filling type

**OrderTypeTime** - Order expiration types

- `GTC` - Good Till Canceled
- `DAY` - Good for day
- `SPECIFIED` - Good till specified time
- `SPECIFIED_DAY` - Good till specified day
- `UNKNOWN` - Unknown time type

### Methods

#### Order Selection

- `select(ticket)` - Select order by ticket
- `select_by_index(index)` - Select order by index
- `total()` - Get total number of active orders

#### Order Properties (Integer)

- `ticket()` - Order ticket/ID
- `time_setup()` - Order setup time (datetime)
- `time_setup_msc()` - Order setup time in milliseconds
- `time_done()` - Order done time (datetime)
- `time_done_msc()` - Order done time in milliseconds
- `time_expiration()` - Order expiration time (datetime)
- `type()` - Order type (OrderType enum)
- `state()` - Order state (OrderState enum)
- `magic()` - Magic number
- `position_id()` - Position ID
- `position_by_id()` - Position by ID (for close by orders)

#### Order Properties (Double)

- `volume_initial()` - Initial order volume
- `volume_current()` - Current order volume
- `price_open()` - Order price
- `price_current()` - Current market price
- `price_stoplimit()` - Stop limit price
- `stop_loss()` - Stop loss level
- `take_profit()` - Take profit level

#### Order Properties (String)

- `symbol()` - Trading symbol
- `comment()` - Order comment
- `external_id()` - External order ID

#### Order Properties (Enums)

- `type_filling()` - Order filling type (OrderTypeFilling enum)
- `type_time()` - Order time type (OrderTypeTime enum)

#### Helper Methods

- `type_description()` - Order type as string
- `state_description()` - Order state as string
- `type_filling_description()` - Filling type as string
- `type_time_description()` - Time type as string
- `format_order()` - Format order as readable string

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import OrderInfo, MT5OrderProvider

client = MT5Client()
client.initialize()

provider = MT5OrderProvider(client)
order = OrderInfo(provider)

# Iterate through all pending orders
print(f"Total pending orders: {order.total()}")
for i in range(order.total()):
    if order.select_by_index(i):
        print(f"\nOrder #{order.ticket()}")
        print(f"  Symbol: {order.symbol()}")
        print(f"  Type: {order.type_description()}")
        print(f"  State: {order.state_description()}")
        print(f"  Volume: {order.volume_current()}/{order.volume_initial()}")
        print(f"  Price: {order.price_open()}")
        print(f"  SL: {order.stop_loss()}")
        print(f"  TP: {order.take_profit()}")
        print(f"  Time: {order.time_setup()}")
        print(f"  Expiration: {order.time_expiration()}")

client.shutdown()
```

---

## 5. HistoryOrderInfo Component

Access historical (completed) orders.

### Classes

- **`HistoryOrderInfo`** - Historical order interface
- **`MT5HistoryOrderProvider`** - Order history from MT5
- **`BacktestHistoryOrderProvider`** - Simulated order history
- **`HistoryOrderDataProvider`** - Protocol interface for providers

### Enums

*(Same as OrderInfo component - see above)*

### Methods

#### Order Selection

- `select_by_index(index)` - Select historical order by index
- `total_orders()` - Get total number of historical orders

#### Order Properties

*(Same as OrderInfo class - see OrderInfo component above)*

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import HistoryOrderInfo, MT5HistoryOrderProvider
from datetime import datetime, timedelta

client = MT5Client()
client.initialize()

# Get orders from last 30 days
date_from = datetime.now() - timedelta(days=30)
provider = MT5HistoryOrderProvider(client, date_from=date_from)
order = HistoryOrderInfo(provider)

print(f"Total historical orders: {order.total_orders()}")
for i in range(order.total_orders()):
    if order.select_by_index(i):
        print(f"\nOrder #{order.ticket()}")
        print(f"  Symbol: {order.symbol()}")
        print(f"  Type: {order.type_description()}")
        print(f"  State: {order.state_description()}")
        print(f"  Volume: {order.volume_initial()}")
        print(f"  Price: {order.price_open()}")
        print(f"  Setup: {order.time_setup()}")
        print(f"  Done: {order.time_done()}")

client.shutdown()
```

---

## 6. DealInfo Component

Access executed deals (trade transactions).

### Classes

- **`DealInfo`** - Deal information interface
- **`MT5DealProvider`** - Deal history from MT5
- **`BacktestDealProvider`** - Simulated deals
- **`DealDataProvider`** - Protocol interface for providers

### Enums

**DealType** - Deal types

- `BUY` - Buy deal
- `SELL` - Sell deal
- `BALANCE` - Balance operation
- `CREDIT` - Credit operation
- `CHARGE` - Additional charge
- `CORRECTION` - Correction
- `BONUS` - Bonus
- `COMMISSION` - Commission
- `COMMISSION_DAILY` - Daily commission
- `COMMISSION_MONTHLY` - Monthly commission
- `COMMISSION_AGENT_DAILY` - Daily agent commission
- `COMMISSION_AGENT_MONTHLY` - Monthly agent commission
- `INTEREST` - Interest rate
- `BUY_CANCELED` - Canceled buy
- `SELL_CANCELED` - Canceled sell
- `UNKNOWN` - Unknown type

**DealEntry** - Deal entry direction

- `IN` - Entry into position
- `OUT` - Exit from position
- `INOUT` - Reversal (in and out simultaneously)
- `OUT_BY` - Close by opposite position
- `STATE` - State record (balance operations)
- `UNKNOWN` - Unknown entry

### Methods

#### Deal Selection

- `select_by_index(index)` - Select deal by index
- `total_deals()` - Get total number of deals

#### Deal Properties (Integer)

- `ticket()` - Deal ticket/ID
- `order()` - Order ticket that created this deal
- `time()` - Deal execution time (datetime)
- `time_msc()` - Deal execution time in milliseconds
- `type()` - Deal type (DealType enum)
- `entry()` - Deal entry direction (DealEntry enum)
- `magic()` - Magic number
- `position_id()` - Position ID

#### Deal Properties (Double)

- `volume()` - Deal volume in lots
- `price()` - Deal execution price
- `commission()` - Commission charged
- `swap()` - Swap charged/credited
- `profit()` - Deal profit/loss
- `fee()` - Additional fee (backtest only)

#### Deal Properties (String)

- `symbol()` - Trading symbol
- `comment()` - Deal comment
- `external_id()` - External deal ID

#### Helper Methods

- `type_description()` - Deal type as string
- `entry_description()` - Deal entry as string
- `format_deal()` - Format deal as readable string

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import DealInfo, MT5DealProvider, DealType
from datetime import datetime, timedelta

client = MT5Client()
client.initialize()

# Get deals from last 30 days
date_from = datetime.now() - timedelta(days=30)
provider = MT5DealProvider(client, date_from=date_from)
deal = DealInfo(provider)

total_profit = 0.0
print(f"Total deals: {deal.total_deals()}")

for i in range(deal.total_deals()):
    if deal.select_by_index(i):
        # Only process trade deals
        if deal.deal_type() in [DealType.BUY, DealType.SELL]:
            total_profit += deal.profit()
            print(f"\n{deal.format_deal()}")
            print(f"  Entry: {deal.entry_description()}")
            print(f"  Profit: {deal.profit():.2f}")
            print(f"  Commission: {deal.commission():.2f}")
            print(f"  Swap: {deal.swap():.2f}")
            print(f"  Time: {deal.time()}")

print(f"\nTotal profit from deals: {total_profit:.2f}")

client.shutdown()
```

---

## 7. SymbolInfo Component

Access symbol (instrument) specifications and market data.

### Classes

- **`SymbolInfo`** - Symbol information interface
- **`MT5SymbolProvider`** - Symbol data from MT5
- **`BacktestSymbolProvider`** - Simulated symbol data
- **`SymbolDataProvider`** - Protocol interface for providers

### Enums

**SymbolTradeExecution** - Trade execution modes

- `REQUEST` - Execution by request
- `INSTANT` - Instant execution
- `MARKET` - Market execution
- `EXCHANGE` - Exchange execution
- `UNKNOWN` - Unknown mode

**SymbolCalcMode** - Calculation modes

- `FOREX` - Forex calculation
- `CFD` - CFD calculation
- `FUTURES` - Futures calculation
- `CFD_INDEX` - CFD index calculation
- `CFD_LEVERAGE` - CFD leverage calculation
- `EXCH_STOCKS` - Exchange stocks
- `EXCH_FUTURES` - Exchange futures
- `EXCH_FUTURES_FORTS` - Exchange futures FORTS
- `UNKNOWN` - Unknown mode

**SymbolTradeMode** - Trading modes

- `DISABLED` - Trading disabled
- `LONG_ONLY` - Long positions only
- `SHORT_ONLY` - Short positions only
- `CLOSE_ONLY` - Close only
- `FULL` - Full trading
- `UNKNOWN` - Unknown mode

**SymbolSwapMode** - Swap calculation modes

- `DISABLED` - Swaps disabled
- `POINTS` - Swaps in points
- `CURRENCY_SYMBOL` - Swaps in symbol currency
- `CURRENCY_MARGIN` - Swaps in margin currency
- `CURRENCY_DEPOSIT` - Swaps in deposit currency
- `INTEREST_CURRENT` - Interest on current price
- `INTEREST_OPEN` - Interest on open price
- `REOPEN_CURRENT` - Reopen by current price
- `REOPEN_BID` - Reopen by bid price
- `UNKNOWN` - Unknown mode

### Methods

#### Symbol Selection

- `name(symbol=None)` - Get or set symbol name
- `select(select=True)` - Select/deselect symbol in MarketWatch
- `is_synchronized()` - Check if symbol data is synchronized
- `refresh()` - Refresh symbol data
- `refresh_rates()` - Refresh tick data

#### Price Information

- `bid()` - Current bid price
- `ask()` - Current ask price
- `last()` - Last deal price
- `bid_high()` - Highest bid of the day
- `bid_low()` - Lowest bid of the day
- `ask_high()` - Highest ask of the day
- `ask_low()` - Lowest ask of the day
- `last_high()` - Highest last price of the day
- `last_low()` - Lowest last price of the day
- `volume_high()` - Highest volume of the day
- `volume_low()` - Lowest volume of the day

#### Spread & Trading Costs

- `spread()` - Current spread in points
- `spread_float()` - Check if spread is floating
- `tick_value()` - Tick value in account currency
- `tick_value_profit()` - Tick value for profit calculation
- `tick_value_loss()` - Tick value for loss calculation
- `tick_size()` - Tick size in price units
- `trade_tick_value()` - Trade tick value
- `trade_tick_size()` - Trade tick size

#### Symbol Specifications

- `point()` - Point size
- `digits()` - Number of decimal places
- `trade_contract_size()` - Contract size
- `trade_mode()` - Trading mode (SymbolTradeMode enum)
- `trade_execution()` - Execution mode (SymbolTradeExecution enum)
- `trade_calc_mode()` - Calculation mode (SymbolCalcMode enum)
- `trade_stops_level()` - Stops level in points
- `trade_freeze_level()` - Freeze level in points

#### Volume Limits

- `volume_min()` - Minimum volume
- `volume_max()` - Maximum volume
- `volume_step()` - Volume step
- `volume_limit()` - Maximum total volume

#### Currency Information

- `currency_base()` - Base currency
- `currency_profit()` - Profit currency
- `currency_margin()` - Margin currency

#### Swap Information

- `swap_mode()` - Swap calculation mode (SymbolSwapMode enum)
- `swap_long()` - Swap for long positions
- `swap_short()` - Swap for short positions
- `swap_rollover3days()` - Day of week for triple swap

#### Session Information

- `session_deals()` - Number of deals in current session
- `session_buy_orders()` - Number of buy orders in session
- `session_sell_orders()` - Number of sell orders in session
- `session_turnover()` - Session turnover
- `session_interest()` - Session interest
- `session_price_limit_min()` - Session minimum price
- `session_price_limit_max()` - Session maximum price

#### Helper Methods

- `normalize_price(price)` - Normalize price to symbol's digits
- `info_tick(symbol)` - Get tick information
- `select_by_name(symbol)` - Select symbol by name

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import SymbolInfo, MT5SymbolProvider

client = MT5Client()
client.initialize()

provider = MT5SymbolProvider(client, "EURUSD")
symbol = SymbolInfo(provider)

# Display symbol information
print(f"Symbol: {symbol.name()}")
print(f"Bid: {symbol.bid()}")
print(f"Ask: {symbol.ask()}")
print(f"Spread: {symbol.spread()} points")
print(f"Point: {symbol.point()}")
print(f"Digits: {symbol.digits()}")
print(f"Contract Size: {symbol.trade_contract_size()}")
print(f"Volume Min: {symbol.volume_min()}")
print(f"Volume Max: {symbol.volume_max()}")
print(f"Volume Step: {symbol.volume_step()}")
print(f"Stops Level: {symbol.trade_stops_level()}")
print(f"Freeze Level: {symbol.trade_freeze_level()}")
print(f"Tick Value: {symbol.tick_value()}")
print(f"Tick Size: {symbol.tick_size()}")
print(f"Swap Long: {symbol.swap_long()}")
print(f"Swap Short: {symbol.swap_short()}")

# Normalize price
price = 1.095678
normalized = symbol.normalize_price(price)
print(f"Normalized price: {normalized}")

client.shutdown()
```

---

## 8. TerminalInfo Component

Access trading terminal information.

### Classes

- **`TerminalInfo`** - Terminal information interface
- **`MT5TerminalProvider`** - Terminal data from MT5
- **`TerminalDataProvider`** - Protocol interface for providers

### Methods

#### Terminal Properties

- `build()` - Terminal build number
- `name()` - Terminal name
- `company()` - Company name
- `language()` - Terminal language
- `path()` - Terminal installation path
- `data_path()` - Terminal data folder path
- `common_data_path()` - Common data folder path

#### Connection Status

- `connected()` - Check if connected to trade server
- `trade_allowed()` - Check if trading is allowed
- `email_enabled()` - Check if email sending is enabled
- `ftp_enabled()` - Check if FTP is enabled
- `dlls_allowed()` - Check if DLLs are allowed

#### System Resources

- `cpu_cores()` - Number of CPU cores
- `memory_physical()` - Physical memory in MB
- `memory_total()` - Total memory in MB
- `memory_available()` - Available memory in MB
- `memory_used()` - Used memory in MB
- `disk_space()` - Free disk space in MB

#### Terminal Capabilities

- `x64()` - Check if terminal is 64-bit
- `opencl_support()` - OpenCL support level
- `max_bars()` - Maximum bars in chart
- `code_page()` - Terminal code page

#### Helper Methods

- `info_integer(property_id)` - Get integer property by ID
- `info_string(property_id)` - Get string property by ID

### Example

```python
from apps.mt5 import MT5Client
from apps.trading import TerminalInfo, MT5TerminalProvider

client = MT5Client()
client.initialize()

provider = MT5TerminalProvider(client)
terminal = TerminalInfo(provider)

# Display terminal information
print(f"Terminal: {terminal.name()}")
print(f"Company: {terminal.company()}")
print(f"Build: {terminal.build()}")
print(f"Language: {terminal.language()}")
print(f"Path: {terminal.path()}")
print(f"Connected: {terminal.connected()}")
print(f"Trade Allowed: {terminal.trade_allowed()}")
print(f"CPU Cores: {terminal.cpu_cores()}")
print(f"Memory Total: {terminal.memory_total()} MB")
print(f"Memory Available: {terminal.memory_available()} MB")
print(f"Memory Used: {terminal.memory_used()} MB")
print(f"Disk Space: {terminal.disk_space()} MB")
print(f"64-bit: {terminal.x64()}")
print(f"Max Bars: {terminal.max_bars()}")

client.shutdown()
```

---

## Common Patterns

### Switching Between Live and Backtest

```python
# Define your trading logic once
def execute_strategy(trade):
    if trade.position_open(
        symbol="EURUSD",
        order_type=OrderType.BUY,
        volume=0.1,
        price=1.0952,
        sl=1.0900,
        tp=1.1000
    ):
        print("Position opened")

# Use with live trading
from apps.trading import MT5TradeProvider
provider = MT5TradeProvider(client)
trade = Trade(provider)
execute_strategy(trade)

# Use with backtesting (same logic!)
from apps.trading import BacktestTradeProvider
provider = BacktestTradeProvider(initial_balance=10000)
provider.set_symbol_price("EURUSD", bid=1.0950, ask=1.0952)
trade = Trade(provider)
execute_strategy(trade)
```

### Iterating Through Positions

```python
from apps.trading import PositionInfo, MT5PositionProvider

provider = MT5PositionProvider(client)
position = PositionInfo(provider)

# Iterate through all open positions
for i in range(position.total()):
    if position.select_by_index(i):
        print(f"Position #{position.ticket()}")
        print(f"  Symbol: {position.symbol()}")
        print(f"  Type: {position.type_description()}")
        print(f"  Volume: {position.volume()}")
        print(f"  Profit: {position.profit():.2f}")
```

### Analyzing Deal History

```python
from apps.trading import DealInfo, MT5DealProvider, DealType
from datetime import datetime, timedelta

# Get deals from last 30 days
date_from = datetime.now() - timedelta(days=30)
provider = MT5DealProvider(client, date_from=date_from)
deal = DealInfo(provider)

total_profit = 0.0
for i in range(deal.total_deals()):
    if deal.select_by_index(i):
        if deal.deal_type() in [DealType.BUY, DealType.SELL]:
            total_profit += deal.profit()
            print(f"{deal.format_deal()} - Profit: {deal.profit():.2f}")

print(f"Total profit: {total_profit:.2f}")
```

---

## Best Practices

1. **Always use providers**: Never directly instantiate Info classes without a provider
2. **Handle errors**: Check return codes and handle failures gracefully
3. **Use magic numbers**: Identify your trades with unique magic numbers
4. **Test in backtest first**: Validate strategies in backtest before live trading
5. **Set stop losses**: Always use stop losses to manage risk
6. **Check margin**: Verify sufficient margin before opening positions
7. **Clean up connections**: Always call `client.shutdown()` when done

## Integration with Backtest Engine

The trading module integrates seamlessly with the backtest engine:

```python
from apps.strategy import BaseStrategy
from apps.trading import OrderType

class MyStrategy(BaseStrategy):
    def on_tick(self, symbol, bid, ask, timestamp):
        # Use self.trade (automatically configured with backtest provider)
        if self.should_buy():
            self.trade.position_open(
                symbol=symbol,
                order_type=OrderType.BUY,
                volume=0.1,
                price=ask,
                sl=ask - 0.0050,
                tp=ask + 0.0100
            )
```

## Error Handling

```python
from apps.trading import Trade, TradeRetcode

if trade.position_open(...):
    # Success
    print(f"Order: #{trade.result_order()}")
else:
    # Handle specific errors
    retcode = trade.result_retcode()

    if retcode == TradeRetcode.NO_MONEY:
        print("Insufficient funds")
    elif retcode == TradeRetcode.INVALID_STOPS:
        print("Invalid stop loss or take profit")
    elif retcode == TradeRetcode.MARKET_CLOSED:
        print("Market is closed")
    else:
        print(f"Error: {trade.result_retcode_description()}")
```

## All Examples

The `examples/trading/` directory contains comprehensive examples for each component:

- `trade_example.py` - Trading operations (open, modify, close)
- `account_info_example.py` - Account information and calculations
- `position_info_example.py` - Position management
- `order_info_example.py` - Active order management
- `history_order_info_example.py` - Historical order analysis
- `deal_info_example.py` - Deal history and analysis
- `symbol_info_example.py` - Symbol specifications and market data
- `terminal_info_example.py` - Terminal information

Run any example:

```bash
python examples/trading/trade_example.py
```

## License

Copyright 2025, HaruQuant

## See Also

- `apps/mt5/` - MT5 client implementation
- `apps/strategy/` - Strategy framework
- `examples/trading/` - Comprehensive examples
