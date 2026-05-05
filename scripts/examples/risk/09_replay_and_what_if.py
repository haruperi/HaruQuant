"""
Example 17: Replay and What-If Engine

Type: live-broker dependent manual demo

Phase 9 task-by-task walkthrough using the actual HaruQuant stack:
1. timeline reconstruction
2. replay clock stepping
3. per-frame risk snapshot reconstruction
4. cockpit payload generation
5. hypothetical action injection
6. what-if comparison

Run:
    python scripts/examples/risk/09_replay_and_what_if.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from haruquant.risk import (
    HypotheticalOrderAction,
    ReplayClock,
    ReplayEngine,
    RiskLimits,
    TimelineReconstructor,
    WhatIfEngine,
)
from haruquant.simulation import Engine
from haruquant.execution import Trade
from haruquant.execution import core
from haruquant.data import TicksGenerator


TIMEFRAME = "H1"
BAR_COUNT = 40
SYMBOLS = ["EURUSD", "GBPUSD"]
SYMBOL_TO_CLUSTER = {"EURUSD": "FOREX", "GBPUSD": "FOREX"}
BASE_LIMITS = RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=6, corr_lookback=8)


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


def build_ticks(symbol: str, bars: pd.DataFrame, point_value: float) -> pd.DataFrame:
    ticks = TicksGenerator(
        model="timeframe_ticks",
        trading_timeframe=TIMEFRAME,
        point_value=point_value,
        spread_model="native_spread",
    ).generate(bars.copy())
    ticks = ticks.copy()
    ticks["symbol"] = symbol
    return ticks


class ExampleContext:
    def __init__(self):
        self.engine = Engine(backend="sim")
        seed_sim_account(self.engine)
        self.market_data = {}
        self.ticks_data = None
        self.replay_run = None
        self.what_if = None
        self.timeline = None

    def setup(self) -> None:
        print("Loading real historical bars from connected client...")
        merged_ticks = []
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
            point_value = float(getattr(prepared, "point", 0.0001) or 0.0001)
            merged_ticks.append(build_ticks(symbol, bars.tail(12), point_value))
            print(f"  {symbol}: loaded {len(bars)} bars, latest_close={latest_close:.5f}")

        self.open_positions()
        self.ticks_data = pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")
        self.timeline = TimelineReconstructor().build_timeline(self.ticks_data, frame_mode="bar")
        self.replay_run = ReplayEngine().replay(
            engine=self.engine,
            data=self.ticks_data,
            symbols=[symbol for symbol in SYMBOLS if symbol in self.market_data],
            timeframe=TIMEFRAME,
            market_data=self.market_data,
            limits=BASE_LIMITS,
            symbol_to_cluster=SYMBOL_TO_CLUSTER,
            metadata={
                "source": "phase9_replay_example",
                "backend_retiring": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
            },
            frame_mode="bar",
            include_recommendations=False,
            candidate_symbols=SYMBOLS,
            hedge_symbols=SYMBOLS,
            max_recommendations=5,
            max_frames=8,
            run_kwargs={"position_size": 0.01, "monitor_verbose": False, "show_progress": False},
        )
        if self.replay_run.frames:
            self.what_if = WhatIfEngine().evaluate(
                self.replay_run.frames[-1],
                actions=[HypotheticalOrderAction(action_type="add", symbol="EURUSD", delta_lots=0.02)],
                include_recommendations=True,
                candidate_symbols=SYMBOLS,
                hedge_symbols=SYMBOLS,
                max_recommendations=5,
            )

    def open_positions(self) -> None:
        print("Opening small simulator positions...")
        trade = Trade(self.engine.api)
        for request in [
            {"symbol": "EURUSD", "side": "BUY", "volume": 0.10},
            {"symbol": "GBPUSD", "side": "SELL", "volume": 0.08},
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
                comment="Phase 9 replay example",
            )
            print(
                f"  {request['symbol']} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )

    def close(self):
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_timeline_reconstruction(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Timeline Reconstruction")
    print(f"  timeline_points={len(ctx.timeline)}")
    if ctx.timeline:
        print(f"  first={ctx.timeline[0].frame_timestamp} capture={ctx.timeline[0].capture_timestamp}")
        print(f"  last={ctx.timeline[-1].frame_timestamp} capture={ctx.timeline[-1].capture_timestamp}")


def example_02_replay_clock_stepping(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Replay Clock Stepping")
    clock = ReplayClock.from_timeline(ctx.replay_run.timeline)
    first = clock.advance()
    second = clock.advance()
    print(f"  first_step={None if first is None else first.frame_timestamp}")
    print(f"  second_step={None if second is None else second.frame_timestamp}")
    print(f"  finished={clock.finished}")


def example_03_per_frame_risk_snapshot(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Per-Frame Risk Snapshot")
    frame = ctx.replay_run.frames[-1]
    print(f"  frame_index={frame.frame_index} timestamp={frame.timestamp}")
    print(f"  portfolio_var={frame.snapshot.summary.get('portfolio_var')}")
    print(f"  portfolio_es={frame.snapshot.summary.get('portfolio_es')}")
    print(f"  overall_score={frame.scorecard.summary.get('overall_risk_quality_score')}")


def example_04_cockpit_payload(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Cockpit Payload")
    cockpit = ctx.replay_run.frames[-1].cockpit_state
    print(f"  account={cockpit.account}")
    print(f"  governance={cockpit.governance}")
    print(f"  top_recommendations={cockpit.recommendations[:2]}")


def example_05_hypothetical_action_injection(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Hypothetical Action Injection")
    action = ctx.what_if.actions[0]
    print(f"  action_type={action.action_type} symbol={action.symbol} delta_lots={action.delta_lots}")


def example_06_what_if_comparison(ctx: ExampleContext) -> None:
    print_example_header("Example 06: What-If Comparison")
    print(f"  summary={ctx.what_if.summary}")
    projected = ctx.what_if.projected_recommendations
    if projected is not None and projected.recommendations:
        top = projected.recommendations[0]
        print(
            f"  projected_top={top.action.action_type} {top.action.symbol} "
            f"usefulness={top.recommendation_score.usefulness_score:.2f}"
        )


def main() -> None:
    print_example_header("PHASE 9 REPLAY AND WHAT-IF ENGINE")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_timeline_reconstruction(ctx)
        example_02_replay_clock_stepping(ctx)
        example_03_per_frame_risk_snapshot(ctx)
        example_04_cockpit_payload(ctx)
        example_05_hypothetical_action_injection(ctx)
        example_06_what_if_comparison(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
