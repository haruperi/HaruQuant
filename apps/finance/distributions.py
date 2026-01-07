"""
Statistical structure of returns & trades.

Used heavily in Monte Carlo & ML
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
# Distribution Analysis
# =========================================================================


def return_distribution(returns: pd.Series) -> Dict[str, float]:
    """
    Statistical summary of returns distribution.

    Args:
        returns: Returns series

    Returns:
        Dict with mean, median, std, skew, kurtosis, min, max
    """
    if len(returns) == 0:
        return {
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

    return {
        "mean": float(returns.mean()),
        "median": float(returns.median()),
        "std": float(returns.std()),
        "skew": float(returns.skew()),
        "kurtosis": float(returns.kurtosis()),
        "min": float(returns.min()),
        "max": float(returns.max()),
        "q25": float(returns.quantile(0.25)),
        "q75": float(returns.quantile(0.75)),
    }


def trade_pnl_distribution(trades: pd.DataFrame) -> Dict[str, float]:
    """
    Statistical summary of trade P&L distribution.

    Args:
        trades: Trades DataFrame

    Returns:
        Dict with distribution statistics
    """
    if len(trades) == 0 or "profit_loss" not in trades.columns:
        return {
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
    """
    Statistical summary of R-multiple distribution.

    Args:
        trades: Trades DataFrame

    Returns:
        Dict with distribution statistics
    """
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return {
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
# Distribution Fitting
# =========================================================================


def fit_distribution(
    data: pd.Series, dist_name: Literal["norm", "t", "lognorm", "gamma"] = "norm"
) -> Dict[str, float]:
    """
    Fit distribution to data.

    Args:
        data: Data series
        dist_name: Distribution name ('norm', 't', 'lognorm', 'gamma')

    Returns:
        Dict with distribution parameters
    """
    if not HAS_SCIPY:
        raise ImportError(
            "scipy is required for distribution fitting. Install with: pip install scipy"
        )

    if len(data) < 2:
        return {}

    data_array = data.values

    if dist_name == "norm":
        # Normal distribution
        mu, sigma = stats.norm.fit(data_array)
        return {"mu": float(mu), "sigma": float(sigma)}

    elif dist_name == "t":
        # Student's t-distribution
        df, loc, scale = stats.t.fit(data_array)
        return {"df": float(df), "loc": float(loc), "scale": float(scale)}

    elif dist_name == "lognorm":
        # Log-normal distribution
        shape, loc, scale = stats.lognorm.fit(data_array, floc=0)
        return {"shape": float(shape), "loc": float(loc), "scale": float(scale)}

    elif dist_name == "gamma":
        # Gamma distribution
        shape, loc, scale = stats.gamma.fit(data_array, floc=0)
        return {"shape": float(shape), "loc": float(loc), "scale": float(scale)}

    return {}


def qq_plot_data(data: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate Q-Q plot data for normality test.

    Args:
        data: Data series

    Returns:
        Tuple of (theoretical_quantiles, sample_quantiles)
    """
    if not HAS_SCIPY:
        raise ImportError(
            "scipy is required for Q-Q plot. Install with: pip install scipy"
        )

    if len(data) < 2:
        return (np.array([]), np.array([]))

    # Standardize data
    standardized = (data - data.mean()) / data.std()

    # Sort data
    sorted_data = np.sort(standardized.values)

    # Theoretical quantiles (normal distribution)
    n = len(sorted_data)
    theoretical = stats.norm.ppf(np.linspace(0.01, 0.99, n))

    return (theoretical, sorted_data)


def fat_tail_score(returns: pd.Series) -> float:
    """
    Fat tail score - kurtosis-based measure.

    Measures how "fat" the tails are compared to normal distribution

    Args:
        returns: Returns series

    Returns:
        Fat tail score (excess kurtosis)
        - 0: Normal distribution
        - > 0: Fat tails (more extreme events)
        - < 0: Thin tails (fewer extreme events)
    """
    if len(returns) < 4:
        return 0.0

    # Excess kurtosis (kurtosis - 3 for normal)
    return float(returns.kurtosis())


# =========================================================================
# Normality Tests
# =========================================================================


def jarque_bera_test(returns: pd.Series) -> Dict[str, float]:
    """
    Jarque-Bera test for normality.

    Tests whether returns follow normal distribution

    Args:
        returns: Returns series

    Returns:
        Dict with statistic, p_value, is_normal
    """
    if not HAS_SCIPY:
        raise ImportError(
            "scipy is required for Jarque-Bera test. Install with: pip install scipy"
        )

    if len(returns) < 4:
        return {"statistic": 0.0, "p_value": 1.0, "is_normal": True}

    statistic, p_value = stats.jarque_bera(returns.values)

    # Typically reject normality if p < 0.05
    is_normal = p_value > 0.05

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "is_normal": bool(is_normal),
    }


def shapiro_wilk_test(returns: pd.Series) -> Dict[str, float]:
    """
    Shapiro-Wilk test for normality.

    More powerful test for small samples

    Args:
        returns: Returns series

    Returns:
        Dict with statistic, p_value, is_normal
    """
    if not HAS_SCIPY:
        raise ImportError(
            "scipy is required for Shapiro-Wilk test. Install with: pip install scipy"
        )

    if len(returns) < 3:
        return {"statistic": 0.0, "p_value": 1.0, "is_normal": True}

    # Shapiro-Wilk test limited to 5000 samples
    sample = returns.values
    if len(sample) > 5000:
        sample = np.random.choice(sample, 5000, replace=False)

    statistic, p_value = stats.shapiro(sample)

    is_normal = p_value > 0.05

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "is_normal": bool(is_normal),
    }


# =========================================================================
# Higher Moments
# =========================================================================


def higher_moments(data: pd.Series) -> Dict[str, float]:
    """
    Calculate higher statistical moments.

    Args:
        data: Data series

    Returns:
        Dict with skewness, kurtosis, and derived measures
    """
    if len(data) < 4:
        return {
            "skewness": 0.0,
            "kurtosis": 0.0,
            "excess_kurtosis": 0.0,
        }

    skew = data.skew()
    kurt = data.kurtosis()  # Pandas returns excess kurtosis

    return {
        "skewness": float(skew),
        "excess_kurtosis": float(kurt),
        "kurtosis": float(kurt + 3),  # Total kurtosis
    }


# =========================================================================
# Outlier Detection
# =========================================================================


def detect_outliers(
    data: pd.Series, method: Literal["iqr", "zscore"] = "iqr", threshold: float = 3.0
) -> pd.Series:
    """
    Detect outliers in data.

    Args:
        data: Data series
        method: Detection method ('iqr' or 'zscore')
        threshold: Threshold for outlier detection
            - IQR: multiplier for IQR (default 3.0)
            - Z-score: number of std deviations (default 3.0)

    Returns:
        Boolean series indicating outliers
    """
    if len(data) == 0:
        return pd.Series(dtype=bool)

    if method == "iqr":
        # IQR method
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr

        outliers = (data < lower_bound) | (data > upper_bound)

    elif method == "zscore":
        # Z-score method
        z_scores = np.abs((data - data.mean()) / data.std())
        outliers = z_scores > threshold

    else:
        outliers = pd.Series(False, index=data.index)

    return outliers


def outlier_ratio(data: pd.Series, **kwargs) -> float:
    """
    Percentage of outliers in data.

    Args:
        data: Data series
        **kwargs: Arguments passed to detect_outliers

    Returns:
        Outlier ratio (0-1)
    """
    if len(data) == 0:
        return 0.0

    outliers = detect_outliers(data, **kwargs)
    return float(outliers.sum() / len(data))
