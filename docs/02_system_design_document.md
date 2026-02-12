# System Design Document (SDD)

## Hybrid C++/Python Quantitative Trading & Backtesting System

| Field               | Detail                                      |
|---------------------|---------------------------------------------|
| **Document ID**     | SDD-HQTBS-001                               |
| **Version**         | 1.0.0                                       |
| **Date**            | 2026-02-10                                  |
| **Status**          | Draft — Planning Phase                      |
| **Classification**  | Internal / Confidential                     |
| **SRS Reference**   | SRS-HQTBS-001 v1.0.0                       |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architectural Overview](#2-architectural-overview)
3. [Directory Structure & Repository Layout](#3-directory-structure--repository-layout)
4. [Foundation Layer Design](#4-foundation-layer-design)
5. [Data Infrastructure Design](#5-data-infrastructure-design)
6. [C++ Core Engine Design](#6-c-core-engine-design)
7. [Bridge Layer Design (Nanobind)](#7-bridge-layer-design-nanobind)
8. [Strategy Framework Design](#8-strategy-framework-design)
9. [Trading Framework Design](#9-trading-framework-design)
10. [Backtesting Engine Design](#10-backtesting-engine-design)
11. [Risk Management System Design](#11-risk-management-system-design)
12. [Live Trading System Design](#12-live-trading-system-design)
13. [Paper Trading System Design](#13-paper-trading-system-design)
14. [Notification System Design](#14-notification-system-design)
15. [API Layer Design](#15-api-layer-design)
16. [Frontend UI Design](#16-frontend-ui-design)
17. [Database Design](#17-database-design)
18. [Build System & DevOps Design](#18-build-system--devops-design)
19. [Testing Architecture](#19-testing-architecture)
20. [Deployment Architecture](#20-deployment-architecture)
21. [Appendices](#21-appendices)

---

## 1. Introduction

### 1.1 Purpose

This System Design Document translates the requirements defined in SRS-HQTBS-001 into concrete architectural decisions, component designs, class structures, interface definitions, data models, and interaction patterns. It serves as the technical blueprint from which all implementation work proceeds.

### 1.2 Scope

This document covers the complete system design for the C++20 core engine, Nanobind bridge layer, Python control tower, and all supporting subsystems including data infrastructure, risk management, live trading, paper trading, notifications, API, UI, build system, CI/CD, testing architecture, and deployment.

### 1.3 Design Principles

| Principle | Application |
|-----------|-------------|
| **Performance-critical path in C++** | The event loop, matching engine, state manager, and all per-tick computations live in C++. Python is never on the hot path. |
| **Zero-copy across the bridge** | Data flows from C++ to Python via memory references, not copies. Python sees C++ memory directly. |
| **Interface segregation** | Modules communicate through abstract interfaces (ABCs in Python, pure virtual classes in C++). No concrete cross-module dependencies. |
| **Identical API across modes** | Strategy code calls the same `buy()`, `sell()`, `positions()` whether in backtest, paper, or live mode. The runtime backend is swapped, not the interface. |
| **Deterministic by default** | All randomness is seeded. All state is serializable. Any run can be replayed bit-identically. |
| **Fail-safe in live trading** | Any ambiguity, error, or disconnection results in order rejection, not silent execution. |

### 1.4 Document Conventions

- Class names use `PascalCase`, methods/functions use `snake_case`
- C++ namespaces use `hqt::` prefix (Hybrid Quantitative Trading)
- Python packages use `hqt` top-level package
- Design references to SRS requirements use `[REQ: XXX-FR-NNN]` notation

### 1.5 Technology Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| C++ Core | C++20 | MSVC 2022+ / GCC 12+ / Clang 15+ |
| Bridge | Nanobind | 2.x |
| Python | CPython | 3.11+ |
| Parallelism | Ray | 2.x |
| Data (time-series) | Apache Parquet + HDF5 | — |
| Data (metadata) | SQLite / PostgreSQL | SQLAlchemy 2.x + Alembic |
| Messaging | ZeroMQ | 4.3+ |
| UI | PySide6 (Qt6) + PyQtGraph | 6.x |
| API | FastAPI | 0.100+ |
| C++ Build | CMake 3.25+ / vcpkg | — |
| C++ Logging | spdlog | 1.x |
| C++ Testing | Google Test + Google Benchmark | latest |
| Python Testing | pytest + hypothesis | latest |
| CI/CD | GitHub Actions | — |
| Config | TOML (toml++ for C++, tomli for Python) | — |

---

## 2. Architectural Overview

### 2.1 Layered Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAYER 4: PRESENTATION                            │
│                                                                         │
│  ┌─────────────────────────┐    ┌────────────────────────────────────┐  │
│  │   Desktop UI (PySide6)  │    │        REST API (FastAPI)          │  │
│  │   PyQtGraph Charts      │    │   HTTP Endpoints + WebSocket       │  │
│  │   Dashboard / Editor    │    │   Streaming                        │  │
│  └───────────┬─────────────┘    └────────────────────────────────────┘  │
│              │ Qt Signal/Slot                                           │
├──────────────┼──────────────────────────────────────────────────────────┤
│              ▼         LAYER 3: PYTHON CONTROL TOWER                    │
│                                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌────────────────┐  │
│  │  Strategy     │ │ Risk Manager │ │ Config     │ │ Notification   │  │
│  │  Framework    │ │ + Governor   │ │ Manager    │ │ Manager        │  │
│  └──────┬───────┘ └──────┬───────┘ └────────────┘ └────────────────┘  │
│         │                │                                              │
│  ┌──────┴────────────────┴──────────────────────────────────────────┐  │
│  │              Trading Framework (Unified Interface)                │  │
│  │  AccountInfo | OrderManager | PositionManager | SymbolManager    │  │
│  └──────────────────────────────┬───────────────────────────────────┘  │
│                                 │                                       │
│  ┌──────────────────────────────┴───────────────────────────────────┐  │
│  │                     Mode Router                                   │  │
│  │     Backtest Backend  |  Paper Backend  |  Live Backend           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │   Orchestration: Ray Agents | WFO | Monte Carlo | Edge Lab       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                        LAYER 2: BRIDGE (Nanobind)                       │
│  Type Exposure (C++→Py) | Callbacks (C++→Py) | Commands (Py→C++)       │
│  Lifetime Manager       | GIL Manager        | Error Propagation       │
├─────────────────────────────────────────────────────────────────────────┤
│                        LAYER 1: C++ CORE ENGINE                         │
│  EventLoop (PQ) | MatchingEngine | StateManager | OrderManager         │
│  CurrencyConverter | MarginCalculator | ZMQ Broadcaster | WAL          │
│  Slippage/Commission/Swap/Spread Models | MmapReader                   │
├─────────────────────────────────────────────────────────────────────────┤
│                        LAYER 0: DATA STORAGE                            │
│  Parquet/HDF5 (mmap) | SQLite/PostgreSQL (SQLAlchemy) | WAL Files     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Process Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Main Process                           │
│  Python Main Thread (Orchestrator)                       │
│  C++ Engine (in-process via Nanobind, shared memory)     │
│  UI Thread (Qt Event Loop)                               │
│                           │ ZMQ (inproc/tcp)             │
└───────────────────────────┼──────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
   │ Ray Worker 1│  │ Ray Worker 2│  │ Ray Worker N │
   │ C++ Engine  │  │ C++ Engine  │  │ C++ Engine   │
   │ (mmap data) │  │ (mmap data) │  │ (mmap data)  │
   └─────────────┘  └─────────────┘  └──────────────┘

   ┌──────────────────────────────────────────────────┐
   │            MT5 Terminal Process (Windows)          │
   │  MQL5 Bridge EA (ZMQ PUB ticks, ZMQ REP orders)  │
   └──────────────────────────────────────────────────┘
```

### 2.3 Data Flow Patterns

**Pattern 1 — Backtest Single Tick**:

```
1. C++ EventLoop → pop next Tick from Priority Queue (lowest timestamp)
2. C++ StateManager → update symbol market prices
3. C++ MatchingEngine → check pending orders against new price
4. C++ StateManager → update unrealized PnL for open positions
5. C++ StateManager → recalculate equity, check margin/stop-out
6. Bridge → acquire GIL → call Python Strategy.on_tick(tick)
7. Python Strategy → logic executes, may call engine.buy()/sell()
8. Bridge → release GIL → dispatch buy/sell to C++ OrderManager
9. C++ MatchingEngine → calculate fill price (slippage + commission)
10. C++ StateManager → create position, update balance
11. C++ ZmqBroadcaster → publish state update (non-blocking)
12. C++ EventLoop → advance to next tick
```

**Pattern 2 — Distributed Optimization**:

```
Python Orchestrator
  ├─ Define parameter grid
  ├─ Ray: distribute to N workers
  │    └─ Each worker: init C++ Engine(params) → run → return metrics
  ├─ Collect all results
  ├─ Rank by objective function
  └─ Store to database
```

**Pattern 3 — Live Trading Order Flow**:

```
MT5 EA ──(ZMQ PUB)──► C++ Engine tick
  → Strategy.on_tick() → engine.sell()
  → Risk Governor approval
  → C++ Engine ──(ZMQ REQ)──► MT5 EA ──► Broker
  → MT5 EA ──(ZMQ REP)──► Fill confirmation
  → State update → ZMQ broadcast → UI + Notifications
```

---

## 3. Directory Structure & Repository Layout

```
hqt/
├── CMakeLists.txt                     # Top-level CMake
├── vcpkg.json                         # C++ dependency manifest
├── pyproject.toml                     # Python project config
├── alembic.ini                        # DB migration config
├── config/
│   ├── base.toml                      # Base configuration
│   ├── development.toml               # Dev overrides
│   ├── testing.toml                   # Test overrides
│   └── production.toml                # Production overrides
│
├── cpp/                               # ═══ C++ CORE ENGINE ═══
│   ├── CMakeLists.txt
│   ├── include/hqt/
│   │   ├── core/
│   │   │   ├── event_loop.hpp         # Priority queue event loop
│   │   │   ├── event.hpp              # Event types
│   │   │   ├── global_clock.hpp       # Multi-asset time sync
│   │   │   └── engine.hpp             # Top-level engine facade
│   │   ├── matching/
│   │   │   ├── matching_engine.hpp    # Order fill evaluation
│   │   │   ├── slippage_model.hpp     # Interface + implementations
│   │   │   ├── commission_model.hpp
│   │   │   ├── swap_model.hpp
│   │   │   └── spread_model.hpp
│   │   ├── state/
│   │   │   ├── account_state.hpp      # Balance, equity, margin
│   │   │   ├── position.hpp           # Open position
│   │   │   ├── order.hpp              # Order (all types)
│   │   │   ├── deal.hpp               # Closed deal record
│   │   │   ├── state_manager.hpp      # Aggregate state
│   │   │   └── state_snapshot.hpp     # Checkpoint serialization
│   │   ├── market/
│   │   │   ├── symbol_info.hpp        # Symbol specification
│   │   │   ├── market_state.hpp       # Current prices
│   │   │   └── currency_converter.hpp # Cross-rate conversion
│   │   ├── margin/
│   │   │   └── margin_calculator.hpp
│   │   ├── data/
│   │   │   ├── mmap_reader.hpp        # Memory-mapped reader
│   │   │   ├── tick.hpp               # Tick struct
│   │   │   ├── bar.hpp                # Bar struct
│   │   │   └── data_feed.hpp          # Unified tick/bar abstraction
│   │   ├── io/
│   │   │   ├── zmq_broadcaster.hpp    # ZMQ PUB state updates
│   │   │   └── zmq_broker_gateway.hpp # ZMQ REQ/REP for MT5
│   │   ├── journal/
│   │   │   └── write_ahead_log.hpp    # WAL for crash recovery
│   │   └── util/
│   │       ├── fixed_point.hpp        # Fixed-point arithmetic
│   │       ├── timestamp.hpp          # Microsecond timestamps
│   │       └── random.hpp             # Seeded PRNG
│   ├── src/                           # .cpp implementation files
│   ├── tests/                         # Google Test unit tests
│   └── benchmarks/                    # Google Benchmark micro-benchmarks
│
├── bridge/                            # ═══ NANOBIND BRIDGE ═══
│   ├── CMakeLists.txt
│   ├── src/
│   │   ├── module.cpp                 # Module definition
│   │   ├── bind_engine.cpp            # Engine exposure
│   │   ├── bind_state.cpp             # State types
│   │   ├── bind_market.cpp            # Market data types
│   │   ├── bind_callbacks.cpp         # Callback registration
│   │   └── bind_commands.cpp          # Command interface
│   └── tests/                         # Bridge integration tests (Python)
│
├── src/hqt/                           # ═══ PYTHON PACKAGES ═══
│   ├── foundation/                    # Logging, config, exceptions, DB, utils
│   │   ├── logging/
│   │   ├── config/
│   │   ├── exceptions/
│   │   ├── utils/
│   │   └── database/
│   ├── data/                          # Data models, validation, providers, storage
│   │   ├── models/
│   │   ├── validation/
│   │   ├── providers/
│   │   ├── storage/
│   │   └── versioning/
│   ├── strategy/                      # Indicators, base strategy, parameters
│   │   ├── indicators/
│   │   ├── base.py
│   │   ├── parameter.py
│   │   └── registry.py
│   ├── trading/                       # Unified trading interface + mode router
│   │   ├── interfaces.py
│   │   ├── account.py
│   │   ├── order.py
│   │   ├── position.py
│   │   ├── symbol.py
│   │   ├── deal.py
│   │   ├── trade_manager.py
│   │   └── mode_router.py
│   ├── backtesting/                   # Engines, metrics, optimization, MC, WFO, edge lab
│   │   ├── engine/
│   │   ├── metrics/
│   │   ├── optimization/
│   │   ├── monte_carlo/
│   │   ├── wfo/
│   │   ├── edge_lab/
│   │   ├── visualization/
│   │   ├── storage/
│   │   ├── agents/
│   │   └── result.py
│   ├── risk/                          # Config, sizing, regime, allocation, governor
│   │   ├── position_sizing/
│   │   ├── regime/
│   │   ├── allocation/
│   │   ├── governor.py
│   │   └── monitor.py
│   ├── live/                          # Engine, event handlers, gateway
│   │   └── gateway/
│   ├── paper/                         # Paper trading engine
│   ├── notifications/                 # Channels (Telegram, Email), manager
│   │   └── channels/
│   ├── api/                           # FastAPI routes + WebSocket
│   │   ├── routes/
│   │   └── websockets/
│   ├── ui/                            # PySide6 desktop UI
│   │   ├── widgets/
│   │   ├── models/
│   │   └── threads/
│   └── observability/                 # Health metrics
│
├── strategies/                        # User strategy files
├── mql5/                              # MQL5 Bridge EA source
├── migrations/                        # Alembic migration scripts
├── tests/                             # Python tests (unit, integration, e2e)
├── docs/                              # Documentation
└── scripts/                           # Dev & ops scripts
```

---

## 4. Foundation Layer Design

### 4.1 Logging System

[REQ: FND-FR-001 through FND-FR-009]

**Architecture**: Dual-language logging — spdlog (C++) for the core engine, Python `logging` for the strategy/orchestration layer, unified into a single stream.

```
C++ Core (spdlog)                 Python Layer (logging)
     │                                  │
     ├── Async sink (non-blocking)      ├── Console Handler
     │                                  ├── Rotating File Handler
     └── Bridge sink ──────────────────►├── JSON File Handler
         (forwards to Python)           │
                                        ▼
                                  Redaction Filter (masks secrets)
                                        │
                                        ▼
                                  Unified Log Stream
```

**C++ Logger Setup**: spdlog async logger with 8192-slot queue. Performance-critical paths use `SPDLOG_ACTIVE_LEVEL` compile-time elimination — TRACE/DEBUG calls compile to no-ops in Release builds.

**Log Format**: `[2026-02-10T14:30:00.123456Z] [INFO] [engine.event_loop] [tid:12345] Message`

**Python Bridge Handler**: A custom spdlog sink forwards C++ log records to Python's logging module on a dedicated thread, avoiding event loop blocking.

### 4.2 Configuration Management

[REQ: FND-FR-015 through FND-FR-022]

**Design**: TOML files with environment overlays and schema validation.

```python
class ConfigManager:
    def load(self, env: str = "development") -> FrozenConfig:
        base = load_toml("config/base.toml")
        overlay = load_toml(f"config/{env}.toml")
        merged = deep_merge(base, overlay)
        resolved = self._resolve_secrets(merged)     # ${secret:key} → value
        resolved = self._resolve_env_vars(resolved)   # ${env:VAR} → value
        validated = ConfigSchema(**resolved)           # Pydantic validation
        return freeze(validated)
```

**Config sections**: `[engine]`, `[data]`, `[broker]`, `[risk]`, `[notifications]`, `[logging]`, `[ui]`, `[database]`, `[optimization]`. Each section maps to a Pydantic model with typed fields, defaults, and bounds.

**C++ Access**: The C++ core reads the same TOML files via toml++ at engine initialization. Only engine-relevant sections are parsed.

**Secrets Resolution**: References like `${secret:telegram_bot_token}` are resolved from the OS-level keyring (Windows Credential Locker / Linux libsecret).

### 4.3 Exception Handling

[REQ: FND-FR-010 through FND-FR-014]

**Hierarchy**:

```
HQTBaseError
├── DataError (ValidationError, GapError, PriceSanityError, DuplicateError)
├── TradingError (OrderError, MarginError, StopOutError)
├── SystemError (EngineError, BridgeError)
├── ConfigError (SchemaError, SecretError)
└── BrokerError (ConnectionError, TimeoutError, ReconnectError)
```

**Cross-language propagation**: C++ exceptions derive from `hqt::HQTException`. Nanobind maps them to corresponding Python classes at the bridge boundary. All C++ calls are wrapped in try/catch.

### 4.4 Fault Tolerance

[REQ: FND-FR-037 through FND-FR-042]

**Write-Ahead Log (WAL)**: Implemented in C++ (`write_ahead_log.hpp`). Every state-changing operation (order execution, position modification) writes a binary entry to the WAL with CRC32 checksum before execution. On crash recovery, uncommitted entries are replayed.

**Reconnection Strategy**: Exponential backoff — immediate → 1s → 2s → 4s → ... → max 60s. After `max_retries` (default 10), trigger emergency notification and pause strategy.

**Worker Recovery**: Ray workers emit heartbeats every 5 seconds. Dead workers are detected within 15 seconds and automatically restarted with their assigned parameter set.

---

## 5. Data Infrastructure Design

### 5.1 Data Models (C++ ↔ Python)

[REQ: DAT-FR-001 through DAT-FR-005]

**C++ Core Structs** (cache-line aligned, fixed-point prices):

```cpp
namespace hqt {

struct alignas(64) Tick {
    int64_t timestamp_us;    // Microseconds since epoch (UTC)
    uint32_t symbol_id;      // Symbol lookup index
    int64_t bid;             // Fixed-point: value × 10^digits
    int64_t ask;             // Fixed-point
    int64_t bid_volume;
    int64_t ask_volume;
    int32_t spread_points;
};

struct alignas(64) Bar {
    int64_t timestamp_us;
    uint32_t symbol_id;
    int64_t open, high, low, close;  // All fixed-point
    int64_t tick_volume, real_volume;
    int32_t spread_points;
    uint8_t timeframe;       // M1=1, M5=5, H1=60, H4=240, D1=1440
};

} // namespace hqt
```

**Fixed-Point Arithmetic**: All prices stored as `int64_t` with implicit scaling. EURUSD (5 digits): `1.10523` → `110523`. XAUUSD (2 digits): `2350.50` → `235050`. The `SymbolInfo` carries `digits` for conversion. All monetary calculations avoid floating-point until final display.

**Unified Data Abstraction** [REQ: DAT-FR-005]:

```cpp
class IDataFeed {
public:
    virtual const Tick* current_tick(uint32_t symbol_id) const = 0;
    virtual const Bar* current_bar(uint32_t symbol_id, Timeframe tf) const = 0;
    virtual const Bar* get_bars(uint32_t symbol_id, Timeframe tf,
                                 int count, int shift = 0) const = 0;
    virtual bool is_new_bar(uint32_t symbol_id, Timeframe tf) const = 0;
};

class TickDataFeed : public IDataFeed { ... };  // Tick-level granularity
class BarDataFeed : public IDataFeed { ... };   // Bar-level granularity
```

### 5.2 Data Storage Architecture

[REQ: DAT-FR-021 through DAT-FR-029]

**File Layout**:

```
data/
├── parquet/
│   ├── EURUSD/
│   │   ├── ticks/2024-01.parquet     # Monthly partitions (ticks)
│   │   ├── M1/2024.parquet           # Yearly partitions (bars)
│   │   └── D1/all.parquet
│   └── XAUUSD/ ...
├── catalog.db                         # SQLite data catalog
└── checksums/manifest.json            # Version hash registry
```

**Parquet Schema**: All prices as INT64 fixed-point with DELTA_BINARY_PACKED encoding. Spread as INT32 with RLE encoding. Columnar access allows reading only close prices without loading OHLCV.

**Memory-Mapped Access**: C++ `MmapReader` uses OS mmap to open Parquet/HDF5 files. Only accessed pages are loaded into RAM (OS manages page faults). Supports concurrent read from multiple Ray workers sharing the same files.

**Data Versioning**: Each data file has a SHA-256 content hash stored in the catalog. Every backtest records the hash(es) used, enabling exact reproduction via `DataLineage.can_reproduce(backtest_id)`.

### 5.3 Data Validation Pipeline

[REQ: DAT-FR-006 through DAT-FR-015]

Sequential checks: PriceSanityCheck → GapDetector → SpikeDetector → MissingTimestampDetector → ZeroVolumeDetector → DuplicateDetector → SpreadAnalyzer. Each check returns a list of `ValidationIssue` objects. The pipeline produces a `ValidationReport` with counts, affected timestamps, and severity levels. Thresholds are configurable per symbol/source.

### 5.4 Data Providers

[REQ: DAT-FR-016 through DAT-FR-020]

```python
class DataProvider(ABC):
    @abstractmethod
    def fetch_bars(self, symbol, timeframe, start, end, progress_callback=None) -> pd.DataFrame: ...
    @abstractmethod
    def fetch_ticks(self, symbol, start, end, progress_callback=None) -> pd.DataFrame: ...
    @abstractmethod
    def get_available_symbols(self) -> list[str]: ...
    @abstractmethod
    def get_available_timeframes(self) -> list[str]: ...
```

Implementations: `MT5DataProvider` (uses MetaTrader5 Python package), `DukascopyProvider` (downloads compressed tick data via HTTPS). Both support incremental downloads — only fetching data newer than the latest stored timestamp.

---

## 6. C++ Core Engine Design

### 6.1 Engine Facade

[REQ: CPP-FR-001 through CPP-FR-032]

```cpp
namespace hqt {
class Engine {
public:
    Engine(const EngineConfig& config);

    // Data loading
    void load_symbol(uint32_t symbol_id, const SymbolInfo& info,
                     const std::filesystem::path& data_path);
    void load_conversion_pair(uint32_t from_id, uint32_t to_id,
                              const std::filesystem::path& data_path);

    // Execution lifecycle
    void run();                      // Run until all data consumed
    void run_steps(size_t n);        // Process n events then pause
    void pause(); void resume(); void stop();

    // Trading commands (called from Python via bridge)
    OrderResult buy(const OrderRequest& req);
    OrderResult sell(const OrderRequest& req);
    OrderResult modify_order(uint64_t ticket, const ModifyRequest& req);
    bool close_position(uint64_t ticket, double volume = 0.0);
    void close_all();
    bool cancel_order(uint64_t ticket);

    // State access (read-only, exposed to Python)
    const AccountState& account() const;
    const std::vector<Position>& positions() const;
    const std::vector<Order>& pending_orders() const;
    const std::vector<Deal>& history_deals() const;
    const MarketState& market() const;

    // Multi-timeframe (PIT-safe)
    std::span<const Bar> get_bars(uint32_t symbol_id, Timeframe tf,
                                   int count, int shift = 0) const;

    // Callback registration
    void set_on_tick(std::function<void(const Tick&)> cb);
    void set_on_bar(std::function<void(uint32_t, Timeframe, const Bar&)> cb);
    void set_on_trade(std::function<void(const Deal&)> cb);

private:
    std::unique_ptr<EventLoop> event_loop_;
    std::unique_ptr<MatchingEngine> matching_engine_;
    std::unique_ptr<StateManager> state_manager_;
    std::unique_ptr<OrderManager> order_manager_;
    std::unique_ptr<CurrencyConverter> currency_converter_;
    std::unique_ptr<MarginCalculator> margin_calculator_;
    std::unique_ptr<ZmqBroadcaster> broadcaster_;
    std::unique_ptr<WriteAheadLog> wal_;
    std::unique_ptr<IDataFeed> data_feed_;
    EngineConfig config_;
    std::mt19937_64 rng_;  // Seeded PRNG for deterministic slippage
};
} // namespace hqt
```

### 6.2 Event Loop

[REQ: CPP-FR-001 through CPP-FR-005]

Min-heap priority queue ordered by timestamp. Event types: `TICK`, `BAR_CLOSE`, `ORDER_TRIGGER`, `TIMER`, `CUSTOM`. For multi-asset backtesting, the GlobalClock ensures no symbol advances past a timestamp others haven't reached. Supports pause/resume/step-forward for interactive debugging.

```cpp
class EventLoop {
    std::priority_queue<Event, std::vector<Event>, std::greater<Event>> queue_;
    std::atomic<bool> running_, paused_, stopped_;
public:
    void push(Event e);
    void run(std::function<void(const Event&)> handler);
    void pause(); void resume(); void stop();
    void step(size_t n);
};
```

### 6.3 Matching Engine

[REQ: CPP-FR-006 through CPP-FR-010]

Evaluates all pending orders against each new tick. Calculates fill price using the configured slippage model. Applies commission and spread. Handles gap scenarios — if price gaps past a SL/TP, fills at gap price (not stop level).

**Slippage Model Interface**:

```cpp
class ISlippageModel {
public:
    virtual int32_t calculate(const OrderRequest& order, const Tick& tick,
                               const SymbolInfo& info, std::mt19937_64& rng) const = 0;
};
// Implementations: ZeroSlippage, FixedSlippage, RandomSlippage, LatencyProfileSlippage
```

**Commission Model Interface**: `ICommissionModel` with implementations: FixedPerLot, FixedPerTrade, SpreadMarkup, PercentageOfValue.

**Swap Model Interface**: `ISwapModel` calculates overnight charges based on swap points, volume, and holding duration. Supports swap types: points, percentage, money.

**Spread Model Interface**: `ISpreadModel` with implementations: FixedSpread, HistoricalSpread, TimeOfDaySpread.

### 6.4 State Manager

[REQ: CPP-FR-011 through CPP-FR-014]

Maintains: account balance/equity/margin, open positions, pending orders, closed deals, history orders. Equity recalculated on every tick. Supports serialization for checkpoint/restore. Emits state change events via ZMQ broadcaster.

### 6.5 Currency Conversion Engine

[REQ: TRD-FR-015 through TRD-FR-018]

Maintains a dependency graph of conversion rates. For EURJPY in a USD account, automatically resolves: EURJPY profit → USDJPY rate → USD profit. Rates update on every tick. Validates all required conversion paths at initialization — raises `ConfigError` if a path is missing.

### 6.6 Margin Calculator

[REQ: TRD-FR-019 through TRD-FR-023]

Calculates per-position margin: `(volume × contract_size × price) / leverage`, converted to account currency. Tracks total margin, free margin, margin level. Enforces margin call (reject new orders at <100%) and stop-out (close largest loser at <50%). Supports hedging mode (reduced margin for hedged positions).

### 6.7 ZMQ Broadcaster

[REQ: CPP-FR-022 through CPP-FR-024]

Non-blocking PUB socket with topic-based routing (`equity`, `trade`, `order`, `tick`). High-water mark configured to drop oldest messages if buffer fills — never blocks the event loop. Messages serialized with MessagePack for compact binary encoding.

### 6.8 Build System

[REQ: CPP-FR-025 through CPP-FR-028]

CMake 3.25+ with vcpkg manifest mode. Dependencies: libzmq, hdf5, spdlog, toml++, googletest, googlebenchmark, nanobind. Produces a shared library (.dll/.so) wrapped by Nanobind into a Python-importable `hqt_engine` module. Supports Debug (symbols, sanitizers) and Release (O2 optimization) configurations.

### 6.9 Memory Safety

[REQ: CPP-FR-029 through CPP-FR-032]

- **Ownership**: C++ Engine owns all state. Python holds non-owning references via Nanobind `rv_policy::reference`.
- **Lifetime**: Bridge invalidates Python references when Engine is destroyed. Strategy code should never store references beyond a single callback invocation.
- **RAII**: All resources (files, sockets, memory) managed by RAII wrappers.
- **Smart pointers**: `unique_ptr` for exclusive ownership, `shared_ptr` only where explicit sharing is required. Raw owning pointers prohibited.
- **CI enforcement**: AddressSanitizer + UndefinedBehaviorSanitizer run on all C++ tests.

---

## 7. Bridge Layer Design (Nanobind)

[REQ: BRG-FR-001 through BRG-FR-007]

### 7.1 Module Structure

```cpp
NB_MODULE(hqt_engine, m) {
    bind_data_types(m);     // Tick, Bar, SymbolInfo
    bind_state_types(m);    // AccountState, Position, Order, Deal
    bind_engine(m);         // Engine class
    bind_callbacks(m);      // on_tick, on_bar, on_trade registration
    bind_commands(m);       // buy, sell, modify, close
}
```

### 7.2 Type Exposure

All C++ state exposed as read-only Python properties. Fixed-point integers converted to Python `float` at the boundary via `FixedPoint::to_double()`. Data passed by reference (zero-copy) — Python accesses C++ memory addresses directly.

### 7.3 GIL Management

```cpp
// C++ → Python callback: acquire GIL
engine.set_on_tick([py_cb](const Tick& tick) {
    nb::gil_scoped_acquire gil;
    py_cb(tick);
});

// Python → C++ long-running: release GIL
.def("run", [](Engine& e) {
    nb::gil_scoped_release release;
    e.run();
});
```

### 7.4 Error Propagation

C++ `hqt::HQTException` subclasses registered as Python exceptions. Bridge wraps all C++ calls in try/catch and re-raises as the corresponding Python exception with full error context (code, message, module, timestamp).

---

## 8. Strategy Framework Design

### 8.1 Strategy Base Class

[REQ: STR-FR-008 through STR-FR-014]

```python
class Strategy(ABC):
    # Metadata
    name: str = "Unnamed Strategy"
    symbols: list[str] = []
    timeframes: list[str] = ["M1"]

    def __init__(self, context: ITradingContext):
        self._ctx = context

    # Lifecycle (override in subclass)
    def on_init(self) -> None: ...
    @abstractmethod
    def on_tick(self, tick) -> None: ...
    def on_bar(self, symbol, timeframe, bar) -> None: ...
    def on_trade(self, deal) -> None: ...
    def on_deinit(self) -> None: ...

    # Trading commands (delegate to context)
    def buy(self, symbol, volume, **kwargs): return self._ctx.buy(...)
    def sell(self, symbol, volume, **kwargs): return self._ctx.sell(...)
    def close_position(self, ticket, volume=0.0): ...
    def modify_order(self, ticket, **kwargs): ...

    # Data access (PIT-safe)
    def get_bars(self, symbol, timeframe, count, shift=0): ...

    # State access (read-only)
    @property
    def account(self): return self._ctx.account
    @property
    def positions(self): return self._ctx.positions
```

### 8.2 Strategy Parameters

```python
class StrategyParameter:
    """Descriptor for optimizable parameters with bounds."""
    def __init__(self, default, min_value=None, max_value=None, step=None, description=""): ...

# Usage:
class TrendNaive(Strategy):
    fast_period = StrategyParameter(10, min_value=2, max_value=100, step=1)
    slow_period = StrategyParameter(50, min_value=10, max_value=500, step=1)
```

The optimizer discovers `StrategyParameter` descriptors via introspection and generates the parameter grid automatically.

### 8.3 Indicator Library

[REQ: STR-FR-001 through STR-FR-007]

```python
class Indicator(ABC):
    @abstractmethod
    def calculate(self, data: np.ndarray) -> np.ndarray: ...  # Full recalc
    @abstractmethod
    def update(self, value: float) -> float: ...               # Incremental
    def reset(self) -> None: ...
    @property
    def ready(self) -> bool: ...  # True when warmup period complete
```

Organized by category: `trend.py` (SMA, EMA, WMA, DEMA, TEMA, HMA, KAMA, Ichimoku, SAR, SuperTrend, ADX), `momentum.py` (RSI, Stochastic, MACD, CCI, Williams %R, ROC, MFI), `volatility.py` (ATR, Bollinger, Keltner, Donchian, StdDev), `volume.py` (OBV, VWAP, Volume Profile, A/D).

---

## 9. Trading Framework Design

### 9.1 Unified Interface (Mode Router Pattern)

[REQ: TRD-FR-001 through TRD-FR-008]

```python
class ITradingContext(ABC):
    """Interface that strategies code against. Identical across all modes."""
    @abstractmethod
    def buy(self, symbol, volume, **kwargs) -> OrderResult: ...
    @abstractmethod
    def sell(self, symbol, volume, **kwargs) -> OrderResult: ...
    @abstractmethod
    def close_position(self, ticket, volume=0.0) -> bool: ...
    @abstractmethod
    def modify_order(self, ticket, **kwargs) -> OrderResult: ...
    @abstractmethod
    def cancel_order(self, ticket) -> bool: ...
    @abstractmethod
    def close_all(self) -> None: ...
    @property
    @abstractmethod
    def account(self) -> AccountInfo: ...
    @property
    @abstractmethod
    def positions(self) -> list[Position]: ...
    @property
    @abstractmethod
    def pending_orders(self) -> list[Order]: ...
    @abstractmethod
    def symbol_info(self, symbol) -> SymbolInfo: ...
    @abstractmethod
    def get_bars(self, symbol, timeframe, count, shift=0) -> np.ndarray: ...
```

**Mode Router**:

```python
class ModeRouter:
    """Selects the appropriate backend based on configuration."""

    @staticmethod
    def create_context(mode: str, config: Config) -> ITradingContext:
        match mode:
            case "backtest":
                return BacktestContext(config)       # Wraps C++ Engine
            case "paper":
                return PaperTradingContext(config)   # Simulated fills on live data
            case "live":
                return LiveTradingContext(config)    # Real broker via MT5 gateway
```

Strategy code never changes — only the runtime mode changes which backend processes the commands.

### 9.2 Order Types

[REQ: TRD-FR-009 through TRD-FR-014]

```python
class OrderType(IntEnum):
    MARKET_BUY = 0
    MARKET_SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5
    BUY_STOP_LIMIT = 6
    SELL_STOP_LIMIT = 7

class OrderFilling(IntEnum):
    FILL_OR_KILL = 0
    IMMEDIATE_OR_CANCEL = 1
    RETURN_REMAINDER = 2

class OrderExpiration(IntEnum):
    GTC = 0              # Good Till Cancel
    TODAY = 1            # End of trading day
    SPECIFIED = 2        # User-specified datetime

@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    order_type: OrderType
    volume: Decimal
    price: Decimal | None = None         # Required for limit/stop
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    deviation: int = 0                    # Max slippage (points)
    filling: OrderFilling = OrderFilling.FILL_OR_KILL
    expiration: OrderExpiration = OrderExpiration.GTC
    expiration_time: datetime | None = None
    magic_number: int = 0
    comment: str = ""
```

---

## 10. Backtesting Engine Design

### 10.1 Event-Driven Engine

[REQ: BKT-FR-001 through BKT-FR-004]

```python
class EventDrivenEngine:
    """Orchestrates event-driven backtesting using the C++ core."""

    def __init__(self, config: BacktestConfig):
        self.cpp_engine = hqt_engine.Engine(config.to_engine_config())
        self.strategy: Strategy | None = None
        self.result: BacktestResult | None = None

    def run(self, strategy_class: type[Strategy], params: dict = {}) -> BacktestResult:
        # 1. Load data into C++ engine
        for symbol in strategy_class.symbols:
            self._load_symbol_data(symbol)

        # 2. Load conversion pairs for currency conversion
        self._load_conversion_pairs()

        # 3. Initialize strategy
        self.strategy = strategy_class(BacktestContext(self.cpp_engine))
        self.strategy.apply_params(params)
        self.strategy.on_init()

        # 4. Register callbacks
        self.cpp_engine.set_on_tick(self.strategy.on_tick)
        self.cpp_engine.set_on_bar(self.strategy.on_bar)
        self.cpp_engine.set_on_trade(self.strategy.on_trade)

        # 5. Run C++ engine (GIL released during execution)
        self.cpp_engine.run()

        # 6. Cleanup
        self.strategy.on_deinit()

        # 7. Compute metrics and return result
        return self._build_result()
```

### 10.2 Vectorized Engine

[REQ: BKT-FR-005 through BKT-FR-007]

Accepts pre-computed signal arrays (`+1` = buy, `-1` = sell, `0` = hold) and simulates trades without per-bar callbacks. Uses NumPy vectorized operations for maximum speed. Produces results compatible with the same `BacktestResult` model.

### 10.3 Multi-Asset Portfolio Engine

[REQ: BKT-FR-008 through BKT-FR-011]

The C++ `GlobalClock` manages chronological ordering across all symbols. The portfolio engine wraps the same C++ core but loads multiple symbols and ensures the event loop processes all symbols at T1 before advancing to T2. Supports mixed data granularity (M1 bars for one symbol, tick data for another).

### 10.4 Performance Metrics

[REQ: BKT-FR-012 through BKT-FR-018]

```python
class MetricsCalculator:
    def calculate(self, result: BacktestResult) -> MetricsReport:
        return MetricsReport(
            returns=ReturnsMetrics(result),      # Total, annualized, monthly, daily
            risk=RiskMetrics(result),             # StdDev, drawdown, VaR, CVaR
            trade=TradeMetrics(result),            # Win rate, profit factor, expectancy
            ratios=RatioMetrics(result),           # Sharpe, Sortino, Calmar, Omega
            efficiency=EfficiencyMetrics(result),  # SQN, Ulcer, recovery factor
            distribution=DistributionMetrics(result), # Skew, kurtosis, normality
            benchmark=BenchmarkMetrics(result),   # Alpha, beta, correlation
        )
```

### 10.5 Parameter Optimization

[REQ: BKT-FR-024 through BKT-FR-028]

**Grid Search**:

```python
class GridOptimizer:
    def optimize(self, strategy_class, param_grid, config, objective) -> list[OptResult]:
        combinations = list(itertools.product(*param_grid.values()))

        # Distribute via Ray
        futures = []
        for params in combinations:
            future = ray_backtest_worker.remote(strategy_class, dict(zip(param_grid.keys(), params)), config)
            futures.append(future)

        results = ray.get(futures)
        return sorted(results, key=lambda r: objective(r), reverse=True)
```

**Agent Architecture**: Each Ray worker initializes an independent C++ Engine instance. Workers share read-only mmap data files. Worker count defaults to `physical_cores - 2`.

### 10.6 Monte Carlo & Stress Testing

[REQ: BKT-FR-029 through BKT-FR-032]

Trade sequence resampling: randomly reorder the trade log N times (default 10,000) and compute metrics for each permutation. Results reported as percentile distributions (5th, 25th, 50th, 75th, 95th) for final equity, max drawdown, Sharpe, and win rate. Parameter perturbation: add small random noise to parameters and re-run.

### 10.7 Walk-Forward Optimization

[REQ: BKT-FR-033 through BKT-FR-036]

```python
class WFOManager:
    def run(self, strategy_class, param_grid, config, wfo_config) -> WFOResult:
        windows = self.splitter.split(config.date_range, wfo_config)
        oos_equity_segments = []

        for window in windows:
            # Optimize on in-sample
            best_params = self.optimizer.optimize(
                strategy_class, param_grid,
                config.with_dates(window.in_sample_start, window.in_sample_end),
                wfo_config.objective
            )[0].params

            # Validate on out-of-sample
            oos_result = self.engine.run(
                strategy_class, best_params,
                config.with_dates(window.out_of_sample_start, window.out_of_sample_end)
            )
            oos_equity_segments.append(oos_result.equity_curve)

        combined_oos = concatenate(oos_equity_segments)
        return WFOResult(combined_oos, efficiency=oos_perf/is_perf)
```

### 10.8 Edge Lab

[REQ: BKT-FR-037 through BKT-FR-042]

Four edge detectors: EDS-0 (Null Model — random entry baseline), EDS-1 (Mean Reversion — z-score fade), EDS-2 (Trend Persistence — ATR breakout follow-through), EDS-3 (Session Edge — time-of-day alpha). Each produces statistical reports with confidence intervals, effect sizes, and p-values.

### 10.9 Backtest Storage & Reproducibility

[REQ: BKT-FR-043 through BKT-FR-046]

Every backtest stores: strategy name + version (git hash), parameters, engine config, data version hashes, random seed, date range, all metrics, complete trade log, engine version (C++ build hash + Python version). Deterministic replay via `reproduce(backtest_id)` retrieves all artifacts and re-runs.

---

## 11. Risk Management System Design

### 11.1 Risk Governor

[REQ: RSK-FR-014 through RSK-FR-016]

```python
class RiskGovernor:
    """Final gatekeeper — approves or rejects every order."""

    def __init__(self, config: RiskConfig, state_accessor):
        self.config = config
        self.state = state_accessor
        self.daily_loss = Decimal("0")
        self.trades_today = 0
        self._circuit_breaker_active = False

    def approve(self, order_request: OrderRequest) -> tuple[bool, str]:
        if self._circuit_breaker_active:
            return False, "Circuit breaker active — trading halted"

        checks = [
            self._check_max_positions(),
            self._check_max_daily_trades(),
            self._check_daily_loss_limit(),
            self._check_max_drawdown(),
            self._check_position_size_limit(order_request),
            self._check_correlated_exposure(order_request),
            self._check_margin_available(order_request),
        ]

        for passed, reason in checks:
            if not passed:
                self._log_violation(order_request, reason)
                return False, reason

        return True, "Approved"

    def on_trade_closed(self, deal):
        """Update running state after trade closes."""
        if deal.profit < 0:
            self.daily_loss += abs(deal.profit)
        if self.daily_loss >= self.config.max_daily_loss:
            self._activate_circuit_breaker()

    def check_equity_kill_switch(self, equity: Decimal):
        if equity < self.config.equity_kill_switch:
            self._trigger_emergency_shutdown()
```

### 11.2 Position Sizing

[REQ: RSK-FR-004 through RSK-FR-007]

```python
class PositionSizer(ABC):
    @abstractmethod
    def calculate(self, account, symbol_info, signal) -> Decimal: ...

class RiskPercentSizer(PositionSizer):
    """Size based on risk % of account with stop-loss distance."""
    def calculate(self, account, symbol_info, signal):
        risk_amount = account.balance * self.risk_pct
        sl_distance = abs(signal.entry_price - signal.stop_loss)
        pip_value = calculate_pip_value(symbol_info, account.currency)
        raw_lots = risk_amount / (sl_distance / symbol_info.point * pip_value)
        return validate_lot_size(raw_lots, symbol_info)
```

Implementations: FixedLot, RiskPercent, Kelly, ATRBased, FixedCapital, Milestone (progressive sizing at equity milestones). All validated against broker constraints (volume_min, volume_max, volume_step).

### 11.3 Regime Detection

[REQ: RSK-FR-008 through RSK-FR-010]

HMM-based baseline: classifies market into states (trending, mean-reverting, volatile, quiet) using return series features. Strategies can query current regime to adjust behavior. Risk limits can be tightened/loosened by regime.

### 11.4 Portfolio Allocation

[REQ: RSK-FR-011 through RSK-FR-013]

Methods: equal weight, risk parity (allocate inversely to volatility contribution), inverse volatility, maximum diversification. Weights recalculated at configurable intervals.

---

## 12. Live Trading System Design

### 12.1 Engine Core

[REQ: LIV-FR-001 through LIV-FR-003]

```python
class LiveTradingEngine:
    def __init__(self, config, strategy_class, gateway):
        self.cpp_engine = hqt_engine.Engine(config.to_live_config())
        self.gateway = gateway          # MT5BrokerGateway
        self.strategy = strategy_class(LiveTradingContext(self))
        self.governor = RiskGovernor(config.risk)
        self.state = EngineState.STOPPED

    def start(self):
        self.state = EngineState.RUNNING
        self.gateway.connect()
        self._reconcile_state()
        self.strategy.on_init()
        self.gateway.subscribe_ticks(self._on_tick)

    def _on_tick(self, tick):
        self.cpp_engine.update_market(tick)
        self.strategy.on_tick(tick)

    def pause(self): self.state = EngineState.PAUSED
    def resume(self): self.state = EngineState.RUNNING
    def stop(self):
        self.strategy.on_deinit()
        self.gateway.disconnect()
        self.state = EngineState.STOPPED
```

### 12.2 Signal-to-Order Flow

[REQ: LIV-FR-006 through LIV-FR-008]

```
Strategy.buy() ──► LiveTradingContext.buy()
    │
    ▼
Risk Governor: approve(order_request)
    │
    ├── REJECTED → log violation, notify, return error
    │
    ▼ APPROVED
Broker Gateway: send_order(translated_request)
    │
    ├── TIMEOUT → retry once, then log + notify
    │
    ▼ RESPONSE
Parse fill confirmation ──► Update local state
    │
    ▼
Notify (if configured) + Broadcast via ZMQ
```

Every step is logged with timestamp: signal → risk check → order sent → acknowledged → filled/rejected.

### 12.3 Emergency Shutdown

[REQ: LIV-FR-009 through LIV-FR-011]

Callable via: UI button, API endpoint, keyboard shortcut (Ctrl+Shift+X), or automatic risk governor trigger. Sequence: cancel all pending orders → close all positions at market → halt strategy → send notification → persist state + reason to database.

### 12.4 State Reconciliation

[REQ: LIV-FR-012 through LIV-FR-014]

On startup and after reconnection: query broker for current positions, orders, and balance. Compare with locally stored state. Minor discrepancies (swap differences) auto-reconciled. Major discrepancies (unknown positions, balance mismatch) flagged for user review before resuming.

### 12.5 MT5 Broker Gateway

[REQ: LIV-FR-015 through LIV-FR-020]

```python
class MT5BrokerGateway(BrokerGateway):
    """Communicates with MT5 terminal via MQL5 Bridge EA over ZeroMQ."""

    def __init__(self, config):
        self.tick_subscriber = zmq.SUB   # PUB/SUB for tick stream
        self.order_socket = zmq.REQ      # REQ/REP for order execution

    def send_order(self, request: OrderRequest) -> OrderResult:
        msg = self.translator.to_mt5_format(request)
        # e.g., "ORDER_SEND;EURUSD;BUY;1.0;SL=1.0900;TP=1.1100"
        self.order_socket.send_string(msg)
        reply = self.order_socket.recv_string(timeout=5000)
        return self.translator.parse_response(reply)

    def subscribe_ticks(self, callback):
        """Subscribe to live tick stream from MT5 EA."""
        while self.running:
            msg = self.tick_subscriber.recv()
            tick = self.translator.parse_tick(msg)
            callback(tick)
```

**MQL5 Bridge EA**: A stateless MQL5 Expert Advisor that opens ZMQ sockets and acts as a relay. Receives order commands as text, executes `OrderSend()`, returns confirmation. Streams every tick via PUB socket.

**Gateway Interface** (abstract for future broker support):

```python
class BrokerGateway(ABC):
    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def send_order(self, request) -> OrderResult: ...
    @abstractmethod
    def subscribe_ticks(self, callback) -> None: ...
    @abstractmethod
    def get_account_state(self) -> AccountState: ...
    @abstractmethod
    def get_positions(self) -> list[Position]: ...
    @abstractmethod
    def is_connected(self) -> bool: ...
```

---

## 13. Paper Trading System Design

[REQ: PAP-FR-001 through PAP-FR-005]

```python
class PaperTradingEngine:
    """Simulates order execution using live data without placing real orders."""

    def __init__(self, config, strategy_class, gateway):
        self.gateway = gateway   # Only for tick data, no order execution
        self.fill_simulator = SimulatedFill(config.slippage_model, config.commission_model)
        self.state_manager = PaperStateManager(config.initial_balance)
        self.strategy = strategy_class(PaperTradingContext(self))
        self.snapshot_scheduler = SnapshotScheduler(config.snapshot_interval)

    def _on_order(self, request: OrderRequest) -> OrderResult:
        # Simulate fill using current market prices + slippage model
        fill = self.fill_simulator.simulate(request, self.current_tick)
        self.state_manager.apply_fill(fill)
        self.db.store_paper_trade(fill)
        return fill.to_order_result()
```

Configuration flag only: `mode = "paper"` vs `mode = "live"`. Same strategy code, same risk governor. Account snapshots stored at configurable intervals for performance tracking.

---

## 14. Notification System Design

[REQ: NTF-FR-001 through NTF-FR-007]

```python
class NotificationChannel(ABC):
    @abstractmethod
    def send(self, notification: Notification) -> bool: ...
    @abstractmethod
    def is_available(self) -> bool: ...
    @abstractmethod
    def test_connection(self) -> bool: ...

class NotificationManager:
    def __init__(self, config, channels: dict[str, NotificationChannel]):
        self.channels = channels
        self.routing_rules = config.routing  # type → channels mapping
        self.rate_limiter = RateLimiter(config.max_per_minute)

    def notify(self, notification: Notification):
        if not self.rate_limiter.allow():
            return
        for channel_name in self.routing_rules.get(notification.type, []):
            channel = self.channels.get(channel_name)
            if channel and channel.is_available():
                channel.send(notification)
        self.db.store_notification(notification)
```

Channels: `TelegramChannel` (Bot API over HTTPS), `EmailChannel` (SMTP/TLS). Rate-limited to prevent spam. All notifications stored in database for audit trail.

---

## 15. API Layer Design

[REQ: API-FR-001 through API-FR-005]

```python
# FastAPI application structure
app = FastAPI(title="HQT Trading System API")

# Route groups
app.include_router(backtesting_router, prefix="/api/v1/backtests")
app.include_router(optimization_router, prefix="/api/v1/optimizations")
app.include_router(live_trading_router, prefix="/api/v1/live")
app.include_router(paper_trading_router, prefix="/api/v1/paper")
app.include_router(data_router, prefix="/api/v1/data")
app.include_router(risk_router, prefix="/api/v1/risk")
app.include_router(notifications_router, prefix="/api/v1/notifications")
app.include_router(health_router, prefix="/api/v1/health")

# WebSocket for live streaming
@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    zmq_subscriber = create_zmq_subscriber()
    while True:
        msg = await zmq_subscriber.recv()
        await ws.send_json(parse_zmq_message(msg))
```

JWT authentication on all endpoints. Auto-generated OpenAPI docs at `/docs`.

---

## 16. Frontend UI Design

[REQ: GUI-FR-001 through GUI-FR-009]

```
┌──────────────────────────────────────────────────────────────────┐
│  HQT Trading System                                    [─][□][×]│
├──────────┬───────────────────────────────────────────────────────┤
│          │  ┌─────────────────────────────────────────────────┐  │
│ Dashboard│  │         PyQtGraph Candlestick Chart              │  │
│ ─────────│  │  EURUSD M1  |  OHLC + indicators + trade marks  │  │
│ Strategy │  │                                                  │  │
│ Editor   │  │  ═══════════════════════════════════════════════ │  │
│ ─────────│  │  ▲                                               │  │
│ Backtest │  │  │      ┌──┐  ┌──┐                               │  │
│ Results  │  │  │  ┌──┐│  │  │  │┌──┐    ┌──┐                  │  │
│ ─────────│  │  │  │  ││  │┌─┤  ││  │┌──┐│  │                  │  │
│ Risk     │  │  │──┤  ││  ││ │  ││  ││  ││  │──                │  │
│ Monitor  │  │  │  │  │└──┘│ └──┘│  ││  │└──┘                  │  │
│ ─────────│  │  │  └──┘    └─────┘  │└──┘                       │  │
│ Trade Log│  │  └───────────────────────────────────────────────│  │
│ ─────────│  └─────────────────────────────────────────────────┘  │
│ Optimize │                                                       │
│          │  ┌──────────────────┐  ┌────────────────────────────┐│
│          │  │ Open Positions   │  │ Account Summary            ││
│          │  │ EURUSD BUY 1.0  │  │ Balance: $10,000.00        ││
│          │  │ PnL: +$45.20    │  │ Equity:  $10,045.20        ││
│          │  │ GBPUSD SELL 0.5 │  │ Margin:  $2,500.00         ││
│          │  │ PnL: -$12.30    │  │ Free:    $7,545.20         ││
│          │  └──────────────────┘  └────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

**Architecture**: PySide6 QMainWindow with dock widgets. C++ engine runs in a `QThread` (separate from UI thread). Communication via Qt Signal/Slot — engine emits `new_data` signal, UI slot `update_chart()` redraws. Charts use PyQtGraph (GPU-accelerated, 60fps capable).

**Threading Model**:

```python
class EngineThread(QThread):
    """Runs C++ engine in a separate thread."""
    tick_processed = Signal(dict)   # Emitted after each tick
    trade_executed = Signal(dict)    # Emitted on fills
    engine_finished = Signal()       # Emitted when backtest complete

    def run(self):
        self.cpp_engine.set_on_tick(lambda t: self.tick_processed.emit(t.to_dict()))
        self.cpp_engine.run()        # Blocks this thread, not UI thread
        self.engine_finished.emit()
```

---

## 17. Database Design

### 17.1 Entity-Relationship Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   users      │────<│ user_settings│     │  strategies      │
└──────┬──────┘     └──────────────┘     └────────┬────────┘
       │                                           │
       │         ┌─────────────┐                  │
       └────────<│  sessions   │>─────────────────┘
                 └──────┬──────┘
                        │
          ┌─────────────┼────────────────┐
          ▼             ▼                ▼
   ┌────────────┐ ┌──────────────┐ ┌──────────────┐
   │ backtests  │ │optimizations │ │ simulations  │
   └─────┬──────┘ └──────┬───────┘ └──────────────┘
         │               │
         ▼               ▼
   ┌────────────┐ ┌──────────────┐
   │backtest_   │ │optimization_ │
   │trades      │ │results       │
   └────────────┘ └──────────────┘

   ┌────────────┐ ┌──────────────┐ ┌──────────────┐
   │live_trades │ │paper_trades  │ │account_      │
   │            │ │              │ │snapshots     │
   └────────────┘ └──────────────┘ └──────────────┘

   ┌────────────┐ ┌──────────────┐ ┌──────────────┐
   │edge_results│ │finance_      │ │notifications │
   │            │ │metrics       │ │              │
   └────────────┘ └──────────────┘ └──────────────┘
```

### 17.2 Core Tables

**backtests**:

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_id | FK → sessions | Parent session |
| strategy_name | VARCHAR(255) | Strategy class name |
| strategy_version | VARCHAR(64) | Git commit hash |
| strategy_params | JSONB | Frozen parameter dict |
| engine_config | JSONB | Frozen engine config |
| data_version_hashes | JSONB | {symbol: sha256_hash} |
| random_seed | BIGINT | For deterministic replay |
| engine_version | VARCHAR(128) | C++ build hash + Python version |
| date_start | TIMESTAMP | Backtest start date |
| date_end | TIMESTAMP | Backtest end date |
| symbols | JSONB | List of symbols |
| timeframes | JSONB | List of timeframes |
| initial_balance | DECIMAL(15,2) | Starting balance |
| final_balance | DECIMAL(15,2) | Ending balance |
| total_return_pct | DECIMAL(10,4) | Total return % |
| sharpe_ratio | DECIMAL(8,4) | Annualized Sharpe |
| max_drawdown_pct | DECIMAL(10,4) | Maximum drawdown % |
| total_trades | INTEGER | Trade count |
| win_rate | DECIMAL(6,4) | Win percentage |
| profit_factor | DECIMAL(8,4) | Gross profit / gross loss |
| metrics_full | JSONB | All computed metrics |
| equity_curve | BYTEA | Compressed equity curve array |
| created_at | TIMESTAMP | Record creation time |
| duration_seconds | REAL | Backtest runtime |

**backtest_trades**:

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| backtest_id | FK → backtests | Parent backtest |
| ticket | BIGINT | Trade ticket number |
| symbol | VARCHAR(20) | Symbol |
| type | SMALLINT | BUY=0, SELL=1 |
| volume | DECIMAL(10,4) | Lot size |
| open_price | DECIMAL(15,6) | Entry price |
| close_price | DECIMAL(15,6) | Exit price |
| stop_loss | DECIMAL(15,6) | SL level |
| take_profit | DECIMAL(15,6) | TP level |
| open_time | TIMESTAMP | Entry timestamp |
| close_time | TIMESTAMP | Exit timestamp |
| commission | DECIMAL(10,4) | Commission charged |
| swap | DECIMAL(10,4) | Swap charges |
| profit | DECIMAL(15,4) | Net PnL |
| magic_number | INTEGER | Strategy identifier |
| comment | VARCHAR(255) | Trade comment |

**live_trades**: Same schema as backtest_trades plus `broker_ticket` (broker-assigned ID), `execution_latency_ms`, and `slippage_points`.

**optimizations**:

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_id | FK → sessions | |
| strategy_name | VARCHAR(255) | |
| param_grid | JSONB | Full parameter grid definition |
| objective_function | VARCHAR(100) | e.g., "sharpe_ratio" |
| total_combinations | INTEGER | |
| completed | INTEGER | |
| best_params | JSONB | Best parameter set |
| best_objective_value | DECIMAL(10,4) | |
| worker_count | INTEGER | |
| duration_seconds | REAL | |
| created_at | TIMESTAMP | |

**optimization_results**: One row per parameter combination with params JSONB + all metrics.

**edge_results**: Stores edge lab outputs per symbol with statistical measures.

**notifications**: type, title, message, channel, delivery_status, timestamp.

**account_snapshots**: Paper/live trading periodic state captures.

### 17.3 Migration Strategy

Alembic with auto-generated migration scripts. Convention: `YYYY_MM_DD_HHMM_description.py`. Every schema change requires a migration. Rollback support for all migrations.

---

## 18. Build System & DevOps Design

### 18.1 CMake Structure

[REQ: CPP-FR-025 through CPP-FR-028]

```cmake
# Top-level CMakeLists.txt
cmake_minimum_required(VERSION 3.25)
project(hqt VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# vcpkg integration
find_package(spdlog REQUIRED)
find_package(cppzmq REQUIRED)
find_package(HDF5 REQUIRED)
find_package(tomlplusplus REQUIRED)

# C++ core library
add_subdirectory(cpp)

# Nanobind bridge
add_subdirectory(bridge)

# Tests & benchmarks
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(cpp/tests)
    add_subdirectory(cpp/benchmarks)
endif()
```

### 18.2 CI/CD Pipeline

[REQ: XCC-FR-008 through XCC-FR-012]

```yaml
# .github/workflows/ci.yml (simplified)
jobs:
  build-and-test:
    strategy:
      matrix:
        os: [windows-latest, ubuntu-latest]
        include:
          - os: windows-latest
            compiler: msvc
          - os: ubuntu-latest
            compiler: gcc-12
    steps:
      - uses: actions/checkout@v4
      - name: Setup vcpkg
      - name: Build C++ (CMake)
      - name: Run C++ Tests (Google Test)
      - name: Build Nanobind bridge
      - name: Run Bridge Tests (pytest)
      - name: Install Python deps
      - name: Run Python Tests (pytest)
      - name: Run E2E Regression Tests
      - name: Run Static Analysis (clang-tidy + mypy + ruff)

  sanitizers:
    runs-on: ubuntu-latest
    steps:
      - name: Build with AddressSanitizer + UBSan
      - name: Run C++ Tests under sanitizers

  release:
    needs: [build-and-test, sanitizers]
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Build release artifacts
      - name: Package Python wheel with compiled bridge
      - name: Upload artifacts
```

### 18.3 Versioning

Composite version: `{human_version}+cpp.{cpp_build_hash}.py.{python_pkg_version}`

Example: `1.0.0+cpp.a3f8b2c.py.1.0.0`

Stored with every backtest result for full provenance.

---

## 19. Testing Architecture

### 19.1 Test Pyramid

[REQ: XCC-FR-001 through XCC-FR-007]

```
              ┌───────────┐
              │  E2E      │  5 tests: full backtest, optimization,
              │  Tests    │  live trading, replay, crash recovery
              ├───────────┤
              │Integration│  ~50 tests: bridge types, callbacks,
              │  Tests    │  commands, memory, errors, data pipeline
              ├───────────┤
              │           │  ~500 tests:
              │   Unit    │  C++: event loop, matching, state, orders,
              │   Tests   │       currency, margin, slippage, fixed-point
              │           │  Python: indicators, strategy, risk, metrics,
              │           │          validation, config, notifications
              └───────────┘
```

**Coverage Targets**: C++ ≥ 80%, Python ≥ 85%, Bridge ≥ 90%.

### 19.2 Key Test Categories

**Numerical Correctness (Hypothesis)**: Property-based tests verifying PnL calculations, position sizing, and currency conversions hold across edge cases (extreme prices, tiny volumes, exotic pairs).

**Deterministic Replay**: Run a strategy twice with the same seed, data, and config — assert bit-identical results.

**Gap Scenario Tests**: Verify matching engine fills at gap price when price jumps past SL/TP.

**Margin Tests**: Verify margin calculation, margin call enforcement, and stop-out execution match manual calculations.

**Bridge Memory Safety**: Stress test with 1M+ bridge calls, verify no leaks via AddressSanitizer.

**Regression Tests**: Known strategies on known data with pre-computed expected results.

---

## 20. Deployment Architecture

### 20.1 Single-Machine Deployment (Primary)

```
Windows Machine
├── MT5 Terminal (live trading, data download)
│   └── HQT Bridge EA (ZMQ sockets)
├── HQT Application
│   ├── C++ Engine (hqt_engine.dll)
│   ├── Python Runtime
│   ├── PySide6 UI
│   ├── FastAPI (optional, local)
│   └── Ray (local, all cores)
├── Data Directory (SSD)
│   └── Parquet/HDF5 files
└── Database (SQLite local)
```

### 20.2 Split Deployment (Advanced)

```
Linux Server (backtest/optimization)     Windows Machine (live trading)
├── C++ Engine (.so)                     ├── MT5 Terminal
├── Ray Cluster Head                     │   └── HQT Bridge EA
├── Data Directory (NVMe)                ├── C++ Engine (.dll)
├── PostgreSQL                           ├── Python Runtime
└── N × Ray Workers                      └── PySide6 UI
    (each with C++ engine instance)          │
                                             └── Connects to PostgreSQL
                                                 on Linux server
```

### 20.3 Developer Setup

```bash
# 1. Clone and install vcpkg
git clone https://github.com/<org>/hqt.git
cd hqt && git submodule update --init

# 2. Build C++ core + bridge
cmake -B build -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build --config Release

# 3. Install Python package (editable)
pip install -e ".[dev]"

# 4. Initialize database
alembic upgrade head

# 5. Run tests
pytest tests/
cd build && ctest
```

---

## 21. Appendices

### Appendix A: SRS Requirement Traceability

| SRS Section | SDD Section | Coverage |
|-------------|-------------|----------|
| 4.1 Foundation | 4. Foundation Layer Design | Full |
| 4.2 Data Infrastructure | 5. Data Infrastructure Design | Full |
| 4.3 Strategy Framework | 8. Strategy Framework Design | Full |
| 4.4 Trading Framework | 9. Trading Framework Design | Full |
| 4.5 C++ Core Engine | 6. C++ Core Engine Design | Full |
| 4.6 Bridge Layer | 7. Bridge Layer Design | Full |
| 4.7 Backtesting Engine | 10. Backtesting Engine Design | Full |
| 4.8 Risk Management | 11. Risk Management Design | Full |
| 4.9 Live Trading | 12. Live Trading Design | Full |
| 4.10 Paper Trading | 13. Paper Trading Design | Full |
| 4.11 Notification System | 14. Notification Design | Full |
| 4.12 API Layer | 15. API Layer Design | Full |
| 4.13 Frontend UI | 16. Frontend UI Design | Full |
| 5.1 Testing Strategy | 19. Testing Architecture | Full |
| 5.2 CI/CD Pipeline | 18.2 CI/CD Pipeline | Full |
| 5.3 System Observability | 4. Foundation + 15. API (health) | Full |
| 5.4 Versioning | 18.3 Versioning | Full |
| 6. NFRs | Addressed in component designs | Full |
| 7. External Interfaces | 5.4, 12.5, 14. Notification | Full |
| 8. Data Requirements | 5.2, 17. Database Design | Full |

### Appendix B: Key Design Decisions Log

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| C++ build system | CMake, Meson, Bazel | CMake | Best Nanobind/vcpkg integration, widest IDE support |
| C++ package manager | vcpkg, Conan 2 | vcpkg | Manifest mode, CMake-native, Microsoft maintained |
| Python↔C++ binding | pybind11, Nanobind, cython | Nanobind | Lower overhead, newer, better zero-copy support |
| Price representation | double, Decimal, fixed-point int64 | Fixed-point int64 | Zero precision loss in C++, fastest arithmetic |
| Data format | Parquet, HDF5, CSV, custom binary | Parquet (primary) + HDF5 (fallback) | Columnar, compressed, mmap-friendly, wide ecosystem |
| UI framework | PySide6, Electron, Dear PyGui | PySide6 | Native look, mature, industry standard for trading |
| Charting | Matplotlib, PyQtGraph, Plotly | PyQtGraph | GPU-accelerated, Qt-native, handles real-time data |
| Distributed compute | Ray, Dask, multiprocessing | Ray | Actor model, cluster support, industry adoption |
| IPC messaging | ZeroMQ, gRPC, Redis | ZeroMQ | Lowest latency, simplest for PUB/SUB + REQ/REP |
| Config format | TOML, YAML, JSON, INI | TOML | Typed, readable, toml++ for C++, tomli for Python |
| Database ORM | SQLAlchemy, Peewee, raw SQL | SQLAlchemy 2.x | Most mature, multi-backend, Alembic migrations |
| API framework | FastAPI, Flask, Django REST | FastAPI | Async, auto-docs, Pydantic native, WebSocket support |

### Appendix C: Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-10 | — | Initial SDD covering all modules |

---

*End of Document — SDD-HQTBS-001 v1.0.0*
