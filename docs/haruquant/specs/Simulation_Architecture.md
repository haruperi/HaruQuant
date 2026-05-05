# Simulation Architecture

HaruQuant's simulation system is designed for high-performance backtesting and MetaTrader 5 (MT5) parity. It follows a decoupled, config-driven architecture where the core simulation loop remains fast and focused, while orchestration, data preparation, and reporting are handled by dedicated services.

## Simulation Lifecycle

The lifecycle of a backtest simulation follows a strictly defined flow:

1.  **Config Definition**: The user or UI provides a JSON-compatible configuration dictionary.
2.  **Runner Orchestration**: The `SimulationRunner` parses the config, validates inputs, and manages the execution flow.
3.  **Runtime Reset**: The `Engine` resets its internal state (account, positions, orders, history) based on the `account` configuration.
4.  **Data Preparation**: The `SimulationDataPreparer` handles the heavy lifting of data retrieval and signal generation.
    *   **Bar Loading**: Loads historical OHLC data from the configured source (MT5, Dukascopy, or Local).
    *   **Strategy Instantiation**: Resolves and instantiates the strategy using the `StrategyRegistry`.
    *   **Signal Generation**: Executes `strategy.on_bar()` to generate entry/exit signals.
    *   **Tick Generation**: Transforms signal-ready bars into a high-resolution tick stream using the `TicksGenerator`.
    *   **Portfolio Merging**: Merges multi-symbol tick streams into a single, time-sorted portfolio tick stream.
5.  **Prepared Ticks**: The result is a unified `DataFrame` or set of arrays ready for the simulation core.
6.  **Simulator Execution**: The `Engine` routes the prepared data to the selected simulator backend:
    *   **Vectorized**: A high-speed, Numba-optimized core for rapid backtesting.
    *   **Event-Driven**: A slower, state-accurate replay for final validation and MT5 parity checks.
7.  **Result Enrichment**: The raw output from the simulator is packaged into a `SimulationRunResult`.
8.  **Reporting & Persistence**: Optional hooks trigger printable summaries or save results to the SQLite database.

## Implementation & Component Roles

### Public Facade (`engine.py`)
`Engine.run(config)` is the primary entry point. It delegates to the `SimulationRunner` and owns the runtime state trackers (deals, orders, account balance).

### Configuration (`config.py`)
Provides typed `dataclasses` and validation for the simulation parameters. It ensures that the input JSON is structurally correct and contains all required fields.

### Orchestration (`runner.py`)
The `SimulationRunner` is the "brain" of the backtest. It coordinates the sequence of data preparation, execution, and result gathering.

### Data Preparation (`data_preparation.py`)
Separates data acquisition from simulation logic. It is responsible for ensuring the simulator receives a clean, standardized tick stream regardless of the data source.

### Simulation Backends (`vectorized.py` & `event_driven.py`)
These are the "engines" of the system. They are strictly focused on consuming ticks and applying execution rules. They have no knowledge of databases, strategies, or file systems.

---

## Usage and Configuration

### Example Usage

```python
from services.simulation.engine import Engine

# Initialize engine
engine = Engine(backend="sim")

# Run simulation with config
config = {
    "engine_type": "vectorized",
    "account": {
        "initial_balance": 10000.0,
        "commission": 7.0,
        "leverage": 400
    },
    "data": {
        "source": "metatrader",
        "symbols": ["AUDUSD", "EURGBP"],
        "timeframe": "H1",
        "start": "2025-01-01",
        "end": "2025-12-31",
        "warmup_start": "2024-10-01"
    },
    "strategy": {
        "name": "TrendFollowingStrategy",
        "params": {
            "fast_period": 20,
            "slow_period": 50,
            "filter_period": 200
        }
    },
    "execution": {
        "tick_model": "timeframe_ticks",
        "spread_model": "native_spread",
        "contract_size": 100000,
        "position_size": {
            "type": "fixed_lot",
            "lot_size": 0.1
        }
    },
    "reporting": {
        "print_summary": True,
        "save_to_db": True
    }
}

result = engine.run(config)
```

### Configuration Schema (JSON)

#### Top-Level Fields
| Field | Type | Description |
| :--- | :--- | :--- |
| `engine_type` | `string` | `vectorized` (fast) or `event_driven` (accurate). |
| `account` | `object` | Initial balance, commission, and leverage. |
| `data` | `object` | Symbols, timeframe, and date ranges. |
| `strategy` | `object` | Strategy name and parameter dictionary. |
| `execution` | `object` | Models for ticks, spread, and sizing. |
| `risk` | `object` | (Optional) Advanced risk management settings. |
| `reporting` | `object` | Output and persistence settings. |

#### Account Config
```json
{
  "initial_balance": 10000.0,
  "commission": 7.0,
  "leverage": 400,
  "currency": "USD"
}
```

#### Data Config
```json
{
  "source": "metatrader",
  "symbols": ["AUDUSD", "EURGBP"],
  "timeframe": "H1",
  "start": "2025-01-01",
  "end": "2025-12-31",
  "warmup_start": "2024-10-01"
}
```

#### Execution Config
```json
{
  "tick_model": "timeframe_ticks",
  "spread_model": "native_spread",
  "slippage_model": "fixed",
  "slippage_points": 1,
  "contract_size": 100000,
  "position_size": {
    "type": "fixed_lot",
    "lot_size": 0.1
  }
}
```

#### Risk Config (Advanced)
```json
{
  "enabled": true,
  "risk_limits": {
    "var_cap_frac": 0.10,
    "es_cap_frac": 0.15,
    "max_margin_used_frac": 0.50
  },
  "enable_regime_detection": true,
  "enable_allocation": true,
  "correlation_preference": {
    "target_corr": 0.50,
    "penalty_strength": 2.0
  }
}
```
