
from apps.live.models import Signal, SignalType

def test_signal_type_enum():
    assert SignalType.BUY == "buy"
    assert SignalType.SELL == "sell"
    assert SignalType.CLOSE == "close"
    assert SignalType.CLOSE_BUY == "close buy"
    assert SignalType.CLOSE_SELL == "close sell"

def test_signal_model_creation():
    signal = Signal(
        symbol="EURUSD",
        timeframe="H1",
        signal_type=SignalType.BUY,
        signal_time="2023-01-01 12:00:00",
        entry_price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1200,
        metadata={"strategy": "test"}
    )
    
    assert signal.symbol == "EURUSD"
    assert signal.timeframe == "H1"
    assert signal.signal_type == "buy"
    assert signal.signal_time == "2023-01-01 12:00:00"
    assert signal.entry_price == 1.1000
    assert signal.stop_loss == 1.0900
    assert signal.take_profit == 1.1200
    assert signal.metadata == {"strategy": "test"}

def test_signal_model_optional_fields():
    signal = Signal(
        symbol="GBPUSD",
        timeframe="M15",
        signal_type="sell",
        signal_time="2023-01-01 13:00:00"
    )
    
    assert signal.symbol == "GBPUSD"
    assert signal.entry_price is None
    assert signal.risk_pips is None
    
def test_signal_risk_fields():
    signal = Signal(
        symbol="USDJPY",
        timeframe="D1",
        signal_type="buy",
        signal_time="2023-01-01 14:00:00",
        risk_pips=50,
        risk_usd=100.0,
        position_size=1.5,
        reward_risk_ratio=2.5
    )
    
    assert signal.risk_pips == 50
    assert signal.risk_usd == 100.0
    assert signal.position_size == 1.5
    assert signal.reward_risk_ratio == 2.5
