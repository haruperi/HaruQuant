
from unittest.mock import Mock
import pandas as pd
import pytest
from apps.live.signal_processor import SignalProcessor

@pytest.fixture
def mock_strategy():
    strategy = Mock()
    strategy.on_bar.side_effect = lambda df: df # Identity
    strategy.get_signal.return_value = None
    return strategy

@pytest.fixture
def processor(mock_strategy):
    return SignalProcessor(mock_strategy, max_bars=10)

def test_initialize_empty(processor):
    assert processor.initialize(pd.DataFrame()) is False
    assert processor.initialize(None) is False

def test_initialize_success(processor, mock_strategy):
    df = pd.DataFrame({"close": [1, 2, 3]})
    
    mock_strategy.on_bar.return_value = df
    
    assert processor.initialize(df) is True
    assert processor._initialized is True
    assert len(processor._data) == 3

def test_update_with_new_bar_not_initialized(processor):
    assert processor.update_with_new_bar(pd.Series([4])) is None

def test_update_with_new_bar(processor, mock_strategy):
    # Init
    df = pd.DataFrame({"close": [1, 2, 3]})
    mock_strategy.on_bar.return_value = df
    processor.initialize(df)
    
    # Update
    new_bar = pd.Series([4], index=["close"])
    
    # Strategy should return dataframe with appended bar
    # Mock simulation:
    def on_bar_side_effect(df):
        return df
    mock_strategy.on_bar.side_effect = on_bar_side_effect
    
    mock_strategy.get_signal.return_value = {"signal": "buy"}
    
    signal = processor.update_with_new_bar(new_bar)
    
    assert len(processor._data) == 4
    assert signal == {"signal": "buy"}
    mock_strategy.on_bar.assert_called()
    mock_strategy.get_signal.assert_called()

def test_max_bars_trimming(processor, mock_strategy):
    # Max bars 10
    df = pd.DataFrame({"close": list(range(10))})
    mock_strategy.on_bar.return_value = df
    processor.initialize(df)
    
    # Add one more
    new_bar = pd.Series([10], index=["close"])
    # We need to mock on_bar to just return what we pass it or similar, 
    # but signal processor appends BEFORE calling on_bar.
    # processor._append_new_bar -> _data has 11 rows -> trimmed to 10.
    
    mock_strategy.on_bar.side_effect = lambda x: x
    
    processor.update_with_new_bar(new_bar)
    
    assert len(processor._data) == 10
    assert processor._data.iloc[-1]["close"] == 10
    assert processor._data.iloc[0]["close"] == 1

def test_get_last_signal(processor, mock_strategy):
    df = pd.DataFrame({"close": [1]})
    mock_strategy.on_bar.return_value = df
    processor.initialize(df)
    
    mock_strategy.get_signal.return_value = {"signal": "sell"}
    
    assert processor.get_last_signal() == {"signal": "sell"}
