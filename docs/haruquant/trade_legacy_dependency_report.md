# Trade Legacy Dependency Report

Date: 2026-02-18

## Scope

Legacy wrappers assessed:

- `apps.trade.AccountInfo`
- `apps.trade.SymbolInfo`
- `apps.trade.PositionInfo`
- `apps.trade.OrderInfo`
- `apps.trade.HistoryOrderInfo`
- `apps.trade.DealInfo`
- `apps.trade.TerminalInfo`
- `apps.trade.Trade`

Current status after cleanup pass:

- Removed:
  - `apps.trade.PositionInfo`
  - `apps.trade.OrderInfo`
  - `apps.trade.HistoryOrderInfo`
  - `apps.trade.DealInfo`
  - `apps.trade.TerminalInfo`
- Remaining:
  - `apps.trade.AccountInfo`
  - `apps.trade.SymbolInfo`
  - `apps.trade.Trade`

Goal:

- Remove legacy wrappers where safe.
- Keep live MT5 execution working.

## Runtime Dependencies (apps/)

Current non-test imports of `apps.trade`:

- `apps/live/engine.py`
  - imports: `AccountInfo`, `SymbolInfo`, `Trade`
- `apps/live/safety_checks.py`
  - imports: `AccountInfo`, `SymbolInfo`
- `apps/live/position_manager.py`
  - imports: `Trade`
- `apps/live/portfolio_manager.py`
  - imports: `AccountInfo`
- `apps/live/trade_executor.py`
  - imports: `SymbolInfo`, `Trade`
- `apps/api/routes/live.py`
  - imports: `AccountInfo`
- `apps/api/routes/dashboard/broker.py`
  - imports: `AccountInfo`
- `apps/simulation/engine.py`
  - imports: `PositionInfo`
- `apps/simulation/simulator.py`
  - imports: `AccountInfo`, `Trade`
- `apps/simulation/utils.py`
  - imports: `PositionInfo`

## Test/Usage Dependencies (tests/)

- Risk usage examples:
  - `tests/usage/risk/01_position_sizing.py` ... `tests/usage/risk/08_integrate_existing_system.py`
  - import: `AccountInfo`
- Trade usage examples:
  - `tests/usage/trade/order_send_simulator_example.py` (`Trade`)
  - `tests/usage/trade/pending_orders_simulator_example.py` (`PositionInfo`)
  - `tests/usage/trade/trade_example.py` (`Trade`) [intentional live example]
  - `tests/usage/trade/terminal_info_example.py` (`TerminalInfo`)
  - `tests/usage/trade/trade_simulator_example.py` (`PositionInfo`)
- Unit test:
  - `tests/unit/apps/trade/test_account_info.py` (`apps.trade.account_info.AccountInfo`)

## Blockers By Wrapper

- `Trade`: hard blocker for live MT5 execution path (`apps/live/*`, `apps/simulation/simulator.py`, `tests/usage/trade/trade_example.py`).
- `AccountInfo`: used in live/api/simulation runtime paths.
- `SymbolInfo`: used in live runtime paths.
- `PositionInfo`, `OrderInfo`, `HistoryOrderInfo`, `DealInfo`, `TerminalInfo`: removed in cleanup pass.

## Safe Deletion Order

Phase A: completed.

Phase B (runtime migration required first):

1. `SymbolInfo` (replace in `apps/live/engine.py`, `apps/live/safety_checks.py`, `apps/live/trade_executor.py`)
2. `AccountInfo` (replace in `apps/live/*`, `apps/api/routes/*`, `apps/simulation/simulator.py`)

Phase C (keep until C++ live transport exists):

1. `Trade` (live MT5 execution transport)

## Recommended Next Step

Do a focused migration of simulation runtime imports first:

- Replace `apps.trade.PositionInfo` with C++ bound `haruquant.sim.PositionInfo` in:
  - `apps/simulation/engine.py`
  - `apps/simulation/utils.py`

This unlocks deletion of one legacy wrapper with minimal live-system impact.
