"""
Example 15: Scorecard Engine

Type: live-broker dependent manual demo

Phase 7 task-by-task walkthrough using the actual HaruQuant stack:
1. portfolio health score
2. concentration score
3. diversification score
4. leverage and margin safety scores
5. stress resilience score
6. regime alignment score
7. governance compliance score
8. overall risk quality score

Run:
    python backend/scripts/examples/risk/07_scorecard_engine.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.services.risk_engine import PortfolioStateEngine, RiskLimits, RiskScorecardEngine, RiskSnapshotEngine
from backend.services.simulation.engine import Engine`nfrom backend.services.execution.trade import Trade`nfrom backend.services.execution import core


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


def synthetic_equity_curve() -> pd.Series:
    values = [10000.0, 10100.0, 10060.0, 9960.0, 9890.0, 9920.0, 9980.0]
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="h"), dtype=float)


class ExampleContext:
    def __init__(self):
        self.engine = Engine(backend="sim")
        seed_sim_account(self.engine)
        self.market_data = {}
        self.state = None
        self.snapshot = None
        self.scorecard = None

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
                "source": "phase7_scorecard_engine_example",
                "backend": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
                "equity_curve": synthetic_equity_curve(),
            },
        )
        self.snapshot = RiskSnapshotEngine().build_snapshot(self.state)
        self.scorecard = RiskScorecardEngine().build_scorecard(self.snapshot)

    def open_positions(self) -> None:
        print("Opening small simulator positions...")
        trade = Trade(self.engine.api)
        for request in [
            {"symbol": "EURUSD", "side": "BUY", "volume": 0.10},
            {"symbol": "GBPUSD", "side": "BUY", "volume": 0.08},
            {"symbol": "USDJPY", "side": "SELL", "volume": 0.06},
            {"symbol": "XAUUSD", "side": "BUY", "volume": 0.04},
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
                comment="Phase 7 scorecard example",
            )
            print(
                f"  {request['symbol']} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )
        self.engine.monitor_account(verbose=False)

    def score(self, key: str):
        return next(row for row in self.scorecard.score_rows if row.score_key == key)

    def close(self):
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_portfolio_health_score(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Portfolio Health Score")
    row = ctx.score("portfolio_health_score")
    print(f"  score={row.score_value} confidence={row.confidence_label} context={row.context}")


def example_02_concentration_score(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Concentration Score")
    row = ctx.score("concentration_score")
    print(f"  score={row.score_value} confidence={row.confidence_label} context={row.context}")


def example_03_diversification_score(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Diversification Score")
    row = ctx.score("diversification_score")
    print(f"  score={row.score_value} confidence={row.confidence_label} context={row.context}")


def example_04_leverage_and_margin_safety_scores(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Leverage and Margin Safety Scores")
    for key in ["leverage_safety_score", "margin_safety_score"]:
        row = ctx.score(key)
        print(f"  key={key} score={row.score_value} confidence={row.confidence_label} context={row.context}")


def example_05_stress_resilience_score(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Stress Resilience Score")
    row = ctx.score("stress_resilience_score")
    print(f"  score={row.score_value} confidence={row.confidence_label} context={row.context}")


def example_06_regime_alignment_score(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Regime Alignment Score")
    row = ctx.score("regime_alignment_score")
    print(f"  score={row.score_value} confidence={row.confidence_label} context={row.context}")


def example_07_governance_compliance_score(ctx: ExampleContext) -> None:
    print_example_header("Example 07: Governance Compliance Score")
    row = ctx.score("governance_compliance_score")
    print(f"  score={row.score_value} confidence={row.confidence_label} context={row.context}")


def example_08_overall_risk_quality_score(ctx: ExampleContext) -> None:
    print_example_header("Example 08: Overall Risk Quality Score")
    row = ctx.score("overall_risk_quality_score")
    print(f"  score={row.score_value} confidence={row.confidence_label}")
    print(f"  components={row.context.get('components')}")


def main() -> None:
    print_example_header("PHASE 7 SCORECARD ENGINE")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_portfolio_health_score(ctx)
        example_02_concentration_score(ctx)
        example_03_diversification_score(ctx)
        example_04_leverage_and_margin_safety_scores(ctx)
        example_05_stress_resilience_score(ctx)
        example_06_regime_alignment_score(ctx)
        example_07_governance_compliance_score(ctx)
        example_08_overall_risk_quality_score(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
