# Trades API Endpoints

This document describes the API endpoints for accessing trade details and chart data.

## Base URL

```
http://localhost:8000/api/trades
```

---

## Endpoints

### 1. Get Trade By ID

Retrieves detailed information about a specific trade, including all fields from the `backtest_trades` table and associated backtest metadata.

#### Request

```http
GET /api/trades/{trade_id}
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `trade_id` | integer | Yes | The unique identifier of the trade |

**Example Request:**

```bash
curl http://localhost:8000/api/trades/12345
```

#### Response

**Success Response (200 OK):**

```json
{
  "trade_id": 12345,
  "backtest_id": 67,
  "symbol": "EURUSD",
  "side": "BUY",
  "open_time": "2024-12-15T14:30:00",
  "close_time": "2024-12-15T16:45:00",
  "open_price": 1.05234,
  "close_price": 1.05478,
  "pnl": 244.00,
  "pnl_pips": 24.4,
  "pnl_percent": 2.44,
  "commission": -7.00,
  "swap": -0.50,
  "net_profit": 236.50,
  "position_size": 1.0,
  "stop_loss_price": 1.05000,
  "profit_target_price": 1.05500,
  "initial_risk_usd": 234.00,
  "initial_risk_pips": 23.4,
  "r_multiple": 1.04,
  "mae_usd": -45.00,
  "mae_pips": -4.5,
  "mfe_usd": 267.00,
  "mfe_pips": 26.7,
  "time_in_trade_seconds": 8100,
  "bars_in_trade": 135,
  "balance_at_entry": 10000.00,
  "equity_at_entry": 10000.00,
  "strategy_name": "Moving Average Crossover",
  "exit_reason": "Take Profit",
  "trade_context": "Bullish trend continuation",
  "backtest_symbols": "[\"EURUSD\", \"GBPUSD\"]",
  "backtest_timeframes": "[\"H1\"]",
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-12-31T23:59:59",
  "initial_balance": 10000.00
}
```

**Error Responses:**

| Status Code | Description | Response Body |
|-------------|-------------|---------------|
| 404 | Trade not found | `{"detail": "Trade with ID 12345 not found"}` |
| 500 | Internal server error | `{"detail": "An error occurred while fetching trade"}` |

---

### 2. Get Backtest Chart Data

Retrieves the complete OHLCV chart data for the entire backtest period, along with all trades in the backtest. This data is kept in memory on the client side for fast navigation between trades.

#### Request

```http
GET /api/trades/{trade_id}/backtest-chart-data?bars_before=25&bars_after=25
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `trade_id` | integer | Yes | The unique identifier of the trade |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `bars_before` | integer | No | 25 | Number of bars to include before trade entry (for initial context) |
| `bars_after` | integer | No | 25 | Number of bars to include after trade exit (for initial context) |

**Example Request:**

```bash
curl "http://localhost:8000/api/trades/12345/backtest-chart-data?bars_before=25&bars_after=25"
```

#### Response

**Success Response (200 OK):**

```json
{
  "chart_data": [
    {
      "time": 1702627200,
      "open": 1.05123,
      "high": 1.05234,
      "low": 1.05098,
      "close": 1.05200,
      "volume": 1250
    },
    {
      "time": 1702630800,
      "open": 1.05200,
      "high": 1.05345,
      "low": 1.05189,
      "close": 1.05312,
      "volume": 1420
    }
    // ... thousands more bars for entire backtest period
  ],
  "symbol": "EURUSD",
  "timeframe": "H1",
  "all_trades": [
    {
      "trade_id": 12344,
      "backtest_id": 67,
      "symbol": "EURUSD",
      "side": "SELL",
      "open_time": "2024-12-15T10:00:00",
      "close_time": "2024-12-15T12:30:00",
      "open_price": 1.05500,
      "close_price": 1.05234,
      "pnl": 266.00,
      "pnl_pips": 26.6
      // ... other trade fields
    },
    {
      "trade_id": 12345,
      "backtest_id": 67,
      "symbol": "EURUSD",
      "side": "BUY",
      "open_time": "2024-12-15T14:30:00",
      "close_time": "2024-12-15T16:45:00",
      "open_price": 1.05234,
      "close_price": 1.05478,
      "pnl": 244.00,
      "pnl_pips": 24.4
      // ... other trade fields
    }
    // ... all other trades in backtest, sorted by close_time
  ],
  "current_trade_index": 1,
  "bars_before": 25,
  "bars_after": 25,
  "total_bars": 8760,
  "backtest_start": "2024-01-01T00:00:00",
  "backtest_end": "2024-12-31T23:59:59"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `chart_data` | array | Complete OHLCV data for entire backtest period. Each bar contains: `time` (Unix timestamp), `open`, `high`, `low`, `close`, `volume` |
| `symbol` | string | Trading symbol (e.g., "EURUSD") |
| `timeframe` | string | Chart timeframe (e.g., "H1", "M15", "D1") |
| `all_trades` | array | All trades in this backtest, sorted by `close_time` ascending |
| `current_trade_index` | integer | Index of the requested trade in the `all_trades` array |
| `bars_before` | integer | Number of bars before trade (echoed from request) |
| `bars_after` | integer | Number of bars after trade (echoed from request) |
| `total_bars` | integer | Total number of bars in `chart_data` |
| `backtest_start` | string | Start date/time of backtest period |
| `backtest_end` | string | End date/time of backtest period |

**Error Responses:**

| Status Code | Description | Response Body |
|-------------|-------------|---------------|
| 404 | Trade not found | `{"detail": "Trade with ID 12345 not found"}` |
| 503 | MT5 unavailable | `{"detail": "MetaTrader 5 connection unavailable. Chart data cannot be retrieved."}` |
| 500 | Internal server error | `{"detail": "An error occurred while fetching chart data"}` |

---

## Implementation Details

### Caching

Chart data is cached on the backend with a TTL (Time To Live) of **1 hour** (3600 seconds). The cache key is:

```
chart_{symbol}_{timeframe}_{start_timestamp}_{end_timestamp}
```

This significantly improves performance for subsequent requests to the same backtest data.

### Data Flow

1. **Client requests trade detail** → Frontend fetches both endpoints in parallel
2. **Backend queries database** → Retrieves trade + backtest metadata
3. **Backend fetches MT5 data** → Calls `MT5Data.get_bars()` for entire backtest period
4. **Backend caches result** → Stores in memory cache for 1 hour
5. **Client stores in memory** → Full dataset kept in React state
6. **Client filters client-side** → Shows only visible window of bars based on current trade
7. **Prev/Next navigation** → No API calls, just updates visible window from cached data

### Performance Characteristics

- **Initial load**: 1-3 seconds (includes MT5 data fetch)
- **Subsequent loads**: 100-500ms (cache hit)
- **Prev/Next navigation**: Instant (<100ms, client-side filtering only)
- **Memory usage**: ~500KB - 2MB depending on backtest duration

---

## Usage Examples

### Fetching a Trade and Its Chart Data

```python
import requests

# Fetch trade details
trade_response = requests.get("http://localhost:8000/api/trades/12345")
trade = trade_response.json()

# Fetch chart data for the backtest
chart_response = requests.get(
    "http://localhost:8000/api/trades/12345/backtest-chart-data",
    params={"bars_before": 25, "bars_after": 25}
)
chart_data = chart_response.json()

print(f"Trade: {trade['symbol']} {trade['side']}")
print(f"P&L: ${trade['pnl']:.2f}")
print(f"Total bars: {chart_data['total_bars']}")
print(f"Current trade is #{chart_data['current_trade_index'] + 1} of {len(chart_data['all_trades'])}")
```

### TypeScript/JavaScript Example

```typescript
import { tradesApi } from '@/lib/api/trades'

// Fetch trade and chart data in parallel
const [trade, chartData] = await Promise.all([
  tradesApi.getTradeById(12345),
  tradesApi.getBacktestChartData(12345, 25, 25)
])

console.log(`Trade: ${trade.symbol} ${trade.side}`)
console.log(`P&L: $${trade.pnl?.toFixed(2)}`)
console.log(`Total bars: ${chartData.total_bars}`)
console.log(`Trades in backtest: ${chartData.all_trades.length}`)

// Store full chart data in memory
const fullChartData = chartData.chart_data

// Filter to visible window (client-side)
const visibleData = fullChartData.filter(
  bar => bar.time >= visibleWindow.start && bar.time <= visibleWindow.end
)
```

---

## Error Handling

### Backend Error Handling

The endpoints implement the following error handling:

1. **Database Errors**: Return 500 with generic error message
2. **Trade Not Found**: Return 404 with specific message
3. **MT5 Connection Errors**: Return 503 with service unavailable message
4. **Invalid Parameters**: Return 422 with validation error details

### Frontend Error Handling

The frontend should handle:

1. **404 Errors**: Show "Trade not found" message with back button
2. **503 Errors**: Show stats only, display "Chart unavailable" message
3. **Network Errors**: Show retry button with error message
4. **Invalid Data**: Fall back to error boundary with reload option

---

## Related Documentation

- [Trade Detail View Component](../components/trade-detail-view.md)
- [MT5 Data Integration](../backend/mt5-integration.md)
- [Caching Strategy](../backend/caching.md)
