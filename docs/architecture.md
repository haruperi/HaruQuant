# Architecture Overview

This document describes the current HaruQuant application architecture based on the code in `apps/`.

## High-Level Layout
- `apps/api`: FastAPI application, routing, auth utilities, logging configuration, and WebSocket managers.
- `apps/sqlite`: Database access layer used by the API and background tasks via `DatabaseManager`.
- `apps/strategy`: Strategy storage and loading utilities for versioned strategy code.
- `apps/backtest`: Backtest engines and persistence layer (`BacktestDatabase`) used by strategy routes.
- `apps/live`: Live trading session orchestration used by live-trading routes.
- `apps/mt5`: MetaTrader 5 client/data access used by broker, live, and backtest flows.
- `apps/ctrade`: MT5-specific trade classes aligned to the MQL5 Standard Library (`CSymbolInfo`, `CAccountInfo`, `COrderInfo`, `CHistoryOrderInfo`, `CPositionInfo`, `CDealInfo`, `CTrade`, `CTerminalInfo`).
- `apps/simulator`: MT5-aligned local trade simulator for positions, validation, and P/L calculations (no live orders), plus tester-mode MT5 overloads, MT5-like order_send handling, a disk-backed market data store for bars/ticks, and a tester runner for real/simulated tick modelling.
- `apps/optimization`: Optimization tasks and models used by optimization routes.
- `apps/edge`: Edge Lab statistical edge discovery toolkit used by edge-lab routes.
- `apps/edge/seasonality.py`: Seasonality analytics engine that aggregates intraday, weekly, and calendar stats.
- `apps/utils`: Shared helpers (data loading, validation, security).

## API Layer
The FastAPI app is defined in `apps/api/main.py`. It registers route modules for:
- Auth (`apps/api/routes/auth.py`)
- Settings (`apps/api/routes/settings.py`)
- System status/resources (`apps/api/routes/system.py`)
- Strategies and backtests (`apps/api/routes/strategies.py`)
- Broker status (`apps/api/routes/broker.py`)
- Market hours (`apps/api/routes/market_hours.py`)
- Trades and chart data (`apps/api/routes/trades.py`)
- Live trading (`apps/api/routes/live.py`, currently disabled in `apps/api/main.py`)
- Data ingestion/preview (`apps/api/routes/data.py`)
- Optimization (`apps/api/routes/optimization.py`)
- Docs management (`apps/api/routes/docs.py`)
- Edge Lab (`apps/api/routes/edge.py`)
  - Seasonality analytics (`POST /api/edge-lab/seasonality`)
- Performance reports (`apps/api/routes/reports/*`)
  - Strategy performance summaries (`POST /api/reports/strategy-performance-quick`, `POST /api/reports/strategy-performance-summary`)
  - Strategy performance distributions (`POST /api/reports/strategy-performance-distributions`)

## Authentication
`apps/api/auth_utils.py` implements file-backed token storage in `data/tokens.json`, token generation/verification, and user authentication via `DatabaseManager`.

## WebSocket Layer
`apps/api/websocket.py` provides three managers:
- `BacktestLogManager` for streaming backtest logs.
- `LiveTradingManager` for live trading updates with channel subscriptions.
- `OptimizationProgressManager` for optimization progress updates.

Routes in `apps/api/routes/strategies.py`, `apps/api/routes/live.py`, and `apps/api/routes/optimization.py` expose WebSocket endpoints that use these managers.

## Data Ingestion
`apps/api/routes/data.py` runs an ingest pipeline:
1. Load market data from MT5 or Dukascopy (`apps/utils/data_getters.py`).
2. Validate using `DataValidator`.
3. Save raw data to parquet under `data/raw`.
4. Store metadata via `DatabaseManager`.

## Strategy & Backtesting
Strategies are versioned and stored via `apps/strategy/storage.py` and referenced from the database.
Strategy metadata stored alongside code includes UI-specific settings like `parameterTypes` and `variableTypes` to preserve types across edits.
`BaseStrategy` ensures a default `symbol` parameter is present to avoid missing-key errors during strategy init.
Backtests are launched from `apps/api/routes/strategies.py` and executed with:
- `VectorizedEngine` or `EventDrivenEngine` (from `apps/backtest`)
- Optional high-resolution execution data
Results are persisted using `BacktestDatabase` and queried via `DatabaseManager`.

## UI Performance Pages
Performance dashboards under `ui/src/app/(dashboard)/performance` call report endpoints through `ui/src/components/performance/use-performance-data.ts`.
That hook loads quick metrics first, then full metrics and equity curves, and returns a combined `all/long/short` metrics object for the performance tables.

## Portfolio Backtesting
Multi-asset portfolio backtests are executed via `apps/backtest/portfolio.py`:
- `PortfolioStrategy` binds symbols, strategies, and asset specs to their data.
- `PortfolioEngine` runs an `EventDrivenEngine` per symbol with equal capital allocation.
- Asset results are aggregated into a `PortfolioBacktestResult`, including trades and summary stats.

## Live Trading
`apps/api/routes/live.py` manages live sessions with:
- Session CRUD and control
- Strategy attachment to sessions
- Signals, positions, and logs
Active sessions are tracked in-memory and coordinated through `apps/live/session.py`.
`apps/live/engine.py` normalizes strategy type aliases (and falls back to strategy names) when choosing built-in strategy classes, and skips unknown types with a warning so live sessions can still start.
Live sessions can also include optional auto-stop settings (`stop_mode`, `stop_at`) stored with the session record.
For live sessions, the engine first attempts to load the strategy class from versioned strategy storage using the selected `strategy_version_id`, falling back to built-in strategy types if needed.
When a session is running, live positions are pulled directly from MT5 and mapped into API responses; position close/modify endpoints operate on MT5 tickets.

## Optimization
`apps/api/routes/optimization.py` starts optimization, walk-forward, and Monte Carlo tasks in the background.
Progress updates are streamed through `OptimizationProgressManager`.

## SQX Strategy Imports
SQX imports are stored in `sqx_strategy_edge` with one row per `strategy_name`.
Stage-specific metrics are stored in prefixed columns (e.g., `a1_profit_factor`), and `stage` tracks the latest stage.
Scores are calculated per strategy name, while symbol is used for grouping and ranking.
The API exposes `GET /api/sqx/strategies` for listing strategies with scores.

## Logging
`apps/api/logging_config.py` configures log sinks for access and error logs in `logs/`.
Backtest logs are streamed through WebSockets using `BacktestLogManager`.
