"""EDS-2 trend persistence edge discovery strategy."""

from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

import numpy as np
import pandas as pd

from apps.utils.logger import logger

from .config import BootstrapConfig, PermutationConfig, TrendPersistenceConfig
from .features import adr, rolling_percentile_rank
from .metrics import expectancy, median_mae_mfe, profit_factor, win_rate
from .null_models import block_bootstrap_ci, permutation_test, r_space_null
from .results_schema import EdgeResult, EdgeStats, TradeSample


def run_eds_trend_persistence(  # noqa: C901
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    cfg: TrendPersistenceConfig,
    boot: BootstrapConfig,
    perm: PermutationConfig,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> EdgeResult:
    """EDS-2 Trend Persistence Detector: high-ATR breakout follow-through.

    Hypothesis: After breakout in high-vol regime, returns show persistence.

    Entry Conditions:
    - High ATR regime (ATR percentile >= q_high)
    - Price breaks N-bar high/low

    Exit: Target hit (k*ATR), time stop, or opposite breakout

    Args:
        df: OHLC DataFrame
        symbol: Trading symbol
        timeframe: Timeframe string
        cfg: Trend persistence configuration
        boot: Bootstrap configuration
        perm: Permutation configuration
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        EdgeResult with trades and statistics
    """
    logger.info(f"Running EDS-2 Trend Persistence for {symbol} {timeframe}")
    out = df.copy()
    close = out[close_col].astype(float)
    high = out[high_col].astype(float)
    low = out[low_col].astype(float)

    adr_n = 10

    def _daily_adr_series(df: pd.DataFrame) -> pd.Series:
        daily = df.resample("1D").agg(
            {high_col: "max", low_col: "min", close_col: "last"}
        )
        daily = daily.dropna(subset=[high_col, low_col, close_col])
        daily["adr"] = adr(daily, adr_n, high_col=high_col, low_col=low_col)
        adr_series = daily["adr"].shift(1)
        adr_series = adr_series.reindex(df.index, method="ffill")
        return adr_series

    out["adr"] = _daily_adr_series(out)
    out["atr_rank"] = rolling_percentile_rank(out["adr"], cfg.atr_regime_window)

    trades: List[TradeSample] = []
    i = max(cfg.atr_regime_window, cfg.breakout_n, cfg.atr_n) + 1

    while i < len(out) - cfg.max_hold_bars - 2:
        atr_rank = float(out["atr_rank"].iloc[i])
        if not np.isfinite(atr_rank) or atr_rank < cfg.atr_q_high:
            i += 1
            continue

        prev_hi = float(high.iloc[i - cfg.breakout_n : i].max())
        prev_lo = float(low.iloc[i - cfg.breakout_n : i].min())
        px = float(close.iloc[i])

        side: Optional[str] = None
        if px > prev_hi:
            side = "BUY"
        elif px < prev_lo:
            side = "SELL"

        if side is None:
            i += 1
            continue

        entry_price = px
        adr_i = float(out["adr"].iloc[i])
        adr_session = adr_i / 3 if timeframe.upper() != "D1" else adr_i
        stop_dist = cfg.k_stop_atr * adr_session
        if stop_dist <= 0 or not np.isfinite(stop_dist):
            i += 1
            continue

        exit_i = i + cfg.max_hold_bars
        segment = close.iloc[i : exit_i + 1].values

        if side == "BUY":
            target = entry_price + cfg.k_target_atr * adr_session
            hit = np.where(segment >= target)[0]
            if len(hit):
                exit_i = i + int(hit[0])
        else:
            target = entry_price - cfg.k_target_atr * adr_session
            hit = np.where(segment <= target)[0]
            if len(hit):
                exit_i = i + int(hit[0])

        exit_price = float(close.iloc[exit_i])
        pnl = (
            (exit_price - entry_price) if side == "BUY" else (entry_price - exit_price)
        )
        r_mult = pnl / stop_dist

        seg = close.iloc[i : exit_i + 1].values
        if side == "BUY":
            mae = (np.min(seg) - entry_price) / stop_dist
            mfe = (np.max(seg) - entry_price) / stop_dist
        else:
            mae = (entry_price - np.max(seg)) / stop_dist
            mfe = (entry_price - np.min(seg)) / stop_dist

        trades.append(
            TradeSample(
                entry_time=out.index[i],
                exit_time=out.index[exit_i],
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                r_multiple=float(r_mult),
                mae_r=float(mae),
                mfe_r=float(mfe),
                hold_bars=int(exit_i - i),
                meta={
                    "atr_rank": atr_rank,
                    "adr_d1": adr_i,
                    "breakout_n": cfg.breakout_n,
                },
            )
        )

        i = exit_i + 1

    r = np.array([t.r_multiple for t in trades], dtype=float)
    mae = np.array([t.mae_r for t in trades], dtype=float)
    mfe = np.array([t.mfe_r for t in trades], dtype=float)
    hold = np.array([t.hold_bars for t in trades], dtype=float)

    exp_r = expectancy(r)
    wr = win_rate(r)
    pf = profit_factor(r)
    med_mae, med_mfe = median_mae_mfe(mae, mfe)
    avg_hold = float(np.mean(hold)) if len(hold) else float("nan")

    ci_low, ci_high = block_bootstrap_ci(
        r,
        statistic=lambda x: float(np.mean(x)),
        n_boot=boot.n_boot,
        block_size=boot.block_size,
        ci_level=boot.ci_level,
        seed=boot.seed,
    )

    # Null distribution in R-space
    null = r_space_null(
        out,
        n_trades=len(trades),
        hold_bars=cfg.max_hold_bars,
        side="BUY",
        k_stop_atr=cfg.k_stop_atr,
        atr_series=out["adr"],
        n_perm=perm.n_perm,
        seed=perm.seed,
        close_col=close_col,
    )
    pval = (
        permutation_test(observed=float(np.nan_to_num(exp_r)), null_samples=null)
        if len(null)
        else float("nan")
    )
    logger.debug(f"EDS-2 permutation p-value: {pval:.4f}")

    total_r = float(np.nansum(r)) if len(r) else float("nan")
    stats = EdgeStats(
        n_trades=int(len(trades)),
        expectancy_r=float(exp_r) if np.isfinite(exp_r) else float("nan"),
        win_rate=float(wr) if np.isfinite(wr) else float("nan"),
        profit_factor=float(pf),
        median_mae_r=float(med_mae),
        median_mfe_r=float(med_mfe),
        avg_hold_bars=float(avg_hold),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        p_value_perm=float(pval),
        extras={
            "total_r": total_r,
            "atr_q_high": cfg.atr_q_high,
            "breakout_n": cfg.breakout_n,
            "max_hold_bars": cfg.max_hold_bars,
            "target_atr": cfg.k_target_atr,
        },
    )

    return EdgeResult(
        symbol=symbol,
        timeframe=timeframe,
        eds_name="EDS-2 TrendPersistence (HighATR Breakout)",
        config=asdict(cfg),
        stats=stats,
        trades=trades,
    )

