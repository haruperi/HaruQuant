# API Documentation
## Complete Trading System REST & WebSocket API

**Version:** 1.0
**Date:** November 23, 2025
**Base URL:** `http://localhost:8000/api/v1`
**WebSocket URL:** `ws://localhost:8000/ws`

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-23 | API Team | Initial API documentation |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Common Patterns](#3-common-patterns)
4. [Authentication Endpoints](#4-authentication-endpoints)
5. [Market Data Endpoints](#5-market-data-endpoints)
6. [Strategy Endpoints](#6-strategy-endpoints)
7. [Backtesting Endpoints](#7-backtesting-endpoints)
8. [Optimization Endpoints](#8-optimization-endpoints)
9. [Live Trading Endpoints](#9-live-trading-endpoints)
10. [Risk Management Endpoints](#10-risk-management-endpoints)
11. [Analytics Endpoints](#11-analytics-endpoints)
12. [System Endpoints](#12-system-endpoints)
13. [WebSocket API](#13-websocket-api)
14. [Error Handling](#14-error-handling)
15. [Rate Limiting](#15-rate-limiting)
16. [Appendices](#16-appendices)

---

## 1. Overview

### 1.1 Introduction

The Complete Trading System API provides programmatic access to all system functionality including market data management, strategy development, backtesting, optimization, and live trading execution.

### 1.2 API Characteristics

- **Architecture**: RESTful API following REST principles
- **Format**: JSON for all requests and responses
- **Authentication**: JWT (JSON Web Tokens)
- **Versioning**: URL-based versioning (`/api/v1`, `/api/v2`)
- **Real-time**: WebSocket support for streaming data
- **HTTPS**: TLS 1.2+ required in production

### 1.3 Base URLs

| Environment | Base URL | WebSocket URL |
|-------------|----------|---------------|
| Development | `http://localhost:8000/api/v1` | `ws://localhost:8000/ws` |
| Production | `https://your-domain.com/api/v1` | `wss://your-domain.com/ws` |

### 1.4 Quick Start

```bash
# 1. Authenticate
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "trader", "password": "your_password"}'

# 2. Use the access token
curl http://localhost:8000/api/v1/strategies \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 1.5 API Libraries

**Python:**
```python
import requests

# Authenticate
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "trader", "password": "password"}
)
token = response.json()["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {token}"}
strategies = requests.get(
    "http://localhost:8000/api/v1/strategies",
    headers=headers
).json()
```

**JavaScript:**
```javascript
// Authenticate
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'trader', password: 'password'})
});
const {access_token} = await response.json();

// Make authenticated request
const strategies = await fetch('http://localhost:8000/api/v1/strategies', {
  headers: {'Authorization': `Bearer ${access_token}`}
}).then(r => r.json());
```

---

## 2. Authentication

### 2.1 Authentication Methods

The API uses JWT (JSON Web Tokens) for authentication. Tokens are obtained via the login endpoint and must be included in the `Authorization` header for all authenticated requests.

### 2.2 Token Types

**Access Token:**
- Used for API authentication
- Short-lived (default: 60 minutes)
- Included in Authorization header

**Refresh Token:**
- Used to obtain new access tokens
- Long-lived (default: 7 days)
- Should be stored securely

### 2.3 Authentication Flow

```
1. Client sends credentials to /auth/login
2. Server validates credentials
3. Server returns access_token and refresh_token
4. Client stores tokens securely
5. Client includes access_token in all requests
6. When access_token expires, use refresh_token to get new access_token
```

### 2.4 Including Authentication

**Header Format:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Example:**
```bash
curl http://localhost:8000/api/v1/strategies \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

---

## 3. Common Patterns

### 3.1 Request Headers

**Required Headers:**
```
Content-Type: application/json
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Optional Headers:**
```
Accept: application/json
X-Request-ID: unique-request-id (for tracking)
```

### 3.2 Response Format

**Success Response:**
```json
{
  "status": "success",
  "data": {
    // Response data here
  },
  "metadata": {
    "timestamp": "2025-11-23T10:00:00Z",
    "version": "1.0.0"
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid parameter: symbol is required",
    "details": {
      "field": "symbol",
      "constraint": "required"
    }
  },
  "metadata": {
    "timestamp": "2025-11-23T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### 3.3 HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, PATCH, DELETE |
| 201 | Created | Successful POST creating a resource |
| 202 | Accepted | Request accepted for async processing |
| 204 | No Content | Successful DELETE with no response body |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid auth but insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### 3.4 Pagination

For endpoints that return lists, pagination is supported:

**Request Parameters:**
```
?page=1&page_size=50&sort_by=created_at&sort_order=desc
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total_items": 150,
      "total_pages": 3,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

### 3.5 Filtering

**Query Parameters:**
```
?filter[status]=active&filter[created_after]=2025-01-01
```

### 3.6 Field Selection

Request only specific fields:
```
?fields=id,name,created_at
```

### 3.7 Date/Time Format

All timestamps use ISO 8601 format with UTC timezone:
```
2025-11-23T10:00:00Z
```

---

## 4. Authentication Endpoints

### 4.1 Login

Authenticate user and receive JWT tokens.

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "username": "trader",
  "password": "secure_password"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

**Errors:**
- `401 Unauthorized`: Invalid credentials
- `429 Too Many Requests`: Too many login attempts

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "trader",
    "password": "password123"
  }'
```

---

### 4.2 Logout

Invalidate current access token.

**Endpoint:** `POST /auth/logout`

**Headers:** `Authorization: Bearer {token}`

**Request:** No body required

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "message": "Successfully logged out"
  }
}
```

---

### 4.3 Refresh Token

Obtain a new access token using refresh token.

**Endpoint:** `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

---

### 4.4 Get Current User

Get information about the authenticated user.

**Endpoint:** `GET /auth/me`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "id": "usr_abc123",
    "username": "trader",
    "email": "trader@example.com",
    "is_active": true,
    "created_at": "2025-01-15T10:00:00Z",
    "last_login": "2025-11-23T09:30:00Z"
  }
}
```

---

### 4.5 Change Password

Change user password.

**Endpoint:** `PUT /auth/change-password`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "message": "Password changed successfully"
  }
}
```

**Errors:**
- `401 Unauthorized`: Current password incorrect
- `400 Bad Request`: Password does not meet requirements

---

## 5. Market Data Endpoints

### 5.1 List Symbols

Get all available trading symbols.

**Endpoint:** `GET /data/symbols`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `exchange` (optional): Filter by exchange
- `asset_class` (optional): Filter by asset class (forex, crypto, stocks, futures)
- `is_active` (optional): Filter by active status (true/false)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "symbols": [
      {
        "id": "BTCUSDT",
        "name": "Bitcoin/US Dollar",
        "exchange": "Binance",
        "asset_class": "crypto",
        "tick_size": 0.01,
        "lot_size": 0.001,
        "is_active": true
      },
      {
        "id": "EURUSD",
        "name": "Euro/US Dollar",
        "exchange": "MT5",
        "asset_class": "forex",
        "tick_size": 0.00001,
        "lot_size": 1000,
        "is_active": true
      }
    ]
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/data/symbols?asset_class=forex \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 5.2 Get Symbol Details

Get detailed information about a specific symbol.

**Endpoint:** `GET /data/symbols/{symbol_id}`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "id": "BTCUSDT",
    "name": "Bitcoin/US Dollar",
    "exchange": "Binance",
    "asset_class": "crypto",
    "tick_size": 0.01,
    "lot_size": 0.001,
    "min_quantity": 0.001,
    "max_quantity": 9000,
    "is_active": true,
    "trading_hours": "24/7",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-11-20T15:30:00Z"
  }
}
```

**Errors:**
- `404 Not Found`: Symbol not found

---

### 5.3 Get Historical Bars

Retrieve historical OHLCV bar data.

**Endpoint:** `GET /data/bars/{symbol_id}`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `timeframe` (required): Bar timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
- `start` (required): Start date (ISO 8601 format)
- `end` (required): End date (ISO 8601 format)
- `limit` (optional): Maximum number of bars (default: 1000, max: 10000)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "bars": [
      {
        "timestamp": "2025-11-23T00:00:00Z",
        "open": 37250.50,
        "high": 37450.00,
        "low": 37100.25,
        "close": 37350.75,
        "volume": 1234.567,
        "spread": 0.5
      },
      {
        "timestamp": "2025-11-23T01:00:00Z",
        "open": 37350.75,
        "high": 37550.00,
        "low": 37300.00,
        "close": 37480.50,
        "volume": 2345.678,
        "spread": 0.5
      }
    ],
    "count": 2
  }
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/data/bars/BTCUSDT?\
timeframe=1h&start=2025-11-01T00:00:00Z&end=2025-11-23T23:59:59Z" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Errors:**
- `400 Bad Request`: Invalid timeframe or date range
- `404 Not Found`: Symbol not found

---

### 5.4 Download Historical Data

Trigger asynchronous download of historical data from broker.

**Endpoint:** `POST /data/download`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2025-11-23T23:59:59Z",
  "provider": "mt5"
}
```

**Response:** `202 Accepted`
```json
{
  "status": "success",
  "data": {
    "job_id": "job_abc123",
    "status": "queued",
    "estimated_time": 60,
    "message": "Data download job queued"
  }
}
```

**Check Status:**
```bash
GET /data/download/{job_id}/status
```

---

### 5.5 Get Data Status

Get status of available data for a symbol.

**Endpoint:** `GET /data/status`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `symbol` (required): Symbol ID
- `timeframe` (optional): Specific timeframe

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "data_availability": [
      {
        "timeframe": "1h",
        "earliest_date": "2023-01-01T00:00:00Z",
        "latest_date": "2025-11-23T10:00:00Z",
        "total_bars": 15768,
        "completeness": 99.8,
        "gaps": 2
      }
    ]
  }
}
```

---

## 6. Strategy Endpoints

### 6.1 List Strategies

Get all user strategies.

**Endpoint:** `GET /strategies`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50)
- `sort_by` (optional): Sort field (name, created_at, updated_at)
- `sort_order` (optional): asc or desc

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "strategies": [
      {
        "id": "strat_abc123",
        "name": "MA Crossover Strategy",
        "description": "Simple moving average crossover",
        "version": "1.0.0",
        "created_at": "2025-10-15T10:00:00Z",
        "updated_at": "2025-11-20T14:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total_items": 15,
      "total_pages": 1
    }
  }
}
```

---

### 6.2 Create Strategy

Create a new trading strategy.

**Endpoint:** `POST /strategies`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "name": "RSI Mean Reversion",
  "description": "Mean reversion strategy using RSI",
  "parameters": {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70
  },
  "entry_rules": {
    "long": "rsi < rsi_oversold",
    "short": "rsi > rsi_overbought"
  },
  "exit_rules": {
    "take_profit": 2.0,
    "stop_loss": 1.0,
    "trailing_stop": false
  },
  "risk_config": {
    "max_position_size": 0.1,
    "position_sizing_method": "fixed_fractional"
  }
}
```

**Response:** `201 Created`
```json
{
  "status": "success",
  "data": {
    "id": "strat_xyz789",
    "name": "RSI Mean Reversion",
    "version": "1.0.0",
    "created_at": "2025-11-23T10:30:00Z",
    "message": "Strategy created successfully"
  }
}
```

**Errors:**
- `400 Bad Request`: Invalid strategy parameters
- `422 Unprocessable Entity`: Validation error

---

### 6.3 Get Strategy

Get details of a specific strategy.

**Endpoint:** `GET /strategies/{strategy_id}`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "id": "strat_abc123",
    "name": "MA Crossover Strategy",
    "description": "Simple moving average crossover",
    "version": "1.0.0",
    "parameters": {
      "fast_ma": 20,
      "slow_ma": 50
    },
    "entry_rules": {
      "long": "fast_ma > slow_ma",
      "short": "fast_ma < slow_ma"
    },
    "exit_rules": {
      "take_profit": 2.0,
      "stop_loss": 1.0,
      "trailing_stop": true
    },
    "risk_config": {
      "max_position_size": 0.1,
      "position_sizing_method": "volatility"
    },
    "created_at": "2025-10-15T10:00:00Z",
    "updated_at": "2025-11-20T14:30:00Z"
  }
}
```

---

### 6.4 Update Strategy

Update an existing strategy.

**Endpoint:** `PUT /strategies/{strategy_id}`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "description": "Updated description",
  "parameters": {
    "fast_ma": 15,
    "slow_ma": 45
  }
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "id": "strat_abc123",
    "version": "1.1.0",
    "updated_at": "2025-11-23T11:00:00Z",
    "message": "Strategy updated successfully"
  }
}
```

---

### 6.5 Delete Strategy

Delete a strategy.

**Endpoint:** `DELETE /strategies/{strategy_id}`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "message": "Strategy deleted successfully"
  }
}
```

**Errors:**
- `404 Not Found`: Strategy not found
- `409 Conflict`: Cannot delete strategy with active backtests/trades

---

### 6.6 Validate Strategy

Validate strategy parameters and rules.

**Endpoint:** `POST /strategies/{strategy_id}/validate`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "is_valid": true,
    "validation_results": {
      "parameters": "valid",
      "entry_rules": "valid",
      "exit_rules": "valid",
      "indicators": "valid"
    },
    "warnings": []
  }
}
```

**If Invalid:**
```json
{
  "status": "success",
  "data": {
    "is_valid": false,
    "validation_results": {
      "parameters": "invalid"
    },
    "errors": [
      "fast_ma must be less than slow_ma"
    ],
    "warnings": [
      "RSI period should be between 2 and 30 for best results"
    ]
  }
}
```

---

### 6.7 Get Strategy Versions

List all versions of a strategy.

**Endpoint:** `GET /strategies/{strategy_id}/versions`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "strategy_id": "strat_abc123",
    "versions": [
      {
        "version": "1.0.0",
        "created_at": "2025-10-15T10:00:00Z",
        "changes": "Initial version"
      },
      {
        "version": "1.1.0",
        "created_at": "2025-11-23T11:00:00Z",
        "changes": "Updated MA periods"
      }
    ]
  }
}
```

---

## 7. Backtesting Endpoints

### 7.1 Run Backtest

Execute a backtest for a strategy.

**Endpoint:** `POST /backtests`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "strategy_id": "strat_abc123",
  "symbols": ["BTCUSDT"],
  "timeframe": "1h",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2025-11-23T23:59:59Z",
  "initial_capital": 10000,
  "commission": 0.001,
  "slippage": 0.0005,
  "mode": "event_driven"
}
```

**Response:** `202 Accepted`
```json
{
  "status": "success",
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "running",
    "estimated_time": 30,
    "message": "Backtest queued for execution"
  }
}
```

**Errors:**
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Strategy not found
- `422 Unprocessable Entity`: Insufficient data for date range

---

### 7.2 Get Backtest Status

Check the status of a running backtest.

**Endpoint:** `GET /backtests/{backtest_id}/status`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "running",
    "progress": 45,
    "bars_processed": 4500,
    "total_bars": 10000,
    "elapsed_time": 15,
    "estimated_remaining": 18
  }
}
```

**Possible status values:**
- `queued`: Waiting to start
- `running`: Currently executing
- `completed`: Successfully finished
- `failed`: Error occurred
- `cancelled`: Cancelled by user

---

### 7.3 Get Backtest Results

Retrieve results of a completed backtest.

**Endpoint:** `GET /backtests/{backtest_id}/results`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "backtest_id": "bt_xyz789",
    "strategy_id": "strat_abc123",
    "status": "completed",
    "configuration": {
      "symbols": ["BTCUSDT"],
      "timeframe": "1h",
      "start_date": "2024-01-01T00:00:00Z",
      "end_date": "2025-11-23T23:59:59Z",
      "initial_capital": 10000
    },
    "metrics": {
      "total_return": 0.2345,
      "annualized_return": 0.2567,
      "sharpe_ratio": 1.87,
      "sortino_ratio": 2.15,
      "max_drawdown": -0.0821,
      "max_drawdown_duration": 45,
      "win_rate": 0.654,
      "total_trades": 156,
      "winning_trades": 102,
      "losing_trades": 54,
      "avg_win": 125.50,
      "avg_loss": -78.30,
      "largest_win": 450.00,
      "largest_loss": -220.00,
      "expectancy": 1.52,
      "calmar_ratio": 2.85,
      "volatility": 0.1234
    },
    "completed_at": "2025-11-23T10:35:23Z",
    "execution_time": 32.5
  }
}
```

**Errors:**
- `404 Not Found`: Backtest not found
- `425 Too Early`: Backtest not yet completed

---

### 7.4 Get Backtest Trades

Retrieve all trades from a backtest.

**Endpoint:** `GET /backtests/{backtest_id}/trades`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `page` (optional): Page number
- `page_size` (optional): Items per page (default: 100)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "backtest_id": "bt_xyz789",
    "trades": [
      {
        "id": 1,
        "symbol": "BTCUSDT",
        "direction": "long",
        "entry_time": "2024-01-15T10:00:00Z",
        "exit_time": "2024-01-15T18:00:00Z",
        "entry_price": 42500.00,
        "exit_price": 42850.00,
        "quantity": 0.5,
        "pnl": 175.00,
        "pnl_percent": 0.0082,
        "commission": 21.35,
        "exit_reason": "take_profit"
      },
      {
        "id": 2,
        "symbol": "BTCUSDT",
        "direction": "short",
        "entry_time": "2024-01-16T14:00:00Z",
        "exit_time": "2024-01-16T20:00:00Z",
        "entry_price": 43100.00,
        "exit_price": 43300.00,
        "quantity": 0.5,
        "pnl": -100.00,
        "pnl_percent": -0.0046,
        "commission": 21.60,
        "exit_reason": "stop_loss"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 100,
      "total_items": 156,
      "total_pages": 2
    }
  }
}
```

---

### 7.5 Get Equity Curve

Get equity curve data for visualization.

**Endpoint:** `GET /backtests/{backtest_id}/equity`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "backtest_id": "bt_xyz789",
    "equity_curve": [
      {
        "timestamp": "2024-01-01T00:00:00Z",
        "equity": 10000.00,
        "cash": 10000.00,
        "positions_value": 0.00
      },
      {
        "timestamp": "2024-01-02T00:00:00Z",
        "equity": 10150.00,
        "cash": 5000.00,
        "positions_value": 5150.00
      }
    ]
  }
}
```

---

### 7.6 Cancel Backtest

Cancel a running backtest.

**Endpoint:** `POST /backtests/{backtest_id}/cancel`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "cancelled",
    "message": "Backtest cancelled successfully"
  }
}
```

---

### 7.7 Delete Backtest

Delete a backtest and its results.

**Endpoint:** `DELETE /backtests/{backtest_id}`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "message": "Backtest deleted successfully"
  }
}
```

---

### 7.8 Compare Backtests

Compare multiple backtest results.

**Endpoint:** `GET /backtests/compare`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `ids` (required): Comma-separated backtest IDs

**Example:**
```
GET /backtests/compare?ids=bt_abc123,bt_def456,bt_ghi789
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "comparison": [
      {
        "backtest_id": "bt_abc123",
        "strategy_name": "MA Crossover",
        "total_return": 0.2345,
        "sharpe_ratio": 1.87,
        "max_drawdown": -0.0821,
        "total_trades": 156
      },
      {
        "backtest_id": "bt_def456",
        "strategy_name": "RSI Mean Reversion",
        "total_return": 0.1892,
        "sharpe_ratio": 1.65,
        "max_drawdown": -0.0654,
        "total_trades": 203
      }
    ]
  }
}
```

---

## 8. Optimization Endpoints

### 8.1 Start Optimization

Start parameter optimization for a strategy.

**Endpoint:** `POST /optimization/runs`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "strategy_id": "strat_abc123",
  "parameter_grid": {
    "fast_ma": [10, 15, 20, 25],
    "slow_ma": [50, 75, 100],
    "rsi_period": [14, 21]
  },
  "optimization_metric": "sharpe_ratio",
  "backtest_config": {
    "symbols": ["BTCUSDT"],
    "timeframe": "1h",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2025-11-23T23:59:59Z",
    "initial_capital": 10000
  },
  "n_jobs": 4
}
```

**Response:** `202 Accepted`
```json
{
  "status": "success",
  "data": {
    "run_id": "opt_xyz789",
    "status": "running",
    "total_combinations": 24,
    "estimated_time": 180,
    "message": "Optimization started"
  }
}
```

---

### 8.2 Get Optimization Status

Check optimization progress.

**Endpoint:** `GET /optimization/runs/{run_id}/status`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "run_id": "opt_xyz789",
    "status": "running",
    "progress": 62,
    "completed_combinations": 15,
    "total_combinations": 24,
    "elapsed_time": 95,
    "estimated_remaining": 58,
    "best_so_far": {
      "parameters": {"fast_ma": 15, "slow_ma": 75, "rsi_period": 14},
      "metric_value": 2.15
    }
  }
}
```

---

### 8.3 Get Optimization Results

Retrieve optimization results.

**Endpoint:** `GET /optimization/runs/{run_id}/results`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `top_n` (optional): Return only top N results (default: all)
- `sort_by` (optional): Sort field (default: metric_value)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "run_id": "opt_xyz789",
    "strategy_id": "strat_abc123",
    "optimization_metric": "sharpe_ratio",
    "status": "completed",
    "total_combinations": 24,
    "results": [
      {
        "rank": 1,
        "parameters": {
          "fast_ma": 15,
          "slow_ma": 75,
          "rsi_period": 14
        },
        "metric_value": 2.15,
        "additional_metrics": {
          "total_return": 0.2845,
          "max_drawdown": -0.0654,
          "win_rate": 0.682
        }
      },
      {
        "rank": 2,
        "parameters": {
          "fast_ma": 20,
          "slow_ma": 50,
          "rsi_period": 21
        },
        "metric_value": 1.98,
        "additional_metrics": {
          "total_return": 0.2567,
          "max_drawdown": -0.0721,
          "win_rate": 0.654
        }
      }
    ],
    "completed_at": "2025-11-23T12:15:30Z"
  }
}
```

---

### 8.4 Get Best Parameters

Get the best parameters from optimization.

**Endpoint:** `GET /optimization/runs/{run_id}/best`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "run_id": "opt_xyz789",
    "best_parameters": {
      "fast_ma": 15,
      "slow_ma": 75,
      "rsi_period": 14
    },
    "metric_value": 2.15,
    "all_metrics": {
      "total_return": 0.2845,
      "sharpe_ratio": 2.15,
      "sortino_ratio": 2.58,
      "max_drawdown": -0.0654,
      "win_rate": 0.682,
      "total_trades": 178
    }
  }
}
```

---

### 8.5 Cancel Optimization

Cancel a running optimization.

**Endpoint:** `POST /optimization/runs/{run_id}/cancel`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "run_id": "opt_xyz789",
    "status": "cancelled",
    "completed_combinations": 15,
    "total_combinations": 24,
    "message": "Optimization cancelled"
  }
}
```

---

## 9. Live Trading Endpoints

### 9.1 Start Strategy

Start a strategy for live trading.

**Endpoint:** `POST /trading/strategies/{strategy_id}/start`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "symbols": ["BTCUSDT"],
  "paper_trading": true,
  "risk_limits": {
    "max_position_size": 0.1,
    "max_portfolio_exposure": 0.5,
    "max_drawdown": 0.15
  },
  "notifications": {
    "telegram": true,
    "email": true
  }
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "strategy_id": "strat_abc123",
    "execution_id": "exec_xyz789",
    "status": "running",
    "mode": "paper",
    "symbols": ["BTCUSDT"],
    "started_at": "2025-11-23T10:00:00Z"
  }
}
```

**Errors:**
- `400 Bad Request`: Invalid configuration
- `409 Conflict`: Strategy already running

---

### 9.2 Stop Strategy

Stop a running strategy.

**Endpoint:** `POST /trading/strategies/{strategy_id}/stop`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `close_positions` (optional): Whether to close open positions (default: false)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "strategy_id": "strat_abc123",
    "status": "stopped",
    "stopped_at": "2025-11-23T15:30:00Z",
    "open_positions_closed": 2,
    "message": "Strategy stopped successfully"
  }
}
```

---

### 9.3 Get Strategy Status

Get real-time status of a running strategy.

**Endpoint:** `GET /trading/strategies/{strategy_id}/status`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "strategy_id": "strat_abc123",
    "execution_id": "exec_xyz789",
    "status": "running",
    "mode": "paper",
    "started_at": "2025-11-23T10:00:00Z",
    "uptime_seconds": 19800,
    "symbols": ["BTCUSDT"],
    "current_positions": 1,
    "total_trades": 15,
    "current_equity": 10450.00,
    "unrealized_pnl": 125.50,
    "realized_pnl": 325.50,
    "last_signal_time": "2025-11-23T15:25:00Z"
  }
}
```

---

### 9.4 List Active Strategies

Get all currently running strategies.

**Endpoint:** `GET /trading/strategies/active`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "active_strategies": [
      {
        "strategy_id": "strat_abc123",
        "name": "MA Crossover",
        "status": "running",
        "mode": "paper",
        "symbols": ["BTCUSDT"],
        "current_equity": 10450.00,
        "pnl": 450.00,
        "uptime": "5h 30m"
      }
    ]
  }
}
```

---

### 9.5 Get Positions

Get all current open positions.

**Endpoint:** `GET /trading/positions`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `strategy_id` (optional): Filter by strategy
- `symbol` (optional): Filter by symbol

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "positions": [
      {
        "id": "pos_abc123",
        "strategy_id": "strat_abc123",
        "symbol": "BTCUSDT",
        "type": "long",
        "entry_price": 37250.00,
        "current_price": 37485.50,
        "quantity": 0.5,
        "unrealized_pnl": 117.75,
        "unrealized_pnl_percent": 0.0063,
        "opened_at": "2025-11-23T14:30:00Z",
        "duration": "1h 5m"
      }
    ],
    "summary": {
      "total_positions": 1,
      "total_exposure": 18742.75,
      "total_unrealized_pnl": 117.75
    }
  }
}
```

---

### 9.6 Get Position Details

Get detailed information about a specific position.

**Endpoint:** `GET /trading/positions/{position_id}`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "id": "pos_abc123",
    "strategy_id": "strat_abc123",
    "strategy_name": "MA Crossover",
    "symbol": "BTCUSDT",
    "type": "long",
    "entry_price": 37250.00,
    "current_price": 37485.50,
    "quantity": 0.5,
    "unrealized_pnl": 117.75,
    "unrealized_pnl_percent": 0.0063,
    "stop_loss": 36850.00,
    "take_profit": 37950.00,
    "opened_at": "2025-11-23T14:30:00Z",
    "duration_seconds": 3900
  }
}
```

---

### 9.7 Close Position

Manually close an open position.

**Endpoint:** `POST /trading/positions/{position_id}/close`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "position_id": "pos_abc123",
    "symbol": "BTCUSDT",
    "exit_price": 37485.50,
    "realized_pnl": 117.75,
    "closed_at": "2025-11-23T15:35:00Z",
    "message": "Position closed successfully"
  }
}
```

---

### 9.8 Get Orders

Get all orders (pending and filled).

**Endpoint:** `GET /trading/orders`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `strategy_id` (optional): Filter by strategy
- `status` (optional): Filter by status (pending, filled, cancelled)
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "orders": [
      {
        "id": "ord_abc123",
        "strategy_id": "strat_abc123",
        "symbol": "BTCUSDT",
        "type": "market",
        "side": "buy",
        "quantity": 0.5,
        "price": null,
        "status": "filled",
        "filled_price": 37250.00,
        "created_at": "2025-11-23T14:30:00Z",
        "filled_at": "2025-11-23T14:30:01Z"
      },
      {
        "id": "ord_def456",
        "strategy_id": "strat_abc123",
        "symbol": "BTCUSDT",
        "type": "limit",
        "side": "sell",
        "quantity": 0.5,
        "price": 37950.00,
        "status": "pending",
        "created_at": "2025-11-23T14:30:02Z"
      }
    ]
  }
}
```

---

### 9.9 Create Order

Manually create an order (for manual trading).

**Endpoint:** `POST /trading/orders`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "symbol": "BTCUSDT",
  "type": "limit",
  "side": "buy",
  "quantity": 0.5,
  "price": 37000.00,
  "stop_price": null,
  "time_in_force": "GTC"
}
```

**Response:** `201 Created`
```json
{
  "status": "success",
  "data": {
    "order_id": "ord_xyz789",
    "symbol": "BTCUSDT",
    "type": "limit",
    "side": "buy",
    "quantity": 0.5,
    "price": 37000.00,
    "status": "pending",
    "created_at": "2025-11-23T15:40:00Z",
    "message": "Order created successfully"
  }
}
```

---

### 9.10 Cancel Order

Cancel a pending order.

**Endpoint:** `DELETE /trading/orders/{order_id}`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "order_id": "ord_xyz789",
    "status": "cancelled",
    "cancelled_at": "2025-11-23T15:45:00Z",
    "message": "Order cancelled successfully"
  }
}
```

---

### 9.11 Emergency Stop

Emergency stop all trading activities.

**Endpoint:** `POST /trading/emergency-stop`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "close_all_positions": true,
  "cancel_all_orders": true,
  "reason": "Manual emergency stop"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "stopped_strategies": 3,
    "cancelled_orders": 5,
    "closed_positions": 2,
    "timestamp": "2025-11-23T15:50:00Z",
    "message": "Emergency stop executed successfully"
  }
}
```

---

## 10. Risk Management Endpoints

### 10.1 Get Risk Limits

Get current risk limits configuration.

**Endpoint:** `GET /risk/limits`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "limits": {
      "max_position_size": 0.1,
      "max_portfolio_exposure": 0.5,
      "max_drawdown": 0.15,
      "max_daily_trades": 50,
      "max_daily_loss": 0.05
    },
    "current_utilization": {
      "portfolio_exposure": 0.25,
      "current_drawdown": 0.03,
      "daily_trades": 15,
      "daily_loss": 0.01
    }
  }
}
```

---

### 10.2 Update Risk Limits

Update risk limits configuration.

**Endpoint:** `PUT /risk/limits`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "max_position_size": 0.15,
  "max_portfolio_exposure": 0.6,
  "max_drawdown": 0.20,
  "max_daily_trades": 75
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "limits": {
      "max_position_size": 0.15,
      "max_portfolio_exposure": 0.6,
      "max_drawdown": 0.20,
      "max_daily_trades": 75
    },
    "updated_at": "2025-11-23T16:00:00Z",
    "message": "Risk limits updated successfully"
  }
}
```

---

### 10.3 Get Current Exposure

Get current portfolio exposure.

**Endpoint:** `GET /risk/exposure`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "total_exposure": 25000.00,
    "total_equity": 50000.00,
    "exposure_percent": 0.50,
    "by_symbol": [
      {
        "symbol": "BTCUSDT",
        "exposure": 15000.00,
        "percent_of_portfolio": 0.30
      },
      {
        "symbol": "ETHUSDT",
        "exposure": 10000.00,
        "percent_of_portfolio": 0.20
      }
    ],
    "by_strategy": [
      {
        "strategy_id": "strat_abc123",
        "strategy_name": "MA Crossover",
        "exposure": 18000.00,
        "percent_of_portfolio": 0.36
      }
    ]
  }
}
```

---

### 10.4 Get Risk Metrics

Get comprehensive risk metrics.

**Endpoint:** `GET /risk/metrics`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "current_drawdown": 0.03,
    "max_drawdown": 0.08,
    "volatility": 0.15,
    "sharpe_ratio": 1.85,
    "var_95": -250.00,
    "var_99": -450.00,
    "position_correlation": 0.65,
    "portfolio_beta": 1.12
  }
}
```

---

### 10.5 Calculate VaR

Calculate Value at Risk for current portfolio.

**Endpoint:** `GET /risk/var`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `confidence_level` (optional): Confidence level (default: 0.95)
- `time_horizon` (optional): Time horizon in days (default: 1)
- `method` (optional): Calculation method (historical, parametric, monte_carlo)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "var_95": -250.00,
    "var_99": -450.00,
    "cvar_95": -320.00,
    "cvar_99": -550.00,
    "method": "historical",
    "confidence_level": 0.95,
    "time_horizon": 1,
    "calculated_at": "2025-11-23T16:15:00Z"
  }
}
```

---

### 10.6 Check Risk

Check if a proposed trade passes risk checks.

**Endpoint:** `POST /risk/check`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "symbol": "BTCUSDT",
  "side": "buy",
  "quantity": 0.5,
  "price": 37500.00
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "approved": true,
    "checks": {
      "position_size": "passed",
      "portfolio_exposure": "passed",
      "drawdown_limit": "passed",
      "daily_trades": "passed",
      "correlation": "passed"
    },
    "warnings": [],
    "recommended_quantity": 0.5
  }
}
```

**If Risk Check Fails:**
```json
{
  "status": "success",
  "data": {
    "approved": false,
    "checks": {
      "position_size": "passed",
      "portfolio_exposure": "failed",
      "drawdown_limit": "passed"
    },
    "errors": [
      "Trade would exceed max portfolio exposure (60% > 50%)"
    ],
    "recommended_quantity": 0.35
  }
}
```

---

## 11. Analytics Endpoints

### 11.1 Get Equity Curve

Get equity curve for a strategy or portfolio.

**Endpoint:** `GET /analytics/equity-curve`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `strategy_id` (optional): Specific strategy
- `start_date` (optional): Start date
- `end_date` (optional): End date
- `resolution` (optional): Data resolution (1h, 1d, 1w)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "equity_curve": [
      {
        "timestamp": "2025-11-01T00:00:00Z",
        "equity": 10000.00
      },
      {
        "timestamp": "2025-11-02T00:00:00Z",
        "equity": 10150.00
      }
    ],
    "summary": {
      "initial_equity": 10000.00,
      "final_equity": 12345.00,
      "peak_equity": 12850.00,
      "total_return": 0.2345
    }
  }
}
```

---

### 11.2 Get Drawdown

Get drawdown data.

**Endpoint:** `GET /analytics/drawdown`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "drawdown_series": [
      {
        "timestamp": "2025-11-01T00:00:00Z",
        "drawdown": 0.00
      },
      {
        "timestamp": "2025-11-15T00:00:00Z",
        "drawdown": -0.08
      }
    ],
    "max_drawdown": -0.08,
    "max_drawdown_start": "2025-11-10T00:00:00Z",
    "max_drawdown_end": "2025-11-18T00:00:00Z",
    "max_drawdown_duration": 8
  }
}
```

---

### 11.3 Get Returns Distribution

Get distribution of returns.

**Endpoint:** `GET /analytics/returns`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `period` (optional): Return period (daily, weekly, monthly)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "daily_returns": {
      "mean": 0.0012,
      "median": 0.0008,
      "std_dev": 0.0234,
      "skewness": 0.15,
      "kurtosis": 3.2,
      "min": -0.08,
      "max": 0.12
    },
    "distribution": [
      {"bin": -0.08, "count": 2},
      {"bin": -0.06, "count": 5},
      {"bin": -0.04, "count": 12}
    ]
  }
}
```

---

### 11.4 Get Trade Analysis

Get detailed trade statistics.

**Endpoint:** `GET /analytics/trades`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `strategy_id` (optional): Filter by strategy
- `start_date` (optional): Start date
- `end_date` (optional): End date

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "total_trades": 156,
    "winning_trades": 102,
    "losing_trades": 54,
    "win_rate": 0.654,
    "avg_win": 125.50,
    "avg_loss": -78.30,
    "largest_win": 450.00,
    "largest_loss": -220.00,
    "avg_holding_period": "8h 45m",
    "profit_factor": 1.85,
    "expectancy": 52.30,
    "by_day_of_week": {
      "Monday": {"trades": 28, "win_rate": 0.67},
      "Tuesday": {"trades": 32, "win_rate": 0.62}
    }
  }
}
```

---

### 11.5 Get Performance Metrics

Get comprehensive performance metrics.

**Endpoint:** `GET /analytics/metrics/{strategy_id}`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "strategy_id": "strat_abc123",
    "period": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2025-11-23T23:59:59Z"
    },
    "returns": {
      "total_return": 0.2345,
      "annualized_return": 0.2567,
      "cagr": 0.2489
    },
    "risk_adjusted": {
      "sharpe_ratio": 1.87,
      "sortino_ratio": 2.15,
      "calmar_ratio": 2.85,
      "omega_ratio": 1.52
    },
    "risk": {
      "max_drawdown": -0.0821,
      "volatility": 0.1234,
      "downside_deviation": 0.0876,
      "var_95": -250.00
    },
    "trades": {
      "total": 156,
      "win_rate": 0.654,
      "profit_factor": 1.85,
      "expectancy": 52.30
    }
  }
}
```

---

## 12. System Endpoints

### 12.1 Health Check

Check if the API is running.

**Endpoint:** `GET /system/health`

**Headers:** None required

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T10:00:00Z",
  "version": "1.0.0"
}
```

---

### 12.2 System Status

Get detailed system status.

**Endpoint:** `GET /system/status`

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "api_version": "1.0.0",
    "uptime_seconds": 3600000,
    "services": {
      "database": {
        "status": "up",
        "latency_ms": 5
      },
      "redis": {
        "status": "up",
        "latency_ms": 1
      },
      "mt5_broker": {
        "status": "up",
        "latency_ms": 45
      }
    },
    "active_strategies": 3,
    "active_backtests": 1,
    "active_optimizations": 0,
    "system_metrics": {
      "cpu_percent": 45.2,
      "memory_percent": 62.5,
      "disk_percent": 38.7
    }
  }
}
```

---

### 12.3 Get Logs

Retrieve system logs.

**Endpoint:** `GET /system/logs`

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
- `level` (optional): Filter by level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `module` (optional): Filter by module
- `start_date` (optional): Start date
- `limit` (optional): Number of logs to return (default: 100)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "logs": [
      {
        "timestamp": "2025-11-23T10:15:30Z",
        "level": "INFO",
        "module": "trading",
        "message": "Strategy strat_abc123 started successfully"
      },
      {
        "timestamp": "2025-11-23T10:16:45Z",
        "level": "WARNING",
        "module": "risk",
        "message": "Position size near limit: 95% of max"
      }
    ]
  }
}
```

---

### 12.4 Get Configuration

Get system configuration (non-sensitive values only).

**Endpoint:** `GET /system/config`

**Description:**
Returns application configuration values loaded via Pydantic settings (environment, database url, redis url, api host/port). Sensitive fields (passwords, secrets) are omitted or masked.

**Response:**
```json
{
  "environment": "dev",
  "database_url": "sqlite:///path/to/db",
  "redis_url": "redis://localhost:6379/0",
  "api_host": "0.0.0.0",
  "api_port": 8000
}
```

### 12.5 Get Logging Status

Retrieve logging configuration and status.

**Endpoint:** `GET /system/logging`

**Description:**
Returns current log level and log file locations configured in `app/logger`.

**Response:**
```json
{
  "level": "INFO",
  "log_dir": "logs",
  "files": ["logs/app.log", "logs/error.log"]
}
```

### 12.6 Get Database Status

Check database connectivity.

**Endpoint:** `GET /system/database`

**Response:**
```json
{
  "status": "ok",
  "url": "sqlite:///path/to/db"
}
```

### 12.7 Get Redis Status

Check Redis connectivity.

**Endpoint:** `GET /system/redis`

**Response:**
```json
{
  "status": "ok",
  "url": "redis://localhost:6379/0"
}
```

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "api_version": "1.0.0",
    "environment": "production",
    "features": {
      "backtesting": true,
      "optimization": true,
      "live_trading": true,
      "paper_trading": true
    },
    "limits": {
      "max_concurrent_backtests": 20,
      "max_strategies": 50,
      "max_symbols": 30
    },
    "supported_brokers": ["mt5", "dukascopy"],
    "supported_asset_classes": ["forex", "crypto", "stocks", "futures"]
  }
}
```

---

## 13. WebSocket API

### 13.1 WebSocket Overview

The WebSocket API provides real-time streaming data for:
- Live tick data
- Bar updates
- Position changes
- Order updates
- Notifications

**WebSocket URL:** `ws://localhost:8000/ws`

### 13.2 Connection

**Connect to WebSocket:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('Connected');
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'YOUR_ACCESS_TOKEN'
  }));
};
```

### 13.3 Authentication

After connecting, send authentication message:

```json
{
  "type": "auth",
  "token": "YOUR_ACCESS_TOKEN"
}
```

**Success Response:**
```json
{
  "type": "auth_success",
  "message": "Authentication successful"
}
```

**Error Response:**
```json
{
  "type": "auth_error",
  "message": "Invalid token"
}
```

### 13.4 Subscribe to Ticks

Subscribe to real-time tick data for symbols.

**Subscribe Message:**
```json
{
  "type": "subscribe",
  "channel": "ticks",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

**Subscription Confirmation:**
```json
{
  "type": "subscribed",
  "channel": "ticks",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

**Tick Data Stream:**
```json
{
  "type": "tick",
  "symbol": "BTCUSDT",
  "data": {
    "timestamp": "2025-11-23T10:00:01.234Z",
    "bid": 37245.50,
    "ask": 37246.00,
    "volume": 1.25
  }
}
```

### 13.5 Subscribe to Bars

Subscribe to bar updates.

**Subscribe Message:**
```json
{
  "type": "subscribe",
  "channel": "bars",
  "symbols": ["BTCUSDT"],
  "timeframe": "1m"
}
```

**Bar Data Stream:**
```json
{
  "type": "bar",
  "symbol": "BTCUSDT",
  "timeframe": "1m",
  "data": {
    "timestamp": "2025-11-23T10:01:00Z",
    "open": 37245.50,
    "high": 37250.00,
    "low": 37240.00,
    "close": 37248.50,
    "volume": 15.67,
    "spread": 0.5
  }
}
```

### 13.6 Subscribe to Positions

Subscribe to position updates.

**Subscribe Message:**
```json
{
  "type": "subscribe",
  "channel": "positions"
}
```

**Position Update Stream:**
```json
{
  "type": "position_update",
  "event": "opened",
  "data": {
    "id": "pos_abc123",
    "symbol": "BTCUSDT",
    "type": "long",
    "entry_price": 37245.50,
    "quantity": 0.5,
    "timestamp": "2025-11-23T10:01:15Z"
  }
}
```

**Position Closed:**
```json
{
  "type": "position_update",
  "event": "closed",
  "data": {
    "id": "pos_abc123",
    "symbol": "BTCUSDT",
    "exit_price": 37485.50,
    "realized_pnl": 120.00,
    "timestamp": "2025-11-23T11:30:00Z"
  }
}
```

### 13.7 Subscribe to Orders

Subscribe to order updates.

**Subscribe Message:**
```json
{
  "type": "subscribe",
  "channel": "orders"
}
```

**Order Update Stream:**
```json
{
  "type": "order_update",
  "event": "filled",
  "data": {
    "id": "ord_abc123",
    "symbol": "BTCUSDT",
    "type": "market",
    "side": "buy",
    "quantity": 0.5,
    "filled_price": 37245.50,
    "timestamp": "2025-11-23T10:01:15Z"
  }
}
```

### 13.8 Subscribe to Notifications

Subscribe to system notifications.

**Subscribe Message:**
```json
{
  "type": "subscribe",
  "channel": "notifications"
}
```

**Notification Stream:**
```json
{
  "type": "notification",
  "priority": "high",
  "title": "Risk Limit Warning",
  "message": "Portfolio exposure reached 90% of limit",
  "timestamp": "2025-11-23T10:15:00Z"
}
```

### 13.9 Unsubscribe

Unsubscribe from a channel.

**Unsubscribe Message:**
```json
{
  "type": "unsubscribe",
  "channel": "ticks",
  "symbols": ["BTCUSDT"]
}
```

**Confirmation:**
```json
{
  "type": "unsubscribed",
  "channel": "ticks",
  "symbols": ["BTCUSDT"]
}
```

### 13.10 Heartbeat

The server sends periodic heartbeat messages:

```json
{
  "type": "heartbeat",
  "timestamp": "2025-11-23T10:00:00Z"
}
```

Clients should respond with:

```json
{
  "type": "pong"
}
```

---

## 14. Error Handling

### 14.1 Error Response Format

All errors follow a consistent format:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional error details
    }
  },
  "metadata": {
    "timestamp": "2025-11-23T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### 14.2 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing authentication |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `BROKER_ERROR` | 500 | Broker API error |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### 14.3 Validation Errors

Validation errors include field-specific details:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "errors": [
        {
          "field": "symbol",
          "message": "symbol is required",
          "constraint": "required"
        },
        {
          "field": "quantity",
          "message": "quantity must be greater than 0",
          "constraint": "min_value",
          "min": 0
        }
      ]
    }
  }
}
```

### 14.4 Error Handling Best Practices

**Client-Side Error Handling:**

```python
try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    result = response.json()

    if result.get('status') == 'error':
        error = result['error']
        print(f"Error: {error['code']} - {error['message']}")
        if 'details' in error:
            print(f"Details: {error['details']}")
    else:
        # Process successful response
        pass

except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e.response.status_code}")
    print(e.response.json())

except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

---

## 15. Rate Limiting

### 15.1 Rate Limit Rules

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Data Downloads | 60 requests | 1 hour |
| Backtests | 20 concurrent | - |
| API Calls (General) | 1000 requests | 1 hour |
| WebSocket Connections | 10 concurrent | - |

### 15.2 Rate Limit Headers

Responses include rate limit information in headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1700740800
```

### 15.3 Rate Limit Exceeded Response

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "limit": 1000,
      "window": "1 hour",
      "retry_after": 180
    }
  }
}
```

### 15.4 Best Practices

- Implement exponential backoff for retries
- Cache responses when appropriate
- Use WebSocket for real-time data instead of polling
- Batch requests when possible

---

## 16. Appendices

### Appendix A: Complete Example Workflow

**Full Workflow: From Data to Live Trading**

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# 1. Authenticate
auth_response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "trader",
    "password": "password"
})
token = auth_response.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Download Historical Data
download_response = requests.post(f"{BASE_URL}/data/download",
    headers=headers,
    json={
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2025-11-23T23:59:59Z",
        "provider": "mt5"
    }
)
job_id = download_response.json()["data"]["job_id"]

# Wait for download to complete
while True:
    status = requests.get(f"{BASE_URL}/data/download/{job_id}/status",
                         headers=headers).json()
    if status["data"]["status"] == "completed":
        break
    time.sleep(5)

# 3. Create Strategy
strategy_response = requests.post(f"{BASE_URL}/strategies",
    headers=headers,
    json={
        "name": "MA Crossover",
        "parameters": {"fast_ma": 20, "slow_ma": 50},
        "entry_rules": {"long": "fast_ma > slow_ma"},
        "exit_rules": {"take_profit": 2.0, "stop_loss": 1.0}
    }
)
strategy_id = strategy_response.json()["data"]["id"]

# 4. Run Backtest
backtest_response = requests.post(f"{BASE_URL}/backtests",
    headers=headers,
    json={
        "strategy_id": strategy_id,
        "symbols": ["BTCUSDT"],
        "timeframe": "1h",
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2025-11-23T23:59:59Z",
        "initial_capital": 10000
    }
)
backtest_id = backtest_response.json()["data"]["backtest_id"]

# Wait for backtest to complete
while True:
    status = requests.get(f"{BASE_URL}/backtests/{backtest_id}/status",
                         headers=headers).json()
    if status["data"]["status"] == "completed":
        break
    time.sleep(2)

# 5. Get Results
results = requests.get(f"{BASE_URL}/backtests/{backtest_id}/results",
                      headers=headers).json()
print(f"Sharpe Ratio: {results['data']['metrics']['sharpe_ratio']}")

# 6. Start Paper Trading
trading_response = requests.post(
    f"{BASE_URL}/trading/strategies/{strategy_id}/start",
    headers=headers,
    json={
        "symbols": ["BTCUSDT"],
        "paper_trading": True,
        "risk_limits": {"max_position_size": 0.1}
    }
)
print("Paper trading started!")
```

### Appendix B: Postman Collection

A Postman collection with all API endpoints is available for download.

### Appendix C: SDK Support

**Python SDK (Coming Soon):**
```python
from trading_system import TradingSystemAPI

api = TradingSystemAPI(api_key="your_key")
strategies = api.strategies.list()
backtest = api.backtests.run(strategy_id="strat_123", symbols=["BTCUSDT"])
```

### Appendix D: Changelog

**Version 1.0.0 (2025-11-23)**
- Initial API release
- All core endpoints implemented
- WebSocket support for real-time data
- Authentication and authorization
- Rate limiting

---

**End of API Documentation**

For questions, issues, or feature requests, please contact the development team or file an issue in the project repository.

**API Version:** 1.0.0
**Documentation Updated:** November 23, 2025
