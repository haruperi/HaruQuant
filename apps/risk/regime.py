"""Market Regime Detection module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RegimeState:
    """Market regime used to tighten limits."""

    name: str  # "NORMAL" or "STRESS"


class RiskRegimeDetector:
    """Detects NORMAL vs STRESS regimes using simple robust signals.

    Signals:
    1) Volatility spike on equal-weight portfolio proxy
    2) Correlation spike (average off-diagonal correlation)
    3) Equity drawdown trigger (optional, if equity_curve provided)

    If at least 2 signals are triggered => STRESS, else NORMAL.
    """

    def __init__(
        self,
        vol_spike_mult: float = 1.8,
        corr_spike_level: float = 0.55,
        dd_trigger_frac: float = 0.05,
        lookback: int = 60,
    ):
        """Initialize regime detector."""
        self.vol_spike_mult = vol_spike_mult
        self.corr_spike_level = corr_spike_level
        self.dd_trigger_frac = dd_trigger_frac
        self.lookback = lookback

    def detect(
        self, returns_df: pd.DataFrame, equity_curve: Optional[pd.Series] = None
    ) -> RegimeState:
        """Detect current market regime based on returns and equity curve."""
        flags = 0

        # 1) Vol spike on equal-weight proxy
        if returns_df is not None and returns_df.shape[0] >= self.lookback:
            r = returns_df.dropna().iloc[-self.lookback :]
            if not r.empty:
                port = r.mean(axis=1)
                vol_now = float(port.std())
                vol_med = float(port.rolling(20).std().median())
                if vol_med > 0 and vol_now > self.vol_spike_mult * vol_med:
                    flags += 1

        # 2) Corr spike (avg off-diagonal)
        if returns_df is not None and returns_df.shape[1] >= 2:
            r = returns_df.dropna().iloc[-self.lookback :]
            if r.shape[0] >= 5:
                corr = r.corr()
                off = corr.values.copy()
                np.fill_diagonal(off, np.nan)
                avg_off = float(np.nanmean(off))
                if avg_off >= self.corr_spike_level:
                    flags += 1

        # 3) Drawdown trigger
        if equity_curve is not None and len(equity_curve) >= 10:
            peak = float(equity_curve.cummax().iloc[-1])
            cur = float(equity_curve.iloc[-1])
            if peak > 0:
                dd = (peak - cur) / peak
                if dd >= self.dd_trigger_frac:
                    flags += 1

        return RegimeState(name="STRESS" if flags >= 2 else "NORMAL")
