"""Reporting helpers for simulation results."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

import pandas as pd
from backend.services.analytics.overview import format_summary_as_rows

if TYPE_CHECKING:
    from backend.services.simulation.results import SimulationRunResult


def print_trade_record_summary(result: SimulationRunResult) -> None:
    # No changes to trade printing logic needed here, it still uses result.trades
    print(f"completed_trades={len(result.result.trades)}")
    for idx, record in enumerate(result.result.trades, start=1):
        print(
            f"trade[{idx}] ticket={record.ticket} symbol={record.symbol} side={record.type} "
            f"size={record.size:.2f} pnl={record.profit_loss:.2f} mfe={record.mfe_usd:.2f} "
            f"mae={record.mae_usd:.2f} close_type={record.close_type} exit_reason={record.exit_reason}"
        )


def print_run_result_summary(result: SimulationRunResult) -> None:
    # We need the overview summary data
    from backend.services.analytics.overview import calculate_analytics_for_subset
    
    # We calculate just the 'all' summary for the CLI printout
    start = result.metadata.get("data", {}).get("start")
    end = result.metadata.get("data", {}).get("end")
    
    analytics = calculate_analytics_for_subset(
        pd.DataFrame([asdict(t) for t in result.result.trades]),
        initial_balance=result.metrics.get("initial_balance", 0.0),
        start_time=start,
        end_time=end
    )
    
    for label, value in format_summary_as_rows(analytics["summary"]):
        print(f"{label:<24} {value}")


def print_portfolio_symbol_summary(result: SimulationRunResult) -> None:
    # Use metrics from the result object
    symbol_summary = result.metrics.get("symbol_summary", {})
    for symbol, row in symbol_summary.items():
        print(
            f"portfolio_summary[{symbol}] "
            f"trades={int(row.get('trades', 0.0))} pnl={float(row.get('pnl', 0.0)):.2f}"
        )


def print_simulation_summary(result: SimulationRunResult) -> None:
    print_run_result_summary(result)
    print_portfolio_symbol_summary(result)
    if result.warnings:
        for warning in result.warnings:
            print(f"warning={warning}")
