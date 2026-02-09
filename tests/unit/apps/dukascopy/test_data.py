
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
import pandas as pd
from apps.dukascopy.data import (
    _resample_to_nearest,
    _get_dataframe_columns_for_timeunit,
    _process_stream_row,
    _should_continue_streaming,
    _handle_stream_error,
    _process_stream_batch,
    _stream,
    fetch,
    live_fetch,
    TIME_UNIT_MIN,
    TIME_UNIT_HOUR,
    TIME_UNIT_DAY,
    TIME_UNIT_WEEK,
    TIME_UNIT_MONTH,
    TIME_UNIT_SEC,
    TIME_UNIT_TICK,
    INTERVAL_TICK,
    INTERVAL_MIN_1,
    OFFER_SIDE_BID,
    OFFER_SIDE_ASK,
    _fetch
)

def test_resample_to_nearest_min():
    timestamp = datetime(2023, 1, 1, 10, 17, 30)
    # Resample to nearest 15 mins
    result = _resample_to_nearest(timestamp, TIME_UNIT_MIN, 15)
    assert result == datetime(2023, 1, 1, 10, 15, 0)

def test_resample_to_nearest_hour():
    timestamp = datetime(2023, 1, 1, 14, 45, 0)
    # Resample to nearest 4 hours
    result = _resample_to_nearest(timestamp, TIME_UNIT_HOUR, 4)
    assert result == datetime(2023, 1, 1, 12, 0, 0)

def test_resample_to_nearest_day():
    timestamp = datetime(2023, 10, 15, 12, 0, 0)
    # Resample to nearest 1 day
    result = _resample_to_nearest(timestamp, TIME_UNIT_DAY, 1)
    assert result == datetime(2023, 10, 15, 0, 0, 0)

def test_get_dataframe_columns_for_timeunit():
    ohlc_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    assert _get_dataframe_columns_for_timeunit(TIME_UNIT_MIN) == ohlc_cols
    
    tick_cols = ["timestamp", "bidprice", "askprice", "bidvolume", "askvolume"]
    assert _get_dataframe_columns_for_timeunit(TIME_UNIT_TICK) == tick_cols

def test_process_stream_row_valid():
    row = [1000, 1.1, 1.2, 1.0, 1.1, 100]
    result = _process_stream_row(row, "MIN", None)
    assert result == row

def test_process_stream_row_past_end():
    row = [2000, 1.1, 1.2, 1.0, 1.1, 100]
    result = _process_stream_row(row, "MIN", 1500)
    assert result is None

def test_process_stream_row_tick():
    # Tick data usually needs division by 1,000,000 for prices? 
    # Based on code: row[-1] = row[-1] / 1_000_000, row[-2] = row[-2] / 1_000_000
    # The code divides the last two elements.
    # In tick_df columns are ["timestamp", "bidprice", "askprice", "bidvolume", "askvolume"]
    # Wait, the code says:
    # if interval == INTERVAL_TICK:
    #     row[-1] = row[-1] / 1_000_000
    #     row[-2] = row[-2] / 1_000_000
    # This implies the last two columns are modified. 
    # For tick data, usually prices are ints that need scaling? 
    # Or maybe volumes?
    # Let's verify against the code logic.
    row = [1000, 1.1, 1.2, 1000000, 2000000] 
    # indices: 0, 1, 2, 3 (-2), 4 (-1)
    
    result = _process_stream_row(list(row), INTERVAL_TICK, None)
    assert result[-1] == 2.0
    assert result[-2] == 1.0

def test_should_continue_streaming():
    assert _should_continue_streaming([], None) is True
    assert _should_continue_streaming([], datetime.now()) is False
    assert _should_continue_streaming([1], None) is True

@patch('apps.dukascopy.data.requests.get')
@patch('apps.dukascopy.data.random.choices')
def test_fetch_internal(mock_choices, mock_get):
    # Mock random.choices to return fixed characters for JSONP
    mock_choices.return_value = list("123456789")
    
    mock_response = MagicMock()
    # jsonp format: _callbacks____xxxx({json});
    # with mocked choices: _callbacks____123456789
    json_content = '{"data": "test"}'
    mock_response.text = f"_callbacks____123456789({json_content});"
    mock_get.return_value = mock_response
    
    result = _fetch("EURUSD", "1MIN", "BID", 1000)
    assert result == {"data": "test"}

# ============================================================================
# Additional Tests for 100% Coverage
# ============================================================================

# Test _resample_to_nearest for SEC time unit
def test_resample_to_nearest_sec():
    timestamp = datetime(2023, 1, 1, 10, 15, 37, 500000)
    result = _resample_to_nearest(timestamp, TIME_UNIT_SEC, 30)
    assert result == datetime(2023, 1, 1, 10, 15, 30, 0)

# Test _resample_to_nearest for WEEK time unit
def test_resample_to_nearest_week():
    # Wednesday Jan 4, 2023
    timestamp = datetime(2023, 1, 4, 14, 30, 0)
    result = _resample_to_nearest(timestamp, TIME_UNIT_WEEK, 1)
    # The function calculates: (weekday() + 1) % (interval_value * 7)
    # For Wednesday (weekday=2): (2+1) % 7 = 3 days to subtract
    # So it goes back 3 days from Wednesday to Sunday
    assert result.hour == 0
    assert result.minute == 0

# Test _resample_to_nearest for MONTH time unit
def test_resample_to_nearest_month():
    timestamp = datetime(2023, 3, 15, 10, 30, 0)
    result = _resample_to_nearest(timestamp, TIME_UNIT_MONTH, 1)
    # Should round to start of month
    assert result.month == 4
    assert result.day == 1
    assert result.hour == 0

# Test _resample_to_nearest for TICK time unit
def test_resample_to_nearest_tick():
    timestamp = datetime(2023, 1, 1, 10, 15, 30)
    result = _resample_to_nearest(timestamp, TIME_UNIT_TICK, 1)
    # TICK should return timestamp unchanged
    assert result == timestamp

# Test _resample_to_nearest with invalid time unit
def test_resample_to_nearest_invalid():
    timestamp = datetime(2023, 1, 1, 10, 15, 30)
    with pytest.raises(NotImplementedError, match="resampling not implemented for INVALID"):
        _resample_to_nearest(timestamp, "INVALID", 1)

# Test _fetch with limit parameter
@patch('apps.dukascopy.data.requests.get')
@patch('apps.dukascopy.data.random.choices')
def test_fetch_with_limit(mock_choices, mock_get):
    mock_choices.return_value = list("123456789")
    mock_response = MagicMock()
    json_content = '{"data": "test"}'
    mock_response.text = f"_callbacks____123456789({json_content});"
    mock_get.return_value = mock_response
    
    result = _fetch("EURUSD", "1MIN", "BID", 1000, limit=5000)
    
    # Verify limit was passed in query params
    call_args = mock_get.call_args
    assert call_args[1]['params']['limit'] == '5000'
    assert result == {"data": "test"}

# Test _process_stream_row with None input
def test_process_stream_row_none():
    result = _process_stream_row(None, "MIN", None)
    assert result is None

# Test _handle_stream_error - continues when max_retries is None
@patch('apps.dukascopy.data.sleep')
@patch('apps.dukascopy.data.logger')
def test_handle_stream_error_no_max_retries(mock_logger, mock_sleep):
    e = Exception("Test error")
    result = _handle_stream_error(e, 5, None)
    assert result is True
    assert mock_logger.error.called

# Test _handle_stream_error - raises when max_retries exceeded
@patch('apps.dukascopy.data.logger')
def test_handle_stream_error_max_retries_exceeded(mock_logger):
    e = Exception("Test error")
    with pytest.raises(Exception, match="Test error"):
        _handle_stream_error(e, 10, 5)

# Test _handle_stream_error - continues when within retry limit
@patch('apps.dukascopy.data.sleep')
@patch('apps.dukascopy.data.logger')
def test_handle_stream_error_within_limit(mock_logger, mock_sleep):
    e = Exception("Test error")
    result = _handle_stream_error(e, 3, 10)
    assert result is True
    assert mock_logger.error.called

# Test _process_stream_batch - first iteration
def test_process_stream_batch_first_iteration():
    lastUpdates = [[1000, 1.1, 1.2, 1.0, 1.1, 100], [2000, 1.2, 1.3, 1.1, 1.2, 200]]
    rows, cursor = _process_stream_batch(lastUpdates, True, 0, INTERVAL_MIN_1, None)
    assert len(rows) == 2
    assert cursor == 2000

# Test _process_stream_batch - subsequent iteration with duplicate cursor
def test_process_stream_batch_skip_duplicate():
    lastUpdates = [[1000, 1.1, 1.2, 1.0, 1.1, 100], [2000, 1.2, 1.3, 1.1, 1.2, 200]]
    rows, cursor = _process_stream_batch(lastUpdates, False, 1000, INTERVAL_MIN_1, None)
    # Should skip first row since cursor matches
    assert len(rows) == 1
    assert cursor == 2000

# Test _process_stream_batch - early return on end_timestamp
def test_process_stream_batch_end_timestamp():
    lastUpdates = [[1000, 1.1, 1.2, 1.0, 1.1, 100], [3000, 1.2, 1.3, 1.1, 1.2, 200]]
    rows, cursor = _process_stream_batch(lastUpdates, True, 0, INTERVAL_MIN_1, 2000)
    # Should stop at first row since second exceeds end_timestamp
    assert len(rows) == 1
    assert cursor == 1000  # Cursor updated to first row's timestamp

# Test _stream generator - successful streaming
@patch('apps.dukascopy.data._fetch')
@patch('apps.dukascopy.data.logger')
def test_stream_success(mock_logger, mock_fetch):
    mock_fetch.side_effect = [
        [[1000, 1.1, 1.2, 1.0, 1.1, 100]],
        []  # Empty to stop
    ]
    
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 2)
    
    result = list(_stream("EUR/USD", INTERVAL_MIN_1, OFFER_SIDE_BID, start, end, max_retries=3))
    assert len(result) == 1
    assert result[0] == [1000, 1.1, 1.2, 1.0, 1.1, 100]

# Test _stream generator - with error and retry
@patch('apps.dukascopy.data._fetch')
@patch('apps.dukascopy.data.sleep')
@patch('apps.dukascopy.data.logger')
def test_stream_with_retry(mock_logger, mock_sleep, mock_fetch):
    # First call raises exception, second call succeeds, third call returns empty to stop
    mock_fetch.side_effect = [
        Exception("Network error"),
        [[1000, 1.1, 1.2, 1.0, 1.1, 100]],
        []
    ]
    
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 2)
    
    result = list(_stream("EUR/USD", INTERVAL_MIN_1, OFFER_SIDE_BID, start, end, max_retries=5))
    assert len(result) == 1

# Test _stream generator - empty results with no end date
@patch('apps.dukascopy.data._fetch')
@patch('apps.dukascopy.data.logger')
def test_stream_empty_no_end(mock_logger, mock_fetch):
    mock_fetch.return_value = []
    
    start = datetime(2023, 1, 1)
    
    result = list(_stream("EUR/USD", INTERVAL_MIN_1, OFFER_SIDE_BID, start, None, max_retries=3))
    assert len(result) == 0

# Test fetch function - integration test
@patch('apps.dukascopy.data.get_instrument')
@patch('apps.dukascopy.data._stream')
def test_fetch_integration(mock_stream, mock_get_instrument):
    mock_get_instrument.return_value = "EUR/USD"
    mock_stream.return_value = iter([
        [1609459200000, 1.2, 1.3, 1.1, 1.25, 1000],  # 2021-01-01 00:00:00
        [1609459260000, 1.25, 1.27, 1.24, 1.26, 1100]
    ])
    
    start = datetime(2021, 1, 1)
    end = datetime(2021, 1, 2)
    
    df = fetch("EURUSD", INTERVAL_MIN_1, OFFER_SIDE_BID, start, end)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.name == "timestamp"

# Test live_fetch - tick mode
@patch('apps.dukascopy.data.get_instrument')
@patch('apps.dukascopy.data._stream')
def test_live_fetch_tick_mode(mock_stream, mock_get_instrument):
    mock_get_instrument.return_value = "EUR/USD"
    mock_stream.return_value = iter([
        [1609459200000, 1.2, 1.3, 1000, 1100],
        [1609459200100, 1.21, 1.31, 1010, 1110]
    ])
    
    start = datetime(2021, 1, 1)
    end = datetime(2021, 1, 1, 0, 1)
    
    gen = live_fetch("EURUSD", 1, TIME_UNIT_TICK, OFFER_SIDE_BID, start, end)
    
    # First yield is empty DataFrame
    df1 = next(gen)
    assert len(df1) == 0
    
    # Second yield has first tick
    df2 = next(gen)
    assert len(df2) == 1

# Test live_fetch - OHLC aggregation
@patch('apps.dukascopy.data.get_instrument')
@patch('apps.dukascopy.data._stream')
def test_live_fetch_ohlc_aggregation(mock_stream, mock_get_instrument):
    mock_get_instrument.return_value = "EUR/USD"
    
    # Create tick data that spans multiple minutes
    base_ts = int(datetime(2021, 1, 1, 0, 0, 0).timestamp() * 1000)
    mock_stream.return_value = iter([
        [base_ts, 1.2000, 1.2010, 100, 110],
        [base_ts + 30000, 1.2005, 1.2015, 105, 115],  # Same minute
        [base_ts + 60000, 1.2010, 1.2020, 110, 120],  # Next minute
    ])
    
    start = datetime(2021, 1, 1)
    end = datetime(2021, 1, 1, 0, 5)
    
    gen = live_fetch("EURUSD", 1, TIME_UNIT_MIN, OFFER_SIDE_BID, start, end)
    
    # Consume generator
    results = list(gen)
    
    # Should have multiple DataFrames as it processes ticks
    assert len(results) > 0
    final_df = results[-1]
    assert isinstance(final_df, pd.DataFrame)

# Test live_fetch - ASK side
@patch('apps.dukascopy.data.get_instrument')
@patch('apps.dukascopy.data._stream')
def test_live_fetch_ask_side(mock_stream, mock_get_instrument):
    mock_get_instrument.return_value = "EUR/USD"
    
    base_ts = int(datetime(2021, 1, 1, 0, 0, 0).timestamp() * 1000)
    mock_stream.return_value = iter([
        [base_ts, 1.2000, 1.2010, 100, 110],
    ])
    
    start = datetime(2021, 1, 1)
    end = datetime(2021, 1, 1, 0, 1)
    
    gen = live_fetch("EURUSD", 1, TIME_UNIT_MIN, OFFER_SIDE_ASK, start, end)
    
    results = list(gen)
    assert len(results) > 0

# Test live_fetch - assertion error for invalid interval
@patch('apps.dukascopy.data.get_instrument')
def test_live_fetch_invalid_interval(mock_get_instrument):
    mock_get_instrument.return_value = "EUR/USD"
    
    start = datetime(2021, 1, 1)
    end = datetime(2021, 1, 1, 0, 1)
    
    with pytest.raises(AssertionError):
        gen = live_fetch("EURUSD", 0, TIME_UNIT_MIN, OFFER_SIDE_BID, start, end)
        next(gen)

# Test _stream generator - error causes return (line 325)
@patch('apps.dukascopy.data._fetch')
@patch('apps.dukascopy.data._handle_stream_error')
@patch('apps.dukascopy.data.logger')
def test_stream_error_causes_return(mock_logger, mock_handle_error, mock_fetch):
    """Test that when _handle_stream_error returns False, the generator returns."""
    mock_fetch.side_effect = Exception("Fatal error")
    mock_handle_error.return_value = False  # Signal to stop
    
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 2)
    
    result = list(_stream("EUR/USD", INTERVAL_MIN_1, OFFER_SIDE_BID, start, end, max_retries=3))
    assert len(result) == 0  # Should return empty due to error

# Test live_fetch - tick mode with multiple ticks (line 446)
@patch('apps.dukascopy.data.get_instrument')
@patch('apps.dukascopy.data._stream')
def test_live_fetch_tick_mode_multiple_ticks(mock_stream, mock_get_instrument):
    """Test tick mode processes multiple ticks correctly with continue statement."""
    mock_get_instrument.return_value = "EUR/USD"
    mock_stream.return_value = iter([
        [1609459200000, 1.2, 1.3, 1000, 1100],
        [1609459200100, 1.21, 1.31, 1010, 1110],
        [1609459200200, 1.22, 1.32, 1020, 1120]
    ])
    
    start = datetime(2021, 1, 1)
    end = datetime(2021, 1, 1, 0, 1)
    
    gen = live_fetch("EURUSD", 1, TIME_UNIT_TICK, OFFER_SIDE_BID, start, end)
    
    # Consume all results
    results = list(gen)
    
    # Should have multiple DataFrames (one empty + one per tick)
    assert len(results) >= 3
    final_df = results[-1]
    assert len(final_df) == 3  # Should have all 3 ticks
