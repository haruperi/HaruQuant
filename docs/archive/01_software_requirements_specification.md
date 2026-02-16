# Software Requirements Specification (SRS)

## Hybrid C++/Python Quantitative Trading & Backtesting System

| Field               | Detail                                      |
|---------------------|---------------------------------------------|
| **Document ID**     | SRS-HQTBS-001                               |
| **Version**         | 1.0.0                                       |
| **Date**            | 2026-02-10                                  |
| **Status**          | Draft — Planning Phase                      |
| **Classification**  | Internal / Confidential                     |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Architecture](#3-system-architecture)
4. [Module Specifications](#4-module-specifications)
   - 4.1 [Foundation Layer](#41-foundation-layer)
   - 4.2 [Data Infrastructure](#42-data-infrastructure)
   - 4.3 [Strategy Framework](#43-strategy-framework)
   - 4.4 [Trading Framework](#44-trading-framework)
   - 4.5 [C++ Core Engine](#45-c-core-engine)
   - 4.6 [Bridge Layer (Nanobind)](#46-bridge-layer-nanobind)
   - 4.7 [Backtesting Engine](#47-backtesting-engine)
   - 4.8 [Risk Management System](#48-risk-management-system)
   - 4.9 [Live Trading System](#49-live-trading-system)
   - 4.10 [Paper Trading System](#410-paper-trading-system)
   - 4.11 [Notification System](#411-notification-system)
   - 4.12 [API Layer](#412-api-layer)
   - 4.13 [Frontend UI](#413-frontend-ui)
5. [Cross-Cutting Concerns](#5-cross-cutting-concerns)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [External Interfaces](#7-external-interfaces)
8. [Data Requirements](#8-data-requirements)
9. [Constraints & Assumptions](#9-constraints--assumptions)
10. [Acceptance Criteria](#10-acceptance-criteria)
11. [Appendices](#11-appendices)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the complete functional and non-functional requirements for a hybrid C++/Python quantitative trading and backtesting system. The system follows a "Sandwich Architecture" where a high-performance C++20 core handles computation, a Nanobind bridge provides zero-copy interoperability, and a Python layer manages strategy logic, ML integration, orchestration, and user interfaces.

This document serves as the authoritative reference for all subsequent design, implementation, and testing activities.

### 1.2 Scope

The system encompasses:

- A C++20 core engine for event processing, order matching, and state management
- A Python strategy and orchestration layer with ML integration capability
- A Nanobind bridge for zero-copy C++ ↔ Python interoperability
- Event-driven and vectorized backtesting engines with multi-asset support
- Live trading via MT5 broker gateway (MQL5 EA ↔ ZeroMQ bridge)
- Paper trading with simulated execution
- Parameter optimization with distributed agent architecture (Ray)
- Monte Carlo simulation, walk-forward optimization, and edge discovery
- Risk management with regime detection, position sizing, and portfolio allocation
- A desktop UI (PySide6 + PyQtGraph) with real-time charting
- A notification system (Telegram, Email)
- A REST API for frontend access to all backend functionality

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|-----------|
| **ATR** | Average True Range — a volatility indicator |
| **DXA** | Device-independent units used in document formatting |
| **EA** | Expert Advisor — an automated trading program in MQL5 |
| **GIL** | Global Interpreter Lock — Python's threading limitation |
| **HDF5** | Hierarchical Data Format version 5 — binary data storage format |
| **IPC** | Inter-Process Communication |
| **mmap** | Memory-mapped file I/O |
| **MQL5** | MetaQuotes Language 5 — scripting language for MT5 |
| **MT5** | MetaTrader 5 — retail trading platform |
| **PIT** | Point-in-Time — data available at a specific historical moment |
| **PnL** | Profit and Loss |
| **SRS** | Software Requirements Specification |
| **WFO** | Walk-Forward Optimization |
| **ZMQ** | ZeroMQ — high-performance asynchronous messaging library |

### 1.4 References

- IEEE 830-1998 — Recommended Practice for Software Requirements Specifications
- MT5 MQL5 Standard Library Documentation
- Nanobind Documentation (v2.x)
- Ray Framework Documentation
- PySide6 / Qt6 Documentation

### 1.5 Document Conventions

Requirements are identified using the format `[MODULE-CATEGORY-NNN]` where:

- `MODULE` = abbreviated module name (e.g., `FND` for Foundation, `BKT` for Backtesting)
- `CATEGORY` = `FR` (Functional), `NFR` (Non-Functional), `IF` (Interface), `DR` (Data)
- `NNN` = sequential number

Priority levels: **P0** (Must Have — launch blocker), **P1** (Should Have — high value), **P2** (Nice to Have — deferred acceptable).

---

## 2. Overall Description

### 2.1 Product Perspective

This system replaces a prior pure-Python trading system. The architectural migration to a hybrid C++/Python model is driven by performance requirements for multi-asset backtesting (50+ symbols), distributed optimization (10,000+ parameter combinations), and sub-millisecond execution latency for live trading signal processing.

The system is a standalone desktop application with optional API exposure. It is not a web application, though the API layer permits future web frontend development.

### 2.2 User Classes and Characteristics

| User Class | Description | Technical Level |
|-----------|-------------|-----------------|
| **Strategy Developer** | Writes and tests trading strategies in Python. Primary user. | Advanced Python, intermediate statistics |
| **Quantitative Researcher** | Performs edge discovery, Monte Carlo analysis, parameter optimization. | Advanced statistics and programming |
| **System Administrator** | Manages infrastructure, broker connections, data pipelines. | Systems administration, DevOps |
| **Live Trader** | Monitors live and paper trading, intervenes manually when needed. | Intermediate technical, advanced trading |

### 2.3 Operating Environment

| Component | Requirement |
|-----------|-------------|
| **Operating System** | Windows 10/11 (primary — MT5 requirement), Linux (backtesting/optimization only) |
| **CPU** | Minimum 8 cores recommended; 16+ cores for distributed optimization |
| **RAM** | Minimum 16 GB; 32+ GB for multi-asset tick-level backtesting |
| **Storage** | SSD required; 500 GB+ for multi-year tick data |
| **Python** | 3.11+ |
| **C++ Compiler** | C++20 compatible (MSVC 2022+, GCC 12+, Clang 15+) |
| **MT5 Terminal** | Required for live trading and MT5 data provider |

### 2.4 Design and Implementation Constraints

- **C-01**: The C++ core must compile on both Windows (MSVC) and Linux (GCC/Clang) for backtesting portability.
- **C-02**: Live trading requires Windows due to the MT5 terminal dependency.
- **C-03**: The Python GIL must not bottleneck the C++ event loop. All performance-critical computation stays in C++.
- **C-04**: Strategy code must remain in Python for accessibility and ML library integration.
- **C-05**: The system must support deterministic replay — identical inputs must produce identical outputs for any given code + data version.
- **C-06**: All monetary calculations must use fixed-point or decimal arithmetic to avoid floating-point rounding errors in PnL calculations.

### 2.5 Assumptions and Dependencies

- **A-01**: The user has a valid MT5 broker account with API access enabled.
- **A-02**: Historical data from Dukascopy or MT5 is available for the desired symbols and timeframes.
- **A-03**: Nanobind supports all required data type exposures at the time of development.
- **A-04**: The Ray framework supports the target deployment platforms.
- **A-05**: Broker-specific margin and commission schedules are available and can be configured.

---

## 3. System Architecture

### 3.1 The "Sandwich" Architecture

The system is organized into three primary layers with supporting infrastructure.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 4: USER INTERFACE                          │
│  PySide6 (Qt6) + PyQtGraph  |  REST API (FastAPI)                  │
│  Signal/Slot UI updates      |  WebSocket live data streaming       │
├─────────────────────────────────────────────────────────────────────┤
│                    LAYER 3: PYTHON CONTROL TOWER                    │
│  Strategy Logic  |  ML Integration  |  Orchestration  |  Ray Agents │
│  Risk Manager    |  Notifications   |  Config Manager  |  CLI       │
├─────────────────────────────────────────────────────────────────────┤
│                    LAYER 2: BRIDGE (Nanobind)                       │
│  Zero-Copy Exposure  |  Read-Only Properties  |  Callback Dispatch  │
│  Type Marshalling    |  Lifetime Management   |  Error Propagation  │
├─────────────────────────────────────────────────────────────────────┤
│                    LAYER 1: C++ CORE ENGINE                         │
│  Event Loop (Priority Queue)  |  Matching Engine  |  State Manager  │
│  mmap Data Reader  |  Order Manager  |  Position Tracker            │
│  Slippage/Commission/Swap Models  |  ZMQ Broadcaster               │
├─────────────────────────────────────────────────────────────────────┤
│                    LAYER 0: DATA STORAGE                            │
│  HDF5 / Apache Parquet  |  SQLite/PostgreSQL (metadata)            │
│  Memory-Mapped File I/O  |  Data Versioning Registry               │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow — Single Tick Processing

```
1. C++ Core    → Pulls next tick from Priority Queue (lowest timestamp across all symbols)
2. C++ Core    → Updates internal Ask/Bid/Spread variables for the symbol
3. C++ Core    → Checks pending orders against new price (stop/limit triggers)
4. C++ Core    → Updates unrealized PnL for all open positions
5. Bridge      → Calls Python Strategy.on_tick() callback
6. Python      → User strategy logic executes (e.g., if RSI > 70: engine.sell())
7. Bridge      → engine.sell() invokes C++ OrderManager directly via memory pointer
8. C++ Core    → OrderManager calculates slippage, creates position, updates equity
9. C++ Core    → Pushes state update to ZMQ broadcaster (for UI / logging)
10. C++ Core   → Advances to next tick in Priority Queue
```

### 3.3 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Core Engine | C++20 | Maximum event loop speed; avoids Python interpreter overhead |
| Bridge | Nanobind 2.x | Lower overhead than pybind11; zero-copy data exposure |
| Strategy Layer | Python 3.11+ | ML ecosystem (PyTorch, scikit-learn); developer accessibility |
| Parallelism | Ray | Industry standard for distributed compute; agent architecture |
| Data Storage (time-series) | HDF5 / Apache Parquet | Columnar format; mmap compatible; fast partial reads |
| Data Storage (metadata) | SQLite (local) / PostgreSQL (shared) | Structured metadata, backtest results, user settings |
| Messaging (IPC) | ZeroMQ | Microsecond latency; decouples engine from UI |
| UI Framework | PySide6 (Qt6) | Native look; multi-window layouts; industry standard for trading GUIs |
| Charting | PyQtGraph | GPU-accelerated scientific/financial plotting |
| API | FastAPI | Async Python; auto-generated OpenAPI docs |
| Build System (C++) | CMake 3.25+ | Cross-platform; Nanobind integration support |
| C++ Package Manager | vcpkg or Conan 2 | Dependency management for ZMQ, HDF5, spdlog, etc. |
| C++ Testing | Google Test + Google Benchmark | Unit testing and micro-benchmarking |
| Python Testing | pytest + hypothesis | Property-based testing for numerical correctness |
| CI/CD | GitHub Actions | Multi-platform build matrix (Windows MSVC + Linux GCC) |
| C++ Logging | spdlog | High-performance; structured logging; integrates with Python layer |

### 3.4 Module Dependency Map

```
Foundation ──────────────────────────────────────────────────────┐
  ├── Logging (spdlog C++ ↔ Python logging bridge)              │
  ├── Exception Handling                                        │
  ├── Configuration Management                                  │
  ├── Utilities                                                 │
  ├── Security & Secrets Management                             │
  └── Database (schema + migrations)                            │
                                                                │
Data Infrastructure ────────────────────────────────────────────┤
  ├── Data Models (Tick, Bar, Symbol spec)                      │
  ├── Data Validation Pipeline                                  │
  ├── Data Providers (MT5, Dukascopy)                           │
  ├── Data Storage & Management (HDF5/Parquet + mmap)           │
  └── Data Versioning & Lineage                                 │
                                                                │
C++ Core Engine ────────────────────────────────────────────────┤
  ├── Event Loop (Priority Queue)                               │
  ├── Matching Engine                                           │
  ├── State Manager (Account, Equity, Positions)                │
  ├── Order Manager (all order types)                           │
  ├── Execution Models (Slippage, Commission, Swap, Spread)     │
  ├── Currency Conversion Engine                                │
  ├── Margin Calculator                                         │
  ├── mmap Data Reader                                          │
  └── ZMQ Broadcaster                                           │
                                                                │
Bridge Layer (Nanobind) ────────────────────────────────────────┤
  ├── Type Exposure (C++ → Python read-only properties)         │
  ├── Callback System (C++ → Python on_tick, on_bar, etc.)      │
  ├── Command Interface (Python → C++ buy, sell, modify, etc.)  │
  └── Lifetime & Memory Safety Manager                          │
                                                                │
Strategy Framework ─────────────────────────────────────────────┤
  ├── Indicators (Trend, Momentum, Volatility, Volume)          │
  ├── Strategy Base Class                                       │
  ├── Multi-Timeframe Data Access                               │
  └── Concrete Strategies                                       │
                                                                │
Trading Framework (Unified Interface) ──────────────────────────┤
  ├── Account Management                                        │
  ├── Order Management                                          │
  ├── Position Management                                       │
  ├── Symbol Management                                         │
  ├── Deal / History Order                                      │
  └── Trade Management                                          │
                                                                │
Backtesting Engine ─────────────────────────────────────────────┤
  ├── Event-Driven Engine                                       │
  ├── Vectorized Engine                                         │
  ├── Multi-Asset Portfolio Engine                               │
  ├── Execution Simulator                                       │
  ├── Performance Metrics                                       │
  ├── Parameter Optimization (Grid, Bayesian)                   │
  ├── Monte Carlo & Stress Testing                              │
  ├── Walk-Forward Optimization                                 │
  ├── Edge Lab                                                  │
  ├── Visualization & Reporting                                 │
  ├── Backtest Storage                                          │
  └── Agent Architecture (Ray + C++ instances)                  │
                                                                │
Risk Management System ─────────────────────────────────────────┤
  ├── Risk Limits Configuration                                 │
  ├── Position Sizing                                           │
  ├── Regime Detection                                          │
  ├── Portfolio Allocation                                      │
  ├── Risk Governor                                             │
  └── Risk Monitoring                                           │
                                                                │
Live Trading System ────────────────────────────────────────────┤
  ├── Live Trading Engine Core                                  │
  ├── Event Handlers                                            │
  ├── Signal-to-Order Flow                                      │
  ├── Emergency Shutdown                                        │
  ├── State Reconciliation                                      │
  ├── Broker Gateway (MT5 via MQL5 EA + ZMQ)                    │
  └── Portfolio Management                                      │
                                                                │
Paper Trading System ───────────────────────────────────────────┤
  ├── Paper Trading Mode (simulated fills)                      │
  ├── Trading Service                                           │
  ├── Records Keeping                                           │
  └── Account Snapshots                                         │
                                                                │
Notification System ────────────────────────────────────────────┤
  ├── Notification Models                                       │
  ├── Channel Interface                                         │
  ├── Telegram Channel                                          │
  └── Email Channel                                             │
                                                                │
API Layer ──────────────────────────────────────────────────────┤
  └── REST API (FastAPI) — exposes all backend functionality    │
                                                                │
Frontend UI ────────────────────────────────────────────────────┘
  ├── PySide6 Main Window
  ├── PyQtGraph Charting
  ├── Multi-Chart Visualizer
  └── Strategy Editor / Dashboard
```

---

## 4. Module Specifications

### 4.1 Foundation Layer

#### 4.1.1 Logging System

**Description**: A dual-language logging system with spdlog (C++) for the core engine and Python's `logging` module for the strategy/orchestration layer. Both feed into a unified log stream with structured output.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FND-FR-001 | The C++ core shall use spdlog for all logging within the engine. | P0 |
| FND-FR-002 | The Python layer shall use a custom logging configuration built on the standard `logging` module. | P0 |
| FND-FR-003 | The system shall support log levels: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL. | P0 |
| FND-FR-004 | Log output shall include timestamp (microsecond resolution), log level, module name, thread ID, and message. | P0 |
| FND-FR-005 | The system shall support simultaneous output to console, rotating file, and structured JSON file. | P0 |
| FND-FR-006 | C++ spdlog messages shall be routable to the Python logging system via the bridge for unified log viewing. | P1 |
| FND-FR-007 | Log rotation shall be configurable by file size (default 50 MB) and retention count (default 10 files). | P0 |
| FND-FR-008 | Performance-critical C++ code paths shall use asynchronous logging to avoid blocking the event loop. | P0 |
| FND-FR-009 | The system shall provide a log filtering mechanism by module, level, and keyword pattern. | P1 |

#### 4.1.2 Exception Handling

**Description**: A structured exception hierarchy spanning both C++ and Python with proper cross-language error propagation.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FND-FR-010 | The system shall define a base exception hierarchy with categories: DataError, TradingError, ConfigError, BrokerError, EngineError, ValidationError. | P0 |
| FND-FR-011 | C++ exceptions shall be translated to corresponding Python exceptions at the Nanobind bridge boundary. | P0 |
| FND-FR-012 | All exceptions shall carry: error code, human-readable message, module origin, timestamp, and optional context dictionary. | P0 |
| FND-FR-013 | Unhandled C++ exceptions shall not crash the Python process; they shall be caught at the bridge boundary and re-raised as Python exceptions. | P0 |
| FND-FR-014 | The system shall provide validation exception classes for: data validation, trading parameter validation, configuration validation, and input validation. | P0 |

#### 4.1.3 Configuration Management

**Description**: A centralized, validated, environment-aware configuration system that manages all system parameters from a single source of truth.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FND-FR-015 | The system shall use TOML as the primary configuration file format. | P0 |
| FND-FR-016 | Configuration shall support hierarchical structure with sections for: engine, data, strategies, broker, risk, notifications, logging, UI, database, and optimization. | P0 |
| FND-FR-017 | The system shall support environment-specific configuration overlays (development, testing, production) that merge with a base configuration. | P0 |
| FND-FR-018 | All configuration values shall be validated against a schema at application startup, with clear error messages for invalid entries. | P0 |
| FND-FR-019 | Sensitive configuration values (API keys, broker credentials) shall be loadable from environment variables or an encrypted secrets store, never stored in plain text config files. | P0 |
| FND-FR-020 | The system shall support runtime configuration reload for non-critical parameters (e.g., log level, UI refresh rate) without restarting the application. | P1 |
| FND-FR-021 | Each configuration parameter shall have a documented default value, acceptable range/type, and description. | P0 |
| FND-FR-022 | C++ core engine parameters shall be readable from the same TOML configuration files via a C++ TOML parser (e.g., toml++). | P0 |

#### 4.1.4 Utilities

**Description**: Common utility functions shared across modules.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FND-FR-023 | DateTime utilities shall handle timezone conversions, market session detection, trading calendar calculations, and bar alignment across timeframes. | P0 |
| FND-FR-024 | Validation utilities shall provide type checking, range validation, and parameter constraint enforcement. | P0 |
| FND-FR-025 | Calculation utilities shall provide pip value calculation, lot size conversion, profit calculation in account currency, and margin requirement computation. | P0 |
| FND-FR-026 | All monetary calculations shall use `Decimal` type (Python) or fixed-point arithmetic (C++) to avoid floating-point precision errors. | P0 |

#### 4.1.5 Security & Secrets Management

**Description**: Secure handling of credentials, API keys, and sensitive configuration data.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FND-FR-027 | The system shall provide a secrets manager that stores and retrieves encrypted credentials using OS-level key storage (Windows Credential Locker / Linux keyring). | P0 |
| FND-FR-028 | Broker API credentials, Telegram bot tokens, email passwords, and database credentials shall never appear in log output, configuration files, or error messages. | P0 |
| FND-FR-029 | The system shall mask sensitive values in all logging output using automatic redaction patterns. | P0 |
| FND-FR-030 | API layer authentication shall use token-based authentication (JWT) with configurable expiration. | P1 |

#### 4.1.6 Database

**Description**: Persistent storage for system metadata, backtest results, user settings, and trading records.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FND-FR-031 | The system shall use SQLAlchemy as the ORM with support for SQLite (local development) and PostgreSQL (shared/production). | P0 |
| FND-FR-032 | The database schema shall include tables for: sessions, backtests, users, user_settings, edge_results, finance_metrics, live_trades, optimizations, simulations, strategies, paper_trades, and account_snapshots. | P0 |
| FND-FR-033 | Database schema migrations shall be managed using Alembic with versioned migration scripts. | P0 |
| FND-FR-034 | The system shall support automated database backup to a configurable location with configurable frequency. | P1 |
| FND-FR-035 | The system shall provide data export functionality in CSV and JSON formats for all database tables. | P1 |
| FND-FR-036 | Database connection pooling shall be configured with appropriate pool size, overflow limits, and connection timeout values. | P0 |

#### 4.1.7 Fault Tolerance & Recovery

**Description**: System-wide resilience strategy for handling failures across all layers.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FND-FR-037 | The system shall implement automatic reconnection with exponential backoff for broker (MT5) disconnections during live trading. | P0 |
| FND-FR-038 | If the C++ core encounters a segmentation fault or unrecoverable error, the bridge shall catch the signal, persist the current state to disk, and notify the user via the notification system. | P0 |
| FND-FR-039 | Distributed worker agents (Ray) shall implement heartbeat monitoring. Dead workers shall be automatically restarted with their assigned parameter set. | P1 |
| FND-FR-040 | All state-changing operations (order execution, position modification) shall be journaled to a write-ahead log before execution for crash recovery. | P0 |
| FND-FR-041 | The live trading engine shall perform state reconciliation with the broker on startup and after any disconnection, comparing local state with broker-reported positions and orders. | P0 |
| FND-FR-042 | The system shall provide a recovery mode that can reconstruct application state from the write-ahead log and database after an unclean shutdown. | P1 |

---

### 4.2 Data Infrastructure

#### 4.2.1 Data Models

**Description**: Core data structures used across the system, defined in both C++ (for the engine) and Python (for the strategy layer) with bridge exposure.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| DAT-FR-001 | The system shall define a `Tick` data model with fields: symbol, timestamp (microsecond), bid, ask, bid_volume, ask_volume, spread. | P0 |
| DAT-FR-002 | The system shall define a `Bar` (OHLCV) data model with fields: symbol, timeframe, timestamp, open, high, low, close, tick_volume, real_volume, spread. | P0 |
| DAT-FR-003 | The system shall define a `SymbolSpecification` model with fields: name, description, digits, point, tick_size, tick_value, contract_size, margin_initial, margin_maintenance, swap_long, swap_short, swap_type, trade_mode, volume_min, volume_max, volume_step, currency_base, currency_profit, currency_margin. | P0 |
| DAT-FR-004 | All data models shall have C++ struct definitions in the core engine and corresponding Python dataclass/Pydantic model definitions exposed via Nanobind. | P0 |
| DAT-FR-005 | The system shall support a unified data abstraction layer that provides both tick-level and bar-level access through a common interface, allowing strategies to be agnostic to the underlying data granularity. | P0 |

#### 4.2.2 Data Validation Pipeline

**Description**: Comprehensive data quality checks to ensure integrity before backtesting or storage.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| DAT-FR-006 | The system shall perform price sanity checks: bid > 0, ask > 0, ask ≥ bid, prices within configurable bounds relative to recent history. | P0 |
| DAT-FR-007 | The system shall detect price gaps exceeding a configurable threshold (default: 10x average bar range). | P0 |
| DAT-FR-008 | The system shall detect price spikes where a single bar's range exceeds a configurable multiple of ATR (default: 5x ATR). | P0 |
| DAT-FR-009 | The system shall detect and report missing timestamps based on the expected bar frequency and market trading hours. | P0 |
| DAT-FR-010 | The system shall detect zero-volume bars and flag them as potentially invalid. | P1 |
| DAT-FR-011 | The system shall detect and remove duplicate timestamps, keeping the last occurrence by default (configurable). | P0 |
| DAT-FR-012 | The system shall perform spread analysis: detect abnormal spread widening (>3x median spread). | P1 |
| DAT-FR-013 | The system shall provide automated data cleaning: fill small gaps via forward-fill or interpolation (configurable), remove duplicates, and optionally filter spikes. | P1 |
| DAT-FR-014 | The system shall generate a data validation report summarizing all detected issues with counts, affected timestamps, and severity levels. | P0 |
| DAT-FR-015 | The validation pipeline shall be configurable per symbol and per data source, as acceptable thresholds differ between FX, metals, and indices. | P1 |

#### 4.2.3 Data Providers

**Description**: Connectors to external data sources for downloading historical and real-time market data.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| DAT-FR-016 | The system shall provide a MetaTrader 5 data provider that downloads historical bars for any symbol and timeframe available in the connected MT5 terminal. | P0 |
| DAT-FR-017 | The system shall provide a Dukascopy data provider that downloads historical tick data from Dukascopy's public data feeds. | P1 |
| DAT-FR-018 | All data providers shall implement a common `DataProvider` interface with methods: `fetch_bars()`, `fetch_ticks()`, `get_available_symbols()`, `get_available_timeframes()`. | P0 |
| DAT-FR-019 | Data providers shall support incremental downloads — only fetching data newer than the latest stored timestamp. | P0 |
| DAT-FR-020 | Data download progress shall be reported via callbacks for UI progress bar integration. | P1 |

#### 4.2.4 Data Storage & Management

**Description**: High-performance storage for time-series market data using columnar formats with memory-mapped access.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| DAT-FR-021 | The system shall store tick and bar data in HDF5 or Apache Parquet format, organized by symbol and timeframe. | P0 |
| DAT-FR-022 | The C++ core shall access stored data via memory-mapped file I/O (mmap) to avoid loading entire datasets into RAM. | P0 |
| DAT-FR-023 | The storage layer shall support columnar access — reading only specific columns (e.g., close prices only) without loading the entire bar record. | P0 |
| DAT-FR-024 | The system shall maintain a data catalog (metadata database) tracking: symbol, timeframe, date range, record count, data source, download timestamp, and data version hash. | P0 |
| DAT-FR-025 | The system shall support data compaction — merging incremental downloads into optimized contiguous files. | P1 |

#### 4.2.5 Data Versioning & Lineage

**Description**: Tracking data snapshots to ensure backtest reproducibility and audit trail.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| DAT-FR-026 | Each data file shall have a version identifier (content hash) stored in the data catalog. | P0 |
| DAT-FR-027 | Every backtest result shall record the data version hash(es) of the data files used, enabling exact reproduction. | P0 |
| DAT-FR-028 | When data is re-downloaded or modified, the previous version shall be preserved (or its hash recorded) so that prior backtest results remain verifiable. | P1 |
| DAT-FR-029 | The system shall provide a `data_lineage` query: given a backtest ID, return the exact data versions, strategy version, and engine version used. | P1 |

---

### 4.3 Strategy Framework

#### 4.3.1 Indicators

**Description**: Technical indicator library implemented in Python (with optional C++ acceleration for compute-intensive indicators).

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| STR-FR-001 | The system shall provide a base `Indicator` class with methods: `calculate()`, `update()` (incremental), `reset()`, and `ready` property. | P0 |
| STR-FR-002 | The system shall provide trend indicators: SMA, EMA, WMA, DEMA, TEMA, HMA, KAMA, Ichimoku, Parabolic SAR, SuperTrend, ADX. | P0 |
| STR-FR-003 | The system shall provide momentum indicators: RSI, Stochastic, MACD, CCI, Williams %R, ROC, MFI, Awesome Oscillator. | P0 |
| STR-FR-004 | The system shall provide volatility indicators: ATR, Bollinger Bands, Keltner Channels, Donchian Channels, Standard Deviation. | P0 |
| STR-FR-005 | The system shall provide volume indicators: OBV, VWAP, Volume Profile, Accumulation/Distribution. | P1 |
| STR-FR-006 | Indicators shall support incremental (streaming) updates for real-time use without recalculating the entire history. | P0 |
| STR-FR-007 | Indicator utility functions shall include: crossover detection, divergence detection, and slope calculation. | P1 |

#### 4.3.2 Strategy

**Description**: Base strategy class and strategy lifecycle management.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| STR-FR-008 | The system shall provide a base `Strategy` class with lifecycle methods: `on_init()`, `on_tick()`, `on_bar()`, `on_trade()`, `on_timer()`, `on_deinit()`. | P0 |
| STR-FR-009 | The strategy base class shall expose engine interfaces: `buy()`, `sell()`, `modify_order()`, `close_position()`, `close_all()`, `account_info()`, `symbol_info()`, `positions()`, `orders()`, `history_orders()`, `history_deals()`. | P0 |
| STR-FR-010 | The strategy base class shall provide `get_bars(symbol, timeframe, count)` for multi-timeframe data access within a single strategy. | P0 |
| STR-FR-011 | Multi-timeframe access shall enforce Point-in-Time (PIT) correctness — a strategy requesting D1 bars during an intraday tick shall only see completed daily bars, never the current incomplete day's high/low/close. | P0 |
| STR-FR-012 | Strategies shall declare their required symbols and timeframes at initialization so the engine can pre-load the necessary data. | P0 |
| STR-FR-013 | The system shall provide concrete starter strategies: Trend Naive (moving average crossover), Mean Reversion Naive (Bollinger Band bounce), Breakout Pending (range breakout with pending orders). | P1 |
| STR-FR-014 | Strategy parameters shall be declared as typed, bounded class attributes with metadata (name, default, min, max, step) for optimization integration. | P0 |

---

### 4.4 Trading Framework

**Description**: A unified trading interface that works identically for backtesting and live trading, mirroring the MQL5 Standard Library structure.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| TRD-FR-001 | The system shall provide an `AccountInfo` class exposing: balance, equity, margin, free_margin, margin_level, profit, currency, leverage, stop_out_level. | P0 |
| TRD-FR-002 | The system shall provide an `OrderManager` supporting order types: MARKET_BUY, MARKET_SELL, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP, BUY_STOP_LIMIT, SELL_STOP_LIMIT. | P0 |
| TRD-FR-003 | Orders shall support parameters: symbol, volume, price, stop_loss, take_profit, deviation (slippage tolerance), type_filling, type_time, expiration, magic_number, comment. | P0 |
| TRD-FR-004 | The system shall provide a `PositionManager` exposing: open positions with entry price, current price, unrealized PnL, volume, swap, commission, magic_number, comment. | P0 |
| TRD-FR-005 | The system shall support trailing stop functionality: fixed distance trailing, ATR-based trailing, step trailing, and custom trailing via callback. | P0 |
| TRD-FR-006 | The system shall provide a `SymbolManager` exposing symbol specifications: digits, point, tick_size, tick_value, spread, contract_size, margin requirements, trading sessions. | P0 |
| TRD-FR-007 | The system shall provide `DealInfo` and `HistoryOrderInfo` classes for accessing closed trade history, including deal type, profit, commission, swap, entry/exit prices and timestamps. | P0 |
| TRD-FR-008 | The trading framework interface shall be identical whether connected to the backtesting engine, paper trading engine, or live trading engine — strategy code shall not require modification to switch modes. | P0 |

#### 4.4.1 Order Types — Complete Specification

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| TRD-FR-009 | Market orders shall execute at the current ask (buy) or bid (sell) with optional maximum slippage deviation. | P0 |
| TRD-FR-010 | Limit orders shall execute only at the specified price or better. Buy limits below current ask, sell limits above current bid. | P0 |
| TRD-FR-011 | Stop orders shall trigger when price reaches the stop level, then execute as market orders. Buy stops above current ask, sell stops below current bid. | P0 |
| TRD-FR-012 | Stop-limit orders shall place a limit order when the stop level is triggered. | P1 |
| TRD-FR-013 | The system shall support order expiration modes: GTC (Good Till Cancel), today (end of trading day), specified datetime. | P0 |
| TRD-FR-014 | The system shall support partial fill handling: fill-or-kill, immediate-or-cancel, return remainder. | P1 |

#### 4.4.2 Currency Conversion Engine

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| TRD-FR-015 | The system shall automatically calculate profit/loss in the account's base currency for all traded symbols, including cross-pairs. | P0 |
| TRD-FR-016 | Currency conversion shall use the appropriate cross-rate at the time of each tick (for backtesting) or real-time rate (for live trading). For example, EURJPY profit in a USD account requires the concurrent USDJPY rate. | P0 |
| TRD-FR-017 | The currency conversion engine shall maintain a dependency graph of required conversion pairs and ensure they are loaded/subscribed during initialization. | P0 |
| TRD-FR-018 | If a required conversion pair is unavailable, the system shall raise a `ConfigError` at initialization with a clear message identifying the missing pair. | P0 |

#### 4.4.3 Margin Calculation & Tracking

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| TRD-FR-019 | The system shall calculate margin requirements for each position based on: symbol contract size, volume, leverage, and current price. | P0 |
| TRD-FR-020 | The system shall track total used margin, free margin, and margin level (equity / margin × 100%) in real-time. | P0 |
| TRD-FR-021 | The system shall enforce margin call level (configurable, default 100%) — preventing new position opens when margin level is below the threshold. | P0 |
| TRD-FR-022 | The system shall simulate stop-out level (configurable, default 50%) — automatically closing the largest losing position when margin level drops below the threshold. | P0 |
| TRD-FR-023 | Margin calculation shall support hedging mode (reduced margin for hedged positions) and netting mode. | P1 |

---

### 4.5 C++ Core Engine

**Description**: The high-performance computation core responsible for event processing, order matching, and state management.

#### 4.5.1 Event Loop

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-001 | The event loop shall use a priority queue ordered by timestamp to process events from all symbols in chronological order. | P0 |
| CPP-FR-002 | The event loop shall support event types: tick, bar_close, order_trigger, timer, custom. | P0 |
| CPP-FR-003 | For multi-asset backtesting, the engine shall not advance to timestamp T2 until all symbols have completed processing for T1 (Global Clock synchronization). | P0 |
| CPP-FR-004 | The event loop shall enforce Point-in-Time (PIT) data correctness — no data from future timestamps shall be accessible during processing of the current timestamp. | P0 |
| CPP-FR-005 | The event loop shall support pause, resume, step-forward (process N events), and stop commands for debugging and interactive use. | P1 |

#### 4.5.2 Matching Engine

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-006 | The matching engine shall evaluate all pending orders against each new tick to determine if trigger conditions are met. | P0 |
| CPP-FR-007 | The matching engine shall calculate execution price including slippage based on the configured slippage model. | P0 |
| CPP-FR-008 | The matching engine shall apply commission based on the configured commission model (per-lot, per-trade, spread markup, or percentage). | P0 |
| CPP-FR-009 | The matching engine shall calculate swap charges/credits at the configured rollover time for positions held overnight. | P0 |
| CPP-FR-010 | The matching engine shall handle gap scenarios — if price gaps past a stop-loss or take-profit level, execution occurs at the gap price (not the stop level), simulating real market behavior. | P0 |

#### 4.5.3 State Manager

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-011 | The state manager shall maintain: account balance, account equity, open positions (with unrealized PnL), pending orders, closed trade history, and cumulative statistics. | P0 |
| CPP-FR-012 | Account equity shall be recalculated on every tick as: balance + sum(unrealized PnL of all open positions). | P0 |
| CPP-FR-013 | The state manager shall emit state change events via the ZMQ broadcaster for UI consumption. | P0 |
| CPP-FR-014 | The state manager shall support serialization/deserialization for checkpoint/restore functionality. | P1 |

#### 4.5.4 Execution Models

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-015 | The system shall provide a slippage model interface with implementations: zero slippage (ideal), fixed slippage (pips), random slippage (uniform distribution within range), volume-dependent slippage, and latency profile-based slippage (e.g., "NY4 Data Center," "News Event Volatility"). | P0 |
| CPP-FR-016 | The system shall provide a commission model interface with implementations: fixed per-lot, fixed per-trade, spread markup, and percentage of trade value. | P0 |
| CPP-FR-017 | The system shall provide a swap model interface that calculates overnight financing charges based on: swap points (long/short), position volume, and holding duration. Swap type shall be configurable (points, percentage, money). | P0 |
| CPP-FR-018 | The system shall provide a spread model interface with implementations: fixed spread, variable spread from historical data, and time-of-day dependent spread. | P0 |

#### 4.5.5 Memory-Mapped Data Reader

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-019 | The data reader shall use mmap to access HDF5/Parquet files without loading them entirely into RAM. | P0 |
| CPP-FR-020 | The data reader shall support lazy loading — only mapping the data chunks needed for the current time window into the virtual address space. | P0 |
| CPP-FR-021 | The data reader shall support concurrent read access from multiple threads/processes for parallel optimization scenarios. | P1 |

#### 4.5.6 ZMQ Broadcaster

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-022 | The C++ core shall publish state updates (equity, new trades, order fills) via ZeroMQ PUB socket. | P0 |
| CPP-FR-023 | Messages shall use a topic-based routing scheme (e.g., `equity`, `trade`, `order`, `tick`) so subscribers can filter. | P0 |
| CPP-FR-024 | The broadcaster shall not block the event loop — messages shall be sent asynchronously with a configurable high-water mark (drop oldest if buffer full). | P0 |

#### 4.5.7 C++ Build System

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-025 | The C++ project shall use CMake 3.25+ as the build system with support for Windows (MSVC) and Linux (GCC/Clang) targets. | P0 |
| CPP-FR-026 | C++ dependencies (ZeroMQ, HDF5, spdlog, toml++, Google Test) shall be managed via vcpkg or Conan 2 with a lock file for reproducible builds. | P0 |
| CPP-FR-027 | The build system shall produce a shared library (.dll / .so) that Nanobind wraps into a Python-importable module. | P0 |
| CPP-FR-028 | The build system shall support Debug and Release configurations with appropriate optimization flags and debug symbols. | P0 |

#### 4.5.8 C++ Memory Safety

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| CPP-FR-029 | All C++ objects exposed to Python via Nanobind shall have clearly defined ownership semantics — the C++ core owns all engine state; Python holds non-owning references. | P0 |
| CPP-FR-030 | The bridge shall invalidate Python references when the underlying C++ object is destroyed, raising a clear error rather than allowing use-after-free. | P0 |
| CPP-FR-031 | The C++ core shall use RAII for all resource management (file handles, sockets, memory allocations). | P0 |
| CPP-FR-032 | Smart pointers (unique_ptr, shared_ptr) shall be used for all heap allocations within the C++ core. Raw owning pointers are prohibited. | P0 |

---

### 4.6 Bridge Layer (Nanobind)

**Description**: The zero-copy interoperability layer connecting C++ and Python.

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BRG-FR-001 | The bridge shall expose C++ engine state (account, positions, orders, symbol info) as read-only Python properties with zero-copy semantics. | P0 |
| BRG-FR-002 | The bridge shall support Python → C++ command dispatch for: buy, sell, modify_order, close_position, close_all, cancel_order. | P0 |
| BRG-FR-003 | The bridge shall support C++ → Python callback dispatch for: on_tick, on_bar, on_trade, on_timer, on_order_event. | P0 |
| BRG-FR-004 | Tick and bar data shall be passed from C++ to Python as read-only memory views (numpy-compatible) without data copying. | P0 |
| BRG-FR-005 | The bridge shall propagate C++ exceptions to Python as typed Python exceptions with full error context. | P0 |
| BRG-FR-006 | The bridge shall handle the Python GIL correctly — releasing the GIL during C++ computation and reacquiring it before Python callbacks. | P0 |
| BRG-FR-007 | The bridge shall provide a Python-side `Engine` class that encapsulates all interactions, serving as the single entry point for strategy code. | P0 |

---

### 4.7 Backtesting Engine

#### 4.7.1 Event-Driven Engine

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-001 | The event-driven engine shall process one event at a time in chronological order, calling strategy callbacks for each event. | P0 |
| BKT-FR-002 | The engine shall support both tick-level and bar-level event granularity, selectable at initialization. | P0 |
| BKT-FR-003 | The engine shall track and record all trades, orders, and position changes with timestamps for post-analysis. | P0 |
| BKT-FR-004 | The engine shall calculate and maintain running equity curve data at configurable intervals (every tick, every bar, or every N events). | P0 |

#### 4.7.2 Vectorized Engine

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-005 | The vectorized engine shall accept pre-computed signal arrays and simulate trades without per-bar callbacks, for maximum speed. | P0 |
| BKT-FR-006 | The vectorized engine shall support: fixed position sizing, stop-loss, take-profit, and basic commission modeling. | P0 |
| BKT-FR-007 | The vectorized engine shall produce results compatible with the same `BacktestResult` structure as the event-driven engine for unified analysis. | P0 |

#### 4.7.3 Multi-Asset Portfolio Engine

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-008 | The portfolio engine shall support simultaneous backtesting of multiple symbols with shared account state (balance, equity, margin). | P0 |
| BKT-FR-009 | The Global Clock shall ensure chronological ordering across all symbols — no symbol advances past a timestamp that other symbols haven't reached. | P0 |
| BKT-FR-010 | The engine shall support symbol cross-dependency — derived data (custom spreads, correlation indices) that update as underlying symbols move. | P1 |
| BKT-FR-011 | The engine shall support mixed data granularity — e.g., M1 bars for one symbol and tick data for another within the same backtest. | P1 |

#### 4.7.4 Performance Metrics

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-012 | Return metrics: total return, annualized return, monthly returns, daily returns, cumulative return series. | P0 |
| BKT-FR-013 | Risk metrics: standard deviation, downside deviation, maximum drawdown (value and duration), average drawdown, Value at Risk (VaR), Conditional VaR. | P0 |
| BKT-FR-014 | Trade metrics: total trades, win rate, average win, average loss, largest win, largest loss, average holding time, profit factor, expectancy per trade. | P0 |
| BKT-FR-015 | Ratio metrics: Sharpe ratio, Sortino ratio, Calmar ratio, Omega ratio, risk-reward ratio. | P0 |
| BKT-FR-016 | Efficiency metrics: system quality number (SQN), ulcer index, recovery factor, payoff ratio. | P1 |
| BKT-FR-017 | Distribution metrics: return distribution analysis, skewness, kurtosis, normality tests. | P1 |
| BKT-FR-018 | Benchmark comparison: alpha, beta, correlation, information ratio, tracking error against a configurable benchmark. | P1 |

#### 4.7.5 Visualization & Reporting

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-019 | The system shall generate an equity curve chart with drawdown overlay. | P0 |
| BKT-FR-020 | The system shall generate a drawdown chart showing drawdown magnitude and duration over time. | P0 |
| BKT-FR-021 | The system shall generate additional charts: monthly returns heatmap, trade distribution histogram, rolling Sharpe ratio, underwater plot. | P1 |
| BKT-FR-022 | The system shall generate a comprehensive backtest report (HTML or PDF) containing all metrics, charts, trade log, and configuration summary. | P0 |
| BKT-FR-023 | Charts shall be rendered using PyQtGraph for integrated display within the desktop UI, with export to PNG/SVG for reports. | P0 |

#### 4.7.6 Parameter Optimization

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-024 | The system shall support grid search optimization: exhaustive search over a defined parameter grid. | P0 |
| BKT-FR-025 | The optimization engine shall integrate with the agent architecture (Ray) for parallel execution across multiple CPU cores and machines. | P0 |
| BKT-FR-026 | The optimization engine shall store all optimization results (parameter combinations + metrics) in the database for analysis. | P0 |
| BKT-FR-027 | The optimization engine shall support configurable objective functions (maximize Sharpe, minimize drawdown, maximize profit factor, custom composite). | P0 |
| BKT-FR-028 | The system shall support Bayesian optimization (Optuna integration) as an alternative to grid search for large parameter spaces. | P1 |

#### 4.7.7 Monte Carlo & Stress Testing

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-029 | The system shall perform Monte Carlo simulation by resampling trade sequences (with replacement) from a completed backtest to generate confidence intervals for key metrics. | P0 |
| BKT-FR-030 | The system shall support Monte Carlo parameter perturbation — running the strategy with small random variations in parameters to test sensitivity. | P1 |
| BKT-FR-031 | The system shall report Monte Carlo results as percentile distributions (5th, 25th, 50th, 75th, 95th) for: final equity, maximum drawdown, Sharpe ratio, and win rate. | P0 |
| BKT-FR-032 | The system shall support stress testing with configurable adverse scenarios: flash crash, prolonged drawdown, high volatility regime, spread widening events. | P1 |

#### 4.7.8 Walk-Forward Optimization (WFO)

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-033 | The WFO manager shall split data into configurable in-sample / out-of-sample windows with rolling or anchored schemes. | P0 |
| BKT-FR-034 | For each window, the WFO manager shall optimize parameters on in-sample data and validate on out-of-sample data. | P0 |
| BKT-FR-035 | The WFO manager shall produce a combined out-of-sample equity curve by concatenating all out-of-sample periods. | P0 |
| BKT-FR-036 | The WFO manager shall report walk-forward efficiency: the ratio of out-of-sample performance to in-sample performance. | P0 |

#### 4.7.9 Edge Lab — Symbol-Specific Edge Discovery Toolkit

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-037 | EDS-0 (Null Model): Establish baseline performance from random entry/exit trading to quantify what pure chance produces for a given symbol. | P0 |
| BKT-FR-038 | EDS-1 (Mean Reversion Detector): Detect mean reversion edges using compression detection and z-score fade signals. | P1 |
| BKT-FR-039 | EDS-2 (Trend Persistence Detector): Detect trend continuation edges using ATR breakout follow-through analysis. | P1 |
| BKT-FR-040 | EDS-3 (Session Edge Detector): Detect time-of-day alpha by analyzing returns segmented by trading session (Asian, London, New York). | P1 |
| BKT-FR-041 | Each edge detector shall produce a statistical report with confidence intervals, effect sizes, and p-values. | P0 |
| BKT-FR-042 | Edge discovery results shall be stored in the database and linked to the specific symbol and data version used. | P0 |

#### 4.7.10 Backtest Storage & Reproducibility

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-043 | Every completed backtest shall be stored in the database with: strategy name, strategy version (git hash), strategy parameters, engine settings, data version hashes, start/end dates, all performance metrics, and the complete trade log. | P0 |
| BKT-FR-044 | The system shall support deterministic replay — re-running a stored backtest with the same code, data, and configuration shall produce bit-identical results. | P0 |
| BKT-FR-045 | For deterministic replay, all sources of randomness (slippage model, Monte Carlo) shall use seeded pseudo-random number generators with the seed stored alongside results. | P0 |
| BKT-FR-046 | The system shall record the engine version (C++ build hash + Python package version) alongside each backtest result for full provenance tracking. | P0 |

#### 4.7.11 Agent Architecture — Parallel Execution

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| BKT-FR-047 | The system shall use Ray for distributing optimization workloads across multiple CPU cores. | P0 |
| BKT-FR-048 | Each Ray worker shall instantiate an independent C++ engine instance, bypassing the Python GIL for true parallelism. | P0 |
| BKT-FR-049 | Workers shall share read-only market data via memory-mapped files to avoid per-worker data duplication. | P0 |
| BKT-FR-050 | The system shall support configurable worker count with intelligent defaults (number of physical cores minus 2 for system headroom). | P0 |
| BKT-FR-051 | The system shall support distributed execution across multiple machines via Ray cluster mode. | P2 |
| BKT-FR-052 | Worker health monitoring shall detect and restart failed workers, reassigning their parameter sets. | P1 |

---

### 4.8 Risk Management System

#### 4.8.1 Risk Limits Configuration

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| RSK-FR-001 | The system shall support configurable risk limits: max position size (per symbol and total), max daily loss, max drawdown, max number of open positions, max number of trades per day, max correlated exposure. | P0 |
| RSK-FR-002 | Risk limits shall be enforceable in both backtesting and live trading modes identically. | P0 |
| RSK-FR-003 | When a risk limit is breached, the system shall: reject the offending order, log the violation, and notify the user via the notification system. | P0 |

#### 4.8.2 Position Sizing

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| RSK-FR-004 | The system shall support position sizing methods: fixed lot size, risk percentage of account (with stop-loss distance), Kelly criterion, ATR-based, fixed percentage of capital, and milestone-based (progressive sizing at equity milestones). | P0 |
| RSK-FR-005 | Position size shall be validated against broker constraints: volume_min, volume_max, volume_step, and available margin. | P0 |
| RSK-FR-006 | Kelly criterion parameters shall be estimable from BacktestResult (win rate, average win/loss ratio). | P1 |
| RSK-FR-007 | Position sizing shall integrate with both the event-driven and vectorized backtesting engines. | P0 |

#### 4.8.3 Regime Detection

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| RSK-FR-008 | The system shall provide regime detection models that classify current market conditions (e.g., trending, mean-reverting, volatile, quiet). | P1 |
| RSK-FR-009 | Regime classification shall be usable by strategies to adjust behavior (e.g., reduce size in unfavorable regimes) and by risk management to adjust limits. | P1 |
| RSK-FR-010 | The system shall support Hidden Markov Model (HMM) based regime detection as a baseline implementation. | P2 |

#### 4.8.4 Portfolio Allocation

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| RSK-FR-011 | The system shall support portfolio allocation methods: equal weight, risk parity, inverse volatility, maximum diversification. | P1 |
| RSK-FR-012 | Allocation weights shall be recalculated at configurable intervals (daily, weekly, monthly). | P1 |
| RSK-FR-013 | The allocation engine shall respect correlation constraints — reducing exposure to highly correlated positions. | P2 |

#### 4.8.5 Risk Governor

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| RSK-FR-014 | The risk governor shall act as a final gatekeeper, approving or rejecting every order before execution against all configured risk limits. | P0 |
| RSK-FR-015 | The risk governor shall support circuit breakers: if daily loss exceeds X%, halt all new trades for the remainder of the session. | P0 |
| RSK-FR-016 | The risk governor shall support equity-based kill switch: if equity drops below a configured absolute value, close all positions and halt trading. | P0 |

#### 4.8.6 Risk Monitoring

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| RSK-FR-017 | The system shall provide real-time risk dashboard data: current exposure by symbol, total portfolio risk, margin utilization, daily PnL, drawdown status. | P0 |
| RSK-FR-018 | The risk monitor shall track correlation between open positions and alert when portfolio concentration exceeds configurable thresholds. | P1 |

---

### 4.9 Live Trading System

#### 4.9.1 Live Trading Engine Core

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| LIV-FR-001 | The live trading engine shall support start, pause, resume, and stop operations with clean state transitions. | P0 |
| LIV-FR-002 | The engine shall process live ticks from the broker and invoke the same strategy callbacks (on_tick, on_bar) as the backtesting engine. | P0 |
| LIV-FR-003 | The engine shall maintain a heartbeat with the broker connection and detect disconnections within configurable timeout (default: 5 seconds). | P0 |

#### 4.9.2 Event Handlers

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| LIV-FR-004 | The system shall provide event handlers for: tick received, bar closed, order filled, order rejected, order modified, position closed, connection lost, connection restored. | P0 |
| LIV-FR-005 | Event handlers shall execute asynchronously to avoid blocking tick processing. | P0 |

#### 4.9.3 Signal-to-Order Flow

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| LIV-FR-006 | Strategy signals (buy/sell) shall pass through the risk governor before being sent to the broker gateway. | P0 |
| LIV-FR-007 | The signal-to-order flow shall log every step: signal generated → risk check passed/failed → order sent → order acknowledged → order filled/rejected. | P0 |
| LIV-FR-008 | The system shall enforce a configurable minimum interval between orders to the same symbol to prevent rapid-fire order spam. | P1 |

#### 4.9.4 Emergency Shutdown

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| LIV-FR-009 | The system shall provide an emergency shutdown function that: cancels all pending orders, closes all open positions at market, halts strategy execution, and sends a notification. | P0 |
| LIV-FR-010 | Emergency shutdown shall be triggerable via: UI button, API call, keyboard shortcut, or automated risk governor trigger. | P0 |
| LIV-FR-011 | Emergency shutdown shall persist its activation reason and the state at the time of activation to the database for post-mortem analysis. | P0 |

#### 4.9.5 State Reconciliation

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| LIV-FR-012 | On startup and after reconnection, the system shall query the broker for the current account state (positions, orders, balance) and reconcile with locally stored state. | P0 |
| LIV-FR-013 | Reconciliation discrepancies shall be logged with full detail and presented to the user for review before resuming trading. | P0 |
| LIV-FR-014 | The system shall support automatic reconciliation for minor discrepancies (e.g., swap amount differences) and require manual approval for major discrepancies (e.g., unknown open positions). | P1 |

#### 4.9.6 Broker Gateway — MT5

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| LIV-FR-015 | The system shall communicate with the MT5 terminal via a MQL5 Expert Advisor that acts as a ZeroMQ bridge (listener/executor). | P0 |
| LIV-FR-016 | The MQL5 EA shall receive order commands as structured text messages (e.g., `ORDER_SEND;EURUSD;BUY;1.0;SL=1.0900`) and return execution confirmations. | P0 |
| LIV-FR-017 | The MQL5 EA shall stream live tick data to the C++ engine via ZMQ with sub-millisecond latency. | P0 |
| LIV-FR-018 | The broker gateway shall translate between the system's order format and the MT5-specific order format, handling all broker-specific quirks. | P0 |
| LIV-FR-019 | The broker gateway shall implement connection management: initial connection, heartbeat monitoring, automatic reconnection with exponential backoff, and graceful disconnection. | P0 |
| LIV-FR-020 | The broker gateway interface shall be abstract, allowing future implementations for other brokers (e.g., Interactive Brokers, cTrader) without modifying the engine. | P1 |

#### 4.9.7 Portfolio Management (Live)

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| LIV-FR-021 | The live portfolio manager shall track all open positions across all symbols with real-time PnL. | P0 |
| LIV-FR-022 | The portfolio manager shall enforce portfolio-level risk limits (max total exposure, max correlated exposure, max portfolio drawdown). | P0 |

---

### 4.10 Paper Trading System

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| PAP-FR-001 | The paper trading engine shall simulate order execution using live market data from the broker without placing real orders. | P0 |
| PAP-FR-002 | Paper trading shall use the same slippage, commission, and spread models as backtesting (configurable). | P0 |
| PAP-FR-003 | All paper trades shall be stored in the database with the same detail level as live trades. | P0 |
| PAP-FR-004 | The system shall support account snapshots — periodic recording of paper trading account state (balance, equity, open positions) for performance tracking. | P0 |
| PAP-FR-005 | The system shall support switching between paper trading and live trading modes without code changes — only a configuration flag change. | P0 |

---

### 4.11 Notification System

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NTF-FR-001 | The system shall define notification models with fields: type (info, warning, error, trade, risk_alert), title, message, timestamp, channel, delivery_status. | P0 |
| NTF-FR-002 | The system shall implement a Telegram notification channel that sends messages via the Telegram Bot API. | P0 |
| NTF-FR-003 | The system shall implement an Email notification channel that sends messages via SMTP with configurable server settings. | P1 |
| NTF-FR-004 | All notification channels shall implement a common `NotificationChannel` interface with methods: `send()`, `is_available()`, `test_connection()`. | P0 |
| NTF-FR-005 | The Notification Manager shall support configurable routing rules: e.g., trade notifications to Telegram, error alerts to Email + Telegram. | P1 |
| NTF-FR-006 | The Notification Manager shall implement rate limiting to prevent notification spam (configurable max notifications per minute per channel). | P0 |
| NTF-FR-007 | All sent notifications shall be stored in the database for audit trail. | P1 |

---

### 4.12 API Layer

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| API-FR-001 | The system shall expose a REST API (FastAPI) providing access to all backend functionality. | P1 |
| API-FR-002 | API endpoints shall cover: backtesting (run, status, results), optimization (run, status, results), live trading (start, pause, stop, status), paper trading (start, stop, status), data management (download, validate, status), risk configuration (view, update), notifications (test, configure). | P1 |
| API-FR-003 | The API shall provide WebSocket endpoints for real-time streaming of: live equity, open positions, trade events, and engine status. | P1 |
| API-FR-004 | All API endpoints shall require authentication (JWT token). | P1 |
| API-FR-005 | The API shall generate automatic OpenAPI (Swagger) documentation. | P1 |

---

### 4.13 Frontend UI

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| GUI-FR-001 | The system shall provide a PySide6 (Qt6) desktop application as the primary user interface. | P1 |
| GUI-FR-002 | The UI shall include a main dashboard showing: account status, active strategies, open positions, recent trades, and risk summary. | P1 |
| GUI-FR-003 | The UI shall include a chart view (PyQtGraph) capable of rendering candlestick charts with indicator overlays and trade markers at 60fps. | P1 |
| GUI-FR-004 | The UI shall include a multi-chart layout for simultaneous viewing of multiple symbols during portfolio backtesting or live trading. | P2 |
| GUI-FR-005 | The UI shall include a strategy editor/configurator for selecting strategies, setting parameters, and launching backtests. | P1 |
| GUI-FR-006 | The UI shall include a backtest results viewer with interactive charts, metrics display, and trade log browser. | P1 |
| GUI-FR-007 | The UI shall include a risk management dashboard showing real-time risk metrics. | P1 |
| GUI-FR-008 | The UI shall communicate with the C++ core via the Nanobind bridge (in-process) for minimum latency. | P1 |
| GUI-FR-009 | UI rendering shall not block the C++ engine — the engine shall run in a separate thread with Signal/Slot communication to the UI thread. | P0 |

---

## 5. Cross-Cutting Concerns

### 5.1 Testing Strategy

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| XCC-FR-001 | The C++ core shall have unit tests using Google Test covering: event loop, matching engine, state manager, order types, slippage/commission/swap models, margin calculation, currency conversion. | P0 |
| XCC-FR-002 | The C++ core shall have performance benchmarks using Google Benchmark for: event loop throughput (ticks/second), order matching latency, state update latency. | P0 |
| XCC-FR-003 | The Nanobind bridge shall have integration tests verifying: data exposure correctness, command dispatch, callback invocation, error propagation, and memory safety (no leaks, no use-after-free). | P0 |
| XCC-FR-004 | The Python layer shall have unit tests using pytest covering: indicators, strategy base class, risk management, data validation, performance metrics calculation. | P0 |
| XCC-FR-005 | The system shall have end-to-end tests that run known strategies on known data and verify that results match expected values (regression tests). | P0 |
| XCC-FR-006 | Numerical correctness tests shall use property-based testing (Hypothesis) to verify that PnL calculations, position sizing, and currency conversions hold across edge cases. | P1 |
| XCC-FR-007 | Test coverage targets: C++ core ≥ 80%, Python layer ≥ 85%, bridge layer ≥ 90%. | P1 |

### 5.2 CI/CD Pipeline

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| XCC-FR-008 | The CI pipeline shall build and test on: Windows (MSVC 2022) and Linux (GCC 12+ and Clang 15+). | P0 |
| XCC-FR-009 | The CI pipeline shall run all C++ unit tests, Python unit tests, bridge integration tests, and end-to-end regression tests on every push. | P0 |
| XCC-FR-010 | The CI pipeline shall produce versioned release artifacts: compiled C++ shared library, Nanobind Python module, and installable Python package. | P1 |
| XCC-FR-011 | The CI pipeline shall run static analysis: clang-tidy (C++), mypy + ruff (Python). | P1 |
| XCC-FR-012 | The CI pipeline shall run memory sanitizers (AddressSanitizer, UndefinedBehaviorSanitizer) on C++ tests in a dedicated CI job. | P1 |

### 5.3 System Observability & Health Monitoring

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| XCC-FR-013 | The system shall monitor and expose health metrics: C++ engine tick processing rate, bridge call latency, Python callback duration, memory usage (C++ heap, Python RSS), event queue depth, ZMQ message backlog. | P1 |
| XCC-FR-014 | During live trading, the system shall monitor: broker connection latency, order round-trip time, data feed lag, and heartbeat status. | P0 |
| XCC-FR-015 | During distributed optimization (Ray), the system shall monitor: worker count, worker health, tasks completed, tasks remaining, estimated time to completion. | P1 |
| XCC-FR-016 | Health metrics shall be accessible via the API and displayed in the UI dashboard. | P1 |

### 5.4 Versioning & Reproducibility

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| XCC-FR-017 | The system shall maintain a composite version identifier combining: C++ core build hash, Python package version, and a human-readable release version. | P0 |
| XCC-FR-018 | Every stored backtest result shall record the composite version identifier and all configuration used. | P0 |
| XCC-FR-019 | The system shall provide a `reproduce(backtest_id)` command that retrieves the configuration, data versions, and random seeds from a stored backtest and re-runs it. | P1 |
| XCC-FR-020 | Strategy source code shall be stored or referenced (git commit hash) alongside backtest results. | P1 |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-001 | The C++ event loop shall process ≥ 1,000,000 ticks per second per symbol in bar-level backtesting mode on a single core. | P0 |
| NFR-002 | The C++ event loop shall process ≥ 100,000 ticks per second per symbol in tick-level backtesting mode with strategy callbacks on a single core. | P0 |
| NFR-003 | Bridge call latency (Python → C++ command) shall be < 1 microsecond per call. | P0 |
| NFR-004 | UI chart rendering shall maintain ≥ 30 fps during live data streaming with up to 10,000 visible bars. | P1 |
| NFR-005 | Memory usage for a 50-symbol, 10-year bar-level backtest shall not exceed 4 GB RAM (excluding mmap-backed data files). | P1 |
| NFR-006 | A full grid optimization of 10,000 parameter combinations on a 16-core machine shall complete within 10 minutes for a 1-year, single-symbol, bar-level backtest. | P1 |

### 6.2 Reliability

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-007 | The live trading engine shall achieve ≥ 99.9% uptime during market hours (excluding scheduled maintenance). | P0 |
| NFR-008 | The system shall recover from broker disconnections within 30 seconds via automatic reconnection. | P0 |
| NFR-009 | No data loss shall occur during unclean shutdown — all pending state shall be recoverable from the write-ahead log. | P0 |
| NFR-010 | The C++ core shall have zero known memory leaks as verified by AddressSanitizer in CI. | P0 |

### 6.3 Scalability

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-011 | The system shall support backtesting up to 100 symbols simultaneously in a single portfolio backtest. | P1 |
| NFR-012 | The distributed agent architecture shall scale linearly with added CPU cores (≥ 85% efficiency at 16 cores). | P1 |
| NFR-013 | The data storage layer shall handle datasets up to 1 TB per symbol without degradation via mmap. | P1 |

### 6.4 Maintainability

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-014 | The codebase shall follow consistent coding standards: Google C++ Style Guide (with project-specific modifications) for C++, PEP 8 + Ruff for Python. | P0 |
| NFR-015 | All public APIs (C++ and Python) shall have docstring/Doxygen documentation. | P0 |
| NFR-016 | Module coupling shall be minimized — modules shall communicate through well-defined interfaces, not concrete implementations. | P0 |
| NFR-017 | The system shall maintain a developer onboarding document covering: build setup, running tests, architecture overview, and contributing guidelines. | P1 |

### 6.5 Portability

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-018 | The backtesting engine and all supporting modules (except live trading / MT5 gateway) shall run on both Windows and Linux. | P0 |
| NFR-019 | The live trading module shall clearly document its Windows-only dependency (MT5) and provide a deployment guide for a split architecture (backtest on Linux, trade on Windows). | P1 |

### 6.6 Security

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-020 | No credentials shall be stored in plain text anywhere in the system (config files, logs, database, code). | P0 |
| NFR-021 | API endpoints shall enforce authentication and authorization on all requests. | P1 |
| NFR-022 | The system shall log all authentication attempts and security-relevant events. | P1 |

---

## 7. External Interfaces

### 7.1 MetaTrader 5 Interface

| Interface | Direction | Protocol | Description |
|-----------|-----------|----------|-------------|
| Live tick data | MT5 → System | ZeroMQ (PUB/SUB) | MQL5 EA streams ticks to C++ engine |
| Order commands | System → MT5 | ZeroMQ (REQ/REP) | C++ engine sends order commands, EA executes and confirms |
| Historical data | MT5 → System | MT5 Python API | Data download for local storage (one-time or scheduled) |
| Account info | MT5 → System | MT5 Python API | Account state queries for reconciliation |

### 7.2 Dukascopy Interface

| Interface | Direction | Protocol | Description |
|-----------|-----------|----------|-------------|
| Historical tick data | Dukascopy → System | HTTPS | Download compressed tick data files |

### 7.3 Notification Interfaces

| Interface | Direction | Protocol | Description |
|-----------|-----------|----------|-------------|
| Telegram | System → Telegram | HTTPS (Bot API) | Send notification messages |
| Email | System → SMTP Server | SMTP/TLS | Send email notifications |

### 7.4 Data Storage Interfaces

| Interface | Direction | Format | Description |
|-----------|-----------|--------|-------------|
| Time-series data | Read/Write | HDF5 / Parquet | Market data storage via mmap |
| Metadata/Results | Read/Write | SQLite / PostgreSQL | Via SQLAlchemy ORM |

---

## 8. Data Requirements

### 8.1 Data Retention

| Data Category | Retention Period | Storage |
|--------------|-----------------|---------|
| Market data (tick/bar) | Indefinite | HDF5/Parquet files |
| Backtest results | Indefinite | Database |
| Optimization results | Configurable (default: 1 year) | Database |
| Live trade records | Indefinite | Database |
| Paper trade records | Configurable (default: 6 months) | Database |
| Logs (file) | Configurable (default: 30 days rolling) | Rotating files |
| Notifications | Configurable (default: 90 days) | Database |
| Write-ahead log | Until confirmed persisted + 7 days | File |

### 8.2 Data Volume Estimates

| Data Type | Estimate |
|-----------|----------|
| 1 year of M1 bars, 1 symbol | ~525,600 records (~25 MB in Parquet) |
| 1 year of tick data, 1 symbol (major FX) | ~50-100M records (~2-5 GB in Parquet) |
| 50 symbols, 10 years, M1 bars | ~263M records (~12 GB) |
| 50 symbols, 10 years, tick data | ~25-50 billion records (~1-2.5 TB) |
| 10,000 optimization runs (metadata) | ~50 MB in database |
| Single backtest trade log (1000 trades) | ~500 KB in database |

---

## 9. Constraints & Assumptions

### 9.1 Technical Constraints

| ID | Constraint |
|----|-----------|
| TC-01 | MT5 terminal is available only on Windows. Live trading functionality is Windows-only. |
| TC-02 | Python GIL prevents true multi-threading in Python. All parallel Python workloads must use multiprocessing (via Ray). |
| TC-03 | Nanobind requires the C++ shared library to be compiled for the same platform and Python version as the runtime. |
| TC-04 | ZeroMQ IPC transport is not available on Windows; TCP transport (localhost) must be used instead. |
| TC-05 | HDF5 does not support concurrent writes from multiple processes. Write operations must be serialized. |

### 9.2 Assumptions

| ID | Assumption |
|----|-----------|
| AS-01 | Broker provides sufficient historical data for the desired backtest periods (or Dukascopy data is used as alternative). |
| AS-02 | Network latency to broker is < 100ms under normal conditions. |
| AS-03 | The user's hardware meets the minimum specifications defined in section 2.3. |
| AS-04 | Broker commission and swap rates are available and can be configured at setup time. |
| AS-05 | The MQL5 ZeroMQ library (or equivalent) is available for the target MT5 build. |

---

## 10. Acceptance Criteria

### 10.1 Module-Level Acceptance

| Module | Acceptance Criteria |
|--------|-------------------|
| C++ Core Engine | Processes 1M+ ticks/sec; all order types execute correctly; matching engine handles gap scenarios |
| Nanobind Bridge | Zero-copy verified; < 1μs call latency; no memory leaks under 1M+ call stress test |
| Event-Driven Backtester | Produces identical results to a reference implementation for 5 known strategies on known data |
| Vectorized Backtester | Results match event-driven engine within acceptable tolerance for equivalent configurations |
| Risk Management | All risk limits enforced; position sizing matches manual calculations; governor blocks correctly |
| Live Trading | Successfully executes round-trip trade (open + close) on demo account; reconnection works after simulated disconnect |
| Paper Trading | Results are statistically consistent with backtesting results on the same data period |
| Performance Metrics | All metrics match manual/spreadsheet calculations for a reference trade log |
| Data Validation | Correctly identifies all planted data quality issues in a test dataset |
| Notifications | Telegram and Email delivery confirmed within 5 seconds of trigger |

### 10.2 System-Level Acceptance

| Criterion | Test |
|-----------|------|
| End-to-end backtest | Run a moving average crossover strategy on EURUSD 2020-2024 M1 data and produce a complete report |
| End-to-end optimization | Grid search over 1000 parameter combinations on 8 cores, all complete successfully |
| End-to-end live trading | Strategy runs on demo account for 24 hours without crash, executing at least one trade |
| Deterministic replay | Re-run a stored backtest and verify bit-identical results |
| Crash recovery | Kill the process during a backtest, restart, and verify state recovery |

---

## 11. Appendices

### Appendix A: Module Abbreviations

| Abbreviation | Module |
|-------------|--------|
| FND | Foundation |
| DAT | Data Infrastructure |
| STR | Strategy Framework |
| TRD | Trading Framework |
| CPP | C++ Core Engine |
| BRG | Bridge Layer |
| BKT | Backtesting Engine |
| RSK | Risk Management |
| LIV | Live Trading |
| PAP | Paper Trading |
| NTF | Notification System |
| API | API Layer |
| GUI | Frontend UI |
| XCC | Cross-Cutting Concerns |
| NFR | Non-Functional Requirements |

### Appendix B: Priority Distribution Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | ~130 | Must Have — required for MVP |
| P1 | ~55 | Should Have — high value, target for v1.1 |
| P2 | ~8 | Nice to Have — deferred to future releases |

### Appendix C: Glossary of Financial Terms

| Term | Definition |
|------|-----------|
| **Pip** | Smallest price increment for a currency pair (typically 0.0001 for majors) |
| **Lot** | Standard unit of trade (100,000 units of base currency in FX) |
| **Spread** | Difference between ask and bid price |
| **Swap** | Overnight financing charge/credit for holding a position past rollover |
| **Margin** | Collateral required to open a leveraged position |
| **Drawdown** | Peak-to-trough decline in account equity |
| **Sharpe Ratio** | Risk-adjusted return: (return − risk-free rate) / standard deviation |
| **Walk-Forward** | Optimization technique that validates on unseen data to test robustness |
| **Stop-Out** | Broker-forced liquidation when margin level drops below threshold |
| **Slippage** | Difference between expected and actual execution price |

### Appendix D: Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-10 | — | Initial SRS draft covering all modules and cross-cutting concerns |

---

*End of Document — SRS-HQTBS-001 v1.0.0*
