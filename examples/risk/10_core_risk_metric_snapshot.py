"""
Example 10: Core Risk Metric Snapshot

This example builds on the existing simulator/trading integration and the
Phase 1 canonical state foundation:
- loads real historical bars from the connected MT5 client
- seeds the simulator with actual symbol metadata
- opens a few small simulator positions through the trading API
- reconstructs a canonical PortfolioState from the engine
- runs the Phase 2 risk snapshot engine to produce normalized metric rows

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


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _mutable_sim_symbol(engine: Engine, symbol_name: str):
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


def _seed_sim_account(engine: Engine) -> None:
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


def _round_volume(symbol_info, raw_volume: float) -> float:
    volume_min = float(getattr(symbol_info, "volume_min", 0.01) or 0.01)
    volume_max = float(getattr(symbol_info, "volume_max", 100.0) or 100.0)
    volume_step = float(getattr(symbol_info, "volume_step", 0.01) or 0.01)
    volume = max(volume_min, min(raw_volume, volume_max))
    if volume_step > 0:
        volume = round(volume / volume_step) * volume_step
    return float(max(volume, volume_min))


def _prepare_symbol(engine: Engine, symbol: str, latest_close: float):
    raw_symbol = engine.client.symbol_info(symbol)
    if raw_symbol is None:
        return None
    if engine.symbol_info(symbol) is None:
        engine.state.trading_symbols.append(raw_symbol)
    mutable = _mutable_sim_symbol(engine, symbol)
    if mutable is None:
        return None
    point = float(getattr(mutable, "point", 0.0001) or 0.0001)
    spread_points = float(getattr(mutable, "spread", 2.0) or 2.0)
    spread_value = point * max(spread_points, 1.0)
    mutable.bid = float(latest_close)
    mutable.ask = float(latest_close + spread_value)
    mutable.last = float(latest_close)
    return mutable


def main() -> None:
    _print_header("PHASE 2 CORE RISK METRIC SNAPSHOT")
    engine = Engine(backend="sim")
    try:
        _seed_sim_account(engine)
        trade = Trade(engine.api)
        market_data = {}

        print(f"Loading real {TIMEFRAME} bars from connected client...")
        for symbol in SYMBOLS:
            bars = engine.client.get_bars(symbol=symbol, timeframe=TIMEFRAME, count=BAR_COUNT, start_pos=0)
            if bars is None or bars.empty:
                print(f"{symbol}: no data available, skipped")
                continue
            market_data[symbol] = bars.copy()
            close_col = "close" if "close" in bars.columns else "Close"
            latest_close = float(bars[close_col].iloc[-1])
            prepared = _prepare_symbol(engine, symbol, latest_close)
            if prepared is None:
                print(f"{symbol}: symbol info unavailable, skipped")
                continue
            print(f"{symbol}: loaded {len(bars)} bars, latest_close={latest_close:.5f}")

        requests = [
            {"symbol": "EURUSD", "side": "BUY", "volume": 0.10},
            {"symbol": "GBPUSD", "side": "BUY", "volume": 0.08},
            {"symbol": "USDJPY", "side": "SELL", "volume": 0.06},
        ]
        print("\nOpening small simulator positions...")
        for request in requests:
            symbol_info = engine.symbol_info(request["symbol"])
            if symbol_info is None:
                continue
            volume = _round_volume(symbol_info, request["volume"])
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
                f"{request['symbol']} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )
        engine.monitor_account(verbose=False)

        latest_ts = max(df.index[-1] for df in market_data.values() if not df.empty)
        state_engine = PortfolioStateEngine()
        state = state_engine.build_state_from_engine(
            engine=engine,
            symbols=[symbol for symbol in SYMBOLS if symbol in market_data],
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=pd.Timestamp(latest_ts).isoformat(),
            limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=60),
            symbol_to_cluster=SYMBOL_TO_CLUSTER,
            metadata={
                "source": "phase2_metric_snapshot_example",
                "backend": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
            },
        )

        snapshot = RiskSnapshotEngine().build_snapshot(state)
        _print_header("SNAPSHOT SUMMARY")
        for key in [
            "gross_exposure",
            "net_exposure",
            "portfolio_var",
            "portfolio_es",
            "gross_exposure_to_equity",
            "gross_leverage",
            "margin_used",
            "margin_used_frac",
        ]:
            print(f"{key}: {snapshot.summary.get(key)}")

        print("\nSample Metric Rows:")
        for row in snapshot.metric_rows[:15]:
            print(
                f"  family={row.family} key={row.metric_key} scope={row.scope} "
                f"scope_key={row.scope_key} value={row.numeric_value or row.text_value}"
            )

        print(f"\nTotal Metric Rows: {len(snapshot.metric_rows)}")
        print("This example uses real bars, the existing simulator, and the Phase 2 snapshot engine.")
    finally:
        if getattr(engine, "client", None) is not None:
            engine.client.shutdown()


if __name__ == "__main__":
    main()
