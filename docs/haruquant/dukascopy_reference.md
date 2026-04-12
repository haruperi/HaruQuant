# Dukascopy Market Data Boundary

A Python client for fetching historical market data from Dukascopy's free data feed, providing access to forex, stocks, indices, commodities, and cryptocurrencies.

## Overview

The Dukascopy market data boundary provides a governed MCP-facing interface to download historical OHLC (Open, High, Low, Close) data from Dukascopy's servers. It supports multiple timeframes from tick data to monthly bars and includes automatic retry logic, fail-closed error handling, deterministic normalization, and freshness metadata.

## Key Features

- **Multiple Timeframes**: From tick data to monthly bars
- **Wide Instrument Coverage**: Forex, stocks, indices, commodities, cryptocurrencies
- **Automatic Retry Logic**: Handles connection failures gracefully
- **Data Streaming**: Efficient streaming for large datasets
- **Bid/Ask Data**: Separate bid and ask price data
- **Pandas Integration**: Returns data as pandas DataFrames
- **Instrument Mapping**: Friendly names for thousands of instruments

## Architecture

The boundary consists of three main components:
- `backend/mcp/market_data_mcp/dukascopy.py`: external HTTP client for data fetching
- `backend/mcp/market_data_mcp/tools.py`: MCP tool facade for governed access
- `backend/services/market_data/dukascopy_instruments.py`: instrument name mappings
- `backend/services/market_data/dukascopy.py`: deterministic bar normalization and freshness metadata

```
┌──────────────────┐
│  Dukascopy API   │  ← Data Fetching
├──────────────────┤
│ fetch()          │  ← Historical data
│ live_fetch()     │  ← Live/recent data
│ _stream()        │  ← Streaming data
└──────────────────┘

┌──────────────────┐
│ INSTRUMENT_MAP   │  ← Instrument Mappings
├──────────────────┤
│ Forex Pairs      │  ← EURUSD, GBPUSD, etc.
│ Stocks           │  ← AAPL, TSLA, etc.
│ Indices          │  ← SP500, DAX, etc.
│ Commodities      │  ← Gold, Oil, etc.
│ Cryptocurrencies │  ← BTC, ETH, etc.
└──────────────────┘
```

---

## 1. Dukascopy API Component

Core functionality for fetching historical market data from Dukascopy servers.

### Functions

- **`fetch()`** - Fetch historical data for a date range
- **`live_fetch()`** - Fetch live/recent historical data
- **`_stream()`** - Internal streaming function for large datasets

### Constants

**Time Units:**
- `TIME_UNIT_TICK` - Tick data
- `TIME_UNIT_SEC` - Seconds
- `TIME_UNIT_MIN` - Minutes
- `TIME_UNIT_HOUR` - Hours
- `TIME_UNIT_DAY` - Days
- `TIME_UNIT_WEEK` - Weeks
- `TIME_UNIT_MONTH` - Months

**Intervals:**
- `INTERVAL_TICK` - Tick data
- `INTERVAL_SEC_1` - 1 second
- `INTERVAL_SEC_10` - 10 seconds
- `INTERVAL_SEC_30` - 30 seconds
- `INTERVAL_MIN_1` - 1 minute
- `INTERVAL_MIN_5` - 5 minutes
- `INTERVAL_MIN_15` - 15 minutes
- `INTERVAL_MIN_30` - 30 minutes
- `INTERVAL_HOUR_1` - 1 hour
- `INTERVAL_HOUR_4` - 4 hours
- `INTERVAL_DAY_1` - 1 day
- `INTERVAL_WEEK_1` - 1 week
- `INTERVAL_MONTH_1` - 1 month

**Offer Sides:**
- `OFFER_SIDE_BID` - "B" - Bid prices
- `OFFER_SIDE_ASK` - "A" - Ask prices

### Methods

#### fetch()

Fetch historical data from Dukascopy for a specified date range.

**Parameters:**
- `instrument: str` - Instrument name (e.g., "EUR/USD", "AAPL.US/USD")
- `interval: str` - Data interval (use INTERVAL_* constants)
- `offer_side: str` - Bid or Ask (use OFFER_SIDE_* constants)
- `start: datetime` - Start date
- `end: datetime` - End date
- `max_retries: int = 7` - Maximum retry attempts on failure
- `limit: int = 30_000` - Maximum rows per request (max 30,000)

**Returns:**
- `pandas.DataFrame` - OHLC data with columns:
  - `time` - Timestamp
  - `open` - Open price
  - `high` - High price
  - `low` - Low price
  - `close` - Close price
  - `volume` - Volume (for tick data)

**Example:**
```python
from backend.mcp.market_data_mcp import fetch, INTERVAL_HOUR_1, OFFER_SIDE_BID
from datetime import datetime, timedelta

# Fetch 1-hour EUR/USD bid data for last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

data = fetch(
    instrument="EUR/USD",
    interval=INTERVAL_HOUR_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

print(f"Retrieved {len(data)} bars")
print(data.head())
```

#### live_fetch()

Fetch live/recent historical data with custom interval values.

**Parameters:**
- `instrument: str` - Instrument name
- `interval_value: int` - Interval value (e.g., 5 for 5 minutes)
- `time_unit: str` - Time unit (use TIME_UNIT_* constants)
- `offer_side: str` - Bid or Ask
- `start: datetime` - Start date
- `end: datetime` - End date
- `max_retries: int = 7` - Maximum retry attempts
- `limit: int = 30_000` - Maximum rows per request

**Returns:**
- `pandas.DataFrame` - OHLC data

**Example:**
```python
from backend.mcp.market_data_mcp import live_fetch, TIME_UNIT_MIN, OFFER_SIDE_ASK
from datetime import datetime, timedelta

# Fetch 15-minute EUR/USD ask data
end_date = datetime.now()
start_date = end_date - timedelta(hours=24)

data = live_fetch(
    instrument="EUR/USD",
    interval_value=15,
    time_unit=TIME_UNIT_MIN,
    offer_side=OFFER_SIDE_ASK,
    start=start_date,
    end=end_date
)

print(f"Retrieved {len(data)} bars")
```

### Example

**Basic Usage:**

```python
from backend.mcp.market_data_mcp import (
    fetch,
    INTERVAL_DAY_1,
    INTERVAL_HOUR_1,
    INTERVAL_MIN_5,
    OFFER_SIDE_BID,
    OFFER_SIDE_ASK
)
from datetime import datetime, timedelta

# Fetch daily EUR/USD data
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

daily_data = fetch(
    instrument="EUR/USD",
    interval=INTERVAL_DAY_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

print(f"Daily data: {len(daily_data)} bars")
print(daily_data.tail())
```

**Multiple Timeframes:**

```python
from backend.mcp.market_data_mcp import fetch, INTERVAL_HOUR_1, INTERVAL_MIN_15, OFFER_SIDE_BID
from datetime import datetime, timedelta

end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# Fetch hourly data
hourly = fetch(
    instrument="GBP/USD",
    interval=INTERVAL_HOUR_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

# Fetch 15-minute data
m15 = fetch(
    instrument="GBP/USD",
    interval=INTERVAL_MIN_15,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

print(f"Hourly: {len(hourly)} bars")
print(f"15-min: {len(m15)} bars")
```

**Bid vs Ask Data:**

```python
from backend.mcp.market_data_mcp import fetch, INTERVAL_HOUR_1, OFFER_SIDE_BID, OFFER_SIDE_ASK
from datetime import datetime, timedelta

end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# Fetch both bid and ask data
bid_data = fetch(
    instrument="USD/JPY",
    interval=INTERVAL_HOUR_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

ask_data = fetch(
    instrument="USD/JPY",
    interval=INTERVAL_HOUR_1,
    offer_side=OFFER_SIDE_ASK,
    start=start_date,
    end=end_date
)

# Calculate spread
bid_data['spread'] = ask_data['close'] - bid_data['close']
print(f"Average spread: {bid_data['spread'].mean():.5f}")
```

**Stock Data:**

```python
from backend.mcp.market_data_mcp import fetch, INTERVAL_DAY_1, OFFER_SIDE_BID
from datetime import datetime, timedelta

# Fetch Apple stock data
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

aapl_data = fetch(
    instrument="AAPL.US/USD",
    interval=INTERVAL_DAY_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

print(f"AAPL data: {len(aapl_data)} days")
print(f"Latest close: ${aapl_data.iloc[-1]['close']:.2f}")
```

**Cryptocurrency Data:**

```python
from backend.mcp.market_data_mcp import fetch, INTERVAL_HOUR_1, OFFER_SIDE_BID
from datetime import datetime, timedelta

# Fetch Bitcoin data
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

btc_data = fetch(
    instrument="BTC/USD",
    interval=INTERVAL_HOUR_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

print(f"BTC data: {len(btc_data)} hours")
print(f"Latest price: ${btc_data.iloc[-1]['close']:,.2f}")
```

**Commodity Data:**

```python
from backend.mcp.market_data_mcp import fetch, INTERVAL_DAY_1, OFFER_SIDE_BID
from datetime import datetime, timedelta

# Fetch Gold data
end_date = datetime.now()
start_date = end_date - timedelta(days=180)

gold_data = fetch(
    instrument="XAU/USD",
    interval=INTERVAL_DAY_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

print(f"Gold data: {len(gold_data)} days")
print(f"Latest price: ${gold_data.iloc[-1]['close']:.2f}/oz")
```

---

## 2. Instrument Mappings Component

Comprehensive instrument name mappings for easy access to thousands of tradable instruments.

### INSTRUMENT_MAP

A dictionary mapping friendly instrument names to Dukascopy instrument strings.

**Format:**
```python
INSTRUMENT_MAP = {
    "EURUSD": "EUR/USD",
    "AAPL": "AAPL.US/USD",
    "SP500": "E_SandP-500",
    "GOLD": "XAU/USD",
    "BTCUSD": "BTC/USD",
    # ... 4000+ more instruments
}
```

### Instrument Categories

**Forex Pairs (Major):**
- `EURUSD` → "EUR/USD"
- `GBPUSD` → "GBP/USD"
- `USDJPY` → "USD/JPY"
- `USDCHF` → "USD/CHF"
- `AUDUSD` → "AUD/USD"
- `USDCAD` → "USD/CAD"
- `NZDUSD` → "NZD/USD"

**Forex Pairs (Cross):**
- `EURJPY` → "EUR/JPY"
- `GBPJPY` → "GBP/JPY"
- `EURGBP` → "EUR/GBP"
- `AUDCAD` → "AUD/CAD"
- `AUDCHF` → "AUD/CHF"
- `AUDNZD` → "AUD/NZD"

**US Stocks:**
- `AAPL` → "AAPL.US/USD" (Apple)
- `MSFT` → "MSFT.US/USD" (Microsoft)
- `GOOGL` → "GOOGL.US/USD" (Google)
- `AMZN` → "AMZN.US/USD" (Amazon)
- `TSLA` → "TSLA.US/USD" (Tesla)
- `META` → "META.US/USD" (Meta)
- `NVDA` → "NVDA.US/USD" (NVIDIA)

**European Stocks:**
- `ASML` → "ASML.NL/EUR" (ASML Netherlands)
- `SAP` → "SAP.DE/EUR" (SAP Germany)
- `NESN` → "NESN.CH/CHF" (Nestlé Switzerland)
- `NOVN` → "NOVN.CH/CHF" (Novartis Switzerland)
- `VOW3` → "VOW3.DE/EUR" (Volkswagen Germany)

**Indices:**
- `SP500` → "E_SandP-500" (S&P 500)
- `DAX` → "E_DAAX" (DAX 40)
- `CAC40` → "E_CAAC-40" (CAC 40)
- `FTSE100` → "E_FTSE-100" (FTSE 100)
- `NIKKEI` → "E_Nikkei-225" (Nikkei 225)
- `NASDAQ` → "E_NASDAQ-100" (NASDAQ 100)

**Commodities:**
- `GOLD` → "XAU/USD" (Gold)
- `SILVER` → "XAG/USD" (Silver)
- `CRUDE` → "E_Light" (WTI Crude Oil)
- `BRENT` → "E_Brent" (Brent Crude Oil)
- `NATGAS` → "E_NatGas" (Natural Gas)

**Cryptocurrencies:**
- `BTCUSD` → "BTC/USD" (Bitcoin)
- `ETHUSD` → "ETH/USD" (Ethereum)
- `LTCUSD` → "LTC/USD" (Litecoin)
- `XRPUSD` → "XRP/USD" (Ripple)
- `BCHUSD` → "BCH/USD" (Bitcoin Cash)
- `ADAUSD` → "ADA/USD" (Cardano)

### Helper Function

**get_instrument_name()**

Get the Dukascopy instrument string from a friendly name.

```python
def get_instrument_name(friendly_name: str) -> str:
    """
    Get Dukascopy instrument string from friendly name.

    Args:
        friendly_name: Friendly instrument name (e.g., "EURUSD", "AAPL")

    Returns:
        Dukascopy instrument string (e.g., "EUR/USD", "AAPL.US/USD")

    Raises:
        KeyError: If instrument not found
    """
    # Normalize input (uppercase, remove special characters)
    normalized = friendly_name.upper().replace("/", "").replace(".", "")

    if normalized in INSTRUMENT_MAP:
        return INSTRUMENT_MAP[normalized]

    raise KeyError(f"Instrument '{friendly_name}' not found in INSTRUMENT_MAP")
```

### Example

**Using Instrument Mappings:**

```python
from backend.services.market_data.dukascopy_instruments import INSTRUMENT_MAP
from backend.mcp.market_data_mcp import fetch, INTERVAL_DAY_1, OFFER_SIDE_BID
from datetime import datetime, timedelta

# Get instrument string
eurusd = INSTRUMENT_MAP["EURUSD"]  # "EUR/USD"
aapl = INSTRUMENT_MAP["AAPL"]      # "AAPL.US/USD"
sp500 = INSTRUMENT_MAP["SP500"]    # "E_SandP-500"

print(f"EUR/USD: {eurusd}")
print(f"Apple: {aapl}")
print(f"S&P 500: {sp500}")

# Fetch data using mapped names
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

data = fetch(
    instrument=eurusd,
    interval=INTERVAL_DAY_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

print(f"Retrieved {len(data)} bars for {eurusd}")
```

**Fetching Multiple Instruments:**

```python
from backend.services.market_data.dukascopy_instruments import INSTRUMENT_MAP
from backend.mcp.market_data_mcp import fetch, INTERVAL_HOUR_1, OFFER_SIDE_BID
from datetime import datetime, timedelta
import pandas as pd

# Define portfolio
portfolio = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "BTCUSD"]

end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# Fetch data for all instruments
data_dict = {}
for symbol in portfolio:
    instrument = INSTRUMENT_MAP[symbol]
    data = fetch(
        instrument=instrument,
        interval=INTERVAL_HOUR_1,
        offer_side=OFFER_SIDE_BID,
        start=start_date,
        end=end_date
    )
    data_dict[symbol] = data
    print(f"{symbol}: {len(data)} bars")

# Combine closing prices
closes = pd.DataFrame({
    symbol: data['close']
    for symbol, data in data_dict.items()
})

print("\nLatest prices:")
print(closes.tail())
```

**Searching for Instruments:**

```python
from backend.services.market_data.dukascopy_instruments import INSTRUMENT_MAP

# Find all Apple-related instruments
apple_instruments = {
    k: v for k, v in INSTRUMENT_MAP.items()
    if 'AAPL' in k
}

print("Apple instruments:")
for key, value in apple_instruments.items():
    print(f"  {key}: {value}")

# Find all EUR pairs
eur_pairs = {
    k: v for k, v in INSTRUMENT_MAP.items()
    if k.startswith('EUR') and '/' in v
}

print("\nEUR pairs:")
for key, value in list(eur_pairs.items())[:10]:
    print(f"  {key}: {value}")
```

---

## Common Patterns

### Complete Workflow

```python
from backend.services.market_data.dukascopy_instruments import INSTRUMENT_MAP
from backend.mcp.market_data_mcp import (
    fetch,
    INTERVAL_HOUR_1,
    OFFER_SIDE_BID
)
from datetime import datetime, timedelta
import pandas as pd

# 1. Define instruments
symbols = ["EURUSD", "GBPUSD", "USDJPY"]

# 2. Set date range
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# 3. Fetch data
all_data = {}
for symbol in symbols:
    instrument = INSTRUMENT_MAP[symbol]
    data = fetch(
        instrument=instrument,
        interval=INTERVAL_HOUR_1,
        offer_side=OFFER_SIDE_BID,
        start=start_date,
        end=end_date
    )
    all_data[symbol] = data
    print(f"✓ {symbol}: {len(data)} bars")

# 4. Process data
for symbol, data in all_data.items():
    data['returns'] = data['close'].pct_change()
    print(f"{symbol} - Latest: {data.iloc[-1]['close']:.5f}")
```

### Error Handling

```python
from backend.mcp.market_data_mcp import fetch, INTERVAL_DAY_1, OFFER_SIDE_BID
from backend.services.market_data.dukascopy_instruments import INSTRUMENT_MAP
from datetime import datetime, timedelta

def safe_fetch(symbol, days=30):
    """Safely fetch data with error handling."""
    try:
        instrument = INSTRUMENT_MAP.get(symbol)
        if not instrument:
            print(f"❌ Instrument '{symbol}' not found")
            return None

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        data = fetch(
            instrument=instrument,
            interval=INTERVAL_DAY_1,
            offer_side=OFFER_SIDE_BID,
            start=start_date,
            end=end_date,
            max_retries=5
        )

        print(f"✓ {symbol}: {len(data)} bars")
        return data

    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return None

# Use safe fetch
data = safe_fetch("EURUSD", days=60)
if data is not None:
    print(f"Latest close: {data.iloc[-1]['close']:.5f}")
```

### Data Analysis

```python
from backend.services.market_data.dukascopy_instruments import INSTRUMENT_MAP
from backend.mcp.market_data_mcp import fetch, INTERVAL_DAY_1, OFFER_SIDE_BID
from datetime import datetime, timedelta
import pandas as pd

# Fetch data
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

data = fetch(
    instrument=INSTRUMENT_MAP["EURUSD"],
    interval=INTERVAL_DAY_1,
    offer_side=OFFER_SIDE_BID,
    start=start_date,
    end=end_date
)

# Calculate technical indicators
data['sma_20'] = data['close'].rolling(window=20).mean()
data['sma_50'] = data['close'].rolling(window=50).mean()
data['volatility'] = data['close'].rolling(window=20).std()

# Calculate returns
data['daily_return'] = data['close'].pct_change()
data['cumulative_return'] = (1 + data['daily_return']).cumprod() - 1

# Summary statistics
print(f"Total bars: {len(data)}")
print(f"Date range: {data.iloc[0]['time']} to {data.iloc[-1]['time']}")
print(f"Latest close: {data.iloc[-1]['close']:.5f}")
print(f"20-day SMA: {data.iloc[-1]['sma_20']:.5f}")
print(f"50-day SMA: {data.iloc[-1]['sma_50']:.5f}")
print(f"Cumulative return: {data.iloc[-1]['cumulative_return']:.2%}")
```

---

## Best Practices

1. **Use instrument mappings**: Always use `INSTRUMENT_MAP` for consistent naming
2. **Handle errors gracefully**: Wrap fetch calls in try-except blocks
3. **Respect rate limits**: Add delays between multiple requests
4. **Use appropriate timeframes**: Choose timeframes based on your analysis needs
5. **Validate data**: Check for missing values and data quality
6. **Cache data**: Save fetched data locally to avoid repeated requests
7. **Use both bid and ask**: Fetch both sides for spread analysis
8. **Set reasonable date ranges**: Large date ranges may timeout
9. **Monitor retries**: Use `max_retries` parameter appropriately
10. **Check data completeness**: Verify you received expected number of bars

## Supported Instruments

The module supports 4000+ instruments across multiple asset classes:

- **Forex**: 50+ major and cross currency pairs
- **Stocks**: 3000+ stocks from US, Europe, Asia markets
- **Indices**: 30+ major global indices
- **Commodities**: Gold, Silver, Oil, Natural Gas, Agricultural products
- **Cryptocurrencies**: Bitcoin, Ethereum, and 20+ altcoins

See `instruments.py` for the complete list.

## Data Limitations

- **Historical depth**: Varies by instrument (typically 10+ years for forex)
- **Tick data**: Limited to recent history (few months)
- **Weekend data**: No data during market closures
- **Request limits**: Maximum 30,000 rows per request
- **Rate limiting**: Dukascopy may throttle excessive requests

## License

Copyright 2025, HaruQuant

## See Also

- `apps/mt5/` - MT5 client for live trading data
- `apps/utils/data_getters.py` - Unified data retrieval interface
- Dukascopy website: https://www.dukascopy.com/
