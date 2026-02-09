
from unittest.mock import Mock
from datetime import datetime
import pandas as pd
import pytest
from apps.live.bar_monitor import BarMonitor

@pytest.fixture
def mock_client():
    return Mock()

@pytest.fixture
def monitor(mock_client):
    return BarMonitor(mock_client, "EURUSD", "H1")

def test_initialization(monitor):
    assert monitor.symbol == "EURUSD"
    assert monitor.timeframe == "H1"
    assert monitor._last_bar_time is None

def test_get_historical_data_success(monitor, mock_client):
    # Prepare dummy data
    dates = pd.date_range("2023-01-01", periods=10, freq="H")
    df = pd.DataFrame({"close": range(10)}, index=dates)
    mock_client.get_bars.return_value = df
    
    result = monitor.get_historical_data(10)
    
    assert result is not None
    assert len(result) == 10
    # Last closed bar is index -2 (9th item)
    assert monitor._last_bar_time == dates[-2]

def test_get_historical_data_failure(monitor, mock_client):
    mock_client.get_bars.return_value = None
    assert monitor.get_historical_data(10) is None
    
    mock_client.get_bars.return_value = pd.DataFrame() # Empty
    assert monitor.get_historical_data(10) is None

def test_check_new_bar_no_previous(monitor, mock_client):
    # First run, should fetch bars and init last_bar_time, returning False
    dates = pd.date_range("2023-01-01", periods=2, freq="H")
    df = pd.DataFrame({"close": [1, 2]}, index=dates)
    mock_client.get_bars.return_value = df
    
    assert monitor.check_new_bar() is False
    assert monitor._last_bar_time == dates[-2]

def test_check_new_bar_same_bar(monitor, mock_client):
    dates = pd.date_range("2023-01-01", periods=2, freq="H")
    monitor._last_bar_time = dates[-2] # Set current detected as index -2
    
    df = pd.DataFrame({"close": [1, 2]}, index=dates)
    mock_client.get_bars.return_value = df
    
    assert monitor.check_new_bar() is False

def test_check_new_bar_detected(monitor, mock_client):
    dates = pd.date_range("2023-01-01", periods=3, freq="H")
    # Previous check saw dates[-3] as last closed bar
    monitor._last_bar_time = dates[-3]
    
    # Now we have [dates[-2], dates[-1]] returned by get_bars(count=2)
    # Wait, get_bars(count=2) returns last 2 bars available.
    # If we advanced 1 bar, the new last 2 bars are dates[-2] and dates[-1].
    # The new last closed bar is dates[-2].
    
    df = pd.DataFrame({"close": [2, 3]}, index=dates[-2:])
    mock_client.get_bars.return_value = df
    
    assert monitor.check_new_bar() is True
    assert monitor._last_bar_time == dates[-2]

def test_get_last_closed_bar_success(monitor, mock_client):
    dates = pd.date_range("2023-01-01", periods=2, freq="H")
    df = pd.DataFrame(
        {"open": [1.1, 1.2], "high": [1.15, 1.25], "low": [1.05, 1.15], "close": [1.12, 1.22]},
        index=dates
    )
    mock_client.get_bars.return_value = df
    
    bar = monitor.get_last_closed_bar()
    assert bar is not None
    assert bar.name == dates[-2]
    assert bar["close"] == 1.12

def test_get_last_closed_bar_fail(monitor, mock_client):
    mock_client.get_bars.return_value = None
    assert monitor.get_last_closed_bar() is None
