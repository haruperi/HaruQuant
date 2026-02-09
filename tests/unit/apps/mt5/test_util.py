"""Tests for dukascopy module - comprehensive coverage."""

import pytest
import json
import pickle
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from apps.mt5.util import MT5Utils, timeframe_seconds
from apps.mt5 import MT5Client  # For constants


# ==================== Existing Tests ====================

def test_convert_time():
    """Test datetime to timestamp conversion."""
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts = MT5Utils.convert_time(dt, "timestamp")
    assert isinstance(ts, int)
    assert ts == int(dt.timestamp())
    
    # Test timestamp to datetime
    dt_out = MT5Utils.convert_time(ts, "datetime")
    assert dt_out == dt
    
    # Test ISO string to datetime
    iso = "2023-01-01T12:00:00+00:00"
    dt_out = MT5Utils.convert_time(iso, "datetime")
    assert dt_out == dt


def test_convert_price():
    """Test price conversion between digit precisions."""
    res = MT5Utils.convert_price(1.0, 0, 2)  # 1.0 * 100
    assert res == 100.0
    
    res = MT5Utils.convert_price(100.0, 2, 0)  # 100.0 * 0.01
    assert res == 1.0


def test_round_price():
    """Test price rounding to tick size."""
    # Nearest
    assert MT5Utils.round_price(1.234, 0.01, "nearest") == 1.23
    assert MT5Utils.round_price(1.236, 0.01, "nearest") == 1.24
    
    # Up
    assert MT5Utils.round_price(1.231, 0.01, "up") == 1.24
    
    # Down
    assert MT5Utils.round_price(1.239, 0.01, "down") == 1.23


def test_convert_volume():
    """Test volume conversion between units."""
    # Lots to units
    assert MT5Utils.convert_volume(1.0, "lots", "units") == 100000.0
    
    # Units to lots
    assert MT5Utils.convert_volume(100000.0, "units", "lots") == 1.0
    
    # Mini lots to lots
    assert MT5Utils.convert_volume(10.0, "mini_lots", "lots") == 1.0


def test_round_volume():
    """Test volume rounding to step size."""
    assert MT5Utils.round_volume(0.123, 0.01) == 0.12
    assert MT5Utils.round_volume(0.126, 0.01) == 0.13


def test_to_dict():
    """Test data to dictionary conversion."""
    data = {"a": 1, "b": None, "_c": 2}
    
    # Default
    assert MT5Utils.to_dict(data) == {"a": 1, "b": None}
    
    # Exclude None
    assert MT5Utils.to_dict(data, exclude_none=True) == {"a": 1}
    
    # Include private
    assert MT5Utils.to_dict(data, exclude_private=False) == {"a": 1, "b": None, "_c": 2}


def test_calculate_percent():
    """Test percentage calculation."""
    assert MT5Utils.calculate("percent", 5, 10) == 50.0


def test_calculate_percent_change():
    """Test percentage change calculation."""
    assert MT5Utils.calculate("percent_change", 100, 110) == 10.0


# ==================== New Time Operation Tests ====================

def test_convert_time_iso_output():
    """Test converting to ISO format."""
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    iso = MT5Utils.convert_time(dt, "iso")
    assert iso == "2023-01-01T12:00:00+00:00"


def test_convert_time_mt5_format():
    """Test converting to MT5 timestamp format."""
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mt5_ts = MT5Utils.convert_time(dt, "mt5")
    assert mt5_ts == int(dt.timestamp())


def test_convert_time_iso_with_z():
    """Test parsing ISO string with Z suffix."""
    iso_z = "2023-01-01T12:00:00Z"
    dt = MT5Utils.convert_time(iso_z, "datetime")
    assert dt.year == 2023
    assert dt.month == 1
    assert dt.day == 1


def test_convert_time_invalid_type():
    """Test error handling for invalid input type."""
    with pytest.raises(ValueError, match="Unsupported time value type"):
        MT5Utils.convert_time([], "datetime")


def test_convert_time_invalid_format():
    """Test error handling for invalid output format."""
    dt = datetime(2023, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Unsupported output format"):
        MT5Utils.convert_time(dt, "invalid_format")


def test_convert_time_same_digits():
    """Test price conversion with same digits."""
    result = MT5Utils.convert_price(1.5, 2, 2)
    assert result == 1.5


@patch('apps.mt5.util.mt5')
def test_get_time_now(mock_mt5):
    """Test getting current UTC time."""
    result = MT5Utils.get_time("now")
    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc


@patch('apps.mt5.util.mt5')
def test_get_time_local(mock_mt5):
    """Test getting local time."""
    result = MT5Utils.get_time("local")
    assert isinstance(result, datetime)


@patch('apps.mt5.util.mt5')
def test_get_time_mt5_initialized(mock_mt5):
    """Test getting MT5 server time when initialized."""
    mock_mt5.initialize.return_value = True
    mock_terminal_info = Mock()
    mock_mt5.terminal_info.return_value = mock_terminal_info
    
    result = MT5Utils.get_time("mt5")
    assert isinstance(result, datetime)


@patch('apps.mt5.util.mt5')
def test_get_time_mt5_not_initialized(mock_mt5):
    """Test getting MT5 time when not initialized."""
    mock_mt5.initialize.return_value = False
    
    result = MT5Utils.get_time("mt5")
    assert isinstance(result, datetime)


@patch('apps.mt5.util.mt5')
def test_get_time_mt5_terminal_info_none(mock_mt5):
    """Test getting MT5 time when terminal_info is None."""
    mock_mt5.initialize.return_value = True
    mock_mt5.terminal_info.return_value = None
    
    result = MT5Utils.get_time("mt5")
    assert isinstance(result, datetime)


@patch('apps.mt5.util.mt5')
def test_get_time_with_timezone_offset(mock_mt5):
    """Test time with timezone offset."""
    result = MT5Utils.get_time("now", timezone_offset=2)
    assert isinstance(result, datetime)


@patch('apps.mt5.util.mt5')
def test_get_time_with_format_string(mock_mt5):
    """Test time with custom format string."""
    result = MT5Utils.get_time("now", format_str="%Y-%m-%d")
    assert isinstance(result, str)
    assert len(result) == 10  # YYYY-MM-DD


@patch('apps.mt5.util.mt5')
def test_get_time_invalid_type(mock_mt5):
    """Test error for invalid time type."""
    with pytest.raises(ValueError, match="Unsupported time_type"):
        MT5Utils.get_time("invalid_type")


# ==================== Price Operation Tests ====================

def test_format_price_basic():
    """Test basic price formatting."""
    result = MT5Utils.format_price(1.12345, digits=5)
    assert result == "1.12345"


def test_format_price_with_currency():
    """Test price formatting with currency symbol."""
    result = MT5Utils.format_price(1.12345, digits=2, include_currency=True, currency_symbol="$")
    assert result == "$1.12"


def test_format_price_without_currency_symbol():
    """Test price formatting with include_currency but no symbol."""
    result = MT5Utils.format_price(1.12345, digits=2, include_currency=True, currency_symbol="")
    assert result == "1.12"


def test_round_price_invalid_tick_size():
    """Test error for invalid tick size."""
    with pytest.raises(ValueError, match="tick_size must be positive"):
        MT5Utils.round_price(1.5, 0, "nearest")


def test_round_price_invalid_direction():
    """Test error for invalid rounding direction."""
    with pytest.raises(ValueError, match="Invalid direction"):
        MT5Utils.round_price(1.5, 0.01, "invalid")


def test_add_pips_to_price_none_symbol():
    """Test adding pips with None symbol info."""
    result = MT5Utils.add_pips_to_price(1.5, 10, None)
    assert result == 1.5


def test_add_pips_to_price_5_digits():
    """Test adding pips for 5-digit symbol."""
    mock_symbol = Mock()
    mock_symbol.digits = 5
    mock_symbol.point = 0.00001
    
    result = MT5Utils.add_pips_to_price(1.12000, 10, mock_symbol, direction=1)
    assert result == pytest.approx(1.12100, rel=1e-5)


def test_add_pips_to_price_3_digits():
    """Test adding pips for 3-digit symbol."""
    mock_symbol = Mock()
    mock_symbol.digits = 3
    mock_symbol.point = 0.001
    
    result = MT5Utils.add_pips_to_price(100.000, 5, mock_symbol, direction=1)
    assert result == pytest.approx(100.050, rel=1e-3)


def test_add_pips_to_price_2_digits():
    """Test adding pips for 2-digit symbol."""
    mock_symbol = Mock()
    mock_symbol.digits = 2
    mock_symbol.point = 0.01
    
    result = MT5Utils.add_pips_to_price(1.50, 10, mock_symbol, direction=1)
    assert result == pytest.approx(1.60, rel=1e-2)


def test_add_pips_to_price_subtract():
    """Test subtracting pips."""
    mock_symbol = Mock()
    mock_symbol.digits = 5
    mock_symbol.point = 0.00001
    
    result = MT5Utils.add_pips_to_price(1.12000, 10, mock_symbol, direction=-1)
    assert result == pytest.approx(1.11900, rel=1e-5)


# ==================== Volume Operation Tests ====================

def test_convert_volume_micro_lots():
    """Test converting micro lots."""
    result = MT5Utils.convert_volume(100.0, "micro_lots", "lots")
    assert result == 1.0


def test_convert_volume_custom_contract_size():
    """Test volume conversion with custom contract size."""
    result = MT5Utils.convert_volume(1.0, "lots", "units", contract_size=50000)
    assert result == 50000.0


def test_convert_volume_invalid_from_unit():
    """Test error for invalid from_unit."""
    with pytest.raises(ValueError, match="Invalid from_unit"):
        MT5Utils.convert_volume(1.0, "invalid", "lots")


def test_convert_volume_invalid_to_unit():
    """Test error for invalid to_unit."""
    with pytest.raises(ValueError, match="Invalid to_unit"):
        MT5Utils.convert_volume(1.0, "lots", "invalid")


def test_round_volume_invalid_step():
    """Test error for invalid volume step."""
    with pytest.raises(ValueError, match="volume_step must be positive"):
        MT5Utils.round_volume(1.0, 0, "nearest")


def test_round_volume_up():
    """Test rounding volume up."""
    result = MT5Utils.round_volume(0.123, 0.01, "up")
    assert result == 0.13


def test_round_volume_down():
    """Test rounding volume down."""
    result = MT5Utils.round_volume(0.129, 0.01, "down")
    assert result == 0.12


def test_round_volume_invalid_direction():
    """Test error for invalid rounding direction."""
    with pytest.raises(ValueError, match="Invalid direction"):
        MT5Utils.round_volume(1.0, 0.01, "invalid")


# ==================== Type Conversion Tests ====================

def test_convert_to_bool_string_true():
    """Test converting string to bool (true values)."""
    assert MT5Utils._convert_to_bool("true") is True
    assert MT5Utils._convert_to_bool("1") is True
    assert MT5Utils._convert_to_bool("yes") is True
    assert MT5Utils._convert_to_bool("on") is True


def test_convert_to_bool_string_false():
    """Test converting string to bool (false values)."""
    assert MT5Utils._convert_to_bool("false") is False
    assert MT5Utils._convert_to_bool("0") is False


def test_convert_to_bool_number():
    """Test converting number to bool."""
    assert MT5Utils._convert_to_bool(1) is True
    assert MT5Utils._convert_to_bool(0) is False


def test_convert_to_list_from_tuple():
    """Test converting tuple to list."""
    result = MT5Utils._convert_to_list((1, 2, 3))
    assert result == [1, 2, 3]


def test_convert_to_list_from_set():
    """Test converting set to list."""
    result = MT5Utils._convert_to_list({1, 2, 3})
    assert isinstance(result, list)
    assert len(result) == 3


def test_convert_to_list_from_single_value():
    """Test converting single value to list."""
    result = MT5Utils._convert_to_list(42)
    assert result == [42]


def test_convert_to_dict_valid():
    """Test converting dict to dict."""
    data = {"a": 1, "b": 2}
    result = MT5Utils._convert_to_dict(data)
    assert result == data


def test_convert_to_dict_invalid():
    """Test error when converting non-dict to dict."""
    with pytest.raises(ValueError, match="Cannot convert"):
        MT5Utils._convert_to_dict([1, 2, 3])


def test_convert_to_tuple_from_list():
    """Test converting list to tuple."""
    result = MT5Utils._convert_to_tuple([1, 2, 3])
    assert result == (1, 2, 3)


def test_convert_to_tuple_from_single_value():
    """Test converting single value to tuple."""
    result = MT5Utils._convert_to_tuple(42)
    assert result == (42,)


def test_get_type_converter_dispatcher():
    """Test type converter dispatcher."""
    dispatcher = MT5Utils._get_type_converter_dispatcher()
    assert "int" in dispatcher
    assert "float" in dispatcher
    assert "str" in dispatcher
    assert "bool" in dispatcher
    assert "list" in dispatcher
    assert "dict" in dispatcher
    assert "tuple" in dispatcher
    assert "datetime" in dispatcher


def test_convert_type_int():
    """Test converting to int."""
    result = MT5Utils.convert_type("42", "int")
    assert result == 42


def test_convert_type_float():
    """Test converting to float."""
    result = MT5Utils.convert_type("3.14", "float")
    assert result == 3.14


def test_convert_type_str():
    """Test converting to str."""
    result = MT5Utils.convert_type(42, "str")
    assert result == "42"


def test_convert_type_bool():
    """Test converting to bool."""
    result = MT5Utils.convert_type("true", "bool")
    assert result is True


def test_convert_type_list():
    """Test converting to list."""
    result = MT5Utils.convert_type((1, 2, 3), "list")
    assert result == [1, 2, 3]


def test_convert_type_tuple():
    """Test converting to tuple."""
    result = MT5Utils.convert_type([1, 2, 3], "tuple")
    assert result == (1, 2, 3)


def test_convert_type_datetime():
    """Test converting to datetime."""
    ts = 1672574400  # 2023-01-01 12:00:00 UTC
    result = MT5Utils.convert_type(ts, "datetime")
    assert isinstance(result, datetime)


def test_convert_type_unsupported():
    """Test error for unsupported type."""
    with pytest.raises(ValueError, match="Unsupported target type"):
        MT5Utils.convert_type(42, "unsupported_type")


def test_convert_type_conversion_error():
    """Test error during type conversion."""
    with pytest.raises(ValueError, match="Failed to convert"):
        MT5Utils.convert_type("not_a_number", "int")


# ==================== Data Formatting Tests ====================

def test_to_dict_named_tuple():
    """Test converting named tuple to dict."""
    from collections import namedtuple
    Point = namedtuple('Point', ['x', 'y'])
    point = Point(1, 2)
    
    result = MT5Utils.to_dict(point)
    assert result == {'x': 1, 'y': 2}


def test_to_dict_object_with_dict():
    """Test converting object with __dict__ to dict."""
    class TestObj:
        def __init__(self):
            self.a = 1
            self.b = 2
            self._private = 3
    
    obj = TestObj()
    result = MT5Utils.to_dict(obj)
    assert result == {'a': 1, 'b': 2}


def test_to_dict_list():
    """Test converting list to dict."""
    result = MT5Utils.to_dict([1, 2, 3])
    assert result == {"items": [1, 2, 3]}


def test_to_dict_other_type():
    """Test converting other types to dict."""
    result = MT5Utils.to_dict(42)
    assert result == {"value": "42"}


def test_to_dataframe_list_of_dicts():
    """Test converting list of dicts to DataFrame."""
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    df = MT5Utils.to_dataframe(data)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["a", "b"]


def test_to_dataframe_list_of_tuples():
    """Test converting list of tuples to DataFrame with columns."""
    data = [(1, 2), (3, 4)]
    df = MT5Utils.to_dataframe(data, columns=["a", "b"])
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["a", "b"]


def test_to_dataframe_named_tuples():
    """Test converting list of named tuples to DataFrame."""
    from collections import namedtuple
    Point = namedtuple('Point', ['x', 'y'])
    data = [Point(1, 2), Point(3, 4)]
    
    df = MT5Utils.to_dataframe(data)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["x", "y"]


def test_to_dataframe_empty_list():
    """Test converting empty list to DataFrame."""
    df = MT5Utils.to_dataframe([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_to_dataframe_error_handling():
    """Test to_dataframe error handling."""
    # Create invalid data that will fail DataFrame conversion
    class BadData:
        def __iter__(self):
            raise Exception("Test error")
    
    with pytest.raises(ValueError, match="Failed to convert to DataFrame"):
        MT5Utils.to_dataframe(BadData())


# ==================== File Operation Tests ====================

def test_save_load_json():
    """Test saving and loading JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.json"
        data = {"a": 1, "b": 2, "c": [1, 2, 3]}
        
        # Save
        result = MT5Utils.save(data, filepath, format="json")
        assert result is True
        assert filepath.exists()
        
        # Load
        loaded = MT5Utils.load(filepath, format="json")
        assert loaded == data


def test_save_json_with_indent():
    """Test saving JSON with custom indent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.json"
        data = {"a": 1}
        
        MT5Utils.save(data, filepath, format="json", indent=4)
        assert filepath.exists()


def test_save_load_csv_dataframe():
    """Test saving and loading CSV with DataFrame."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        
        # Save
        result = MT5Utils.save(df, filepath, format="csv")
        assert result is True
        
        # Load
        loaded = MT5Utils.load(filepath, format="csv")
        assert isinstance(loaded, pd.DataFrame)


def test_save_csv_list_of_dicts():
    """Test saving CSV from list of dicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        
        result = MT5Utils.save(data, filepath, format="csv")
        assert result is True


def test_save_csv_list_of_lists():
    """Test saving CSV from list of lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        data = [[1, 2], [3, 4]]
        
        result = MT5Utils.save(data, filepath, format="csv")
        assert result is True


def test_save_csv_invalid_data():
    """Test error when saving invalid data as CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        
        with pytest.raises(ValueError, match="CSV format requires"):
            MT5Utils.save("invalid", filepath, format="csv")


def test_save_load_pickle():
    """Test saving and loading pickle file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.pkl"
        data = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
        
        # Save
        result = MT5Utils.save(data, filepath, format="pickle")
        assert result is True
        
        # Load
        loaded = MT5Utils.load(filepath, format="pickle")
        assert loaded == data


def test_save_unsupported_format():
    """Test error for unsupported save format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.txt"
        
        with pytest.raises(ValueError, match="Unsupported format"):
            MT5Utils.save({"a": 1}, filepath, format="unsupported")


def test_load_file_not_found():
    """Test error when loading non-existent file."""
    with pytest.raises(FileNotFoundError):
        MT5Utils.load("/nonexistent/file.json", format="json")


def test_load_unsupported_format():
    """Test error for unsupported load format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.txt"
        filepath.write_text("test")
        
        with pytest.raises(ValueError, match="Unsupported format"):
            MT5Utils.load(filepath, format="unsupported")


# ==================== Calculation Tests ====================

def test_calculate_percent_with_kwargs():
    """Test percent calculation with keyword arguments."""
    result = MT5Utils.calculate("percent", value=25, total=100)
    assert result == 25.0


def test_calculate_percent_zero_total():
    """Test percent calculation with zero total."""
    result = MT5Utils.calculate("percent", 10, 0)
    assert result == 0.0


def test_calculate_percent_missing_args():
    """Test error when percent args are missing."""
    with pytest.raises(ValueError, match="value and total are required"):
        MT5Utils.calculate("percent")


def test_calculate_percent_change_with_kwargs():
    """Test percent change with keyword arguments."""
    result = MT5Utils.calculate("percent_change", old_value=100, new_value=150)
    assert result == 50.0


def test_calculate_percent_change_zero_old():
    """Test percent change with zero old value."""
    result = MT5Utils.calculate("percent_change", 0, 100)
    assert result == 0.0


def test_calculate_percent_change_missing_args():
    """Test error when percent_change args are missing."""
    with pytest.raises(ValueError, match="old_value and new_value are required"):
        MT5Utils.calculate("percent_change")


@patch('apps.mt5.util.MT5Utils._calculate_pip_value')
def test_calculate_pip_value(mock_calc):
    """Test pip value calculation."""
    mock_calc.return_value = 10.0
    mock_symbol = Mock()
    
    result = MT5Utils.calculate("pip_value", mock_symbol, 1.0)
    assert result == 10.0
    mock_calc.assert_called_once()


@patch('apps.mt5.util.MT5Utils._calculate_profit')
def test_calculate_profit(mock_calc):
    """Test profit calculation."""
    mock_calc.return_value = 100.0
    
    result = MT5Utils.calculate("profit", 1.1, 1.2, 1.0, 100000)
    assert result == 100.0


@patch('apps.mt5.util.MT5Utils._calculate_margin')
def test_calculate_margin(mock_calc):
    """Test margin calculation."""
    mock_calc.return_value = 1000.0
    
    result = MT5Utils.calculate("margin", 1.0, 1.1, 100, 100000)
    assert result == 1000.0


def test_calculate_unsupported_operation():
    """Test error for unsupported calculation operation."""
    with pytest.raises(ValueError, match="Unsupported operation"):
        MT5Utils.calculate("unsupported_op")


def test_calculate_pip_value_private():
    """Test private pip value calculation method."""
    mock_symbol = Mock()
    mock_symbol.point = 0.00001
    mock_symbol.trade_contract_size = 100000
    
    result = MT5Utils._calculate_pip_value(mock_symbol, 1.0)
    assert result == 1.0


def test_calculate_profit_private_buy():
    """Test private profit calculation for buy."""
    result = MT5Utils._calculate_profit(1.1, 1.2, 1.0, 100000, "buy")
    assert result == pytest.approx(10000.0, rel=1e-6)


def test_calculate_profit_private_sell():
    """Test private profit calculation for sell."""
    result = MT5Utils._calculate_profit(1.2, 1.1, 1.0, 100000, "sell")
    assert result == pytest.approx(10000.0, rel=1e-6)


def test_calculate_margin_private():
    """Test private margin calculation method."""
    result = MT5Utils._calculate_margin(1.0, 1.5, 100, 100000)
    assert result == 1500.0


# ==================== Filling Mode Tests ====================

@patch('apps.mt5.util.mt5')
def test_get_filling_mode_ioc(mock_mt5):
    """Test getting filling mode when IOC is supported."""
    mock_symbol_info = Mock()
    mock_symbol_info.filling_mode = 2  # SYMBOL_FILLING_IOC
    mock_mt5.symbol_info.return_value = mock_symbol_info
    mock_mt5.ORDER_FILLING_IOC = 1
    
    result = MT5Utils.get_filling_mode("EURUSD")
    assert result == 1


@patch('apps.mt5.util.mt5')
def test_get_filling_mode_fok(mock_mt5):
    """Test getting filling mode when only FOK is supported."""
    mock_symbol_info = Mock()
    mock_symbol_info.filling_mode = 1  # SYMBOL_FILLING_FOK
    mock_mt5.symbol_info.return_value = mock_symbol_info
    mock_mt5.ORDER_FILLING_FOK = 0
    
    result = MT5Utils.get_filling_mode("EURUSD")
    assert result == 0


@patch('apps.mt5.util.mt5')
def test_get_filling_mode_none_symbol(mock_mt5):
    """Test getting filling mode when symbol info is None."""
    mock_mt5.symbol_info.return_value = None
    mock_mt5.ORDER_FILLING_FOK = 0
    
    result = MT5Utils.get_filling_mode("INVALID")
    assert result == 0


@patch('apps.mt5.util.mt5')
def test_get_filling_mode_error(mock_mt5):
    """Test error handling in get_filling_mode."""
    mock_mt5.symbol_info.side_effect = Exception("Test error")
    mock_mt5.ORDER_FILLING_FOK = 0
    
    result = MT5Utils.get_filling_mode("EURUSD")
    assert result == 0


# ==================== Timeframe Seconds Tests ====================

@patch('apps.mt5.util.mt5')
def test_timeframe_seconds_m1(mock_mt5):
    """Test timeframe seconds for M1."""
    mock_mt5.TIMEFRAME_M1 = 1
    result = timeframe_seconds(1)
    assert result == 60


@patch('apps.mt5.util.mt5')
def test_timeframe_seconds_h1(mock_mt5):
    """Test timeframe seconds for H1."""
    mock_mt5.TIMEFRAME_H1 = 16385
    result = timeframe_seconds(16385)
    assert result == 3600


@patch('apps.mt5.util.mt5')
def test_timeframe_seconds_d1(mock_mt5):
    """Test timeframe seconds for D1."""
    mock_mt5.TIMEFRAME_D1 = 16408
    result = timeframe_seconds(16408)
    assert result == 86400


# ==================== Synthetic Tick Generation Tests ====================

def test_generate_ticks_from_bars():
    """Test synthetic tick generation from bars using TicksGen."""
    from apps.mt5.util import TicksGen
    
    bars = [
        {
            "time": 1672574400,
            "open": 1.1,
            "high": 1.2,
            "low": 1.0,
            "close": 1.15,
            "spread": 0.0001,
            "tick_volume": 100,
            "real_volume": 1000.0,
        }
    ]
    
    ticks = TicksGen.generate_ticks_from_bars(bars, "EURUSD", 0.00001)
    
    assert len(ticks) == 4  # open, high, low, close
    assert ticks[0]["symbol"] == "EURUSD"
    assert ticks[0]["bid"] == 1.1
    assert ticks[1]["bid"] == 1.2
    assert ticks[2]["bid"] == 1.0
    assert ticks[3]["bid"] == 1.15
