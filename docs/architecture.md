# Architecture Overview

This document describes the current HaruQuant application architecture based on the code in `apps/`.

## High-Level Layout
- `apps/api`: FastAPI application, routing, auth utilities, logging configuration, and WebSocket managers.
- `apps/sqlite`: Database access layer used by the API and background tasks via `DatabaseManager`.
- `apps/strategy`: Strategy storage and loading utilities for versioned strategy code.
- `apps/simulation`: MT5-aligned local simulator used for both the simulator UI and backtest execution.
- `apps/live`: Live trading session orchestration used by live-trading routes.
- `apps/mt5`: MetaTrader 5 client/data access used by broker, live, and backtest flows, including the shared MT5 runtime adapter (`MT5Api`).
- `apps/trade`: MT5-aligned trade classes.
- `apps/ctrade`: MT5-specific trade classes aligned to the MQL5 Standard Library (`CSymbolInfo`, `CAccountInfo`, `COrderInfo`, `CHistoryOrderInfo`, `CPositionInfo`, `CDealInfo`, `CTrade`, `CTerminalInfo`) with an injected MT5 API surface.
- `apps/simulator`: MT5-aligned local trade simulator for positions, validation, and P/L calculations (no live orders), plus tester-mode MT5 overloads, MT5-like order_send handling, a disk-backed market data store for bars/ticks, and a tester runner for real/simulated tick modelling.
- `apps/simulator/session.py`: Streaming simulator session manager for bar playback, indicators, and replay/strategy hooks.
- `apps/optimization`: Optimization tasks and models used by optimization routes.
- `apps/edge`: Edge Lab statistical edge discovery toolkit used by edge-lab routes.
- `apps/scheduler`: APScheduler-based background jobs (e.g., simulator session cleanup).
- `apps/edge/seasonality.py`: Seasonality analytics engine that aggregates intraday, weekly, and calendar stats.
- `apps/utils`: Shared helpers (data loading, validation, security), including trade validation and error descriptions.

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
- Simulator (`apps/api/routes/simulator.py`) for historical playback sessions and WebSocket bar streaming
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
Simulator streaming uses `apps/api/routes/simulator.py` and `apps/simulator/session.py` for bar/trade/account/indicator updates.

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
Backtests are launched from `apps/api/routes/backtest.py` and executed with the simulator stack:
- `TradeSimulator` + `SimulationEngine` in `apps/simulation`
- Data modeling modes: `trading_timeframe`, `m1_ohlc`, `synthetic_ticks`, `real_ticks`
- Optional M1/tick execution data depending on the selected mode
Results are persisted into the backtest tables via the SQLite backtest manager.

----------------------------
Vectorized Backtest Engine (Close-Based)
- `engine_type="vectorised"` runs a close-only, vectorized backtest.
- Processes the full DataFrame in bulk using pandas/numpy arrays.
- Simplified execution model: no intra-bar SL/TP and no mark-to-market updates.
- Intended for fast research and parameter sweeps, not final validation.
- Position array buffers are preallocated and reused per bar to avoid allocation overhead while keeping per-bar updates intact.

----------------------------
Numba JIT Core (Optional)
- Event-driven backtests can enable a Numba-accelerated position update kernel via `use_numba=True`.
- The JIT kernel only replaces per-position math (profit, margin, SL/TP hit checks) while preserving per-bar behavior.
- Position arrays can be maintained as a struct-of-arrays to avoid per-bar object traversal in the hot loop.
- When `use_position_arrays=True` and `use_fast_calc=True`, the engine can compute profit/margin via NumPy array math while still updating PositionInfo and trade records every bar.

## UI Performance Pages
Performance dashboards under `ui/src/app/(dashboard)/performance` call report endpoints through `ui/src/components/performance/use-performance-data.ts`.
That hook loads quick metrics first, then full metrics and equity curves, and returns a combined `all/long/short` metrics object for the performance tables.

## UI Simulator
The simulator UI lives at `ui/src/app/(dashboard)/simulation/page.tsx`, which manages the config/execution/results view state.
API calls are defined in `ui/src/lib/api/simulator.ts`, and the configuration form (including strategy selection, replay selection, and CSV import) lives in `ui/src/components/simulation/config-form.tsx`.
Real-time charting is implemented in `ui/src/components/simulation/simulation-chart.tsx`, which connects to the simulator WebSocket stream and renders bars, indicators, and trade markers.
Trading controls are split into `ui/src/components/simulation/speed-control.tsx`, `ui/src/components/simulation/skip-control.tsx`, `ui/src/components/simulation/trading-panel.tsx`, and `ui/src/components/simulation/trade-dialog.tsx`, with optional browser notifications driven by `ui/src/lib/hooks/use-simulator-trade-notifications.ts`.
Position and account UI components live in `ui/src/components/simulation/positions-panel.tsx`, `ui/src/components/simulation/orders-panel.tsx`, and `ui/src/components/simulation/account-metrics.tsx` and are designed to bind to simulator WebSocket/account state updates.
The execution container is `ui/src/components/simulation/execution-view.tsx`, which coordinates the simulator WebSocket, chart click trading, and control panels. Results rendering lives in `ui/src/components/simulation/results-view.tsx` and consumes session metadata plus captured trades/account snapshots.

## Portfolio Backtesting
Portfolio backtesting is currently disabled (legacy `apps/backtest` engines were removed). The backtest API now routes through the simulator backend and supports single-symbol runs.

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

## Trading Simulator
Simulator sessions are stored in `simulation_sessions` and `simulation_trades` and streamed through `apps/api/routes/simulator.py`.
Each session uses `apps/simulator/session.py` to load bars, run optional strategy or replay modes, and emit WebSocket messages for bars, trades, account snapshots, indicators, and completion status.
The simulator and live MT5 now share a single MT5 API surface (`MT5Api` in `apps/mt5/client.py`) so trade classes can work against live or simulated backends.
The MT5-aligned local trade simulator in `apps/simulation/simulator.py` maintains in-memory positions, updates running P/L from ticks, closes positions when SL/TP thresholds are hit, and manages pending orders with validation, modification, and trigger/expiry handling.
Per-bar execution flow lives in `apps/simulation/engine.py`, record tracking is centralized in `apps/simulation/records.py`, and MT5-style data containers are defined in `apps/simulation/data.py`.
`SimulatorClient.order_send` now mirrors MT5 behavior by validating requests and performing all state updates (pending orders, open/close positions, SL/TP modifications, and deal history), while higher-level simulator methods delegate to it instead of duplicating validations.
The simulator engine supports multiple data modeling modes (`trading_timeframe`, `m1_ohlc`, `synthetic_ticks`, `real_ticks`) and uses `step_data` to control the execution granularity while still generating signals from the trading timeframe. The `m1_ohlc` mode now steps one tick per M1 bar (using the M1 close with spread), rather than a 4-tick OHLC pattern.

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
