import pytest
import numpy as np
import pandas as pd
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from apps.mt5.client import MT5Api, MT5Client, ConnectionState, get_mt5_api
import apps.mt5.client as client_mod

@pytest.fixture
def mock_mt5():
    with patch('apps.mt5.client.mt5') as m:
        yield m

class TestMT5Api:
    def test_init(self):
        mock_mod = MagicMock()
        api = MT5Api(mt5_module=mock_mod)
        assert api._mt5 == mock_mod
        assert not api.is_initialized()

    def test_initialize(self):
        mock_mod = MagicMock()
        mock_mod.initialize.return_value = True
        api = MT5Api(mt5_module=mock_mod)
        assert api.initialize(path="p", timeout=1)
        assert api.is_initialized()
        mock_mod.initialize.assert_called_with(path="p", timeout=1)

    def test_shutdown(self):
        mock_mod = MagicMock()
        mock_mod.shutdown.return_value = True
        api = MT5Api(mt5_module=mock_mod)
        api._initialized = True
        assert api.shutdown()
        assert not api.is_initialized()
        mock_mod.shutdown.assert_called_once()

    def test_last_error(self):
        mock_mod = MagicMock()
        mock_mod.last_error.return_value = (1, "err")
        api = MT5Api(mt5_module=mock_mod)
        assert api.last_error() == (1, "err")

    def test_is_initialized(self):
        # Already covered but for clarity
        api = MT5Api()
        assert api.is_initialized() is False

    def test_getattr(self):
        mock_mod = MagicMock()
        mock_mod.version = "5.0"
        api = MT5Api(mt5_module=mock_mod)
        assert api.version == "5.0"

class TestConnectionState:
    def test_str_repr(self):
        s = ConnectionState.CONNECTED
        assert str(s) == "connected"
        assert repr(s) == "ConnectionState.CONNECTED"

class TestMT5Client:
    def test_init(self):
        client = MT5Client(timeout=1000, portable=True)
        assert client.timeout == 1000
        assert client.portable is True
        assert client.connection_state == ConnectionState.DISCONNECTED

    def test_connect_success(self, mock_mt5):
        mock_mt5.initialize.return_value = True
        mock_mt5.login.return_value = True
        mock_mt5.symbol_select.return_value = True
        
        client = MT5Client()
        assert client.connect(path="path/to/exe", login=12345, password="password", server="Server")
        assert client.connection_state == ConnectionState.CONNECTED
        assert client._successful_connections == 1
        assert client._last_connection_time is not None

    def test_connect_init_fail(self, mock_mt5):
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = (-1, "init error")
        
        client = MT5Client()
        assert not client.connect(path="p", login=1, password="p", server="s")
        assert client.connection_state == ConnectionState.FAILED
        assert client._failed_connections == 1

    def test_connect_login_fail(self, mock_mt5):
        mock_mt5.initialize.return_value = True
        mock_mt5.login.return_value = False
        mock_mt5.last_error.return_value = (-2, "login error")
        
        client = MT5Client()
        assert not client.connect(path="p", login=1, password="p", server="s")
        assert client.connection_state == ConnectionState.FAILED
        assert client._failed_connections == 1

    def test_connect_exception(self, mock_mt5):
        mock_mt5.initialize.side_effect = Exception("crash")
        
        client = MT5Client()
        assert not client.connect(path="p", login=1, password="p", server="s")
        assert client.connection_state == ConnectionState.FAILED
        assert client._failed_connections == 1

    def test_getattr(self, mock_mt5):
        mock_mt5.account_info.return_value = "some_info"
        client = MT5Client()
        assert client.account_info() == "some_info"

    def test_is_connected(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        
        # Connected in both
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        assert client.is_connected() is True

        # Connected in MT5, but not in our state
        client.connection_state = ConnectionState.DISCONNECTED
        assert client.is_connected() is False

        # Connected in our state, but not in MT5
        client.connection_state = ConnectionState.CONNECTED
        m_info.connected = False
        assert client.is_connected() is False
        
        # terminal_info returns None
        mock_mt5.terminal_info.return_value = None
        assert client.is_connected() is False

    def test_shutdown_success(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        client.shutdown()
        mock_mt5.shutdown.assert_called_once()
        assert client.connection_state == ConnectionState.DISCONNECTED

    def test_shutdown_exception(self, mock_mt5):
        mock_mt5.shutdown.side_effect = Exception("shutdown error")
        client = MT5Client()
        client.shutdown() # Should catch the error
        assert client.connection_state == ConnectionState.DISCONNECTED

    def test_get_bars_not_connected(self, mock_mt5):
        client = MT5Client()
        # Mock is_connected to return False
        mock_mt5.terminal_info.return_value = None
        df = client.get_bars("EURUSD", "M1")
        assert df.empty

    def test_get_bars_range_success(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        dt = np.dtype([('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4')])
        rates = np.array([
            (1600000000, 1.1, 1.2, 1.0, 1.15, 100, 1),
            (1600000060, 1.15, 1.25, 1.1, 1.2, 110, 1)
        ], dtype=dt)
        mock_mt5.copy_rates_range.return_value = rates
        
        df = client.get_bars("EURUSD", "M1", date_from=datetime(2020, 1, 1), date_to=datetime(2020, 1, 2))
        assert not df.empty
        assert len(df) == 2
        assert "open" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_get_bars_pos_success(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        dt = np.dtype([('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4')])
        mock_mt5.copy_rates_from_pos.return_value = np.array([(1600000000, 1.1, 1.2, 1.0, 1.15, 100, 1)], dtype=dt)
        
        df = client.get_bars("EURUSD", "M1", count=100, start_pos=0)
        assert len(df) == 1
        assert df.iloc[0]['open'] == 1.1

    def test_get_bars_fail_status(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        mock_mt5.copy_rates_from_pos.return_value = None
        mock_mt5.last_error.return_value = (4401, "Symbol not found")
        
        df = client.get_bars("NOSYM", "M1")
        assert df.empty

    def test_get_bars_exception(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        mock_mt5.copy_rates_from_pos.side_effect = Exception("Network error")
        df = client.get_bars("EURUSD", "M1")
        assert df.empty

    def test_get_ticks_not_connected(self, mock_mt5):
        client = MT5Client()
        mock_mt5.terminal_info.return_value = None
        assert client.get_ticks("EURUSD") is None

    def test_get_ticks_range_success(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        dt = np.dtype([('time', 'i8'), ('ask', 'f8'), ('bid', 'f8'), ('last', 'f8'), ('volume', 'f8'), ('time_msc', 'i8'), ('flags', 'i4'), ('volume_real', 'f8')])
        ticks = np.array([(1600000000, 1.1, 1.05, 1.08, 10.0, 1600000000000, 124, 10.0)], dtype=dt)
        mock_mt5.copy_ticks_range.return_value = ticks
        
        df = client.get_ticks("EURUSD", start=datetime(2020, 1, 1), end=datetime(2020, 1, 2))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "ask" in df.columns
        assert "last" not in df.columns # Dropped in method

    def test_get_ticks_from_success_list(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        dt = np.dtype([('time', 'i8'), ('ask', 'f8'), ('bid', 'f8')])
        ticks = np.array([(1600000000, 1.1, 1.05)], dtype=dt)
        mock_mt5.copy_ticks_from.return_value = ticks
        
        res = client.get_ticks("EURUSD", start=datetime(2020, 1, 1), as_dataframe=False)
        assert isinstance(res, list)
        assert len(res) == 1
        assert res[0]['ask'] == 1.1

    def test_get_ticks_recent_dataframe(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        dt = np.dtype([('time', 'i8'), ('ask', 'f8'), ('bid', 'f8')])
        mock_mt5.copy_ticks_from.return_value = np.array([], dtype=dt) # Empty but not None
        
        df = client.get_ticks("EURUSD", count=10)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_get_ticks_fail(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        mock_mt5.copy_ticks_from.return_value = None
        mock_mt5.last_error.return_value = (500, "MT5 Internal Error")
        assert client.get_ticks("EURUSD") is None

    def test_get_ticks_exception(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        mock_mt5.copy_ticks_from.side_effect = Exception("Timeout")
        assert client.get_ticks("EURUSD") is None

    def test_get_mt5_timeframe(self):
        client = MT5Client()
        assert client._get_mt5_timeframe("M1") == client_mod.mt5.TIMEFRAME_M1
        assert client._get_mt5_timeframe("m5") == client_mod.mt5.TIMEFRAME_M5
        assert client._get_mt5_timeframe("H1") == client_mod.mt5.TIMEFRAME_H1
        assert client._get_mt5_timeframe("D1") == client_mod.mt5.TIMEFRAME_D1
        assert client._get_mt5_timeframe("unknown") == client_mod.mt5.TIMEFRAME_D1

    def test_add_to_watchlist_success(self, mock_mt5):
        client = MT5Client()
        client.initial_symbols = ["EURUSD", "GBPUSD"]
        mock_mt5.symbol_select.return_value = True
        client._add_to_watchlist()
        assert mock_mt5.symbol_select.call_count == 2

    def test_add_to_watchlist_partial_fail(self, mock_mt5):
        client = MT5Client()
        client.initial_symbols = ["VALID", "INVALID"]
        mock_mt5.symbol_select.side_effect = [True, False]
        client._add_to_watchlist()
        assert mock_mt5.symbol_select.call_count == 2

    def test_add_to_watchlist_empty(self):
        client = MT5Client()
        client.initial_symbols = []
        client._add_to_watchlist() # Should handle nicely

    def test_add_to_watchlist_exception(self, mock_mt5):
        client = MT5Client()
        client.initial_symbols = ["EURUSD"]
        mock_mt5.symbol_select.side_effect = Exception("MT5 dead")
        client._add_to_watchlist() # Should catch

    def test_start_streaming_not_connected(self, mock_mt5):
        client = MT5Client()
        mock_mt5.terminal_info.return_value = None
        assert client.start_streaming("EURUSD", "ticks", lambda x: None) is False

    def test_start_streaming_bars_no_tf(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        assert client.start_streaming("EURUSD", "bars", lambda x: None) is False

    def test_start_streaming_already_active(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        client._active_streams["EURUSD_ticks"] = True
        assert client.start_streaming("EURUSD", "ticks", lambda x: None) is True

    def test_start_streaming_success(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        with patch('threading.Thread') as mock_thread:
            assert client.start_streaming("EURUSD", "ticks", lambda x: None) is True
            mock_thread.assert_called_once()
            assert "EURUSD_ticks" in client._active_streams
            assert "EURUSD_ticks" in client._stream_threads

    def test_stop_streaming_success(self):
        client = MT5Client()
        client._active_streams["EURUSD_ticks"] = True
        client._stream_threads["EURUSD_ticks"] = MagicMock()
        assert client.stop_streaming("EURUSD", "ticks") is True
        assert client._active_streams["EURUSD_ticks"] is False
        assert "EURUSD_ticks" not in client._stream_threads

    def test_stop_streaming_not_active(self):
        client = MT5Client()
        assert client.stop_streaming("EURUSD", "ticks") is False

    def test_get_bars_empty(self, mock_mt5):
        client = MT5Client()
        client.connection_state = ConnectionState.CONNECTED
        m_info = MagicMock()
        m_info.connected = True
        mock_mt5.terminal_info.return_value = m_info
        
        # Return empty numpy array
        mock_mt5.copy_rates_from_pos.return_value = np.array([], dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4')])
        
        df = client.get_bars("EURUSD", "M1")
        assert df.empty

    def test_stream_worker_ticks(self, mock_mt5):
        client = MT5Client()
        client._active_streams["EURUSD_ticks"] = True
        
        callback = MagicMock()
        
        # 1st call: returns tick. 2nd call: returns SAME tick. 3rd call: returns DIFFERENT tick and stops.
        call_count = 0
        def get_ticks_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [{'time': 1, 'ask': 1.1, 'bid': 1.05}]
            if call_count == 2:
                return [{'time': 1, 'ask': 1.1, 'bid': 1.05}]
            client._active_streams["EURUSD_ticks"] = False
            return [{'time': 2, 'ask': 1.2, 'bid': 1.15}]

        with patch.object(client, 'get_ticks', side_effect=get_ticks_side_effect):
            with patch('apps.mt5.client.time.sleep'):
                client._stream_worker("EURUSD", "ticks", callback, 0.1, None)
        
        # Should be called 2 times (1st and 3rd call)
        assert callback.call_count == 2

    def test_stream_worker_bars(self, mock_mt5):
        client = MT5Client()
        client._active_streams["EURUSD_bars"] = True
        callback = MagicMock()
        
        call_count = 0
        def get_bars_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return pd.DataFrame([{'open': 1.1}], index=[datetime(2020, 1, 1, 0, 1)])
            if call_count == 2:
                # Same data, should not trigger callback
                return pd.DataFrame([{'open': 1.1}], index=[datetime(2020, 1, 1, 0, 1)])
            client._active_streams["EURUSD_bars"] = False
            return pd.DataFrame([{'open': 1.2}], index=[datetime(2020, 1, 1, 0, 3)])

        with patch.object(client, 'get_bars', side_effect=get_bars_side_effect):
            with patch('apps.mt5.client.time.sleep'):
                client._stream_worker("EURUSD", "bars", callback, 1.0, "M1")
        
        assert callback.call_count == 2

    def test_stream_worker_bars_empty(self, mock_mt5):
        client = MT5Client()
        client._active_streams["EURUSD_bars"] = True
        
        def side_effect(*args, **kwargs):
            client._active_streams["EURUSD_bars"] = False
            return pd.DataFrame()

        with patch.object(client, 'get_bars', side_effect=side_effect):
            with patch('apps.mt5.client.time.sleep'):
                client._stream_worker("EURUSD", "bars", MagicMock(), 1.0, "M1")

    def test_stop_streaming_with_thread(self, mock_mt5):
        client = MT5Client()
        stream_id = "EURUSD_ticks"
        client._active_streams[stream_id] = True
        client._stream_threads[stream_id] = MagicMock()
        
        assert client.stop_streaming("EURUSD", "ticks") is True
        # Check that it's set to False, not deleted
        assert client._active_streams[stream_id] is False
        assert stream_id not in client._stream_threads

    def test_stop_streaming_no_thread(self, mock_mt5):
        client = MT5Client()
        stream_id = "EURUSD_ticks"
        client._active_streams[stream_id] = True
        # No thread mocked here
        assert client.stop_streaming("EURUSD", "ticks") is True
        assert client._active_streams[stream_id] is False

    def test_stream_worker_exception(self, mock_mt5):
        client = MT5Client()
        stream_id = "EURUSD_ticks"
        client._active_streams[stream_id] = True
        
        # ensure it exits. If get_ticks raises, it hits time.sleep(1) and loops.
        count = 0
        def get_ticks_side_effect(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 1: raise Exception("Crash")
            client._active_streams[stream_id] = False
            return []

        with patch.object(client, 'get_ticks', side_effect=get_ticks_side_effect):
            with patch('apps.mt5.client.time.sleep'):
                client._stream_worker("EURUSD", "ticks", lambda x: None, 0.1, None)
        
        assert client._active_streams[stream_id] is False

    def test_stream_worker_unknown_type(self, mock_mt5):
        client = MT5Client()
        stream_id = "EURUSD_unknown"
        client._active_streams[stream_id] = True
        
        count = 0
        def sleep_side_effect(*args, **kwargs):
            nonlocal count
            count += 1
            if count >= 1: # On first sleep
                client._active_streams[stream_id] = False

        with patch('apps.mt5.client.time.sleep', side_effect=sleep_side_effect):
            client._stream_worker("EURUSD", "unknown", lambda x: None, 0.1, None)
        
        assert client._active_streams[stream_id] is False

    def test_stream_worker_disconnected(self, mock_mt5):
        client = MT5Client()
        stream_id = "EURUSD_ticks"
        client._active_streams[stream_id] = True
        
        # This is harder to test now since is_connected isn't called in the loop.
        # But we can test what happens if get_ticks returns None or [] consistently.
        # However, the loop continues.
        # Let's just remove this test or change it to test empty data.
        def get_ticks_side_effect(*args, **kwargs):
            client._active_streams[stream_id] = False
            return None

        with patch.object(client, 'get_ticks', side_effect=get_ticks_side_effect):
            with patch('apps.mt5.client.time.sleep'):
                client._stream_worker("EURUSD", "ticks", lambda x: None, 0.1, None)
        
        assert client._active_streams[stream_id] is False

    def test_stream_worker_bars_no_timeframe(self, mock_mt5):
        client = MT5Client()
        stream_id = "EURUSD_bars"
        client._active_streams[stream_id] = True
        
        def stop_loop(*args, **kwargs):
            client._active_streams[stream_id] = False

        with patch('apps.mt5.client.time.sleep', side_effect=stop_loop):
            # timeframe=None should skip get_bars block
            client._stream_worker("EURUSD", "bars", lambda x: None, 0.1, None)
        
        assert client._active_streams[stream_id] is False

    def test_repr_and_str(self, mock_mt5):
        client = MT5Client()
        client.account_login = 12345
        client.account_server = "Server"
        
        r = repr(client)
        assert "12345" in r
        assert "Server" in r
        assert "MT5Client" in str(client)

    def test_context_manager(self, mock_mt5):
        with patch.object(MT5Client, 'shutdown') as mock_shutdown:
            with MT5Client() as client:
                assert isinstance(client, MT5Client)
            mock_shutdown.assert_called_once()

def test_get_mt5_api_func():
    assert isinstance(get_mt5_api(), MT5Api)
