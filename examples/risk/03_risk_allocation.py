"""
Usage Example: Risk Allocation with Live MT5 Data

Demonstrates:
1. Equal risk allocation
2. Custom risk budgets
3. Correlation-based adjustments
4. Rebalancing deltas
5. RC rebalance proposal
6. Regime impact (NORMAL vs STRESS)

Run:
    python tests/usage/risk/03_risk_allocation.py
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
    AllocationPlanner,
    GovernanceEngine,
    PortfolioRiskEngine,
    RiskLimits,
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
    return mt5_client


def _get_account_equity() -> float:
    engine_instance = Engine(backend="mt5")
    api = engine_instance.api
    account = api.account_info()
    equity = float(account.equity)
    engine_instance.client.shutdown()
    return equity


def _print_lots(title: str, lots: Dict[str, float]) -> None:
    print(title)
    for symbol, lot in lots.items():
        print(f"  {symbol}: {lot:.4f} lots")


def main() -> None:
    print("\n" + "=" * 80)
    print("RISK ALLOCATION - LIVE MT5 DATA")
    print("=" * 80)

    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    try:
        equity = _get_account_equity()
        if equity <= 0:
            print("Failed to fetch account equity from MT5.")
            return

        symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        limits = RiskLimits(var_cap_frac=0.10, es_cap_frac=0.15)
        governance_engine = GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=mt5_client,
                timeframe="H1",
                start_pos=0,
                end_pos=200,
            ),
            limits=limits,
        )

        base_lots = {"EURUSD": 0.30, "GBPUSD": 0.30, "USDJPY": 0.30}

        # 1) Equal allocation
        print("\n" + "-" * 80)
        print("1) Equal Risk Allocation")
        allocator = AllocationPlanner(governance_engine)
        target_equal = allocator.compute_target_lots(
            symbols=symbols, base_lots=base_lots, budgets=None, regime=None
        )
        _print_lots("Base Lots:", base_lots)
        _print_lots("Target Lots:", target_equal)

        # 2) Custom budgets
        print("\n" + "-" * 80)
        print("2) Custom Risk Budgets")
        custom_budgets = {"EURUSD": 0.25, "GBPUSD": 0.25, "USDJPY": 0.50}
        target_custom = allocator.compute_target_lots(
            symbols=symbols, base_lots=base_lots, budgets=custom_budgets, regime=None
        )
        print("Budgets:")
        for symbol, budget in custom_budgets.items():
            print(f"  {symbol}: {budget:.0%}")
        _print_lots("Target Lots:", target_custom)

        # 3) Correlation preference
        print("\n" + "-" * 80)
        print("3) Correlation Preference")
        corr_pref = CorrelationPreference(target_corr=0.40, penalty_strength=3.0, min_budget_frac=0.20)
        allocator_corr = AllocationPlanner(governance_engine, corr_pref)
        target_corr = allocator_corr.compute_target_lots(
            symbols=symbols, base_lots=base_lots, budgets=None, regime=None
        )
        _print_lots("Target Lots (corr-adjusted):", target_corr)

        # 4) Rebalancing deltas
        print("\n" + "-" * 80)
        print("4) Rebalancing Deltas")
        current_positions = {"EURUSD": 0.50, "GBPUSD": 0.30, "USDJPY": 0.20}
        deltas = allocator.lots_to_deltas(current_positions, target_equal)
        print("Current Positions:")
        for symbol, lot in current_positions.items():
            print(f"  {symbol}: {lot:.4f} lots")
        print("Deltas:")
        for symbol, delta in deltas.items():
            print(f"  {symbol}: {delta:+.4f} lots")

        # 5) RC rebalance proposal
        print("\n" + "-" * 80)
        print("5) Risk Contribution Rebalance")
        rc_target = {"EURUSD": 1 / 3, "GBPUSD": 1 / 3, "USDJPY": 1 / 3}
        rc_deltas = governance_engine.risk_engine.propose_rc_rebalance(
            positions=current_positions,
            target_rc_budget=rc_target,
            limits=governance_engine.effective_limits(None),
            max_iters=10,
            step_frac=0.10,
        )
        if rc_deltas:
            print("Proposed RC Deltas:")
            for symbol, delta in rc_deltas.items():
                print(f"  {symbol}: {delta:+.4f} lots")
        else:
            print("Portfolio already balanced by RC.")

        # 6) Regime impact
        print("\n" + "-" * 80)
        print("6) Regime Impact")
        normal = RegimeState(name="NORMAL")
        stress = RegimeState(name="STRESS")
        target_normal = allocator.compute_target_lots(
            symbols=symbols, base_lots=base_lots, budgets=None, regime=normal
        )
        target_stress = allocator.compute_target_lots(
            symbols=symbols, base_lots=base_lots, budgets=None, regime=stress
        )
        _print_lots("Target Lots (NORMAL):", target_normal)
        _print_lots("Target Lots (STRESS):", target_stress)

        print("\n" + "=" * 80)
        print("DONE")
        print("=" * 80)

    finally:
        mt5_client.shutdown()


if __name__ == "__main__":
    main()

