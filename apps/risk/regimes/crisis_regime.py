"""Crisis/stress regime detection built from the legacy detector logic."""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from .models import RegimeSignal, RegimeState


class CrisisRegimeDetector:
    """Detect NORMAL vs STRESS using robust portfolio stress signals."""

    def __init__(
        self,
        vol_spike_mult: float = 1.8,
        corr_spike_level: float = 0.55,
        dd_trigger_frac: float = 0.05,
        lookback: int = 60,
        vol_med_window: int = 20,
    ):
        self.vol_spike_mult = vol_spike_mult
        self.corr_spike_level = corr_spike_level
        self.dd_trigger_frac = dd_trigger_frac
        self.lookback = lookback
        self.vol_med_window = vol_med_window

    def detect(
        self, returns_df: pd.DataFrame, equity_curve: Optional[pd.Series] = None
    ) -> RegimeState:
        """Return the crisis regime only."""
        return self.detect_with_signals(returns_df, equity_curve)[0]

    def detect_with_signals(
        self, returns_df: pd.DataFrame, equity_curve: Optional[pd.Series] = None
    ) -> tuple[RegimeState, List[RegimeSignal]]:
        """Return crisis regime and the underlying explainable signals."""
        signals: List[RegimeSignal] = []

        vol_signal = RegimeSignal(signal_key="volatility_spike", triggered=False)
        if returns_df is not None and returns_df.shape[0] >= self.lookback:
            r = returns_df.dropna().iloc[-self.lookback :]
            if not r.empty:
                port = r.mean(axis=1)
                vol_now = float(port.std())
                vol_med = float(port.rolling(self.vol_med_window).std().median())
                triggered = bool(vol_med > 0 and vol_now > self.vol_spike_mult * vol_med)
                vol_signal = RegimeSignal(
                    signal_key="volatility_spike",
                    triggered=triggered,
                    observed_value=vol_now,
                    threshold_value=(self.vol_spike_mult * vol_med) if vol_med > 0 else None,
                    message="Portfolio volatility spike check.",
                )
        signals.append(vol_signal)

        corr_signal = RegimeSignal(signal_key="correlation_spike", triggered=False)
        if returns_df is not None and returns_df.shape[1] >= 2:
            r = returns_df.dropna().iloc[-self.lookback :]
            if r.shape[0] >= 5:
                corr = r.corr()
                off = corr.values.copy()
                np.fill_diagonal(off, np.nan)
                valid_off = off[~np.isnan(off)]
                avg_off = float(np.mean(valid_off)) if valid_off.size else 0.0
                triggered = bool(avg_off >= self.corr_spike_level)
                corr_signal = RegimeSignal(
                    signal_key="correlation_spike",
                    triggered=triggered,
                    observed_value=avg_off,
                    threshold_value=self.corr_spike_level,
                    message="Average off-diagonal correlation spike check.",
                )
        signals.append(corr_signal)

        dd_signal = RegimeSignal(signal_key="drawdown_trigger", triggered=False)
        if equity_curve is not None and len(equity_curve) >= 10:
            peak = float(equity_curve.cummax().iloc[-1])
            cur = float(equity_curve.iloc[-1])
            if peak > 0:
                dd = (peak - cur) / peak
                triggered = bool(dd >= self.dd_trigger_frac)
                dd_signal = RegimeSignal(
                    signal_key="drawdown_trigger",
                    triggered=triggered,
                    observed_value=dd,
                    threshold_value=self.dd_trigger_frac,
                    message="Equity drawdown trigger check.",
                )
        signals.append(dd_signal)

        triggered_signals = [signal.signal_key for signal in signals if signal.triggered]
        flags = len(triggered_signals)
        name = "STRESS" if flags >= 2 else "NORMAL"
        confidence = min(flags / 3.0, 1.0)
        return (
            RegimeState(
                name=name,
                family="crisis",
                confidence=confidence,
                signals_triggered=triggered_signals,
                warnings=[signal.message for signal in signals if signal.triggered],
                metadata={"signal_count": flags},
            ),
            signals,
        )
