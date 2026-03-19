"""
Example 11: Governance and Limits Engine

Phase 3 task-by-task walkthrough using the actual HaruQuant stack:
1. define limit models and policy contracts
2. implement pre-trade checks
3. implement post-trade checks
4. implement hard limits
5. implement soft limits
6. implement override recording model
7. implement circuit-breaker rules
8. implement risk-budget utilization tracking
9. store policy events and breach records

Run:
    python examples/risk/11_governance_limits_engine.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import (
    GovernanceEngine,
    PortfolioRiskEngine,
    PortfolioStateEngine,
    RiskLimits,
    RiskSnapshotEngine,
)
from apps.risk.regime import RegimeState
from apps.trading import Engine, Trade, core


TIMEFRAME = "H1"
BAR_COUNT = 300
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]
SYMBOL_TO_CLUSTER = {"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"}
BASE_LIMITS = RiskLimits(
    var_cap_frac=0.20,
    es_cap_frac=0.30,
    delta_var_cap_frac=0.05,
    delta_es_cap_frac=0.08,
    max_margin_used_frac=0.50,
    max_single_rc_frac=1.00,
    warning_utilization_frac=0.75,
    cluster_var_caps={"FOREX": 0.25},
    cluster_es_caps={"FOREX": 0.35},
)


def print_example_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_event_rows(events) -> None:
    if not events:
        print("  no events")
        return
    for event in events:
        print(
            f"  [{event.severity.upper()}] {event.rule_key}: {event.message} "
            f"(observed={event.observed_value}, threshold={event.threshold_value})"
        )


def print_utilizations(report) -> None:
    governance_state = report.governance_state
    if governance_state is None or not governance_state.utilizations:
        print("  no utilization records")
        return
    for key, utilization in governance_state.utilizations.items():
        print(
            f"  {key}: observed={utilization.observed:.4f} "
            f"threshold={utilization.threshold:.4f} "
            f"utilization={utilization.utilization_frac:.2%}"
        )


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


class StateRiskAdapter:
    def __init__(self, state):
        self.state = state

    def get_account_equity(self):
        return float(self.state.account.equity)

    def get_peak_equity(self):
        peak_equity = self.state.metadata.get("peak_equity")
        return None if peak_equity is None else float(peak_equity)

    def get_symbol_info(self, symbol):
        spec = self.state.symbols[symbol]
        return {
            "trade_contract_size": spec.contract_size,
            "trade_tick_value": spec.tick_value,
            "trade_tick_size": spec.tick_size,
        }

    def get_margin_required(self, symbol, lots):
        if self.state.account.margin_used is None:
            return None
        gross_lots = sum(abs(float(position.lots)) for position in self.state.positions)
        if gross_lots <= 0:
            return 0.0
        return abs(float(self.state.account.margin_used)) * (abs(float(lots)) / gross_lots)

    def get_bars(self, symbol, timeframe, count=100, start_pos=0):
        market = self.state.markets.get(symbol)
        if market is None:
            return None
        bars = market.bars.copy()
        if "Close" in bars.columns and "close" not in bars.columns:
            bars = bars.rename(columns={"Close": "close"})
        if start_pos > 0:
            bars = bars.iloc[start_pos:]
        if count is not None and count > 0:
            bars = bars.tail(int(count))
        return bars


class ExampleContext:
    def __init__(self):
        self.engine = Engine(backend="sim")
        seed_sim_account(self.engine)
        self.trade = Trade(self.engine.api)
        self.market_data = {}
        self.latest_ts = None

    def setup(self) -> None:
        print("Loading real historical bars from connected client...")
        for symbol in SYMBOLS:
            bars = self.engine.client.get_bars(
                symbol=symbol,
                timeframe=TIMEFRAME,
                count=BAR_COUNT,
                start_pos=0,
            )
            if bars is None or bars.empty:
                print(f"  {symbol}: no data available, skipped")
                continue
            self.market_data[symbol] = bars.copy()
            close_col = "close" if "close" in bars.columns else "Close"
            latest_close = float(bars[close_col].iloc[-1])
            if prepare_symbol(self.engine, symbol, latest_close) is None:
                print(f"  {symbol}: symbol info unavailable, skipped")
                continue
            print(f"  {symbol}: loaded {len(bars)} bars, latest_close={latest_close:.5f}")

        print("Opening small simulator positions...")
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
            self.trade.SetTypeFillingBySymbol(request["symbol"])
            result = self.trade.PositionOpen(
                symbol=request["symbol"],
                order_type=request["side"],
                volume=volume,
                price=price,
                sl=sl,
                tp=0.0,
                comment="Phase 3 governance example",
            )
            print(
                f"  {request['symbol']} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )
        self.engine.monitor_account(verbose=False)
        self.latest_ts = max(df.index[-1] for df in self.market_data.values() if not df.empty)

    def build_state(self, limits: RiskLimits, peak_equity: float = 10250.0):
        return PortfolioStateEngine().build_state_from_engine(
            engine=self.engine,
            symbols=[symbol for symbol in SYMBOLS if symbol in self.market_data],
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=pd.Timestamp(self.latest_ts).isoformat(),
            limits=limits,
            symbol_to_cluster=SYMBOL_TO_CLUSTER,
            metadata={
                "source": "phase3_governance_example",
                "backend": "sim",
                "peak_equity": peak_equity,
                "example_generated_at": datetime.now(UTC).isoformat(),
            },
        )

    def build_governance_engine(self, state):
        return GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=StateRiskAdapter(state),
                timeframe=TIMEFRAME,
                start_pos=0,
                end_pos=BAR_COUNT,
            ),
            limits=state.limits or BASE_LIMITS,
        )

    def close(self):
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_define_limit_models_and_policy_contracts(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Define Limit Models and Policy Contracts")
    state = ctx.build_state(BASE_LIMITS)
    print(f"as_of={state.as_of}")
    print(f"limits_type={type(state.limits).__name__}")
    print(f"var_cap_frac={state.limits.var_cap_frac:.2%}")
    print(f"es_cap_frac={state.limits.es_cap_frac:.2%}")
    print(f"cluster_var_caps={state.limits.cluster_var_caps}")
    print(f"warning_utilization_frac={state.limits.warning_utilization_frac:.2%}")


def example_02_pre_trade_checks(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Pre-Trade Checks")
    state = ctx.build_state(BASE_LIMITS)
    governance = ctx.build_governance_engine(state)
    report = governance.evaluate_add_position(
        current_positions=state.position_map,
        candidate_symbol="EURUSD",
        candidate_lots=0.02,
        symbol_to_cluster=state.symbol_to_cluster,
    )
    print(f"decision={report.decision}")
    print(f"reason={report.reason}")
    print(f"delta_var={report.delta_var:,.2f}")
    print(f"delta_es={report.delta_es:,.2f}")


def example_03_post_trade_checks(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Post-Trade Checks")
    state = ctx.build_state(BASE_LIMITS)
    governance = ctx.build_governance_engine(state)
    report = governance.evaluate_portfolio_state(state)
    print(f"decision={report.decision}")
    print(f"reason={report.reason}")
    print(f"current_var={report.current_var:,.2f}")
    print(f"current_es={report.current_es:,.2f}")


def example_04_hard_limits(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Hard Limits")
    state = ctx.build_state(
        replace(
            BASE_LIMITS,
            var_cap_frac=0.05,
            es_cap_frac=0.08,
            delta_var_cap_frac=0.01,
            delta_es_cap_frac=0.015,
            max_single_rc_frac=0.45,
            cluster_var_caps={"FOREX": 0.04},
            cluster_es_caps={"FOREX": 0.06},
        )
    )
    governance = ctx.build_governance_engine(state)
    report = governance.evaluate_add_position(
        current_positions=state.position_map,
        candidate_symbol="EURUSD",
        candidate_lots=0.60,
        symbol_to_cluster=state.symbol_to_cluster,
    )
    print(f"decision={report.decision}")
    print(f"reason={report.reason}")
    print_event_rows(report.breaches)


def example_05_soft_limits(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Soft Limits")
    state = ctx.build_state(
        replace(
            BASE_LIMITS,
            warning_utilization_frac=0.50,
            var_cap_frac=0.25,
            es_cap_frac=0.35,
            max_single_rc_frac=1.00,
            cluster_var_caps={"FOREX": 0.30},
            cluster_es_caps={"FOREX": 0.40},
        )
    )
    governance = ctx.build_governance_engine(state)
    report = governance.evaluate_portfolio_state(state)
    print(f"decision={report.decision}")
    print(f"status={report.governance_state.status if report.governance_state else 'unknown'}")
    print_event_rows(report.warnings)


def example_06_override_recording_model(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Override Recording Model")
    state = ctx.build_state(BASE_LIMITS)
    governance = ctx.build_governance_engine(state)
    _, overrides = governance.policy_engine.effective_policy(
        state.limits,
        regime=RegimeState(name="STRESS"),
    )
    if not overrides:
        print("  no overrides")
        return
    for override in overrides:
        print(
            f"  {override.field_name}: {override.previous_value} -> {override.new_value} "
            f"source={override.source}"
        )


def example_07_circuit_breaker_rules(ctx: ExampleContext) -> None:
    print_example_header("Example 07: Circuit-Breaker Rules")
    state = ctx.build_state(
        replace(
            BASE_LIMITS,
            drawdown_halt_frac=0.01,
            warning_utilization_frac=0.95,
        ),
        peak_equity=12000.0,
    )
    governance = ctx.build_governance_engine(state)
    report = governance.evaluate_portfolio_state(state)
    print(f"decision={report.decision}")
    print(f"reason={report.reason}")
    print_event_rows(report.breaches)


def example_08_risk_budget_utilization_tracking(ctx: ExampleContext) -> None:
    print_example_header("Example 08: Risk-Budget Utilization Tracking")
    state = ctx.build_state(BASE_LIMITS)
    governance = ctx.build_governance_engine(state)
    report = governance.evaluate_portfolio_state(state)
    print_utilizations(report)


def example_09_policy_events_and_breach_records(ctx: ExampleContext) -> None:
    print_example_header("Example 09: Policy Events and Breach Records")
    state = ctx.build_state(
        replace(
            BASE_LIMITS,
            var_cap_frac=0.05,
            es_cap_frac=0.08,
            max_single_rc_frac=0.45,
            cluster_var_caps={"FOREX": 0.04},
            cluster_es_caps={"FOREX": 0.06},
        )
    )
    snapshot = RiskSnapshotEngine().build_snapshot(state)
    print(f"snapshot_compliance_state={snapshot.summary.get('compliance_state')}")
    print(f"policy_event_count={len(snapshot.policy_events)}")
    print_event_rows(snapshot.policy_events)


def main() -> None:
    print_example_header("PHASE 3 GOVERNANCE AND LIMITS ENGINE")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_define_limit_models_and_policy_contracts(ctx)
        example_02_pre_trade_checks(ctx)
        example_03_post_trade_checks(ctx)
        example_04_hard_limits(ctx)
        example_05_soft_limits(ctx)
        example_06_override_recording_model(ctx)
        example_07_circuit_breaker_rules(ctx)
        example_08_risk_budget_utilization_tracking(ctx)
        example_09_policy_events_and_breach_records(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
