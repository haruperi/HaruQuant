
import pytest
import pandas as pd
import numpy as np
from apps.finance import returns

@pytest.fixture
def sample_equity():
    return pd.Series([100.0, 110.0, 105.0, 120.0], index=pd.date_range("2023-01-01", periods=4))

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "profit_loss": [10.0, -5.0, 15.0],
        "open_time": pd.date_range("2023-01-01 10:00", periods=3, freq="h"),
        "close_time": pd.date_range("2023-01-01 10:30", periods=3, freq="h")
    })

def test_buy_and_hold_return(sample_equity):
    # 100 -> 120 = 20%
    assert returns.buy_and_hold_return(sample_equity) == 20.0

def test_buy_and_hold_cagr(sample_equity):
    # Short period, huge CAGR
    cagr = returns.buy_and_hold_cagr(sample_equity)
    assert cagr > 0.0

def test_total_return(sample_equity):
    # 120-100 = 20
    assert returns.total_return(sample_equity) == 20.0

def test_net_profit(sample_trades):
    # 10 - 5 + 15 = 20
    assert returns.net_profit(sample_trades) == 20.0

def test_gross_profit(sample_trades):
    # 10 + 15 = 25
    assert returns.gross_profit(sample_trades) == 25.0

def test_gross_loss(sample_trades):
    # -5
    assert returns.gross_loss(sample_trades) == -5.0

def test_equity_curve(sample_trades):
    eq = returns.equity_curve(sample_trades, 100.0)
    # Start 100. Trade 1 (+10) -> 110. Trade 2 (-5) -> 105. Trade 3 (+15) -> 120.
    assert eq.iloc[-1] == 120.0
    assert eq.iloc[0] == 100.0 # Initial point added

def test_returns_series(sample_equity):
    # 110/100-1 = 0.1
    # 105/110-1 = -0.045
    # 120/105-1 = 0.142
    ret = returns.returns_series(sample_equity)
    assert len(ret) == 3
    assert ret.iloc[0] == pytest.approx(0.1)

def test_log_returns_series(sample_equity):
    log_ret = returns.log_returns_series(sample_equity)
    expected = np.log(sample_equity / sample_equity.shift(1)).dropna()
    pd.testing.assert_series_equal(log_ret, expected)

def test_period_returns(sample_equity):
    # Daily returns
    daily = returns.daily_returns(sample_equity)
    assert isinstance(daily, pd.Series)

def test_cagr(sample_equity):
    # 3 days (approx 0.008 years)
    # Gain 20%
    # CAGR >> 20%
    assert returns.cagr(sample_equity) > 20.0

def test_annualized_return(sample_equity):
    ret = returns.returns_series(sample_equity)
    # Daily returns ~ 0.1, -0.04, 0.14
    # Annualized should be high
    ann = returns.annualized_return(ret)
    assert ann > 0.0

def test_geometric_mean_return(sample_equity):
    ret = returns.returns_series(sample_equity)
    geo = returns.geometric_mean_return(ret)
    assert geo > -1.0 and geo < 1.0

def test_return_volatility(sample_equity):
    ret = returns.returns_series(sample_equity)
    vol = returns.return_volatility(ret)
    assert vol > 0.0

def test_downside_return_volatility(sample_equity):
    # Create specific data with multiple downside returns
    # Returns: -0.01, -0.02, 0.05
    prices = pd.Series([100, 99, 97.02, 101.871])
    ret = returns.returns_series(prices)
    down_vol = returns.downside_return_volatility(ret)
    assert down_vol >= 0.0

def test_skewness_kurtosis(sample_equity):
    ret = returns.returns_series(sample_equity)
    assert isinstance(returns.return_skewness(ret), float)
    assert isinstance(returns.return_kurtosis(ret), float)

def test_adjusted_profit(sample_trades):
    # Winners: 2. Avg 12.5. N=2. Adj N = 2-sqrt(2) = 0.58...
    # Adj Gross ~ 0.58 * 12.5 ~ 7.3
    adj_gross = returns.adjusted_gross_profit(sample_trades)
    assert adj_gross < 25.0
    
    # Losers: 1. Avg -5. N=1. Adj N = 1+1 = 2.
    # Adj Gross Loss ~ 2 * -5 = -10.
    adj_loss = returns.adjusted_gross_loss(sample_trades)
    assert adj_loss < -5.0

def test_select_net_profit(sample_trades):
    # No outliers in sample (std is small)
    sel = returns.select_net_profit(sample_trades)
    assert sel == 20.0

def test_outlier_removal():
    # Need enough data points so single outlier doesn't skew mean/std too much
    # 100 trades of 10, 1 trade of 1000
    pnl = [10.0] * 50 + [10000.0]
    outliers = pd.DataFrame({"profit_loss": pnl})
    # 10000 should be outlier
    res = returns.select_net_profit(outliers)
    assert res == 500.0

def test_return_ratios(sample_equity, sample_trades):
    # Return on Max Strat DD
    # DD: 110->105 = 5.
    # Total return 20.
    # Ratio 4.0
    assert returns.return_on_max_strategy_drawdown(sample_equity) == 4.0
    
    # Return on Account
    # Profit 20.
    # Max trade DD: Need to check. 
    # Trades: +10 (110), -5 (105), +15 (120).
    # 1. Eq 110.
    # 2. Eq 105. DD 5.
    # 3. Eq 120.
    # Max DD 5.
    # Expected Return on Account: 20/5 = 4.0
    assert returns.return_on_account(sample_trades) == 4.0
    
    assert returns.return_on_initial_capital(sample_trades, 100.0) == 0.2
