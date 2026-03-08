"""Example workflow with 5 FX trades.

Run:
    python examples/workflow_5_fx.py
"""

from __future__ import annotations

import sys
import os
import logging
import numpy as np
import pandas as pd

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk.risk_limits import RiskLimits, CorrelationPreference
from apps.risk.governor import RiskGovernor
from apps.risk.allocator import RiskBudgetAllocator
from apps.risk.regime import RiskRegimeDetector
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.trading import Engine

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    # Assuming running from project root, database is at data/database/haruquant.db
    # Adjust path if necessary
    db_path = os.path.join(os.getcwd(), "data", "database", "haruquant.db")
    user_manager.db_path = db_path

    username = "haruperi"
    user = user_manager.get_user(username=username)
    if not user:
        logger.error(f"User {username} not found")
        sys.exit(1)

    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        logger.error(f"No default broker credentials found for {username}")
        sys.exit(1)

    return creds


def main():
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD"]

    # Equal-risk base lots (normally produced by your ATR/stop-based sizing)
    base_lots = {"EURUSD": 0.30, "GBPUSD": 0.25, "USDJPY": 0.35, "AUDUSD": 0.28, "NZDUSD": 0.22}

    symbol_to_cluster = {s: "FX:USD" for s in symbols}

    creds = get_mt5_credentials()
    logger.info(f"Connecting to MT5 with login {creds['login']}")

    mt5_client = MT5Client()
    
    if not mt5_client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ):
        logger.error("Failed to initialize MT5 client")
        sys.exit(1)

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
        def _get_positions(symbol=None):
            engine_instance = Engine(backend="mt5")
            pos = engine_instance.api.positions_get(symbol=symbol)
            engine_instance.client.shutdown()
            return pos
        mt5_client.get_positions = _get_positions  # type: ignore[attr-defined]

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

    governor = RiskGovernor(mt5_client=mt5_client, limits=limits, timeframe="D1", end_pos=350)

    corr_pref = CorrelationPreference(target_corr=0.50, penalty_strength=2.0, min_budget_frac=0.30)
    allocator = RiskBudgetAllocator(governor, corr_pref=corr_pref)

    detector = RiskRegimeDetector()

    # Detect regime using returns of existing portfolio (empty here => NORMAL)
    regime = detector.detect(pd.DataFrame())

    # Plan target lots with soft corr preference + RC budgeting
    target_lots = allocator.compute_target_lots(symbols, base_lots, budgets=None, regime=regime)

    # Open positions one by one with hard gating
    positions = {}
    for sym in symbols:
        cand = target_lots[sym]
        rep = governor.evaluate_add_position(positions, sym, cand, symbol_to_cluster=symbol_to_cluster, regime=regime)
        print(f"{sym}: {rep.decision} | {rep.reason}")
        if rep.decision == "ACCEPT":
            positions[sym] = positions.get(sym, 0.0) + cand

    print("\nFinal positions:", positions)

    # Rebalance to equal RC budgets
    budget_now = {s: 1.0 for s in positions.keys()}
    deltas = governor.propose_rc_rebalance(positions, budget_now, regime=regime)
    print("\nRebalance deltas:", deltas)

    mt5_client.shutdown()


if __name__ == "__main__":
    main()
