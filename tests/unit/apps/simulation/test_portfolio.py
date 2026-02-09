
import pytest
import pandas as pd
from unittest.mock import MagicMock
from apps.simulation.portfolio import PortfolioStrategy

@pytest.fixture
def mock_strategy():
    strategy = MagicMock()
    return strategy

@pytest.fixture
def mock_symbol_specs():
    specs = {
        "EURUSD": MagicMock(),
        "GBPUSD": MagicMock()
    }
    return specs

@pytest.fixture
def sample_data():
    date_range = pd.date_range("2023-01-01", periods=10, freq="h")
    data = {
        "EURUSD": pd.DataFrame({"close": [1.0, 1.01, 1.02, 1.01, 1.0, 0.99, 1.0, 1.01, 1.02, 1.03]}, index=date_range),
        "GBPUSD": pd.DataFrame({"close": [1.2, 1.21, 1.22, 1.21, 1.2, 1.19, 1.2, 1.21, 1.22, 1.23]}, index=date_range)
    }
    return data

def test_portfolio_strategy_init(mock_strategy, mock_symbol_specs, sample_data):
    strategies = {"EURUSD": mock_strategy, "GBPUSD": mock_strategy}
    
    # Valid init
    ps = PortfolioStrategy(strategies, mock_symbol_specs, sample_data)
    assert ps.allocation_method == "equal_weight"

def test_validate_mismatch(mock_strategy, mock_symbol_specs, sample_data):
    # Strategies has EXTRA symbol
    strategies = {"EURUSD": mock_strategy, "GBPUSD": mock_strategy, "USDJPY": mock_strategy}
    
    with pytest.raises(ValueError, match="don't match"):
        PortfolioStrategy(strategies, mock_symbol_specs, sample_data)

def test_equal_weight_allocation(mock_strategy, mock_symbol_specs, sample_data):
    strategies = {"EURUSD": mock_strategy, "GBPUSD": mock_strategy}
    ps = PortfolioStrategy(strategies, mock_symbol_specs, sample_data, max_total_exposure=1.0)
    
    allocations = ps.calculate_allocations()
    assert allocations["EURUSD"] == 0.5
    assert allocations["GBPUSD"] == 0.5

def test_risk_parity_allocation(mock_strategy, mock_symbol_specs, sample_data):
    # EURUSD vol: std([1.0, 1.01, ...]) -> small
    # Create distinct volatility
    date_range = pd.date_range("2023-01-01", periods=5)
    # Volatile asset
    data_high_vol = pd.DataFrame({"close": [100, 105, 95, 110, 90]}, index=date_range) 
    # Stable asset
    data_low_vol = pd.DataFrame({"close": [100, 101, 99, 102, 98]}, index=date_range)
    
    data = {
        "HIGH": data_high_vol,
        "LOW": data_low_vol
    }
    specs = {"HIGH": MagicMock(), "LOW": MagicMock()}
    strategies = {"HIGH": mock_strategy, "LOW": mock_strategy}
    
    ps = PortfolioStrategy(strategies, specs, data, allocation_method="risk_parity")
    allocations = ps.calculate_allocations()
    
    # Low vol should have higher allocation
    assert allocations["LOW"] > allocations["HIGH"]
    # Total should sum to max_exposure (1.0)
    assert abs(sum(allocations.values()) - 1.0) < 0.0001
