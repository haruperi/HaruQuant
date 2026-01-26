# CTrade Module (MT5 Standard Library)

This module contains MT5-specific trade classes aligned to the MQL5 Standard Library.
It is intentionally MT5-only and does not depend on the legacy `apps/trading` module.

Reference:
- MQL5 CSymbolInfo: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/csymbolinfo
- MQL5 CAccountInfo: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/caccountinfo
- MQL5 COrderInfo: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/corderinfo
- MQL5 CHistoryOrderInfo: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/chistoryorderinfo
- MQL5 CPositionInfo: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cpositioninfo
- MQL5 CDealInfo: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cdealinfo
- MQL5 CTrade: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/ctrade
- MQL5 CTerminalInfo: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cterminalinfo

## CSymbolInfo

`CSymbolInfo` mirrors the MQL5 Standard Library interface and method names.
It provides symbol properties and tick data for MT5.

### Usage

```python
import MetaTrader5 as mt5
from apps.ctrade import CSymbolInfo

mt5.initialize()

symbol = CSymbolInfo("EURUSD")
symbol.Refresh()
symbol.RefreshRates()

print(symbol.Name())
print(symbol.Bid(), symbol.Ask())
print(symbol.Spread())

mt5.shutdown()
```

## CTerminalInfo

`CTerminalInfo` mirrors the MQL5 Standard Library interface and method names.
It provides terminal properties for MT5.

### Usage

```python
import MetaTrader5 as mt5
from apps.ctrade import CTerminalInfo

mt5.initialize()

terminal = CTerminalInfo()
print(terminal.Name())
print(terminal.Build())
print(terminal.Language())

mt5.shutdown()
```

## CTrade

`CTrade` mirrors the MQL5 Standard Library interface and method names.
It provides trading operations for MT5.

### Usage

```python
import MetaTrader5 as mt5
from apps.ctrade import CTrade

mt5.initialize()

trade = CTrade()
trade.SetExpertMagicNumber(12345)
trade.SetDeviationInPoints(10)

# NOTE: This will place a real trade if executed.
# trade.Buy(0.1, "EURUSD", comment="CTrade test")

mt5.shutdown()
```

## CDealInfo

`CDealInfo` mirrors the MQL5 Standard Library interface and method names.
It provides deal properties for MT5.

### Usage

```python
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from apps.ctrade import CDealInfo

mt5.initialize()

date_from = datetime.now() - timedelta(days=30)
date_to = datetime.now()
deal = CDealInfo(date_from=date_from, date_to=date_to)

if deal.SelectByIndex(0):
    print(deal.Ticket())
    print(deal.Symbol())
    print(deal.DealTypeDescription())

mt5.shutdown()
```

## CPositionInfo

`CPositionInfo` mirrors the MQL5 Standard Library interface and method names.
It provides position properties for MT5.

### Usage

```python
import MetaTrader5 as mt5
from apps.ctrade import CPositionInfo

mt5.initialize()

pos = CPositionInfo()
if pos.SelectByIndex(0):
    print(pos.Symbol())
    print(pos.TypeDescription())
    print(pos.Volume())

mt5.shutdown()
```

## CHistoryOrderInfo

`CHistoryOrderInfo` mirrors the MQL5 Standard Library interface and method names.
It provides history order properties for MT5.

### Usage

```python
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from apps.ctrade import CHistoryOrderInfo

mt5.initialize()

date_from = datetime.now() - timedelta(days=30)
date_to = datetime.now()
order = CHistoryOrderInfo(date_from=date_from, date_to=date_to)

if order.SelectByIndex(0):
    print(order.Ticket())
    print(order.Symbol())
    print(order.OrderTypeDescription())

mt5.shutdown()
```

## COrderInfo

`COrderInfo` mirrors the MQL5 Standard Library interface and method names.
It provides order properties for MT5.

### Usage

```python
import MetaTrader5 as mt5
from apps.ctrade import COrderInfo

mt5.initialize()

order = COrderInfo()
if order.SelectByIndex(0):
    print(order.Ticket())
    print(order.Symbol())
    print(order.TypeDescription())

mt5.shutdown()
```

### Notes

- Call `Refresh()` to load symbol properties.
- Call `RefreshRates()` to load tick data.
- `IsSynchronized()` returns True when both symbol info and tick data are available.

## CAccountInfo

`CAccountInfo` mirrors the MQL5 Standard Library interface and method names.
It provides account properties for MT5.

### Usage

```python
import MetaTrader5 as mt5
from apps.ctrade import CAccountInfo

mt5.initialize()

account = CAccountInfo()
print(account.Login())
print(account.Balance())
print(account.Equity())
print(account.MarginLevel())

mt5.shutdown()
```
