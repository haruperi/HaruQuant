"""
Usage Example: Regime Detection with Live MT5 Data

Demonstrates regime detection scenarios using real MT5 prices:
1. Normal market conditions
2. Volatility spike
3. Correlation spike
4. Drawdown trigger
5. Majority vote behavior

Run:
    python tests/usage/risk/02_regime_detection.py
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Optional

import numpy as np
import pandas as pd

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.mt5 import MT5Client
from apps.risk import RiskRegimeDetector
from apps.sqlite.users import UserManager
from apps.trade import AccountInfo


def _get_mt5_credentials() -> Optional[dict]:
    creds = UserManager().get_mt5_credentials()
    if not creds:
        print("No default broker credentials found.")
        return None
    return creds


def _connect_mt5() -> Optional[MT5Client]:
    creds = _get_mt5_credentials()
    if not creds:
        return None

    mt5_client = MT5Client()
    if not mt5_client.connect(
        path=creds["path"],
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
    ):
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return None
    return mt5_client


def _fetch_returns_df(
    mt5_client: MT5Client, symbols: list[str], timeframe: str, bars: int
) -> pd.DataFrame:
    data: Dict[str, pd.Series] = {}
    for symbol in symbols:
        df = mt5_client.get_bars(symbol=symbol, timeframe=timeframe, count=bars, start_pos=0)
        if df is None or df.empty or "close" not in df.columns:
            continue
        data[symbol] = df["close"].astype(float).pct_change()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).dropna(how="all")


def _make_vol_spike(returns_df: pd.DataFrame, spike_mult: float = 3.0) -> pd.DataFrame:
    if returns_df.empty:
        return returns_df
    out = returns_df.copy()
    tail = max(5, int(len(out) * 0.2))
    out.iloc[-tail:] = out.iloc[-tail:] * spike_mult
    return out


def _make_high_corr(returns_df: pd.DataFrame, noise_scale: float = 0.05) -> pd.DataFrame:
    if returns_df.empty:
        return returns_df
    base = returns_df.mean(axis=1)
    noise = np.random.normal(0.0, base.std() * noise_scale, size=(len(base), returns_df.shape[1]))
    out = pd.DataFrame(
        base.values.reshape(-1, 1) + noise,
        index=returns_df.index,
        columns=returns_df.columns,
    )
    return out


def _make_drawdown_equity(index: pd.Index, base_equity: float, drawdown_frac: float) -> pd.Series:
    if len(index) == 0:
        return pd.Series(dtype=float)
    peak_at = int(len(index) * 0.7)
    rising = np.linspace(base_equity * 0.95, base_equity, peak_at, endpoint=False)
    target = base_equity * (1.0 - drawdown_frac)
    falling = np.linspace(base_equity, target, len(index) - peak_at)
    equity = np.concatenate([rising, falling])
    return pd.Series(equity, index=index)


def main() -> None:
    print("\n" + "=" * 80)
    print("REGIME DETECTION - LIVE MT5 DATA")
    print("=" * 80)

    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    try:
        symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
        timeframe = "D1"
        bars = 120

        returns_df = _fetch_returns_df(mt5_client, symbols, timeframe, bars)
        if returns_df.empty or returns_df.shape[0] < 60:
            print("Insufficient data for regime detection.")
            return

        account = AccountInfo()
        equity = float(account.Equity())
        if equity <= 0:
            print("Failed to fetch account equity from MT5.")
            return

        detector = RiskRegimeDetector(
            vol_spike_mult=1.8,
            corr_spike_level=0.55,
            dd_trigger_frac=0.05,
            lookback=60,
        )

        print(f"Symbols: {', '.join(symbols)}")
        print(f"Timeframe: {timeframe} | Bars: {bars}")
        print(f"Equity: ${equity:,.2f}")

        # 1) Normal
        print("\n" + "-" * 80)
        print("1) Normal Market Conditions")
        regime_normal = detector.detect(returns_df, equity_curve=None)
        print(f"Detected Regime: {regime_normal.name}")

        # 2) Volatility spike
        print("\n" + "-" * 80)
        print("2) Volatility Spike")
        vol_spike_df = _make_vol_spike(returns_df, spike_mult=3.0)
        regime_vol = detector.detect(vol_spike_df, equity_curve=None)
        print(f"Detected Regime: {regime_vol.name}")

        # 3) Correlation spike
        print("\n" + "-" * 80)
        print("3) Correlation Spike")
        corr_df = _make_high_corr(returns_df)
        regime_corr = detector.detect(corr_df, equity_curve=None)
        print(f"Detected Regime: {regime_corr.name}")

        # 4) Drawdown trigger
        print("\n" + "-" * 80)
        print("4) Drawdown Trigger")
        equity_curve = _make_drawdown_equity(returns_df.index, equity, drawdown_frac=0.08)
        regime_dd = detector.detect(returns_df, equity_curve=equity_curve)
        print(f"Detected Regime: {regime_dd.name}")

        # 5) Majority vote
        print("\n" + "-" * 80)
        print("5) Majority Vote (Vol + Corr + Drawdown)")
        combined_df = _make_high_corr(_make_vol_spike(returns_df, spike_mult=2.0))
        combined_equity = _make_drawdown_equity(returns_df.index, equity, drawdown_frac=0.10)
        regime_combo = detector.detect(combined_df, equity_curve=combined_equity)
        print(f"Detected Regime: {regime_combo.name}")

        print("\n" + "=" * 80)
        print("DONE")
        print("=" * 80)

    finally:
        mt5_client.shutdown()


def main_actual() -> None:
    print("\n" + "=" * 80)
    print("REGIME DETECTION - LIVE BAR-BY-BAR (H1)")
    print("=" * 80)

    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    try:
        symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
        timeframe = "H1"
        bars = 400

        data: Dict[str, pd.Series] = {}
        for symbol in symbols:
            df = mt5_client.get_bars(
                symbol=symbol, timeframe=timeframe, count=bars, start_pos=0
            )
            if df is None or df.empty or "close" not in df.columns:
                continue
            data[symbol] = df["close"].astype(float)

        if not data:
            print("No data available for regime detection.")
            return

        prices_df = pd.DataFrame(data).dropna(how="all")
        returns_df = prices_df.pct_change().dropna(how="all")
        if returns_df.empty or returns_df.shape[0] < 60:
            print("Insufficient data for bar-by-bar regime detection.")
            return

        account = AccountInfo()
        equity = float(account.Equity())
        if equity <= 0:
            print("Failed to fetch account equity from MT5.")
            return

        detector = RiskRegimeDetector(
            vol_spike_mult=1.8,
            corr_spike_level=0.55,
            dd_trigger_frac=0.05,
            lookback=60,
        )

        print(f"Symbols: {', '.join(symbols)}")
        print(f"Timeframe: {timeframe} | Bars: {bars}")
        print(f"Equity: ${equity:,.2f}")
        print("\nBar-by-bar regime detection:")

        for i in range(detector.lookback, len(returns_df) + 1):
            window = returns_df.iloc[:i]
            equity_curve = pd.Series([equity] * len(window), index=window.index)
            regime = detector.detect(window, equity_curve)
            ts = window.index[-1]
            print(f"{ts} -> {regime.name}")

        print("\n" + "=" * 80)
        print("DONE")
        print("=" * 80)

    finally:
        mt5_client.shutdown()


if __name__ == "__main__":
    # main()
    main_actual()
