# Simulation Backtest Interface Refactor Plan

## Objective

Refactor the current backtest flow so the public interface is clean, config-driven, and simulation-centric:

```python
result = engine_instance.run(config)
```

The example layer should not reset simulator state, build ticks, instantiate strategies, merge symbols, or compute result internals. Those responsibilities should move into `services/simulation`.

The core simulator must remain fast and clean. It consumes prepared tick/array data and outputs clean records. Data loading, strategy preparation, tick generation, reporting, persistence, and metrics must stay outside the hot simulation loop.

## Current Problems

- `scripts/examples/trading/trade_example.py` owns production responsibilities such as runtime reset and tick preparation.
- `example_12_complete_backtests()` declares UI-style config but does not pass most of it into the engine.
- `build_symbol_ticks_for_backtest()` lives in an example script but should be simulation preparation logic.
- `reset_sim_runtime_state()` lives in an example script but should be engine/runtime logic.
- ~~`run_vectorized()` ignores `position_size` and hardcodes `0.01` lots.~~ Fixed in Phase 9 for fixed-lot sizing.
- `commission`, `slippage_config`, `spread_config`, `strategy`, `data_source`, and `trading_timeframe` are partially unused or inconsistently wired.
- `services/simulation/engine.py` mixes facade, orchestration, vectorized simulation, event-driven simulation, MT5 parity helpers, runtime state, and reporting-adjacent reconstruction logic.
- There is no stable config contract for a full simulation backtest.

## Target Interface

Example scripts should become thin wrappers:

```python
def example_12_complete_backtests():
    config = {
        "engine_type": "vectorized",
        "account": {
            "initial_balance": 10000.0,
            "commission": 7.0,
            "leverage": 400,
        },
        "data": {
            "source": "metatrader",
            "symbols": ["AUDUSD", "EURGBP", "NZDCHF"],
            "timeframe": "H1",
            "start": "2025-11-01",
            "end": "2025-12-31",
            "warmup_start": "2025-10-01",
        },
        "strategy": {
            "name": "TrendFollowingStrategy",
            "params": {
                "fast_period": 20,
                "slow_period": 50,
                "filter_period": 200,
            },
        },
        "execution": {
            "tick_model": "timeframe_ticks",
            "spread_model": "native_spread",
            "slippage_model": "fixed",
            "slippage_points": 1,
            "contract_size": 100000.0,
            "position_size": {
                "type": "fixed_lot",
                "lot_size": 0.1,
            },
        },
        "reporting": {
            "print_summary": True,
            "save_to_db": False,
        },
    }

    result = engine_instance.run(config)
    print_simulation_summary(result)
```

No example-level calls to:

- `reset_sim_runtime_state()`
- `build_symbol_ticks_for_backtest()`
- direct strategy construction
- manual tick merging
- manual trade counting
- direct database persistence

## Target Module Layout

Expand the existing simulation package instead of introducing a new `backtesting` package:

```text
services/simulation/
    __init__.py
    engine.py
    config.py
    runner.py
    data_preparation.py
    strategy_registry.py
    vectorized.py
    event_driven.py
    results.py
    reporting.py
    models.py
    route_support.py
    serializers.py
    session_py
    session_coordinator.py
    session_manager.py
    session_runtime.py
    session_service.py
    trade_service.py
```

Primary roles:

- `engine.py`: public facade, runtime state owner, routes `run(config)` into the simulation runner.
- `config.py`: typed simulation backtest config and validation.
- `runner.py`: full backtest orchestration.
- `data_preparation.py`: loads bars, applies strategy, trims warmup, generates ticks, merges symbols.
- `strategy_registry.py`: resolves strategy names to classes.
- `vectorized.py`: fast default simulator over prepared data.
- `event_driven.py`: slower confirmation simulator over prepared data.
- `results.py`: standard result contract and post-run enrichment.
- `reporting.py`: summaries and printable reports.

## Boundary Rules

### Public Facade

`Engine.run(config)` is the only public full-backtest entrypoint.

Responsibilities:

- Parse and validate config.
- Reset runtime state.
- Prepare data.
- Select simulation mode.
- Return a standard result.

### Simulation Runner

`runner.py` owns orchestration.

Responsibilities:

- Convert raw dict to typed config.
- Call engine runtime reset.
- Call data preparation.
- Route prepared data to `vectorized.py` or `event_driven.py`.
- Enrich result.
- Optionally call persistence/reporting hooks.

### Data Preparation

`data_preparation.py` owns pre-simulation work.

Responsibilities:

- Load historical bars from configured source.
- Instantiate strategy from registry.
- Run strategy lifecycle.
- Generate signal-ready bars.
- Trim warmup.
- Generate ticks through `TicksGenerator`.
- Attach symbol metadata columns.
- Merge portfolio tick stream.

### Core Simulators

`vectorized.py` and `event_driven.py` consume prepared data only.

Allowed:

- Consume prepared tick DataFrame or contiguous arrays.
- Apply execution rules.
- Update positions/cash/equity.
- Emit raw trades/equity/orders/positions.

Forbidden:

- No data loading.
- No strategy class imports.
- No config parsing.
- No database writes.
- No report printing.
- No UI/example assumptions.

## End-to-End Flow

1. Example builds a config dict.
2. Example calls `engine_instance.run(config)`.
3. `Engine.run()` delegates to `SimulationRunner`.
4. `SimulationConfig.from_dict()` validates and normalizes config.
5. `Engine.reset_runtime(config.account)` resets account, positions, orders, history, trades, and equity.
6. `SimulationDataPreparer.prepare(config, engine)` loads bars per symbol.
7. Strategy registry resolves `config.strategy.name`.
8. Strategy is instantiated with configured params per symbol.
9. `strategy.on_init()` is called.
10. `strategy.on_bar(bars)` creates signal columns.
11. Warmup rows are removed after indicators/signals are computed.
12. `TicksGenerator` creates standardized ticks.
13. Prepared symbol ticks are merged into one portfolio tick stream.
14. Runner calls `engine.run_prepared(prepared, config)`.
15. `engine.run_prepared()` routes to `vectorized.run_simulation()` by default.
16. `vectorized.py` prepares contiguous arrays.
17. Numba core runs fast execution loop.
18. Raw arrays are reconstructed into clean records.
19. `results.py` builds/enriches `SimulationRunResult`.
20. Optional reporting/persistence hooks consume the result.
21. `Engine.run(config)` returns the final result.

## Config Contract

### Required Top-Level Fields

- `engine_type`
- `account`
- `data`
- `strategy`
- `execution`

### `engine_type`

Supported:

- `vectorized`: default, fast, used for most backtests.
- `event_driven`: slower confirmation replay, used as final validation.

### `account`

Required:

- `initial_balance`

Optional:

- `commission`
- `leverage`
- `currency`

### `data`

Required:

- `source`
- `symbols`
- `timeframe`
- `start`
- `end`
- `warmup_start`

Supported initial source:

- `metatrader`

Future sources:

- `dukascopy`
- `csv`
- `database`

### `strategy`

Required:

- `name`
- `params`

Example:

```json
{
  "name": "TrendFollowingStrategy",
  "params": {
    "fast_period": 20,
    "slow_period": 50,
    "filter_period": 200
  }
}
```

### `execution`

Required:

- `tick_model`
- `spread_model`
- `contract_size`
- `position_size`

Supported initial tick models:

- `timeframe_ticks`
- `m1_ticks`
- `real_ticks`
- `synthetic_ticks`

Supported initial spread models:

- `native_spread`
- `fixed_spread`
- `variable_spread`

Supported initial position sizing:

- `fixed_lot`

Future position sizing:

- `fixed_percent`
- `fixed_fractional`
- `milestone`
- `kelly_criterion`
- `volatility_adjusted_atr`

### `reporting`

Optional:

- `print_summary`
- `save_to_db`
- `alias`
- `description`

## Implementation Phases

### Phase 1: Add Simulation Config

Create `services/simulation/config.py`.

Tasks:

- Add dataclasses for account, data, strategy, execution, position sizing, reporting, and full config.
- Add `SimulationConfig.from_dict(raw)`.
- Normalize dates to `datetime`.
- Normalize symbols to a list of strings.
- Default `engine_type` to `vectorized`.
- Validate required fields.
- Reject unknown engine types, tick models, spread models, and sizing modes.

Acceptance criteria:

- Valid example config parses successfully.
- Missing symbols/timeframe/strategy raises a clear error.
- Parsed config exposes typed fields instead of loose nested dict lookups.

### Phase 2: Add Strategy Registry

Create `services/simulation/strategy_registry.py`.

Tasks:

- Register current strategy classes.
- Add `get_strategy_class(name)`.
- Add `register_strategy(name, cls)`.
- Remove strategy imports from examples over time.

Acceptance criteria:

- `"TrendFollowingStrategy"` resolves to the current class.
- Unknown strategy names fail early with a clear error.

### Phase 3: Move Data Preparation

Create `services/simulation/data_preparation.py`.

Tasks:

- Move `build_symbol_ticks_for_backtest()` logic out of `trade_example.py`.
- Implement `SimulationDataPreparer.prepare(config, engine)`.
- Implement `prepare_symbol(...)`.
- Return `PreparedSimulationData`.
- Preserve existing behavior first: MT5 bars, strategy signals, warmup trim, `TicksGenerator`, symbol columns, merge.
- Route data loading by `data.source`: `metatrader`, `dukascopy`, and `local`.
- Load MT5/Dukascopy `real_ticks` from the same configured market data source.
- Load local CSV/parquet files for bars, M1 bars, and real ticks through `data.local_files`.

Acceptance criteria:

- Prepared ticks contain `bid`, `ask`, `entry_signal`, `exit_signal`, `is_bar_close`, and `symbol`.
- Prepared portfolio tick stream is sorted by datetime with stable merge ordering.
- Per-symbol tick counts are available in metadata.
- Local CSV/parquet data can be used without example scripts building ticks directly.
- `real_ticks` no longer fails for MT5, Dukascopy, or local sources when `bid` and `ask` data is provided.

### Phase 4: Move Runtime Reset Into Engine

Update `services/simulation/engine.py`.

Tasks:

- Add `Engine.reset_runtime(account_config)`.
- Move account reset and state clearing out of example script.
- Reset completed trades/equity and runtime trackers.
- Preserve simulator backend behavior.

Acceptance criteria:

- `Engine.reset_runtime()` fully replaces `reset_sim_runtime_state()`.
- Repeated `Engine.run(config)` calls start from clean state.

### Phase 5: Add Simulation Runner

Create `services/simulation/runner.py`.

Tasks:

- Implement `SimulationRunner`.
- Flow: parse config -> reset runtime -> prepare data -> run prepared simulation -> enrich result -> optional persistence/reporting hooks.
- Keep runner orchestration outside hot simulation internals.

Acceptance criteria:

- `SimulationRunner(engine).run(config_dict)` returns a result for a short date range.
- Runner does not import example scripts.

### Phase 6: Route Engine.run(config)

Update `Engine.run()`.

Tasks:

- Remove backward compatibility requirement.
- Make dict config the expected public input.
- Add internal `run_prepared(prepared, config)`.
- Route `vectorized` to `vectorized.py`.
- Route `event_driven` to `event_driven.py`.

Acceptance criteria:

- `engine_instance.run(config)` works.
- Direct raw DataFrame use is no longer the main public contract.

### Phase 7: Split Vectorized Simulator

Create `services/simulation/vectorized.py`.

Tasks:

- Move Numba constants and `_run_turbo_sim_numba`.
- Move vectorized prepared-data array extraction.
- Move trade/equity reconstruction that is specific to vectorized output.
- Expose `run_simulation(engine, prepared, config)`.

Acceptance criteria:

- Vectorized run produces same result as before for the same prepared data.
- `engine.py` no longer contains the Numba core.

### Phase 8: Split Event-Driven Simulator

Create `services/simulation/event_driven.py`.

Tasks:

- Move event-driven loop from `engine.py`.
- Keep engine methods needed for MT5-style order operations accessible.
- Expose `run_simulation(engine, prepared, config)`.

Acceptance criteria:

- Event-driven mode runs the same prepared tick stream.
- Event-driven remains slower but suitable for confirmation.

### Phase 9: Wire Position Size Into Vectorized Core

Tasks:

- Remove hardcoded `0.01` from vectorized core.
- Pass fixed lot size from config.
- Add `default_volume` scalar to Numba function.
- Later allow per-row/per-signal volume arrays.

Acceptance criteria:

- Config `lot_size=0.1` produces trades with size `0.1`.
- Config `lot_size=0.01` matches current benchmark behavior.

### Phase 10: Wire Execution Costs

Tasks:

- Pass `contract_size` from config.
- Pass commission config into vectorized core.
- Add fixed slippage points support.
- Keep spread handling in tick generation.

Acceptance criteria:

- `contract_size` affects PnL.
- Fixed lot, spread, and basic costs are deterministic.
- Existing no-cost benchmark can still be reproduced when costs are zero.

### Phase 11: Standardize Results

Create or expand `services/simulation/results.py`.

Tasks:

- Define `SimulationRunResult`.
- Include config snapshot and preparation metadata.
- Add total profit, total return, trade count, per-symbol summary, and warnings.
- Keep raw trades/equity accessible.

Suggested fields:

```text
config
engine_type
symbols
timeframe
start
end
processed_ticks
initial_balance
final_balance
final_equity
total_profit
total_return
trades
equity_curve
orders
positions
metrics
symbol_summary
warnings
metadata
```

Acceptance criteria:

- Example code no longer calculates trade counts manually.
- Result has a direct `total_profit` field.

### Phase 12: Move Reporting

Create `services/simulation/reporting.py`.

Tasks:

- Move `print_run_result_summary`.
- Move `print_portfolio_symbol_summary`.
- Move `print_trade_record_summary`.
- Add `print_simulation_summary(result)`.

Acceptance criteria:

- Example script only calls reporting functions.
- Reporting consumes result only and does not inspect engine state.

### Phase 13: Rewrite Example 12

Update `scripts/examples/trading/trade_example.py`.

Tasks:

- Replace procedural backtest setup with config dict.
- Call `engine_instance.run(config)`.
- Call `print_simulation_summary(result)` if desired.
- Remove local data preparation and reset calls from the example path.

Acceptance criteria:

- Example 12 reads like a clean UI contract.
- Example 12 contains no direct tick-building or runtime reset logic.

### Phase 14: Remove Obsolete Example Helpers

After migrated examples are stable, delete or move:

- `reset_sim_runtime_state`
- `build_symbol_ticks_for_backtest`
- `print_run_result_summary`
- `print_portfolio_symbol_summary`
- `print_trade_record_summary`
- `save_engine_backtest_snapshot`

Acceptance criteria:

- No production simulation code depends on `trade_example.py`.
- Example script is safe to delete without breaking simulation services.

### Phase 15: Tests

Add tests around the new simulation contract.

Minimum tests:

- Config parsing accepts the Example 12 config.
- Config parsing rejects missing required fields.
- Strategy registry resolves known strategies.
- Data preparer returns required tick columns.
- Vectorized simulator honors fixed lot size.
- `Engine.run(config)` returns a standard result.
- A short deterministic date range matches previous known output.
- Vectorized and event-driven outputs are comparable on a tiny deterministic fixture.

### Phase 16: Documentation

Update docs after implementation:

- `docs/haruquant/specs/System_Architecture.md`
- `docs/haruquant/workflows/Catalog.md`
- This plan with completed checkboxes or notes.

Add config examples if needed:

- `docs/haruquant/specs/Simulation_Config.md`

## Migration Checklist

- [x] Add `services/simulation/config.py`.
- [x] Add `services/simulation/strategy_registry.py`.
- [x] Add `services/simulation/data_preparation.py`.
- [x] Add `Engine.reset_runtime(account_config)`.
- [x] Add `services/simulation/runner.py`.
- [x] Change `Engine.run(config)` to use `SimulationRunner`.
- [x] Add `Engine.run_prepared(prepared, config)`.
- [x] Add `services/simulation/vectorized.py`.
- [x] Move vectorized Numba core out of `engine.py`.
- [x] Add `services/simulation/event_driven.py`.
- [x] Move event-driven loop out of `engine.py`.
- [x] Wire money-management position sizing into simulator routing.
- [x] Wire contract size into vectorized core from config.
- [x] Wire fixed slippage and commission config.
- [x] Add/expand `services/simulation/results.py`.
- [x] Add `services/simulation/reporting.py`.
- [x] Rewrite `example_12_complete_backtests()`.
- [x] Remove obsolete example-level simulation helpers from the Example 12 path.
- [x] Add config/data-prep/simulator tests.
- [ ] Run short backtest validation against broker data.
- [ ] Run full 10-year benchmark validation.
- [x] Update architecture/config documentation.

## Validation Strategy

Use three validation levels:

1. Tiny deterministic fixture:
   - Hand-built ticks.
   - Known entries/exits.
   - Exact expected PnL.

2. Short broker-data run:
   - One symbol.
   - Small date range.
   - Compare old flow vs new flow before deleting old helpers.

3. Full benchmark:
   - AUDUSD, EURGBP, NZDCHF.
   - H1.
   - 2015-01-01 to 2025-12-31.
   - Confirm runtime, PnL, trade count, and per-symbol summaries.

## Non-Goals For First Migration

- Do not implement all advanced metrics immediately.
- Do not implement all position sizing models immediately.
- Do not optimize reporting or persistence.
- Do not introduce a new `backtesting` namespace.
- Do not add VectorBT dependencies or references.
- Do not change strategy semantics unless required to preserve existing results.

## Design Principle

The high-level simulation interface should be clean:

```python
result = engine_instance.run(config)
```

The low-level simulator should stay clean and fast:

```text
prepared ticks/arrays -> vectorized core -> clean records
```

Everything else is orchestration around that core, not part of the core.
