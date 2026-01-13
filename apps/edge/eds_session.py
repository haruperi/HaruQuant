"""EDS-3: Session Edge Detector.

Hypothesis: The symbol behaves differently by session (London/NY/Asia).

This detector:
1. Buckets returns by session
2. Computes conditional statistics per session
3. Tests session-specific micro-strategies
4. Applies FDR correction for multiple testing

Session-based strategies tested:
- London opening range breakout
- Asia range fade
- NY momentum continuation
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from apps.logger import logger

from .config import BootstrapConfig, PermutationConfig, SessionConfig, SessionEdgeConfig
from .datasets import tag_sessions
from .features import atr
from .metrics import expectancy, median_mae_mfe, profit_factor, win_rate
from .null_models import (
    benjamini_hochberg,
    block_bootstrap_ci,
    permutation_test,
    session_randomized_null,
)
from .results_schema import EdgeResult, EdgeStats, TradeSample


def compute_session_statistics(
    df: pd.DataFrame,
    session: str,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> Dict[str, float]:
    """Compute detailed statistics for a specific session.

    Args:
        df: DataFrame with session column
        session: Session name to analyze
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        Dictionary of session statistics
    """
    session_df = df[df["session"] == session].copy()

    if len(session_df) < 10:
        return {
            "n_bars": len(session_df),
            "mean_return": float("nan"),
            "volatility": float("nan"),
            "skew": float("nan"),
            "avg_range": float("nan"),
        }

    session_df["returns"] = np.log(
        session_df[close_col] / session_df[close_col].shift(1)
    )
    session_df["range"] = session_df[high_col] - session_df[low_col]

    returns = session_df["returns"].dropna()

    return {
        "n_bars": len(session_df),
        "mean_return": float(returns.mean()),
        "volatility": float(returns.std()),
        "skew": float(returns.skew()) if len(returns) > 2 else float("nan"),
        "avg_range": float(session_df["range"].mean()),
        "positive_return_rate": float((returns > 0).mean()),
    }


def run_session_breakout_strategy(  # noqa: C901
    df: pd.DataFrame,
    session: str,
    opening_range_bars: int,
    hold_bars: int,
    k_stop_atr: float,
    atr_series: pd.Series,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> List[TradeSample]:
    """Run opening range breakout strategy for a session.

    Entry: Break of session opening range (first N bars)
    Exit: Time stop or reversal

    Args:
        df: DataFrame with session column
        session: Target session
        opening_range_bars: Bars to define opening range
        hold_bars: Maximum holding period
        k_stop_atr: Stop distance multiplier
        atr_series: ATR series
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        List of trade samples
    """
    if "session" not in df.columns:
        df = tag_sessions(df)

    trades: List[TradeSample] = []
    close = df[close_col].values
    high = df[high_col].values
    low = df[low_col].values
    sessions = df["session"].values
    n = len(df)

    # Find session starts
    session_starts = []
    for i in range(1, n):
        if sessions[i] == session and sessions[i - 1] != session:
            session_starts.append(i)

    for start in session_starts:
        if start + opening_range_bars + hold_bars >= n:
            continue

        # Compute opening range
        range_end = start + opening_range_bars
        range_high = np.max(high[start:range_end])
        range_low = np.min(low[start:range_end])

        # Look for breakout after opening range
        for i in range(range_end, min(range_end + 20, n - hold_bars)):
            if sessions[i] != session:
                break  # Session ended

            atr_i = atr_series.iloc[i]
            if not np.isfinite(atr_i) or atr_i <= 0:
                continue

            stop_dist = k_stop_atr * atr_i
            side: Optional[str] = None

            if close[i] > range_high:
                side = "BUY"
            elif close[i] < range_low:
                side = "SELL"

            if side is None:
                continue

            entry_price = close[i]
            exit_i = min(i + hold_bars, n - 1)
            exit_price = close[exit_i]

            pnl = (
                (exit_price - entry_price)
                if side == "BUY"
                else (entry_price - exit_price)
            )
            r_mult = pnl / stop_dist

            segment = close[i : exit_i + 1]
            if side == "BUY":
                mae = (np.min(segment) - entry_price) / stop_dist
                mfe = (np.max(segment) - entry_price) / stop_dist
            else:
                mae = (entry_price - np.max(segment)) / stop_dist
                mfe = (entry_price - np.min(segment)) / stop_dist

            trades.append(
                TradeSample(
                    entry_time=df.index[i],
                    exit_time=df.index[exit_i],
                    side=side,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    r_multiple=float(r_mult),
                    mae_r=float(mae),
                    mfe_r=float(mfe),
                    hold_bars=int(exit_i - i),
                    meta={
                        "session": session,
                        "strategy": "opening_range_breakout",
                        "range_high": range_high,
                        "range_low": range_low,
                    },
                )
            )

            break  # One trade per session start

    return trades


def run_session_fade_strategy(  # noqa: C901
    df: pd.DataFrame,
    session: str,
    hold_bars: int,
    k_stop_atr: float,
    atr_series: pd.Series,
    zscore_threshold: float = 2.0,
    close_col: str = "Close",
) -> List[TradeSample]:
    """Run mean-reversion fade strategy within session.

    Entry: Extended z-score within session
    Exit: Mean reversion or time stop

    Args:
        df: DataFrame with session column
        session: Target session
        hold_bars: Maximum holding period
        k_stop_atr: Stop distance multiplier
        atr_series: ATR series
        zscore_threshold: Z-score threshold for entry
        close_col: Close column name

    Returns:
        List of trade samples
    """
    if "session" not in df.columns:
        df = tag_sessions(df)

    # Compute session-relative z-score
    df = df.copy()
    df["session_sma"] = df.groupby("session")[close_col].transform(
        lambda x: x.rolling(20, min_periods=5).mean()
    )
    df["session_std"] = df.groupby("session")[close_col].transform(
        lambda x: x.rolling(20, min_periods=5).std()
    )
    df["session_z"] = (df[close_col] - df["session_sma"]) / df["session_std"]

    trades: List[TradeSample] = []
    close = df[close_col].values
    z_scores = df["session_z"].values
    sessions = df["session"].values
    n = len(df)

    i = 50  # Skip warmup
    while i < n - hold_bars - 1:
        if sessions[i] != session:
            i += 1
            continue

        z = z_scores[i]
        if not np.isfinite(z):
            i += 1
            continue

        atr_i = atr_series.iloc[i]
        if not np.isfinite(atr_i) or atr_i <= 0:
            i += 1
            continue

        side: Optional[str] = None
        if z <= -zscore_threshold:
            side = "BUY"  # Oversold, expect reversion up
        elif z >= zscore_threshold:
            side = "SELL"  # Overbought, expect reversion down

        if side is None:
            i += 1
            continue

        entry_price = close[i]
        stop_dist = k_stop_atr * atr_i

        # Exit on mean reversion or time stop
        exit_i = None
        for j in range(1, hold_bars + 1):
            if i + j >= n:
                break
            zf = z_scores[i + j]
            if side == "BUY" and zf >= 0:
                exit_i = i + j
                break
            if side == "SELL" and zf <= 0:
                exit_i = i + j
                break

        if exit_i is None:
            exit_i = min(i + hold_bars, n - 1)

        exit_price = close[exit_i]
        pnl = (
            (exit_price - entry_price) if side == "BUY" else (entry_price - exit_price)
        )
        r_mult = pnl / stop_dist

        segment = close[i : exit_i + 1]
        if side == "BUY":
            mae = (np.min(segment) - entry_price) / stop_dist
            mfe = (np.max(segment) - entry_price) / stop_dist
        else:
            mae = (entry_price - np.max(segment)) / stop_dist
            mfe = (entry_price - np.min(segment)) / stop_dist

        trades.append(
            TradeSample(
                entry_time=df.index[i],
                exit_time=df.index[exit_i],
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                r_multiple=float(r_mult),
                mae_r=float(mae),
                mfe_r=float(mfe),
                hold_bars=int(exit_i - i),
                meta={
                    "session": session,
                    "strategy": "session_fade",
                    "z_entry": z,
                },
            )
        )

        i = exit_i + 1

    return trades


def run_eds_session(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    cfg: SessionEdgeConfig,
    sessions_cfg: SessionConfig,
    boot: BootstrapConfig,
    perm: PermutationConfig,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> EdgeResult:
    """EDS-3: Session Edge Detector.

    Analyzes time-of-day alpha and tests session-specific strategies.
    Applies FDR correction for multiple hypothesis testing.

    Args:
        df: OHLC DataFrame
        symbol: Trading symbol
        timeframe: Timeframe string
        cfg: Session edge configuration
        sessions_cfg: Session hour definitions
        boot: Bootstrap configuration
        perm: Permutation configuration
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        EdgeResult with session analysis and trades
    """
    logger.info(f"Running EDS-3 Session Edge for {symbol} {timeframe}")

    # Tag sessions
    out = tag_sessions(
        df.copy(),
        asia_hours=sessions_cfg.asia_hours,
        london_hours=sessions_cfg.london_hours,
        ny_hours=sessions_cfg.ny_hours,
        off_hours=sessions_cfg.off_hours,
    )

    # Compute ATR
    out["atr"] = atr(out, cfg.atr_n, high_col, low_col, close_col)
    atr_series = out["atr"]

    # ==========================================================================
    # STEP 1: Compute session statistics
    # ==========================================================================
    session_stats: Dict[str, Dict] = {}
    for session in cfg.sessions:
        session_stats[session] = compute_session_statistics(
            out, session, close_col, high_col, low_col
        )

    logger.debug(f"Session statistics: {session_stats}")

    # ==========================================================================
    # STEP 2: Run session strategies and collect trades
    # ==========================================================================
    all_trades: List[TradeSample] = []
    strategy_results: Dict[str, Dict] = {}
    p_values: List[float] = []
    hypothesis_names: List[str] = []

    for session in cfg.sessions:
        # Opening range breakout
        if cfg.analyze_breakouts:
            breakout_trades = run_session_breakout_strategy(
                out,
                session=session,
                opening_range_bars=cfg.opening_range_bars,
                hold_bars=cfg.hold_bars,
                k_stop_atr=cfg.k_stop_atr,
                atr_series=atr_series,
                close_col=close_col,
                high_col=high_col,
                low_col=low_col,
            )

            if len(breakout_trades) >= cfg.min_trades_per_session:
                r_vals = np.array([t.r_multiple for t in breakout_trades])
                exp = expectancy(r_vals)

                # Bootstrap CI
                ci_low, ci_high = block_bootstrap_ci(
                    r_vals,
                    statistic=lambda x: float(np.mean(x)),
                    n_boot=boot.n_boot,
                    block_size=boot.block_size,
                    ci_level=boot.ci_level,
                    seed=boot.seed,
                )

                # Null test
                entry_indices = np.array(
                    [out.index.get_loc(t.entry_time) for t in breakout_trades]
                )
                null_dist = session_randomized_null(
                    out,
                    entry_indices=entry_indices,
                    hold_bars=cfg.hold_bars,
                    side="BUY",
                    k_stop_atr=cfg.k_stop_atr,
                    atr_series=atr_series,
                    n_perm=perm.n_perm,
                    seed=perm.seed,
                    close_col=close_col,
                )
                pval = (
                    permutation_test(exp, null_dist)
                    if len(null_dist) > 0
                    else float("nan")
                )

                strategy_results[f"{session}_breakout"] = {
                    "n_trades": len(breakout_trades),
                    "expectancy": exp,
                    "win_rate": win_rate(r_vals),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "p_value": pval,
                }

                p_values.append(pval if np.isfinite(pval) else 1.0)
                hypothesis_names.append(f"{session}_breakout")
                all_trades.extend(breakout_trades)

        # Session fade (mean reversion)
        if cfg.analyze_reversals:
            fade_trades = run_session_fade_strategy(
                out,
                session=session,
                hold_bars=cfg.hold_bars,
                k_stop_atr=cfg.k_stop_atr,
                atr_series=atr_series,
                close_col=close_col,
            )

            if len(fade_trades) >= cfg.min_trades_per_session:
                r_vals = np.array([t.r_multiple for t in fade_trades])
                exp = expectancy(r_vals)

                ci_low, ci_high = block_bootstrap_ci(
                    r_vals,
                    statistic=lambda x: float(np.mean(x)),
                    n_boot=boot.n_boot,
                    block_size=boot.block_size,
                    ci_level=boot.ci_level,
                    seed=boot.seed,
                )

                entry_indices = np.array(
                    [out.index.get_loc(t.entry_time) for t in fade_trades]
                )
                null_dist = session_randomized_null(
                    out,
                    entry_indices=entry_indices,
                    hold_bars=cfg.hold_bars,
                    side="BUY",
                    k_stop_atr=cfg.k_stop_atr,
                    atr_series=atr_series,
                    n_perm=perm.n_perm,
                    seed=perm.seed,
                    close_col=close_col,
                )
                pval = (
                    permutation_test(exp, null_dist)
                    if len(null_dist) > 0
                    else float("nan")
                )

                strategy_results[f"{session}_fade"] = {
                    "n_trades": len(fade_trades),
                    "expectancy": exp,
                    "win_rate": win_rate(r_vals),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "p_value": pval,
                }

                p_values.append(pval if np.isfinite(pval) else 1.0)
                hypothesis_names.append(f"{session}_fade")
                all_trades.extend(fade_trades)

    # ==========================================================================
    # STEP 3: FDR correction for multiple testing
    # ==========================================================================
    if len(p_values) > 0:
        significant = benjamini_hochberg(np.array(p_values), q=0.10)
        for i, name in enumerate(hypothesis_names):
            strategy_results[name]["significant_after_fdr"] = bool(significant[i])
            logger.debug(
                f"{name}: p={p_values[i]:.4f}, FDR significant={significant[i]}"
            )
    else:
        logger.warning("No strategies had enough trades for analysis")

    # ==========================================================================
    # STEP 4: Compute aggregate stats
    # ==========================================================================
    if len(all_trades) > 0:
        r = np.array([t.r_multiple for t in all_trades])
        mae = np.array([t.mae_r for t in all_trades])
        mfe = np.array([t.mfe_r for t in all_trades])
        hold = np.array([t.hold_bars for t in all_trades])

        exp_r = expectancy(r)
        wr = win_rate(r)
        pf = profit_factor(r)
        med_mae, med_mfe = median_mae_mfe(mae, mfe)
        avg_hold = float(np.mean(hold))

        ci_low, ci_high = block_bootstrap_ci(
            r,
            statistic=lambda x: float(np.mean(x)),
            n_boot=boot.n_boot,
            block_size=boot.block_size,
            ci_level=boot.ci_level,
            seed=boot.seed,
        )

        # Overall p-value (combined)
        overall_pval = (
            min(p_values) * len(p_values) if p_values else float("nan")
        )  # Bonferroni approximation
    else:
        exp_r = wr = pf = avg_hold = float("nan")
        med_mae = med_mfe = float("nan")
        ci_low = ci_high = float("nan")
        overall_pval = float("nan")

    stats = EdgeStats(
        n_trades=len(all_trades),
        expectancy_r=float(exp_r) if np.isfinite(exp_r) else float("nan"),
        win_rate=float(wr) if np.isfinite(wr) else float("nan"),
        profit_factor=float(pf),
        median_mae_r=float(med_mae),
        median_mfe_r=float(med_mfe),
        avg_hold_bars=float(avg_hold) if np.isfinite(avg_hold) else float("nan"),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        p_value_perm=float(overall_pval),
        extras={
            "session_stats": session_stats,
            "strategy_results": strategy_results,
            "sessions_analyzed": list(cfg.sessions),
            "n_hypotheses_tested": len(hypothesis_names),
        },
    )

    logger.info(
        f"EDS-3 complete: {len(all_trades)} trades across {len(cfg.sessions)} sessions"
    )

    return EdgeResult(
        symbol=symbol,
        timeframe=timeframe,
        eds_name="EDS-3 SessionEdge",
        config=asdict(cfg),
        stats=stats,
        trades=all_trades,
    )
