"""
Example 11: Governance and Limits Engine

Type: live-broker dependent manual demo

Scenario-based walkthrough using the actual HaruQuant governance stack:
1. first trade from an empty portfolio
2. add second position within limits
3. VaR cap violation
4. delta VaR cap violation
5. ES cap violation
6. risk contribution cap violation
7. cluster cap violation
8. regime tightening
9. position reduction

Run:
    python backend/scripts/examples/risk/03_governance_limits_engine.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.services.risk_engine import GovernanceEngine, PortfolioRiskEngine, PortfolioStateEngine, RiskLimits
from backend.services.risk_engine.regimes import RegimeState
from backend.services.simulation.engine import Engine`nfrom backend.services.execution import core


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
    max_currency_exposure_frac=1.00,
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


def print_report(report) -> None:
    print(f"  decision={report.decision}")
    print(f"  reason={report.reason}")
    print(f"  current_var={report.current_var:,.2f}")
    print(f"  new_var={report.new_var:,.2f}")
    print(f"  delta_var={report.delta_var:,.2f}")
    print(f"  current_es={report.current_es:,.2f}")
    print(f"  new_es={report.new_es:,.2f}")
    print(f"  delta_es={report.delta_es:,.2f}")
    print(
        f"  current_margin={float(report.current_margin_used or 0.0):,.2f} "
        f"new_margin={float(report.new_margin_used or 0.0):,.2f}"
    )
    if report.overrides:
        for override in report.overrides:
            print(
                f"  override {override.field_name}: {override.previous_value} -> "
                f"{override.new_value} source={override.source}"
            )
    if report.warnings:
        print("  warnings:")
        print_event_rows(report.warnings)
    if report.breaches:
        print("  breaches:")
        print_event_rows(report.breaches)


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
        spec = self.state.symbols.get(symbol)
        market = self.state.markets.get(symbol)
        if spec is None or market is None or market.bars.empty:
            return None
        close_col = "close" if "close" in market.bars.columns else "Close"
        if close_col not in market.bars.columns:
            return None
        price = float(market.bars[close_col].iloc[-1] or 0.0)
        leverage = float(self.state.account.metadata.get("leverage", 0.0) or 0.0)
        contract_size = float(spec.contract_size or 0.0)
        if price <= 0.0 or leverage <= 0.0 or contract_size <= 0.0:
            return None
        return abs(float(lots)) * contract_size * price / leverage

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
        self.market_data = {}
        self.latest_ts = None
        self.state_engine = PortfolioStateEngine()

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
        self.latest_ts = max(df.index[-1] for df in self.market_data.values() if not df.empty)

    def build_state(
        self,
        positions: dict[str, float],
        limits: RiskLimits,
        *,
        peak_equity: float = 10250.0,
    ):
        return self.state_engine.build_state_from_engine(
            engine=self.engine,
            symbols=[symbol for symbol in SYMBOLS if symbol in self.market_data],
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=pd.Timestamp(self.latest_ts).isoformat(),
            positions=positions,
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

    def evaluate_transition(
        self,
        current_positions: dict[str, float],
        new_positions: dict[str, float],
        limits: RiskLimits,
        *,
        regime: RegimeState | None = None,
        peak_equity: float = 10250.0,
    ):
        current_state = self.build_state(current_positions, limits, peak_equity=peak_equity)
        new_state = self.build_state(new_positions, limits, peak_equity=peak_equity)
        governance = self.build_governance_engine(current_state)
        return governance.evaluate_transition_from_states(
            current_state,
            new_state,
            regime=regime,
        )

    def evaluate_add(
        self,
        current_positions: dict[str, float],
        candidate_symbol: str,
        candidate_lots: float,
        limits: RiskLimits,
        *,
        regime: RegimeState | None = None,
        peak_equity: float = 10250.0,
    ):
        state = self.build_state(current_positions, limits, peak_equity=peak_equity)
        governance = self.build_governance_engine(state)
        return governance.evaluate_add_position(
            current_positions=state.position_map,
            candidate_symbol=candidate_symbol,
            candidate_lots=candidate_lots,
            symbol_to_cluster=state.symbol_to_cluster,
            regime=regime,
        )

    def close(self):
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_first_trade_empty_portfolio(ctx: ExampleContext) -> None:
    print_example_header("Example 01: First Trade (Empty Portfolio)")
    report = ctx.evaluate_transition({}, {"EURUSD": 0.10}, BASE_LIMITS)
    print_report(report)


def example_02_add_second_position_within_limits(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Add Second Position (Within Limits)")
    report = ctx.evaluate_transition(
        {"EURUSD": 0.10},
        {"EURUSD": 0.10, "GBPUSD": 0.08},
        BASE_LIMITS,
    )
    print_report(report)


def example_03_var_cap_violation(ctx: ExampleContext) -> None:
    print_example_header("Example 03: VaR Cap Violation")
    limits = RiskLimits(**{**BASE_LIMITS.__dict__, "var_cap_frac": 0.02, "es_cap_frac": 0.50, "delta_var_cap_frac": 0.50})
    report = ctx.evaluate_transition(
        {"EURUSD": 0.10, "GBPUSD": 0.08},
        {"EURUSD": 0.35, "GBPUSD": 0.25, "USDJPY": -0.20},
        limits,
    )
    print_report(report)


def example_04_delta_var_cap_violation(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Delta VaR Cap Violation")
    limits = RiskLimits(**{**BASE_LIMITS.__dict__, "var_cap_frac": 0.50, "es_cap_frac": 0.50, "delta_var_cap_frac": 0.005})
    report = ctx.evaluate_transition(
        {"EURUSD": 0.10},
        {"EURUSD": 0.25, "GBPUSD": 0.10},
        limits,
    )
    print_report(report)


def example_05_es_cap_violation(ctx: ExampleContext) -> None:
    print_example_header("Example 05: ES Cap Violation")
    limits = RiskLimits(**{**BASE_LIMITS.__dict__, "var_cap_frac": 0.50, "es_cap_frac": 0.03, "delta_es_cap_frac": 0.50})
    report = ctx.evaluate_transition(
        {"EURUSD": 0.10, "GBPUSD": 0.08},
        {"EURUSD": 0.30, "GBPUSD": 0.20, "USDJPY": -0.20},
        limits,
    )
    print_report(report)


def example_06_risk_contribution_cap_violation(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Risk Contribution Cap Violation")
    limits = RiskLimits(
        **{
            **BASE_LIMITS.__dict__,
            "var_cap_frac": 0.50,
            "es_cap_frac": 0.50,
            "delta_var_cap_frac": 0.50,
            "delta_es_cap_frac": 0.50,
            "max_single_rc_frac": 0.05,
        }
    )
    report = ctx.evaluate_transition(
        {"EURUSD": 0.10, "GBPUSD": 0.10},
        {"EURUSD": 0.10, "GBPUSD": 0.10, "USDJPY": -0.40},
        limits,
    )
    print_report(report)


def example_07_cluster_cap_violation(ctx: ExampleContext) -> None:
    print_example_header("Example 07: Cluster Cap Violation")
    limits = RiskLimits(
        **{
            **BASE_LIMITS.__dict__,
            "var_cap_frac": 0.50,
            "es_cap_frac": 0.50,
            "delta_var_cap_frac": 0.50,
            "delta_es_cap_frac": 0.50,
            "cluster_var_caps": {"FOREX": 0.03},
            "cluster_es_caps": {"FOREX": 0.05},
        }
    )
    report = ctx.evaluate_transition(
        {"EURUSD": 0.10},
        {"EURUSD": 0.20, "GBPUSD": 0.15, "USDJPY": -0.12},
        limits,
    )
    print_report(report)


def example_08_regime_tightening(ctx: ExampleContext) -> None:
    print_example_header("Example 08: Regime Tightening")
    current_positions = {"EURUSD": 0.10}
    new_positions = {"EURUSD": 0.18, "GBPUSD": 0.10}
    normal_report = ctx.evaluate_transition(current_positions, new_positions, BASE_LIMITS)
    stress_report = ctx.evaluate_transition(
        current_positions,
        new_positions,
        BASE_LIMITS,
        regime=RegimeState(name="STRESS"),
    )
    print("Normal regime:")
    print_report(normal_report)
    print("Stress regime:")
    print_report(stress_report)


def example_09_position_reduction(ctx: ExampleContext) -> None:
    print_example_header("Example 09: Position Reduction")
    report = ctx.evaluate_add(
        {"EURUSD": 0.10, "GBPUSD": 0.08},
        candidate_symbol="EURUSD",
        candidate_lots=-0.10,
        limits=BASE_LIMITS,
    )
    print_report(report)


def main() -> None:
    print_example_header("PHASE 3 GOVERNANCE AND LIMITS ENGINE")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_first_trade_empty_portfolio(ctx)
        example_02_add_second_position_within_limits(ctx)
        example_03_var_cap_violation(ctx)
        example_04_delta_var_cap_violation(ctx)
        example_05_es_cap_violation(ctx)
        example_06_risk_contribution_cap_violation(ctx)
        example_07_cluster_cap_violation(ctx)
        example_08_regime_tightening(ctx)
        example_09_position_reduction(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
