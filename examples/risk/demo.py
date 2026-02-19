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

from apps.risk.risk_limits import RiskLimits, CorrelationPreference
from apps.risk.governor import RiskGovernor
from apps.risk.allocator import RiskBudgetAllocator
from apps.risk.regime import RiskRegimeDetector
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager

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

    mt5_client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )
    
    if not mt5_client.connect():
        logger.error("Failed to initialize MT5 client")
        sys.exit(1)

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


if __name__ == "__main__":
    main()
