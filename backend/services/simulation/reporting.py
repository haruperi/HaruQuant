"""Reporting helpers for simulation results."""

from __future__ import annotations

from backend.services.simulation.results import SimulationRunResult


def print_trade_record_summary(result: SimulationRunResult) -> None:
    print(f"completed_trades={result.trade_count}")
    for idx, record in enumerate(result.trades, start=1):
        print(
            f"trade[{idx}] ticket={record.ticket} symbol={record.symbol} side={record.type} "
            f"size={record.size:.2f} pnl={record.profit_loss:.2f} mfe={record.mfe_usd:.2f} "
            f"mae={record.mae_usd:.2f} close_type={record.close_type} exit_reason={record.exit_reason}"
        )


def print_run_result_summary(result: SimulationRunResult) -> None:
    print(f"processed_ticks={result.processed_ticks}")
    print(f"initial_balance={result.initial_balance:.2f}")
    print(f"final_balance={result.final_balance:.2f}")
    print(f"final_equity={result.final_equity:.2f}")
    print(f"total_profit={result.total_profit:.2f}")
    print(f"total_return={result.total_return:.4%}")
    print(f"completed_trades={result.trade_count}")
    print(f"equity_points={len(result.equity_curve)}")
    if result.trades:
        first = result.trades[0]
        last = result.trades[-1]
        print(
            f"first_trade=ticket:{first.ticket} side:{first.type} pnl:{first.profit_loss:.2f} "
            f"mfe:{first.mfe_usd:.2f} mae:{first.mae_usd:.2f}"
        )
        print(
            f"last_trade=ticket:{last.ticket} side:{last.type} pnl:{last.profit_loss:.2f} "
            f"mfe:{last.mfe_usd:.2f} mae:{last.mae_usd:.2f}"
        )


def print_portfolio_symbol_summary(result: SimulationRunResult) -> None:
    for symbol, row in result.symbol_summary.items():
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
