
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from apps.finance import distributions

@pytest.fixture
def sample_returns():
    return pd.Series([0.01, 0.02, -0.01, 0.03, -0.02])

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "profit_loss": [100.0, 200.0, -100.0, 300.0, -200.0],
        "r_multiple": [1.0, 2.0, -1.0, 3.0, -2.0]
    })

def test_return_distribution(sample_returns):
    dist = distributions.return_distribution(sample_returns)
    assert dist["mean"] == pytest.approx(0.006)
    assert dist["min"] == -0.02
    assert dist["max"] == 0.03
    
    # Empty case
    empty_dist = distributions.return_distribution(pd.Series(dtype=float))
    assert empty_dist["mean"] == 0.0

def test_trade_pnl_distribution(sample_trades):
    dist = distributions.trade_pnl_distribution(sample_trades)
    assert dist["mean"] == 60.0
    assert dist["max"] == 300.0
    
    # Missing column
    assert distributions.trade_pnl_distribution(pd.DataFrame())["mean"] == 0.0

def test_r_multiple_distribution(sample_trades):
    dist = distributions.r_multiple_distribution(sample_trades)
    assert dist["mean"] == 0.6
    assert dist["max"] == 3.0
    
    # Missing column
    assert distributions.r_multiple_distribution(pd.DataFrame())["mean"] == 0.0

def test_higher_moments(sample_returns):
    moments = distributions.higher_moments(sample_returns)
    assert "skewness" in moments
    assert "kurtosis" in moments
    
    # Insufficient data
    assert distributions.higher_moments(pd.Series([1, 2]))["skewness"] == 0.0

def test_skewness_kurtosis(sample_returns):
    s = distributions.skewness(sample_returns)
    k = distributions.kurtosis(sample_returns)
    assert isinstance(s, float)
    assert isinstance(k, float)
    
    val = distributions.skewness(pd.Series([1, 2]))
    assert val == 0.0

def test_outliers(sample_returns):
    # Add outlier
    outlier_series = pd.concat([sample_returns, pd.Series([10.0])])
    
    # IQR
    outliers_iqr = distributions.detect_outliers(outlier_series, method="iqr")
    assert outliers_iqr.iloc[-1] == True
    
    # Z-score
    outliers_z = distributions.detect_outliers(outlier_series, method="zscore", threshold=2.0)
    # 10.0 should be far from mean
    assert outliers_z.iloc[-1] == True
    
    # Ratio
    ratio = distributions.outlier_ratio(outlier_series, method="iqr")
    assert ratio > 0.0

def test_fat_tail_score(sample_returns):
    score = distributions.fat_tail_score(sample_returns)
    assert isinstance(score, float)
    
    assert distributions.fat_tail_score(pd.Series([1, 2])) == 0.0

# Mock scipy for distribution fitting tests if not installed or just to ensure coverage logic
@patch("apps.finance.distributions.HAS_SCIPY", True)
@patch("apps.finance.distributions.stats")
def test_fit_distribution_mock(mock_stats, sample_returns):
    # Setup mocks
    mock_stats.norm.fit.return_value = (0.1, 0.2)
    mock_stats.t.fit.return_value = (10, 0.1, 0.2)
    mock_stats.lognorm.fit.return_value = (0.5, 0.1, 0.2)
    mock_stats.gamma.fit.return_value = (2.0, 0.1, 0.2)
    
    # Test norm
    res = distributions.fit_distribution(sample_returns, "norm")
    assert res == {"mu": 0.1, "sigma": 0.2}
    
    # Test t
    res = distributions.fit_distribution(sample_returns, "t")
    assert res == {"df": 10.0, "loc": 0.1, "scale": 0.2}
    
    # Test others
    distributions.fit_distribution(sample_returns, "lognorm")
    distributions.fit_distribution(sample_returns, "gamma")
    
    # Test unknown
    assert distributions.fit_distribution(sample_returns, "unknown") == {}

@patch("apps.finance.distributions.HAS_SCIPY", False)
def test_fit_distribution_no_scipy(sample_returns):
    with pytest.raises(ImportError):
        distributions.fit_distribution(sample_returns, "norm")

@patch("apps.finance.distributions.HAS_SCIPY", True)
@patch("apps.finance.distributions.stats")
def test_qq_plot_mock(mock_stats, sample_returns):
    mock_stats.norm.ppf.return_value = np.array([-1, 0, 1, 2, 3])
    
    theo, sample = distributions.qq_plot_data(sample_returns)
    assert len(theo) == len(sample_returns)
    
    # Insufficient
    theo, sample = distributions.qq_plot_data(pd.Series([1]))
    assert len(theo) == 0

@patch("apps.finance.distributions.HAS_SCIPY", False)
def test_qq_plot_no_scipy(sample_returns):
    with pytest.raises(ImportError):
        distributions.qq_plot_data(sample_returns)

@patch("apps.finance.distributions.HAS_SCIPY", True)
@patch("apps.finance.distributions.stats")
def test_normality_tests_mock(mock_stats, sample_returns):
    mock_stats.jarque_bera.return_value = (1.0, 0.5)
    mock_stats.shapiro.return_value = (0.9, 0.5)
    
    jb = distributions.jarque_bera_test(sample_returns)
    assert jb["is_normal"] == True
    
    sw = distributions.shapiro_wilk_test(sample_returns)
    assert sw["is_normal"] == True

@patch("apps.finance.distributions.HAS_SCIPY", False)
def test_normality_tests_no_scipy(sample_returns):
    with pytest.raises(ImportError):
        distributions.jarque_bera_test(sample_returns)
    with pytest.raises(ImportError):
        distributions.shapiro_wilk_test(sample_returns)
