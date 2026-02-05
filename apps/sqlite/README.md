# SQLite Database Module

Complete database interface for the HaruQuant algorithmic trading platform using SQLite with a modular, mixin-based architecture.

## Overview

The SQLite module provides a comprehensive database solution for managing all aspects of algorithmic trading operations, from user management to backtest analytics and live trading. It uses a **4-layer backtest architecture** for optimal data organization and query performance.

### Key Features

- **Modular Design**: Mixin-based architecture for clean separation of concerns
- **4-Layer Backtest Storage**: Optimized for analytics and reporting
- **WAL Mode**: Write-Ahead Logging for better concurrent access
- **Cascade Operations**: Automatic cleanup of related data
- **Type Safety**: Comprehensive type hints throughout
- **Error Handling**: Custom exceptions and transaction management
- **Performance**: Indexed tables and optimized queries

## Architecture

### Module Structure

```
apps/sqlite/
├── __init__.py             # Main SQLiteDatabase class
├── base.py                 # DatabaseBase - Connection management
├── schema.py               # SchemaManager - Schema initialization
├── users.py                # UserManager - User operations
├── market_data.py          # MarketDataManager - Data metadata
├── strategies.py           # StrategyManager - Strategy versioning
├── backtests.py            # BacktestManager - Backtest results
├── optimization.py         # OptimizationManager - Parameter optimization
├── live_trading.py         # LiveTradingManager - Live trading sessions
├── edge_discovery.py       # EdgeDiscoveryManager - Edge discovery & validation
├── sqx.py                  # SQXManager - StrategyQuant X imports
├── simulator.py            # SimulatorManager - Trade simulator sessions
└── database_operations.py  # Legacy compatibility wrapper
```

### Class Hierarchy

```python
SQLiteDatabase
├── DatabaseBase          # Connection & path management
├── SchemaManager         # Database initialization
├── UserManager           # User CRUD operations
├── MarketDataManager     # Market data metadata
├── StrategyManager       # Strategy versioning
├── SQXManager            # StrategyQuant X imports
├── BacktestManager       # Backtest storage & retrieval
├── OptimizationManager   # Optimization runs
├── LiveTradingManager    # Live trading sessions
├── EdgeDiscoveryManager  # Edge discovery & validation
└── SimulatorManager      # Trade simulator sessions
```

The `SQLiteDatabase` class inherits from all manager mixins, providing a unified interface to all database operations.

## Installation & Setup

### Basic Setup

```python
from apps.sqlite import SQLiteDatabase

# Create database instance (uses default path: data/database/haruquant.db)
db = SQLiteDatabase()

# Or specify custom path
db = SQLiteDatabase(db_path="custom/path/trading.db")

# Initialize database schema (creates all tables)
db.initialize_database()
```

### Default Database Path

By default, the database is created at:
```
<project_root>/data/database/haruquant.db
```

The directory is automatically created if it doesn't exist.

## Components

### 1. DatabaseBase (`base.py`)

**Purpose**: Foundation class for database connection management.

**Features**:
- Automatic database path resolution
- WAL mode configuration for concurrency
- Connection lifecycle management
- Custom exceptions

**Usage**:
```python
from apps.sqlite.base import DatabaseBase, UserAlreadyExistsError

db = DatabaseBase(db_path="my_database.db")
# WAL mode automatically enabled if database exists
```

**Custom Exceptions**:
- `UserAlreadyExistsError`: Raised when creating duplicate users

---

### 2. SchemaManager (`schema.py`)

**Purpose**: Database schema initialization and management.

**Key Methods**:
- `initialize_database()`: Creates all tables, indices, and foreign keys
- `delete_database()`: Removes the database file

**Database Schema Overview**:

#### User Management Tables
- `users`: User accounts with authentication
- `user_settings`: User preferences and configurations

#### Strategy Tables
- `strategies`: Strategy definitions
- `strategy_versions`: Version control for strategies
- `strategy_shares`: Strategy collaboration/sharing

#### Backtest Tables (4-Layer Architecture)

**Layer 1 - Run Configuration**:
- `backtest_runs`: Backtest metadata and configuration

**Layer 2 - Facts**:
- `backtest_trades`: Individual trade records
- `backtest_trade_events`: Trade lifecycle events
- `backtest_equity_curve`: Account equity over time

**Layer 3 - Derived Finance Metrics**:
- `finance_trade_metrics`: Trade statistics
- `finance_return_metrics`: Return analysis
- `finance_drawdown_metrics`: Drawdown analysis
- `finance_ratio_metrics`: Performance ratios (Sharpe, Sortino, etc.)
- `finance_risk_metrics`: Risk metrics (VaR, CVaR, etc.)
- `finance_efficiency_metrics`: Efficiency analysis

**Layer 4 - Research**:
- `finance_benchmark_metrics`: Benchmark comparisons
- `finance_distributions`: Statistical distributions

#### Optimization Tables
- `optimization_runs`: Parameter optimization runs
- `optimization_results`: Individual optimization results
- `walk_forward_windows`: Walk-forward analysis windows
- `monte_carlo_simulations`: Monte Carlo simulation results

#### Live Trading Tables
- `live_trading_sessions`: Live trading sessions
- `session_strategies`: Strategy assignments to sessions
- `live_signals`: Detected trading signals
- `live_positions`: Open and closed positions
- `live_position_events`: Position event audit trail
- `live_risk_rules`: Risk management rules
- `live_session_logs`: Session activity logs

#### Market Data Tables
- `market_data`: Market data file metadata

#### Edge Discovery Tables
- `edge_discovery_runs`: Edge discovery run configurations and results
- `edge_discovery_stats`: Statistical metrics for edge runs
- `edge_discovery_trades`: Individual trades from edge discovery

#### SQX (StrategyQuant X) Tables
- `sqx_strategy_edge`: Strategy metrics and scores from SQX imports
- `imports`: Import history log

#### Simulator Tables
- `simulation_sessions`: Trade simulator sessions
- `simulation_trades`: Simulated trades
- `simulator_deals`: Low-level simulated deal data

**Usage**:
```python
# Initialize all tables
success = db.initialize_database()

# Reset database
db.delete_database()
db.initialize_database()
```

---

### 3. UserManager (`users.py`)

**Purpose**: User account and settings management.

**Key Methods**:

| Method | Description |
|--------|-------------|
| `create_user()` | Create new user with hashed password |
| `get_user()` | Retrieve user by ID, username, or email |
| `update_user()` | Update user details |
| `delete_user()` | Delete user (cascades to strategies, backtests, etc.) |
| `create_user_settings()` | Create default settings |
| `get_user_settings()` | Retrieve user settings |
| `update_user_settings()` | Update user preferences |
| `get_mt5_credentials()` | Get default MT5 broker credentials |
| `get_mt5_credentials_by_login()` | Get specific MT5 account |

**User Settings Fields**:
- `theme`, `language`, `timezone`
- `log_verbosity`, `performance_mode`
- `broker_credentials`: MT5 account details
- `trading_preferences`: Default trading parameters
- `notifications`, `alert_triggers`

**Usage**:
```python
# Create user
user_id = db.create_user(
    email="trader@example.com",
    username="trader123",
    password="secure_password",
    full_name="John Trader"
)

# Update settings
db.update_user_settings(user_id, {
    "theme": "dark",
    "trading_preferences": {
        "default_risk_pct": 1.0,
        "symbols": ["EURUSD", "GBPUSD"]
    }
})

# Get MT5 credentials
creds = db.get_mt5_credentials(user_id)
```

---

### 4. StrategyManager (`strategies.py`)

**Purpose**: Trading strategy version control and sharing.

**Key Methods**:

| Method | Description |
|--------|-------------|
| `create_strategy()` | Create new strategy |
| `create_strategy_version()` | Create new version |
| `get_strategy()` | Get strategy details |
| `get_user_strategies()` | Get all strategies for user |
| `get_strategy_versions()` | Get version history |
| `get_strategy_version()` | Get specific version |
| `update_strategy()` | Update strategy details |
| `delete_strategy()` | Delete strategy and versions |
| `delete_strategy_version()` | Delete specific version |
| `share_strategy()` | Share with another user |
| `unshare_strategy()` | Remove sharing |

**Strategy Fields**:
- `name`, `description`, `category`
- `status`: active/inactive/testing
- `is_public`: Public visibility
- `active_version_id`: Current version reference

**Version Fields**:
- `version`: Semantic version (e.g., "1.0.0")
- `file_path`: Path to strategy file
- `parameters`: Strategy parameters (JSON)
- `changelog`: Version changes

**Usage**:
```python
# Create strategy
strategy_id = db.create_strategy(
    user_id=user_id,
    name="MA Crossover",
    description="Moving average crossover strategy",
    category="Trend Following"
)

# Create version
version_id = db.create_strategy_version(
    strategy_id=strategy_id,
    version="1.0.0",
    file_path="strategies/ma_crossover.py",
    parameters={"fast_period": 10, "slow_period": 20},
    changelog="Initial release"
)

# Share strategy
db.share_strategy(
    strategy_id=strategy_id,
    shared_with_user_id=collaborator_id,
    permission="view"  # or "clone", "edit"
)
```

---

### 5. BacktestManager (`backtests.py`)

**Purpose**: Backtest execution tracking and results storage using 4-layer architecture.

**Key Methods**:

| Method | Description |
|--------|-------------|
| `create_backtest_run()` | Create new backtest run (Layer 1) |
| `save_backtest_result()` | Save complete backtest result (all layers) |
| `get_backtest_run()` | Get backtest configuration |
| `get_backtest_trades()` | Get all trades (Layer 2) |
| `get_backtest_equity_curve()` | Get equity curve (Layer 2) |
| `get_backtest_finance_metrics()` | Get all metrics (Layer 3) |
| `get_all_backtests()` | Get backtests with filters |
| `update_backtest_status()` | Update run status |
| `delete_backtest()` | Delete backtest (cascades to all layers) |

**4-Layer Architecture**:

**Layer 1 - Run**: Configuration and reproducibility
- Strategy details, date range, symbols
- Engine configuration, models used
- Initial/final balance
- Config hash for reproducibility

**Layer 2 - Facts**: Raw data
- Individual trades with full details
- Trade events (entries, exits, modifications)
- Equity curve points

**Layer 3 - Derived**: Calculated metrics
- Trade metrics: Win rate, profit factor, expectancy
- Return metrics: CAGR, volatility, Sharpe ratio
- Drawdown metrics: Max DD, ulcer index
- Ratio metrics: Sortino, Calmar, Omega
- Risk metrics: VaR, CVaR, risk of ruin
- Efficiency metrics: MFE/MAE, exit efficiency

**Layer 4 - Research**: Advanced analytics
- Benchmark comparisons
- Statistical distributions

**Usage**:
```python
# Create backtest run
backtest_id = db.create_backtest_run(
    strategy_name="MA Crossover",
    strategy_version="1.0.0",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    engine_type="event",
    data_resolution="tick",
    config_hash="abc123",
    symbols=["EURUSD"],
    timeframes=["H1"],
    initial_balance=10000.0
)

# Save complete backtest result (all 4 layers)
db.save_backtest_result(backtest_result, backtest_id)

# Retrieve metrics
metrics = db.get_backtest_finance_metrics(backtest_id)
sharpe = metrics['ratio_metrics']['sharpe']
max_dd = metrics['drawdown_metrics']['max_drawdown']
```

---

### 6. OptimizationManager (`optimization.py`)

**Purpose**: Parameter optimization, walk-forward analysis, and Monte Carlo simulations.

**Key Methods**:

**Optimization Runs**:
- `create_optimization_run()`: Create optimization
- `update_optimization_status()`: Update progress
- `get_optimization_run()`: Get optimization details
- `save_optimization_results()`: Save results
- `get_optimization_results()`: Retrieve results

**Walk-Forward Analysis**:
- `create_walk_forward_window()`: Create WF window
- `get_walk_forward_windows()`: Get all windows
- `get_walk_forward_summary()`: Get summary statistics

**Monte Carlo**:
- `create_monte_carlo_simulation()`: Create simulation
- `save_monte_carlo_results()`: Save results
- `get_monte_carlo_simulation()`: Get simulation details

**Usage**:
```python
# Create optimization
opt_id = db.create_optimization_run(
    strategy_name="MA Strategy",
    strategy_version="1.0.0",
    optimization_type="grid_search",
    optimization_method="exhaustive",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    parameter_space={
        "fast_period": [5, 8, 10, 13],
        "slow_period": [20, 21, 25, 30]
    },
    objective_function="sharpe_ratio",
    total_combinations=16
)

# Save results
results = [
    {
        "backtest_id": 101,
        "parameters": {"fast_period": 10, "slow_period": 21},
        "score": 2.15,
        "rank": 1,
        # ... other metrics
    }
]
db.save_optimization_results(opt_id, results)

# Walk-forward validation
window_id = db.create_walk_forward_window(
    optimization_id=opt_id,
    window_number=1,
    train_start=datetime(2023, 1, 1),
    train_end=datetime(2023, 6, 30),
    test_start=datetime(2023, 7, 1),
    test_end=datetime(2023, 9, 30),
    best_parameters={"fast_period": 10, "slow_period": 21},
    train_metrics={"return": 15.5, "sharpe": 1.8},
    test_metrics={"return": 12.3, "sharpe": 1.5}
)
```

---

### 7. LiveTradingManager (`live_trading.py`)

**Purpose**: Live and paper trading session management with signal and position tracking.

**Key Methods**:

**Sessions**:
- `create_live_session()`: Create trading session
- `get_live_session()`: Get session details
- `get_user_live_sessions()`: Get all sessions for user
- `update_live_session()`: Update session
- `delete_live_session()`: Delete session

**Session Strategies**:
- `add_strategy_to_session()`: Add strategy to session
- `get_session_strategies()`: Get session strategies
- `remove_strategy_from_session()`: Remove strategy

**Signals**:
- `create_live_signal()`: Create signal
- `update_live_signal()`: Update signal status
- `get_session_signals()`: Get signals for session

**Positions**:
- `create_live_position()`: Open position
- `update_live_position()`: Update position
- `get_session_positions()`: Get positions
- `create_position_event()`: Log position event

**Logging**:
- `create_session_log()`: Create log entry
- `get_session_logs()`: Retrieve logs

**Usage**:
```python
# Create session
session_id = db.create_live_session(
    user_id=user_id,
    session_name="Production Trading",
    mode="paper",  # or "live"
    max_total_risk_pct=2.0,
    max_positions=5,
    max_drawdown_pct=10.0
)

# Add strategy
db.add_strategy_to_session(
    session_id=session_id,
    strategy_version_id=version_id,
    symbols=["EURUSD", "GBPUSD"],
    timeframes=["H1"],
    max_risk_per_trade_pct=1.0
)

# Create signal
signal_id = db.create_live_signal(
    session_id=session_id,
    strategy_version_id=version_id,
    symbol="EURUSD",
    timeframe="H1",
    signal_type="BUY",
    signal_time=datetime.now().isoformat(),
    entry_price=1.0850,
    stop_loss=1.0820,
    take_profit=1.0910
)

# Execute signal -> create position
position_id = db.create_live_position(
    session_id=session_id,
    signal_id=signal_id,
    mt5_ticket=123456,
    symbol="EURUSD",
    type="BUY",
    open_time=datetime.now().isoformat(),
    open_price=1.0851,
    position_size=0.1
)

# Log event
db.create_position_event(
    position_id=position_id,
    event_type="entry",
    price=1.0851,
    size=0.1
)
```

---

### 8. MarketDataManager (`market_data.py`)

**Purpose**: Market data file metadata and validation tracking.

**Key Methods**:
- `save_market_data_metadata()`: Save data metadata
- `get_market_data_list()`: Get all market data records

**Metadata Fields**:
- `symbol`, `timeframe`, `source`
- `start_date`, `end_date`, `record_count`
- `validation_report`: Quality metrics (JSON)
- `file_path`: Path to actual data file

**Usage**:
```python
data_id = db.save_market_data_metadata({
    "symbol": "EURUSD",
    "timeframe": "H1",
    "source": "MT5",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "record_count": 8760,
    "validation_report": {
        "missing_bars": 0,
        "duplicates": 0,
        "quality_score": 100.0
    },
    "file_path": "data/market/EURUSD_H1_2023.csv"
})

# Get all market data
data_list = db.get_market_data_list()
```

---

### 9. EdgeDiscoveryManager (`edge_discovery.py`)

**Purpose**: Edge discovery and statistical validation for trading strategies.

**Key Methods**:

| Method | Description |
|--------|-------------|
| `save_edge_result()` | Save edge discovery result with stats and trades |
| `get_edge_run()` | Get edge run by ID |
| `get_edge_runs()` | Get edge runs with filtering |
| `get_edge_runs_count()` | Count edge runs with filters |
| `get_confirmed_edges()` | Get only confirmed edges |
| `get_edge_summary_rows()` | Get grouped summary by symbol/timeframe |
| `get_edge_summary()` | Get overall edge statistics |
| `get_edge_trades()` | Get trades for a run |
| `get_edge_stats()` | Get statistical metrics for a run |
| `delete_edge_run()` | Delete edge run and related data |

**Edge Discovery Fields**:

**Run Fields**:
- `symbol`, `timeframe`, `eds_name`, `eds_type`
- `n_trades`, `expectancy_r`, `win_rate`, `profit_factor`
- `ci_low`, `ci_high`, `p_value_perm`
- `verdict`: EDGE_CONFIRMED, POTENTIAL_EDGE, WEAK_SIGNAL, NO_EDGE, INSUFFICIENT_DATA
- `edge_confirmed`: Boolean (ci_low > 0 and p_value < 0.05)
- `config`: Edge detection configuration (JSON)

**Stats Fields**:
- `n_trades`, `expectancy_r`, `win_rate`, `profit_factor`
- `median_mae_r`, `median_mfe_r`, `avg_hold_bars`
- `ci_low`, `ci_high`, `p_value_perm`
- `extras`: Additional statistical metrics (JSON)

**Trade Fields**:
- `entry_time`, `exit_time`, `side`
- `entry_price`, `exit_price`, `r_multiple`
- `mae_r`, `mfe_r`, `hold_bars`
- `meta`: Trade metadata (JSON)

**Usage**:
```python
# Save edge discovery result
edge_result = {
    "symbol": "EURUSD",
    "timeframe": "H1",
    "eds_name": "EDS-1-MeanReversion",
    "config": {
        "bootstrap": {"n_boot": 2000, "ci_level": 0.95},
        "perm": {"n_perm": 2000}
    },
    "stats": {
        "n_trades": 150,
        "expectancy_r": 0.45,
        "win_rate": 0.58,
        "ci_low": 0.32,
        "ci_high": 0.58,
        "p_value_perm": 0.023
    },
    "trades": [...]
}

run_id = db.save_edge_result(edge_result, user_id=1, save_trades=True)

# Get confirmed edges
confirmed = db.get_confirmed_edges(symbol="EURUSD", limit=10)

# Get edge summary by symbol/timeframe
summary_rows = db.get_edge_summary_rows(symbol="EURUSD")

# Get overall statistics
summary = db.get_edge_summary()
print(f"Confirmation Rate: {summary['confirmation_rate']:.1%}")
print(f"Avg Expectancy: {summary['avg_expectancy_confirmed']:.3f}")
```

For detailed examples, see [`tests/usage/sqlite/usage_edge_discovery.py`](../../../tests/usage/sqlite/usage_edge_discovery.py).

---

### 10. SQXManager (`sqx.py`)

**Purpose**: StrategyQuant X (SQX) export management and strategy scoring.

**Key Methods**:

| Method | Description |
|--------|-------------|
| `merge_sqx_export()` | Merge SQX CSV export into database |
| `get_sqx_strategies()` | Retrieve SQX strategies |
| `update_strategy_scores()` | Update strategy scores |

**Merge Features**:
- **Column Mapping**: Maps CSV columns to canonical database columns
- **Symbol Canonicalization**: Normalizes symbols (e.g., `EURUSD_dukascopy` → `EURUSD`)
- **Win Percent Normalization**: Converts 0-100 scale to 0-1 if needed
- **Stage-Specific Metrics**: Adds stage prefixes (e.g., `a1_profit_factor`, `a2_net_profit`)
- **Purge Missing**: Optionally removes strategies not in current import

**Strategy Fields**:
- `strategy_name`, `symbol`, `timeframe`
- `profit_factor`, `net_profit`, `trades`
- `max_drawdown_pct`, `annual_return_pct`, `win_percent`
- `ret_dd_ratio`, `source_symbol`, `source_timeframe`
- `stage`, `last_seen_at`, `last_import_name`

**Stage-Specific Fields** (auto-generated with prefixes):
- `a1_*`: A1_OOS2 stage metrics
- `a2_*`: A2_OOS3 stage metrics
- `e1_*`: E1_WFM stage metrics
- `spread_max_retdd_ratio`: B2_SPREAD_MAX metric

**Score Fields**:
- `edge_score`, `robust_score`, `stability_score`
- `risk_score`, `simple_score`, `fragility_penalty`
- `base_score_0_1`, `final_score`
- `rank_in_symbol`, `rejected`

**Usage**:
```python
import pandas as pd

# Load SQX export CSV
df = pd.read_csv("sqx_export.csv")

# Define column mapping
mapping = {
    "strategy_name": "Strategy Name",
    "symbol": "Symbol (IS)",
    "timeframe": "TimeFrame (IS)",
    "profit_factor": "Profit Factor (IS)",
    "annual_return_pct": "Annual Return % (IS)"
}

# Merge into database
rows = db.merge_sqx_export(
    df=df,
    mapping=mapping,
    stage="CORE",
    import_name="import_2024_01",
    purge_missing=False
)

# Retrieve strategies
strategies = db.get_sqx_strategies(symbol="EURUSD")

# Update scores
score_df = pd.DataFrame({
    "strategy_name": ["MA_Cross_v1", "BB_Reversal_v2"],
    "edge_score": [0.85, 0.92],
    "final_score": [0.732, 0.813],
    "rank_in_symbol": [2, 1]
})

db.update_strategy_scores(score_df)
```

For detailed examples, see [`tests/usage/sqlite/usage_sqx.py`](../../../tests/usage/sqlite/usage_sqx.py).

---

### 11. SimulatorManager (`simulator.py`)

**Purpose**: Trade simulator session and deal management for practice trading.

**Key Methods**:

**Sessions**:
- `create_simulation_session()`: Create new simulation session
- `get_simulation_session()`: Get session by ID
- `list_simulation_sessions()`: List sessions for user
- `update_simulation_session()`: Update session fields
- `update_session_status()`: Update session status
- `save_simulation_state()`: Save current bar index for resume
- `get_paused_simulation_sessions()`: Get paused sessions
- `delete_simulation_session()`: Delete session and trades
- `delete_simulation_sessions_older_than()`: Clean up old sessions

**Trades**:
- `save_trade()`: Save simulated trade
- `get_simulation_trades()`: Get trades for session

**Deals**:
- `save_simulator_deal()`: Save low-level deal data
- `load_simulator_deals()`: Load deals by time range

**Session Fields**:
- `session_name`, `mode`, `status`
- `symbol`, `timeframe`
- `start_time`, `end_time`, `initial_balance`
- `speed_multiplier`, `current_bar_index`, `total_bars`
- `replay_source`, `replay_backtest_id`, `replay_file_name`
- `config`: Session configuration (JSON)
- `completed_at`: Completion timestamp

**Trade Fields**:
- `time`, `symbol`, `side`, `price`, `volume`
- `sl`, `tp`, `pnl`
- `reason`, `source`
- `payload`: Full trade data (JSON)

**Deal Fields**:
- `time`, `magic`, `symbol`, `type`, `direction`
- `volume`, `price`, `spread`, `sl`, `tp`
- `commission`, `margin_required`, `fee`, `swap`, `profit`
- `comment`, `reason`, `entry_reason`
- `session_id`: Associated session

**Usage**:
```python
from datetime import datetime

# Create simulation session
config = {
    "session_name": "EURUSD Practice",
    "mode": "manual",
    "symbol": "EURUSD",
    "timeframe": "H1",
    "start_time": datetime(2023, 1, 1),
    "end_time": datetime(2023, 12, 31),
    "initial_balance": 10000.0,
    "total_bars": 8760,
    "replay_file_name": "EURUSD_H1_2023.csv"
}

session_id = db.create_simulation_session(user_id=1, config=config)

# Save a trade
trade = {
    "time": datetime(2023, 1, 5, 10, 30),
    "symbol": "EURUSD",
    "side": "BUY",
    "price": 1.0850,
    "volume": 0.1,
    "sl": 1.0820,
    "tp": 1.0910,
    "pnl": 60.0,
    "reason": "Support bounce",
    "source": "manual"
}

trade_id = db.save_trade(session_id, trade)

# Save progress (for resume)
db.save_simulation_state(session_id, current_bar_index=500)

# Pause session
db.update_session_status(session_id, status="paused")

# Resume later
paused = db.get_paused_simulation_sessions(user_id=1)
db.update_session_status(session_id, status="running")

# Get all trades
trades = db.get_simulation_trades(session_id)

# Complete session
db.update_session_status(session_id, status="completed")
```

For detailed examples, see [`tests/usage/sqlite/usage_simulator.py`](../../../tests/usage/sqlite/usage_simulator.py).

---

## Advanced Features

### Foreign Key Constraints

All tables use foreign key constraints for referential integrity:
- `ON DELETE CASCADE`: Child records deleted with parent
- `ON DELETE SET NULL`: References nulled on parent delete

Example:
```sql
FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
```

### WAL Mode

Write-Ahead Logging (WAL) is automatically enabled for better concurrency:
- Readers don't block writers
- Writers don't block readers
- Multiple simultaneous readers
- Better performance for concurrent operations

### Indices

Performance-optimized indices on:
- Foreign keys
- Frequently queried fields
- Sort/filter columns

Examples:
```sql
CREATE INDEX idx_backtest_trades_backtest_id ON backtest_trades(backtest_id)
CREATE INDEX idx_backtest_trades_open_time ON backtest_trades(open_time)
CREATE INDEX idx_optimization_results_score ON optimization_results(score DESC)
```

### JSON Fields

Flexible storage for complex data:
- User settings
- Strategy parameters
- Validation reports
- Position metadata

Automatically serialized/deserialized:
```python
# JSON automatically handled
db.update_user_settings(user_id, {
    "trading_preferences": {"risk": 1.0}  # dict -> JSON
})

settings = db.get_user_settings(user_id)
# settings["trading_preferences"] is dict (parsed from JSON)
```

## Usage Examples

Comprehensive usage examples are available in `tests/usage/sqlite/`:
- `usage_init.py`: Main SQLiteDatabase class
- `usage_base.py`: DatabaseBase
- `usage_schema.py`: SchemaManager
- `usage_users.py`: UserManager
- `usage_strategies.py`: StrategyManager
- `usage_backtests.py`: BacktestManager
- `usage_optimization.py`: OptimizationManager
- `usage_live_trading.py`: LiveTradingManager
- `usage_market_data.py`: MarketDataManager
- `usage_edge_discovery.py`: EdgeDiscoveryManager
- `usage_sqx.py`: SQXManager
- `usage_simulator.py`: SimulatorManager

See `tests/usage/sqlite/README.md` for detailed documentation.

## Best Practices

### 1. Always Initialize

```python
db = SQLiteDatabase()
db.initialize_database()  # Creates tables if needed
```

### 2. Error Handling

```python
from apps.sqlite import SQLiteDatabase, UserAlreadyExistsError

try:
    user_id = db.create_user(...)
except UserAlreadyExistsError:
    user = db.get_user(username=username)
    user_id = user["id"]
```

### 3. Use Datetime Objects

```python
from datetime import datetime

backtest_id = db.create_backtest_run(
    start_date=datetime(2023, 1, 1),  # Use datetime objects
    end_date=datetime(2023, 12, 31),
    # ...
)
```

### 4. Leverage Cascading Deletes

```python
# Deleting user cascades to all related data
db.delete_user(user_id)  # Also deletes strategies, backtests, sessions
```

### 5. Use Type Hints

All methods have comprehensive type hints:
```python
def create_user(
    self,
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None,
    is_superuser: bool = False,
    encryption_key: Optional[bytes] = None,
) -> int:
    ...
```

### 6. Clean Up Test Data

```python
# For testing
db = SQLiteDatabase(db_path="test.db")
db.initialize_database()
# ... run tests ...
db.delete_database()  # Clean up
```

## Performance Considerations

### Query Optimization

1. **Use Indices**: All foreign keys and frequently queried fields are indexed
2. **Limit Results**: Use `limit` parameter when fetching large datasets
3. **Filter Early**: Apply filters at database level, not in Python

### Concurrency

1. **WAL Mode**: Enabled by default for better concurrent access
2. **Transaction Safety**: All operations use proper transaction handling
3. **Connection Management**: Connections opened/closed per operation

### Storage

1. **Normalized Schema**: Reduces redundancy
2. **JSON for Flexibility**: Complex data in JSON fields
3. **Cascade Deletes**: Automatic cleanup prevents orphaned records

## Integration

### With Logger Module

```python
from apps.logger import logger
from apps.sqlite import SQLiteDatabase

db = SQLiteDatabase()
# All operations automatically logged via apps.logger
```

### With Security Module

```python
from apps.utils.security import get_encryption_key, hash_password

# User passwords automatically hashed
user_id = db.create_user(
    email="user@example.com",
    username="user",
    password="plaintext"  # Automatically hashed
)
```

### With Backtest Engine

```python
from apps.backtest.result import BacktestResult

# Run backtest
result = backtest_engine.run(...)

# Save to database (all 4 layers)
backtest_id = db.save_backtest_result(result)
```

## Testing

### Unit Tests

```python
import unittest
from apps.sqlite import SQLiteDatabase

class TestUserManager(unittest.TestCase):
    def setUp(self):
        self.db = SQLiteDatabase(db_path="test.db")
        self.db.initialize_database()

    def tearDown(self):
        self.db.delete_database()

    def test_create_user(self):
        user_id = self.db.create_user(
            email="test@example.com",
            username="test",
            password="pass"
        )
        self.assertIsInstance(user_id, int)
```

### Integration Tests

See `tests/usage/sqlite/` for integration examples.

## Migration Guide

### From Version 1.x to 2.x

If upgrading from an older version:

1. **Backup Database**: Always backup before migration
2. **Run Migration Script**: Execute schema updates
3. **Verify Data**: Check all data migrated correctly
4. **Update Code**: Update code to use new API

### SQX Strategy Edge (strategy_name only)

1. **Backup Database**: Always backup before migration.
2. **Run Migration Script**:
   - `python scripts/migrate_sqx_strategy_edge.py`
3. **Verify Data**:
   - Confirm stage-prefixed columns are present (e.g., `a1_profit_factor`).

### Reinitialize Database (Clean Rebuild)

1. **Delete Database File**:
   - `data/database/haruquant.db`
2. **Recreate Schema**:
   - `python scripts/initialize_database.py`
3. **Reimport SQX Exports**:
   - Import each stage CSV through the SQX Import UI.

## Troubleshooting

### Common Issues

**Issue**: `Database locked` error
- **Solution**: Enable WAL mode (automatic) or reduce concurrent writes

**Issue**: Foreign key constraint failed
- **Solution**: Ensure parent records exist before creating child records

**Issue**: Duplicate user error
- **Solution**: Check if user exists before creating, or catch `UserAlreadyExistsError`

**Issue**: JSON decode error
- **Solution**: Ensure JSON fields contain valid JSON strings

## API Reference

For detailed API documentation, see:
- Type hints in source files
- Docstrings in each method
- Usage examples in `tests/usage/sqlite/`

## Contributing

When extending the SQLite module:

1. **Follow Mixin Pattern**: Create manager classes as mixins
2. **Add Type Hints**: All methods should have type hints
3. **Document Changes**: Update this README and add usage examples
4. **Test Thoroughly**: Add unit and integration tests
5. **Use Transactions**: Ensure data integrity with proper transaction handling

## License

Part of the HaruQuant trading platform.

## Support

For issues, questions, or contributions:
- Check usage examples in `tests/usage/sqlite/`
- Review source code docstrings
- Consult main project documentation
