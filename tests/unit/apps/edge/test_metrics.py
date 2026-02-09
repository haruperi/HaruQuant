
import pytest
import numpy as np
from apps.edge.metrics import (
    expectancy, win_rate, profit_factor, median_mae_mfe,
    avg_win_loss, payoff_ratio, expectancy_score,
    sharpe_ratio, sortino_ratio, calmar_ratio,
    max_drawdown, max_drawdown_duration, recovery_factor,
    consecutive_wins_losses, trade_efficiency, edge_ratio,
    t_statistic, sqn, compute_trade_metrics, compute_equity_metrics
)


def test_expectancy():
    r = np.array([1.0, -0.5, 2.0, -1.0])
    assert expectancy(r) == 0.375
    assert np.isnan(expectancy([]))

def test_win_rate():
    r = np.array([1.0, -0.5, 2.0, -1.0])
    assert win_rate(r) == 0.5
    assert np.isnan(win_rate([]))

def test_profit_factor():
    r = np.array([1.0, -0.5, 2.0, -1.0])
    # Gross profit = 3.0, Gross loss = 1.5
    assert profit_factor(r) == 2.0
    
    # No losses - should return inf
    import math
    r_winners = np.array([1.0, 2.0])
    pf = profit_factor(r_winners)
    assert math.isinf(pf), f"Expected inf, got {pf}"
    
    # No wins - should return 0.0 (no profit / losses = 0)
    r_losers = np.array([-1.0, -2.0])
    assert profit_factor(r_losers) == 0.0
    
    # Empty array - should return nan
    assert np.isnan(profit_factor(np.array([])))

def test_median_mae_mfe():
    mae = np.array([-1.0, -2.0, -3.0])
    mfe = np.array([1.0, 2.0, 3.0])
    assert median_mae_mfe(mae, mfe) == (-2.0, 2.0)

def test_avg_win_loss():
    r = np.array([1.0, -0.5, 2.0, -1.0])
    assert avg_win_loss(r) == (1.5, -0.75)

def test_payoff_ratio():
    r = np.array([1.0, -0.5, 2.0, -1.0])
    # avg_win = 1.5, avg_loss = -0.75
    assert payoff_ratio(r) == 2.0

def test_expectancy_score():
    r = np.array([1.0, -0.5, 2.0, -1.0])
    # wr = 0.5, pr = 2.0
    # score = 0.5 * 2.0 - (1 - 0.5) = 1.0 - 0.5 = 0.5
    assert expectancy_score(r) == 0.5

def test_sharpe_ratio():
    returns = np.array([0.01, 0.02, -0.01, 0.03])
    # mean = 0.0125
    # std = 0.01708...
    # ratio = 0.0125 / 0.01708 * sqrt(252)
    s = sharpe_ratio(returns)
    assert s > 0
    assert not np.isnan(s)

def test_max_drawdown():
    returns = np.array([0.1, 0.1, -0.1, -0.1, 0.1])
    # 1.1, 1.21, 1.089, 0.9801, 1.078...
    # Peak is 1.21
    # Low is 0.9801
    # DD = (0.9801 - 1.21) / 1.21 = -0.19
    mdd = max_drawdown(returns)
    assert -0.2 < mdd < -0.18

def test_max_drawdown_duration():
    # curve: 100 -> 110 -> 120 -> 110 -> 100 -> 110 -> 130
    # DD starts after 120
    # 110 (1), 100 (2), 110 (3), 130 (rec)
    returns = np.array([0.1, 0.1, -0.1, -0.1, 0.1, 0.2])
    assert max_drawdown_duration(returns) >= 2

def test_consecutive_wins_losses():
    r = np.array([1, 1, -1, 1, -1, -1, -1, 1])
    wins, losses = consecutive_wins_losses(r)
    assert wins == 2
    assert losses == 3

def test_trade_efficiency():
    r = np.array([1.0, 2.0])
    mfe = np.array([2.0, 4.0])
    # eff: 0.5, 0.5 -> mean 0.5
    assert trade_efficiency(r, mfe) == 0.5

def test_edge_ratio():
    mfe = np.array([2.0, 4.0])
    mae = np.array([-1.0, -2.0])
    # ratio: 2/1, 4/2 -> 2.0, 2.0 -> mean 2.0
    assert edge_ratio(mfe, mae) == 2.0

def test_sqn():
    r = np.array([1.0] * 30 + [-1.0] * 10) # 40 trades
    # just check it returns a float
    assert isinstance(sqn(r), float)


def test_sortino_ratio():
    """Test Sortino ratio calculation."""
    returns = np.array([0.01, 0.02, -0.01, 0.03, -0.005])
    s = sortino_ratio(returns)
    assert s > 0
    assert not np.isnan(s)
    
    # All positive returns - should return inf
    returns_positive = np.array([0.01, 0.02, 0.03])
    assert np.isinf(sortino_ratio(returns_positive))
    
    # Insufficient data
    assert np.isnan(sortino_ratio(np.array([0.01])))


def test_calmar_ratio():
    """Test Calmar ratio calculation."""
    returns = np.array([0.1, 0.1, -0.1, -0.1, 0.1])
    c = calmar_ratio(returns)
    assert isinstance(c, float)
    assert not np.isnan(c)
    
    # No drawdown - should return inf for positive returns
    returns_up = np.array([0.1, 0.1, 0.1])
    assert np.isinf(calmar_ratio(returns_up))


def test_recovery_factor():
    """Test recovery factor calculation."""
    returns = np.array([0.1, 0.1, -0.1, -0.1, 0.1])
    rf = recovery_factor(returns)
    assert isinstance(rf, float)
    assert not np.isnan(rf)
    
    # Empty array
    assert np.isnan(recovery_factor(np.array([])))


def test_t_statistic():
    """Test t-statistic calculation."""
    # Positive expectancy
    r = np.array([1.0, 2.0, 1.5, 1.8, 2.2])
    t = t_statistic(r)
    assert t > 0
    
    # Negative expectancy
    r_neg = np.array([-1.0, -2.0, -1.5])
    t_neg = t_statistic(r_neg)
    assert t_neg < 0
    
    # Insufficient data
    assert np.isnan(t_statistic(np.array([1.0])))
    
    # Zero std - should return inf
    r_same = np.array([1.0, 1.0, 1.0])
    assert np.isinf(t_statistic(r_same))


def test_compute_trade_metrics():
    """Test comprehensive trade metrics computation."""
    r = np.array([1.0, -0.5, 2.0, -1.0, 1.5])
    mae = np.array([-0.3, -0.8, -0.2, -1.2, -0.4])
    mfe = np.array([1.2, 0.1, 2.5, 0.2, 1.8])
    
    metrics = compute_trade_metrics(r, mae, mfe)
    
    assert metrics["n_trades"] == 5
    assert "expectancy" in metrics
    assert "win_rate" in metrics
    assert "profit_factor" in metrics
    assert "sqn" in metrics
    assert "t_stat" in metrics
    assert "avg_win" in metrics
    assert "avg_loss" in metrics
    assert "payoff_ratio" in metrics
    assert "max_consecutive_wins" in metrics
    assert "max_consecutive_losses" in metrics
    assert "median_mae" in metrics
    assert "median_mfe" in metrics
    assert "edge_ratio" in metrics
    assert "trade_efficiency" in metrics


def test_compute_trade_metrics_no_mae_mfe():
    """Test trade metrics without MAE/MFE."""
    r = np.array([1.0, -0.5, 2.0])
    metrics = compute_trade_metrics(r)
    
    assert metrics["n_trades"] == 3
    assert "median_mae" not in metrics
    assert "median_mfe" not in metrics
    assert "edge_ratio" not in metrics
    assert "trade_efficiency" not in metrics


def test_compute_equity_metrics():
    """Test equity curve metrics computation."""
    returns = np.array([0.01, 0.02, -0.01, 0.03, -0.005])
    metrics = compute_equity_metrics(returns)
    
    assert "total_return" in metrics
    assert "annual_return" in metrics
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "calmar_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "max_dd_duration" in metrics
    assert "recovery_factor" in metrics
    
    # Check values are reasonable
    assert not np.isnan(metrics["total_return"])
    assert not np.isnan(metrics["annual_return"])


def test_edge_cases():
    """Test edge cases for various metrics."""
    # Empty arrays
    assert np.isnan(expectancy(np.array([])))
    assert np.isnan(win_rate(np.array([])))
    
    # Single value
    assert expectancy(np.array([1.0])) == 1.0
    assert win_rate(np.array([1.0])) == 1.0
    assert win_rate(np.array([-1.0])) == 0.0
    
    # All zeros - no wins, no losses
    r_zeros = np.array([0.0, 0.0, 0.0])
    assert expectancy(r_zeros) == 0.0
    assert win_rate(r_zeros) == 0.0
    # profit_factor with no wins and no losses returns nan
    assert np.isnan(profit_factor(r_zeros))


