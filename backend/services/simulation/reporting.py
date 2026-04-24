"""Reporting helpers for simulation results."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from math import isfinite
from typing import Any

import pandas as pd

from backend.services.analytics import benchmark, drawdowns, metrics, ratios, returns, risks
from backend.services.simulation.results import SimulationRunResult


def _records_to_frame(records: list[Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        if hasattr(record, "to_dict"):
            rows.append(record.to_dict())
        elif is_dataclass(record):
            rows.append(asdict(record))
        elif isinstance(record, dict):
            rows.append(dict(record))
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    for column in ("open_time", "close_time", "orig_open_time", "timestamp"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def _equity_curve_to_series(result: SimulationRunResult) -> pd.Series:
    frame = _records_to_frame(result.equity_curve)
    if not frame.empty and {"timestamp", "equity"} <= set(frame.columns):
        frame = frame.dropna(subset=["timestamp"]).copy()
        series = pd.Series(
            frame["equity"].astype(float).to_numpy(),
            index=pd.DatetimeIndex(frame["timestamp"]),
            dtype=float,
        ).sort_index()
        if not series.empty and series.index.has_duplicates:
            # Portfolio runs can emit multiple intra-timestamp snapshots while each symbol is
            # processed. Keep the final equity state for each timestamp before analytics.
            series = series.groupby(level=0).last()
        if not series.empty:
            return series

    trades = _records_to_frame(result.trades)
    if not trades.empty and {"open_time", "close_time", "profit_loss"} <= set(trades.columns):
        return returns.equity_curve(trades, result.initial_balance).astype(float)

    start = pd.Timestamp(result.start)
    return pd.Series([float(result.initial_balance), float(result.final_equity)], index=[start, start])


def _strategy_daily_returns(equity_curve: pd.Series) -> pd.Series:
    daily = returns.daily_returns(equity_curve)
    if not daily.empty:
        return daily
    fallback = returns.returns_series(equity_curve)
    return fallback.astype(float)


def _benchmark_price_series(result: SimulationRunResult) -> pd.Series:
    prepared = result.prepared
    by_symbol = getattr(prepared, "signal_bars_by_symbol", {}) or {}
    normalized_prices: list[pd.Series] = []
    policy = str(getattr(result.config.reporting, "benchmark_policy", "equal_weight") or "equal_weight")
    configured_symbol = getattr(result.config.reporting, "benchmark_symbol", None)

    if policy == "custom_symbol" and configured_symbol:
        symbols_to_use = [str(configured_symbol).upper()]
    elif policy == "first_symbol":
        symbols_to_use = [result.symbols[0]] if result.symbols else []
    else:
        symbols_to_use = list(result.symbols)

    for symbol in symbols_to_use:
        bars = by_symbol.get(symbol)
        if bars is None or bars.empty:
            continue
        close_col = "close" if "close" in bars.columns else "Close" if "Close" in bars.columns else None
        if close_col is None:
            continue
        series = pd.to_numeric(bars[close_col], errors="coerce").dropna()
        if series.empty:
            continue
        series = series[series.index >= pd.Timestamp(result.start)]
        if series.empty:
            continue
        first = float(series.iloc[0])
        if first == 0.0:
            continue
        normalized_prices.append(series.astype(float) / first)

    if not normalized_prices:
        return pd.Series(dtype=float)

    combined = pd.concat(normalized_prices, axis=1).sort_index().ffill().dropna(how="all")
    if combined.empty:
        return pd.Series(dtype=float)
    if policy in {"first_symbol", "custom_symbol"}:
        return combined.iloc[:, 0].astype(float)
    return combined.mean(axis=1).astype(float)


def _trade_return_pct(trades: pd.DataFrame) -> pd.Series:
    if trades.empty or "type" not in trades.columns:
        return pd.Series(dtype=float)

    open_price = pd.to_numeric(trades.get("open_price"), errors="coerce")
    close_price = pd.to_numeric(trades.get("close_price"), errors="coerce")
    trade_type = trades["type"].astype(str).str.lower()

    buy_returns = ((close_price - open_price) / open_price) * 100.0
    sell_returns = ((open_price - close_price) / open_price) * 100.0
    out = buy_returns.where(trade_type == "buy", sell_returns)
    return out.replace([pd.NA, float("inf"), float("-inf")], pd.NA).dropna().astype(float)


def _average_drawdown_percent(equity_curve: pd.Series) -> float:
    if len(equity_curve) < 2:
        return 0.0
    running_max = equity_curve.expanding().max()
    running_max = running_max.replace(0.0, pd.NA)
    pct_drawdown = ((equity_curve - running_max) / running_max) * 100.0
    pct_drawdown = pct_drawdown.dropna()
    pct_drawdown = pct_drawdown[pct_drawdown < 0.0]
    if pct_drawdown.empty:
        return 0.0
    return float(pct_drawdown.mean())


def _timedelta_from_seconds(seconds: float | int | None) -> pd.Timedelta:
    numeric = float(seconds or 0.0)
    return pd.to_timedelta(numeric, unit="s")


def _periods_to_timedelta(periods: float | int, index: pd.DatetimeIndex) -> pd.Timedelta:
    if not len(index):
        return pd.Timedelta(0)
    if len(index) < 2:
        return pd.Timedelta(days=float(periods or 0))
    diffs = index.to_series().diff().dropna()
    diffs = diffs[diffs > pd.Timedelta(0)]
    if diffs.empty:
        step = pd.Timedelta(days=1)
    else:
        step = diffs.median()
    return step * float(periods or 0)


def _fmt_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "nan"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not isfinite(numeric):
        return "nan"
    return f"{numeric:.{decimals}f}"


def _fmt_timedelta(value: Any) -> str:
    if value is None:
        return "0 days 00:00:00"
    delta = pd.Timedelta(value)
    return str(delta)


def simulation_summary_rows(result: SimulationRunResult) -> list[tuple[str, str]]:
    trades = _records_to_frame(result.trades)
    equity_curve = _equity_curve_to_series(result)
    strategy_returns = _strategy_daily_returns(equity_curve)
    benchmark_price = _benchmark_price_series(result)
    benchmark_returns = returns.daily_returns(benchmark_price)
    trade_returns_pct = _trade_return_pct(trades)

    start = pd.Timestamp(result.start)
    end = pd.Timestamp(result.end)
    duration = end - start

    exposure_pct = metrics.percent_time_in_market(trades, start, end) if not trades.empty else 0.0
    equity_final = float(equity_curve.iloc[-1]) if not equity_curve.empty else result.final_equity
    equity_peak = float(equity_curve.max()) if not equity_curve.empty else result.final_equity
    total_return_pct = result.total_return * 100.0
    buy_hold_return_pct = returns.buy_and_hold_return(benchmark_price) if not benchmark_price.empty else 0.0
    annual_return_pct = returns.annualized_return(strategy_returns, periods_per_year=252) if not strategy_returns.empty else 0.0
    annual_volatility_pct = risks.annualized_volatility(strategy_returns, periods_per_year=252) * 100.0 if not strategy_returns.empty else 0.0
    cagr_pct = returns.cagr(equity_curve) if len(equity_curve) >= 2 else 0.0
    sharpe_ratio = ratios.sharpe_ratio(strategy_returns, annualize=True) if not strategy_returns.empty else 0.0
    sortino_ratio = ratios.sortino_ratio(strategy_returns, annualize=True) if not strategy_returns.empty else 0.0
    calmar_ratio = ratios.calmar_ratio(cagr_pct, drawdowns.max_strategy_drawdown_percent(equity_curve)) if len(equity_curve) >= 2 else 0.0
    alpha_pct = benchmark.alpha(strategy_returns, benchmark_returns) * 100.0 if not strategy_returns.empty and not benchmark_returns.empty else 0.0
    beta_value = benchmark.beta(strategy_returns, benchmark_returns) if not strategy_returns.empty and not benchmark_returns.empty else 0.0
    max_drawdown_pct = -drawdowns.max_strategy_drawdown_percent(equity_curve) if len(equity_curve) >= 2 else 0.0
    avg_drawdown_pct = _average_drawdown_percent(equity_curve)
    
    total_profit_usd = result.total_profit
    var_95_pct = risks.value_at_risk(strategy_returns, confidence=0.95) * 100.0 if not strategy_returns.empty else 0.0

    dd_duration_series = drawdowns.drawdown_duration_series(equity_curve) if len(equity_curve) >= 2 else pd.Series(dtype=int)
    max_dd_duration = _periods_to_timedelta(dd_duration_series.max() if not dd_duration_series.empty else 0, pd.DatetimeIndex(equity_curve.index))
    avg_dd_duration = _periods_to_timedelta(drawdowns.avg_drawdown_duration(equity_curve) if len(equity_curve) >= 2 else 0.0, pd.DatetimeIndex(equity_curve.index))

    max_trade_duration = pd.Timedelta(0)
    avg_trade_duration = pd.Timedelta(0)
    if not trades.empty and {"open_time", "close_time"} <= set(trades.columns):
        trade_durations = (trades["close_time"] - trades["open_time"]).dropna()
        if not trade_durations.empty:
            max_trade_duration = trade_durations.max()
            avg_trade_duration = trade_durations.mean()
    elif not trades.empty and "time_in_trade" in trades.columns:
        max_trade_duration = _timedelta_from_seconds(trades["time_in_trade"].max())
        avg_trade_duration = _timedelta_from_seconds(trades["time_in_trade"].mean())

    best_trade_pct = float(trade_returns_pct.max()) if not trade_returns_pct.empty else 0.0
    worst_trade_pct = float(trade_returns_pct.min()) if not trade_returns_pct.empty else 0.0
    avg_trade_pct = float(trade_returns_pct.mean()) if not trade_returns_pct.empty else 0.0
    expectancy_pct = float(ratios.expectancy(trade_returns_pct)) if not trade_returns_pct.empty else 0.0

    if not trades.empty and "r_multiple" in trades.columns and pd.to_numeric(trades["r_multiple"], errors="coerce").abs().sum() > 0:
        sqn_value = metrics.sqn(trades)
    else:
        sqn_value = metrics.sqn(trade_returns_pct.to_numpy()) if not trade_returns_pct.empty else 0.0

    rows = [
        ("Start", str(start)),
        ("End", str(end)),
        ("Duration", _fmt_timedelta(duration)),
        ("Exposure Time [%]", _fmt_number(exposure_pct, 5)),
        ("Equity Final [$]", _fmt_number(equity_final, 2)),
        ("Equity Peak [$]", _fmt_number(equity_peak, 2)),
        ("Return [$]", _fmt_number(total_profit_usd, 2)),
        ("Return [%]", _fmt_number(total_return_pct, 5)),
        ("Buy & Hold Return [%]", _fmt_number(buy_hold_return_pct, 5)),
        ("Return (Ann.) [%]", _fmt_number(annual_return_pct, 5)),
        ("Volatility (Ann.) [%]", _fmt_number(annual_volatility_pct, 5)),
        ("Value at Risk (95%) [%]", _fmt_number(var_95_pct, 5)),
        ("CAGR [%]", _fmt_number(cagr_pct, 5)),
        ("Sharpe Ratio", _fmt_number(sharpe_ratio, 5)),
        ("Sortino Ratio", _fmt_number(sortino_ratio, 5)),
        ("Calmar Ratio", _fmt_number(calmar_ratio, 5)),
        ("Alpha [%]", _fmt_number(alpha_pct, 5)),
        ("Beta", _fmt_number(beta_value, 5)),
        ("Max. Drawdown [%]", _fmt_number(max_drawdown_pct, 5)),
        ("Avg. Drawdown [%]", _fmt_number(avg_drawdown_pct, 5)),
        ("Max. Drawdown Duration", _fmt_timedelta(max_dd_duration)),
        ("Avg. Drawdown Duration", _fmt_timedelta(avg_dd_duration)),
        ("# Trades", str(result.trade_count)),
        ("Win Rate [%]", _fmt_number(metrics.win_rate(trades) if not trades.empty else 0.0, 5)),
        ("Best Trade [%]", _fmt_number(best_trade_pct, 5)),
        ("Worst Trade [%]", _fmt_number(worst_trade_pct, 5)),
        ("Avg. Trade [%]", _fmt_number(avg_trade_pct, 5)),
        ("Max. Trade Duration", _fmt_timedelta(max_trade_duration)),
        ("Avg. Trade Duration", _fmt_timedelta(avg_trade_duration)),
        ("Profit Factor", _fmt_number(ratios.profit_factor(trades) if not trades.empty else 0.0, 5)),
        ("Expectancy [%]", _fmt_number(expectancy_pct, 5)),
        ("SQN", _fmt_number(sqn_value, 5)),
        ("Kelly Criterion", _fmt_number(metrics.kelly_criterion(trades) if not trades.empty else 0.0, 5)),
    ]
    return rows


def print_trade_record_summary(result: SimulationRunResult) -> None:
    print(f"completed_trades={result.trade_count}")
    for idx, record in enumerate(result.trades, start=1):
        print(
            f"trade[{idx}] ticket={record.ticket} symbol={record.symbol} side={record.type} "
            f"size={record.size:.2f} pnl={record.profit_loss:.2f} mfe={record.mfe_usd:.2f} "
            f"mae={record.mae_usd:.2f} close_type={record.close_type} exit_reason={record.exit_reason}"
        )


def print_run_result_summary(result: SimulationRunResult) -> None:
    for label, value in simulation_summary_rows(result):
        print(f"{label:<24} {value}")


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
