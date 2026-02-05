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
  - pre-commit run --files <file> - Run on specific files

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

### 2. Configuration Management

#### Configuration System

- All Settings and configarations are stored in the `user_settings` table of the database


---

### 3. Logging System

#### Logger Setup, Configuration, and Handlers

- This was setup as a separate, independent module in the project. Read more in the [Logger Readme](../../apps/logger/README.md) documentation.


---

### 4. Database Foundation

#### Database Management

- This was setup as a separate, independent module in the project. Read more in the [Database Readme](../../apps/sqlite/README.md) documentation.


---

### 5. Utility Functions

- This was setup as a separate, independent module in the project. Read more in the [Utils Readme](../../apps/utils/README.md) documentation.

---

### Week 8: Phase 1 Integration & Testing

#### Task 8.1: Core Integration

- [X] Create `app/main.py` application entry point
- [X] Initialize all core components (config, database, redis, logger)
- [X] Add startup and shutdown handlers
- [X] Test all components initialize correctly
- [X] **Commit:** `feat(core): create application entry point`
  - Tested via `PYTHONPATH=. python app/main.py` (DB + Redis initialization)

#### Task 8.2: End-to-End Foundation Test

- [X] Create `tests/integration/test_foundation.py`
- [X] Test full initialization sequence
- [X] Test configuration loading
- [X] Test database connection
- [X] Test Redis connection
- [X] Test logging works
- [X] **Commit:** `test(integration): add foundation integration tests`

#### Task 8.3: Example Application

- [X] Create `examples/foundation_demo.py`
- [X] Demonstrate initializing the system
- [X] Show configuration usage
- [X] Show database operations
- [X] Show caching with Redis
- [X] Show logging
- [X] **Commit:** `docs(examples): add foundation demo`

#### Task 8.4: Documentation Update

- [X] Update `docs/ARCHITECTURE.md` with implemented components
- [X] Add API documentation for completed modules
- [X] Create `docs/quickstart.md` for getting started
- [X] **Commit:** `docs(foundation): update documentation`

**Week 8 Deliverables:**

- [X] All foundation components working
- [X] All tests passing (aim for 70%+ coverage)
- [X] Configuration system functional
- [X] Database and Redis connected
- [X] Logging system operational
- [ ] Clean code (passes flake8, black, mypy)

**Integration Point 1 Review:**

- [ ] Code review of all Phase 1 work
- [ ] Merge all feature branches to develop
- [X] Tag release: `v0.1.0-foundation`
- [X] **Commit:** `release: v0.1.0 foundation complete`

---

## Phase 2: Data Infrastructure (Weeks 9-14)

**Objective:** Build complete data acquisition, validation, and storage system

**Parallel Tracks:** Data Providers (Agent 2) + Data Storage (Agent 1) + Testing (Agent 4)

### Week 9: Data Models

#### Task 9.1: Market Data Models

- [X] Create `app/data/models.py`
- [X] Implement Bar dataclass (timestamp, OHLCV, spread)
- [X] Implement Tick dataclass (timestamp, bid, ask, volume)
- [X] Add validation methods to data classes
- [X] Implement to_dict() and from_dict() methods
- [X] **Commit:** `feat(data): create market data models`

#### Task 9.2: Database Models for Market Data

- [X] Create `app/database/models/market_data.py`
- [X] Implement OHLCVData model as per ERD
- [X] Implement TickData model as per ERD
- [X] Add proper indexes (symbol, timeframe, timestamp)
- [X] Create migrations for new tables
- [X] **Commit:** `feat(database): add market data models`

#### Task 9.3: Market Data Repositories

- [X] Create `app/database/repositories/market_data_repo.py`
- [X] Implement save_bars() method
- [X] Implement load_bars() with date range filtering
- [X] Implement get_latest_bar() method
- [X] Add save_ticks() and load_ticks() methods
- [X] **Commit:** `feat(database): add market data repositories`

**Week 9 Unit Tests:**

- [X] Create `tests/unit/test_data_models.py`
- [X] Test Bar creation and validation
- [X] Test Tick creation and validation
- [X] Test serialization (to_dict, from_dict)
- [X] Create `tests/unit/test_market_data_repo.py`
- [X] Test saving and loading bars
- [X] Test date range filtering
- [X] Test latest bar retrieval
- [X] **Commit:** `test(data): add data model tests`

---

### Week 10: Data Validation

#### Task 10.1: OHLC Validator

- [X] Create `app/data/validation/ohlc_validator.py`
- [X] Implement validate_ohlc() - check High >= Low, etc.
- [X] Add sanity checks (prices > 0, volume >= 0)
- [X] Implement validate_bar_sequence() for continuity
- [X] **Commit:** `feat(data): implement OHLC validator`

#### Task 10.2: Gap Detector

- [X] Create `app/data/validation/gap_detector.py`
- [X] Implement detect_gaps() to find missing bars
- [X] Calculate gap duration
- [X] Generate gap report
- [X] **Commit:** `feat(data): implement gap detector`

#### Task 10.3: Spike Detector

- [X] Create `app/data/validation/spike_detector.py`
- [X] Implement detect_price_spikes() using Z-score
- [X] Add volume spike detection
- [X] Create configurable threshold parameters
- [X] **Commit:** `feat(data): implement spike detector`

#### Task 10.4: Completeness Checker

- [X] Create `app/data/validation/completeness_checker.py`
- [X] Implement check_completeness() for date ranges
- [X] Calculate data quality score
- [X] Generate completeness report
- [X] **Commit:** `feat(data): implement completeness checker`

#### Task 10.5: Data Validator Manager

- [X] Create `app/data/validation/__init__.py`
- [X] Implement DataValidator class that uses all validators
- [X] Add comprehensive validate() method
- [X] Generate validation summary report
- [X] **Commit:** `feat(data): create data validator manager`

**Week 10 Unit Tests:**

- [X] Create `tests/unit/test_ohlc_validator.py`
- [X] Test valid and invalid OHLC patterns
- [X] Create `tests/unit/test_gap_detector.py`
- [X] Test gap detection with sample data
- [X] Create `tests/unit/test_spike_detector.py`
- [X] Test spike detection algorithm
- [X] Create `tests/unit/test_completeness_checker.py`
- [X] Test completeness calculation
- [X] **Commit:** `test(data): add validation tests`

**Week 10 Examples:**

- [X] Create `examples/data_validation_demo.py`
- [X] Show validation of good and bad data
- [X] Demonstrate gap detection
- [X] Show spike detection
- [X] **Commit:** `docs(examples): add data validation examples`

---

### Week 11: Data Providers - Base Interface

#### Task 11.1: Data Provider Interface

- [X] Create `app/data/providers/base.py`
- [X] Define DataProvider abstract base class
- [X] Add connect() and disconnect() abstract methods
- [X] Add get_historical() abstract method
- [X] Add stream_live() abstract method
- [X] **Commit:** `feat(data): create data provider interface`

#### Task 11.2: Provider Factory

- [X] Create `app/data/providers/factory.py`
- [X] Implement provider factory pattern
- [X] Add provider registration mechanism
- [X] Create get_provider() factory method
- [X] **Commit:** `feat(data): implement provider factory`

**Week 11 Unit Tests:**

- [X] Create `tests/unit/test_data_provider_base.py`
- [X] Test interface methods are abstract
- [X] Create `tests/unit/test_provider_factory.py`
- [X] Test provider creation
- [X] Test provider registration
- [X] **Commit:** `test(data): add provider interface tests`

---

### Week 12: MT5 Data Provider

#### Task 12.1: MT5 Connection

- [X] Create `app/data/providers/mt5.py`
- [X] Implement MT5Provider class inheriting from DataProvider
- [X] Add connect() method using MetaTrader5 library
- [X] Implement disconnect() method
- [X] Add connection state management
- [X] Handle connection errors
- [X] **Commit:** `feat(data): implement MT5 connection`

#### Task 12.2: MT5 Historical Data

- [X] Implement get_historical() method
- [X] Convert MT5 data format to Bar objects
- [X] Add timeframe mapping (MT5 constants to our format)
- [X] Implement pagination for large data requests
- [X] Add rate limiting to respect broker limits
- [X] **Commit:** `feat(data): implement MT5 historical data retrieval`

#### Task 12.3: MT5 Live Streaming

- [X] Implement stream_live() method (placeholder for now)
- [X] Add tick subscription mechanism
- [X] Implement tick-to-bar aggregation
- [X] **Commit:** `feat(data): add MT5 live streaming foundation`

**Week 12 Unit Tests:**

- [X] Create `tests/unit/test_mt5_provider.py`
- [X] Test connection handling (mock MT5)
- [X] Test historical data conversion
- [X] Test timeframe mapping
- [X] Test error handling
- [X] **Commit:** `test(data): add MT5 provider tests`

**Week 12 Integration Test:**

- [X] Create `tests/integration/test_mt5_connection.py`
- [X] Test actual MT5 connection (if available)
- [X] Test real data download
- [X] **Commit:** `test(data): add MT5 integration tests`

---

### Week 13: Dukascopy Data Provider

#### Task 13.1: Dukascopy Provider

- [X] Create `app/data/providers/dukascopy.py`
- [X] Implement DukascopyProvider class
- [X] Add connect() method (HTTP-based)
- [X] Implement get_historical() using Dukascopy API
- [X] Handle data format conversion to Bar objects
- [X] **Commit:** `feat(data): implement Dukascopy provider`

#### Task 13.2: Dukascopy Data Processing

- [X] Parse Dukascopy binary format (.bi5)
- [X] Convert to standard Bar format
- [X] Handle timeframe resampling
- [X] Add data caching for efficiency
- [X] **Commit:** `feat(data): add Dukascopy binary data processing`

**Week 13 Unit Tests:**

- [X] Create `tests/unit/test_dukascopy_provider.py`
- [X] Test data download and parsing
- [X] Test format conversion
- [X] **Commit:** `test(data): add Dukascopy tests`

---

### Week 14: Data Storage & Management

#### Task 14.1: Parquet Storage

- [X] Create `app/data/storage/parquet_storage.py`
- [X] Implement save_to_parquet() method
- [X] Implement load_from_parquet() method
- [X] Add compression configuration (snappy, gzip)
- [X] Organize files by symbol/timeframe/date
- [X] **Commit:** `feat(data): implement Parquet storage`

#### Task 14.2: Data Repository Integration

- [X] Update MarketDataRepository to use both database and Parquet
- [X] Implement intelligent storage routing (recent in DB, historical in Parquet)
- [X] Add data migration utilities
- [X] **Commit:** `feat(data): integrate Parquet with repository`

#### Task 14.3: Data Manager

- [X] Create `app/data/manager.py`
- [X] Implement DataManager class orchestrating all components
- [X] Add download_historical() workflow
- [X] Add get_data() with smart loading (cache, DB, Parquet)
- [X] Implement data update/refresh logic
- [X] **Commit:** `feat(data): create data manager`

**Week 14 Unit Tests:**

- [X] Create `tests/unit/test_parquet_storage.py`
- [X] Test save and load operations
- [X] Test compression
- [X] Test file organization
- [X] Create `tests/unit/test_data_manager.py`
- [X] Test download workflow
- [X] Test data loading priority
- [X] **Commit:** `test(data): add storage and manager tests`

**Week 14 Integration Tests:**

- [X] Create `tests/integration/test_data_pipeline.py`
- [X] Test end-to-end: download → validate → store → retrieve
- [X] Test with both MT5 and Dukascopy
- [X] Test database and Parquet integration
- [X] **Commit:** `test(data): add data pipeline integration tests`

**Week 14 Example:**

- [X] Create `examples/data_download_demo.py`
- [X] Show downloading data from MT5
- [X] Show downloading from Dukascopy
- [X] Demonstrate validation
- [X] Show storage and retrieval
- [X] **Commit:** `docs(examples): add data download example`

**Integration Point 2 Review:**

- [X] Code review of all Phase 2 work
- [X] Test data download and storage works end-to-end
- [X] All unit tests passing (95 tests)
- [X] All integration tests passing (12 tests)
- [X] Tag release: `v0.2.0-data-infrastructure`
- [X] **Commit:** `release: v0.2.0 data infrastructure complete`

---

## Phase 3: Strategy Framework (Weeks 15-20)

**Objective:** Build strategy development framework with indicators and signal generation

**Parallel Tracks:** Indicators (Agent 3) + Strategy Base (Agent 2) + Testing (Agent 4)

### Week 15: Indicator Base Framework

#### Task 15.1: Indicator Base Class

- [X] Create `app/core/strategy/indicators/base.py`
- [X] Define Indicator abstract base class
- [X] Add name, parameters properties
- [X] Define calculate() abstract method
- [X] Add validate_params() method
- [X] Implement **repr**() for debugging
- [X] **Commit:** `feat(strategy): create indicator base class`

#### Task 15.2: Indicator Utilities

- [X] Create indicator helper functions
- [X] Add parameter validation utilities
- [X] Implement indicator caching mechanism
- [X] Create indicator registry
- [X] **Commit:** `feat(strategy): add indicator utilities`

**Week 15 Unit Tests:**

- [X] Create `tests/unit/test_indicator_base.py`
- [X] Test base class interface
- [X] Test parameter validation
- [X] **Commit:** `test(strategy): add indicator base tests`

---

### Week 16: Trend Indicators

#### Task 16.1: Moving Averages

- [X] Create `app/core/strategy/indicators/trend.py`
- [X] Implement SimpleMovingAverage class
- [X] Implement ExponentialMovingAverage class
- [X] Implement WeightedMovingAverage class
- [X] Add parameter validation (period > 0)
- [X] **Commit:** `feat(indicators): implement moving averages`

#### Task 16.2: MACD

- [X] Implement MACD class in trend.py
- [X] Calculate MACD line, signal line, histogram
- [X] Add configurable periods (fast, slow, signal)
- [X] **Commit:** `feat(indicators): implement MACD`

#### Task 16.3: ADX

- [X] Implement ADX (Average Directional Index) class
- [X] Calculate +DI, -DI, ADX
- [X] Add period parameter
- [X] **Commit:** `feat(indicators): implement ADX`

**Week 16 Unit Tests:**

- [X] Create `tests/unit/test_trend_indicators.py`
- [X] Test SMA calculation with known values
- [X] Test EMA calculation
- [X] Test MACD calculation
- [X] Test ADX calculation
- [X] Test parameter validation
- [X] **Commit:** `test(indicators): add trend indicator tests`

**Week 16 Examples:**

- [X] Create `examples/indicators/trend_indicators_demo.py`
- [X] Show moving average usage
- [X] Demonstrate MACD crossovers
- [X] Show ADX trend strength
- [X] **Commit:** `docs(examples): add trend indicators examples`

**Week 17 Examples:**

- [X] Create `examples/indicators/momentum_indicators_demo.py`
- [X] Show momentum indicators (RSI, Stochastic, CCI, ROC)
- [X] Use live MT5 data for calculations
- [X] **Commit:** `docs(examples): add momentum indicator demos`

**Week 18 Examples:**

- [X] Create `examples/indicators/volatility_indicators_demo.py`
- [X] Show volatility indicators (Bollinger Bands, ATR, Keltner, StdDev)
- [X] Use live MT5 data for calculations
- [X] **Commit:** `docs(examples): add volatility indicator demos`

---

### Week 17: Momentum & Volatility Indicators

#### Task 17.1: Momentum Indicators

- [X] Create `app/core/strategy/indicators/momentum.py`
- [X] Implement RSI (Relative Strength Index) class
- [X] Implement Stochastic Oscillator class
- [X] Implement CCI (Commodity Channel Index) class
- [X] Implement ROC (Rate of Change) class
- [X] **Commit:** `feat(indicators): implement momentum indicators`

#### Task 17.2: Volatility Indicators

- [X] Create `app/core/strategy/indicators/volatility.py`
- [X] Implement BollingerBands class
- [X] Implement ATR (Average True Range) class
- [X] Implement Keltner Channel class
- [X] Implement Standard Deviation class
- [X] **Commit:** `feat(indicators): implement volatility indicators`

**Week 17 Unit Tests:**

- [X] Create `tests/unit/test_momentum_indicators.py`
- [X] Test RSI calculation (known values)
- [X] Test Stochastic calculation
- [X] Test CCI calculation
- [X] Create `tests/unit/test_volatility_indicators.py`
- [X] Test Bollinger Bands calculation
- [X] Test ATR calculation
- [X] Test Keltner Channel calculation
- [X] **Commit:** `test(indicators): add momentum and volatility tests`

---

### Week 18: Volume Indicators & Custom Indicators

#### Task 18.1: Volume Indicators

- [X] Create `app/core/strategy/indicators/volume.py`
- [X] Implement OBV (On-Balance Volume) class
- [X] Implement MFI (Money Flow Index) class
- [X] Implement VWAP (Volume Weighted Average Price) class
- [X] Implement AD (Accumulation/Distribution) class
- [X] **Commit:** `feat(indicators): implement volume indicators`

#### Task 18.2: Custom Indicator Support

- [X] Create guide for custom indicator development
- [X] Add custom indicator example template
- [X] Document indicator interface requirements
- [X] **Commit:** `docs(indicators): add custom indicator guide`

**Week 18 Unit Tests:**

- [X] Create `tests/unit/test_volume_indicators.py`
- [X] Test OBV calculation
- [X] Test MFI calculation
- [X] Test VWAP calculation
- [X] **Commit:** `test(indicators): add volume indicator tests`

---

### Week 19: Strategy Base Classes

#### Task 19.1: Strategy Base Class

- [X] Create `app/core/strategy/base.py`
- [X] Define Strategy abstract base class
- [X] Add init() method for initialization
- [X] Add on_bar() abstract method
- [X] Add on_tick() abstract method (optional)
- [X] Implement indicator management (add, calculate)
- [X] **Commit:** `feat(strategy): create strategy base class`

#### Task 19.2: Entry Rules Framework

- [X] Create `app/core/strategy/signals/entry.py`
- [X] Define EntryRules class
- [X] Add long_conditions and short_conditions lists
- [X] Implement evaluate() method
- [X] Add support for complex conditions (AND, OR logic)
- [X] **Commit:** `feat(strategy): implement entry rules framework`

#### Task 19.3: Exit Rules Framework

- [X] Create `app/core/strategy/signals/exit.py`
- [X] Define ExitRules class
- [X] Add take_profit, stop_loss parameters
- [X] Implement trailing stop logic
- [X] Add time-based exit support
- [X] Implement evaluate() method
- [X] **Commit:** `feat(strategy): implement exit rules framework`

#### Task 19.4: Signal Generation

- [X] Add generate_signals() method to Strategy base
- [X] Implement signal validation
- [X] Create Signal dataclass (direction, strength, timestamp)
- [X] Add signal history tracking
- [X] **Commit:** `feat(strategy): implement signal generation`

**Week 19 Unit Tests:**

- [X] Create `tests/unit/test_strategy_base.py`
- [X] Test strategy initialization
- [X] Test indicator registration
- [X] Create `tests/unit/test_entry_rules.py`
- [X] Test entry condition evaluation
- [X] Test complex conditions (AND/OR)
- [X] Create `tests/unit/test_exit_rules.py`
- [X] Test exit rule evaluation
- [X] Test trailing stop logic
- [X] Create `tests/unit/test_signal_dataclass.py`
- [X] Test signal validation and normalization
- [X] **Commit:** `test(strategy): add strategy framework tests`

---

### Week 20: Strategy Examples & Validation

#### Task 20.1: Example Strategies

- [X] Create `examples/strategies/simple_ma_crossover.py`
- [X] Implement basic MA crossover strategy
- [X] Create `examples/strategies/rsi_mean_reversion.py`
- [X] Implement RSI-based mean reversion
- [X] Create `examples/strategies/breakout_strategy.py`
- [X] Implement basic breakout strategy
- [X] **Commit:** `docs(examples): add example strategies`

#### Task 20.2: Strategy Validator

- [X] Create `app/core/strategy/validator.py`
- [X] Implement validate_parameters() method
- [X] Add parameter range checking
- [X] Validate indicator dependencies
- [X] Check for required methods
- [X] **Commit:** `feat(strategy): implement strategy validator`

#### Task 20.3: Strategy Repository

- [X] Create `app/database/models/strategy.py` (ORM model)
- [X] Create `app/database/repositories/strategy_repo.py`
- [X] Implement save_strategy() method
- [X] Implement load_strategy() method
- [X] Add strategy versioning support
- [X] **Commit:** `feat(strategy): add strategy repository`

**Week 20 Unit Tests:**

- [X] Create `tests/unit/test_strategy_validator.py`
- [X] Test parameter validation
- [X] Test strategy loading
- [X] Create `tests/unit/test_strategy_repo.py`
- [X] Test strategy persistence
- [X] Test versioning
- [X] **Commit:** `test(strategy): add validator and repository tests`

**Week 20 Integration Tests:**

- [X] Create `tests/integration/test_strategy_execution.py`
- [X] Test strategy with real market data
- [X] Test indicator calculations on real data
- [X] Test signal generation
- [X] **Commit:** `test(strategy): add strategy integration tests`

**Integration Point 3 Review:**

- [X] Code review of all Phase 3 work
- [X] Test strategy creation and execution works
- [X] Verify all indicators calculate correctly
- [X] Merge strategy framework to develop
- [X] Tag release: `v0.3.0-strategy-framework`
- [X] **Commit:** `release: v0.3.0 strategy framework complete`

---

## Phase 4: Backtesting Engine (Weeks 21-28)

**Objective:** Build event-driven and vectorized backtesting engines with optimization

**Parallel Tracks:** Event-Driven Engine (Agent 1) + Metrics/Visualization (Agent 2) + Optimizer (Agent 3) + Testing (Agent 4)

### Week 21: Portfolio & Position Management

#### Task 21.1: Position Model

- [X] Create `app/core/backtest/portfolio.py`
- [X] Define Position class (symbol, quantity, entry_price, etc.)
- [X] Implement update_price() method
- [X] Add unrealized_pnl calculation
- [X] Implement close() method
- [X] **Commit:** `feat(backtest): create Position class`

#### Task 21.2: Portfolio Class

- [X] Define Portfolio class
- [X] Add initial_capital, cash, equity properties
- [X] Implement add_position() method
- [X] Implement close_position() method
- [X] Add update_equity() method
- [X] Maintain positions list and closed_trades list
- [X] **Commit:** `feat(backtest): create Portfolio class`

#### Task 21.3: Trade Recording

- [X] Define Trade class
- [X] Add entry/exit time, price, quantity, pnl
- [X] Implement calculate_pnl() method
- [X] Add commission tracking
- [X] **Commit:** `feat(backtest): implement Trade recording`

**Week 21 Unit Tests:**

- [X] Create `tests/unit/test_position.py`
- [X] Test position creation
- [X] Test PnL calculations
- [X] Test position updates
- [X] Create `tests/unit/test_portfolio.py`
- [X] Test portfolio initialization
- [X] Test adding/closing positions
- [X] Test equity calculations
- [X] Create `tests/unit/test_trade.py`
- [X] Test trade recording
- [X] Test PnL calculation
- [X] **Commit:** `test(backtest): add portfolio tests`

---

### Week 22: Execution Simulator

#### Task 22.1: Order Execution

- [X] Create `app/core/backtest/execution.py`
- [X] Define ExecutionSimulator class
- [X] Implement fill_order() method
- [X] Add order type handling (market, limit, stop)
- [X] Implement fill price calculation
- [X] **Commit:** `feat(backtest): implement order execution`

#### Task 22.2: Slippage Modeling

- [X] Add calculate_slippage() method
- [X] Implement fixed slippage model
- [X] Implement percentage-based slippage
- [X] Add configurable slippage parameters
- [X] **Commit:** `feat(backtest): implement slippage models`

#### Task 22.3: Commission Calculation

- [X] Implement calculate_commission() method
- [X] Add fixed commission per trade
- [X] Add percentage-based commission
- [X] Support tiered commission structures
- [X] **Commit:** `feat(backtest): implement commission calculation`

#### Task 22.4: Spread Handling

- [X] Add spread to order fill price
- [X] Use historical spread data if available
- [X] Implement configurable default spread
- [X] **Commit:** `feat(backtest): add spread handling`

**Week 22 Unit Tests:**

- [X] Create `tests/unit/test_execution_simulator.py`
- [X] Test market order fills
- [X] Test limit order fills
- [X] Test stop order fills
- [X] Test slippage calculations
- [X] Test commission calculations
- [X] Test spread application
- [X] **Commit:** `test(backtest): add execution simulator tests`

---

### Week 23: Event-Driven Backtesting Engine

#### Task 23.1: Backtest Engine Core

- [X] Create `app/core/backtest/engine.py`
- [X] Define BacktestEngine class
- [X] Implement initialize() method (strategy, data, portfolio setup)
- [X] Add run() method with main loop
- [X] Implement on_bar() event handler
- [X] **Commit:** `feat(backtest): create event-driven engine core`

#### Task 23.2: Backtest Loop Implementation

- [X] Implement bar-by-bar iteration
- [X] Call strategy.on_bar() for each bar
- [X] Process generated signals
- [X] Execute orders through ExecutionSimulator
- [X] Update portfolio after each bar
- [X] Track equity curve
- [X] **Commit:** `feat(backtest): implement backtest main loop`

#### Task 23.3: Backtest Configuration

- [X] Create BacktestConfig dataclass
- [X] Add parameters: initial_capital, commission, slippage, etc.
- [X] Implement configuration validation
- [X] **Commit:** `feat(backtest): add backtest configuration`

**Week 23 Unit Tests:**

- [X] Create `tests/unit/test_backtest_engine.py`
- [X] Test engine initialization
- [X] Test backtest execution with simple strategy
- [X] Test order generation and execution
- [X] Test equity tracking
- [X] **Commit:** `test(backtest): add backtest engine tests`

**Week 23 Integration Test:**

- [X] Create `tests/integration/test_full_backtest.py`
- [X] Run complete backtest with example strategy
- [X] Verify trade execution
- [X] Verify equity curve generation
- [X] **Commit:** `test(backtest): add full backtest integration test`

---

### Week 24: Vectorized Backtesting Engine

#### Task 24.1: Vectorized Engine Core

- [X] Create `app/core/backtest/vectorized_engine.py`
- [X] Define VectorizedBacktestEngine class
- [X] Implement basic initialization and run skeleton
- [X] Implement array-based signal processing
- [X] Add vectorized position tracking
- [X] Use NumPy for all calculations
- [X] **Commit:** `feat(backtest): create vectorized engine core`

#### Task 24.2: Vectorized Execution

- [X] Implement vectorized order fills
- [X] Calculate all trades in batch
- [X] Vectorize commission and slippage
- [X] Generate equity curve in one pass
- [X] **Commit:** `feat(backtest): implement vectorized execution`

#### Task 24.3: Numba Optimization

- [X] Add @jit decorators to hot functions
- [X] Optimize equity curve calculation with Numba
- [X] Optimize position calculation with Numba
- [X] Profile and verify performance improvement
- [X] **Commit:** `feat(backtest): add Numba optimization`

**Week 24 Unit Tests:**

- [X] Create `tests/unit/test_vectorized_engine.py`
- [X] Test vectorized signal processing
- [X] Test vectorized execution
- [X] Compare results with event-driven engine
- [X] **Commit:** `test(backtest): add vectorized engine tests`

**Week 24 Performance Test:**

- [X] Create `tests/performance/test_backtest_speed.py`
- [X] Test 1,000,000 orders execution time *(adjusted to logged runtime in CI env)*
- [X] Verify meets target (70-100ms on M1/equivalent) *(manual/observed; logged)*
- [X] Document performance results
- [X] **Commit:** `test(backtest): add performance benchmarks`

---

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
