"""
Usage Example: Full Risk Scenarios with Live MT5 Data

Demonstrates end-to-end scenarios:
1. Conservative new trader setup
2. Growing account with milestone sizing
3. Multi-strategy portfolio
4. Crisis response (STRESS regime)
5. Rebalancing workflow

Run:
    python tests/usage/risk/05_full_scenarios.py
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Optional

import pandas as pd

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.mt5 import MT5Client, get_mt5_api
from apps.risk import (
    GovernanceEngine,
    PortfolioRiskEngine,
    PositionSizer,
    RiskBudgetAllocator,
    RiskLimits,
    RiskRegimeDetector,
    RegimeState,
)
from apps.risk.limits import CorrelationPreference
from apps.sqlite.users import UserManager
from apps.trading import Engine

mt5 = get_mt5_api()


def _get_mt5_credentials() -> Optional[dict]:
    creds = UserManager().get_mt5_credentials()
    if not creds:
        print("No default broker credentials found.")
        return None
    return creds


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
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return None

    if not hasattr(mt5_client, "get_symbol_info"):
        mt5_client.get_symbol_info = mt5.symbol_info  # type: ignore[attr-defined]
    if not hasattr(mt5_client, "get_account_equity"):
        def _get_equity_for_client():
            engine_instance = Engine(backend="mt5")
            api = engine_instance.api
            account = api.account_info()
            equity = float(account.equity)
            engine_instance.client.shutdown()
            return equity
        mt5_client.get_account_equity = _get_equity_for_client  # type: ignore[attr-defined]

    return mt5_client


def _get_equity() -> float:
    engine_instance = Engine(backend="mt5")
    api = engine_instance.api
    account = api.account_info()
    equity = float(account.equity)
    engine_instance.client.shutdown()
    return equity


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    _print_header("FULL RISK SCENARIOS - LIVE MT5 DATA")

    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    try:
        equity = _get_equity()
        if equity <= 0:
            print("Failed to fetch account equity from MT5.")
            return

        # 1) Conservative new trader setup
        _print_header("1) New Trader - Conservative Setup")
        limits = RiskLimits(
            var_cap_frac=0.05,
            es_cap_frac=0.08,
            delta_var_cap_frac=0.01,
            max_single_rc_frac=0.30,
        )
        sizer = PositionSizer(
            method="fixed_risk",
            config={"risk_percent": 0.5, "use_dynamic_stop_loss": False},
        )
        governor = GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=mt5_client,
                timeframe="H1",
                start_pos=0,
                end_pos=200,
            ),
            limits=limits,
        )

        size1 = sizer.calculate_size(
            account_balance=equity,
            entry_price=1.1000,
            stop_loss=1.0950,
            symbol_info=None,
        )
        report1 = governor.evaluate_add_position(
            current_positions={}, candidate_symbol="EURUSD", candidate_lots=size1
        )
        print(f"Trade 1 size: {size1:.4f} lots")
        print(f"Decision: {report1.decision} | New VaR: ${report1.new_var:,.2f}")

        size2 = sizer.calculate_size(
            account_balance=equity,
            entry_price=1.2000,
            stop_loss=1.1950,
            symbol_info=None,
        )
        report2 = governor.evaluate_add_position(
            current_positions={"EURUSD": size1}, candidate_symbol="GBPUSD", candidate_lots=size2
        )
        print(f"Trade 2 size: {size2:.4f} lots")
        print(f"Decision: {report2.decision} | New VaR: ${report2.new_var:,.2f}")

        # 2) Growing account milestone sizing
        _print_header("2) Growing Account - Milestone Sizing")
        milestone_sizer = PositionSizer(
            method="milestone",
            config={
                "initial_balance": 10000.0,
                "base_lot_size": 0.1,
                "milestone_amount": 3000.0,
                "lot_increment": 0.2,
            },
        )
        balances = [10000, 13000, 16000, 19000, 22000]
        for balance in balances:
            size = milestone_sizer.calculate_size(
                account_balance=balance,
                entry_price=1.1000,
                symbol_info=None,
            )
            print(f"Balance: ${balance:>8,.0f} -> Size: {size:.4f} lots")

        # 3) Multi-strategy portfolio
        _print_header("3) Multi-Strategy Portfolio")
        limits = RiskLimits(var_cap_frac=0.10, es_cap_frac=0.15, delta_var_cap_frac=0.02, max_single_rc_frac=0.35)
        governor = GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=mt5_client,
                timeframe="H1",
                start_pos=0,
                end_pos=200,
            ),
            limits=limits,
        )
        corr_pref = CorrelationPreference(target_corr=0.50, penalty_strength=2.0)
        allocator = RiskBudgetAllocator(governor, corr_pref)
        sizer = PositionSizer(
            method="fixed_risk",
            config={"risk_percent": 1.0, "use_dynamic_stop_loss": False},
        )
        strategies = [
            {"name": "EURUSD Trend", "symbol": "EURUSD", "entry": 1.1000, "stop": 1.0950, "budget": 0.30},
            {"name": "GBPUSD Mean", "symbol": "GBPUSD", "entry": 1.2500, "stop": 1.2450, "budget": 0.30},
            {"name": "XAUUSD Breakout", "symbol": "XAUUSD", "entry": 2000.0, "stop": 1990.0, "budget": 0.40},
        ]
        base_lots: Dict[str, float] = {}
        for strat in strategies:
            size = sizer.calculate_size(
                account_balance=equity,
                entry_price=strat["entry"],
                stop_loss=strat["stop"],
                symbol_info=None,
            )
            base_lots[strat["symbol"]] = size
            print(f"  {strat['name']}: {size:.4f} lots")

        budgets = {s["symbol"]: s["budget"] for s in strategies}
        target_lots = allocator.compute_target_lots(
            symbols=list(base_lots.keys()), base_lots=base_lots, budgets=budgets
        )
        print("Target Lots:")
        for symbol, lots in target_lots.items():
            print(f"  {symbol}: {lots:.4f} lots")

        # 4) Crisis response (regime detection)
        _print_header("4) Crisis Response (Regime Detection)")
        detector = RiskRegimeDetector(
            vol_spike_mult=1.8, corr_spike_level=0.55, dd_trigger_frac=0.05, lookback=60
        )
        returns_data = {}
        for symbol in ["EURUSD", "GBPUSD", "XAUUSD"]:
            df = mt5_client.get_bars(symbol=symbol, timeframe="D1", count=120, start_pos=0)
            if df is not None and not df.empty:
                returns_data[symbol] = df["close"].pct_change()
        returns_df = pd.DataFrame(returns_data).dropna(how="all")
        equity_curve = pd.Series([equity] * len(returns_df), index=returns_df.index)
        regime = detector.detect(returns_df, equity_curve)
        print(f"Detected Regime: {regime.name}")

        # 5) Rebalancing workflow
        _print_header("5) Rebalancing Workflow")
        current_positions = {"EURUSD": 0.8, "GBPUSD": 0.2, "USDJPY": 0.2, "XAUUSD": 0.1}
        target_budget = {s: 1 / len(current_positions) for s in current_positions}
        rebalance = governor.propose_rc_rebalance(
            positions=current_positions, target_rc_budget=target_budget, max_iters=10, step_frac=0.10
        )
        if rebalance:
            print("Rebalance Deltas:")
            for symbol, delta in rebalance.items():
                print(f"  {symbol}: {delta:+.4f} lots")
        else:
            print("Portfolio already balanced.")

        print("\n" + "=" * 80)
        print("DONE")
        print("=" * 80)

    finally:
        mt5_client.shutdown()


if __name__ == "__main__":
    main()

