# Architecture Overview

**Version:** 1.0
**Date:** November 23, 2025
**Status:** Being updated from implementation plan

This document describes the current HaruQuant application architecture

---

## Table of Contents

---

## Overview

---

## 1. Foundation

**Objective:** Project structure, core infrastructure, and development environment

### Project Setup & Environment

#### Setup

- [pyproject.toml](../../pyproject.toml) - Centralized configuration for:

  - Black: 88 character line length, Python 3.9+ target
  - isort: Black-compatible profile, same line length
  - mypy: Configured with reasonable strictness, ignores missing imports for MetaTrader5
  - bandit: Excludes test directories, skips assert checks in tests
  - pylint: Same line length, disabled overly strict rules for trading code
  - pytest: Coverage and test discovery settings
- [.flake8](../../.flake8) - Flake8 configuration:

  - 88 character line length (matching black)
  - Ignores conflicts with black (E203, W503, E501)
  - Max complexity of 10
  - Allows unused imports in __init__.py
- [.pre-commit-config.yaml](../../.pre-commit-config.yaml) - Main pre-commit configuration with:

  - General file checks: trailing whitespace, end-of-file, large files, private keys
  - Black (v24.10.0): Code formatting
  - isort (v5.13.2): Import sorting with black-compatible profile
  - flake8 (v7.1.1): Linting with additional plugins (docstrings, bugbear, comprehensions, simplify)
  - bandit (v1.8.0): Security vulnerability scanning
  - mypy (v1.13.0): Type checking

 **Key Features (No Conflicts)**

- Consistent line length: All tools use 88 characters
- Black-compatible isort: Using --profile black to prevent import conflicts
- Coordinated ignores: flake8 ignores rules that conflict with black
- Appropriate for trading: Allows common trading variable names (df, mt5, id)
- Security-focused: Bandit checks for vulnerabilities, detects private keys
- Type safety: mypy configured with good strictness balance

  The hooks will now run automatically on every commit. You can also run them manually with:
- pre-commit run --all-files - Run on all files
- pre-commit run --files `<file>` - Run on specific files

  pytest options (line 97)
- Added --cov-fail-under=80 to make pytest exit with failure if coverage is below 80%

  New coverage.run section (lines 103-114)
- source: Specifies to measure coverage from the current directory
- omit: Excludes test files, virtual environments, and setup files from coverage calculation
- branch: Enables branch coverage (not just line coverage)

  New coverage.report section (lines 116-129)
- precision: Shows coverage percentages with 2 decimal places
- show_missing: Displays line numbers that aren't covered
- fail_under: Enforces 80% minimum coverage threshold
- exclude_lines: Excludes common patterns that shouldn't count against coverage:

  - pragma: no cover comments
  - __repr__ methods
  - AssertionError and NotImplementedError raises
  - if __name__ == "__main__": blocks
  - Type checking blocks
  - Abstract methods

  Now when you run pytest, it will:

1. Calculate coverage for all source files (excluding tests and venv)
2. Show which lines are missing coverage
3. Fail with exit code 1 if coverage is below 80%

  You can test this with:
  pytest

  Or to see a detailed HTML coverage report:
  pytest --cov=. --cov-report=html

- [Virtual Environment](../../venv) - Virtual environment for the project
- [requirements.txt](../../requirements.txt) - Core dependencies for the project
- Git repository Active
- [README.md](../../README.md) - Summary of project
- [.gitignore](../../.gitignore) - Ignoring files written in
- [LICENSE](../../LICENSE) - LICENSE file in
- [Agents.md](../../Agents.md) - AI Agents instructions for the project

#### Directory Structure

```text
.
├── Reports/
│   └── template.html
├── apps/
│   ├── api/
│   ├── dukascopy/
│   ├── edge/
│   ├── finance/
│   ├── indicator/
│   ├── live/
│   ├── logger/
│   ├── mt5/
│   ├── notifications/
│   ├── optimization/
│   ├── plotting/
│   ├── risk/
│   ├── simulation/
│   ├── sqlite/
│   ├── strategy/
│   ├── trade/
│   ├── utils/
│   └── scheduler.py
├── config/
│   ├── live_trading_config.json
│   ├── multi_strategy_config.json
│   ├── multi_strategy_config_with_db_notifications.json
│   └── risk_enabled_multi_strategy.json
├── data/
│   ├── database/
│   ├── market_data/
│   ├── raw/
│   ├── simulations/
│   ├── states/
│   └── strategies/
├── docs/
│   ├── development/
│   ├── fundamentals/
│   ├── haruquant/
│   └── robustness/
├── examples/
│   ├── compare_api_vs_example.py
│   ├── currency_strength_example.py
│   └── verify_timeframe_alignment.py
├── logs/
│   ├── access.log
│   ├── app.log
│   ├── debug.log
│   └── errors.log
├── output/
│   └── plotting/
├── production/
├── scripts/
│   ├── initialize_database.py
│   └── show_strategy_storage.py
├── tests/
│   ├── benchmarks/
│   ├── integration/
│   ├── unit/
│   ├── usage/
│   ├── validation/
├── ui/
│   ├── public/
│   ├── src/
│   ├── README.md
│   ├── components.json
│   ├── eslint.config.mjs
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── tsconfig.json
│   └── tsconfig.tsbuildinfo
├── Agents.md
├── LICENSE
├── README.md
├── multi_strategy_status.json
├── pyproject.toml
└── requirements.txt
```

---

### Configuration Management

- All Settings and configarations are stored in the `user_settings` table of the database

---

### Logging System

- This was setup as a separate, independent module in the project. Read more in the [Logger Readme](../../apps/logger/README.md) documentation.

---

### Database Management

- This was setup as a separate, independent module in the project. Read more in the [Database Readme](../../apps/sqlite/README.md) documentation.

---

### Utility Functions

- This was setup as a separate, independent module in the project. Read more in the [Utils Readme](../../apps/utils/README.md) documentation.

---

## 2. Data Infrastructure

**Objective:** Build data infrastructure for data providers and trade functions

### MT5 Data Provider

- This was setup as a separate, independent module in the project. Read more in the [MT5 Readme](../../apps/mt5/README.md) documentation.

### Dukascopy Data Provider

- This was setup as a separate, independent module in the project. Read more in the [Dukascopy Readme](../../apps/dukascopy/README.md) documentation.

### Trade functions

- This was setup as a separate, independent module in the project. Read more in the [Trade Readme](../../apps/trade/README.md) documentation.
- These classes and functions are used to Live and Simulation trade aligned with the MQL5 Standard Library

## 3. Strategy Framework

**Objective:** Build strategy development framework with indicators and signal generation

### Indicator Framework

- This was setup as a separate, independent module in the project. Read more in the [Indicator Readme](../../apps/indicator/README.md) documentation.
- Adds relevent indicator columns to the dataframe and returns the full dataframe
- Trend Indicators
- Momentum Indicators
- Volume Indicators
- Volatility Indicators
- Price Indicators
- Sentiment Indicators

### Strategy Base Framework

- This was setup as a separate, independent module in the project. Read more in the [Strategy Readme](../../apps/strategy/README.md) documentation.
- Strategy Base Class
- Entry and Exit columns for signal generation

---

## 4. Backtesting Engine

**Objective:** Build event-driven and vectorized backtesting engines with optimization

- This was setup as a separate, independent module in the project. Read more in the [Simulation Readme](../../apps/simulation/README.md) documentation.

### Portfolio & Position Management (11 functionalities)

| Functionality | Primary File | Class/Method | Line Reference |
|--------------|--------------|--------------|----------------|
| Position Tracking | utils.py | PositionArrayState | 180-450 |
| Price Update | utils.py / engine.py | numba_position_update() / monitor_positions() | 70-178 / 467-650 |
| Equity Updates | engine.py | monitor_account() | 1280-1330 |
| Unrealized PnL | utils.py | numba_position_update() | 112-121 |
| Adding Position | simulator.py | open_position() | 111-220 |
| Positions List | data.py | positions_get() | 1401-1425 |
| Closing Position | simulator.py | close_position() | 222-382 |
| Closed Trades List | simulator.py | _completed_trades | 85 |
| Swap Tracking | data.py | _calc_close_costs() | 493-544 |
| Commission Addition | data.py | _calc_close_costs() | 493-544 |
| Trade Recording | records.py | TradeRecord / _ensure_trade_record() | 35-131 / 186-250 |

### Order Execution & Fill Logic (6 functionalities)

| Functionality | Primary File | Class/Method | Line Reference |
|--------------|--------------|--------------|----------------|
| Market Order Fills | data.py | order_send() - market execution | 595-1370 (936-1050) |
| Limit Order Fills | simulator.py / engine.py | _place_pending_order() / trigger check | 402-453 / ~600-650 |
| Stop Order Fills | simulator.py / engine.py | _place_pending_order() / trigger check | 402-453 / ~600-650 |
| Slippage Calculations | data.py | order_send() - slippage application | 942-950 |
| Commission Calculations | data.py | _calc_close_costs() | 493-544 |
| Spread Application | data.py | order_send() - bid/ask usage | 936-941 |

### Simulation Engine Modes (6 functionalities)

| Functionality | Primary File | Class/Method | Line Reference |
|--------------|--------------|--------------|----------------|
| Event-Driven Engine | engine.py | SimulationEngine.run() | 1457-1800+ |
| Vectorized Engine | engine.py | SimulationEngine.run() - vectorized mode | 1457-1800+ |
| Engine Initialization | simulator.py | TradeSimulator.__init__() | 52-106 |
| Backtest Execution | engine.py | run() main loop | 1657-1768 |
| Signal Processing | engine.py | _process_bar_signal() | 270-347 |
| Position Monitoring | engine.py | monitor_positions() | 467-650 |


-------------------------------------------------------------------------------------

### Week 25: Performance Metrics

#### Task 25.1: Returns Metrics

- [X] Create `app/core/backtest/metrics.py`
- [X] Implement PerformanceMetrics class
- [X] Add calculate_total_return()
- [X] Add calculate_annualized_return()
- [X] Implement CAGR calculation
- [X] **Commit:** `feat(backtest): implement returns metrics`

#### Task 25.2: Risk-Adjusted Metrics

- [X] Implement calculate_sharpe_ratio()
- [X] Implement calculate_sortino_ratio()
- [X] Add smart_sharpe and smart_sortino
- [X] Implement calculate_calmar_ratio()
- [X] Add omega_ratio calculation
- [X] **Commit:** `feat(backtest): implement risk-adjusted metrics`

#### Task 25.3: Risk Metrics

- [X] Implement calculate_max_drawdown()
- [X] Add calculate_max_drawdown_duration()
- [X] Implement calculate_volatility()
- [X] Add downside_deviation calculation
- [X] **Commit:** `feat(backtest): implement risk metrics`

#### Task 25.4: Trade Metrics

- [X] Implement calculate_win_rate()
- [X] Add avg_win_loss_ratio calculation
- [X] Calculate largest_win and largest_loss
- [X] Implement winning/losing_streak tracking
- [X] Add expectancy calculation
- [X] **Commit:** `feat(backtest): implement trade metrics`

#### Task 25.5: Integrate QuantStats

- [ ] Add QuantStats library integration
- [ ] Use QuantStats for additional metrics
- [ ] Create metrics comparison utility
- [ ] **Commit:** `feat(backtest): integrate QuantStats`

**Week 25 Unit Tests:**

- [ ] Create `tests/unit/test_metrics.py`
- [ ] Test each metric with known values
- [ ] Test Sharpe ratio calculation
- [ ] Test max drawdown calculation
- [ ] Test win rate calculation
- [ ] Verify QuantStats integration
- [ ] **Commit:** `test(backtest): add metrics tests`

---

### Week 26: Visualization & Reporting

#### Task 26.1: Equity Curve Visualization

- [X] Create `app/core/backtest/visualizer.py`
- [X] Implement plot_equity_curve() using matplotlib
- [X] Add customization options (colors, labels)
- [X] Include benchmark comparison
- [X] **Commit:** `feat(backtest): implement equity curve plotting`

#### Task 26.2: Drawdown Visualization

- [X] Implement plot_drawdown() chart
- [X] Show underwater plot
- [X] Highlight maximum drawdown period
- [X] **Commit:** `feat(backtest): add drawdown visualization`

#### Task 26.3: Additional Charts

- [X] Implement plot_monthly_returns() heatmap
- [X] Add plot_returns_distribution()
- [X] Create plot_rolling_sharpe()
- [X] **Commit:** `feat(backtest): add additional visualizations`

#### Task 26.4: Backtest Report

- [X] Create generate_report() method
- [X] Include all metrics in report
- [X] Add charts to report
- [X] Generate HTML report option
- [X] **Commit:** `feat(backtest): implement backtest report`

**Week 26 Unit Tests:**

- [X] Create `tests/unit/test_visualizer.py`
- [X] Test chart generation (don't display, just create)
- [X] Test report generation
- [X] **Commit:** `test(backtest): add visualization tests`

**Week 26 Example:**

- [X] Create `examples/backtest_demo.py`
- [X] Run complete backtest with example strategy
- [X] Generate all visualizations
- [X] Show report generation
- [X] **Commit:** `docs(examples): add backtest example`

---

### Week 27: Parameter Optimization

#### Task 27.1: Optimizer Base

- [X] Create `app/core/backtest/optimizer.py`
- [X] Define Optimizer class
- [X] Add parameter grid definition
- [X] Implement generate_parameter_combinations()
- [X] **Commit:** `feat(backtest): create optimizer base`

#### Task 27.2: Grid Search

- [X] Implement grid_search() method
- [X] Add progress tracking
- [X] Store all results
- [X] Rank by optimization metric
- [X] **Commit:** `feat(backtest): implement grid search`

#### Task 27.3: Parallel Optimization

- [X] Implement multiprocessing for optimization
- [X] Add worker pool management
- [X] Distribute backtests across CPU cores
- [X] Collect and aggregate results
- [X] **Commit:** `feat(backtest): add parallel optimization`

#### Task 27.4: Optimization Results

- [X] Create optimization results storage
- [X] Implement best_parameters selection
- [X] Generate optimization report
- [X] Add parameter sensitivity analysis
- [X] **Commit:** `feat(backtest): implement optimization results`

**Week 27 Unit Tests:**

- [X] Create `tests/unit/test_optimizer.py`
- [X] Test parameter combination generation
- [X] Test grid search
- [X] Test result ranking
- [X] Create `tests/integration/test_parallel_optimization.py`
- [X] Test multiprocessing optimization
- [X] Verify results consistency
- [X] **Commit:** `test(backtest): add optimizer tests`

**Week 27 Example:**

- [X] Create `examples/optimizer_demo.py`
- [X] Show parameter grid setup
- [X] Run optimization
- [X] Display results and best parameters
- [X] **Commit:** `docs(examples): add optimization example`

---

### Week 28: Backtest Storage & Integration

#### Task 28.1: Backtest Database Models

- [X] Create `app/database/models/backtest.py`
- [X] Implement BacktestRun model
- [X] Implement BacktestResult model
- [X] Implement BacktestTrade model
- [X] Add relationships and indexes
- [X] Create migrations
- [X] **Commit:** `feat(database): add backtest models`

#### Task 28.2: Backtest Repository

- [X] Create `app/database/repositories/backtest_repo.py`
- [X] Implement save_backtest() method
- [X] Implement load_backtest() method
- [X] Add list_backtests() with filtering
- [X] Implement compare_backtests() method
- [X] **Commit:** `feat(database): add backtest repository`

#### Task 28.3: Backtest Service

- [X] Create `app/services/backtest_service.py`
- [X] Orchestrate: load strategy -> load data -> run backtest -> save results
- [X] Add run_backtest() method
- [X] Add get_backtest_results() method
- [X] Implement backtest comparison logic
- [X] **Commit:** `feat(services): create backtest service`
- [X] **Commit:** `feat(services): create backtest service`

**Week 28 Unit Tests:**

- [X] Create `tests/unit/test_backtest_repo.py`
- [X] Test backtest persistence
- [X] Test loading backtests
- [X] Create `tests/unit/test_backtest_service.py`
- [X] Test service orchestration
- [X] **Commit:** `test(backtest): add repository and service tests`

**Week 28 Integration Tests:**

- [X] Create `tests/integration/test_complete_backtest_flow.py`
- [X] Test: create strategy -> load data -> run backtest -> save -> load -> visualize
- [X] Test optimization workflow
- [X] Test results comparison
- [X] **Commit:** `test(backtest): add complete flow integration test`

**Integration Point 4 Review:**

- [X] Code review of all Phase 4 work
- [X] Run complete backtest end-to-end
- [X] Verify performance targets met
- [X] Test optimization works
- [X] Merge backtesting engine to develop
- [X] Tag release: `v0.4.0-backtesting-engine`
- [X] **Commit:** `release: v0.4.0 backtesting engine complete`

---

## Phase 5: Trading & Execution (Weeks 29-34)

**Objective:** Implement live trading, order management, risk controls, and paper trading

**Parallel Tracks:** Order Management (Agent 1) + Risk Management (Agent 2) + Broker Gateway (Agent 3) + Testing (Agent 4)

### Week 29: Order Management System

#### Task 29.1: Order Models

- [X] Create `app/core/trading/order_manager.py`
- [X] Define Order class (id, symbol, type, side, quantity, price, status)
- [X] Add OrderType enum (MARKET, LIMIT, STOP)
- [X] Add OrderSide enum (BUY, SELL)
- [X] Add OrderStatus enum (PENDING, FILLED, CANCELLED, REJECTED)
- [X] **Commit:** `feat(trading): create order models`

#### Task 29.2: Order Manager Core

- [X] Define OrderManager class
- [X] Implement create_order() method
- [X] Add order validation
- [X] Maintain active_orders list
- [X] Add order state transitions
- [X] **Commit:** `feat(trading): implement order manager core`

#### Task 29.3: Order CRUD Operations

- [X] Implement cancel_order() method
- [X] Implement modify_order() method
- [X] Add get_order_status() method
- [X] Implement get_all_orders() with filtering
- [X] **Commit:** `feat(trading): add order CRUD operations`

#### Task 29.4: Order Database Models

- [X] Create `app/database/models/order.py`
- [X] Implement Order ORM model
- [X] Add order history tracking
- [X] Create migrations
- [X] Create OrderRepository
- [X] **Commit:** `feat(database): add order models and repository`

**Week 29 Unit Tests:**

- [X] Create `tests/unit/test_order.py`
- [X] Test order creation
- [X] Test order validation
- [X] Create `tests/unit/test_order_manager.py`
- [X] Test CRUD operations
- [X] Test state transitions
- [X] Test order persistence
- [X] **Commit:** `test(trading): add order tests`

---

### Week 30: Position Management

#### Task 30.1: Position Manager

- [X] Create `app/core/trading/position_manager.py`
- [X] Define PositionManager class
- [X] Implement get_position() method
- [X] Add update_position() method
- [X] Implement close_position() method
- [X] Add get_all_positions() method
- [X] **Commit:** `feat(trading): implement position manager`

#### Task 30.2: Position Tracking

- [X] Track unrealized PnL for open positions
- [X] Update positions on price ticks
- [X] Calculate total exposure
- [X] Maintain position history
- [X] **Commit:** `feat(trading): add position tracking`

#### Task 30.3: Position Database

- [X] Create `app/database/models/position.py`
- [X] Implement Position ORM model
- [X] Create migrations
- [X] Create PositionRepository
- [X] **Commit:** `feat(database): add position models`

**Week 30 Unit Tests:**

- [X] Create `tests/unit/test_position_manager.py`
- [X] Test position creation and updates
- [X] Test PnL calculations
- [X] Test exposure calculations
- [X] **Commit:** `test(trading): add position manager tests`

---

### Week 31: Risk Management System

#### Task 31.1: Risk Limits Configuration

- [X] Create `app/core/risk/limits.py`
- [X] Define RiskLimits class
- [X] Add max_position_size parameter
- [X] Add max_portfolio_exposure parameter
- [X] Add max_drawdown parameter
- [X] Add max_daily_trades parameter
- [X] Implement validate() method
- [X] **Commit:** `feat(risk): create risk limits`

#### Task 31.2: Risk Manager Core

- [X] Create `app/core/risk/risk_manager.py`
- [X] Define RiskManager class
- [X] Implement check_position_size() method
- [X] Add check_portfolio_risk() method
- [X] Implement can_trade() decision method
- [X] **Commit:** `feat(risk): implement risk manager core`

#### Task 31.3: Position Sizing

- [X] Create `app/core/risk/position_sizing.py`
- [X] Implement fixed fractional sizing
- [X] Add volatility-based sizing (ATR-based)
- [X] Implement calculate_position_size() method
- [X] **Commit:** `feat(risk): implement position sizing`

#### Task 31.4: Drawdown Monitoring

- [X] Implement check_drawdown() method
- [X] Track peak equity
- [X] Calculate current drawdown
- [X] Trigger alerts on threshold breach
- [X] **Commit:** `feat(risk): add drawdown monitoring`

**Week 31 Unit Tests:**

- [X] Create `tests/unit/test_risk_limits.py`
- [X] Test limit validation
- [X] Create `tests/unit/test_risk_manager.py`
- [X] Test position size checks
- [X] Test portfolio risk checks
- [X] Test can_trade() logic
- [X] Create `tests/unit/test_position_sizing.py`
- [X] Test sizing calculations
- [X] **Commit:** `test(risk): add risk management tests`

---

### Week 32: Broker Gateway - MT5 Integration

#### Task 32.1: Broker Gateway Interface

- [X] Create `app/brokers/base.py`
- [X] Define BrokerGateway abstract class
- [X] Add connect() and disconnect() methods
- [X] Add submit_order() method
- [X] Add cancel_order() method
- [X] Add get_positions() method
- [X] Add get_account_info() method
- [X] **Commit:** `feat(brokers): create broker gateway interface`

#### Task 32.2: MT5 Gateway Implementation

- [X] Create `app/brokers/mt5_gateway.py`
- [X] Implement MT5Gateway class
- [X] Add connect() using MT5 library
- [X] Implement submit_order() with MT5 API
- [X] Add cancel_order() implementation
- [X] Implement get_positions() from MT5
- [X] Add get_account_info() from MT5
- [X] **Commit:** `feat(brokers): implement MT5 gateway`

#### Task 32.3: Order Translation

- [X] Map internal Order to MT5 order format
- [X] Handle order type conversions
- [X] Add symbol mapping if needed
- [X] Implement error code translation
- [X] **Commit:** `feat(brokers): add order translation`

#### Task 32.4: Broker Connection Management

- [X] Add connection state tracking
- [X] Implement automatic reconnection
- [X] Add connection error handling
- [X] Implement heartbeat checking
- [X] **Commit:** `feat(brokers): add connection management`

**Week 32 Unit Tests:**

- [X] Create `tests/unit/test_broker_gateway.py`
- [X] Test interface methods
- [X] Create `tests/unit/test_mt5_gateway.py`
- [X] Test order submission (mocked)
- [X] Test order translation
- [X] Test connection handling
- [X] **Commit:** `test(brokers): add broker gateway tests`

**Week 32 Integration Test:**

- [X] Create `tests/integration/test_mt5_gateway.py`
- [X] Test actual MT5 connection
- [X] Test real order submission (small test orders)
- [X] **Commit:** `test(brokers): add MT5 integration tests`

---

### Week 33: Live Trading Engine

#### Task 33.1: Live Trading Engine Core

- [X] Create `app/core/trading/engine.py`
- [X] Define LiveTradingEngine class
- [X] Implement start() method
- [X] Implement stop() method
- [X] Add is_running flag
- [X] **Commit:** `feat(trading): create live trading engine core`

#### Task 33.2: Event Handlers

- [X] Implement on_tick() handler
- [X] Implement on_bar() handler
- [X] Call strategy methods on events
- [X] Process generated signals
- [X] **Commit:** `feat(trading): add event handlers`

#### Task 33.3: Signal to Order Flow

- [X] Implement signal validation
- [X] Call RiskManager.can_trade()
- [X] Calculate position size
- [X] Create and submit order via OrderManager
- [X] Handle order responses
- [X] **Commit:** `feat(trading): implement signal to order flow`

#### Task 33.4: Emergency Shutdown

- [X] Implement emergency_shutdown() method
- [X] Cancel all pending orders
- [X] Close all open positions (optional, configurable)
- [X] Send alerts
- [X] Log shutdown event
- [X] **Commit:** `feat(trading): add emergency shutdown`

#### Task 33.5: State Reconciliation

- [X] Implement reconcile_with_broker() method
- [X] Compare internal state with broker state
- [X] Detect and log discrepancies
- [X] Attempt auto-correction or alert
- [X] **Commit:** `feat(trading): add state reconciliation`

**Week 33 Unit Tests:**

- [X] Create `tests/unit/test_live_trading_engine.py`
- [X] Test engine start/stop
- [X] Test event handling
- [X] Test signal processing
- [X] Test emergency shutdown
- [X] **Commit:** `test(trading): add live trading engine tests`

---

### Week 34: Paper Trading & Integration

#### Task 34.1: Paper Trading Mode

- [X] Add paper_trading flag to LiveTradingEngine
- [X] Create PaperBrokerGateway (simulated broker)
- [X] Implement simulated order execution
- [X] Track paper trading portfolio
- [X] **Commit:** `feat(trading): implement paper trading mode`

#### Task 34.2: Trading Service

- [X] Create `app/services/trading_service.py`
- [X] Orchestrate: strategy → engine → broker → risk
- [X] Implement start_strategy() method
- [X] Add stop_strategy() method
- [X] Implement get_live_performance() method
- [X] **Commit:** `feat(services): create trading service`

#### Task 34.3: Trade Database Models

- [X] Create `app/database/models/trade.py`
- [X] Implement Trade ORM model (live trades)
- [X] Create migrations
- [X] Create TradeRepository
- [X] **Commit:** `feat(database): add trade models`

#### Task 34.4: Account Snapshots

- [X] Create `app/database/models/account_snapshot.py`
- [X] Implement periodic account snapshots
- [X] Store balance, equity, margin, etc.
- [X] Create AccountSnapshotRepository
- [X] **Commit:** `feat(database): add account snapshot tracking`

**Week 34 Unit Tests:**

- [X] Create `tests/unit/test_paper_trading.py`
- [X] Test paper broker gateway
- [X] Test simulated execution
- [X] Create `tests/unit/test_trading_service.py`
- [X] Test service orchestration
- [X] **Commit:** `test(trading): add paper trading tests`

**Week 34 Integration Tests:**

- [X] Create `tests/integration/test_live_trading_flow.py`
- [X] Test complete flow: start → receive data → generate signal → execute (paper) → track
- [X] Test emergency shutdown
- [X] Test reconciliation
- [X] **Commit:** `test(trading): add live trading integration tests`

**Week 34 Example:**

- [X] Create `examples/paper_trading_demo.py`
- [X] Show starting paper trading
- [X] Demonstrate live strategy execution
- [X] Show position tracking
- [X] Show stopping and results
- [X] **Commit:** `docs(examples): add paper trading example`

**Integration Point 5 Review:**

- [ ] Code review of all Phase 5 work
- [ ] Run paper trading end-to-end
- [ ] Test risk management works
- [ ] Test emergency shutdown
- [ ] Merge trading system to develop
- [ ] Tag release: `v0.5.0-live-trading`
- [ ] **Commit:** `release: v0.5.0 live trading complete`

---

## Phase 6: Integration & Polish (Weeks 35-40)

**Objective:** Final integration, notifications, polish, documentation, and MVP release

**Parallel Tracks:** Notifications (Agent 1) + API Layer (Agent 2) + Documentation (Agent 3) + Final Testing (Agent 4)

### Week 35: Notification System

#### Task 35.1: Notification Models

- [X] Create `app/notifications/manager.py`
- [X] Define Notification dataclass
- [X] Add NotificationType enum
- [X] Add NotificationPriority enum
- [X] **Commit:** `feat(notifications): create notification models`

#### Task 35.2: Notification Channels Interface

- [X] Create `app/notifications/channels/base.py`
- [X] Define NotificationChannel abstract class
- [X] Add send() method
- [X] Add is_enabled() method
- [X] **Commit:** `feat(notifications): create channel interface`

#### Task 35.3: Telegram Channel

- [X] Create `app/notifications/channels/telegram.py`
- [X] Implement TelegramChannel class
- [X] Add bot token and chat ID configuration
- [X] Implement send() using python-telegram-bot
- [X] Format messages nicely
- [X] **Commit:** `feat(notifications): implement Telegram channel`

#### Task 35.4: Email Channel

- [X] Create `app/notifications/channels/email.py`
- [X] Implement EmailChannel class
- [X] Add SMTP configuration
- [X] Implement send() using smtplib
- [X] Create email templates
- [X] **Commit:** `feat(notifications): implement email channel`

#### Task 35.5: Notification Manager

- [X] Implement NotificationManager class
- [X] Add send_notification() method
- [X] Implement send_trade_alert()
- [X] Add send_error_alert()
- [X] Implement send_performance_report()
- [X] Support multiple channels
- [X] **Commit:** `feat(notifications): implement notification manager`

**Week 35 Unit Tests:**

- [X] Create `tests/unit/test_notification_manager.py`
- [X] Test notification creation
- [X] Test channel selection
- [X] Create `tests/unit/test_telegram_channel.py`
- [X] Test Telegram message formatting
- [X] Create `tests/unit/test_email_channel.py`
- [X] Test email formatting
- [X] **Commit:** `test(notifications): add notification tests`

**Week 35 Integration Test:**

- [ ] Create `tests/integration/test_notifications.py`
- [ ] Test actual Telegram sending (optional, with test bot)
- [ ] Test email sending
- [ ] **Commit:** `test(notifications): add integration tests`

---

### Week 36: API Layer Foundation (V2 Prep)

#### Task 36.1: FastAPI Application Setup

- [X] Create `app/api/v1/__init__.py`
- [X] Set up FastAPI app in `app/main.py`
- [X] Configure CORS
- [X] Add startup and shutdown events
- [X] **Commit:** `feat(api): set up FastAPI application`

#### Task 36.2: Pydantic Schemas

- [X] Create `app/schemas/strategy.py`
- [X] Create `app/schemas/backtest.py`
- [X] Create `app/schemas/trade.py`
- [X] Create request and response models
- [X] **Commit:** `feat(api): add Pydantic schemas`

#### Task 36.3: Basic Endpoints

- [X] Create `app/api/v1/system.py`
- [X] Implement GET /system/health endpoint
- [X] Implement GET /system/status endpoint
- [X] Create `app/api/v1/data.py`
- [X] Implement GET /data/symbols endpoint
- [X] Add routes for /strategies, /backtest, /orders, /positions, /live/start, /live/stop
- [X] **Commit:** `feat(api): add basic API endpoints`

**Week 36 Unit Tests:**

- [X] Create `tests/unit/test_api_endpoints.py`
- [X] Test health endpoint
- [X] Test schemas validation
- [X] Test basic endpoint availability
- [X] **Commit:** `test(api): add API tests`

---

### Week 37: Comprehensive Testing

#### Task 37.1: Test Coverage Analysis

- [ ] Run pytest with coverage
- [ ] Identify gaps in coverage
- [ ] Add tests to reach 70%+ coverage
- [ ] Document coverage report
- [ ] **Commit:** `test: improve test coverage to 70%+`

#### Task 37.2: Integration Test Suite

- [ ] Create `tests/integration/test_end_to_end.py`
- [ ] Test: download data → create strategy → backtest → optimize → paper trade
- [ ] Test complete workflow
- [ ] **Commit:** `test: add comprehensive end-to-end test`

#### Task 37.3: Performance Testing

- [ ] Create `tests/performance/test_system_performance.py`
- [ ] Benchmark backtest speed (verify 1M orders in 70-100ms)
- [ ] Test data loading speed
- [ ] Test database query performance
- [ ] Document results
- [ ] **Commit:** `test: add performance benchmarks`

#### Task 37.4: Edge Case Testing

- [ ] Test error conditions
- [ ] Test boundary values
- [ ] Test concurrent access scenarios
- [ ] Test failure recovery
- [ ] **Commit:** `test: add edge case tests`

---

### Week 38: Documentation Completion

#### Task 38.1: API Documentation

- [ ] Generate OpenAPI/Swagger docs from FastAPI
- [ ] Add detailed endpoint descriptions
- [ ] Include request/response examples
- [ ] Document authentication
- [ ] **Commit:** `docs(api): complete API documentation`

#### Task 38.2: User Guides

- [ ] Update `docs/installation.md` with complete instructions
- [ ] Create `docs/quickstart.md` tutorial
- [ ] Write `docs/strategy_development.md` guide
- [ ] Create `docs/backtesting_guide.md`
- [ ] Write `docs/live_trading_guide.md`
- [ ] **Commit:** `docs: complete user guides`

#### Task 38.3: Code Examples

- [ ] Review all examples for completeness
- [ ] Add comments and explanations
- [ ] Create `examples/README.md` index
- [ ] Test all examples work
- [ ] **Commit:** `docs: polish code examples`

#### Task 38.4: Developer Documentation

- [ ] Create `docs/CONTRIBUTING.md`
- [ ] Document code standards
- [ ] Add git workflow documentation
- [ ] Create module documentation
- [ ] **Commit:** `docs: add developer documentation`

#### Task 38.5: Architecture Documentation

- [ ] Update `docs/ARCHITECTURE.md` with final architecture
- [ ] Add system diagrams
- [ ] Document design decisions
- [ ] Create deployment guide
- [ ] **Commit:** `docs: finalize architecture documentation`

---

### Week 39: Code Quality & Refactoring

#### Task 39.1: Code Quality Review

- [ ] Run flake8 on entire codebase
- [ ] Run black to format code
- [ ] Run mypy for type checking
- [ ] Fix all issues
- [ ] **Commit:** `refactor: ensure code quality standards`

#### Task 39.2: Code Refactoring

- [ ] Identify code duplication
- [ ] Extract common functions
- [ ] Simplify complex functions
- [ ] Improve naming
- [ ] **Commit:** `refactor: improve code structure`

#### Task 39.3: Performance Optimization

- [ ] Profile critical paths
- [ ] Optimize database queries
- [ ] Improve caching strategy
- [ ] Add indexes where needed
- [ ] **Commit:** `perf: optimize performance`

#### Task 39.4: Error Handling Review

- [ ] Ensure all functions have proper error handling
- [ ] Add meaningful error messages
- [ ] Improve exception hierarchy
- [ ] **Commit:** `refactor: improve error handling`

---

### Week 40: Final Integration & MVP Release

#### Task 40.1: Final Integration Testing

- [ ] Run all tests (unit, integration, performance)
- [ ] Fix any remaining bugs
- [ ] Verify all features work together
- [ ] Test on clean environment
- [ ] **Commit:** `test: final integration testing`

#### Task 40.2: Release Preparation

- [ ] Update version to 1.0.0
- [ ] Create CHANGELOG.md with all features
- [ ] Update README.md with installation and usage
- [ ] Tag release: `v1.0.0-mvp`
- [ ] **Commit:** `release: v1.0.0 MVP`

#### Task 40.3: Deployment Checklist

- [ ] Create deployment scripts
- [ ] Document deployment process
- [ ] Create backup procedures
- [ ] Set up monitoring (basic)
- [ ] **Commit:** `chore: add deployment materials`

#### Task 40.4: User Acceptance Testing

- [ ] Install on fresh system
- [ ] Run through user guide
- [ ] Test all major workflows
- [ ] Collect feedback
- [ ] Fix critical issues

#### Task 40.5: MVP Launch

- [ ] Merge develop to main
- [ ] Create GitHub release with notes
- [ ] Archive all documentation
- [ ] Celebrate! 🎉

**Week 40 Deliverables:**

- [ ] Complete, working MVP
- [ ] All tests passing
- [ ] 70%+ code coverage
- [ ] Complete documentation
- [ ] Ready for production use

---

## 10. Testing Strategy

### 10.1 Test Categories

**Unit Tests:**

- Test individual functions and classes in isolation
- Mock external dependencies
- Fast execution (<1s per test)
- Located in `tests/unit/`

**Integration Tests:**

- Test module interactions
- Use actual databases (test DB)
- Test with real external services where possible
- Located in `tests/integration/`

**Performance Tests:**

- Benchmark critical operations
- Verify performance targets
- Track performance over time
- Located in `tests/performance/`

**End-to-End Tests:**

- Test complete workflows
- Minimal mocking
- Verify system as a whole
- Located in `tests/integration/test_end_to_end.py`

### 10.2 Testing Checklist

**For Each Feature:**

- [ ] Write unit tests before or during implementation (TDD)
- [ ] Achieve >70% coverage for the feature
- [ ] Test happy path
- [ ] Test error conditions
- [ ] Test edge cases
- [ ] Test with invalid inputs
- [ ] Add integration test if feature spans modules
- [ ] Create usage example

**Before Each Commit:**

- [ ] Run relevant unit tests
- [ ] Ensure tests pass
- [ ] Run code quality tools (flake8, black)

**Before Each Merge:**

- [ ] Run full test suite
- [ ] Check code coverage
- [ ] Run integration tests
- [ ] Update documentation if needed

### 10.3 Test Data

**Create Test Fixtures:**

- [ ] Sample OHLCV data (1 year, multiple symbols)
- [ ] Sample strategies (simple, medium, complex)
- [ ] Mock broker responses
- [ ] Sample backtesting configurations

**Located in:** `tests/fixtures/`

---

## 11. Deployment Checklist

### 11.1 Pre-Deployment

- [ ] All tests passing
- [ ] Code coverage >70%
- [ ] Documentation complete
- [ ] CHANGELOG.md updated
- [ ] Version number updated
- [ ] All dependencies documented in requirements.txt

### 11.2 Deployment Steps

- [ ] Create virtual environment
- [ ] Install dependencies
- [ ] Set up databases (SQLite, Redis)
- [ ] Configure settings (`.env` file)
- [ ] Run database migrations
- [ ] Test configuration
- [ ] Start application
- [ ] Verify health endpoint
- [ ] Run smoke tests

### 11.3 Post-Deployment

- [ ] Monitor logs for errors
- [ ] Verify all services running
- [ ] Test critical workflows
- [ ] Set up automated backups
- [ ] Document any deployment issues

---

## Appendix A: Commit Message Examples

```
feat(database): add Symbol model and repository
feat(data): implement MT5 data provider
feat(strategy): create indicator base class
feat(backtest): implement event-driven engine
feat(trading): add order manager
fix(database): correct session management bug
test(data): add data validation tests
docs(api): update endpoint documentation
refactor(strategy): simplify signal generation
perf(backtest): optimize equity curve calculation
chore(deps): update dependency versions
```

---

## Appendix B: Parallel Development Assignment Example

**Sprint 1 (Weeks 1-8): Foundation**

| Agent   | Tasks                          | Integration Point |
| ------- | ------------------------------ | ----------------- |
| Agent 1 | Project setup, Database, Redis | Week 8            |
| Agent 2 | Configuration, Logging         | Week 8            |
| Agent 3 | Utilities, Exceptions          | Week 8            |
| Agent 4 | Testing setup, Documentation   | Week 8            |

**Sprint 2 (Weeks 9-14): Data Infrastructure**

| Agent   | Tasks                            | Integration Point |
| ------- | -------------------------------- | ----------------- |
| Agent 1 | Data models, Database models     | Week 14           |
| Agent 2 | MT5 Provider, Dukascopy Provider | Week 14           |
| Agent 3 | Data validation, Storage         | Week 14           |
| Agent 4 | Data tests, Examples             | Week 14           |

**Sprint 3 (Weeks 15-20): Strategy Framework**

| Agent   | Tasks                            | Integration Point |
| ------- | -------------------------------- | ----------------- |
| Agent 1 | Indicator base, Trend indicators | Week 20           |
| Agent 2 | Momentum, Volatility indicators  | Week 20           |
| Agent 3 | Strategy base, Entry/Exit rules  | Week 20           |
| Agent 4 | Strategy tests, Examples         | Week 20           |

---

## Appendix C: Success Metrics

**Code Quality:**

- [ ] Flake8 passes with zero errors
- [ ] Black formatting applied
- [ ] MyPy type checking passes
- [ ] No critical pylint issues

**Testing:**

- [ ]
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] End-to-end test succeeds

**Functionality:**

- [ ] Can download and store market data
- [ ] Can create and save strategies
- [ ] Can run backtests successfully
- [ ] Backtesting performance meets targets (1M orders in 70-100ms)
- [ ] Can run parameter optimization
- [ ] Paper trading works end-to-end
- [ ] All notifications send successfully

**Documentation:**

- [ ] All public APIs documented
- [ ] User guides complete
- [ ] Examples work
- [ ] Architecture documented

---

## Appendix D: Tools & Resources

**Development Tools:**

- Python 3.11+
- VS Code or PyCharm
- Git
- Docker (optional)

**Testing Tools:**

- pytest
- pytest-cov
- pytest-asyncio (if needed)

**Code Quality:**

- black
- flake8
- mypy
- pylint

**Documentation:**

- Sphinx (optional, for API docs)
- Markdown

**Databases:**

- SQLite (development)
- Redis

---

**End of Implementation Plan**

This plan provides a complete roadmap for building the MVP of the Complete Trading System over 32-40 weeks. Each task is designed to be small, focused, and testable, allowing for steady progress and regular commits.

**Next Step:** Begin with Phase 1, Week 1, Task 1.1 - Repository Initialization

Good luck with the implementation! 🚀
