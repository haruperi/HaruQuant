"""
Example 12: Structural Fragility Analytics

Type: live-broker dependent manual demo

Phase 4 task-by-task walkthrough using the actual HaruQuant stack:
1. symbol volatility state metrics
2. volatility-adjusted exposure
3. volatility shock loss estimates
4. rolling pairwise correlations
5. intra-portfolio correlation summary
6. redundancy and hidden overlap metrics
7. cluster exposure analysis
8. effective independent bets and diversification ratio

Run:
    python backend/scripts/examples/risk/04_structural_fragility_analytics.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from haruquant.risk import PortfolioStateEngine, RiskLimits, RiskSnapshotEngine
from haruquant.simulation import Engine
from haruquant.execution import Trade
from haruquant.execution import core


TIMEFRAME = "H1"
BAR_COUNT = 320
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
SYMBOL_TO_CLUSTER = {
    "EURUSD": "FOREX",
    "GBPUSD": "FOREX",
    "USDJPY": "FOREX",
    "XAUUSD": "METALS",
}
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
                "source": "phase4_structural_fragility_example",
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
            {"symbol": "GBPUSD", "side": "BUY", "volume": 0.09},
            {"symbol": "USDJPY", "side": "SELL", "volume": 0.07},
            {"symbol": "XAUUSD", "side": "BUY", "volume": 0.05},
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
                comment="Phase 4 structural fragility example",
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


def example_01_symbol_volatility_state_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Symbol Volatility State Metrics")
    for row in ctx.rows("volatility_risk"):
        if row.metric_key != "symbol_realized_volatility":
            continue
        print(f"  symbol={row.scope_key} realized_vol={row.numeric_value}")


def example_02_volatility_adjusted_exposure(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Volatility-Adjusted Exposure")
    for row in ctx.rows("volatility_risk"):
        if row.metric_key != "vol_adjusted_exposure":
            continue
        print(f"  symbol={row.scope_key} vol_adjusted_exposure={row.numeric_value}")


def example_03_volatility_shock_loss_estimates(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Volatility Shock Loss Estimates")
    for row in ctx.rows("volatility_risk"):
        if row.metric_key not in {"vol_shock_loss_estimate", "portfolio_vol_shock_loss_estimate"}:
            continue
        label = row.scope_key or "portfolio"
        print(f"  scope={label} shock_loss_estimate={row.numeric_value}")


def example_04_rolling_pairwise_correlations(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Rolling Pairwise Correlations")
    for row in ctx.rows("correlation_risk"):
        if row.metric_key != "pair_correlation":
            continue
        print(f"  pair={row.scope_key} correlation={row.numeric_value}")


def example_05_intra_portfolio_correlation_summary(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Intra-Portfolio Correlation Summary")
    for key in ["average_pair_correlation", "max_pair_correlation"]:
        value = next(
            row.numeric_value
            for row in ctx.rows("correlation_risk")
            if row.metric_key == key and row.scope == "portfolio"
        )
        print(f"  {key}={value}")


def example_06_redundancy_and_hidden_overlap_metrics(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Redundancy and Hidden Overlap Metrics")
    for family, key in [
        ("correlation_risk", "redundancy_score"),
        ("concentration", "hidden_overlap_score"),
    ]:
        value = next(
            row.numeric_value
            for row in ctx.snapshot.metric_rows
            if row.family == family and row.metric_key == key and row.scope == "portfolio"
        )
        print(f"  {key}={value}")


def example_07_cluster_exposure_analysis(ctx: ExampleContext) -> None:
    print_example_header("Example 07: Cluster Exposure Analysis")
    for row in ctx.rows("concentration"):
        if row.metric_key not in {"cluster_gross_exposure", "cluster_gross_exposure_frac"}:
            continue
        print(f"  cluster={row.scope_key} {row.metric_key}={row.numeric_value}")
    for row in ctx.rows("correlation_risk"):
        if row.metric_key not in {"cluster_average_correlation", "cluster_max_correlation"}:
            continue
        print(f"  cluster={row.scope_key} {row.metric_key}={row.numeric_value}")


def example_08_effective_independent_bets_and_diversification_ratio(ctx: ExampleContext) -> None:
    print_example_header("Example 08: Effective Independent Bets and Diversification Ratio")
    for key in ["effective_independent_bets", "diversification_ratio"]:
        value = next(
            row.numeric_value
            for row in ctx.rows("concentration")
            if row.metric_key == key and row.scope == "portfolio"
        )
        print(f"  {key}={value}")


def main() -> None:
    print_example_header("PHASE 4 STRUCTURAL FRAGILITY ANALYTICS")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_symbol_volatility_state_metrics(ctx)
        example_02_volatility_adjusted_exposure(ctx)
        example_03_volatility_shock_loss_estimates(ctx)
        example_04_rolling_pairwise_correlations(ctx)
        example_05_intra_portfolio_correlation_summary(ctx)
        example_06_redundancy_and_hidden_overlap_metrics(ctx)
        example_07_cluster_exposure_analysis(ctx)
        example_08_effective_independent_bets_and_diversification_ratio(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
