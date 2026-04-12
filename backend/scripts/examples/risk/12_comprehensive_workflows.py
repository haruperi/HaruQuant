"""
Comprehensive live MT5 risk-management workflows.

Type: live-broker dependent manual demo

This file consolidates the older example entry points into one place:
- simple_single_strategy.py
- multi_strategy_portfolio.py
- integrate_existing_system.py
- full_scenarios.py
- demo.py

Run:
    python backend/scripts/examples/risk/comprehensive_workflows.py
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.mcp.mt5_mcp import MT5Client, get_mt5_api
from backend.services.risk_engine import (
    AllocationPlanner,
    GovernanceEngine,
    PortfolioRiskEngine,
    PositionSizer,
    RiskLimits,
    RiskRegimeDetector,
)
from backend.services.risk_engine.limits import CorrelationPreference
from backend.db.sqlite.users import UserManager
from backend.services.simulation.engine import Engine

mt5 = get_mt5_api()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _print_subheader(title: str) -> None:
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def _get_mt5_credentials() -> Optional[dict]:
    creds = UserManager().get_mt5_credentials()
    if not creds:
        print("No default broker credentials found.")
        return None
    return creds


def _ensure_mt5_helpers(mt5_client: MT5Client) -> None:
    if not hasattr(mt5_client, "get_account_equity"):
        def _get_equity():
            engine_instance = Engine(backend="mt5")
            equity = float(engine_instance.api.account_info().equity)
            engine_instance.client.shutdown()
            return equity

        mt5_client.get_account_equity = _get_equity  # type: ignore[attr-defined]

    if not hasattr(mt5_client, "get_symbol_info"):
        def _get_symbol_info(sym):
            engine_instance = Engine(backend="mt5")
            info = engine_instance.api.symbol_info(sym)
            engine_instance.client.shutdown()
            return info

        mt5_client.get_symbol_info = _get_symbol_info  # type: ignore[attr-defined]

    if not hasattr(mt5_client, "get_positions"):
        mt5_client.get_positions = mt5.positions_get  # type: ignore[attr-defined]


def _connect_mt5() -> Optional[MT5Client]:
    creds = _get_mt5_credentials()
    if not creds:
        return None

    mt5_client = MT5Client()
    if not mt5_client.connect(
        path=creds["path"],
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
    ):
        print("Failed to initialize MT5")
        return None

    _ensure_mt5_helpers(mt5_client)
    return mt5_client


def _get_current_positions(mt5_client: MT5Client, symbols: Optional[List[str]] = None) -> Dict[str, float]:
    positions: Dict[str, float] = {}
    all_positions = mt5_client.get_positions()
    if not all_positions:
        return positions

    allowed = set(symbols or [])
    for pos in all_positions:
        symbol = pos.symbol
        if allowed and symbol not in allowed:
            continue
        positions[symbol] = positions.get(symbol, 0.0) + float(pos.volume)
    return positions


def _build_governor(
    mt5_client: MT5Client,
    *,
    timeframe: str,
    end_pos: int,
    limits: RiskLimits,
) -> GovernanceEngine:
    return GovernanceEngine(
        risk_engine=PortfolioRiskEngine(
            mt5_client=mt5_client,
            timeframe=timeframe,
            start_pos=0,
            end_pos=end_pos,
        ),
        limits=limits,
    )


def _detect_regime(
    mt5_client: MT5Client,
    detector: RiskRegimeDetector,
    symbols: List[str],
    equity: float,
) -> Optional[object]:
    returns_data = {}
    for symbol in symbols:
        daily_data = mt5_client.get_bars(symbol=symbol, timeframe="D1", count=120, start_pos=0)
        if daily_data is not None and not daily_data.empty and len(daily_data) >= 60:
            returns_data[symbol] = daily_data["close"].pct_change()

    if not returns_data:
        return None

    returns_df = pd.DataFrame(returns_data).dropna(how="all")
    if returns_df.empty:
        return None

    equity_curve = pd.Series([equity] * len(returns_df), index=returns_df.index)
    return detector.detect(returns_df, equity_curve)


@dataclass
class SimpleStrategy:
    name: str
    symbol: str
    timeframe: str
    fast: int
    slow: int
    filter: int

    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        if len(data) < max(self.fast, self.slow, self.filter):
            return None

        frame = data.copy()
        frame["ema_fast"] = frame["close"].ewm(span=self.fast, adjust=False).mean()
        frame["ema_slow"] = frame["close"].ewm(span=self.slow, adjust=False).mean()
        frame["ema_filter"] = frame["close"].ewm(span=self.filter, adjust=False).mean()

        entry_price = float(frame["close"].iloc[-1])
        if (
            frame["ema_fast"].iloc[-2] <= frame["ema_slow"].iloc[-2]
            and frame["ema_fast"].iloc[-1] > frame["ema_slow"].iloc[-1]
            and frame["close"].iloc[-1] > frame["ema_filter"].iloc[-1]
        ):
            return {
                "type": "buy",
                "symbol": self.symbol,
                "entry_price": entry_price,
                "stop_loss": None,
                "reason": f"Fast({self.fast}) crossed above Slow({self.slow}), above Filter({self.filter})",
            }

        if (
            frame["ema_fast"].iloc[-2] >= frame["ema_slow"].iloc[-2]
            and frame["ema_fast"].iloc[-1] < frame["ema_slow"].iloc[-1]
            and frame["close"].iloc[-1] < frame["ema_filter"].iloc[-1]
        ):
            return {
                "type": "sell",
                "symbol": self.symbol,
                "entry_price": entry_price,
                "stop_loss": None,
                "reason": f"Fast({self.fast}) crossed below Slow({self.slow}), below Filter({self.filter})",
            }

        return None


class RiskManagedTradingWrapper:
    """Small wrapper showing how to add risk checks around an existing system."""

    def __init__(self, mt5_client: MT5Client, config: Optional[Dict] = None):
        self.mt5_client = mt5_client
        self.config = config or {}
        self.equity_history: List[float] = []
        self.current_regime = None
        self._setup_risk_components()

    def _setup_risk_components(self) -> None:
        risk_config = self.config.get("risk_management", {})
        limits_config = risk_config.get("limits", {})
        sizing_config = self.config.get("position_sizing", {})

        self.limits = RiskLimits(
            var_cap_frac=limits_config.get("var_cap_frac", 0.10),
            es_cap_frac=limits_config.get("es_cap_frac", 0.15),
            delta_var_cap_frac=limits_config.get("delta_var_cap_frac", 0.02),
            max_single_rc_frac=limits_config.get("max_single_rc_frac", 0.35),
        )
        self.position_sizer = PositionSizer(
            method=sizing_config.get("method", "fixed_risk"),
            config=sizing_config.get("config", {"risk_percent": 1.0}),
            mt5_client=self.mt5_client,
        )
        gov_cfg = risk_config.get("governor_config", {})
        self.governor = _build_governor(
            self.mt5_client,
            timeframe=gov_cfg.get("timeframe", "H1"),
            end_pos=gov_cfg.get("end_pos", 500),
            limits=self.limits,
        )
        regime_cfg = risk_config.get("regime_detector", {})
        self.regime_detector = RiskRegimeDetector(
            vol_spike_mult=regime_cfg.get("vol_spike_mult", 1.8),
            corr_spike_level=regime_cfg.get("corr_spike_level", 0.55),
            dd_trigger_frac=regime_cfg.get("dd_trigger_frac", 0.05),
        )
        self.symbol_clusters = self.config.get("symbol_clusters", {})
        self.risk_budgets = self.config.get("risk_budgets", {})
        self.allocator = AllocationPlanner(self.governor) if risk_config.get("enable_allocation", False) else None

    def _update_regime(self) -> None:
        symbols = list(self.symbol_clusters.keys()) or ["EURUSD"]
        equity = self.mt5_client.get_account_equity()
        regime = _detect_regime(self.mt5_client, self.regime_detector, symbols, equity)
        if regime is not None:
            self.current_regime = regime

    def approve_trade(self, signal: Dict, current_positions: Optional[Dict[str, float]] = None) -> bool:
        symbol = signal["symbol"]
        if "volume" not in signal:
            account_balance = self.mt5_client.get_account_equity()
            symbol_info = self.mt5_client.get_symbol_info(symbol)
            signal["volume"] = self.position_sizer.calculate_size(
                account_balance=account_balance,
                entry_price=signal["entry_price"],
                stop_loss=signal.get("stop_loss"),
                symbol_info=symbol_info,
                symbol=symbol,
                signal_type=signal.get("type"),
            )

        if current_positions is None:
            current_positions = _get_current_positions(self.mt5_client)

        self._update_regime()
        report = self.governor.evaluate_add_position(
            current_positions=current_positions,
            candidate_symbol=symbol,
            candidate_lots=signal["volume"],
            symbol_to_cluster=self.symbol_clusters,
            regime=self.current_regime,
        )
        print(f"  {symbol}: {report.decision} | {report.reason}")
        return report.decision == "ACCEPT"

    def calculate_position_sizes(self, signals: List[Dict], use_allocation: bool = True) -> Dict[str, float]:
        account_balance = self.mt5_client.get_account_equity()
        base_lots: Dict[str, float] = {}
        for signal in signals:
            symbol = signal["symbol"]
            symbol_info = self.mt5_client.get_symbol_info(symbol)
            base_lots[symbol] = self.position_sizer.calculate_size(
                account_balance=account_balance,
                entry_price=signal["entry_price"],
                stop_loss=signal.get("stop_loss"),
                symbol_info=symbol_info,
                symbol=symbol,
                signal_type=signal.get("type"),
            )

        if not use_allocation or self.allocator is None or len(signals) <= 1:
            return base_lots

        symbols = list(base_lots.keys())
        budgets = {s: self.risk_budgets.get(s, 1.0 / len(symbols)) for s in symbols}
        return self.allocator.compute_target_lots(
            symbols=symbols,
            base_lots=base_lots,
            budgets=budgets,
            regime=self.current_regime,
        )

    def propose_rebalancing(self, current_positions: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        positions = current_positions or _get_current_positions(self.mt5_client)
        if not positions:
            return {}
        budgets = {s: self.risk_budgets.get(s, 1.0 / len(positions)) for s in positions}
        return self.governor.risk_engine.propose_rc_rebalance(
            positions=positions,
            target_rc_budget=budgets,
            limits=self.governor.effective_limits(self.current_regime),
        )


def example_01_single_strategy(mt5_client: MT5Client) -> None:
    _print_header("EXAMPLE 01: SINGLE-STRATEGY WORKFLOW")
    equity = mt5_client.get_account_equity()
    print(f"Account Equity: ${equity:,.2f}")

    limits = RiskLimits(
        var_cap_frac=0.08,
        es_cap_frac=0.12,
        delta_var_cap_frac=0.015,
        max_single_rc_frac=0.20,
    )
    sizer = PositionSizer(
        method="fixed_risk",
        config={
            "risk_percent": 1.0,
            "use_dynamic_stop_loss": True,
            "atr_period": 10,
            "atr_target_devider": 3.0,
            "atr_timeframe": "H4",
        },
        mt5_client=mt5_client,
    )
    governor = _build_governor(mt5_client, timeframe="H1", end_pos=500, limits=limits)
    detector = RiskRegimeDetector(vol_spike_mult=1.8, corr_spike_level=0.55, dd_trigger_frac=0.05, lookback=60)
    strategy = SimpleStrategy("EURUSD_Trend", "EURUSD", "M5", 20, 50, 200)

    data = mt5_client.get_bars(symbol=strategy.symbol, timeframe=strategy.timeframe, count=250, start_pos=0)
    if data is None or data.empty:
        print("No market data available.")
        return

    signal = strategy.generate_signal(data)
    if not signal:
        print("No signal generated. Example stops here.")
        return

    _print_subheader("Signal")
    print(f"{signal['symbol']} {signal['type'].upper()} @ {signal['entry_price']:.5f}")
    print(signal["reason"])

    symbol_info = mt5_client.get_symbol_info(strategy.symbol)
    volume = sizer.calculate_size(
        account_balance=equity,
        entry_price=signal["entry_price"],
        stop_loss=signal["stop_loss"],
        symbol_info=symbol_info,
        symbol=strategy.symbol,
        signal_type=signal["type"],
    )
    print(f"Calculated volume: {volume:.3f} lots")

    regime = _detect_regime(mt5_client, detector, [strategy.symbol], equity)
    if regime is not None:
        print(f"Detected regime: {regime.name}")

    current_positions = _get_current_positions(mt5_client, [strategy.symbol])
    report = governor.evaluate_add_position(
        current_positions=current_positions,
        candidate_symbol=strategy.symbol,
        candidate_lots=volume,
        regime=regime,
    )
    _print_subheader("Governance Review")
    print(f"Decision: {report.decision}")
    print(f"Reason: {report.reason}")
    print(f"Current VaR: ${report.current_var:,.2f}")
    print(f"New VaR: ${report.new_var:,.2f}")
    print(f"Delta VaR: ${report.delta_var:,.2f}")
    print(f"New ES: ${report.new_es:,.2f}")


def example_02_multi_strategy_portfolio(mt5_client: MT5Client) -> None:
    _print_header("EXAMPLE 02: MULTI-STRATEGY PORTFOLIO WORKFLOW")
    equity = mt5_client.get_account_equity()
    limits = RiskLimits(
        var_cap_frac=0.10,
        es_cap_frac=0.15,
        delta_var_cap_frac=0.02,
        max_single_rc_frac=0.35,
        cluster_var_caps={"FOREX": 0.06, "METALS": 0.05},
    )
    sizer = PositionSizer(
        method="fixed_risk",
        config={
            "risk_percent": 1.0,
            "use_dynamic_stop_loss": True,
            "atr_period": 10,
            "atr_target_devider": 3.0,
            "atr_timeframe": "H4",
        },
        mt5_client=mt5_client,
    )
    governor = _build_governor(mt5_client, timeframe="H1", end_pos=500, limits=limits)
    detector = RiskRegimeDetector(vol_spike_mult=1.8, corr_spike_level=0.55, dd_trigger_frac=0.05, lookback=60)
    allocator = AllocationPlanner(
        governor,
        CorrelationPreference(target_corr=0.50, penalty_strength=2.0, min_budget_frac=0.30),
    )

    strategies = [
        SimpleStrategy("EURUSD_Trend", "EURUSD", "M15", 20, 50, 200),
        SimpleStrategy("GBPUSD_Trend", "GBPUSD", "M15", 20, 50, 200),
        SimpleStrategy("XAUUSD_Breakout", "XAUUSD", "M15", 10, 30, 100),
    ]
    risk_budgets = {"EURUSD": 0.30, "GBPUSD": 0.30, "XAUUSD": 0.40}
    symbol_clusters = {"EURUSD": "FOREX", "GBPUSD": "FOREX", "XAUUSD": "METALS"}

    all_data: Dict[str, pd.DataFrame] = {}
    signals: List[Dict] = []
    for strategy in strategies:
        data = mt5_client.get_bars(symbol=strategy.symbol, timeframe=strategy.timeframe, count=250, start_pos=0)
        if data is None or data.empty:
            continue
        all_data[strategy.symbol] = data
        signal = strategy.generate_signal(data)
        if signal:
            signal["strategy_name"] = strategy.name
            signals.append(signal)

    if not signals:
        print("No signals generated. Example stops here.")
        return

    _print_subheader("Signals")
    for signal in signals:
        print(f"{signal['strategy_name']}: {signal['symbol']} {signal['type'].upper()}")

    base_lots: Dict[str, float] = {}
    for signal in signals:
        symbol_info = mt5_client.get_symbol_info(signal["symbol"])
        base_lots[signal["symbol"]] = sizer.calculate_size(
            account_balance=equity,
            entry_price=signal["entry_price"],
            stop_loss=signal["stop_loss"],
            symbol_info=symbol_info,
            symbol=signal["symbol"],
            signal_type=signal["type"],
        )

    regime = _detect_regime(mt5_client, detector, list(all_data.keys()), equity)
    if regime is not None:
        print(f"Detected regime: {regime.name}")

    target_lots = allocator.compute_target_lots(
        symbols=list(base_lots.keys()),
        base_lots=base_lots,
        budgets={s: risk_budgets.get(s, 1.0 / len(base_lots)) for s in base_lots},
        regime=regime,
    )

    _print_subheader("Risk-Adjusted Position Sizes")
    for symbol in base_lots:
        print(f"{symbol}: {base_lots[symbol]:.3f} -> {target_lots[symbol]:.3f} lots")

    current_positions = _get_current_positions(mt5_client, list(base_lots.keys()))
    approved = 0
    rejected = 0
    _print_subheader("Governance Decisions")
    for signal in signals:
        symbol = signal["symbol"]
        volume = target_lots[symbol]
        report = governor.evaluate_add_position(
            current_positions=current_positions,
            candidate_symbol=symbol,
            candidate_lots=volume,
            symbol_to_cluster=symbol_clusters,
            regime=regime,
        )
        print(f"{symbol}: {report.decision} | {report.reason}")
        if report.decision == "ACCEPT":
            approved += 1
            current_positions[symbol] = current_positions.get(symbol, 0.0) + volume
        else:
            rejected += 1
    print(f"Approved: {approved} | Rejected: {rejected}")


def example_03_existing_system_integration(mt5_client: MT5Client) -> None:
    _print_header("EXAMPLE 03: EXISTING SYSTEM INTEGRATION WRAPPER")
    config = {
        "risk_management": {
            "limits": {"var_cap_frac": 0.08, "es_cap_frac": 0.12, "delta_var_cap_frac": 0.02},
            "governor_config": {"timeframe": "H1", "end_pos": 500},
            "enable_allocation": True,
        },
        "position_sizing": {"method": "fixed_risk", "config": {"risk_percent": 1.0}},
        "symbol_clusters": {"EURUSD": "FOREX", "GBPUSD": "FOREX", "XAUUSD": "METALS"},
        "risk_budgets": {"EURUSD": 0.35, "GBPUSD": 0.35, "XAUUSD": 0.30},
    }
    wrapper = RiskManagedTradingWrapper(mt5_client, config)

    signals = [
        {"symbol": "EURUSD", "type": "buy", "entry_price": 1.1000, "stop_loss": 1.0950, "strategy": "EMA_Cross"},
        {"symbol": "GBPUSD", "type": "buy", "entry_price": 1.2500, "stop_loss": 1.2450, "strategy": "Breakout"},
    ]

    _print_subheader("Individual Approval")
    current_positions = _get_current_positions(mt5_client)
    for signal in signals:
        approved = wrapper.approve_trade(signal.copy(), current_positions.copy())
        print(f"{signal['symbol']}: {'EXECUTE' if approved else 'SKIP'}")

    _print_subheader("Batch Sizing With Allocation")
    target_sizes = wrapper.calculate_position_sizes([s.copy() for s in signals], use_allocation=True)
    for symbol, lots in target_sizes.items():
        print(f"{symbol}: {lots:.3f} lots")

    _print_subheader("Rebalance Proposal")
    deltas = wrapper.propose_rebalancing(current_positions)
    if not deltas:
        print("No rebalance needed.")
    else:
        for symbol, delta in deltas.items():
            print(f"{symbol}: {delta:+.3f} lots")


def example_04_scenario_showcase(mt5_client: MT5Client) -> None:
    _print_header("EXAMPLE 04: LIVE SCENARIO SHOWCASE")
    equity = mt5_client.get_account_equity()

    _print_subheader("1) Conservative New Trader Setup")
    limits = RiskLimits(var_cap_frac=0.05, es_cap_frac=0.08, delta_var_cap_frac=0.01, max_single_rc_frac=0.30)
    sizer = PositionSizer(method="fixed_risk", config={"risk_percent": 0.5, "use_dynamic_stop_loss": False})
    governor = _build_governor(mt5_client, timeframe="H1", end_pos=200, limits=limits)
    size1 = sizer.calculate_size(account_balance=equity, entry_price=1.1000, stop_loss=1.0950, symbol_info=None)
    report1 = governor.evaluate_add_position({}, "EURUSD", size1)
    print(f"EURUSD size: {size1:.4f} lots | {report1.decision} | New VaR: ${report1.new_var:,.2f}")

    _print_subheader("2) Growing Account Milestone Sizing")
    milestone_sizer = PositionSizer(
        method="milestone",
        config={
            "initial_balance": 10000.0,
            "base_lot_size": 0.1,
            "milestone_amount": 3000.0,
            "lot_increment": 0.2,
        },
    )
    for balance in [10000, 13000, 16000, 19000, 22000]:
        size = milestone_sizer.calculate_size(account_balance=balance, entry_price=1.1000, symbol_info=None)
        print(f"${balance:>8,.0f} -> {size:.4f} lots")

    _print_subheader("3) Regime Detection")
    detector = RiskRegimeDetector(vol_spike_mult=1.8, corr_spike_level=0.55, dd_trigger_frac=0.05, lookback=60)
    regime = _detect_regime(mt5_client, detector, ["EURUSD", "GBPUSD", "XAUUSD"], equity)
    print(f"Detected regime: {regime.name if regime else 'UNKNOWN'}")

    _print_subheader("4) Rebalancing Workflow")
    current_positions = {"EURUSD": 0.8, "GBPUSD": 0.2, "USDJPY": 0.2, "XAUUSD": 0.1}
    target_budget = {symbol: 1 / len(current_positions) for symbol in current_positions}
    rebalance = governor.risk_engine.propose_rc_rebalance(
        positions=current_positions,
        target_rc_budget=target_budget,
        limits=governor.effective_limits(regime),
        max_iters=10,
        step_frac=0.10,
    )
    if not rebalance:
        print("Portfolio already balanced.")
    else:
        for symbol, delta in rebalance.items():
            print(f"{symbol}: {delta:+.4f} lots")


def example_05_live_workflow_and_rebalance(mt5_client: MT5Client) -> None:
    _print_header("EXAMPLE 05: COMPACT LIVE WORKFLOW")
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD"]
    base_lots = {"EURUSD": 0.30, "GBPUSD": 0.25, "USDJPY": 0.35, "AUDUSD": 0.28, "NZDUSD": 0.22}
    symbol_to_cluster = {s: "FX:USD" for s in symbols}

    limits = RiskLimits(
        var_cap_frac=0.10,
        es_cap_frac=0.15,
        delta_var_cap_frac=0.02,
        delta_es_cap_frac=0.03,
        max_single_rc_frac=0.20,
        min_pair_corr=0.20,
        stressed_corr_floor=0.60,
        use_stressed_corr=False,
        cluster_var_caps={"FX:USD": 0.06},
        cluster_es_caps={"FX:USD": 0.09},
    )
    governor = _build_governor(mt5_client, timeframe="D1", end_pos=350, limits=limits)
    allocator = AllocationPlanner(
        governor,
        corr_pref=CorrelationPreference(target_corr=0.50, penalty_strength=2.0, min_budget_frac=0.30),
    )
    detector = RiskRegimeDetector()
    regime = _detect_regime(mt5_client, detector, symbols, mt5_client.get_account_equity())

    target_lots = allocator.compute_target_lots(symbols, base_lots, budgets=None, regime=regime)
    _print_subheader("Target Lots")
    for symbol, lots in target_lots.items():
        print(f"{symbol}: {lots:.3f} lots")

    positions: Dict[str, float] = {}
    _print_subheader("Hard-Gated Entry Flow")
    for symbol in symbols:
        candidate = target_lots[symbol]
        report = governor.evaluate_add_position(
            positions,
            symbol,
            candidate,
            symbol_to_cluster=symbol_to_cluster,
            regime=regime,
        )
        print(f"{symbol}: {report.decision} | {report.reason}")
        if report.decision == "ACCEPT":
            positions[symbol] = positions.get(symbol, 0.0) + candidate

    _print_subheader("Final Positions")
    print(positions)

    budget_now = {s: 1.0 for s in positions}
    deltas = governor.risk_engine.propose_rc_rebalance(
        positions,
        budget_now,
        limits=governor.effective_limits(regime),
    )
    _print_subheader("Rebalance Deltas")
    print(deltas or "Portfolio already balanced.")


def main() -> None:
    _print_header("COMPREHENSIVE RISK WORKFLOWS")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    try:
        example_01_single_strategy(mt5_client)
        example_02_multi_strategy_portfolio(mt5_client)
        example_03_existing_system_integration(mt5_client)
        example_04_scenario_showcase(mt5_client)
        example_05_live_workflow_and_rebalance(mt5_client)
    finally:
        mt5_client.shutdown()
        _print_header("COMPREHENSIVE RISK WORKFLOWS COMPLETED")


if __name__ == "__main__":
    main()
