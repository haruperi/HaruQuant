# Trade Module

MT5 Trading Classes aligned with the MQL5 Standard Library.

## Overview

The `apps.trade` module provides Python implementations of the MQL5 Standard Library trade classes, enabling seamless interaction with MetaTrader 5 (MT5) for live and simulated trading. All classes mirror their MQL5 counterparts, providing familiar interfaces for developers transitioning from MQL5 to Python.

**Key Features:**
- Complete MT5 Standard Library trade class implementations
- Support for both live trading and simulation
- Type-safe wrappers around MT5 API calls
- Automatic handling of MT5 constants and enums
- Comprehensive property access with caching
- Human-readable descriptions for all enum values

**Reference:** [MQL5 Standard Library Trade Classes](https://www.mql5.com/en/docs/standardlibrary/tradeclasses)

## Module Structure

```
apps/trade/
├── __init__.py                  # Module exports and lazy loading
├── account_info.py              # Account properties and balance info
├── deal_info.py                 # Historical deal/transaction data
├── history_order_info.py        # Historical order data
├── order_info.py                # Active pending order info
├── position_info.py             # Open position information
├── symbol_info.py               # Trading symbol specifications
├── terminal_info.py             # MT5 terminal/platform info
└── trade.py                     # Trade execution operations
```

## Installation

```python
from apps.trade import (
    AccountInfo,
    DealInfo,
    HistoryOrderInfo,
    OrderInfo,
    PositionInfo,
    SymbolInfo,
    TerminalInfo,
    Trade,
    TradeSimulator,  # Lazy-loaded from apps.simulation
)
```

## Components

### 1. AccountInfo (`account_info.py`)

**Purpose:** Access and monitor MT5 account properties including balance, equity, margin, permissions, and trading capabilities.

**Class:** `AccountInfo`

#### Methods

##### Account Identification
```python
def Login() -> int
```
Get the account number.

```python
def Name() -> str
```
Get the client name.

```python
def Server() -> str
```
Get the trade server name.

```python
def Currency() -> str
```
Get the deposit currency name (e.g., "USD", "EUR").

```python
def Company() -> str
```
Get the company name that serves the account.

##### Account Mode
```python
def TradeMode() -> int
```
Get the trade mode (Demo, Contest, or Real).

```python
def TradeModeDescription() -> str
```
Get the trade mode as a human-readable string.

```python
def Leverage() -> int
```
Get the amount of leverage (e.g., 100 for 1:100).

##### Permissions
```python
def TradeAllowed() -> bool
```
Check if trading is allowed on this account.

```python
def TradeExpert() -> bool
```
Check if automated trading (Expert Advisors) is allowed.

```python
def LimitOrders() -> int
```
Get the maximum number of allowed pending orders (0 = unlimited).

##### Balance and Equity
```python
def Balance() -> float
```
Get the account balance.

```python
def Credit() -> float
```
Get the credit amount provided by broker.

```python
def Profit() -> float
```
Get the current floating profit/loss from open positions.

```python
def Equity() -> float
```
Get the account equity (Balance + Profit).

##### Margin Information
```python
def Margin() -> float
```
Get the amount of margin currently used by open positions.

```python
def FreeMargin() -> float
```
Get the amount of free margin available for trading.

```python
def MarginLevel() -> float
```
Get the margin level as a percentage (Equity / Margin * 100).

```python
def MarginCall() -> float
```
Get the margin level at which a margin call is triggered.

```python
def MarginStopOut() -> float
```
Get the margin level at which positions are automatically closed.

```python
def MarginMode() -> int
```
Get the margin calculation mode.

```python
def MarginModeDescription() -> str
```
Get the margin calculation mode as a string ("Retail netting", "Exchange", "Retail hedging").

```python
def StopoutMode() -> int
```
Get the stop out mode.

```python
def StopoutModeDescription() -> str
```
Get the stop out mode as a string ("Percent" or "Money").

##### Trading Checks
```python
def OrderProfitCheck(symbol: str, order_type: int, volume: float,
                     price_open: float, price_close: float) -> float
```
Calculate the estimated profit for a trade based on entry and exit prices.

```python
def MarginCheck(symbol: str, order_type: int, volume: float, price: float) -> float
```
Calculate the margin required to open a position.

```python
def FreeMarginCheck(symbol: str, order_type: int, volume: float, price: float) -> float
```
Calculate the free margin that would remain after opening a position.

```python
def MaxLotCheck(symbol: str, order_type: int, price: float, percent: float) -> float
```
Calculate the maximum lot size that can be traded with a given percentage of equity.

##### Generic Property Access
```python
def InfoInteger(prop: Any) -> Optional[int]
def InfoDouble(prop: Any) -> Optional[float]
def InfoString(prop: Any) -> Optional[str]
```
Get account property values by MT5 property constant or string key.

**Usage Example:**

```python
from apps.trade import AccountInfo
from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()

# Create account info instance
account = AccountInfo()

# Display account information
print(f"Account: {account.Login()}")
print(f"Balance: {account.Balance():.2f} {account.Currency()}")
print(f"Equity: {account.Equity():.2f} {account.Currency()}")
print(f"Free Margin: {account.FreeMargin():.2f} {account.Currency()}")
print(f"Leverage: 1:{account.Leverage()}")
print(f"Mode: {account.TradeModeDescription()}")

# Check if can open trade
symbol = "EURUSD"
volume = 1.0
price = 1.1000

margin_required = account.MarginCheck(symbol, mt5.ORDER_TYPE_BUY, volume, price)
print(f"Margin required: {margin_required:.2f}")

if account.FreeMargin() >= margin_required:
    print("Sufficient margin available")
else:
    print("Insufficient margin")

# Calculate max lot size with 50% of equity
max_lots = account.MaxLotCheck(symbol, mt5.ORDER_TYPE_BUY, price, 50.0)
print(f"Max lots (50% equity): {max_lots:.2f}")
```

**Full Example:** [tests/usage/trade/account_info_example.py](../../tests/usage/trade/account_info_example.py)

---

### 2. SymbolInfo (`symbol_info.py`)

**Purpose:** Access trading symbol properties including pricing, spread, lot sizes, margins, swaps, and trading specifications.

**Class:** `SymbolInfo`

#### Methods

##### Symbol Identification
```python
def Name(name: Optional[str] = None) -> Any
```
Get or set the symbol name. If `name` is provided, sets the symbol; otherwise returns current symbol.

```python
def Description() -> str
```
Get the symbol description.

```python
def Path() -> str
```
Get the path in the symbols tree.

```python
def CurrencyBase() -> str
```
Get the base currency name (e.g., "EUR" in EURUSD).

```python
def CurrencyProfit() -> str
```
Get the profit currency name.

```python
def CurrencyMargin() -> str
```
Get the margin currency name.

```python
def Bank() -> str
```
Get the name of current quote source.

##### Symbol Control
```python
def Refresh() -> bool
```
Refresh the symbol data from MT5.

```python
def RefreshRates() -> bool
```
Refresh the symbol quotes (tick data).

```python
def Select(select: Optional[bool] = None) -> bool
```
Get or set whether the symbol is shown in Market Watch.

```python
def IsSynchronized() -> bool
```
Check if symbol is synchronized with the server.

##### Pricing and Tick Data
```python
def Bid() -> float
```
Get the current Bid price.

```python
def BidHigh() -> float
```
Get the maximum Bid price for the current day.

```python
def BidLow() -> float
```
Get the minimum Bid price for the current day.

```python
def Ask() -> float
```
Get the current Ask price.

```python
def AskHigh() -> float
```
Get the maximum Ask price for the current day.

```python
def AskLow() -> float
```
Get the minimum Ask price for the current day.

```python
def Last() -> float
```
Get the last trade price.

```python
def LastHigh() -> float
```
Get the maximum Last price for the current day.

```python
def LastLow() -> float
```
Get the minimum Last price for the current day.

```python
def Time() -> datetime
```
Get the time of the last quote.

```python
def Spread() -> int
```
Get the spread in points.

```python
def SpreadFloat() -> bool
```
Check if the spread is floating.

```python
def TicksBookDepth() -> int
```
Get the depth of market (DOM) levels available.

##### Volume Information
```python
def Volume() -> float
```
Get the volume of the last deal.

```python
def VolumeHigh() -> int
```
Get the maximum volume for the current day.

```python
def VolumeLow() -> int
```
Get the minimum volume for the current day.

##### Trade Settings
```python
def TradeCalcMode() -> int
```
Get the contract calculation mode (Forex, Futures, CFD, etc.).

```python
def TradeCalcModeDescription() -> str
```
Get the contract calculation mode as a string.

```python
def TradeMode() -> int
```
Get the trade execution mode (Disabled, Long only, Short only, Close only, Full access).

```python
def TradeModeDescription() -> str
```
Get the trade execution mode as a string.

```python
def TradeExecution() -> int
```
Get the trade execution mode (Request, Instant, Market, Exchange).

```python
def TradeExecutionDescription() -> str
```
Get the trade execution mode as a string.

```python
def TradeTimeFlags() -> int
```
Get the flags of allowed order expiration modes.

```python
def TradeFillFlags() -> int
```
Get the flags of allowed order filling modes.

##### Margins and Swaps
```python
def MarginInitial() -> float
```
Get the initial margin requirement.

```python
def MarginMaintenance() -> float
```
Get the maintenance margin requirement.

```python
def MarginLong() -> float
```
Get the margin rate for long positions.

```python
def MarginShort() -> float
```
Get the margin rate for short positions.

```python
def MarginLimit() -> float
```
Get the margin rate for limit orders.

```python
def MarginStop() -> float
```
Get the margin rate for stop orders.

```python
def MarginStopLimit() -> float
```
Get the margin rate for stop-limit orders.

```python
def SwapMode() -> int
```
Get the swap calculation mode.

```python
def SwapModeDescription() -> str
```
Get the swap calculation mode as a string.

```python
def SwapRollover3Days() -> int
```
Get the day of week when triple swap is charged (0=Sunday, 1=Monday, etc.).

```python
def SwapRollover3DaysDescription() -> str
```
Get the triple swap day as a string.

```python
def SwapLong() -> float
```
Get the swap value for long positions.

```python
def SwapShort() -> float
```
Get the swap value for short positions.

##### Levels and Quantization
```python
def StopsLevel() -> int
```
Get the minimum distance for stop orders in points.

```python
def FreezeLevel() -> int
```
Get the freeze level for orders in points.

```python
def Digits() -> int
```
Get the number of decimal places.

```python
def Point() -> float
```
Get the value of one point.

```python
def TickValue() -> float
```
Get the tick value (value of minimal price change).

```python
def TickValueProfit() -> float
```
Get the calculated tick price for a profitable position.

```python
def TickValueLoss() -> float
```
Get the calculated tick price for a losing position.

```python
def TickSize() -> float
```
Get the minimal price change.

```python
def PipSize() -> float
```
Get the pip size (usually Point() * 10).

```python
def NormalizePrice(price: float) -> float
```
Normalize a price value according to symbol's digits.

##### Contract Sizes and Lot Limits
```python
def ContractSize() -> float
```
Get the contract size (e.g., 100000 for standard forex lot).

```python
def TradeFaceValue() -> float
```
Get the face value of the contract.

```python
def LotsMin() -> float
```
Get the minimum allowed lot size.

```python
def LotsMax() -> float
```
Get the maximum allowed lot size.

```python
def LotsStep() -> float
```
Get the step size for lot increments.

```python
def LotsLimit() -> float
```
Get the maximum total volume of open positions and pending orders.

##### Session Information
```python
def SessionDeals() -> int
def SessionBuyOrders() -> int
def SessionSellOrders() -> int
def SessionTurnover() -> float
def SessionInterest() -> float
def SessionBuyOrdersVolume() -> float
def SessionSellOrdersVolume() -> float
def SessionOpen() -> float
def SessionClose() -> float
def SessionAW() -> float
def SessionPriceSettlement() -> float
def SessionPriceLimitMin() -> float
def SessionPriceLimitMax() -> float
```
Get various session statistics and price levels.

##### Generic Property Access
```python
def InfoInteger(prop: Any) -> Optional[int]
def InfoDouble(prop: Any) -> Optional[float]
def InfoString(prop: Any) -> Optional[str]
```
Get symbol property values by MT5 property constant or string key.

**Usage Example:**

```python
from apps.trade import SymbolInfo

# Create symbol info instance
symbol = SymbolInfo("EURUSD")
symbol.Refresh()
symbol.RefreshRates()

# Display symbol information
print(f"Symbol: {symbol.Name()}")
print(f"Description: {symbol.Description()}")
print(f"Bid: {symbol.Bid():.5f}")
print(f"Ask: {symbol.Ask():.5f}")
print(f"Spread: {symbol.Spread()} points")

# Display trading specifications
print(f"\nTrading Specifications:")
print(f"Digits: {symbol.Digits()}")
print(f"Point: {symbol.Point()}")
print(f"Pip Size: {symbol.PipSize()}")
print(f"Contract Size: {symbol.ContractSize()}")
print(f"Min Lot: {symbol.LotsMin()}")
print(f"Max Lot: {symbol.LotsMax()}")
print(f"Lot Step: {symbol.LotsStep()}")
print(f"Stops Level: {symbol.StopsLevel()} points")

# Display margin and swap
print(f"\nMargin & Swap:")
print(f"Margin Long: {symbol.MarginLong()}")
print(f"Margin Short: {symbol.MarginShort()}")
print(f"Swap Long: {symbol.SwapLong()}")
print(f"Swap Short: {symbol.SwapShort()}")
print(f"Swap Day: {symbol.SwapRollover3DaysDescription()}")

# Normalize price
raw_price = 1.234567
normalized = symbol.NormalizePrice(raw_price)
print(f"\nPrice {raw_price} normalized to {normalized}")
```

**Full Example:** [tests/usage/trade/symbol_info_example.py](../../tests/usage/trade/symbol_info_example.py)

---

### 3. PositionInfo (`position_info.py`)

**Purpose:** Access and manage information about open trading positions.

**Class:** `PositionInfo`

#### Methods

##### Position Identification
```python
def Identifier() -> int
```
Get the unique position ID.

```python
def Magic() -> int
```
Get the Expert Advisor ID (magic number) that opened the position.

```python
def Symbol() -> str
```
Get the symbol name.

```python
def Comment() -> str
```
Get the position comment.

##### Position Properties
```python
def Time() -> datetime
```
Get the position opening time.

```python
def TimeMsc() -> int
```
Get the opening time in milliseconds since Unix epoch.

```python
def TimeUpdate() -> datetime
```
Get the last position modification time.

```python
def TimeUpdateMsc() -> int
```
Get the last modification time in milliseconds.

```python
def PositionType() -> int
```
Get the position type (Buy or Sell).

```python
def TypeDescription() -> str
```
Get the position type as a string ("Buy" or "Sell").

##### Position Financials
```python
def Volume() -> float
```
Get the position volume in lots.

```python
def PriceOpen() -> float
```
Get the position opening price.

```python
def PriceCurrent() -> float
```
Get the current price for the symbol.

```python
def StopLoss() -> float
```
Get the Stop Loss level.

```python
def TakeProfit() -> float
```
Get the Take Profit level.

```python
def Commission() -> float
```
Get the commission charged for the position.

```python
def Swap() -> float
```
Get the accumulated swap.

```python
def Profit() -> float
```
Get the current profit/loss.

```python
def MarginRequired() -> float
```
Get the margin required for the position.

##### Position Selection
```python
def Select(symbol: str) -> bool
```
Select a position by symbol name.

```python
def SelectByIndex(index: int) -> bool
```
Select a position by its index in the positions list.

```python
def SelectByMagic(symbol: str, magic: int) -> bool
```
Select a position by symbol and magic number.

```python
def SelectByTicket(ticket: int) -> bool
```
Select a position by its ticket number.

```python
def Total() -> int
```
Get the total number of open positions.

##### Position State
```python
def StoreState() -> None
```
Save the current position parameters for later comparison.

```python
def CheckState() -> bool
```
Check if the current position parameters match the stored state.

##### Generic Property Access
```python
def InfoInteger(prop: Any) -> Optional[int]
def InfoDouble(prop: Any) -> Optional[float]
def InfoString(prop: Any) -> Optional[str]
```
Get position property values by MT5 property constant or string key.

**Usage Example:**

```python
from apps.trade import PositionInfo

position = PositionInfo()

# Get total positions
total = position.Total()
print(f"Total positions: {total}")

# Iterate through all positions
for i in range(total):
    if position.SelectByIndex(i):
        print(f"\nPosition #{i+1}:")
        print(f"  Symbol: {position.Symbol()}")
        print(f"  Type: {position.TypeDescription()}")
        print(f"  Volume: {position.Volume()}")
        print(f"  Open Price: {position.PriceOpen():.5f}")
        print(f"  Current Price: {position.PriceCurrent():.5f}")
        print(f"  SL: {position.StopLoss():.5f}")
        print(f"  TP: {position.TakeProfit():.5f}")
        print(f"  Profit: {position.Profit():.2f}")
        print(f"  Magic: {position.Magic()}")

# Select specific position by symbol
if position.Select("EURUSD"):
    print(f"\nEURUSD Position:")
    print(f"  Profit: {position.Profit():.2f}")

    # Store state for monitoring
    position.StoreState()

    # Later, check if position has changed
    if not position.CheckState():
        print("Position has been modified!")
```

**Full Example:** [tests/usage/trade/position_info_example.py](../../tests/usage/trade/position_info_example.py)

---

### 4. OrderInfo (`order_info.py`)

**Purpose:** Access information about active pending orders.

**Class:** `OrderInfo`

#### Methods

##### Order Identification
```python
def Ticket() -> int
```
Get the order ticket number.

```python
def Magic() -> int
```
Get the Expert Advisor magic number.

```python
def PositionId() -> int
```
Get the position ID that this order is associated with.

```python
def PositionById() -> int
```
Get the opposite position ID for close-by orders.

```python
def Symbol() -> str
```
Get the order symbol.

```python
def Comment() -> str
```
Get the order comment.

```python
def ExternalId() -> str
```
Get the external trading system ID.

##### Order Properties
```python
def TimeSetup() -> datetime
```
Get the order placement time.

```python
def TimeSetupMsc() -> int
```
Get the placement time in milliseconds.

```python
def TimeExpiration() -> datetime
```
Get the order expiration time.

```python
def TimeDone() -> datetime
```
Get the order completion/cancellation time.

```python
def TimeDoneMsc() -> int
```
Get the completion time in milliseconds.

```python
def Type() -> int
```
Get the order type (Buy, Sell, Buy Limit, Sell Limit, Buy Stop, Sell Stop, etc.).

```python
def TypeDescription() -> str
```
Get the order type as a string.

```python
def State() -> int
```
Get the order state (Started, Placed, Canceled, Partial, Filled, Rejected, Expired).

```python
def StateDescription() -> str
```
Get the order state as a string.

```python
def TypeTime() -> int
```
Get the order expiration type (GTC, Day, Specified, Specified Day).

```python
def TypeTimeDescription() -> str
```
Get the expiration type as a string.

```python
def TypeFilling() -> int
```
Get the order filling type (FOK, IOC, Return).

```python
def TypeFillingDescription() -> str
```
Get the filling type as a string.

##### Order Financials
```python
def VolumeInitial() -> float
```
Get the initial order volume.

```python
def VolumeCurrent() -> float
```
Get the current unfilled volume.

```python
def PriceOpen() -> float
```
Get the order price.

```python
def PriceCurrent() -> float
```
Get the current price for the symbol.

```python
def PriceStopLimit() -> float
```
Get the Stop Limit order price.

```python
def StopLoss() -> float
```
Get the Stop Loss level.

```python
def TakeProfit() -> float
```
Get the Take Profit level.

##### Order Selection
```python
def Select(ticket: int) -> bool
```
Select an order by ticket number.

```python
def SelectByIndex(index: int) -> bool
```
Select an order by its index in the orders list.

```python
def Total() -> int
```
Get the total number of active orders.

##### Generic Property Access
```python
def InfoInteger(prop: Any) -> Optional[int]
def InfoDouble(prop: Any) -> Optional[float]
def InfoString(prop: Any) -> Optional[str]
```
Get order property values by MT5 property constant or string key.

**Usage Example:**

```python
from apps.trade import OrderInfo

order = OrderInfo()

# Get total pending orders
total = order.Total()
print(f"Total pending orders: {total}")

# Iterate through all orders
for i in range(total):
    if order.SelectByIndex(i):
        print(f"\nOrder #{i+1}:")
        print(f"  Ticket: {order.Ticket()}")
        print(f"  Symbol: {order.Symbol()}")
        print(f"  Type: {order.TypeDescription()}")
        print(f"  State: {order.StateDescription()}")
        print(f"  Volume: {order.VolumeInitial()}")
        print(f"  Price: {order.PriceOpen():.5f}")
        print(f"  SL: {order.StopLoss():.5f}")
        print(f"  TP: {order.TakeProfit():.5f}")
        print(f"  Expiration: {order.TypeTimeDescription()}")
        print(f"  Filling: {order.TypeFillingDescription()}")
        print(f"  Magic: {order.Magic()}")

# Select specific order by ticket
if order.Select(12345678):
    print(f"\nOrder {order.Ticket()}:")
    print(f"  Symbol: {order.Symbol()}")
    print(f"  Type: {order.TypeDescription()}")
    print(f"  Price: {order.PriceOpen():.5f}")
```

**Full Example:** [tests/usage/trade/order_info_example.py](../../tests/usage/trade/order_info_example.py)

---

### 5. HistoryOrderInfo (`history_order_info.py`)

**Purpose:** Access information about historical orders from trading history.

**Class:** `HistoryOrderInfo`

#### Methods

##### Order Identification
```python
def Ticket(ticket: Optional[int] = None) -> int
```
Get the order ticket. If `ticket` is provided, selects that order first.

```python
def Magic() -> int
```
Get the Expert Advisor magic number.

```python
def PositionByID() -> int
```
Get the opposite position ID for close-by orders.

```python
def ExternalID() -> str
```
Get the external trading system ID.

```python
def Symbol() -> str
```
Get the order symbol.

```python
def Comment() -> str
```
Get the order comment.

##### Order Properties
```python
def TimeSetup() -> datetime
```
Get the order placement time.

```python
def TimeSetupMsc() -> int
```
Get the placement time in milliseconds.

```python
def OrderType() -> int
```
Get the order type.

```python
def OrderTypeDescription() -> str
```
Get the order type as a string.

```python
def State() -> int
```
Get the order state.

```python
def StateDescription() -> str
```
Get the order state as a string.

```python
def TimeExpiration() -> datetime
```
Get the order expiration time.

```python
def TimeDone() -> datetime
```
Get the order execution or cancellation time.

```python
def TimeDoneMsc() -> int
```
Get the execution time in milliseconds.

```python
def TypeFilling() -> int
```
Get the order filling type.

```python
def TypeFillingDescription() -> str
```
Get the filling type as a string.

```python
def TypeTime() -> int
```
Get the order expiration type.

```python
def TypeTimeDescription() -> str
```
Get the expiration type as a string.

##### Order Financials
```python
def VolumeInitial() -> float
```
Get the initial order volume.

```python
def VolumeCurrent() -> float
```
Get the unfilled volume (for partially filled orders).

```python
def PriceOpen() -> float
```
Get the order price.

```python
def StopLoss() -> float
```
Get the Stop Loss level.

```python
def TakeProfit() -> float
```
Get the Take Profit level.

```python
def PriceCurrent() -> float
```
Get the price at time of selection.

```python
def PriceStopLimit() -> float
```
Get the Stop Limit order price.

##### History Selection
```python
def HistorySelect(date_from: datetime, date_to: datetime) -> bool
```
Select orders from history within the specified date range.

```python
def HistoryOrdersTotal() -> int
```
Get the total number of orders in the selected history range.

```python
def SelectByIndex(index: int) -> bool
```
Select an order by its index in the history selection.

##### Formatting
```python
def FormatOrder() -> str
```
Get a formatted string representation of the order.

```python
@staticmethod
def format_type(order_type: int) -> str
def format_status(state: int) -> str
def format_type_filling(filling: int) -> str
def format_type_time(type_time: int) -> str
def format_price(price: float, price_trigger: float, digits: int) -> str
```
Static methods for formatting order properties.

##### Generic Property Access
```python
def InfoInteger(prop: Any) -> Optional[int]
def InfoDouble(prop: Any) -> Optional[float]
def InfoString(prop: Any) -> Optional[str]
```
Get order property values by MT5 property constant or string key.

**Usage Example:**

```python
from apps.trade import HistoryOrderInfo
from datetime import datetime, timedelta

order = HistoryOrderInfo()

# Select last 30 days of history
date_to = datetime.now()
date_from = date_to - timedelta(days=30)

if order.HistorySelect(date_from, date_to):
    total = order.HistoryOrdersTotal()
    print(f"Found {total} orders in history")

    # Iterate through historical orders
    for i in range(total):
        if order.SelectByIndex(i):
            print(f"\n{order.FormatOrder()}")
            print(f"  State: {order.StateDescription()}")
            print(f"  Setup: {order.TimeSetup()}")
            print(f"  Done: {order.TimeDone()}")
            print(f"  Volume: {order.VolumeInitial()}")
            print(f"  Filled: {order.VolumeInitial() - order.VolumeCurrent()}")

# Select specific order by ticket
if order.Ticket(87654321):
    print(f"\nOrder Details:")
    print(f"  Ticket: {order.Ticket()}")
    print(f"  Symbol: {order.Symbol()}")
    print(f"  Type: {order.OrderTypeDescription()}")
    print(f"  State: {order.StateDescription()}")
```

**Full Example:** [tests/usage/trade/history_order_info_example.py](../../tests/usage/trade/history_order_info_example.py)

---

### 6. DealInfo (`deal_info.py`)

**Purpose:** Access information about executed deals (transactions) from trading history.

**Class:** `DealInfo`

#### Methods

##### Deal Identification
```python
def Ticket() -> int
```
Get the deal ticket number.

```python
def Order() -> int
```
Get the order ticket that resulted in this deal.

```python
def PositionId() -> int
```
Get the position ID associated with the deal.

```python
def Symbol() -> str
```
Get the deal symbol.

```python
def ExternalId() -> str
```
Get the external trading system ID.

```python
def Magic() -> int
```
Get the Expert Advisor magic number.

##### Deal Properties
```python
def Time() -> datetime
```
Get the deal execution time.

```python
def TimeMsc() -> int
```
Get the execution time in milliseconds.

```python
def DealType() -> int
```
Get the deal type (Buy, Sell, Balance, Credit, Charge, etc.).

```python
def DealTypeDescription() -> str
```
Get the deal type as a string.

```python
def Entry() -> int
```
Get the deal entry direction (In, Out, InOut, Out By, State).

```python
def EntryDescription() -> str
```
Get the entry direction as a string.

```python
def Comment() -> str
```
Get the deal comment.

##### Deal Financials
```python
def Volume() -> float
```
Get the deal volume.

```python
def Price() -> float
```
Get the deal execution price.

```python
def Commission() -> float
```
Get the commission charged.

```python
def Swap() -> float
```
Get the swap charged.

```python
def Profit() -> float
```
Get the profit/loss from the deal.

```python
def Fee() -> float
```
Get any additional fees.

##### Deal Selection
```python
def Select(ticket: int) -> bool
```
Select a deal by ticket number.

```python
def HistorySelect(date_from: datetime, date_to: datetime) -> bool
```
Select deals from history within the specified date range.

```python
def TotalDeals() -> int
```
Get the total number of deals in the selected history range.

```python
def SelectByIndex(index: int) -> bool
```
Select a deal by its index in the history selection.

##### Generic Property Access
```python
def InfoInteger(prop: Any) -> Optional[int]
def InfoDouble(prop: Any) -> Optional[float]
def InfoString(prop: Any) -> Optional[str]
```
Get deal property values by MT5 property constant or string key.

**Usage Example:**

```python
from apps.trade import DealInfo
from datetime import datetime, timedelta

deal = DealInfo()

# Select last 7 days of deals
date_to = datetime.now()
date_from = date_to - timedelta(days=7)

if deal.HistorySelect(date_from, date_to):
    total = deal.TotalDeals()
    print(f"Found {total} deals in history")

    total_profit = 0.0
    total_commission = 0.0

    # Iterate through deals
    for i in range(total):
        if deal.SelectByIndex(i):
            print(f"\nDeal #{i+1}:")
            print(f"  Ticket: {deal.Ticket()}")
            print(f"  Symbol: {deal.Symbol()}")
            print(f"  Type: {deal.DealTypeDescription()}")
            print(f"  Entry: {deal.EntryDescription()}")
            print(f"  Time: {deal.Time()}")
            print(f"  Volume: {deal.Volume()}")
            print(f"  Price: {deal.Price():.5f}")
            print(f"  Profit: {deal.Profit():.2f}")
            print(f"  Commission: {deal.Commission():.2f}")
            print(f"  Swap: {deal.Swap():.2f}")

            total_profit += deal.Profit()
            total_commission += deal.Commission()

    print(f"\nSummary:")
    print(f"  Total Deals: {total}")
    print(f"  Total Profit: {total_profit:.2f}")
    print(f"  Total Commission: {total_commission:.2f}")
    print(f"  Net Profit: {total_profit + total_commission:.2f}")

# Select specific deal by ticket
if deal.Select(98765432):
    print(f"\nDeal {deal.Ticket()}:")
    print(f"  Position: {deal.PositionId()}")
    print(f"  Order: {deal.Order()}")
    print(f"  Symbol: {deal.Symbol()}")
    print(f"  Profit: {deal.Profit():.2f}")
```

**Full Example:** [tests/usage/trade/deal_info_example.py](../../tests/usage/trade/deal_info_example.py)

---

### 7. TerminalInfo (`terminal_info.py`)

**Purpose:** Access MetaTrader 5 terminal (platform) properties and system information.

**Class:** `TerminalInfo`

#### Methods

##### Terminal Identification
```python
def Build() -> int
```
Get the MT5 terminal build number.

```python
def Language() -> str
```
Get the terminal language.

```python
def Name() -> str
```
Get the terminal name.

```python
def Company() -> str
```
Get the company that developed the terminal.

```python
def Path() -> str
```
Get the terminal installation path.

```python
def DataPath() -> str
```
Get the terminal data folder path.

```python
def CommonDataPath() -> str
```
Get the common data folder path for all terminals.

##### Terminal State and Permissions
```python
def IsConnected() -> bool
```
Check if connected to the trade server.

```python
def IsDLLsAllowed() -> bool
```
Check if DLL imports are allowed.

```python
def IsTradeAllowed() -> bool
```
Check if automated trading is allowed.

```python
def IsEmailEnabled() -> bool
```
Check if email sending is enabled.

```python
def IsFtpEnabled() -> bool
```
Check if FTP uploads are enabled.

```python
def GetConnectionInfo() -> dict[str, Any]
```
Get a dictionary with all connection-related flags.

##### System Resources
```python
def CPUCores() -> int
```
Get the number of CPU cores.

```python
def MemoryPhysical() -> int
```
Get the physical memory size in MB.

```python
def MemoryTotal() -> int
```
Get the total memory size in MB.

```python
def MemoryAvailable() -> int
```
Get the available memory in MB.

```python
def MemoryUsed() -> int
```
Get the memory used by the terminal in MB.

```python
def DiskSpace() -> int
```
Get the free disk space in MB.

```python
def MaxBars() -> int
```
Get the maximum bars in chart history.

```python
def CodePage() -> int
```
Get the code page of the language.

```python
def IsX64() -> bool
```
Check if terminal is 64-bit.

```python
def OpenCLSupport() -> int
```
Get the OpenCL version supported.

```python
def GetSystemInfo() -> dict[str, Any]
```
Get a dictionary with all system resource information.

##### Generic Property Access
```python
def InfoInteger(prop: Any) -> Optional[int]
def InfoString(prop: Any) -> Optional[str]
```
Get terminal property values by MT5 property constant or string key.

**Usage Example:**

```python
from apps.trade import TerminalInfo

terminal = TerminalInfo()

# Display terminal information
print("Terminal Information:")
print(f"  Name: {terminal.Name()}")
print(f"  Company: {terminal.Company()}")
print(f"  Build: {terminal.Build()}")
print(f"  Language: {terminal.Language()}")
print(f"  Is 64-bit: {terminal.IsX64()}")

# Display connection status
conn_info = terminal.GetConnectionInfo()
print("\nConnection Status:")
for key, value in conn_info.items():
    print(f"  {key}: {value}")

# Display system resources
sys_info = terminal.GetSystemInfo()
print("\nSystem Resources:")
print(f"  CPU Cores: {sys_info['cpu_cores']}")
print(f"  Physical Memory: {sys_info['memory_physical']} MB")
print(f"  Available Memory: {sys_info['memory_available']} MB")
print(f"  Used Memory: {sys_info['memory_used']} MB")
print(f"  Disk Space: {sys_info['disk_space']} MB")
print(f"  OpenCL Support: {sys_info['opencl_support']}")

# Display paths
print("\nPaths:")
print(f"  Terminal: {terminal.Path()}")
print(f"  Data: {terminal.DataPath()}")
print(f"  Common Data: {terminal.CommonDataPath()}")
```

**Full Example:** [tests/usage/trade/terminal_info_example.py](../../tests/usage/trade/terminal_info_example.py)

---

### 8. Trade (`trade.py`)

**Purpose:** Execute trading operations including opening/closing positions, placing/modifying/deleting orders, and accessing trade request/result information.

**Class:** `Trade`

#### Methods

##### Configuration
```python
def LogLevel(level: Optional[int] = None) -> int
```
Get or set the logging level.

```python
def SetExpertMagicNumber(magic: int) -> None
```
Set the Expert Advisor magic number for all subsequent trades.

```python
def SetDeviationInPoints(deviation: int) -> None
```
Set the maximum allowed price deviation for trade execution.

```python
def SetTypeFilling(filling: int) -> None
```
Set the order filling type (FOK, IOC, Return).

```python
def SetTypeFillingBySymbol(symbol: str) -> bool
```
Automatically set the filling type based on symbol specifications.

```python
def SetAsyncMode(mode: bool) -> None
```
Enable or disable asynchronous trade execution.

```python
def SetMarginMode() -> bool
```
Set the margin calculation mode based on account settings.

##### Order Operations
```python
def OrderOpen(symbol: str, order_type: int, volume: float, price: float,
              sl: float = 0.0, tp: float = 0.0, stoplimit: float = 0.0,
              type_time: Optional[int] = None, expiration: Optional[datetime] = None,
              comment: str = "") -> bool
```
Place a pending order with specified parameters.

```python
def OrderModify(ticket: int, price: float, sl: float = 0.0, tp: float = 0.0,
                stoplimit: float = 0.0, type_time: Optional[int] = None,
                expiration: Optional[datetime] = None) -> bool
```
Modify a pending order's parameters.

```python
def OrderDelete(ticket: int) -> bool
```
Delete a pending order.

##### Position Operations
```python
def PositionOpen(symbol: str, order_type: int, volume: float, price: float = 0.0,
                 sl: float = 0.0, tp: float = 0.0, comment: str = "") -> bool
```
Open a position (market order) with specified parameters.

```python
def PositionModify(symbol: Optional[str] = None, ticket: Optional[int] = None,
                   sl: float = 0.0, tp: float = 0.0) -> bool
```
Modify Stop Loss and Take Profit levels of an open position.

```python
def PositionClose(symbol: Optional[str] = None, ticket: Optional[int] = None) -> bool
```
Close an entire position.

```python
def PositionClosePartial(symbol: Optional[str] = None, ticket: Optional[int] = None,
                         volume: float = 0.0) -> bool
```
Partially close a position with specified volume.

```python
def PositionCloseBy(ticket: int, ticket_by: int) -> bool
```
Close a position by an opposite position (close-by operation).

##### Convenience Methods
```python
def Buy(volume: float, symbol: str, price: float = 0.0,
        sl: float = 0.0, tp: float = 0.0, comment: str = "") -> bool
```
Open a long position (shorthand for PositionOpen with ORDER_TYPE_BUY).

```python
def Sell(volume: float, symbol: str, price: float = 0.0,
         sl: float = 0.0, tp: float = 0.0, comment: str = "") -> bool
```
Open a short position (shorthand for PositionOpen with ORDER_TYPE_SELL).

```python
def BuyLimit(volume: float, symbol: str, price: float, sl: float = 0.0,
             tp: float = 0.0, stoplimit: float = 0.0,
             type_time: Optional[int] = None, expiration: Optional[datetime] = None,
             comment: str = "") -> bool
```
Place a Buy Limit order.

```python
def BuyStop(volume: float, symbol: str, price: float, sl: float = 0.0,
            tp: float = 0.0, stoplimit: float = 0.0,
            type_time: Optional[int] = None, expiration: Optional[datetime] = None,
            comment: str = "") -> bool
```
Place a Buy Stop order.

```python
def SellLimit(volume: float, symbol: str, price: float, sl: float = 0.0,
              tp: float = 0.0, stoplimit: float = 0.0,
              type_time: Optional[int] = None, expiration: Optional[datetime] = None,
              comment: str = "") -> bool
```
Place a Sell Limit order.

```python
def SellStop(volume: float, symbol: str, price: float, sl: float = 0.0,
             tp: float = 0.0, stoplimit: float = 0.0,
             type_time: Optional[int] = None, expiration: Optional[datetime] = None,
             comment: str = "") -> bool
```
Place a Sell Stop order.

##### Request Information (Last Request)
```python
def Request() -> dict[str, Any]
def RequestAction() -> int
def RequestActionDescription() -> str
def RequestMagic() -> int
def RequestOrder() -> int
def RequestSymbol() -> str
def RequestVolume() -> float
def RequestPrice() -> float
def RequestStopLimit() -> float
def RequestSL() -> float
def RequestTP() -> float
def RequestDeviation() -> int
def RequestType() -> int
def RequestTypeDescription() -> str
def RequestTypeFilling() -> int
def RequestTypeFillingDescription() -> str
def RequestTypeTime() -> int
def RequestTypeTimeDescription() -> str
def RequestExpiration() -> int
def RequestComment() -> str
def RequestPosition() -> int
def RequestPositionBy() -> int
```
Access parameters of the last trade request.

##### Check Result Information (Pre-execution Check)
```python
def CheckResult() -> dict[str, Any]
def CheckResultRetcode() -> int
def CheckResultRetcodeDescription() -> str
def CheckResultBalance() -> float
def CheckResultEquity() -> float
def CheckResultProfit() -> float
def CheckResultMargin() -> float
def CheckResultMarginFree() -> float
def CheckResultMarginLevel() -> float
def CheckResultComment() -> str
```
Access the results of the pre-trade check (order_check).

##### Result Information (Execution Result)
```python
def Result() -> dict[str, Any]
def ResultRetcode() -> int
def ResultRetcodeDescription() -> str
def ResultDeal() -> int
def ResultOrder() -> int
def ResultVolume() -> float
def ResultPrice() -> float
def ResultBid() -> float
def ResultAsk() -> float
def ResultComment() -> str
```
Access the results of the last trade execution.

##### Formatting and Output
```python
def FormatRequest() -> str
```
Get a formatted string of the last request.

```python
def FormatRequestResult() -> str
```
Get a formatted string of the last result.

```python
def PrintRequest() -> None
```
Print the last request to console.

```python
def PrintResult() -> None
```
Print the last result to console.

**Usage Example:**

```python
from apps.trade import Trade
from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()
trade = Trade()

# Configure trading parameters
trade.SetExpertMagicNumber(123456)
trade.SetDeviationInPoints(20)

# Open a Buy position
symbol = "EURUSD"
volume = 0.1
sl = 1.0950  # Stop loss
tp = 1.1100  # Take profit

if trade.Buy(volume, symbol, sl=sl, tp=tp, comment="Test trade"):
    print("Trade executed successfully!")
    print(f"Deal: {trade.ResultDeal()}")
    print(f"Order: {trade.ResultOrder()}")
    print(f"Price: {trade.ResultPrice():.5f}")
    print(f"Volume: {trade.ResultVolume()}")
else:
    print("Trade failed!")
    print(f"Error: {trade.ResultRetcodeDescription()}")
    print(f"Comment: {trade.ResultComment()}")

# Modify position SL/TP
if trade.PositionModify(symbol=symbol, sl=1.0960, tp=1.1110):
    print("Position modified successfully!")

# Place a pending Sell Limit order
if trade.SellLimit(volume=0.1, symbol=symbol, price=1.1150, sl=1.1200, tp=1.1050):
    print(f"Sell Limit order placed: {trade.ResultOrder()}")

# Close position
if trade.PositionClose(symbol=symbol):
    print("Position closed!")
    print(f"Close deal: {trade.ResultDeal()}")
```

**Full Example:** [tests/usage/trade/trade_example.py](../../tests/usage/trade/trade_example.py)

---

### 9. TradeSimulator (Lazy-loaded from `apps.simulation`)

**Purpose:** Simulate trading operations for backtesting, practice, and strategy development without risking real capital.

**Note:** This class is lazy-loaded from `apps.simulation.simulator` and becomes available when imported from `apps.trade`.

**Usage Example:**

```python
from apps.trade import TradeSimulator

# Create simulator instance
simulator = TradeSimulator()

# Use with any trade class
from apps.trade import Trade, AccountInfo

trade = Trade(api=simulator)
account = AccountInfo(api=simulator)

# Trade normally - all operations are simulated
trade.Buy(0.1, "EURUSD")
```

**Full Example:** [tests/usage/trade/trade_simulator_example.py](../../tests/usage/trade/trade_simulator_example.py)

---

## Common Patterns

### Pattern 1: Monitoring Account Health

```python
from apps.trade import AccountInfo

def check_account_health(account: AccountInfo) -> dict:
    """Check if account is in good standing for trading."""
    health = {
        "can_trade": True,
        "warnings": [],
        "errors": []
    }

    # Check permissions
    if not account.TradeAllowed():
        health["can_trade"] = False
        health["errors"].append("Trading not allowed on account")

    # Check margin level
    margin_level = account.MarginLevel()
    if margin_level > 0:
        if margin_level < account.MarginStopOut():
            health["can_trade"] = False
            health["errors"].append(f"Margin level critical: {margin_level:.2f}%")
        elif margin_level < account.MarginCall():
            health["warnings"].append(f"Margin call level: {margin_level:.2f}%")
        elif margin_level < 200:
            health["warnings"].append(f"Low margin level: {margin_level:.2f}%")

    # Check free margin
    if account.FreeMargin() < 100:
        health["warnings"].append("Low free margin")

    return health

# Usage
account = AccountInfo()
health = check_account_health(account)

if health["can_trade"]:
    print("Account is healthy for trading")
else:
    print("Cannot trade:")
    for error in health["errors"]:
        print(f"  - {error}")
```

### Pattern 2: Position Risk Management

```python
from apps.trade import PositionInfo, Trade

def apply_trailing_stop(symbol: str, trail_points: int):
    """Apply trailing stop to a position."""
    position = PositionInfo()
    trade = Trade()

    if not position.Select(symbol):
        return False

    current_price = position.PriceCurrent()
    open_price = position.PriceOpen()
    sl = position.StopLoss()
    pos_type = position.PositionType()

    from apps.mt5 import get_mt5_api
    mt5 = get_mt5_api()

    # Calculate point value
    from apps.trade import SymbolInfo
    symbol_info = SymbolInfo(symbol)
    symbol_info.Refresh()
    point = symbol_info.Point()
    trail_distance = trail_points * point

    if pos_type == mt5.POSITION_TYPE_BUY:
        # For buy positions, move SL up when price increases
        new_sl = current_price - trail_distance
        if new_sl > sl:
            return trade.PositionModify(symbol=symbol, sl=new_sl, tp=position.TakeProfit())
    else:
        # For sell positions, move SL down when price decreases
        new_sl = current_price + trail_distance
        if new_sl < sl or sl == 0:
            return trade.PositionModify(symbol=symbol, sl=new_sl, tp=position.TakeProfit())

    return False
```

### Pattern 3: Smart Order Placement

```python
from apps.trade import SymbolInfo, Trade, AccountInfo

def place_smart_order(symbol: str, order_type: int, volume: float,
                      risk_percent: float = 2.0, rr_ratio: float = 2.0):
    """
    Place an order with automatic SL/TP calculation based on risk management.

    Args:
        symbol: Trading symbol
        order_type: Order type (ORDER_TYPE_BUY or ORDER_TYPE_SELL)
        volume: Trade volume
        risk_percent: Percentage of account to risk (default 2%)
        rr_ratio: Risk/Reward ratio (default 2.0)
    """
    from apps.mt5 import get_mt5_api
    mt5 = get_mt5_api()

    symbol_info = SymbolInfo(symbol)
    symbol_info.Refresh()
    symbol_info.RefreshRates()

    account = AccountInfo()
    trade = Trade()

    # Get current prices
    bid = symbol_info.Bid()
    ask = symbol_info.Ask()
    point = symbol_info.Point()
    stops_level = symbol_info.StopsLevel()

    # Calculate position size based on risk
    balance = account.Balance()
    risk_amount = balance * (risk_percent / 100.0)

    # Calculate SL and TP
    if order_type == mt5.ORDER_TYPE_BUY:
        entry_price = ask
        sl_distance = stops_level * 1.5 * point  # 1.5x minimum stops level
        sl = entry_price - sl_distance
        tp = entry_price + (sl_distance * rr_ratio)
    else:
        entry_price = bid
        sl_distance = stops_level * 1.5 * point
        sl = entry_price + sl_distance
        tp = entry_price - (sl_distance * rr_ratio)

    # Place trade
    if trade.PositionOpen(symbol, order_type, volume, price=0.0, sl=sl, tp=tp):
        print(f"Order placed successfully:")
        print(f"  Entry: {entry_price:.5f}")
        print(f"  SL: {sl:.5f}")
        print(f"  TP: {tp:.5f}")
        print(f"  Risk: {risk_amount:.2f} ({risk_percent}%)")
        print(f"  Potential Reward: {risk_amount * rr_ratio:.2f}")
        return True
    else:
        print(f"Order failed: {trade.ResultRetcodeDescription()}")
        return False

# Usage
from apps.mt5 import get_mt5_api
mt5 = get_mt5_api()
place_smart_order("EURUSD", mt5.ORDER_TYPE_BUY, 0.1, risk_percent=1.5, rr_ratio=3.0)
```

### Pattern 4: Trade History Analysis

```python
from apps.trade import DealInfo, HistoryOrderInfo
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_trading_history(days: int = 30):
    """Analyze trading performance over the last N days."""
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)

    deal = DealInfo()
    if not deal.HistorySelect(date_from, date_to):
        return None

    stats = {
        "total_deals": 0,
        "winning_deals": 0,
        "losing_deals": 0,
        "total_profit": 0.0,
        "total_loss": 0.0,
        "total_commission": 0.0,
        "total_swap": 0.0,
        "symbols": defaultdict(lambda: {"trades": 0, "profit": 0.0}),
        "by_day": defaultdict(lambda: {"trades": 0, "profit": 0.0}),
    }

    for i in range(deal.TotalDeals()):
        if deal.SelectByIndex(i):
            # Filter to actual trade deals (not balance/credit operations)
            deal_type = deal.DealType()
            from apps.mt5 import get_mt5_api
            mt5 = get_mt5_api()
            if deal_type not in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL):
                continue

            stats["total_deals"] += 1
            profit = deal.Profit()
            stats["total_profit"] += max(0, profit)
            stats["total_loss"] += min(0, profit)

            if profit > 0:
                stats["winning_deals"] += 1
            elif profit < 0:
                stats["losing_deals"] += 1

            stats["total_commission"] += deal.Commission()
            stats["total_swap"] += deal.Swap()

            symbol = deal.Symbol()
            stats["symbols"][symbol]["trades"] += 1
            stats["symbols"][symbol]["profit"] += profit

            day = deal.Time().date()
            stats["by_day"][day]["trades"] += 1
            stats["by_day"][day]["profit"] += profit

    # Calculate metrics
    if stats["total_deals"] > 0:
        stats["win_rate"] = stats["winning_deals"] / stats["total_deals"] * 100
        stats["net_profit"] = stats["total_profit"] + stats["total_loss"]
        if stats["total_loss"] != 0:
            stats["profit_factor"] = abs(stats["total_profit"] / stats["total_loss"])
        else:
            stats["profit_factor"] = float('inf') if stats["total_profit"] > 0 else 0

    return stats

# Usage
stats = analyze_trading_history(days=30)
if stats:
    print(f"Trading Statistics (Last 30 Days):")
    print(f"  Total Deals: {stats['total_deals']}")
    print(f"  Win Rate: {stats.get('win_rate', 0):.2f}%")
    print(f"  Net Profit: {stats.get('net_profit', 0):.2f}")
    print(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")
    print(f"  Total Commission: {stats['total_commission']:.2f}")
    print(f"  Total Swap: {stats['total_swap']:.2f}")

    print(f"\nBy Symbol:")
    for symbol, data in sorted(stats['symbols'].items(), key=lambda x: x[1]['profit'], reverse=True):
        print(f"  {symbol}: {data['trades']} trades, {data['profit']:.2f} profit")
```

### Pattern 5: Multi-Symbol Position Monitor

```python
from apps.trade import PositionInfo, SymbolInfo
from typing import List, Dict, Any

def get_all_positions_summary() -> List[Dict[str, Any]]:
    """Get detailed summary of all open positions."""
    position = PositionInfo()
    positions_data = []

    total = position.Total()
    for i in range(total):
        if position.SelectByIndex(i):
            symbol = position.Symbol()

            # Get symbol info for price formatting
            symbol_info = SymbolInfo(symbol)
            symbol_info.Refresh()
            digits = symbol_info.Digits()

            # Calculate position metrics
            open_price = position.PriceOpen()
            current_price = position.PriceCurrent()
            volume = position.Volume()
            profit = position.Profit()

            from apps.mt5 import get_mt5_api
            mt5 = get_mt5_api()

            if position.PositionType() == mt5.POSITION_TYPE_BUY:
                pips = (current_price - open_price) / symbol_info.Point()
            else:
                pips = (open_price - current_price) / symbol_info.Point()

            pos_data = {
                "ticket": position.Identifier(),
                "symbol": symbol,
                "type": position.TypeDescription(),
                "volume": volume,
                "open_price": round(open_price, digits),
                "current_price": round(current_price, digits),
                "sl": round(position.StopLoss(), digits) if position.StopLoss() > 0 else None,
                "tp": round(position.TakeProfit(), digits) if position.TakeProfit() > 0 else None,
                "profit": round(profit, 2),
                "pips": round(pips, 1),
                "commission": round(position.Commission(), 2),
                "swap": round(position.Swap(), 2),
                "magic": position.Magic(),
                "comment": position.Comment(),
                "time": position.Time(),
            }

            positions_data.append(pos_data)

    return positions_data

# Usage
positions = get_all_positions_summary()
if positions:
    print(f"Open Positions ({len(positions)}):")
    print("-" * 100)

    total_profit = 0.0
    for pos in positions:
        print(f"#{pos['ticket']}: {pos['type']} {pos['volume']} {pos['symbol']} @ {pos['open_price']}")
        print(f"  Current: {pos['current_price']}, P/L: {pos['profit']:.2f} ({pos['pips']:.1f} pips)")
        if pos['sl']:
            print(f"  SL: {pos['sl']}, TP: {pos['tp']}")
        total_profit += pos['profit']

    print("-" * 100)
    print(f"Total P/L: {total_profit:.2f}")
else:
    print("No open positions")
```

### Pattern 6: Symbol Scanner

```python
from apps.trade import SymbolInfo
from apps.mt5 import get_mt5_api

def scan_tradeable_symbols() -> List[Dict[str, Any]]:
    """Scan all symbols for trading opportunities."""
    mt5 = get_mt5_api()
    symbols = mt5.symbols_get()

    if not symbols:
        return []

    results = []
    for s in symbols:
        symbol_info = SymbolInfo(s.name)
        symbol_info.Refresh()
        symbol_info.RefreshRates()

        # Check if symbol is tradeable
        if symbol_info.TradeMode() == mt5.SYMBOL_TRADE_MODE_DISABLED:
            continue

        # Get key metrics
        spread = symbol_info.Spread()
        spread_pips = spread / 10 if symbol_info.Digits() == 5 or symbol_info.Digits() == 3 else spread

        data = {
            "symbol": s.name,
            "bid": symbol_info.Bid(),
            "ask": symbol_info.Ask(),
            "spread": spread,
            "spread_pips": round(spread_pips, 1),
            "volume": symbol_info.Volume(),
            "description": symbol_info.Description(),
            "trade_mode": symbol_info.TradeModeDescription(),
        }

        results.append(data)

    # Sort by spread
    results.sort(key=lambda x: x['spread_pips'])
    return results

# Usage
symbols = scan_tradeable_symbols()
print(f"Found {len(symbols)} tradeable symbols")
print("\nTop 10 symbols by spread:")
for symbol in symbols[:10]:
    print(f"  {symbol['symbol']}: {symbol['spread_pips']:.1f} pips, {symbol['trade_mode']}")
```

---

## Best Practices

### 1. Always Check Connection Status

```python
from apps.trade import TerminalInfo

terminal = TerminalInfo()
if not terminal.IsConnected():
    print("Not connected to trade server!")
    # Handle reconnection
```

### 2. Validate Symbol Before Trading

```python
from apps.trade import SymbolInfo

def validate_symbol(symbol: str) -> bool:
    """Validate that a symbol is ready for trading."""
    symbol_info = SymbolInfo(symbol)

    # Ensure symbol is selected in Market Watch
    if not symbol_info.Select():
        symbol_info.Select(True)

    # Refresh data
    if not symbol_info.Refresh():
        return False
    if not symbol_info.RefreshRates():
        return False

    # Check if trading is allowed
    from apps.mt5 import get_mt5_api
    mt5 = get_mt5_api()

    if symbol_info.TradeMode() == mt5.SYMBOL_TRADE_MODE_DISABLED:
        print(f"Trading disabled for {symbol}")
        return False

    return True
```

### 3. Use Pre-Trade Checks

```python
from apps.trade import Trade, AccountInfo

trade = Trade()
account = AccountInfo()

# Before placing order, verify margin availability
symbol = "EURUSD"
volume = 1.0
price = 1.1000

from apps.mt5 import get_mt5_api
mt5 = get_mt5_api()

margin_required = account.MarginCheck(symbol, mt5.ORDER_TYPE_BUY, volume, price)
if account.FreeMargin() < margin_required:
    print(f"Insufficient margin: need {margin_required:.2f}, have {account.FreeMargin():.2f}")
else:
    # Proceed with trade
    trade.Buy(volume, symbol)
```

### 4. Handle Trade Errors Gracefully

```python
from apps.trade import Trade

trade = Trade()

if not trade.Buy(0.1, "EURUSD"):
    # Trade failed - get detailed error info
    print(f"Trade failed!")
    print(f"  Retcode: {trade.ResultRetcode()}")
    print(f"  Description: {trade.ResultRetcodeDescription()}")
    print(f"  Comment: {trade.ResultComment()}")

    # Log full request for debugging
    print(f"  Request: {trade.FormatRequest()}")
    print(f"  Result: {trade.FormatRequestResult()}")
```

### 5. Use Magic Numbers for Trade Identification

```python
from apps.trade import Trade

# Set unique magic number for your EA/strategy
STRATEGY_MAGIC = 123456

trade = Trade()
trade.SetExpertMagicNumber(STRATEGY_MAGIC)

# All trades will have this magic number
trade.Buy(0.1, "EURUSD", comment="Strategy v1.0")

# Later, filter positions by magic number
from apps.trade import PositionInfo
position = PositionInfo()

for i in range(position.Total()):
    if position.SelectByIndex(i):
        if position.Magic() == STRATEGY_MAGIC:
            print(f"Found strategy position: {position.Symbol()}")
```

### 6. Normalize Prices

```python
from apps.trade import SymbolInfo

def normalize_sl_tp(symbol: str, sl: float, tp: float) -> tuple:
    """Normalize Stop Loss and Take Profit prices."""
    symbol_info = SymbolInfo(symbol)
    symbol_info.Refresh()

    sl_normalized = symbol_info.NormalizePrice(sl) if sl > 0 else 0.0
    tp_normalized = symbol_info.NormalizePrice(tp) if tp > 0 else 0.0

    return sl_normalized, tp_normalized
```

### 7. Respect Symbol Trading Sessions

```python
from apps.trade import SymbolInfo
from datetime import datetime

def is_trading_session_open(symbol: str) -> bool:
    """Check if symbol's trading session is currently open."""
    symbol_info = SymbolInfo(symbol)
    symbol_info.RefreshRates()

    # Check if we're getting fresh quotes
    last_quote = symbol_info.Time()
    now = datetime.now()

    # If last quote is older than 1 minute, session might be closed
    if (now - last_quote).total_seconds() > 60:
        return False

    # Check if spread is reasonable (not zero and not too high)
    spread = symbol_info.Spread()
    if spread == 0 or spread > 1000:  # Adjust threshold as needed
        return False

    return True
```

### 8. Use Context Managers for MT5 Connection

```python
from contextlib import contextmanager
from apps.mt5 import MT5Client

@contextmanager
def mt5_connection(login: int, password: str, server: str, path: str = ""):
    """Context manager for MT5 connections."""
    client = MT5Client()

    if not client.connect(login=login, password=password, server=server, path=path):
        raise ConnectionError("Failed to connect to MT5")

    try:
        yield client
    finally:
        client.shutdown()

# Usage
with mt5_connection(12345678, "password", "Broker-Server") as mt5:
    from apps.trade import AccountInfo
    account = AccountInfo()
    print(f"Balance: {account.Balance()}")
```

### 9. Monitor and Log All Trading Activity

```python
from apps.trade import Trade
from apps.logger import logger

class MonitoredTrade(Trade):
    """Trade class with enhanced logging."""

    def PositionOpen(self, *args, **kwargs):
        result = super().PositionOpen(*args, **kwargs)

        if result:
            logger.info(f"Position opened: {self.FormatRequest()}")
            logger.info(f"Result: {self.FormatRequestResult()}")
        else:
            logger.error(f"Position failed: {self.ResultRetcodeDescription()}")
            logger.error(f"Request: {self.FormatRequest()}")

        return result
```

### 10. Implement Emergency Stop Mechanism

```python
from apps.trade import Trade, PositionInfo
from apps.logger import logger

def emergency_close_all_positions(reason: str = "Emergency"):
    """Close all open positions immediately."""
    logger.warning(f"EMERGENCY CLOSE ALL: {reason}")

    position = PositionInfo()
    trade = Trade()

    closed = 0
    failed = 0

    for i in range(position.Total()):
        if position.SelectByIndex(i):
            symbol = position.Symbol()
            if trade.PositionClose(symbol=symbol):
                logger.info(f"Closed position: {symbol}")
                closed += 1
            else:
                logger.error(f"Failed to close {symbol}: {trade.ResultRetcodeDescription()}")
                failed += 1

    logger.warning(f"Emergency close complete: {closed} closed, {failed} failed")
    return closed, failed
```

---

## Performance Considerations

1. **Caching**: All info classes cache data after fetching from MT5. Call `Refresh()` or `RefreshRates()` to update cached data.

2. **Batch Operations**: When working with multiple positions or orders, fetch the list once and iterate through indices rather than making repeated API calls.

3. **Property Access**: Use cached property methods (like `Balance()`, `Equity()`) instead of generic `InfoDouble()` calls for better performance.

4. **Symbol Selection**: Keep frequently traded symbols in Market Watch to ensure faster data access.

5. **Async Mode**: Use `Trade.SetAsyncMode(True)` for fire-and-forget orders when you don't need immediate confirmation.

---

## Error Handling

All MT5 trade operations can fail. Always check return values:

```python
from apps.trade import Trade

trade = Trade()

if not trade.Buy(0.1, "EURUSD"):
    # Check why it failed
    retcode = trade.ResultRetcode()

    from apps.mt5 import get_mt5_api
    mt5 = get_mt5_api()

    if retcode == mt5.TRADE_RETCODE_NO_MONEY:
        print("Insufficient funds")
    elif retcode == mt5.TRADE_RETCODE_INVALID_PRICE:
        print("Invalid price")
    elif retcode == mt5.TRADE_RETCODE_MARKET_CLOSED:
        print("Market is closed")
    else:
        print(f"Error: {trade.ResultRetcodeDescription()}")
```

**Common Return Codes:**
- `TRADE_RETCODE_DONE` (10008): Request completed successfully
- `TRADE_RETCODE_PLACED` (10009): Order placed successfully
- `TRADE_RETCODE_REQUOTE` (10004): Requote received
- `TRADE_RETCODE_REJECT` (10006): Request rejected
- `TRADE_RETCODE_NO_MONEY` (10019): Insufficient funds
- `TRADE_RETCODE_INVALID_PRICE` (10015): Invalid price
- `TRADE_RETCODE_MARKET_CLOSED` (10018): Market is closed

---

## Testing with Simulator

All trade classes support simulator mode for risk-free testing:

```python
from apps.simulation.simulator import TradeSimulator
from apps.trade import Trade, AccountInfo, PositionInfo

# Create simulator with custom settings
simulator = TradeSimulator(initial_balance=10000.0)

# Use simulator with trade classes
trade = Trade(api=simulator)
account = AccountInfo(api=simulator)
position = PositionInfo(api=simulator)

# Trade normally - everything is simulated
trade.Buy(0.1, "EURUSD")

print(f"Simulated Balance: {account.Balance()}")
print(f"Simulated Positions: {position.Total()}")
```

---

## Related Modules

- **apps.mt5**: Core MT5 API wrapper and connection management
- **apps.simulation**: Trade simulator for backtesting and practice
- **apps.sqlite**: Database storage for trades and history

---

## Additional Resources

- [MQL5 Documentation](https://www.mql5.com/en/docs)
- [MQL5 Standard Library](https://www.mql5.com/en/docs/standardlibrary)
- [MT5 Python Package Documentation](https://www.mql5.com/en/docs/python_metatrader5)

---

## License

This module is part of the HaruQuant trading platform.

---

## Contributing

When contributing to this module:
1. Maintain alignment with MQL5 Standard Library interfaces
2. Add comprehensive docstrings to all methods
3. Include usage examples for new features
4. Update this README with new components or patterns
5. Test with both live MT5 and simulator

---

*Last Updated: 2026-02-05*
