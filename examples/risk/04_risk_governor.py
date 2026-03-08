"""
Usage Example: Risk Governor with Live MT5 Data

Demonstrates:
1. Basic accept (first trade)
2. Accept within limits (second trade)
3. VaR cap violation
4. Delta VaR cap violation
5. ES cap violation
6. Risk contribution cap violation
7. Cluster cap violation
8. Regime tightening (NORMAL vs STRESS)
9. Position reduction acceptance

Run:
    python tests/usage/risk/04_risk_governor.py
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.mt5 import MT5Client, get_mt5_api
from apps.risk import RiskGovernor, RiskLimits, RegimeState
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
        def _get_equity():
            engine_instance = Engine(backend="mt5")
            api = engine_instance.api
            account = api.account_info()
            equity = float(account.equity)
            engine_instance.client.shutdown()
            return equity
        mt5_client.get_account_equity = _get_equity  # type: ignore[attr-defined]

    return mt5_client


def _print_report(title: str, report) -> None:
    print(title)
    print(f"  Decision: {report.decision}")
    print(f"  Reason: {report.reason}")
    print(f"  Current VaR: ${report.current_var:,.2f}")
    print(f"  New VaR: ${report.new_var:,.2f}")
    print(f"  Delta VaR: ${report.delta_var:,.2f}")
    print(f"  Current ES: ${report.current_es:,.2f}")
    print(f"  New ES: ${report.new_es:,.2f}")
    print(f"  Delta ES: ${report.delta_es:,.2f}")
    if report.rc_map_new:
        print(f"  RC Map: {report.rc_map_new}")
    if report.rc_violations:
        print(f"  RC Violations: {report.rc_violations}")
    if report.cluster_violations:
        print(f"  Cluster Violations: {report.cluster_violations}")


def main() -> None:
    print("\n" + "=" * 80)
    print("RISK GOVERNOR - LIVE MT5 DATA")
    print("=" * 80)

    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    try:
        engine_instance = Engine(backend="mt5")
        api = engine_instance.api
        account = api.account_info()
        equity = float(account.equity)
        if equity <= 0:
            print("Failed to fetch account equity from MT5.")
            return

        symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
        symbol_to_cluster = {
            "EURUSD": "FOREX",
            "GBPUSD": "FOREX",
            "USDJPY": "FOREX",
            "XAUUSD": "METALS",
        }

        limits = RiskLimits(
            var_cap_frac=0.10,
            es_cap_frac=0.15,
            delta_var_cap_frac=0.02,
            delta_es_cap_frac=0.03,
            max_single_rc_frac=0.25,
            cluster_var_caps={"FOREX": 0.06, "METALS": 0.04},
            cluster_es_caps={"FOREX": 0.08, "METALS": 0.06},
        )

        governor = RiskGovernor(
            mt5_client=mt5_client, limits=limits, timeframe="H1", start_pos=0, end_pos=200
        )

        # 1) First trade accept
        print("\n" + "-" * 80)
        print("1) First Trade (Empty Portfolio)")
        report = governor.evaluate_add_position(
            current_positions={}, candidate_symbol="EURUSD", candidate_lots=0.1
        )
        _print_report("First Trade:", report)

        # 2) Accept within limits
        print("\n" + "-" * 80)
        print("2) Add Second Position (Within Limits)")
        report2 = governor.evaluate_add_position(
            current_positions={"EURUSD": 0.1}, candidate_symbol="GBPUSD", candidate_lots=0.1
        )
        _print_report("Second Trade:", report2)

        # 3) VaR cap violation
        print("\n" + "-" * 80)
        print("3) VaR Cap Violation")
        tight_limits = RiskLimits(var_cap_frac=0.03, es_cap_frac=0.15)
        tight_governor = RiskGovernor(
            mt5_client=mt5_client, limits=tight_limits, timeframe="H1", start_pos=0, end_pos=200
        )
        report3 = tight_governor.evaluate_add_position(
            current_positions={}, candidate_symbol="EURUSD", candidate_lots=1.0
        )
        _print_report("VaR Cap Trade:", report3)

        # 4) Delta VaR cap violation
        print("\n" + "-" * 80)
        print("4) Delta VaR Cap Violation")
        delta_limits = RiskLimits(var_cap_frac=0.10, es_cap_frac=0.15, delta_var_cap_frac=0.01)
        delta_governor = RiskGovernor(
            mt5_client=mt5_client, limits=delta_limits, timeframe="H1", start_pos=0, end_pos=200
        )
        delta_governor.evaluate_add_position(
            current_positions={}, candidate_symbol="EURUSD", candidate_lots=0.1
        )
        report4 = delta_governor.evaluate_add_position(
            current_positions={"EURUSD": 0.1}, candidate_symbol="GBPUSD", candidate_lots=0.5
        )
        _print_report("Delta VaR Trade:", report4)

        # 5) ES cap violation
        print("\n" + "-" * 80)
        print("5) ES Cap Violation")
        es_limits = RiskLimits(var_cap_frac=0.10, es_cap_frac=0.05)
        es_governor = RiskGovernor(
            mt5_client=mt5_client, limits=es_limits, timeframe="H1", start_pos=0, end_pos=200
        )
        report5 = es_governor.evaluate_add_position(
            current_positions={}, candidate_symbol="EURUSD", candidate_lots=0.8
        )
        _print_report("ES Cap Trade:", report5)

        # 6) Risk contribution cap violation
        print("\n" + "-" * 80)
        print("6) Risk Contribution Cap Violation")
        rc_limits = RiskLimits(var_cap_frac=0.10, es_cap_frac=0.15, max_single_rc_frac=0.40)
        rc_governor = RiskGovernor(
            mt5_client=mt5_client, limits=rc_limits, timeframe="H1", start_pos=0, end_pos=200
        )
        current = {"EURUSD": 0.1, "GBPUSD": 0.1, "USDJPY": 0.1}
        report6 = rc_governor.evaluate_add_position(
            current_positions=current, candidate_symbol="XAUUSD", candidate_lots=0.8
        )
        _print_report("RC Cap Trade:", report6)

        # 7) Cluster cap violation
        print("\n" + "-" * 80)
        print("7) Cluster Cap Violation")
        cluster_limits = RiskLimits(
            var_cap_frac=0.10,
            es_cap_frac=0.15,
            cluster_var_caps={"FOREX": 0.05, "METALS": 0.03},
            cluster_es_caps={"FOREX": 0.07, "METALS": 0.05},
        )
        cluster_governor = RiskGovernor(
            mt5_client=mt5_client, limits=cluster_limits, timeframe="H1", start_pos=0, end_pos=200
        )
        current_fx = {"EURUSD": 0.3, "GBPUSD": 0.3}
        report7 = cluster_governor.evaluate_add_position(
            current_positions=current_fx,
            candidate_symbol="USDJPY",
            candidate_lots=0.3,
            symbol_to_cluster=symbol_to_cluster,
        )
        _print_report("Cluster Cap Trade:", report7)

        # 8) Regime tightening
        print("\n" + "-" * 80)
        print("8) Regime Tightening")
        normal = RegimeState(name="NORMAL")
        stress = RegimeState(name="STRESS")
        report8_normal = governor.evaluate_add_position(
            current_positions={}, candidate_symbol="EURUSD", candidate_lots=0.4, regime=normal
        )
        report8_stress = governor.evaluate_add_position(
            current_positions={}, candidate_symbol="EURUSD", candidate_lots=0.4, regime=stress
        )
        _print_report("NORMAL Regime Trade:", report8_normal)
        _print_report("STRESS Regime Trade:", report8_stress)

        # 9) Position reduction
        print("\n" + "-" * 80)
        print("9) Position Reduction")
        current_pos = {"EURUSD": 0.5, "GBPUSD": 0.3}
        report9 = governor.evaluate_add_position(
            current_positions=current_pos, candidate_symbol="EURUSD", candidate_lots=-0.3
        )
        _print_report("Reduction Trade:", report9)

        print("\n" + "=" * 80)
        print("DONE")
        print("=" * 80)

    finally:
        if 'engine_instance' in locals():
            engine_instance.client.shutdown()
        mt5_client.shutdown()


if __name__ == "__main__":
    main()

