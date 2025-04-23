"""
Tests for utility functions and helper methods.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.utils import (
    retry_on_exception,
    format_price,
    calculate_pip_value,
    calculate_position_size,
    calculate_technical_indicators,
    calculate_volatility,
    calculate_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_average_win_loss,
    calculate_expectancy,
    format_trade_result,
    format_performance_metrics
)

@pytest.mark.asyncio
async def test_retry_on_exception():
    """Test the retry_on_exception decorator."""
    attempts = 0
    
    @retry_on_exception(max_attempts=3, delay=0.1)
    async def failing_function():
        nonlocal attempts
        attempts += 1
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        await failing_function()
    
    assert attempts == 3

def test_format_price():
    """Test price formatting."""
    assert format_price(1.23456789, 2) == "1.23"
    assert format_price(Decimal("1.23456789"), 4) == "1.2346"
    assert format_price(0.00001, 5) == "0.00001"

def test_calculate_pip_value():
    """Test pip value calculation."""
    # Test standard pairs
    assert calculate_pip_value("EURUSD", 1.1000) == 0.0001
    assert calculate_pip_value("GBPUSD", 1.3000) == 0.0001
    
    # Test JPY pairs
    assert calculate_pip_value("USDJPY", 110.00) == 0.01
    assert calculate_pip_value("EURJPY", 130.00) == 0.01
    
    # Test with different lot sizes
    assert calculate_pip_value("EURUSD", 1.1000, lot_size=0.1) == 0.00001
    assert calculate_pip_value("USDJPY", 110.00, lot_size=0.1) == 0.001

def test_calculate_position_size():
    """Test position size calculation."""
    # Test with standard parameters
    size = calculate_position_size(
        account_balance=10000,
        risk_percent=1,
        stop_loss_pips=50,
        symbol="EURUSD",
        price=1.1000
    )
    assert abs(size - 0.18) < 0.01
    
    # Test with JPY pair
    size = calculate_position_size(
        account_balance=10000,
        risk_percent=1,
        stop_loss_pips=50,
        symbol="USDJPY",
        price=110.00
    )
    assert abs(size - 0.18) < 0.01

def test_calculate_technical_indicators():
    """Test technical indicator calculations."""
    # Create sample data
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    data = pd.DataFrame({
        "Open": np.random.normal(100, 1, 100),
        "High": np.random.normal(101, 1, 100),
        "Low": np.random.normal(99, 1, 100),
        "Close": np.random.normal(100, 1, 100),
        "Volume": np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Test SMA
    indicators = [{"name": "SMA", "params": {"period": 20}}]
    result = calculate_technical_indicators(data, indicators)
    assert "SMA_20" in result.columns
    assert not result["SMA_20"].isna().all()
    
    # Test RSI
    indicators = [{"name": "RSI", "params": {"period": 14}}]
    result = calculate_technical_indicators(data, indicators)
    assert "RSI_14" in result.columns
    assert not result["RSI_14"].isna().all()
    
    # Test MACD
    indicators = [{"name": "MACD"}]
    result = calculate_technical_indicators(data, indicators)
    assert "MACD_12_26" in result.columns
    assert "MACD_Signal_9" in result.columns
    assert "MACD_Hist_12_26_9" in result.columns

def test_calculate_volatility():
    """Test volatility calculation."""
    # Create sample data
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    data = pd.DataFrame({
        "Close": np.random.normal(100, 1, 100)
    }, index=dates)
    
    volatility = calculate_volatility(data)
    assert isinstance(volatility, pd.Series)
    assert not volatility.isna().all()

def test_calculate_drawdown():
    """Test drawdown calculation."""
    # Create sample equity curve
    equity = pd.Series([100, 110, 105, 120, 115, 130])
    drawdown = calculate_drawdown(equity)
    
    assert isinstance(drawdown, pd.Series)
    assert drawdown.min() <= 0
    assert drawdown.max() == 0

def test_calculate_sharpe_ratio():
    """Test Sharpe ratio calculation."""
    # Create sample returns
    returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
    sharpe = calculate_sharpe_ratio(returns)
    
    assert isinstance(sharpe, float)
    assert not np.isnan(sharpe)

def test_calculate_sortino_ratio():
    """Test Sortino ratio calculation."""
    # Create sample returns
    returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
    sortino = calculate_sortino_ratio(returns)
    
    assert isinstance(sortino, float)
    assert not np.isnan(sortino)

def test_calculate_max_drawdown():
    """Test maximum drawdown calculation."""
    # Create sample equity curve
    equity = pd.Series([100, 110, 105, 120, 115, 130])
    max_dd = calculate_max_drawdown(equity)
    
    assert isinstance(max_dd, float)
    assert max_dd <= 0

def test_calculate_win_rate():
    """Test win rate calculation."""
    # Create sample trades
    trades = pd.DataFrame({
        "profit": [100, -50, 200, -30, 150]
    })
    
    win_rate = calculate_win_rate(trades)
    assert isinstance(win_rate, float)
    assert 0 <= win_rate <= 100
    assert abs(win_rate - 60) < 0.1  # 3 winning trades out of 5

def test_calculate_profit_factor():
    """Test profit factor calculation."""
    # Create sample trades
    trades = pd.DataFrame({
        "profit": [100, -50, 200, -30, 150]
    })
    
    pf = calculate_profit_factor(trades)
    assert isinstance(pf, float)
    assert pf > 0

def test_calculate_average_win_loss():
    """Test average win/loss calculation."""
    # Create sample trades
    trades = pd.DataFrame({
        "profit": [100, -50, 200, -30, 150]
    })
    
    avg = calculate_average_win_loss(trades)
    assert isinstance(avg, dict)
    assert "average_win" in avg
    assert "average_loss" in avg
    assert avg["average_win"] > 0
    assert avg["average_loss"] < 0

def test_calculate_expectancy():
    """Test expectancy calculation."""
    # Create sample trades
    trades = pd.DataFrame({
        "profit": [100, -50, 200, -30, 150]
    })
    
    expectancy = calculate_expectancy(trades)
    assert isinstance(expectancy, float)

def test_format_trade_result():
    """Test trade result formatting."""
    result = format_trade_result(
        symbol="EURUSD",
        order_type="BUY",
        volume=0.1,
        entry_price=1.1000,
        exit_price=1.1050,
        profit=50,
        duration=timedelta(hours=1)
    )
    
    assert isinstance(result, str)
    assert "EURUSD" in result
    assert "BUY" in result
    assert "0.1" in result
    assert "1.1000" in result
    assert "1.1050" in result
    assert "50" in result

def test_format_performance_metrics():
    """Test performance metrics formatting."""
    # Create sample data
    equity = pd.Series([10000, 10100, 10200, 10150, 10300])
    trades = pd.DataFrame({
        "profit": [100, -50, 200, -30, 150]
    })
    
    metrics = format_performance_metrics(equity, trades)
    
    assert isinstance(metrics, dict)
    assert "total_return" in metrics
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "win_rate" in metrics
    assert "profit_factor" in metrics
    assert "expectancy" in metrics 