"""
Example 1002: Core Risk Metric Snapshot

Phase 2 task-by-task walkthrough using the actual HaruQuant stack:
1. create metric interface and registry
2. implement position risk metrics
3. implement symbol risk metrics
4. implement currency exposure metrics
5. implement strategy group metrics
6. implement portfolio exposure and heat metrics
7. implement margin and leverage metrics
8. persist normalized metric rows

Run:
    python examples/risk/10_core_risk_metric_snapshot.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import PortfolioStateEngine, RiskLimits, RiskSnapshotEngine
from apps.trading import Engine, Trade, core


TIMEFRAME = "H1"
BAR_COUNT = 300
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]
SYMBOL_TO_CLUSTER = {"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"}
BASE_LIMITS = RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=60)


def print_example_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def mutable_sim_symbol(engine: Engine, symbol_name: str):
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


def round_volume(symbol_info, raw_volume: float) -> float:
    volume_min = float(getattr(symbol_info, "volume_min", 0.01) or 0.01)
    volume_max = float(getattr(symbol_info, "volume_max", 100.0) or 100.0)
    volume_step = float(getattr(symbol_info, "volume_step", 0.01) or 0.01)
    volume = max(volume_min, min(raw_volume, volume_max))
    if volume_step > 0:
        volume = round(volume / volume_step) * volume_step
    return float(max(volume, volume_min))


def prepare_symbol(engine: Engine, symbol: str, latest_close: float):
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


class ExampleContext:
    def __init__(self):
        self.engine = Engine(backend="sim")
        seed_sim_account(self.engine)
        self.market_data = {}
        self.snapshot = None
        self.state = None

    def setup(self) -> None:
        print("Loading real historical bars from connected client...")
        for symbol in SYMBOLS:
            bars = self.engine.client.get_bars(symbol=symbol, timeframe=TIMEFRAME, count=BAR_COUNT, start_pos=0)
            if bars is None or bars.empty:
                print(f"  {symbol}: no data available, skipped")
                continue
            self.market_data[symbol] = bars.copy()
            close_col = "close" if "close" in bars.columns else "Close"
            latest_close = float(bars[close_col].iloc[-1])
            prepared = prepare_symbol(self.engine, symbol, latest_close)
            if prepared is None:
                print(f"  {symbol}: symbol info unavailable, skipped")
                continue
            print(f"  {symbol}: loaded {len(bars)} bars, latest_close={latest_close:.5f}")

        self.open_positions()
        latest_ts = max(df.index[-1] for df in self.market_data.values() if not df.empty)
        self.state = PortfolioStateEngine().build_state_from_engine(
            engine=self.engine,
            symbols=[symbol for symbol in SYMBOLS if symbol in self.market_data],
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=pd.Timestamp(latest_ts).isoformat(),
            limits=BASE_LIMITS,
            symbol_to_cluster=SYMBOL_TO_CLUSTER,
            metadata={
                "source": "phase2_metric_snapshot_example",
                "backend": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
            },
        )
        self.snapshot = RiskSnapshotEngine().build_snapshot(self.state)

    def open_positions(self) -> None:
        print("Opening small simulator positions...")
        trade = Trade(self.engine.api)
        for request in [
            {"symbol": "EURUSD", "side": "BUY", "volume": 0.10},
            {"symbol": "GBPUSD", "side": "BUY", "volume": 0.08},
            {"symbol": "USDJPY", "side": "SELL", "volume": 0.06},   
        ]:
            symbol_info = self.engine.symbol_info(request["symbol"])
            if symbol_info is None:
                continue
            volume = round_volume(symbol_info, request["volume"])
            point = float(getattr(symbol_info, "point", 0.0001) or 0.0001)
            ask = float(getattr(symbol_info, "ask", 0.0) or 0.0)
            bid = float(getattr(symbol_info, "bid", 0.0) or 0.0)
            if request["side"] == "BUY":
                price = ask
                sl = price - (50 * point)
            else:
                price = bid
                sl = price + (50 * point)
            trade.SetTypeFillingBySymbol(request["symbol"])
            result = trade.PositionOpen(
                symbol=request["symbol"],
                order_type=request["side"],
                volume=volume,
                price=price,
                sl=sl,
                tp=0.0,
                comment="Phase 2 metric snapshot example",
            )
            print(
                f"  {request['symbol']} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )
        self.engine.monitor_account(verbose=False)

    def rows(self, family: str):
        return [row for row in self.snapshot.metric_rows if row.family == family]

    def close(self):
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_create_metric_interface_and_registry(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Create Metric Interface and Registry")
    print(f"metric_count={len(ctx.snapshot.metric_rows)}")
    print(f"metric_families={sorted({row.family for row in ctx.snapshot.metric_rows})}")


def example_02_position_risk_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Position Risk Metrics")
    for row in ctx.rows("position_risk")[:9]:
        print(
            f"  key={row.metric_key} scope_key={row.scope_key} value={row.numeric_value or row.text_value}"
        )


def example_03_symbol_risk_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Symbol Risk Metrics")
    for row in ctx.rows("symbol_risk")[:12]:
        print(
            f"  key={row.metric_key} scope_key={row.scope_key} value={row.numeric_value or row.text_value}"
        )


def example_04_currency_exposure_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Currency Exposure Metrics")
    for row in ctx.rows("currency_exposure"):
        print(f"  currency={row.scope_key} exposure={row.numeric_value}")


def example_05_strategy_group_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Strategy Group Metrics")
    strategy_rows = ctx.rows("strategy_risk")
    if not strategy_rows:
        print("  no strategy rows")
        return
    for row in strategy_rows[:12]:
        print(
            f"  key={row.metric_key} scope_key={row.scope_key} value={row.numeric_value or row.text_value}"
        )


def example_06_portfolio_exposure_and_heat_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Portfolio Exposure and Heat Metrics")
    for key in [
        "gross_exposure",
        "net_exposure",
        "portfolio_var",
        "portfolio_es",
        "gross_exposure_to_equity",
        "max_single_exposure_frac",
    ]:
        print(f"  {key}={ctx.snapshot.summary.get(key)}")


def example_07_margin_and_leverage_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 07: Margin and Leverage Metrics")
    for row in ctx.rows("margin_risk"):
        print(f"  key={row.metric_key} value={row.numeric_value}")


def example_08_persist_normalized_metric_rows(ctx: ExampleContext) -> None:
    print_example_header("Example 08: Persist Normalized Metric Rows")
    print("sample_rows:")
    for row in ctx.snapshot.metric_rows[:10]:
        print(
            f"  family={row.family} key={row.metric_key} scope={row.scope} "
            f"scope_key={row.scope_key} numeric={row.numeric_value} text={row.text_value}"
        )


def main() -> None:
    print_example_header("PHASE 2 CORE RISK METRIC SNAPSHOT")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_create_metric_interface_and_registry(ctx)
        example_02_position_risk_metrics(ctx)
        example_03_symbol_risk_metrics(ctx)
        example_04_currency_exposure_metrics(ctx)
        example_05_strategy_group_metrics(ctx)
        example_06_portfolio_exposure_and_heat_metrics(ctx)
        example_07_margin_and_leverage_metrics(ctx)
        example_08_persist_normalized_metric_rows(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
