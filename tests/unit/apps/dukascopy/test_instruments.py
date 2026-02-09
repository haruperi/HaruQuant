"""Tests for dukascopy instruments module."""

import pytest
from apps.dukascopy.instruments import get_instrument


class TestGetInstrument:
    """Test cases for get_instrument function."""

    def test_get_instrument_empty_string(self):
        """Test with empty string returns empty string."""
        result = get_instrument("")
        assert result == ""

    def test_get_instrument_none(self):
        """Test with None returns None."""
        result = get_instrument(None)
        assert result is None

    def test_get_instrument_valid_mapping(self):
        """Test with valid instrument in map."""
        result = get_instrument("EURUSD")
        assert result == "EUR/USD"

    def test_get_instrument_with_spaces(self):
        """Test normalization removes spaces."""
        result = get_instrument("EUR USD")
        assert result == "EUR/USD"

    def test_get_instrument_with_dashes(self):
        """Test normalization removes dashes."""
        result = get_instrument("EUR-USD")
        assert result == "EUR/USD"

    def test_get_instrument_with_dots(self):
        """Test normalization removes dots."""
        result = get_instrument("EUR.USD")
        assert result == "EUR/USD"

    def test_get_instrument_lowercase(self):
        """Test normalization converts to uppercase."""
        result = get_instrument("eurusd")
        assert result == "EUR/USD"

    def test_get_instrument_already_formatted(self):
        """Test instrument already containing / is returned as-is."""
        result = get_instrument("EUR/USD")
        assert result == "EUR/USD"

    def test_get_instrument_unknown(self):
        """Test unknown instrument returns original name."""
        result = get_instrument("UNKNOWN")
        assert result == "UNKNOWN"

    def test_get_instrument_stock_symbol(self):
        """Test with stock symbol."""
        result = get_instrument("AAPL")
        assert result == "AAPL.US/USD"

    def test_get_instrument_mixed_case_stock(self):
        """Test stock symbol with mixed case."""
        result = get_instrument("aapl")
        assert result == "AAPL.US/USD"

    def test_get_instrument_crypto(self):
        """Test with crypto symbol."""
        result = get_instrument("BTCUSD")
        assert result == "BTC/USD"

    def test_get_instrument_with_multiple_separators(self):
        """Test normalization with multiple separator types."""
        result = get_instrument("EUR - USD")
        assert result == "EUR/USD"

    def test_get_instrument_forex_pair(self):
        """Test common forex pair."""
        result = get_instrument("GBPUSD")
        assert result == "GBP/USD"

    def test_get_instrument_audcad(self):
        """Test AUD/CAD pair."""
        result = get_instrument("AUDCAD")
        assert result == "AUD/CAD"

    def test_get_instrument_index(self):
        """Test index instrument."""
        result = get_instrument("DAX")
        assert result == "E_DAAX"

    def test_get_instrument_commodity(self):
        """Test commodity instrument."""
        result = get_instrument("CRUDE")
        assert result == "E_Light"

    def test_get_instrument_with_slash_after_normalization(self):
        """Test that instrument with slash after normalization is returned as-is."""
        # This tests line 4011-4012: if "/" in name: return name
        result = get_instrument("CUSTOM/PAIR")
        assert result == "CUSTOM/PAIR"
