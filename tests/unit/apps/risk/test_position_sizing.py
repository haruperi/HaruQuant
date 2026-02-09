
import pytest
from unittest.mock import MagicMock
from apps.risk.position_sizing import PositionSizer

class MockSymbolInfo:
    def __init__(self, min_lot=0.01, max_lot=100.0, step=0.01, contract_size=100000.0):
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.step = step
        self.contract_size = contract_size
        
    def get_lots_min(self):
        return self.min_lot
    
    def get_lots_max(self):
        return self.max_lot
    
    def get_lots_step(self):
        return self.step
        
    def get_contract_size(self):
        return self.contract_size

@pytest.fixture
def mock_symbol_info():
    return MockSymbolInfo()

def test_fixed_lot_sizing():
    sizer = PositionSizer(method="fixed_lot", config={"lot_size": 0.5})
    size = sizer.calculate_size(10000, 1.1000)
    assert size == 0.5

def test_milestone_sizing():
    # Start 10k, base 0.1, milestone 1000, inc 0.1
    config = {
        "initial_balance": 10000.0,
        "base_lot_size": 0.1,
        "milestone_amount": 1000.0,
        "lot_increment": 0.1
    }
    sizer = PositionSizer(method="milestone", config=config)
    
    # At 10000 -> 0 profit -> 0 inc -> 0.1
    assert sizer.calculate_size(10000, 1.0) == 0.1
    
    # At 11500 -> 1500 profit -> 1 milestone -> 0.1 + 0.1 = 0.2
    assert sizer.calculate_size(11500, 1.0) == 0.2
    
    # At 12000 -> 2000 profit -> 2 milestones -> 0.1 + 0.2 = 0.3
    assert abs(sizer.calculate_size(12000, 1.0) - 0.3) < 0.0001

def test_fixed_risk_sizing(mock_symbol_info):
    # Risk 1% of 10000 = 100
    # Entry 1.1000, SL 1.0990 (10 pips = 0.0010 distance)
    # Contract 100000
    # Risk = Size * Contract * Distance
    # 100 = Size * 100000 * 0.0010
    # 100 = Size * 100
    # Size = 1.0
    config = {"risk_percent": 1.0}
    sizer = PositionSizer(method="fixed_risk", config=config)
    
    size = sizer.calculate_size(
        account_balance=10000,
        entry_price=1.1000,
        stop_loss=1.0990,
        symbol_info=mock_symbol_info
    )
    assert abs(size - 1.0) < 0.0001

def test_kelly_sizing():
    # Kelly = (W * AvgW - (1-W)*AvgL) / AvgW
    # W=0.5, AvgW=100, AvgL=50
    # K = (0.5*100 - 0.5*50) / 100 = (50 - 25) / 100 = 0.25
    # Limit default is 0.25, so no cap needed if calculated is 0.25 (or check cap logic)
    # Balance 10000 -> Position Value = 2500
    # Price 1.0, Contract 100000
    # Size = 2500 / (1 * 100000) = 0.025 -> round to 0.01 step -> 0.02 or 0.03?
    # Logic in code: round(size / step) * step
    # 0.025 / 0.01 = 2.5 -> round to 2 (even) or 3? Python 3 rounds to nearest even for .5 usually
    # 2.5 -> 2.0 -> 0.02
    
    # Let's use clean numbers
    # W=0.6, AvgW=100, AvgL=100
    # K = (0.6*100 - 0.4*100) / 100 = 0.2
    # Balance 100,000. Risk 20,000.
    # Price 2.0. Contract 100,000.
    # Size = 20000 / 200000 = 0.1
    
    config = {"kelly_fraction_limit": 0.5} # Allow up to 0.5
    context = {"win_rate": 0.6, "avg_win": 100, "avg_loss": 100}
    sizer = PositionSizer(method="kelly", config=config)
    
    size = sizer.calculate_size(
        account_balance=100000,
        entry_price=2.0,
        context=context,
        symbol_info=MockSymbolInfo()
    )
    assert abs(size - 0.1) < 0.0001
    
def test_volatility_sizing(mock_symbol_info):
    # Risk 1% of 10000 = 100
    # ATR = 0.0020 (20 pips)
    # Size = Risk / (ATR * Contract)
    # Size = 100 / (0.0020 * 100000) = 100 / 200 = 0.5
    
    config = {"risk_percent": 1.0}
    context = {"atr": 0.0020}
    sizer = PositionSizer(method="volatility", config=config)
    
    size = sizer.calculate_size(
        account_balance=10000,
        entry_price=1.0,
        context=context,
        symbol_info=mock_symbol_info
    )
    assert abs(size - 0.5) < 0.0001
