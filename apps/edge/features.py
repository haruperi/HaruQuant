"""Edge Lab feature computation utilities.

This module provides technical indicators and feature calculations
used in edge discovery strategies.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from apps.logger import logger

# =============================================================================
# BASIC RETURNS & STATISTICS
# =============================================================================


def log_returns(close: pd.Series) -> pd.Series:
    """Compute log returns from close prices.

    Args:
        close: Close price series

    Returns:
        Log return series
    """
    return np.log(close / close.shift(1))


def simple_returns(close: pd.Series) -> pd.Series:
    """Compute simple (arithmetic) returns from close prices.

    Args:
        close: Close price series

    Returns:
        Simple return series
    """
    return close.pct_change()


def sma(series: pd.Series, n: int) -> pd.Series:
    """Compute simple moving average.

    Args:
        series: Input series
        n: Window size

    Returns:
        SMA series
    """
    return series.rolling(n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    """Exponential Moving Average.

    Args:
        series: Input series
        n: Window size (span)

    Returns:
        EMA series
    """
    return series.ewm(span=n, adjust=False).mean()


def std(series: pd.Series, n: int) -> pd.Series:
    """Compute rolling standard deviation.

    Args:
        series: Input series
        n: Window size

    Returns:
        Standard deviation series
    """
    return series.rolling(n).std()


# =============================================================================
# Z-SCORE & DEVIATION MEASURES
# =============================================================================


def zscore(close: pd.Series, n: int) -> pd.Series:
    """Compute z-score: (close - SMA) / STD.

    Measures how many standard deviations price is from its mean.
    Useful for mean reversion signals.

    Args:
        close: Close price series
        n: Window size for SMA and STD

    Returns:
        Z-score series
    """
    m = sma(close, n)
    s = std(close, n)
    return (close - m) / s


def percent_rank(series: pd.Series, n: int) -> pd.Series:
    """Compute percent rank over rolling window.

    Shows where current value ranks in the past n values (0-1).

    Args:
        series: Input series
        n: Window size

    Returns:
        Percent rank series (0 = lowest, 1 = highest)
    """

    def _rank(x: np.ndarray) -> float:
        if len(x) == 0 or np.isnan(x[-1]):
            return float("nan")
        return float(np.sum(x < x[-1]) / len(x))

    return series.rolling(n).apply(_rank, raw=True)


# =============================================================================
# VOLATILITY INDICATORS
# =============================================================================


def atr(
    df: pd.DataFrame,
    n: int,
    high_col: str = "High",
    low_col: str = "Low",
    close_col: str = "Close",
) -> pd.Series:
    """Average True Range.

    Measures volatility based on the true range of price movement.

    Args:
        df: DataFrame with OHLC data
        n: ATR period
        high_col: High column name
        low_col: Low column name
        close_col: Close column name

    Returns:
        ATR series
    """
    high = df[high_col].astype(float)
    low = df[low_col].astype(float)
    close = df[close_col].astype(float)
    prev_close = close.shift(1)

    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    return tr.rolling(n).mean()


def atr_percent(
    df: pd.DataFrame,
    n: int,
    high_col: str = "High",
    low_col: str = "Low",
    close_col: str = "Close",
) -> pd.Series:
    """ATR as percentage of close price.

    Normalizes ATR for comparison across different price levels.

    Args:
        df: DataFrame with OHLC data
        n: ATR period
        high_col: High column name
        low_col: Low column name
        close_col: Close column name

    Returns:
        ATR percent series
    """
    atr_val = atr(df, n, high_col, low_col, close_col)
    return atr_val / df[close_col] * 100


def bollinger_bands(
    close: pd.Series, n: int, k: float
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands.

    Args:
        close: Close price series
        n: SMA period
        k: Number of standard deviations

    Returns:
        Tuple of (lower_band, middle_band, upper_band)
    """
    m = sma(close, n)
    s = std(close, n)
    upper = m + k * s
    lower = m - k * s
    return lower, m, upper


def bb_width(close: pd.Series, n: int, k: float) -> pd.Series:
    """Bollinger Band Width.

    Measures the width of Bollinger Bands as a percentage of the middle band.
    Low values indicate compression (potential breakout setup).

    Args:
        close: Close price series
        n: SMA period
        k: Number of standard deviations

    Returns:
        BB width series
    """
    lower, mid, upper = bollinger_bands(close, n, k)
    return (upper - lower) / mid


def bb_percent_b(close: pd.Series, n: int, k: float) -> pd.Series:
    """Bollinger Band %B.

    Shows where price is relative to the bands.
    0 = at lower band, 1 = at upper band, 0.5 = at middle.

    Args:
        close: Close price series
        n: SMA period
        k: Number of standard deviations

    Returns:
        %B series
    """
    lower, mid, upper = bollinger_bands(close, n, k)
    return (close - lower) / (upper - lower)


def rolling_percentile_rank(series: pd.Series, window: int) -> pd.Series:
    """Compute rolling percentile rank.

    Shows where current value ranks in a rolling window (0-1).

    Args:
        series: Input series
        window: Rolling window size

    Returns:
        Percentile rank series
    """

    def _rank(x: np.ndarray) -> float:
        if len(x) == 0 or np.isnan(x[-1]):
            return float("nan")
        last = x[-1]
        return float(np.sum(x <= last) / len(x))

    return series.rolling(window).apply(_rank, raw=True)


# =============================================================================
# MOMENTUM INDICATORS
# =============================================================================


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Relative Strength Index.

    Args:
        close: Close price series
        n: RSI period

    Returns:
        RSI series (0-100)
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rate_of_change(close: pd.Series, n: int) -> pd.Series:
    """Rate of Change (momentum).

    Args:
        close: Close price series
        n: Lookback period

    Returns:
        ROC series (percentage)
    """
    return (close / close.shift(n) - 1) * 100


def momentum(close: pd.Series, n: int) -> pd.Series:
    """Compute simple momentum as a price difference.

    Args:
        close: Close price series
        n: Lookback period

    Returns:
        Momentum series
    """
    return close - close.shift(n)


# =============================================================================
# TREND INDICATORS
# =============================================================================


def donchian_channel(
    df: pd.DataFrame, n: int, high_col: str = "High", low_col: str = "Low"
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Donchian Channel (breakout levels).

    Args:
        df: DataFrame with OHLC data
        n: Channel period
        high_col: High column name
        low_col: Low column name

    Returns:
        Tuple of (lower, middle, upper) channel lines
    """
    upper = df[high_col].rolling(n).max()
    lower = df[low_col].rolling(n).min()
    middle = (upper + lower) / 2
    return lower, middle, upper


def hurst_exponent(series: pd.Series, lags: int = 20) -> float:
    """Estimate Hurst exponent for mean reversion vs trending detection.

    H < 0.5: Mean reverting
    H = 0.5: Random walk
    H > 0.5: Trending

    Args:
        series: Price or return series
        lags: Number of lags for R/S analysis

    Returns:
        Estimated Hurst exponent
    """
    series = series.dropna()
    if len(series) < lags * 2:
        return 0.5

    lags_arr = range(2, lags)
    tau = []

    for lag in lags_arr:
        # Divide into sub-series
        subseries = np.array(
            [series.iloc[i : i + lag].values for i in range(0, len(series) - lag, lag)]
        )
        if len(subseries) < 2:
            continue

        rs_values = []
        for ss in subseries:
            mean_ss = np.mean(ss)
            cumdev = np.cumsum(ss - mean_ss)
            r = np.max(cumdev) - np.min(cumdev)
            s = np.std(ss)
            if s > 0:
                rs_values.append(r / s)

        if len(rs_values) > 0:
            tau.append((lag, np.mean(rs_values)))

    if len(tau) < 2:
        return 0.5

    lags_log = np.log([t[0] for t in tau])
    rs_log = np.log([t[1] for t in tau])

    # Linear regression to estimate H
    slope = np.polyfit(lags_log, rs_log, 1)[0]
    return float(slope)


def rolling_hurst(series: pd.Series, window: int = 100, lags: int = 20) -> pd.Series:
    """Compute rolling Hurst exponent.

    Args:
        series: Price series
        window: Rolling window size
        lags: Number of lags for Hurst calculation

    Returns:
        Rolling Hurst series
    """

    def _hurst(x):
        return hurst_exponent(pd.Series(x), lags)

    return series.rolling(window).apply(_hurst, raw=False)


# =============================================================================
# SUPPORT/RESISTANCE & LEVELS
# =============================================================================


def pivot_points(
    df: pd.DataFrame,
    high_col: str = "High",
    low_col: str = "Low",
    close_col: str = "Close",
) -> pd.DataFrame:
    """Calculate pivot points and support/resistance levels.

    Uses previous bar's HLC to calculate levels for current bar.

    Args:
        df: DataFrame with OHLC data
        high_col: High column name
        low_col: Low column name
        close_col: Close column name

    Returns:
        DataFrame with pivot point columns
    """
    prev_high = df[high_col].shift(1)
    prev_low = df[low_col].shift(1)
    prev_close = df[close_col].shift(1)

    pivot = (prev_high + prev_low + prev_close) / 3

    result = pd.DataFrame(index=df.index)
    result["pivot"] = pivot
    result["r1"] = 2 * pivot - prev_low
    result["s1"] = 2 * pivot - prev_high
    result["r2"] = pivot + (prev_high - prev_low)
    result["s2"] = pivot - (prev_high - prev_low)
    result["r3"] = prev_high + 2 * (pivot - prev_low)
    result["s3"] = prev_low - 2 * (prev_high - pivot)

    return result


def adr(
    df: pd.DataFrame, n: int = 14, high_col: str = "High", low_col: str = "Low"
) -> pd.Series:
    """Average Daily Range.

    Useful for estimating expected price movement.

    Args:
        df: DataFrame with OHLC data
        n: Period for averaging
        high_col: High column name
        low_col: Low column name

    Returns:
        ADR series
    """
    daily_range = df[high_col] - df[low_col]
    return daily_range.rolling(n).mean()


# =============================================================================
# FORWARD-LOOKING (for analysis, not live trading)
# =============================================================================


def forward_returns(close: pd.Series, horizon: int) -> pd.Series:
    """Compute forward log returns.

    For backtesting/analysis only - looks into the future.

    Args:
        close: Close price series
        horizon: Number of bars to look forward

    Returns:
        Forward return series
    """
    return np.log(close.shift(-horizon) / close)


def forward_max_favorable_excursion(
    df: pd.DataFrame,
    horizon: int,
    side: str,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> pd.Series:
    """Maximum favorable price excursion over horizon.

    For analysis - calculates best possible outcome.

    Args:
        df: DataFrame with OHLC data
        horizon: Bars to look forward
        side: "BUY" or "SELL"
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        MFE series
    """
    entry = df[close_col]
    if side.upper() == "BUY":
        best = df[high_col].rolling(horizon).max().shift(-horizon)
        return best - entry
    else:
        best = df[low_col].rolling(horizon).min().shift(-horizon)
        return entry - best


def forward_max_adverse_excursion(
    df: pd.DataFrame,
    horizon: int,
    side: str,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> pd.Series:
    """Maximum adverse price excursion over horizon.

    For analysis - calculates worst drawdown during trade.

    Args:
        df: DataFrame with OHLC data
        horizon: Bars to look forward
        side: "BUY" or "SELL"
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        MAE series (negative values indicate adverse movement)
    """
    entry = df[close_col]
    if side.upper() == "BUY":
        worst = df[low_col].rolling(horizon).min().shift(-horizon)
        return worst - entry
    else:
        worst = df[high_col].rolling(horizon).max().shift(-horizon)
        return entry - worst


# =============================================================================
# REGIME DETECTION
# =============================================================================


def detect_volatility_regime(
    df: pd.DataFrame,
    atr_n: int = 14,
    window: int = 252,
    n_regimes: int = 3,
    high_col: str = "High",
    low_col: str = "Low",
    close_col: str = "Close",
) -> pd.Series:
    """Detect volatility regime based on ATR percentile.

    Buckets ATR into regimes:
    - 0: Low volatility
    - 1: Normal volatility
    - 2: High volatility

    Args:
        df: DataFrame with OHLC data
        atr_n: ATR period
        window: Rolling window for percentile
        n_regimes: Number of volatility buckets
        high_col: High column name
        low_col: Low column name
        close_col: Close column name

    Returns:
        Regime series (0, 1, 2, ...)
    """
    atr_vals = atr(df, atr_n, high_col, low_col, close_col)
    atr_rank = rolling_percentile_rank(atr_vals, window)

    # Create regime buckets
    thresholds = np.linspace(0, 1, n_regimes + 1)[1:-1]
    regime = pd.Series(index=df.index, dtype=int)

    for i, thresh in enumerate(thresholds):
        regime = regime.where(atr_rank >= thresh, i)

    regime = regime.where(
        atr_rank < thresholds[-1] if len(thresholds) > 0 else True, n_regimes - 1
    )

    logger.debug(f"Volatility regime distribution: {regime.value_counts().to_dict()}")
    return regime


def detect_trend_regime(
    close: pd.Series,
    fast_n: int = 20,
    slow_n: int = 50,
) -> pd.Series:
    """Detect trend regime based on moving average relationship.

    Returns:
    - 1: Uptrend (fast > slow)
    - -1: Downtrend (fast < slow)
    - 0: Neutral (close to crossover)

    Args:
        close: Close price series
        fast_n: Fast MA period
        slow_n: Slow MA period

    Returns:
        Trend regime series
    """
    fast_ma = sma(close, fast_n)
    slow_ma = sma(close, slow_n)

    diff = fast_ma - slow_ma
    threshold = std(diff, slow_n) * 0.5

    regime = pd.Series(0, index=close.index)
    regime = regime.where(diff.abs() <= threshold, np.sign(diff).astype(int))

    return regime
