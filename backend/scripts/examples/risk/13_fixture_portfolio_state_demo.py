"""
Example 13: Fixture Portfolio State Demo

Type: fixture-based deterministic demo

This example builds a canonical PortfolioState from synthetic inputs only.
It does not require a broker connection.

Run:
    python backend/scripts/examples/risk/13_fixture_portfolio_state_demo.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

    from haruquant.risk import PortfolioStateEngine, RiskLimits


def bars(start: str = "2024-01-01", periods: int = 6) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    return pd.DataFrame(
        {
            "Open": [1.10, 1.11, 1.12, 1.13, 1.14, 1.15][:periods],
            "High": [1.11, 1.12, 1.13, 1.14, 1.15, 1.16][:periods],
            "Low": [1.09, 1.10, 1.11, 1.12, 1.13, 1.14][:periods],
            "Close": [1.105, 1.115, 1.125, 1.135, 1.145, 1.155][:periods],
            "Volume": [100, 110, 120, 130, 140, 150][:periods],
            "Spread": [1, 1, 1, 1, 1, 1][:periods],
        },
        index=idx,
    )


def main() -> None:
    state = PortfolioStateEngine().build_state(
        account={"equity": 10000.0, "balance": 9800.0, "currency": "USD"},
        positions={"EURUSD": 0.5, "GBPUSD": -0.3},
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
        },
        market_data={"EURUSD": bars(), "GBPUSD": bars()},
        limits=RiskLimits(),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX"},
        timeframe="H1",
        as_of="2024-01-01T05:00:00Z",
        metadata={"source": "fixture_demo"},
    )

    print("Example type: fixture-based deterministic demo")
    print(f"validation_errors={state.validation_summary.has_errors}")
    print(f"active_symbols={state.active_symbols}")
    print(f"position_map={state.position_map}")
    print(f"symbol_to_cluster={state.symbol_to_cluster}")
    print(f"eurusd_last_close={state.markets['EURUSD'].last_close}")
    print(f"eurusd_exposure={state.exposures['EURUSD']:.2f}")
    print(f"gbpusd_exposure={state.exposures['GBPUSD']:.2f}")


if __name__ == "__main__":
    main()
