"""
Summary:
-------
HaruQuant Statistical Distribution Analytics.
Analysis of return moments, normality, distribution fitting, and outlier detection.
This module provides tools to analyze the shape of trading results, identifying 
asymmetry (skew), tail risk (kurtosis), and non-normal behavior.

Summary of Methods:
------------------
Moment & Shape Analysis:
    - higher_moments: Skewness and excess kurtosis.
    - fat_tail_score: Measure of extreme tail thickness.
    - upside_downside_summary: Analysis of return asymmetry (gain vs loss).
    - percentile_summary: Detailed quantile analysis (P01 to P99).

Statistical Testing:
    - jarque_bera_test / shapiro_wilk_test: Normality testing.
    - qq_plot_data: Theoretical vs actual quantiles for visualization.
    - distribution_fit_quality: Comparison of Normal, T, and Lognormal fits.

Outlier & Histogram:
    - detect_outliers: Identification of extreme results via Z-score or IQR.
    - histogram_data: Frequency counts and binning for UI charts.
    - tail_ratio: Ratio of extreme winners to extreme losers.
    - qq_plot_data: Data points for Quantile-Quantile visual analysis.

Distribution Fitting:
    - fit_distribution: Fit data to Normal, Student-t, Log-Normal, or Gamma distributions.

Outlier Detection:
    - detect_outliers: Identify anomalous points using IQR or Z-score methods.
    - outlier_ratio: Percentage of the data set flagged as outliers.
"""

from typing import Dict, Literal, Optional, Tuple
import numpy as np
import pandas as pd

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from .common import get_closed_trades, get_r_multiples


# =========================================================================
# Shared Helpers & Cleaning
# =========================================================================


def _clean_series(data: pd.Series | np.ndarray) -> pd.Series:
    """Convert input to finite numeric pandas Series."""
    if isinstance(data, pd.Series):
        s = pd.to_numeric(data, errors="coerce")
    else:
        s = pd.Series(data, dtype="float64")

    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    return s.astype(float)


def _empty_distribution() -> Dict[str, float]:
    """Standardized empty distribution dictionary."""
    return {
        "count": 0.0,
        "mean": 0.0,
        "median": 0.0,
        "std": 0.0,
        "skew": 0.0,
        "kurtosis": 0.0,
        "min": 0.0,
        "max": 0.0,
        "q25": 0.0,
        "q75": 0.0,
    }


def _distribution_summary(data: pd.Series) -> Dict[str, float]:
    """Generate a standardized summary of a distribution's shape."""
    s = _clean_series(data)
    if s.empty:
        return _empty_distribution()

    n = len(s)
    return {
        "count": float(n),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "std": float(s.std(ddof=1)) if n >= 2 else 0.0,
        "skew": float(s.skew()) if n >= 3 else 0.0,
        "kurtosis": float(s.kurtosis()) if n >= 4 else 0.0,
        "min": float(s.min()),
        "max": float(s.max()),
        "q25": float(s.quantile(0.25)),
        "q75": float(s.quantile(0.75)),
    }


# =========================================================================
# Core Summary Statistics
# =========================================================================


def return_distribution(rets: pd.Series | np.ndarray) -> Dict[str, float]:
    """Statistical summary of returns distribution."""
    return _distribution_summary(rets)


def trade_pnl_distribution(trades: pd.DataFrame) -> Dict[str, float]:
    """Statistical summary of realized trade P&L distribution."""
    closed = get_closed_trades(trades)
    if closed.empty or "profit_loss" not in closed.columns:
        return _empty_distribution()
    return _distribution_summary(closed["profit_loss"])


def r_multiple_distribution(trades: pd.DataFrame) -> Dict[str, float]:
    """Statistical summary of R-multiple distribution."""
    r_values = get_r_multiples(trades)
    if r_values.empty:
        return _empty_distribution()
    return _distribution_summary(r_values)


def percentile_summary(
    data: pd.Series | np.ndarray,
    percentiles: list[float] | None = None,
) -> Dict[str, float]:
    """
    Return selected percentile values.
    Useful for tail analysis and dashboard distribution views.
    """
    s = _clean_series(data)
    if s.empty:
        return {}

    if percentiles is None:
        percentiles = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]

    return {
        f"p{int(p * 100)}": float(s.quantile(p))
        for p in percentiles
    }


def upside_downside_summary(data: pd.Series | np.ndarray) -> Dict[str, float]:
    """
    Summary of positive and negative outcome distributions.
    """
    s = _clean_series(data)
    if s.empty:
        return {
            "upside_mean": 0.0,
            "downside_mean": 0.0,
            "upside_std": 0.0,
            "downside_std": 0.0,
            "upside_count": 0.0,
            "downside_count": 0.0,
        }

    upside = s[s > 0]
    downside = s[s < 0]

    return {
        "upside_mean": float(upside.mean()) if not upside.empty else 0.0,
        "downside_mean": float(downside.mean()) if not downside.empty else 0.0,
        "upside_std": float(upside.std(ddof=1)) if len(upside) >= 2 else 0.0,
        "downside_std": float(downside.std(ddof=1)) if len(downside) >= 2 else 0.0,
        "upside_count": float(len(upside)),
        "downside_count": float(len(downside)),
    }


# =========================================================================
# Higher Moments & Fat Tails
# =========================================================================


def skewness(data: pd.Series | np.ndarray) -> float:
    """Fisher-Pearson coefficient of skewness."""
    s = _clean_series(data)
    if len(s) < 3: return 0.0
    return float(s.skew())


def kurtosis(data: pd.Series | np.ndarray) -> float:
    """Excess kurtosis (Fisher’s definition, Normal = 0)."""
    s = _clean_series(data)
    if len(s) < 4: return 0.0
    return float(s.kurtosis())


def higher_moments(data: pd.Series | np.ndarray) -> Dict[str, float]:
    """Detailed breakdown of skewness and kurtosis."""
    s = _clean_series(data)
    ex_kurt = kurtosis(s)
    return {
        "skewness": skewness(s),
        "excess_kurtosis": ex_kurt,
        "kurtosis": ex_kurt + 3.0,
    }


def fat_tail_score(data: pd.Series | np.ndarray) -> float:
    """
    Heuristic score of tail heaviness relative to normal.
    (Experimental metric combining excess kurtosis and outlier ratios).
    """
    k = kurtosis(data)
    ratio = outlier_ratio(data, method="iqr")
    # Heuristic: Kurtosis normalized by 3 + 2x outlier percentage
    return float(max(0.0, k / 3.0 + ratio / 5.0))


def tail_ratio(data: pd.Series | np.ndarray, upper_q: float = 0.95, lower_q: float = 0.05) -> float:
    """
    Tail Ratio = |upper percentile| / |lower percentile|.
    Values > 1 suggest upside tail is larger than downside tail.
    """
    if not (0 < lower_q < upper_q < 1):
        return 0.0

    s = _clean_series(data)
    if s.empty:
        return 0.0

    upper = s.quantile(upper_q)
    lower = s.quantile(lower_q)

    if abs(lower) <= 1e-12:
        return float("inf") if upper > 0 else 0.0

    return float(abs(upper) / abs(lower))


# =========================================================================
# Normality Tests
# =========================================================================


def jarque_bera_test(data: pd.Series | np.ndarray) -> Dict[str, float]:
    """
    Jarque-Bera test for normality.
    Returns statistic and p-value.
    """
    if not HAS_SCIPY: return {"statistic": 0.0, "p_value": 0.0}
    
    s = _clean_series(data)
    # JB test requires at least 4 samples for skew/kurt to be meaningful
    if len(s) < 4: return {"statistic": 0.0, "p_value": 0.0}
    
    stat, p = stats.jarque_bera(s.to_numpy())
    return {"statistic": float(stat), "p_value": float(p)}


def shapiro_wilk_test(data: pd.Series | np.ndarray) -> Dict[str, float]:
    """
    Shapiro-Wilk test for normality (Best for smaller samples).
    """
    if not HAS_SCIPY: return {"statistic": 0.0, "p_value": 0.0}
    
    s = _clean_series(data)
    if len(s) < 3: return {"statistic": 0.0, "p_value": 0.0}
    
    # Shapiro-Wilk is limited to 5000 samples in some older scipy versions
    arr = s.to_numpy()
    if len(arr) > 5000:
        arr = np.random.choice(arr, 5000, replace=False)
        
    stat, p = stats.shapiro(arr)
    return {"statistic": float(stat), "p_value": float(p)}


# =========================================================================
# Distribution Fitting & Q-Q Plots
# =========================================================================


def qq_plot_data(data: pd.Series | np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate theoretical vs actual quantiles for a Q-Q plot.
    Returns (theoretical_quantiles, sorted_standardized_data).
    """
    if not HAS_SCIPY:
        return np.array([]), np.array([])
        
    s = _clean_series(data)
    if len(s) < 2:
        return np.array([]), np.array([])
        
    std = s.std(ddof=1)
    if std == 0 or np.isnan(std):
        return np.array([]), np.array([])
        
    standardized = (s - s.mean()) / std
    
    # stats.probplot returns only (osm, osr) when fit=False
    osm, osr = stats.probplot(standardized, dist="norm", fit=False)
    return np.asarray(osm), np.asarray(osr)


def fit_distribution(
    data: pd.Series | np.ndarray, 
    dist_name: Literal["norm", "t", "lognorm", "gamma"] = "norm"
) -> Dict[str, float]:
    """
    Fit a theoretical distribution and return its parameters.
    """
    if not HAS_SCIPY: return {}
    
    s = _clean_series(data)
    arr = s.to_numpy()
    
    # Domain checks
    if dist_name in {"lognorm", "gamma"}:
        arr = arr[arr > 0]
        if len(arr) < 2:
            return {}
            
    if len(arr) < 2:
        return {}

    dist = getattr(stats, dist_name)
    params = dist.fit(arr)
    
    # Map parameters based on distribution type
    if dist_name == "norm":
        return {"mean": float(params[0]), "std": float(params[1])}
    if dist_name == "t":
        return {"df": float(params[0]), "loc": float(params[1]), "scale": float(params[2])}
    if dist_name == "lognorm":
        return {"s": float(params[0]), "loc": float(params[1]), "scale": float(params[2])}
    if dist_name == "gamma":
        return {"a": float(params[0]), "loc": float(params[1]), "scale": float(params[2])}
        
    return {f"param_{i}": float(p) for i, p in enumerate(params)}


def distribution_fit_quality(
    data: pd.Series | np.ndarray,
    dist_name: Literal["norm", "t", "lognorm", "gamma"] = "norm",
) -> Dict[str, float]:
    """
    Fit a distribution and return log-likelihood, AIC, and BIC.
    Lower AIC/BIC is better.
    """
    if not HAS_SCIPY:
        return {}

    s = _clean_series(data)
    arr = s.to_numpy()

    if dist_name in {"lognorm", "gamma"}:
        arr = arr[arr > 0]

    if len(arr) < 3:
        return {}

    try:
        dist = getattr(stats, dist_name)
        params = dist.fit(arr)

        log_likelihood = float(np.sum(dist.logpdf(arr, *params)))
        k = len(params)
        n = len(arr)

        aic = 2 * k - 2 * log_likelihood
        bic = k * np.log(n) - 2 * log_likelihood

        return {
            "log_likelihood": log_likelihood,
            "aic": float(aic),
            "bic": float(bic),
        }
    except Exception:
        return {}


def histogram_data(
    data: pd.Series | np.ndarray,
    bins: int = 30,
) -> Dict[str, list[float]]:
    """
    Generate histogram data for UI plotting.
    """
    if bins <= 0:
        bins = 30
        
    s = _clean_series(data)
    if s.empty:
        return {"bin_edges": [], "counts": []}

    counts, bin_edges = np.histogram(s.to_numpy(), bins=bins)

    return {
        "bin_edges": [float(x) for x in bin_edges],
        "counts": [float(x) for x in counts],
    }


# =========================================================================
# Outlier Detection
# =========================================================================


def detect_outliers(
    data: pd.Series | np.ndarray, 
    method: Literal["zscore", "iqr"] = "zscore", 
    threshold: Optional[float] = None
) -> pd.Series:
    """
    Return a boolean mask where True indicates an outlier.
    
    Default Thresholds:
    - method="zscore": Defaults to 3.0 (Standard normal outlier).
    - method="iqr": Defaults to 1.5 (Tukey's IQR outlier).
    """
    s = _clean_series(data)
    if s.empty:
        return pd.Series(dtype=bool)

    if method == "zscore":
        actual_threshold = threshold if threshold is not None else 3.0
        std = s.std(ddof=1)
        if std == 0 or np.isnan(std):
            return pd.Series(False, index=s.index)
        z = np.abs((s - s.mean()) / std)
        return z > actual_threshold

    if method == "iqr":
        actual_threshold = threshold if threshold is not None else 1.5
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return pd.Series(False, index=s.index)
        lower = q1 - (actual_threshold * iqr)
        upper = q3 + (actual_threshold * iqr)
        return (s < lower) | (s > upper)

    return pd.Series(False, index=s.index)


def outlier_ratio(
    data: pd.Series | np.ndarray, 
    method: Literal["zscore", "iqr"] = "zscore",
    threshold: Optional[float] = None
) -> float:
    """Percentage of data points identified as outliers (0-100)."""
    mask = detect_outliers(data, method=method, threshold=threshold)
    if mask.empty:
        return 0.0
    return float(mask.sum() / len(mask) * 100.0)
