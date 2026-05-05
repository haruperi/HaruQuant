"""EDS-1 mean reversion edge discovery strategy."""

from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

import numpy as np
import pandas as pd

from services.analytics.metrics import median_mae_mfe, win_rate_fraction
from services.analytics.ratios import expectancy, profit_factor
from services.utils.logger import logger

from .config import BootstrapConfig, MeanReversionConfig, PermutationConfig
from .features import adr, bb_width, rolling_percentile_rank, zscore
from .null_models import block_bootstrap_ci, permutation_test, r_space_null
from .results_schema import EdgeResult, EdgeStats, TradeSample


def run_eds_mean_reversion(  # noqa: C901
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    cfg: MeanReversionConfig,
    boot: BootstrapConfig,
    perm: PermutationConfig,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> EdgeResult:
    """EDS-1 Mean Reversion Detector: compression + z-score fade.

    Hypothesis: In low-volatility regimes, deviations from mean revert within H bars.

    Entry Conditions:
    - Compression regime (BBW percentile <= q)
    - Z-score >= threshold (oversold/overbought)

    Exit: Mean touch (z crosses 0) OR time stop

    Args:
        df: OHLC DataFrame
        symbol: Trading symbol
        timeframe: Timeframe string
        cfg: Mean reversion configuration
        boot: Bootstrap configuration
        perm: Permutation configuration
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        EdgeResult with trades and statistics
    """
    logger.info(f"Running EDS-1 Mean Reversion for {symbol} {timeframe}")
    out = df.copy()
    close = out[close_col].astype(float)

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

    out["z"] = zscore(close, cfg.sma_n)
    out["bbw"] = bb_width(close, cfg.bbw_n, cfg.bbw_k)
    out["bbw_rank"] = rolling_percentile_rank(out["bbw"], cfg.compression_window)
    out["adr"] = _daily_adr_series(out)

    trades: List[TradeSample] = []

    i = max(cfg.compression_window, cfg.sma_n, cfg.atr_n) + 1
    while i < len(out) - cfg.max_hold_bars - 2:
        bbw_rank = float(out["bbw_rank"].iloc[i])
        z = float(out["z"].iloc[i])
        if not np.isfinite(bbw_rank) or not np.isfinite(z):
            i += 1
            continue

        if bbw_rank > cfg.compression_q:
            i += 1
            continue

        side: Optional[str] = None
        if z <= -cfg.z_entry:
            side = "BUY"
        elif z >= cfg.z_entry:
            side = "SELL"

        if side is None:
            i += 1
            continue

        entry_price = float(out[close_col].iloc[i])
        adr_i = float(out["adr"].iloc[i])
        adr_session = adr_i / 3 if timeframe.upper() != "D1" else adr_i
        stop_dist = cfg.k_stop_atr * adr_session
        if stop_dist <= 0 or not np.isfinite(stop_dist):
            i += 1
            continue

        # Exit: mean touch (z crosses 0) OR time stop
        exit_i = None
        for j in range(1, cfg.max_hold_bars + 1):
            zf = float(out["z"].iloc[i + j])
            if side == "BUY" and zf >= 0:
                exit_i = i + j
                break
            if side == "SELL" and zf <= 0:
                exit_i = i + j
                break
        if exit_i is None:
            exit_i = i + cfg.max_hold_bars

        exit_price = float(out[close_col].iloc[exit_i])

        pnl = (
            (exit_price - entry_price) if side == "BUY" else (entry_price - exit_price)
        )
        r_mult = pnl / stop_dist

        segment = out[close_col].iloc[i : exit_i + 1].astype(float).values
        if len(segment) < 2:
            i += 1
            continue

        if side == "BUY":
            mae = (np.min(segment) - entry_price) / stop_dist
            mfe = (np.max(segment) - entry_price) / stop_dist
        else:
            mae = (entry_price - np.max(segment)) / stop_dist
            mfe = (entry_price - np.min(segment)) / stop_dist

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
                meta={"bbw_rank": bbw_rank, "z": z, "adr_d1": adr_i},
            )
        )

        i = exit_i + 1

    r = np.array([t.r_multiple for t in trades], dtype=float)
    mae = np.array([t.mae_r for t in trades], dtype=float)
    mfe = np.array([t.mfe_r for t in trades], dtype=float)
    hold = np.array([t.hold_bars for t in trades], dtype=float)

    exp_r = expectancy(r)
    wr = win_rate_fraction(r)
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

    # Null distribution in R-space (more accurate than log-return null)
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
    logger.debug(f"EDS-1 permutation p-value: {pval:.4f}")

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
            "hit_mean_rate": (
                float(
                    np.mean(
                        [
                            1.0 if (t.hold_bars < cfg.max_hold_bars) else 0.0
                            for t in trades
                        ]
                    )
                )
                if trades
                else float("nan")
            ),
            "compression_q": cfg.compression_q,
            "z_entry": cfg.z_entry,
            "max_hold_bars": cfg.max_hold_bars,
        },
    )

    return EdgeResult(
        symbol=symbol,
        timeframe=timeframe,
        eds_name="EDS-1 MeanReversion (Compression+Z)",
        config=asdict(cfg),
        stats=stats,
        trades=trades,
    )

