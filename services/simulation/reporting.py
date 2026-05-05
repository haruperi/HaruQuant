"""Reporting helpers for simulation results."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

import pandas as pd
from services.analytics.overview import format_summary_as_rows

if TYPE_CHECKING:
    from services.simulation.results import SimulationRunResult


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
    for label, value in simulation_summary_rows(result):
        print(f"{label:<24} {value}")


def simulation_summary_rows(result: SimulationRunResult) -> list[tuple[str, str]]:
    """Return formatted summary rows for a standard simulation result."""
    from services.analytics.overview import calculate_analytics_for_subset

    start = result.metadata.get("data", {}).get("start")
    end = result.metadata.get("data", {}).get("end")
    benchmark_equity = _benchmark_equity(result)

    analytics = calculate_analytics_for_subset(
        pd.DataFrame([asdict(t) for t in result.result.trades]),
        initial_balance=result.metrics.get("initial_balance", 0.0),
        start_time=start,
        end_time=end,
        benchmark_equity_series=benchmark_equity,
    )
    summary = dict(analytics["summary"])
    summary.setdefault("start", pd.Timestamp(start).isoformat() if start else "")
    summary.setdefault("end", pd.Timestamp(end).isoformat() if end else "")
    summary["processed_ticks"] = result.processed_ticks
    summary["num_trades"] = result.trade_count
    equity = _equity_series(result)
    if not equity.empty:
        summary["equity_final"] = float(equity.iloc[-1])
        summary["equity_peak"] = float(equity.max())
    if benchmark_equity is not None and len(benchmark_equity) >= 2:
        summary["buy_hold_return_pct"] = (
            float(benchmark_equity.iloc[-1] / benchmark_equity.iloc[0] - 1.0) * 100.0
        )
    summary.update(_drawdown_duration_summary(result))
    rows = list(format_summary_as_rows(summary))
    rows.append(("# Trades", str(result.trade_count)))
    return rows


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


def _benchmark_equity(result: SimulationRunResult) -> pd.Series | None:
    policy = str(result.metadata.get("reporting", {}).get("benchmark_policy", "") or "")
    if policy != "first_symbol":
        return None
    frames = getattr(result.prepared, "signal_bars_by_symbol", {}) or {}
    if not frames:
        return None
    first_symbol = next(iter(frames))
    frame = frames[first_symbol]
    if "close" not in frame or len(frame["close"]) < 2:
        return None
    closes = frame["close"].astype(float)
    initial_balance = float(result.metrics.get("initial_balance", 0.0))
    if closes.iloc[0] == 0:
        return None
    return closes / float(closes.iloc[0]) * initial_balance


def _drawdown_duration_summary(result: SimulationRunResult) -> dict[str, str]:
    equity = _equity_series(result)
    if equity.empty:
        return {}
    peak = equity.cummax()
    underwater = equity < peak
    durations: list[pd.Timedelta] = []
    start: pd.Timestamp | None = None
    previous_ts: pd.Timestamp | None = None
    for ts, is_underwater in underwater.items():
        timestamp = pd.Timestamp(ts)
        if is_underwater and start is None:
            start = timestamp
        if not is_underwater and start is not None:
            durations.append(timestamp - start)
            start = None
        previous_ts = timestamp
    if start is not None and previous_ts is not None:
        durations.append(previous_ts - start)
    if not durations:
        zero = str(pd.Timedelta(0))
        return {
            "max_drawdown_duration": zero,
            "avg_drawdown_duration": zero,
        }
    max_duration = max(durations)
    avg_duration = sum(durations, pd.Timedelta(0)) / len(durations)
    return {
        "max_drawdown_duration": str(max_duration),
        "avg_drawdown_duration": str(avg_duration),
    }


def _equity_series(result: SimulationRunResult) -> pd.Series:
    rows = []
    for point in result.result.equity_curve:
        timestamp = getattr(point, "timestamp", None)
        equity = getattr(point, "equity", None)
        if timestamp is None or equity is None:
            continue
        rows.append((pd.Timestamp(timestamp), float(equity)))
    if not rows:
        return pd.Series(dtype=float)
    series = pd.Series([value for _, value in rows], index=[ts for ts, _ in rows])
    return series.groupby(level=0).last().sort_index()
