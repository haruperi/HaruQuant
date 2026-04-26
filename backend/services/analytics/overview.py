"""
Comprehensive trade and equity analytics overview.

Focus: aggregation and orchestration of all analytics modules.

This module acts as the central hub for the analytics service. It normalizes raw trade data,
orchestrates parallel calculations across multiple performance categories (metrics, ratios,
drawdowns, etc.), and prepares structured payloads for reports and UI displays.

Summary of Methods:
------------------
Utility & Normalization:
    - _normalize_trades: Standardize diverse trade input formats into a unified DataFrame.
    - _periods_to_timedelta: Convert period counts into human-readable time durations.

Core Calculation Engines:
    - calculate_analytics_for_subset: Aggregate all metrics for a specific slice of trade data.
    - get_analytics_overview: Parallel execution of analytics for All, Long, and Short trade subsets.

Reporting & Payload Construction:
    - format_summary_as_rows: Format summary metrics into labeled rows for CLI or PDF reports.
    - build_overview_payload: Construct a complete JSON-ready payload including metrics and equity curves.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from . import metrics, ratios, drawdowns, returns, risks, benchmark, distributions, efficiency


# =========================================================================
# Utility & Normalization
# =========================================================================


def _normalize_trades(trades: Any) -> pd.DataFrame:
    """Ensure trades are in a DataFrame with consistent column names."""
    if isinstance(trades, pd.DataFrame):
        df = trades.copy()
    else:
        from dataclasses import asdict, is_dataclass
        rows = []
        for t in trades:
            if is_dataclass(t):
                rows.append(asdict(t))
            elif hasattr(t, "to_dict"):
                rows.append(t.to_dict())
            elif isinstance(t, dict):
                rows.append(dict(t))
            else:
                continue
        df = pd.DataFrame(rows)
    
    if df.empty:
        return df

    # Standardize column names
    standards = {
        "type": ["side", "direction"],
        "profit_loss": ["pnl", "profit", "final_profit"],
        "size": ["position_size", "quantity", "volume"],
        "time_in_trade": ["time_in_trade_seconds"],
        "r_multiple": ["rMultiple"],
        "mfe_usd": ["mfe_pips"],
        "mae_usd": ["mae_pips"],
    }
    
    for target, alternatives in standards.items():
        if target not in df.columns:
            for alt in alternatives:
                if alt in df.columns:
                    df = df.rename(columns={alt: target})
                    break

    for col in ["open_time", "close_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            
    return df


def _periods_to_timedelta(periods: float | int, index: pd.Index) -> pd.Timedelta:
    """Convert a number of periods/bars to a Timedelta based on index frequency."""
    if not len(index) or periods <= 0:
        return pd.Timedelta(0)
    if len(index) < 2:
        return pd.Timedelta(days=float(periods))
    
    diffs = pd.Series(index).diff().dropna()
    diffs = diffs[diffs > pd.Timedelta(0)]
    step = diffs.median() if not diffs.empty else pd.Timedelta(days=1)
    return step * float(periods)


# =========================================================================
# Core Calculation Engines
# =========================================================================


def calculate_analytics_for_subset(
    trades: pd.DataFrame,
    initial_balance: float,
    start_time: pd.Timestamp | None = None,
    end_time: pd.Timestamp | None = None,
    benchmark_returns_series: pd.Series | None = None,
    benchmark_equity_series: pd.Series | None = None,
) -> dict[str, Any]:
    """Calculate ALL analytics categories for a specific subset of trades."""
    if trades.empty:
        return {
            "metrics": {}, "returns": {}, "ratios": {}, 
            "risks": {}, "drawdowns": {}, "distributions": {}, 
            "efficiency": {}, "benchmark": {}, "summary": {}
        }

    # Pre-calculate common derived data
    equity = returns.equity_curve(trades, initial_balance)
    rets = returns.returns_series(equity)
    
    # 1. Metrics (Trade-based statistics)
    metrics_data = {
        "total_trades": metrics.total_trades(trades),
        "winning_trades": metrics.winning_trades(trades),
        "losing_trades": metrics.losing_trades(trades),
        "breakeven_trades": metrics.breakeven_trades(trades),
        "long_trades": metrics.long_trades(trades),
        "short_trades": metrics.short_trades(trades),
        "open_trades": metrics.count_open_trades(trades),
        "win_rate": metrics.win_rate(trades),
        "loss_rate": metrics.loss_rate(trades),
        "avg_win": metrics.avg_win(trades),
        "avg_loss": metrics.avg_loss(trades),
        "largest_win": metrics.largest_win(trades),
        "largest_loss": metrics.largest_loss(trades),
        "median_win": metrics.median_win(trades),
        "median_loss": metrics.median_loss(trades),
        "slippage_paid": metrics.slippage_paid(trades),
        "commission_paid": metrics.commission_paid(trades),
        "swap_paid": metrics.swap_paid(trades),
        "avg_r_multiple": metrics.avg_r_multiple(trades),
        "median_r_multiple": metrics.median_r_multiple(trades),
        "max_r_multiple": metrics.max_r_multiple(trades),
        "min_r_multiple": metrics.min_r_multiple(trades),
        "max_consecutive_wins": metrics.max_consecutive_wins(trades),
        "max_consecutive_losses": metrics.max_consecutive_losses(trades),
        "avg_consecutive_wins": metrics.avg_consecutive_wins(trades),
        "avg_consecutive_losses": metrics.avg_consecutive_losses(trades),
        "avg_time_in_trade": metrics.avg_time_in_trade(trades),
        "median_time_in_trade": metrics.median_time_in_trade(trades),
        "max_time_in_trade": metrics.max_time_in_trade(trades),
        "min_time_in_trade": metrics.min_time_in_trade(trades),
        "sqn": metrics.sqn(trades),
        "kelly_criterion": metrics.kelly_criterion(trades),
        "time_in_market_hours": metrics.time_in_market_duration(trades).total_seconds() / 3600.0,
        "percent_time_in_market": metrics.percent_time_in_market(trades, start_time, end_time),
        "longest_flat_period_hours": metrics.longest_flat_period_duration(trades, start_time, end_time).total_seconds() / 3600.0,
        "max_size_held": metrics.max_size_held(trades),
        "t_statistic": metrics.t_statistic(trades),
        "trade_efficiency": metrics.trade_efficiency(trades),
        "expectancy_variance": metrics.expectancy_variance(trades),
        "max_runup": metrics.max_runup(equity),
        "median_mae_mfe": metrics.median_mae_mfe(trades),
        "r_expectancy": metrics.r_expectancy(trades),
        "trade_outcome_entropy": metrics.trade_outcome_entropy(trades),
        "trading_period_duration_days": metrics.trading_period_duration(trades).total_seconds() / 86400.0,
    }

    # 2. Returns
    returns_data = {
        "net_profit": returns.net_profit(trades),
        "gross_profit": returns.gross_profit(trades),
        "gross_loss": returns.gross_loss(trades),
        "adjusted_net_profit": returns.adjusted_net_profit(trades),
        "select_net_profit": returns.select_net_profit(trades),
        "total_return": returns.total_return(equity),
        "total_return_usd": returns.total_return(equity),
        "cagr": returns.cagr(equity),
        "annualized_return": returns.annualized_return(rets),
        "geometric_mean_return": returns.geometric_mean_return(rets),
        "cmgr": returns.compound_monthly_growth_rate(equity),
        "volatility": returns.return_volatility(rets),
        "downside_volatility": returns.downside_return_volatility(rets),
        "avg_monthly_return": returns.avg_monthly_return(equity),
        "monthly_return_stddev": returns.monthly_return_stddev(equity),
        "buy_and_hold_return": returns.buy_and_hold_return(benchmark_equity_series) if benchmark_equity_series is not None else 0.0,
        "buy_and_hold_cagr": returns.buy_and_hold_cagr(benchmark_equity_series) if benchmark_equity_series is not None else 0.0,
        "adjusted_gross_profit": returns.adjusted_gross_profit(trades),
        "adjusted_gross_loss": returns.adjusted_gross_loss(trades),
        "select_gross_profit": returns.select_gross_profit(trades),
        "select_gross_loss": returns.select_gross_loss(trades),
        "return_skewness": returns.return_skewness(rets),
        "return_kurtosis": returns.return_kurtosis(rets),
        "daily_returns": returns.daily_returns(equity).tolist(),
        "weekly_returns": returns.weekly_returns(equity).tolist(),
        "monthly_returns": returns.monthly_returns(equity).tolist(),
        "annual_returns": returns.annual_returns(equity).tolist(),
        "log_returns": returns.log_returns_series(equity).tolist(),
    }

    # 3. Ratios
    ratios_data = {
        "sharpe_ratio": ratios.sharpe_ratio(rets, annualize=True),
        "sortino_ratio": ratios.sortino_ratio(rets, annualize=True),
        "calmar_ratio": ratios.calmar_ratio(returns_data["cagr"], drawdowns.max_strategy_drawdown_percent(equity)),
        "omega_ratio": ratios.omega_ratio(rets),
        "gain_to_pain_ratio": ratios.gain_to_pain_ratio(rets),
        "profit_factor": ratios.profit_factor(trades),
        "payoff_ratio": ratios.payoff_ratio(trades),
        "expectancy": ratios.expectancy(trades),
        "expectancy_r": ratios.expectancy_r(trades),
        "edge_ratio": ratios.edge_ratio(trades),
        "rina_index": ratios.rina_index(returns_data["select_net_profit"], drawdowns.avg_drawdown(equity), metrics_data["percent_time_in_market"]),
        "recovery_factor": drawdowns.recovery_factor(equity),
        "information_ratio": ratios.information_ratio(rets, benchmark_returns_series) if benchmark_returns_series is not None else 0.0,
        "sterling_ratio": ratios.sterling_ratio(equity),
        "profit_to_mae_ratio": ratios.profit_to_mae_ratio(trades),
        "mfe_to_mae_ratio": ratios.mfe_to_mae_ratio(trades),
        "fouse_ratio": ratios.fouse_ratio(rets),
        "upside_potential_ratio": ratios.upside_potential_ratio(rets),
        "kappa_ratio": ratios.kappa_ratio(rets),
        "return_over_drawdown": ratios.return_over_drawdown(trades, drawdowns.max_strategy_drawdown(equity)),
        "expectancy_over_variance": ratios.expectancy_over_variance(trades),
        "adjusted_profit_factor": ratios.adjusted_profit_factor(trades),
        "select_profit_factor": ratios.select_profit_factor(trades),
        "net_profit_to_max_dd": ratios.net_profit_as_percent_of_max_strategy_drawdown(trades, drawdowns.max_strategy_drawdown(equity)),
    }

    # 4. Risks
    risks_data = {
        "volatility": risks.volatility(rets),
        "annualized_volatility": risks.annualized_volatility(rets),
        "value_at_risk_95": risks.value_at_risk(rets, confidence=0.95),
        "expected_shortfall_95": risks.expected_shortfall(rets, confidence=0.95),
        "risk_of_ruin": risks.risk_of_ruin(trades, risk_per_trade=1.0),
        "max_exposure": risks.max_exposure(trades),
        "avg_exposure": risks.avg_exposure(trades),
        "downside_volatility_risk": risks.downside_volatility(rets),
        "max_loss_probability": risks.max_loss_probability(trades),
        "drawdown_probability_10pct": risks.drawdown_probability(equity, threshold=10.0),
        "exposure_time_ratio": risks.exposure_time_ratio(trades),
    }

    # 5. Drawdowns
    max_dd_periods = int(drawdowns.max_drawdown_duration(equity))
    avg_dd_periods = float(drawdowns.avg_drawdown_duration(equity))
    
    drawdowns_data = {
        "max_drawdown_usd": drawdowns.max_strategy_drawdown(equity),
        "max_drawdown_pct": drawdowns.max_strategy_drawdown_percent(equity),
        "avg_drawdown_usd": drawdowns.avg_drawdown(equity),
        "max_drawdown_duration": str(_periods_to_timedelta(max_dd_periods, equity.index)),
        "avg_drawdown_duration": str(_periods_to_timedelta(avg_dd_periods, equity.index)),
        "ulcer_index": drawdowns.ulcer_index(equity),
        "pain_index": drawdowns.pain_index(equity),
        "max_close_to_close_drawdown": drawdowns.max_close_to_close_drawdown(trades),
        "max_close_to_close_drawdown_pct": drawdowns.max_close_to_close_drawdown_percent(trades, initial_balance),
        "avg_yearly_max_drawdown": drawdowns.avg_yearly_max_drawdown(equity),
        "account_size_required": drawdowns.account_size_required(trades, initial_balance),
        "pain_ratio": ratios.pain_ratio(rets),
        "max_drawdown_date": drawdowns.max_strategy_drawdown_date(equity).isoformat() if not equity.empty else None,
        "max_close_to_close_drawdown_date": drawdowns.max_close_to_close_drawdown_date(trades).isoformat() if not trades.empty else None,
        "drawdown_distribution": drawdowns.drawdown_distribution(equity),
        "time_to_recovery_periods": [str(_periods_to_timedelta(p, equity.index)) for p in drawdowns.time_to_recovery(equity)],
        "avg_trade_drawdown": drawdowns.avg_trade_drawdown(trades),
    }

    # 6. Distributions
    distributions_data = {
        "returns": distributions.return_distribution(rets),
        "trades": distributions.trade_pnl_distribution(trades),
        "r_multiples": distributions.r_multiple_distribution(trades),
        "outlier_ratio": distributions.outlier_ratio(rets),
        "skewness": distributions.skewness(rets),
        "kurtosis": distributions.kurtosis(rets),
        "jarque_bera": distributions.jarque_bera_test(rets),
        "shapiro_wilk": distributions.shapiro_wilk_test(rets),
        "fat_tail_score": distributions.fat_tail_score(rets),
        "higher_moments": distributions.higher_moments(rets),
    }

    # 7. Efficiency
    efficiency_data = {
        "capital_efficiency": efficiency.capital_efficiency(trades),
        "time_efficiency": efficiency.time_efficiency(trades),
        "return_per_trade": efficiency.return_per_trade(trades),
        "mfe_efficiency": efficiency.mfe_efficiency(trades),
        "mae_efficiency": efficiency.mae_efficiency(trades),
        "exit_efficiency": efficiency.exit_efficiency(trades),
        "win_efficiency": efficiency.win_efficiency(trades),
        "loss_containment_efficiency": efficiency.loss_containment_efficiency(trades),
        "trades_per_day": efficiency.trades_per_day(trades),
        "return_per_unit_risk": efficiency.return_per_unit_risk(trades),
        "risk_adjusted_efficiency": efficiency.risk_adjusted_efficiency(trades),
        "position_size_efficiency": efficiency.position_size_efficiency(trades),
        "return_per_unit_time": efficiency.return_per_unit_time(trades),
        "return_per_trade_opportunity": efficiency.return_per_trade_opportunity(trades),
    }

    # 8. Benchmark
    benchmark_data = {}
    if benchmark_returns_series is not None:
        benchmark_data = {
            "beta": benchmark.beta(rets, benchmark_returns_series),
            "alpha": benchmark.alpha(rets, benchmark_returns_series),
            "r_squared": benchmark.r_squared(rets, benchmark_returns_series),
            "tracking_error": benchmark.tracking_error(rets, benchmark_returns_series),
            "batting_average": benchmark.batting_average(rets, benchmark_returns_series),
            "up_capture": benchmark.up_down_capture(rets, benchmark_returns_series)[0],
            "down_capture": benchmark.up_down_capture(rets, benchmark_returns_series)[1],
            "relative_drawdown": float(benchmark.relative_drawdown(equity, benchmark_equity_series).min()) if benchmark_equity_series is not None else 0.0,
        }

    # 9. Summary (Overview table style)
    summary_data = {
        "start": start_time.isoformat() if start_time else None,
        "end": end_time.isoformat() if end_time else None,
        "duration_days": (end_time - start_time).total_seconds() / 86400.0 if start_time and end_time else 0,
        "equity_final": float(equity.iloc[-1]) if not equity.empty else initial_balance,
        "equity_peak": float(equity.max()) if not equity.empty else initial_balance,
        "total_return": returns_data["total_return"],
        "return_usd": returns_data["net_profit"],
        "return_pct": (returns_data["net_profit"] / initial_balance * 100.0) if initial_balance > 0 else 0,
        "buy_hold_return_pct": returns_data["buy_and_hold_return"],
        "num_trades": metrics_data["total_trades"],
        "win_rate_pct": metrics_data["win_rate"],
        "best_trade_pct": (trades["profit_loss"] / initial_balance * 100.0).max() if not trades.empty and initial_balance > 0 else 0.0,
        "worst_trade_pct": (trades["profit_loss"] / initial_balance * 100.0).min() if not trades.empty and initial_balance > 0 else 0.0,
        "avg_trade_pct": (trades["profit_loss"] / initial_balance * 100.0).mean() if not trades.empty and initial_balance > 0 else 0.0,
        "exposure_time_pct": metrics_data["percent_time_in_market"],
        "max_trade_duration": str((pd.to_datetime(trades["close_time"]) - pd.to_datetime(trades["open_time"])).max()) if not trades.empty else "0 days 00:00:00",
        "avg_trade_duration": str((pd.to_datetime(trades["close_time"]) - pd.to_datetime(trades["open_time"])).mean()) if not trades.empty else "0 days 00:00:00",
        "max_drawdown_pct": drawdowns_data["max_drawdown_pct"],
        "avg_drawdown_pct": (drawdowns.drawdown_series(equity) / equity.expanding().max() * 100.0).mean() if not equity.empty else 0.0,
        "max_drawdown_duration": drawdowns_data["max_drawdown_duration"],
        "avg_drawdown_duration": drawdowns_data["avg_drawdown_duration"],
        "value_at_risk_95": risks_data["value_at_risk_95"],
        "expectancy_pct": ratios_data["expectancy"] / initial_balance * 100.0 if initial_balance > 0 else 0.0,
        "expectancy_r": ratios_data["expectancy_r"],
        "profit_factor": ratios_data["profit_factor"],
        "sharpe_ratio": ratios_data["sharpe_ratio"],
        "sortino_ratio": ratios_data["sortino_ratio"],
        "calmar_ratio": ratios_data["calmar_ratio"],
        "alpha": benchmark_data.get("alpha", 0.0),
        "beta": benchmark_data.get("beta", 0.0),
        "cagr": returns_data["cagr"],
        "annual_return": returns_data["annualized_return"],
        "annual_volatility": risks_data["annualized_volatility"],
        "max_exposure": risks_data["max_exposure"],
        "risk_of_ruin": risks_data["risk_of_ruin"],
        "ulcer_index": drawdowns_data["ulcer_index"],
        "efficiency_ratio": efficiency_data["exit_efficiency"],
        "sqn": metrics_data["sqn"],
        "kelly_criterion": metrics_data["kelly_criterion"],
    }

    return {
        "metrics": metrics_data,
        "returns": returns_data,
        "ratios": ratios_data,
        "risks": risks_data,
        "drawdowns": drawdowns_data,
        "distributions": distributions_data,
        "efficiency": efficiency_data,
        "benchmark": benchmark_data,
        "summary": summary_data,
    }


def get_analytics_overview(
    trades: Any,
    initial_balance: float,
    start_time: Any = None,
    end_time: Any = None,
    benchmark_equity: Optional[pd.Series] = None,
) -> dict[str, Any]:
    """Calculate comprehensive analytics across all categories in parallel subsets."""
    df = _normalize_trades(trades)
    t_start = pd.Timestamp(start_time) if start_time else None
    t_end = pd.Timestamp(end_time) if end_time else None
    
    benchmark_rets = benchmark_equity.pct_change().dropna() if benchmark_equity is not None and len(benchmark_equity) >= 2 else None
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_all = executor.submit(calculate_analytics_for_subset, df, initial_balance, t_start, t_end, benchmark_rets, benchmark_equity)
        f_long = executor.submit(calculate_analytics_for_subset, df[df["type"] == "buy"], initial_balance, t_start, t_end, benchmark_rets, benchmark_equity)
        f_short = executor.submit(calculate_analytics_for_subset, df[df["type"] == "sell"], initial_balance, t_start, t_end, benchmark_rets, benchmark_equity)
        
        results_all = f_all.result()
        results_long = f_long.result()
        results_short = f_short.result()
        
    final_output = {}
    categories = ["metrics", "returns", "ratios", "risks", "drawdowns", "distributions", "efficiency", "benchmark", "summary"]
    for cat in categories:
        final_output[cat] = {"all": results_all.get(cat, {}), "long": results_long.get(cat, {}), "short": results_short.get(cat, {})}
        
    def _to_python_types(obj):
        if isinstance(obj, dict): return {k: _to_python_types(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)): return [_to_python_types(x) for x in obj]
        if isinstance(obj, (np.float64, np.float32)): return float(obj)
        if isinstance(obj, (np.int64, np.int32)): return int(obj)
        return None if pd.isna(obj) else obj

    return _to_python_types(final_output)


# =========================================================================
# Reporting & Payload Construction
# =========================================================================


def format_summary_as_rows(summary_data: dict[str, Any]) -> list[tuple[str, str]]:
    """Format raw summary data into display rows for reports."""
    def _fmt_num(val, decimals=2):
        if val is None or not np.isfinite(float(val)): return "nan"
        return f"{float(val):.{decimals}f}"
    
    return [
        ("Start", str(summary_data.get("start", ""))),
        ("End", str(summary_data.get("end", ""))),
        ("Duration", f"{summary_data.get('duration_days', 0):.2f} days"),
        ("Equity Final [$]", _fmt_num(summary_data.get("equity_final"), 2)),
        ("Equity Peak [$]", _fmt_num(summary_data.get("equity_peak"), 2)),
        ("Return [$]", _fmt_num(summary_data.get("return_usd"), 2)),
        ("Return [%]", _fmt_num(summary_data.get("return_pct"), 5)),
        ("Buy & Hold Return [%]", _fmt_num(summary_data.get("buy_hold_return_pct"), 5)),
        ("Num of Trades", str(summary_data.get("num_trades", 0))),
        ("Win Rate [%]", _fmt_num(summary_data.get("win_rate_pct"), 5)),
        ("Best Trade [%]", _fmt_num(summary_data.get("best_trade_pct"), 5)),
        ("Worst Trade [%]", _fmt_num(summary_data.get("worst_trade_pct"), 5)),
        ("Avg. Trade [%]", _fmt_num(summary_data.get("avg_trade_pct"), 5)),
        ("Exposure Time [%]", _fmt_num(summary_data.get("exposure_time_pct"), 5)),
        ("Max. Trade Duration", str(summary_data.get("max_trade_duration", ""))),
        ("Avg. Trade Duration", str(summary_data.get("avg_trade_duration", ""))),
        ("Max. Drawdown [%]", _fmt_num(summary_data.get("max_drawdown_pct"), 5)),
        ("Avg. Drawdown [%]", _fmt_num(summary_data.get("avg_drawdown_pct"), 5)),
        ("Max. Drawdown Duration", str(summary_data.get("max_drawdown_duration", ""))),
        ("Avg. Drawdown Duration", str(summary_data.get("avg_drawdown_duration", ""))),
        ("Value at Risk (95%)", _fmt_num(summary_data.get("value_at_risk_95"), 5)),
        ("Expectancy [%]", _fmt_num(summary_data.get("expectancy_pct"), 5)),
        ("R-Expectancy", _fmt_num(summary_data.get("expectancy_r"), 5)),
        ("Profit Factor", _fmt_num(summary_data.get("profit_factor"), 5)),
        ("Sharpe Ratio", _fmt_num(summary_data.get("sharpe_ratio"), 5)),
        ("Sortino Ratio", _fmt_num(summary_data.get("sortino_ratio"), 5)),
        ("Calmar Ratio", _fmt_num(summary_data.get("calmar_ratio"), 5)),
        ("Alpha [%]", _fmt_num(summary_data.get("alpha"), 5)),
        ("Beta", _fmt_num(summary_data.get("beta"), 5)),
        ("CAGR [%]", _fmt_num(summary_data.get("cagr"), 5)),
        ("Return (Ann.) [%]", _fmt_num(summary_data.get("annual_return"), 5)),
        ("Volatility (Ann.) [%]", _fmt_num(summary_data.get("annual_volatility"), 5)),
        ("Risk of Ruin [%]", _fmt_num(summary_data.get("risk_of_ruin", 0) * 100, 2)),
        ("Max Exposure [$]", _fmt_num(summary_data.get("max_exposure"), 2)),
        ("Ulcer Index", _fmt_num(summary_data.get("ulcer_index"), 5)),
        ("SQN", _fmt_num(summary_data.get("sqn"), 5)),
        ("Kelly Criterion", _fmt_num(summary_data.get("kelly_criterion"), 5)),
    ]


def build_overview_payload(
    trades: Any,
    initial_balance: float,
    start_time: Any = None,
    end_time: Any = None,
    equity_curve_records: Optional[list[Any]] = None,
) -> dict[str, Any]:
    """Build the full analytics payload for the API including charts."""
    analytics = get_analytics_overview(trades, initial_balance, start_time, end_time)
    df = _normalize_trades(trades)
    
    def _get_curve(subset_df):
        if subset_df.empty: return []
        curve = returns.equity_curve(subset_df, initial_balance)
        return [{"date": ts.isoformat(), "equity": float(val)} for ts, val in curve.items()]

    equity_curves = {
        "all": _get_curve(df),
        "long": _get_curve(df[df["type"] == "buy"]),
        "short": _get_curve(df[df["type"] == "sell"]),
    }

    return {
        "metrics": analytics["summary"],
        "equity_curves": equity_curves,
        "charts": {"equity_curve": equity_curves["all"]}
    }
