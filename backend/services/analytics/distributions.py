"""
Statistical structure of returns & trades.

Focus: distribution shape, tail behavior, and statistical fitting

This module provides tools to analyze the underlying distribution of trading results.
It includes measures for skewness and kurtosis, normality tests (Jarque-Bera, Shapiro-Wilk),
outlier detection logic, and curve fitting for different probability density functions.

Summary of Methods:
------------------
Core Summary Statistics:
    - return_distribution: Statistical summary (mean, std, quartiles) of returns.
    - trade_pnl_distribution: Statistical summary of individual trade P&L.
    - r_multiple_distribution: Statistical summary of risk-normalized outcomes.

Higher Moments:
    - skewness: Measure of return distribution asymmetry.
    - kurtosis: Measure of extreme tail thickness (excess kurtosis).
    - higher_moments: Combined dict of skew and kurtosis.
    - fat_tail_score: Kurtosis-based measure compared to a normal distribution.

Normality & Statistical Tests:
    - jarque_bera_test: Test if returns follow a normal distribution.
    - shapiro_wilk_test: Normality test optimized for smaller sample sizes.
    - qq_plot_data: Data points for Quantile-Quantile visual analysis.

Distribution Fitting:
    - fit_distribution: Fit data to Normal, Student-t, Log-Normal, or Gamma distributions.

Outlier Detection:
    - detect_outliers: Identify anomalous points using IQR or Z-score methods.
    - outlier_ratio: Percentage of the data set flagged as outliers.
"""

from typing import Dict, Literal, Tuple

import numpy as np
import pandas as pd

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# =========================================================================
# Core Summary Statistics
# =========================================================================


def return_distribution(rets: pd.Series) -> Dict[str, float]:
    """Statistical summary of returns distribution."""
    if len(rets) == 0:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "skew": 0.0, "kurtosis": 0.0, 
                "min": 0.0, "max": 0.0, "q25": 0.0, "q75": 0.0}
    return {
        "mean": float(rets.mean()),
        "median": float(rets.median()),
        "std": float(rets.std()),
        "skew": float(rets.skew()),
        "kurtosis": float(rets.kurtosis()),
        "min": float(rets.min()),
        "max": float(rets.max()),
        "q25": float(rets.quantile(0.25)),
        "q75": float(rets.quantile(0.75)),
    }


def trade_pnl_distribution(trades: pd.DataFrame) -> Dict[str, float]:
    """Statistical summary of trade P&L distribution."""
    if len(trades) == 0 or "profit_loss" not in trades.columns:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "skew": 0.0, "kurtosis": 0.0, 
                "min": 0.0, "max": 0.0, "q25": 0.0, "q75": 0.0}
    pnl = trades["profit_loss"]
    return {
        "mean": float(pnl.mean()),
        "median": float(pnl.median()),
        "std": float(pnl.std()),
        "skew": float(pnl.skew()),
        "kurtosis": float(pnl.kurtosis()),
        "min": float(pnl.min()),
        "max": float(pnl.max()),
        "q25": float(pnl.quantile(0.25)),
        "q75": float(pnl.quantile(0.75)),
    }


def r_multiple_distribution(trades: pd.DataFrame) -> Dict[str, float]:
    """Statistical summary of R-multiple distribution."""
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "skew": 0.0, "kurtosis": 0.0, 
                "min": 0.0, "max": 0.0, "q25": 0.0, "q75": 0.0}
    r_values = trades["r_multiple"]
    return {
        "mean": float(r_values.mean()),
        "median": float(r_values.median()),
        "std": float(r_values.std()),
        "skew": float(r_values.skew()),
        "kurtosis": float(r_values.kurtosis()),
        "min": float(r_values.min()),
        "max": float(r_values.max()),
        "q25": float(r_values.quantile(0.25)),
        "q75": float(r_values.quantile(0.75)),
    }


# =========================================================================
# Higher Moments
# =========================================================================


def skewness(data: pd.Series) -> float:
    """Calculate skewness of a data series."""
    if len(data) < 3: return 0.0
    val = data.skew()
    return float(val) if not pd.isna(val) else 0.0


def kurtosis(data: pd.Series) -> float:
    """Calculate excess kurtosis of a data series."""
    if len(data) < 4: return 0.0
    val = data.kurtosis()
    return float(val) if not pd.isna(val) else 0.0


def higher_moments(data: pd.Series) -> Dict[str, float]:
    """Calculate combined higher statistical moments."""
    if len(data) < 4:
        return {"skewness": 0.0, "kurtosis": 0.0, "excess_kurtosis": 0.0}
    k = data.kurtosis()
    return {
        "skewness": float(data.skew()),
        "excess_kurtosis": float(k),
        "kurtosis": float(k + 3),
    }


def fat_tail_score(rets: pd.Series) -> float:
    """Excess kurtosis measure of tail thickness."""
    return float(rets.kurtosis()) if len(rets) >= 4 else 0.0


# =========================================================================
# Normality & Statistical Tests
# =========================================================================


def jarque_bera_test(rets: pd.Series) -> Dict[str, float]:
    """Jarque-Bera test for normality."""
    if not HAS_SCIPY:
        raise ImportError("scipy is required for Jarque-Bera test.")
    if len(rets) < 4:
        return {"statistic": 0.0, "p_value": 1.0, "is_normal": True}
    stat, p = stats.jarque_bera(rets.values)
    return {"statistic": float(stat), "p_value": float(p), "is_normal": bool(p > 0.05)}


def shapiro_wilk_test(rets: pd.Series) -> Dict[str, float]:
    """Shapiro-Wilk test for normality (optimized for < 5000 samples)."""
    if not HAS_SCIPY:
        raise ImportError("scipy is required for Shapiro-Wilk test.")
    if len(rets) < 3:
        return {"statistic": 0.0, "p_value": 1.0, "is_normal": True}
    sample = rets.values
    if len(sample) > 5000:
        sample = np.random.choice(sample, 5000, replace=False)
    stat, p = stats.shapiro(sample)
    return {"statistic": float(stat), "p_value": float(p), "is_normal": bool(p > 0.05)}


def qq_plot_data(data: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """Generate Q-Q plot theoretical vs sample quantiles."""
    if not HAS_SCIPY:
        raise ImportError("scipy is required for Q-Q plot.")
    if len(data) < 2:
        return (np.array([]), np.array([]))
    standardized = (data - data.mean()) / data.std()
    sorted_sample = np.sort(standardized.values)
    theoretical = stats.norm.ppf(np.linspace(0.01, 0.99, len(sorted_sample)))
    return (theoretical, sorted_sample)


# =========================================================================
# Distribution Fitting
# =========================================================================


def fit_distribution(
    data: pd.Series, dist_name: Literal["norm", "t", "lognorm", "gamma"] = "norm"
) -> Dict[str, float]:
    """Fit data to a probability density function."""
    if not HAS_SCIPY:
        raise ImportError("scipy is required for distribution fitting.")
    if len(data) < 2: return {}
    arr = data.values
    if dist_name == "norm":
        mu, sigma = stats.norm.fit(arr)
        return {"mu": float(mu), "sigma": float(sigma)}
    elif dist_name == "t":
        df, loc, scale = stats.t.fit(arr)
        return {"df": float(df), "loc": float(loc), "scale": float(scale)}
    elif dist_name == "lognorm":
        shape, loc, scale = stats.lognorm.fit(arr, floc=0)
        return {"shape": float(shape), "loc": float(loc), "scale": float(scale)}
    elif dist_name == "gamma":
        shape, loc, scale = stats.gamma.fit(arr, floc=0)
        return {"shape": float(shape), "loc": float(loc), "scale": float(scale)}
    return {}


# =========================================================================
# Outlier Detection
# =========================================================================


def detect_outliers(
    data: pd.Series, method: Literal["iqr", "zscore"] = "iqr", threshold: float = 3.0
) -> pd.Series:
    """Identify anomalous data points."""
    if len(data) == 0: return pd.Series(dtype=bool)
    if method == "iqr":
        q1, q3 = data.quantile(0.25), data.quantile(0.75)
        iqr = q3 - q1
        return (data < q1 - threshold * iqr) | (data > q3 + threshold * iqr)
    elif method == "zscore":
        z = np.abs((data - data.mean()) / data.std())
        return z > threshold
    return pd.Series(False, index=data.index)


def outlier_ratio(data: pd.Series, **kwargs) -> float:
    """Percentage of data points identified as outliers."""
    if len(data) == 0: return 0.0
    return float(detect_outliers(data, **kwargs).sum() / len(data))
