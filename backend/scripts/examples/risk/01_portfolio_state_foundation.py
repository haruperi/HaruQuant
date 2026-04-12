"""
Example 01: Canonical Portfolio State Foundation

Type: live-broker dependent manual demo

Phase 1 task-by-task walkthrough using the actual HaruQuant stack:
1. define canonical risk-state models
2. reuse validators through canonical state construction
3. build a portfolio-state adapter layer from the existing engine
4. reconstruct deterministic point-in-time state

Run:
    python backend/scripts/examples/risk/01_portfolio_state_foundation.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from typing import Dict, Optional

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import PortfolioStateEngine, RiskLimits
from apps.trading import Engine, Trade, core


TIMEFRAME = "H1"
BAR_COUNT = 500
SYMBOLS = ["EURUSD", "GBPUSD"]
SYMBOL_TO_CLUSTER = {"EURUSD": "FOREX", "GBPUSD": "FOREX"}
BASE_LIMITS = RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12)


def print_example_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def mutable_sim_symbol(engine: Engine, symbol_name: str) -> Optional[core.SymbolInfo]:
    for idx, symbol_row in enumerate(engine.state.trading_symbols):
        name = str(getattr(symbol_row, "name", "") or "")
        if name != symbol_name:
            continue
        if isinstance(symbol_row, core.SymbolInfo):
            return symbol_row
        mutable = core.SymbolInfo(engine._to_dict(symbol_row))
        engine.state.trading_symbols[idx] = mutable
        return mutable
    return None


def round_volume(raw_volume: float, volume_min: float, volume_max: float, volume_step: float) -> float:
    volume = max(volume_min, min(raw_volume, volume_max))
    if volume_step > 0:
        volume = round(volume / volume_step) * volume_step
    return float(max(volume, volume_min))


def prepare_simulator_symbol(engine: Engine, symbol: str, latest_close: float) -> Optional[core.SymbolInfo]:
    raw_symbol = engine.client.symbol_info(symbol)
    if raw_symbol is None:
        return None
    if engine.symbol_info(symbol) is None:
        engine.state.trading_symbols.append(raw_symbol)
    mutable = mutable_sim_symbol(engine, symbol)
    if mutable is None:
        return None
    point = float(getattr(mutable, "point", 0.0001) or 0.0001)
    spread_points = float(getattr(mutable, "spread", 2.0) or 2.0)
    spread_value = point * max(spread_points, 1.0)
    mutable.bid = float(latest_close)
    mutable.ask = float(latest_close + spread_value)
    mutable.last = float(latest_close)
    return mutable


def load_market_data(engine: Engine, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
    data = engine.client.get_bars(symbol=symbol, timeframe=timeframe, count=count, start_pos=0)
    if data is None or data.empty:
        return pd.DataFrame()
    return data.copy()


def seed_sim_account(engine: Engine) -> None:
    account = engine.account_info()
    account["login"] = 123456
    account["server"] = "Backtest Simulation Server"
    account["company"] = "HaruQuant"
    account["balance"] = 10000.0
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = 10000.0
    account["margin"] = 0.0
    account["margin_free"] = 10000.0
    account["margin_level"] = 0.0
    account["commission"] = 7.0
    account["leverage"] = 400


class ExampleContext:
    def __init__(self):
        self.engine = Engine(backend="sim")
        seed_sim_account(self.engine)
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.latest_ts = None

    def setup(self) -> None:
        print("Example type: live-broker dependent manual demo")
        print("Loading real historical bars from connected client...")
        for symbol in SYMBOLS:
            data = load_market_data(self.engine, symbol, TIMEFRAME, BAR_COUNT)
            if data.empty:
                print(f"  {symbol}: no data available, skipped")
                continue
            self.market_data[symbol] = data
            close_col = "close" if "close" in data.columns else "Close"
            latest_close = float(data[close_col].iloc[-1])
            prepared_symbol = prepare_simulator_symbol(self.engine, symbol, latest_close)
            if prepared_symbol is None:
                print(f"  {symbol}: symbol info unavailable, skipped")
                continue
            print(f"  {symbol}: loaded {len(data)} bars, latest_close={latest_close:.5f}")

        if not self.market_data:
            raise RuntimeError("No market data was loaded. Ensure the MT5 client is connected.")

        self.open_example_positions()
        self.latest_ts = max(df.index[-1] for df in self.market_data.values() if not df.empty)

    def open_example_positions(self) -> None:
        print("Opening small simulator positions...")
        trade = Trade(self.engine.api)
        requests = [
            {"symbol": "EURUSD", "side": "BUY", "target_volume": 0.10},
            {"symbol": "GBPUSD", "side": "SELL", "target_volume": 0.05},
        ]
        for request in requests:
            symbol = request["symbol"]
            if symbol not in self.market_data or self.market_data[symbol].empty:
                continue
            symbol_info = self.engine.symbol_info(symbol)
            if symbol_info is None:
                continue
            point = float(getattr(symbol_info, "point", 0.0001) or 0.0001)
            volume = round_volume(
                raw_volume=float(request["target_volume"]),
                volume_min=float(getattr(symbol_info, "volume_min", 0.01) or 0.01),
                volume_max=float(getattr(symbol_info, "volume_max", 100.0) or 100.0),
                volume_step=float(getattr(symbol_info, "volume_step", 0.01) or 0.01),
            )
            trade.SetTypeFillingBySymbol(symbol)
            ask = float(getattr(symbol_info, "ask", 0.0) or 0.0)
            bid = float(getattr(symbol_info, "bid", 0.0) or 0.0)
            if request["side"] == "BUY":
                price = ask
                sl = price - (50 * point)
            else:
                price = bid
                sl = price + (50 * point)
            result = trade.PositionOpen(
                symbol=symbol,
                order_type=request["side"],
                volume=volume,
                price=price,
                sl=sl,
                tp=0.0,
                comment="Phase 1 portfolio state example",
            )
            print(
                f"  {symbol} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )
        self.engine.monitor_account(verbose=False)

    def build_state(self, as_of: Optional[str] = None, limits: Optional[RiskLimits] = None):
        effective_as_of = as_of or pd.Timestamp(self.latest_ts).isoformat()
        return PortfolioStateEngine().build_state_from_engine(
            engine=self.engine,
            symbols=[symbol for symbol in SYMBOLS if symbol in self.market_data],
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=effective_as_of,
            limits=limits or BASE_LIMITS,
            symbol_to_cluster=SYMBOL_TO_CLUSTER,
            metadata={
                "source": "simulator_plus_real_market_data",
                "backend": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
            },
        )

    def close(self):
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_define_canonical_risk_state_models(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Define Canonical Risk-State Models")
    state = ctx.build_state()
    print(f"account_type={type(state.account).__name__}")
    print(f"positions_type={type(state.positions[0]).__name__ if state.positions else 'none'}")
    first_symbol = next(iter(state.symbols.values()))
    first_market = next(iter(state.markets.values()))
    print(f"symbol_type={type(first_symbol).__name__}")
    print(f"market_type={type(first_market).__name__}")
    print(f"active_symbols={state.active_symbols}")


def example_02_reuse_validators_via_state_construction(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Reuse Validators via Canonical State Construction")
    state = ctx.build_state()
    print(f"has_errors={state.validation_summary.has_errors}")
    print(f"has_warnings={state.validation_summary.has_warnings}")
    if not state.validation_summary.issues:
        print("  no validation issues")
        return
    for issue in state.validation_summary.issues:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")


def example_03_build_portfolio_state_adapter_from_existing_engine(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Build Portfolio State Adapter from Existing Engine")
    state = ctx.build_state()
    print(f"account_equity=${float(state.account.equity):,.2f}")
    print(f"position_map={state.position_map}")
    print(f"exposures={state.exposures}")
    print("markets:")
    for symbol, market in state.markets.items():
        print(
            f"  {symbol}: timeframe={market.timeframe} rows={market.row_count} last_close={market.last_close}"
        )


def example_04_reconstruct_deterministic_point_in_time_state(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Reconstruct Deterministic Point-in-Time State")
    full_as_of = pd.Timestamp(ctx.latest_ts)
    earlier_as_of = pd.Timestamp(full_as_of - pd.Timedelta(hours=24)).isoformat()
    later_state = ctx.build_state()
    earlier_state = ctx.build_state(as_of=earlier_as_of)
    print(f"earlier_as_of={earlier_state.as_of}")
    print(f"later_as_of={later_state.as_of}")
    for symbol in earlier_state.active_symbols:
        earlier_rows = earlier_state.markets[symbol].row_count
        later_rows = later_state.markets[symbol].row_count
        print(f"  {symbol}: earlier_rows={earlier_rows} later_rows={later_rows}")


def main() -> None:
    print_example_header("PHASE 1 PORTFOLIO STATE FOUNDATION")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_define_canonical_risk_state_models(ctx)
        example_02_reuse_validators_via_state_construction(ctx)
        example_03_build_portfolio_state_adapter_from_existing_engine(ctx)
        example_04_reconstruct_deterministic_point_in_time_state(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
