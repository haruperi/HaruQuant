"""Tests for MT5 client module - comprehensive coverage."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import pandas as pd
import threading

from apps.mt5.client import MT5Api, get_mt5_api, MT5Client, ConnectionState


# ==================== MT5Api Tests ====================

def test_mt5api_init_default():
    """Test MT5Api initialization with default module."""
    api = MT5Api()
    assert api._initialized is False


def test_mt5api_init_custom_module():
    """Test MT5Api initialization with custom module."""
    mock_module = Mock()
    api = MT5Api(mt5_module=mock_module)
    assert api._mt5 == mock_module


def test_mt5api_initialize_success():
    """Test successful MT5 initialization."""
    mock_module = Mock()
    mock_module.initialize.return_value = True
    
    api = MT5Api(mt5_module=mock_module)
    result = api.initialize()
    
    assert result is True
    assert api._initialized is True
    mock_module.initialize.assert_called_once()


def test_mt5api_initialize_failure():
    """Test failed MT5 initialization."""
    mock_module = Mock()
    mock_module.initialize.return_value = False
    
    api = MT5Api(mt5_module=mock_module)
    result = api.initialize()
    
    assert result is False
    assert api._initialized is False


def test_mt5api_shutdown():
    """Test MT5 shutdown."""
    mock_module = Mock()
    mock_module.shutdown.return_value = True
    
    api = MT5Api(mt5_module=mock_module)
    api._initialized = True
    
    result = api.shutdown()
    
    assert result is True
    assert api._initialized is False
    mock_module.shutdown.assert_called_once()


def test_mt5api_last_error():
    """Test getting last MT5 error."""
    mock_module = Mock()
    mock_module.last_error.return_value = (1, "Test error")
    
    api = MT5Api(mt5_module=mock_module)
    result = api.last_error()
    
    assert result == (1, "Test error")


def test_mt5api_is_initialized():
    """Test checking initialization status."""
    api = MT5Api()
    assert api.is_initialized() is False
    
    api._initialized = True
    assert api.is_initialized() is True


def test_mt5api_getattr():
    """Test attribute delegation to MT5 module."""
    mock_module = Mock()
    mock_module.TIMEFRAME_M1 = 1
    
    api = MT5Api(mt5_module=mock_module)
    result = api.TIMEFRAME_M1
    
    assert result == 1


def test_get_mt5_api():
    """Test getting shared MT5 API instance."""
    api = get_mt5_api()
    assert isinstance(api, MT5Api)


# ==================== ConnectionState Tests ====================

def test_connection_state_values():
    """Test ConnectionState enum values."""
    assert ConnectionState.DISCONNECTED.value == "disconnected"
    assert ConnectionState.CONNECTED.value == "connected"
    assert ConnectionState.FAILED.value == "failed"
    assert ConnectionState.INITIALIZING.value == "initializing"
    assert ConnectionState.RECONNECTING.value == "reconnecting"


def test_connection_state_str():
    """Test ConnectionState string representation."""
    assert str(ConnectionState.CONNECTED) == "connected"
    assert str(ConnectionState.DISCONNECTED) == "disconnected"


def test_connection_state_repr():
    """Test ConnectionState detailed representation."""
    assert repr(ConnectionState.CONNECTED) == "ConnectionState.CONNECTED"
    assert repr(ConnectionState.FAILED) == "ConnectionState.FAILED"


# ==================== MT5Client Initialization Tests ====================

def test_mt5client_init_default():
    """Test MT5Client initialization with default parameters."""
    client = MT5Client()
    
    assert client.connection_state == ConnectionState.DISCONNECTED
    assert client.timeout == 60000
    assert client.portable is False
    assert isinstance(client.config, dict)
    assert isinstance(client.accounts, dict)
    assert len(client.initial_symbols) > 0


def test_mt5client_init_custom_timeout():
    """Test MT5Client initialization with custom timeout."""
    client = MT5Client(timeout=30000)
    assert client.timeout == 30000


def test_mt5client_init_portable_mode():
    """Test MT5Client initialization in portable mode."""
    client = MT5Client(portable=True)
    assert client.portable is True


def test_mt5client_init_event_handlers():
    """Test MT5Client event handlers initialization."""
    client = MT5Client()
    
    assert "connect" in client._event_handlers
    assert "disconnect" in client._event_handlers
    assert "error" in client._event_handlers
    assert isinstance(client._event_handlers["connect"], list)


def test_mt5client_init_statistics():
    """Test MT5Client statistics initialization."""
    client = MT5Client()
    
    assert client._connection_attempts == 0
    assert client._successful_connections == 0
    assert client._failed_connections == 0
    assert client._last_connection_time is None


# ==================== MT5Client Connection Tests ====================

@patch('apps.mt5.client.mt5')
def test_connect_success(mock_mt5):
    """Test successful connection to MT5."""
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    mock_mt5.symbol_select.return_value = True
    
    client = MT5Client()
    result = client.connect(
        path="C:/MT5/terminal.exe",
        login=12345,
        password="test",
        server="Demo"
    )
    
    assert result is True
    assert client.connection_state == ConnectionState.CONNECTED
    assert client._successful_connections == 1
    assert client._connection_attempts == 1
    mock_mt5.initialize.assert_called_once()
    mock_mt5.login.assert_called_once()


@patch('apps.mt5.client.mt5')
def test_connect_initialization_failure(mock_mt5):
    """Test connection failure during initialization."""
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (1, "Init failed")
    
    client = MT5Client()
    result = client.connect(
        path="C:/MT5/terminal.exe",
        login=12345,
        password="test",
        server="Demo"
    )
    
    assert result is False
    assert client.connection_state == ConnectionState.FAILED
    assert client._failed_connections == 1


@patch('apps.mt5.client.mt5')
def test_connect_login_failure(mock_mt5):
    """Test connection failure during login."""
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = False
    mock_mt5.last_error.return_value = (2, "Login failed")
    
    client = MT5Client()
    result = client.connect(
        path="C:/MT5/terminal.exe",
        login=12345,
        password="test",
        server="Demo"
    )
    
    assert result is False
    assert client.connection_state == ConnectionState.FAILED
    assert client._failed_connections == 1


@patch('apps.mt5.client.mt5')
def test_connect_exception(mock_mt5):
    """Test connection exception handling."""
    mock_mt5.initialize.side_effect = Exception("Test exception")
    
    client = MT5Client()
    result = client.connect(
        path="C:/MT5/terminal.exe",
        login=12345,
        password="test",
        server="Demo"
    )
    
    assert result is False
    assert client.connection_state == ConnectionState.FAILED


@patch('apps.mt5.client.mt5')
def test_add_to_watchlist_success(mock_mt5):
    """Test adding symbols to watchlist."""
    mock_mt5.symbol_select.return_value = True
    
    client = MT5Client()
    client._add_to_watchlist()
    
    # Should have called symbol_select for each initial symbol
    assert mock_mt5.symbol_select.call_count > 0


@patch('apps.mt5.client.mt5')
def test_add_to_watchlist_empty_symbols(mock_mt5):
    """Test adding to watchlist with no symbols."""
    client = MT5Client()
    client.initial_symbols = []
    
    client._add_to_watchlist()
    
    mock_mt5.symbol_select.assert_not_called()


@patch('apps.mt5.client.mt5')
def test_add_to_watchlist_exception(mock_mt5):
    """Test watchlist exception handling."""
    mock_mt5.symbol_select.side_effect = Exception("Test error")
    
    client = MT5Client()
    # Should not raise exception
    client._add_to_watchlist()


@patch('apps.mt5.client.mt5')
def test_add_to_watchlist_symbol_failure(mock_mt5):
    """Test watchlist when symbol_select fails."""
    mock_mt5.symbol_select.return_value = False
    
    client = MT5Client()
    client.initial_symbols = ["INVALID"]
    
    # Should log warning but not raise
    client._add_to_watchlist()


@patch('apps.mt5.client.mt5')
def test_is_connected_true(mock_mt5):
    """Test is_connected when connected."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    assert client.is_connected() is True


@patch('apps.mt5.client.mt5')
def test_is_connected_false_state(mock_mt5):
    """Test is_connected when state is disconnected."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    client = MT5Client()
    client.connection_state = ConnectionState.DISCONNECTED
    
    assert client.is_connected() is False


@patch('apps.mt5.client.mt5')
def test_is_connected_false_terminal(mock_mt5):
    """Test is_connected when terminal is not connected."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = False
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    assert client.is_connected() is False


@patch('apps.mt5.client.mt5')
def test_is_connected_none_terminal(mock_mt5):
    """Test is_connected when terminal info is None."""
    mock_mt5.terminal_info.return_value = None
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    assert client.is_connected() is False


@patch('apps.mt5.client.mt5')
def test_shutdown(mock_mt5):
    """Test MT5 client shutdown."""
    mock_mt5.shutdown.return_value = None
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    client.shutdown()
    
    assert client.connection_state == ConnectionState.DISCONNECTED
    mock_mt5.shutdown.assert_called_once()


@patch('apps.mt5.client.mt5')
def test_shutdown_exception(mock_mt5):
    """Test shutdown exception handling."""
    mock_mt5.shutdown.side_effect = Exception("Test error")
    
    client = MT5Client()
    # Should not raise exception
    client.shutdown()


# ==================== MT5Client Market Data Tests ====================

@patch('apps.mt5.client.mt5')
def test_get_mt5_timeframe_valid(mock_mt5):
    """Test converting valid timeframe string."""
    mock_mt5.TIMEFRAME_M1 = 1
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_mt5.TIMEFRAME_D1 = 16408
    
    client = MT5Client()
    
    assert client._get_mt5_timeframe("M1") == 1
    assert client._get_mt5_timeframe("H1") == 16385
    assert client._get_mt5_timeframe("D1") == 16408


@patch('apps.mt5.client.mt5')
def test_get_mt5_timeframe_case_insensitive(mock_mt5):
    """Test timeframe conversion is case insensitive."""
    mock_mt5.TIMEFRAME_M1 = 1
    
    client = MT5Client()
    assert client._get_mt5_timeframe("m1") == 1


@patch('apps.mt5.client.mt5')
def test_get_mt5_timeframe_invalid(mock_mt5):
    """Test converting invalid timeframe returns default."""
    mock_mt5.TIMEFRAME_D1 = 16408
    
    client = MT5Client()
    result = client._get_mt5_timeframe("INVALID")
    
    assert result == 16408  # Should default to D1


@patch('apps.mt5.client.mt5')
def test_get_bars_not_connected(mock_mt5):
    """Test getting bars when not connected."""
    client = MT5Client()
    client.connection_state = ConnectionState.DISCONNECTED
    mock_mt5.terminal_info.return_value = None
    
    df = client.get_bars("EURUSD", "H1")
    
    assert df.empty


@patch('apps.mt5.client.mt5')
def test_get_bars_with_count(mock_mt5):
    """Test getting bars with count parameter."""
    import numpy as np
    
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    # Create mock rates data
    rates = np.array([
        (1672574400, 1.1, 1.2, 1.0, 1.15, 100, 2),
        (1672578000, 1.15, 1.25, 1.1, 1.2, 150, 3),
    ], dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), 
              ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4')])
    
    mock_mt5.copy_rates_from_pos.return_value = rates
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    df = client.get_bars("EURUSD", "H1", count=2)
    
    assert not df.empty
    assert len(df) == 2
    assert "open" in df.columns
    mock_mt5.copy_rates_from_pos.assert_called_once()


@patch('apps.mt5.client.mt5')
def test_get_bars_with_date_range(mock_mt5):
    """Test getting bars with date range."""
    import numpy as np
    
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    rates = np.array([
        (1672574400, 1.1, 1.2, 1.0, 1.15, 100, 2),
    ], dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), 
              ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4')])
    
    mock_mt5.copy_rates_range.return_value = rates
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    date_from = datetime(2023, 1, 1)
    date_to = datetime(2023, 1, 2)
    
    df = client.get_bars("EURUSD", "H1", date_from=date_from, date_to=date_to)
    
    assert not df.empty
    mock_mt5.copy_rates_range.assert_called_once()


@patch('apps.mt5.client.mt5')
def test_get_bars_none_rates(mock_mt5):
    """Test getting bars when rates are None."""
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.copy_rates_from_pos.return_value = None
    mock_mt5.last_error.return_value = (1, "No data")
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    df = client.get_bars("EURUSD", "H1")
    
    assert df.empty


@patch('apps.mt5.client.mt5')
def test_get_bars_empty_warning(mock_mt5):
    """Test get_bars warning when data is empty."""
    import numpy as np
    
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    # Return empty array
    rates = np.array([], dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), 
                                  ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4')])
    mock_mt5.copy_rates_from_pos.return_value = rates
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    df = client.get_bars("EURUSD", "H1")
    
    assert df.empty


@patch('apps.mt5.client.mt5')
def test_get_bars_exception(mock_mt5):
    """Test get_bars exception handling."""
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.copy_rates_from_pos.side_effect = Exception("Test error")
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    df = client.get_bars("EURUSD", "H1")
    
    assert df.empty


@patch('apps.mt5.client.mt5')
def test_get_ticks_not_connected(mock_mt5):
    """Test getting ticks when not connected."""
    client = MT5Client()
    client.connection_state = ConnectionState.DISCONNECTED
    mock_mt5.terminal_info.return_value = None
    
    result = client.get_ticks("EURUSD")
    
    assert result is None


@patch('apps.mt5.client.mt5')
def test_get_ticks_with_range(mock_mt5):
    """Test getting ticks with date range."""
    import numpy as np
    
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.COPY_TICKS_ALL = 0
    
    ticks = np.array([
        (1672574400, 1.1, 1.2, 0, 0, 0, 0, 0),
    ], dtype=[('time', 'i8'), ('bid', 'f8'), ('ask', 'f8'), 
              ('last', 'f8'), ('volume', 'i8'), ('time_msc', 'i8'), 
              ('flags', 'i4'), ('volume_real', 'f8')])
    
    mock_mt5.copy_ticks_range.return_value = ticks
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 2)
    
    df = client.get_ticks("EURUSD", start=start, end=end)
    
    assert isinstance(df, pd.DataFrame)
    mock_mt5.copy_ticks_range.assert_called_once()


@patch('apps.mt5.client.mt5')
def test_get_ticks_from_date(mock_mt5):
    """Test getting ticks from specific date."""
    import numpy as np
    
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.COPY_TICKS_ALL = 0
    
    ticks = np.array([
        (1672574400, 1.1, 1.2, 0, 0, 0, 0, 0),
    ], dtype=[('time', 'i8'), ('bid', 'f8'), ('ask', 'f8'), 
              ('last', 'f8'), ('volume', 'i8'), ('time_msc', 'i8'), 
              ('flags', 'i4'), ('volume_real', 'f8')])
    
    mock_mt5.copy_ticks_from.return_value = ticks
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    start = datetime(2023, 1, 1)
    
    df = client.get_ticks("EURUSD", start=start, count=10)
    
    assert isinstance(df, pd.DataFrame)


@patch('apps.mt5.client.mt5')
def test_get_ticks_recent(mock_mt5):
    """Test getting recent ticks."""
    import numpy as np
    
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.COPY_TICKS_ALL = 0
    
    ticks = np.array([
        (1672574400, 1.1, 1.2, 0, 0, 0, 0, 0),
    ], dtype=[('time', 'i8'), ('bid', 'f8'), ('ask', 'f8'), 
              ('last', 'f8'), ('volume', 'i8'), ('time_msc', 'i8'), 
              ('flags', 'i4'), ('volume_real', 'f8')])
    
    mock_mt5.copy_ticks_from.return_value = ticks
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    df = client.get_ticks("EURUSD", count=10)
    
    assert isinstance(df, pd.DataFrame)


@patch('apps.mt5.client.mt5')
def test_get_ticks_none_result(mock_mt5):
    """Test getting ticks when result is None."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.copy_ticks_from.return_value = None
    mock_mt5.last_error.return_value = (1, "No ticks")
    mock_mt5.COPY_TICKS_ALL = 0
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    result = client.get_ticks("EURUSD")
    
    assert result is None


@patch('apps.mt5.client.mt5')
def test_get_ticks_empty_result(mock_mt5):
    """Test getting ticks with empty result."""
    import numpy as np
    
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.COPY_TICKS_ALL = 0
    
    ticks = np.array([], dtype=[('time', 'i8'), ('bid', 'f8'), ('ask', 'f8'), 
                                  ('last', 'f8'), ('volume', 'i8'), ('time_msc', 'i8'), 
                                  ('flags', 'i4'), ('volume_real', 'f8')])
    
    mock_mt5.copy_ticks_from.return_value = ticks
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    df = client.get_ticks("EURUSD")
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


@patch('apps.mt5.client.mt5')
def test_get_ticks_as_list(mock_mt5):
    """Test getting ticks as list of dicts."""
    import numpy as np
    
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.COPY_TICKS_ALL = 0
    
    ticks = np.array([
        (1672574400, 1.1, 1.2, 0, 0, 0, 0, 0),
    ], dtype=[('time', 'i8'), ('bid', 'f8'), ('ask', 'f8'), 
              ('last', 'f8'), ('volume', 'i8'), ('time_msc', 'i8'), 
              ('flags', 'i4'), ('volume_real', 'f8')])
    
    mock_mt5.copy_ticks_from.return_value = ticks
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    result = client.get_ticks("EURUSD", as_dataframe=False)
    
    assert isinstance(result, list)
    assert len(result) == 1


@patch('apps.mt5.client.mt5')
def test_get_ticks_exception(mock_mt5):
    """Test get_ticks exception handling."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.copy_ticks_from.side_effect = Exception("Test error")
    mock_mt5.COPY_TICKS_ALL = 0
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    result = client.get_ticks("EURUSD")
    
    assert result is None


# ==================== MT5Client Streaming Tests ====================

@patch('apps.mt5.client.mt5')
def test_start_streaming_not_connected(mock_mt5):
    """Test starting streaming when not connected."""
    client = MT5Client()
    client.connection_state = ConnectionState.DISCONNECTED
    mock_mt5.terminal_info.return_value = None
    
    callback = Mock()
    result = client.start_streaming("EURUSD", "ticks", callback)
    
    assert result is False


@patch('apps.mt5.client.mt5')
def test_start_streaming_bars_no_timeframe(mock_mt5):
    """Test starting bar streaming without timeframe."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    callback = Mock()
    result = client.start_streaming("EURUSD", "bars", callback)
    
    assert result is False


@patch('apps.mt5.client.mt5')
def test_start_streaming_ticks_success(mock_mt5):
    """Test successfully starting tick streaming."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    callback = Mock()
    result = client.start_streaming("EURUSD", "ticks", callback)
    
    assert result is True
    assert "EURUSD_ticks" in client._active_streams


@patch('apps.mt5.client.mt5')
def test_start_streaming_already_active(mock_mt5):
    """Test starting streaming when already active."""
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    client._active_streams["EURUSD_ticks"] = True
    
    callback = Mock()
    result = client.start_streaming("EURUSD", "ticks", callback)
    
    assert result is True


@patch('apps.mt5.client.mt5')
def test_stop_streaming_success(mock_mt5):
    """Test successfully stopping streaming."""
    client = MT5Client()
    client._active_streams["EURUSD_ticks"] = True
    client._stream_threads["EURUSD_ticks"] = Mock()
    
    result = client.stop_streaming("EURUSD", "ticks")
    
    assert result is True
    assert client._active_streams["EURUSD_ticks"] is False


@patch('apps.mt5.client.mt5')
def test_stop_streaming_not_active(mock_mt5):
    """Test stopping streaming when not active."""
    client = MT5Client()
    
    result = client.stop_streaming("EURUSD", "ticks")
    
    assert result is False


@patch('apps.mt5.client.mt5')
def test_stop_streaming_with_thread_cleanup(mock_mt5):
    """Test stopping streaming cleans up thread."""
    client = MT5Client()
    mock_thread = Mock()
    client._active_streams["EURUSD_ticks"] = True
    client._stream_threads["EURUSD_ticks"] = mock_thread
    
    result = client.stop_streaming("EURUSD", "ticks")
    
    assert result is True
    assert "EURUSD_ticks" not in client._stream_threads


@patch('apps.mt5.client.mt5')
def test_stream_worker_ticks_with_data(mock_mt5):
    """Test stream worker for ticks with data."""
    import time as time_module
    
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.COPY_TICKS_ALL = 0
    
    # Create tick data
    import numpy as np
    ticks = np.array([
        (1672574400, 1.1, 1.2, 0, 0, 0, 0, 0),
    ], dtype=[('time', 'i8'), ('bid', 'f8'), ('ask', 'f8'), 
              ('last', 'f8'), ('volume', 'i8'), ('time_msc', 'i8'), 
              ('flags', 'i4'), ('volume_real', 'f8')])
    
    mock_mt5.copy_ticks_from.return_value = ticks
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    callback = Mock()
    client._active_streams["EURUSD_ticks"] = True
    
    # Run worker in thread for short time
    import threading
    thread = threading.Thread(
        target=client._stream_worker,
        args=("EURUSD", "ticks", callback, 1.0, None)
    )
    thread.start()
    
    time_module.sleep(0.3)  # Let it run briefly
    client._active_streams["EURUSD_ticks"] = False
    thread.join(timeout=2)
    
    # Callback should have been called
    assert callback.called


@patch('apps.mt5.client.mt5')
def test_stream_worker_bars_with_data(mock_mt5):
    """Test stream worker for bars with data."""
    import time as time_module
    import numpy as np
    
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    rates = np.array([
        (1672574400, 1.1, 1.2, 1.0, 1.15, 100, 2),
    ], dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), 
              ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4')])
    
    mock_mt5.copy_rates_from_pos.return_value = rates
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    callback = Mock()
    client._active_streams["EURUSD_bars"] = True
    
    # Run worker in thread for short time
    import threading
    thread = threading.Thread(
        target=client._stream_worker,
        args=("EURUSD", "bars", callback, 0.2, "H1")
    )
    thread.start()
    
    time_module.sleep(0.4)  # Let it run briefly
    client._active_streams["EURUSD_bars"] = False
    thread.join(timeout=2)
    
    # Callback should have been called
    assert callback.called


@patch('apps.mt5.client.mt5')
def test_stream_worker_error_handling(mock_mt5):
    """Test stream worker error handling."""
    import time as time_module
    
    mock_terminal_info = Mock()
    mock_terminal_info.connected = True
    mock_mt5.terminal_info.return_value = mock_terminal_info
    mock_mt5.COPY_TICKS_ALL = 0
    mock_mt5.copy_ticks_from.side_effect = Exception("Test error")
    
    client = MT5Client()
    client.connection_state = ConnectionState.CONNECTED
    
    callback = Mock()
    client._active_streams["EURUSD_ticks"] = True
    
    # Run worker in thread for short time
    import threading
    thread = threading.Thread(
        target=client._stream_worker,
        args=("EURUSD", "ticks", callback, 1.0, None)
    )
    thread.start()
    
    time_module.sleep(1.5)  # Let it handle error
    client._active_streams["EURUSD_ticks"] = False
    thread.join(timeout=3)
    
    # Should not crash, callback might not be called due to error


# ==================== MT5Client Magic Methods Tests ====================

def test_mt5client_getattr():
    """Test attribute delegation to MT5 API."""
    with patch('apps.mt5.client.mt5') as mock_mt5:
        mock_mt5.TIMEFRAME_M1 = 1
        
        client = MT5Client()
        result = client.TIMEFRAME_M1
        
        assert result == 1


def test_mt5client_repr():
    """Test MT5Client string representation."""
    client = MT5Client()
    repr_str = repr(client)
    
    assert "MT5Client" in repr_str
    assert "state=" in repr_str


def test_mt5client_str():
    """Test MT5Client user-friendly string."""
    client = MT5Client()
    str_repr = str(client)
    
    assert "MT5Client" in str_repr
    assert "disconnected" in str_repr


def test_mt5client_context_manager():
    """Test MT5Client as context manager."""
    with patch('apps.mt5.client.mt5'):
        with MT5Client() as client:
            assert isinstance(client, MT5Client)


@patch('apps.mt5.client.mt5')
def test_mt5client_context_manager_exit(mock_mt5):
    """Test MT5Client context manager cleanup."""
    mock_mt5.shutdown.return_value = None
    
    with MT5Client() as client:
        client.connection_state = ConnectionState.CONNECTED
    
    # Shutdown should have been called
    mock_mt5.shutdown.assert_called_once()
