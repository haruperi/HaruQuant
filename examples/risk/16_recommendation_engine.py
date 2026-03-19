"""
Example 16: Recommendation Engine

Phase 8 task-by-task walkthrough using the actual HaruQuant stack:
1. marginal risk engine
2. add/remove/resize evaluation
3. hedge candidate evaluation
4. rebalance suggestion logic
5. capital-efficiency ranking
6. action recommendation scoring
7. governance feasibility checks
8. ranked recommendation batch

Run:
    python examples/risk/16_recommendation_engine.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import (
    CapitalEfficiencyRanker,
    MarginalRiskEvaluator,
    PortfolioStateEngine,
    RecommendationAction,
    RecommendationEngine,
    RiskLimits,
    RiskScorecardEngine,
    RiskSnapshotEngine,
)
from apps.risk.optimization import AllocationOptimizer, HedgeOptimizer, RebalanceSuggestionEngine
from apps.trading import Engine, Trade, core


TIMEFRAME = "H1"
BAR_COUNT = 320
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "USDCHF"]
SYMBOL_TO_CLUSTER = {
    "EURUSD": "FOREX",
    "GBPUSD": "FOREX",
    "USDJPY": "FOREX",
    "XAUUSD": "METALS",
    "USDCHF": "FOREX",
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
    values = [10000.0, 10100.0, 10070.0, 9960.0, 9900.0, 9930.0, 9990.0]
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="h"), dtype=float)


class ExampleContext:
    def __init__(self):
        self.engine = Engine(backend="sim")
        seed_sim_account(self.engine)
        self.market_data = {}
        self.state = None
        self.snapshot = None
        self.scorecard = None
        self.recommendation_engine = RecommendationEngine()
        self.evaluator = MarginalRiskEvaluator()
        self.capital_efficiency_ranker = CapitalEfficiencyRanker()
        self.rebalance_engine = RebalanceSuggestionEngine()
        self.allocation_optimizer = AllocationOptimizer(
            capital_efficiency_ranker=self.capital_efficiency_ranker
        )
        self.hedge_optimizer = HedgeOptimizer()
        self.batch = None

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
        active_symbols = [symbol for symbol in SYMBOLS if symbol in self.market_data]
        latest_ts = max(df.index[-1] for df in self.market_data.values() if not df.empty)
        self.state = PortfolioStateEngine().build_state_from_engine(
            engine=self.engine,
            symbols=active_symbols,
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=pd.Timestamp(latest_ts).isoformat(),
            limits=BASE_LIMITS,
            symbol_to_cluster={symbol: cluster for symbol, cluster in SYMBOL_TO_CLUSTER.items() if symbol in active_symbols},
            metadata={
                "source": "phase8_recommendation_engine_example",
                "backend": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
                "equity_curve": synthetic_equity_curve(),
            },
        )
        self.snapshot = RiskSnapshotEngine().build_snapshot(self.state)
        self.scorecard = RiskScorecardEngine().build_scorecard(self.snapshot)
        self.batch = self.recommendation_engine.build_recommendations(
            self.state,
            snapshot=self.snapshot,
            scorecard=self.scorecard,
            candidate_symbols=["USDCHF", "XAUUSD"],
            hedge_symbols=["USDCHF", "USDJPY", "XAUUSD"],
            max_recommendations=8,
        )

    def open_positions(self) -> None:
        print("Opening small simulator positions...")
        trade = Trade(self.engine.api)
        for request in [
            {"symbol": "EURUSD", "side": "BUY", "volume": 0.12},
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
                comment="Phase 8 recommendation example",
            )
            print(
                f"  {request['symbol']} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )
        self.engine.monitor_account(verbose=False)

    def close(self):
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_marginal_risk_engine(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Marginal Risk Engine")
    action = RecommendationAction(
        action_type="reduce",
        symbol="EURUSD",
        delta_lots=-0.03,
        current_lots=float(ctx.state.position_map.get("EURUSD", 0.0)),
        projected_lots=float(ctx.state.position_map.get("EURUSD", 0.0)) - 0.03,
        rationale="Test a concentrated exposure reduction.",
    )
    result = ctx.evaluator.evaluate_action(ctx.state, action, snapshot=ctx.snapshot, scorecard=ctx.scorecard)
    print(f"  usefulness={result.recommendation_score.usefulness_score:.2f}")
    print(f"  explanation={result.explanation}")


def example_02_add_remove_resize_evaluation(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Add / Remove / Resize Evaluation")
    for result in ctx.allocation_optimizer.generate(
        ctx.state,
        ctx.snapshot,
        ctx.scorecard,
        evaluator=ctx.evaluator,
        candidate_symbols=["USDCHF"],
        max_items=3,
    ):
        print(
            f"  {result.action.action_type} {result.action.symbol} "
            f"delta={result.action.delta_lots:+.2f} usefulness={result.recommendation_score.usefulness_score:.2f}"
        )


def example_03_hedge_candidate_evaluation(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Hedge Candidate Evaluation")
    for result in ctx.hedge_optimizer.generate(
        ctx.state,
        ctx.snapshot,
        ctx.scorecard,
        evaluator=ctx.evaluator,
        hedge_symbols=["USDCHF", "USDJPY", "XAUUSD"],
        max_items=3,
    ):
        print(
            f"  hedge {result.action.symbol} delta={result.action.delta_lots:+.2f} "
            f"usefulness={result.recommendation_score.usefulness_score:.2f}"
        )


def example_04_rebalance_suggestion_logic(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Rebalance Suggestion Logic")
    for result in ctx.rebalance_engine.generate(
        ctx.state,
        ctx.snapshot,
        ctx.scorecard,
        evaluator=ctx.evaluator,
        max_items=3,
    ):
        print(
            f"  rebalance {result.action.symbol} delta={result.action.delta_lots:+.4f} "
            f"usefulness={result.recommendation_score.usefulness_score:.2f}"
        )


def example_05_capital_efficiency_ranking(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Capital-Efficiency Ranking")
    for item in ctx.capital_efficiency_ranker.rank(ctx.snapshot):
        print(
            f"  {item['symbol']}: ratio={item['capital_efficiency_ratio']:.2f} "
            f"weight={item['portfolio_weight']:.2f} rc={item['risk_contribution_frac']:.2f}"
        )


def example_06_action_recommendation_scoring(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Action Recommendation Scoring")
    top = ctx.batch.recommendations[0]
    print(f"  action={top.action.action_type} symbol={top.action.symbol}")
    print(f"  usefulness={top.recommendation_score.usefulness_score:.2f}")
    print(f"  score_delta={top.recommendation_score.score_delta:+.2f}")
    print(f"  var_delta={top.recommendation_score.var_delta:+.2f}")
    print(f"  es_delta={top.recommendation_score.es_delta:+.2f}")


def example_07_governance_feasibility_checks(ctx: ExampleContext) -> None:
    print_example_header("Example 07: Governance Feasibility Checks")
    for result in ctx.batch.recommendations[:5]:
        print(
            f"  {result.action.action_type} {result.action.symbol}: "
            f"feasible={result.governance_feasible} decision={result.governance_report.decision}"
        )


def example_08_ranked_recommendation_batch(ctx: ExampleContext) -> None:
    print_example_header("Example 08: Ranked Recommendation Batch")
    print(f"  summary={ctx.batch.summary}")
    for idx, result in enumerate(ctx.batch.recommendations, start=1):
        print(
            f"  {idx}. {result.action.action_type} {result.action.symbol} "
            f"delta={result.action.delta_lots:+.2f} usefulness={result.recommendation_score.usefulness_score:.2f}"
        )


def main() -> None:
    print_example_header("PHASE 8 RECOMMENDATION ENGINE")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_marginal_risk_engine(ctx)
        example_02_add_remove_resize_evaluation(ctx)
        example_03_hedge_candidate_evaluation(ctx)
        example_04_rebalance_suggestion_logic(ctx)
        example_05_capital_efficiency_ranking(ctx)
        example_06_action_recommendation_scoring(ctx)
        example_07_governance_feasibility_checks(ctx)
        example_08_ranked_recommendation_batch(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
