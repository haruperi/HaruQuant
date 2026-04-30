"""
Summary:
-------
HaruQuant Analytics Orchestration & Overview.
Aggregation of trade and equity analytics into unified reporting structures.
This module serves as the primary entry point for generating comprehensive performance reports 
by orchestrating all sub-modules (Returns, Risks, Efficiency, Distributions, etc.).

Summary of Methods:
------------------
Data Orchestration:
    - BacktestResult: Primary data container for strategy outcomes.
    - generate_full_report: Orchestrates all modules to produce a complete analytics dict.
    - run_parallel_analysis: Threaded execution of distinct analytics components.

Reporting Blocks:
    - get_trade_metrics: Aggregated trade diagnostics (win rate, profit factor, etc.).
    - get_equity_metrics: Periodic performance and growth metrics (CAGR, returns).
    - get_risk_metrics: Downside and tail risk analysis (VaR, MaxDD, Ulcer).
    - get_relative_metrics: Benchmark comparison (Alpha, Beta).
    - get_distribution_metrics: Moment and normality analysis.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from . import metrics, ratios, drawdowns, returns, risks, benchmark, distributions, efficiency, statistical_tests, decision_scorecard


# =========================================================================
# Utility & Normalization
# =========================================================================


def _format_duration(td_or_hours: Any) -> str:
    """Format duration into 'Xd Yh' format."""
    if pd.isna(td_or_hours):
        return "0h"
        
    if isinstance(td_or_hours, (pd.Timedelta, pd._libs.tslibs.timedeltas.Timedelta)):
        total_seconds = td_or_hours.total_seconds()
    elif isinstance(td_or_hours, (int, float, np.float64, np.int64)):
        total_seconds = float(td_or_hours) * 3600.0
    else:
        try:
            td = pd.to_timedelta(td_or_hours)
            total_seconds = td.total_seconds()
        except:
            return str(td_or_hours)
            
    hours = total_seconds / 3600.0
    if hours <= 0:
        return "0h"
        
    days = int(hours // 24)
    rem_hours = int(round(hours % 24))
    
    if rem_hours == 24:
        days += 1
        rem_hours = 0
        
    if days > 0:
        return f"{days}d {rem_hours}h"
    return f"{rem_hours}h"


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
        # Guarantee minimum columns for empty DF to avoid KeyErrors downstream
        # especially 'type' which is used for subset slicing
        for col in ["type", "profit_loss", "size", "time_in_trade", "r_multiple", "mfe_usd", "mae_usd", "open_time", "close_time"]:
            if col not in df.columns:
                df[col] = pd.Series(dtype=object)
        return df

    # DEBUG: Check columns
    # import sys
    # print(f"DEBUG: _normalize_trades columns: {df.columns.tolist()}", file=sys.stderr)

    # Standardize column names safely to avoid duplicates
    standards = {
        "type": ["side", "direction"],
        "profit_loss": ["pnl", "profit", "final_profit"],
        "profit_pips": ["pips", "net_pips", "points"],
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
            # Handle potential seconds-since-epoch from MT5
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")
            else:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            
    if "type" not in df.columns and not df.empty:
        df["type"] = "buy" # Default if missing
        
    return df


def _extract_proxy_benchmark(df: pd.DataFrame) -> Optional[pd.Series]:
    """Try to extract a proxy price series from trades if no benchmark is provided."""
    if df.empty or "symbol" not in df.columns or "open_price" not in df.columns:
        return None
        
    # Take the most frequent symbol
    symbols = df["symbol"].dropna()
    if symbols.empty:
        return None
    symbol = symbols.mode()[0]
    symbol_df = df[df["symbol"] == symbol].sort_values("open_time")
    
    if symbol_df.empty:
        return None
        
    # Create a 2-point series as a minimal proxy for buy-and-hold
    # This isn't a full curve, but returns.buy_and_hold_return only needs iloc[0] and iloc[-1]
    # And returns.cagr uses the index to calculate duration.
    try:
        t0 = symbol_df["open_time"].iloc[0]
        t1 = symbol_df["close_time"].iloc[-1]
        p0 = symbol_df["open_price"].iloc[0]
        p1 = symbol_df["close_price"].iloc[-1]
        
        if pd.isna(t0) or pd.isna(t1) or p0 <= 0 or p1 <= 0:
            return None
            
        prices = pd.Series([p0, p1], index=[t0, t1])
        return prices
    except:
        return None


def _periods_to_timedelta(periods: float | int, index: pd.Index) -> pd.Timedelta:
    """Convert a number of periods/bars to a Timedelta based on index frequency."""
    if not len(index) or periods <= 0:
        return pd.Timedelta(0)
    if len(index) < 2:
        return pd.Timedelta(days=float(periods))
    
    # Estimate step from median difference between timestamps
    ts_series = pd.Series(index)
    diffs = ts_series.diff().dropna()
    diffs = diffs[diffs > pd.Timedelta(0)]
    step = diffs.median() if not diffs.empty else pd.Timedelta(days=1)
    return step * float(periods)


# =========================================================================
# Core Calculation Engines
# =========================================================================


def calculate_analytics_for_subset(
    trades: pd.DataFrame,
    initial_balance: float,
    start_time: pd.Timestamp | str | None = None,
    end_time: pd.Timestamp | str | None = None,
    benchmark_returns_series: pd.Series | None = None,
    benchmark_equity_series: pd.Series | None = None,
) -> dict[str, Any]:
    """Calculate ALL analytics categories for a specific subset of trades."""
    # Ensure timestamps are in pd.Timestamp format
    start_time = pd.Timestamp(start_time) if start_time else None
    end_time = pd.Timestamp(end_time) if end_time else None

    if trades.empty:
        return {
            "metrics": {}, "returns": {}, "ratios": {}, 
            "risks": {}, "drawdowns": {}, "distributions": {}, 
            "efficiency": {}, "benchmark": {}, "summary": {}
        }

    # Pre-calculate common derived data
    equity = returns.equity_curve(trades, initial_balance, start_time=start_time, end_time=end_time)
    rets = returns.returns_series(equity)
    
    # Resolve benchmark if missing
    if benchmark_returns_series is None:
        proxy_prices = _extract_proxy_benchmark(trades)
        if proxy_prices is not None and len(proxy_prices) >= 2:
            benchmark_returns_series = proxy_prices.pct_change().dropna()
            benchmark_equity_series = (1 + benchmark_returns_series).cumprod() * initial_balance

    closed_trades = metrics.get_closed_trades(trades)
    open_trades = trades[~trades.index.isin(closed_trades.index)]

    # 1. Metrics (Trade-based statistics)
    metrics_data = {
        "total_trades": metrics.total_trades(closed_trades),
        "winning_trades": metrics.winning_trades(closed_trades),
        "losing_trades": metrics.losing_trades(closed_trades),
        "breakeven_trades": metrics.breakeven_trades(closed_trades),
        "long_trades": metrics.long_trades(closed_trades),
        "short_trades": metrics.short_trades(closed_trades),
        "open_trades": len(open_trades),
        "open_pnl": metrics.open_position_pnl(open_trades),
        "win_rate": metrics.win_rate(closed_trades),
        "loss_rate": metrics.loss_rate(closed_trades),
        "avg_win": metrics.avg_win(closed_trades),
        "avg_loss": metrics.avg_loss(closed_trades),
        "largest_win": metrics.largest_win(closed_trades),
        "largest_loss": metrics.largest_loss(closed_trades),
        "median_win": metrics.median_win(closed_trades),
        "median_loss": metrics.median_loss(closed_trades),
        "slippage_paid": metrics.slippage_paid(closed_trades),
        "commission_paid": metrics.commission_paid(closed_trades),
        "swap_paid": metrics.swap_paid(closed_trades),
        "avg_r_multiple": metrics.avg_r_multiple(closed_trades),
        "median_r_multiple": metrics.median_r_multiple(closed_trades),
        "max_r_multiple": metrics.max_r_multiple(closed_trades),
        "min_r_multiple": metrics.min_r_multiple(closed_trades),
        "max_consecutive_wins": metrics.max_consecutive_wins(closed_trades),
        "max_consecutive_losses": metrics.max_consecutive_losses(closed_trades),
        "avg_consecutive_wins": metrics.avg_consecutive_wins(closed_trades),
        "avg_consecutive_losses": metrics.avg_consecutive_losses(closed_trades),
        "avg_time_in_trade": metrics.avg_time_in_trade(closed_trades),
        "median_time_in_trade": metrics.median_time_in_trade(closed_trades),
        "max_time_in_trade": metrics.max_time_in_trade(closed_trades),
        "min_time_in_trade": metrics.min_time_in_trade(closed_trades),
        "median_mae_r": metrics.median_mae_r(closed_trades),
        "median_mfe_r": metrics.median_mfe_r(closed_trades),
        "sqn": metrics.sqn(closed_trades),
        "kelly_criterion": metrics.kelly_criterion(closed_trades),
        "time_in_market_hours": metrics.time_in_market_duration(closed_trades).total_seconds() / 3600.0,
        "percent_time_in_market": metrics.percent_time_in_market(closed_trades, start_time, end_time),
        "longest_flat_period_hours": metrics.longest_flat_period_duration(closed_trades, start_time, end_time).total_seconds() / 3600.0,
        "max_size_held": metrics.max_gross_size_held(closed_trades, end_time),
        "max_net_size_held": metrics.max_net_size_held(closed_trades, end_time),
        "max_long_size_held": metrics.max_long_size_held(closed_trades),
        "max_short_size_held": metrics.max_short_size_held(closed_trades),
        "t_statistic": metrics.t_statistic(closed_trades["profit_loss"]) if not closed_trades.empty else 0.0,
        "trade_efficiency": metrics.trade_efficiency(closed_trades),
        "r_signal_to_noise": metrics.r_signal_to_noise(closed_trades),
        "expectancy_variance": metrics.r_signal_to_noise(closed_trades),  # Compatibility key
        "rolling_expectancy_stability": metrics.rolling_expectancy_stability(closed_trades),
        "runs_test_zscore": metrics.runs_test_zscore(closed_trades),
        "win_after_win_probability": metrics.win_after_win_probability(closed_trades),
        "max_runup": returns.max_runup(equity),
        "median_mae": metrics.median_mae_r(closed_trades),
        "median_mfe": metrics.median_mfe_r(closed_trades),
        "trade_outcome_entropy": metrics.trade_outcome_entropy(closed_trades),
        "trading_period_duration_days": metrics.trading_period_duration(closed_trades, start_time, end_time).total_seconds() / 86400.0,
        "expectancy": metrics.expectancy(closed_trades),
        "expectancy_r": metrics.expectancy_r(metrics.get_r_multiples(closed_trades)),
    }

    # 2. Returns
    returns_data = {
        "net_profit": returns.net_profit(trades),
        "gross_profit": returns.gross_profit(trades),
        "gross_loss": returns.gross_loss(trades),
        "adjusted_net_profit": returns.adjusted_net_profit(trades),
        "select_net_profit": returns.select_net_profit(trades),
        "total_return": returns.total_return(equity),
        "total_return_usd": returns.total_return_usd(equity),
        "cagr": returns.cagr(equity),
        "annualized_return": returns.annualized_return(rets),
        "geometric_mean_return": returns.geometric_mean_return(rets),
        "cmgr": returns.compound_monthly_growth_rate(equity),
        "volatility": returns.return_volatility(rets),
        "downside_volatility": returns.downside_return_volatility(rets),
        "avg_monthly_return": returns.avg_monthly_return(equity),
        "monthly_return_stddev": returns.monthly_return_stddev(equity),
        "buy_and_hold_return": (
            returns.buy_and_hold_return(benchmark_equity_series)
            if benchmark_equity_series is not None else returns.buy_and_hold_return(_extract_proxy_benchmark(trades))
        ),
        "buy_and_hold_cagr": (
            returns.buy_and_hold_cagr(benchmark_equity_series)
            if benchmark_equity_series is not None else returns.buy_and_hold_cagr(_extract_proxy_benchmark(trades))
        ),
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
        "return_on_max_drawdown": returns.return_on_max_strategy_drawdown(equity),
        "return_on_max_c2c_drawdown": returns.return_on_max_close_to_close_drawdown(trades),
        "return_on_initial_capital": returns.return_on_initial_capital(trades, initial_balance),
        "max_runup": returns.max_runup(equity),
        "max_runup_date": returns.max_runup_date(equity),
        "best_return": returns.best_return(rets),
        "worst_return": returns.worst_return(rets),
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
        "expectancy_r": ratios.expectancy_r(metrics.get_r_multiples(trades)),
        "edge_ratio": ratios.edge_ratio(trades),
        "rina_index": ratios.rina_index(returns_data["select_net_profit"], drawdowns.avg_drawdown(equity), metrics_data["percent_time_in_market"]),
        "recovery_factor": drawdowns.recovery_factor(equity),
        "information_ratio": ratios.information_ratio(rets, benchmark_returns_series) if benchmark_returns_series is not None else 0.0,
        "sterling_ratio": ratios.sterling_ratio(returns_data["cagr"], drawdowns.avg_yearly_max_drawdown(equity)),
        "profit_to_mae_ratio": ratios.profit_to_mae_ratio(trades),
        "mfe_to_mae_ratio": ratios.mfe_to_mae_ratio(trades),
        "fouse_ratio": ratios.fouse_ratio(rets, risk_tolerance=2.0),
        "upside_potential_ratio": ratios.upside_potential_ratio(rets),
        "kappa_ratio": ratios.kappa_ratio(rets),
        "return_over_drawdown": ratios.return_over_drawdown(trades),
        "expectancy_over_std": ratios.expectancy_over_std(trades), 
        "adjusted_profit_factor": ratios.adjusted_profit_factor(trades),
        "select_profit_factor": ratios.select_profit_factor(trades),
        "net_profit_to_max_dd": ratios.net_profit_as_percent_of_max_strategy_drawdown(returns_data["net_profit"], drawdowns.max_strategy_drawdown(equity)),
    }

    # 4. Risks
    risks_data = {
        "volatility": risks.volatility(rets),
        "annualized_volatility": risks.annualized_volatility(rets),
        "value_at_risk_95": risks.value_at_risk(rets, confidence=0.95),
        "expected_shortfall_95": risks.expected_shortfall(rets, confidence=0.95),
        "risk_of_ruin": risks.risk_of_ruin(trades, risk_per_trade_pct=1.0),
        "max_exposure": risks.max_nominal_exposure_simple(trades),
        "avg_exposure": risks.avg_trade_nominal_exposure(trades),
        "downside_volatility_risk": risks.downside_volatility(rets),
        "max_loss_probability": risks.max_loss_probability(trades),
        "drawdown_probability_10pct": risks.drawdown_probability(rets, threshold_pct=10.0),
        "exposure_time_ratio": risks.exposure_time_ratio(trades, start_time, end_time),
        "max_gross_exposure": risks.max_gross_exposure(trades),
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
        "account_size_required": drawdowns.account_size_required(trades),
        "pain_ratio": drawdowns.pain_ratio(equity),
        "max_drawdown_date": drawdowns.max_strategy_drawdown_date(equity).isoformat() if not equity.empty and drawdowns.max_strategy_drawdown_date(equity) is not None else None,
        "max_close_to_close_drawdown_date": drawdowns.max_close_to_close_drawdown_date(trades).isoformat() if not trades.empty and drawdowns.max_close_to_close_drawdown_date(trades) is not None else None,
        "drawdown_distribution": drawdowns.drawdown_distribution(equity),
        "time_to_recovery_periods": [str(_periods_to_timedelta(p, equity.index)) for p in drawdowns.time_to_recovery(equity)],
        "avg_trade_drawdown": drawdowns.avg_trade_drawdown(trades),
        "max_consecutive_drawdown_trades": drawdowns.max_consecutive_drawdown_trades(trades),
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
        "jarque_bera_p_value": distributions.jarque_bera_test(rets).get("p_value", 0.0),
        "shapiro_wilk": distributions.shapiro_wilk_test(rets),
        "shapiro_wilk_p_value": distributions.shapiro_wilk_test(rets).get("p_value", 0.0),
        "is_normal_jb": distributions.jarque_bera_test(rets).get("p_value", 0.0) > 0.05,
        "is_normal_sw": distributions.shapiro_wilk_test(rets).get("p_value", 0.0) > 0.05,
        "fat_tail_score": distributions.fat_tail_score(rets),
        "tail_ratio": distributions.tail_ratio(rets),
        "higher_moments": distributions.higher_moments(rets),
        "percentiles": distributions.percentile_summary(rets),
        "upside_downside": distributions.upside_downside_summary(rets),
        "histogram": distributions.histogram_data(rets),
        "fit_quality": {
            "norm": distributions.distribution_fit_quality(rets, "norm"),
            "t": distributions.distribution_fit_quality(rets, "t"),
            "best_model": "Normal" if (distributions.distribution_fit_quality(rets, "norm").get("aic", 0) < distributions.distribution_fit_quality(rets, "t").get("aic", 0)) else "T-Distribution"
        }
    }

    # 7. Efficiency
    efficiency_data = {
        "capital_efficiency": efficiency.capital_efficiency(trades),
        "avg_trade_notional_efficiency": efficiency.avg_trade_notional_efficiency(trades),
        "return_per_unit_mae": efficiency.return_per_unit_mae(trades),
        "risk_adjusted_efficiency": efficiency.risk_adjusted_efficiency(trades),
        "avg_return_per_risk_unit": efficiency.avg_return_per_risk_unit(trades),
        "return_per_trade_hour": efficiency.return_per_trade_hour(trades),
        "return_per_market_hour": efficiency.return_per_market_hour(trades, end_time),
        "return_per_calendar_day": efficiency.return_per_calendar_day(trades, start_time, end_time),
        "trades_per_day": efficiency.trades_per_day(trades, start_time, end_time),
        "profit_per_trade_per_day": efficiency.profit_per_trade_per_day(trades, start_time, end_time),
        "mfe_efficiency": efficiency.mfe_efficiency(trades),
        "aggregate_mfe_capture_ratio": efficiency.aggregate_mfe_capture_ratio(trades),
        "mae_efficiency": efficiency.mae_efficiency(trades),
        "exit_efficiency": efficiency.exit_efficiency(trades),
        "loss_containment_efficiency": efficiency.loss_containment_efficiency(trades),
        "aggregate_loss_containment_efficiency": efficiency.aggregate_loss_containment_efficiency(trades),
        "position_size_efficiency": efficiency.position_size_efficiency(trades),
        "profit_per_pip_risk": efficiency.profit_per_pip_risk(trades),
        
        # Backward compatibility aliases for UI
        "return_per_unit_risk": efficiency.return_per_unit_mae(trades),
        "return_per_r_risk": efficiency.avg_return_per_risk_unit(trades),
        "time_efficiency": efficiency.return_per_trade_hour(trades),
        "return_per_unit_time": efficiency.return_per_market_hour(trades, end_time),
        "return_per_trade_opportunity": efficiency.return_per_calendar_day(trades, start_time, end_time),
        "return_per_trade": metrics_data.get("expectancy", 0.0),
        "win_efficiency": efficiency.aggregate_mfe_capture_ratio(trades) * 100.0,  # Convert to % for UI
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
            "relative_drawdown": benchmark.max_relative_drawdown_percent(equity, benchmark_equity_series),
            "information_ratio": ratios.information_ratio(rets, benchmark_returns_series),
            "cagr": returns.cagr(benchmark_equity_series),
            "total_return": returns.buy_and_hold_return(benchmark_equity_series),
        }

    # 9. Statistical Validation
    validation_data = {}
    if not closed_trades.empty:
        # P-values and DSR
        dsr_val, dsr_p = statistical_tests.deflated_sharpe_ratio(
            observed_sharpe=ratios_data["sharpe_ratio"],
            n_trials=10, # Conservative default
            n_observations=len(rets),
            skew=distributions_data["skewness"],
            kurt=distributions_data["kurtosis"] + 3.0 # convert excess to normal
        )
        
        perm_test = statistical_tests.permutation_test(rets, n_permutations=500)
        
        validation_data = {
            "deflated_sharpe_ratio": dsr_val,
            "dsr_p_value": dsr_p,
            "permutation_p_value": perm_test.p_value,
            "is_significant": perm_test.is_significant,
            "prob_sharpe_gt_0": statistical_tests.bootstrap_probability_above_threshold(rets, lambda r: ratios.sharpe_ratio(r), threshold=0.0),
            "prob_return_gt_0": statistical_tests.bootstrap_probability_above_threshold(rets, lambda r: np.sum(r), threshold=0.0),
        }

    # 10. Summary (Overview table style)
    summary_data = {
        "start": start_time.isoformat() if start_time else None,
        "end": end_time.isoformat() if end_time else None,
        "duration_days": (end_time - start_time).total_seconds() / 86400.0 if start_time and end_time else 0,
        "equity_final": float(equity.iloc[-1]) if not equity.empty else initial_balance,
        "equity_peak": float(equity.max()) if not equity.empty else initial_balance,
        "total_return": float(returns_data["total_return"]),
        "return_usd": float(returns_data["net_profit"]),
        "return_pct": float(returns_data["net_profit"] / initial_balance * 100.0) if initial_balance > 0 else 0.0,
        "buy_hold_return_pct": float(returns_data["buy_and_hold_return"]),
        "num_trades": int(metrics_data["total_trades"]),
        "win_rate_pct": float(metrics_data["win_rate"]),
        "best_trade_pct": float((trades["profit_loss"] / initial_balance * 100.0).max()) if not trades.empty and initial_balance > 0 else 0.0,
        "worst_trade_pct": float((trades["profit_loss"] / initial_balance * 100.0).min()) if not trades.empty and initial_balance > 0 else 0.0,
        "avg_trade_pct": float((trades["profit_loss"] / initial_balance * 100.0).mean()) if not trades.empty and initial_balance > 0 else 0.0,
        "exposure_time_pct": float(metrics_data["percent_time_in_market"]),
        "time_in_market": _format_duration(metrics_data["time_in_market_hours"]),
        "longest_flat_period": _format_duration(metrics_data["longest_flat_period_hours"]),
        "max_trade_duration": _format_duration((pd.to_datetime(trades["close_time"]) - pd.to_datetime(trades["open_time"])).max()) if not trades.empty else "0h",
        "avg_trade_duration": _format_duration((pd.to_datetime(trades["close_time"]) - pd.to_datetime(trades["open_time"])).mean()) if not trades.empty else "0h",
        "max_drawdown_pct": float(drawdowns_data["max_drawdown_pct"]),
        "avg_drawdown_pct": float(drawdowns.avg_underwater_drawdown_percent(equity)),
        "max_drawdown_duration": _format_duration(drawdowns_data["max_drawdown_duration"]),
        "avg_drawdown_duration": _format_duration(drawdowns_data["avg_drawdown_duration"]),
        "value_at_risk_95": float(risks_data["value_at_risk_95"]),
        "expectancy_pct": float(ratios_data["expectancy"] / initial_balance * 100.0) if initial_balance > 0 else 0.0,
        "expectancy_r": float(ratios_data["expectancy_r"]),
        "profit_factor": float(ratios_data["profit_factor"]),
        "sharpe_ratio": float(ratios_data["sharpe_ratio"]),
        "sortino_ratio": float(ratios_data["sortino_ratio"]),
        "calmar_ratio": float(ratios_data["calmar_ratio"]),
        "alpha": float(benchmark_data.get("alpha", 0.0)),
        "beta": float(benchmark_data.get("beta", 0.0)),
        "cagr": float(returns_data["cagr"]),
        "annual_return": float(returns_data["annualized_return"]),
        "annual_volatility": float(returns_data["volatility"]),
        "risk_of_ruin": float(metrics_data.get("risk_of_ruin", 0.0)),
        "max_exposure": float(metrics_data.get("max_exposure", 0.0)),
        "ulcer_index": float(drawdowns_data.get("ulcer_index", 0.0)),
        "sqn": float(metrics_data.get("sqn", 0.0)),
        "kelly_criterion": float(metrics_data.get("kelly_criterion", 0.0)),
    }

    return {
        "summary": summary_data,
        "metrics": metrics_data,
        "returns": returns_data,
        "ratios": ratios_data,
        "risks": risks_data,
        "drawdowns": drawdowns_data,
        "distributions": distributions_data,
        "efficiency": efficiency_data,
        "benchmark": benchmark_data,
        "validation": validation_data,
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
    categories = ["metrics", "returns", "ratios", "risks", "drawdowns", "distributions", "efficiency", "benchmark", "validation", "summary"]
    for cat in categories:
        final_output[cat] = {"all": results_all.get(cat, {}), "long": results_long.get(cat, {}), "short": results_short.get(cat, {})}
        
    def _to_python_types(obj, key=None):
        if isinstance(obj, dict): return {k: _to_python_types(v, k) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)): return [_to_python_types(x, key) for x in obj]
        
        # Datetime & Timedelta
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, (pd.Timedelta, pd._libs.tslibs.timedeltas.Timedelta)):
            return str(obj)
            
        # Float rounding
        if isinstance(obj, (float, np.float64, np.float32)):
            val = float(obj)
            if not np.isfinite(val): return 0.0
            if key and any(s in key.lower() for s in ["_usd", "_final", "_peak", "pnl", "_profit", "_loss", "balance", "equity"]):
                return round(val, 2)
            return round(val, 5)
            
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
        ("Num of Ticks", str(summary_data.get("processed_ticks", 0))),
        ("Win Rate [%]", _fmt_num(summary_data.get("win_rate_pct"), 5)),
        ("Best Trade [%]", _fmt_num(summary_data.get("best_trade_pct"), 5)),
        ("Worst Trade [%]", _fmt_num(summary_data.get("worst_trade_pct"), 5)),
        ("Avg. Trade [%]", _fmt_num(summary_data.get("avg_trade_pct"), 5)),
        ("Exposure Time [%]", _fmt_num(summary_data.get("exposure_time_pct"), 5)),
        ("Time in Market", str(summary_data.get("time_in_market", "0h"))),
        ("Longest Flat Period", str(summary_data.get("longest_flat_period", "0h"))),
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
        ("Kelly Criterion [%]", _fmt_num(summary_data.get("kelly_criterion"), 5)),
    ]


def _get_dashboard_metrics(analytics: dict[str, Any]) -> dict[str, Any]:
    """Extract a curated set of key performance indicators for the primary dashboard, with Long/Short support."""
    
    def get_3way(cat, key, default=0.0):
        category_data = analytics.get(cat, {})
        return {
            "all": category_data.get("all", {}).get(key, default),
            "long": category_data.get("long", {}).get(key, default),
            "short": category_data.get("short", {}).get(key, default),
        }

    # Helper to merge multiple 3-way metrics into a category object
    def build_category(cat_configs):
        # cat_configs is list of (dashboard_key, cat_name, metric_key)
        out = {"all": {}, "long": {}, "short": {}}
        for dashboard_key, cat_name, metric_key in cat_configs:
            m3 = get_3way(cat_name, metric_key)
            out["all"][dashboard_key] = m3["all"]
            out["long"][dashboard_key] = m3["long"]
            out["short"][dashboard_key] = m3["short"]
        return out

    return {
        "profitability": build_category([
            ("net_profit", "returns", "net_profit"),
            ("total_return", "returns", "total_return"),
            ("cagr", "returns", "cagr"),
            ("profit_factor", "ratios", "profit_factor"),
            ("expectancy_r", "ratios", "expectancy_r"),
        ]),
        "risk": build_category([
            ("max_drawdown_pct", "drawdowns", "max_drawdown_pct"),
            ("max_drawdown_duration", "drawdowns", "max_drawdown_duration"),
            ("value_at_risk_95", "risks", "value_at_risk_95"),
            ("expected_shortfall_95", "risks", "expected_shortfall_95"),
            ("ulcer_index", "drawdowns", "ulcer_index"),
            ("risk_of_ruin", "risks", "risk_of_ruin"),
        ]),
        "quality": build_category([
            ("sharpe_ratio", "ratios", "sharpe_ratio"),
            ("sortino_ratio", "ratios", "sortino_ratio"),
            ("calmar_ratio", "ratios", "calmar_ratio"),
            ("sqn", "metrics", "sqn"),
            ("kelly_criterion", "metrics", "kelly_criterion"),
            ("win_rate", "metrics", "win_rate"),
        ]),
        "robustness": build_category([
            ("deflated_sharpe_ratio", "validation", "deflated_sharpe_ratio"),
            ("dsr_p_value", "validation", "dsr_p_value"),
            ("prob_sharpe_gt_0", "validation", "prob_sharpe_gt_0"),
        ]),
        "efficiency": build_category([
            ("aggregate_mfe_capture_ratio", "efficiency", "aggregate_mfe_capture_ratio"),
            ("aggregate_loss_containment_efficiency", "efficiency", "aggregate_loss_containment_efficiency"),
            ("percent_time_in_market", "metrics", "percent_time_in_market"),
            ("capital_efficiency", "efficiency", "capital_efficiency"),
        ]),
        "benchmark": build_category([
            ("alpha", "benchmark", "alpha"),
            ("beta", "benchmark", "beta"),
            ("information_ratio", "ratios", "information_ratio"),
            ("up_capture", "benchmark", "up_capture"),
            ("down_capture", "benchmark", "down_capture"),
        ]),
    }


def build_overview_payload(
    trades: Any,
    initial_balance: float,
    start_time: Any = None,
    end_time: Any = None,
    equity_curve_records: Optional[list[Any]] = None,
    summary_overrides: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the full analytics payload for the API including charts."""
    df = _normalize_trades(trades)
    
    # 1. Calculate base analytics (get_analytics_overview already handles All/Long/Short)
    analytics = get_analytics_overview(df, initial_balance, start_time, end_time)
    
    # 2. Extract structured summary
    summary = analytics.get("summary", {"all": {}, "long": {}, "short": {}})
    
    # 3. Apply overrides (e.g. processed_ticks) specifically to the 'all' category
    if summary_overrides:
        summary["all"].update(summary_overrides)

    # 4. Prepare metric categories for the payload (already structured by get_analytics_overview)
    categories = ["metrics", "returns", "ratios", "risks", "drawdowns", "distributions", "efficiency", "benchmark", "validation"]
    payload_categories = {cat: analytics.get(cat, {}) for cat in categories}

    # Generate Curves for Charts
    def _get_subset_curves(subset_df):
        if subset_df.empty:
            return pd.Series(dtype=float), pd.Series(dtype=float)
        equity = returns.equity_curve(subset_df, initial_balance)
        raw_dd = drawdowns.drawdown_series(equity)
        
        # Calculate absolute percentage drawdown (0 to 100%)
        # peak = equity - raw_dd (since raw_dd is negative)
        peak = equity - raw_dd
        dd_pct = (abs(raw_dd) / peak.replace(0, 1e-9)) * 100
        
        return equity, dd_pct

    eq_all, dd_all = _get_subset_curves(df)
    eq_long, dd_long = _get_subset_curves(df[df["type"] == "buy"])
    eq_short, dd_short = _get_subset_curves(df[df["type"] == "sell"])

    # Merge into 3-way format for unified charts
    def _merge_to_list(all_s, long_s, short_s, val_key):
        all_indices = sorted(set(all_s.index) | set(long_s.index) | set(short_s.index))
        if not all_indices: return []
        a = all_s.reindex(all_indices).ffill().fillna(initial_balance if "equity" in val_key else 0)
        l = long_s.reindex(all_indices).ffill().fillna(initial_balance if "equity" in val_key else 0)
        s = short_s.reindex(all_indices).ffill().fillna(initial_balance if "equity" in val_key else 0)
        return [{"date": ts.isoformat(), "all": float(a.loc[ts]), "long": float(l.loc[ts]), "short": float(s.loc[ts])} for ts in all_indices]

    equity_chart = _merge_to_list(eq_all, eq_long, eq_short, "equity")
    drawdown_chart = _merge_to_list(dd_all, dd_long, dd_short, "drawdown")

    # 5. Generate Decision Scorecard
    scorecard = {
        "all": decision_scorecard.evaluate_strategy_quality({
            "summary": summary,
            "metrics": payload_categories["metrics"],
            "ratios": payload_categories["ratios"],
            "drawdowns": payload_categories["drawdowns"],
            "validation": payload_categories["validation"]
        })
    }

    # 6. Extract Dashboard Metrics
    dashboard = _get_dashboard_metrics(analytics)

    return {
        "summary": summary,
        "dashboard": dashboard,
        **payload_categories,
        "scorecard": scorecard,
        "equity_curves": {
            "all": [{"date": ts.isoformat(), "equity": float(v)} for ts, v in eq_all.items()],
            "long": [{"date": ts.isoformat(), "equity": float(v)} for ts, v in eq_long.items()],
            "short": [{"date": ts.isoformat(), "equity": float(v)} for ts, v in eq_short.items()],
        },
        "charts": {
            "equity_curve": equity_chart,
            "drawdown_curve": drawdown_chart
        }
    }
