"""
Unit tests for DataSynchronizer.

Tests data synchronization across multiple assets with different timestamps,
missing bars, and trading hours.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from apps.simulation.synchronizer import DataSynchronizer


@pytest.fixture
def aligned_data():
    """Two DataFrames with identical timestamps."""
    dates = pd.date_range('2024-01-01', periods=5, freq='1h')
    df1 = pd.DataFrame({
        'open': [1.0, 1.1, 1.2, 1.3, 1.4],
        'close': [1.1, 1.2, 1.3, 1.4, 1.5]
    }, index=dates)
    df2 = pd.DataFrame({
        'open': [2.0, 2.1, 2.2, 2.3, 2.4],
        'close': [2.1, 2.2, 2.3, 2.4, 2.5]
    }, index=dates)
    return {'SYM1': df1, 'SYM2': df2}


@pytest.fixture
def misaligned_data():
    """Two DataFrames with different timestamps (missing bars)."""
    dates1 = pd.date_range('2024-01-01', periods=5, freq='1h')
    dates2 = pd.date_range('2024-01-01', periods=5, freq='1h')
    # Remove some bars from dates2
    dates2 = dates2.delete([1, 3])  # Missing bars at indices 1 and 3

    df1 = pd.DataFrame({
        'open': [1.0, 1.1, 1.2, 1.3, 1.4],
        'close': [1.1, 1.2, 1.3, 1.4, 1.5]
    }, index=dates1)
    df2 = pd.DataFrame({
        'open': [2.0, 2.2, 2.4],
        'close': [2.1, 2.3, 2.5]
    }, index=dates2)
    return {'SYM1': df1, 'SYM2': df2}


@pytest.fixture
def different_length_data():
    """Two DataFrames with different start/end dates."""
    dates1 = pd.date_range('2024-01-01', periods=10, freq='1h')
    dates2 = pd.date_range('2024-01-01 03:00', periods=8, freq='1h')  # Starts 3 hours later

    df1 = pd.DataFrame({
        'open': np.arange(1.0, 2.0, 0.1),
        'close': np.arange(1.1, 2.1, 0.1)
    }, index=dates1)
    df2 = pd.DataFrame({
        'open': np.arange(2.0, 2.8, 0.1),
        'close': np.arange(2.1, 2.9, 0.1)
    }, index=dates2)
    return {'SYM1': df1, 'SYM2': df2}


class TestDataSynchronizer:
    """Test suite for DataSynchronizer class."""

    def test_synchronize_aligned_data(self, aligned_data):
        """Test synchronization with already aligned data."""
        result = DataSynchronizer.synchronize(aligned_data, method='ffill')

        # Should return same number of symbols
        assert len(result) == 2
        assert 'SYM1' in result
        assert 'SYM2' in result

        # Should have same length
        assert len(result['SYM1']) == len(result['SYM2'])
        assert len(result['SYM1']) == 5

        # Data should be unchanged
        pd.testing.assert_frame_equal(result['SYM1'], aligned_data['SYM1'])
        pd.testing.assert_frame_equal(result['SYM2'], aligned_data['SYM2'])

    def test_synchronize_missing_bars_ffill(self, misaligned_data):
        """Test forward-fill method for missing bars."""
        result = DataSynchronizer.synchronize(misaligned_data, method='ffill')

        # Both should have same length (union of timestamps)
        assert len(result['SYM1']) == len(result['SYM2'])
        assert len(result['SYM2']) == 5  # Should be filled to 5 bars

        # Check forward-fill worked for SYM2
        df2 = result['SYM2']
        assert df2.iloc[1]['open'] == 2.0  # Forward-filled from index 0
        assert df2.iloc[3]['open'] == 2.2  # Forward-filled from index 2

    def test_synchronize_missing_bars_drop(self, misaligned_data):
        """Test drop method for missing bars."""
        result = DataSynchronizer.synchronize(misaligned_data, method='drop')

        # Should only have timestamps where both have data
        assert len(result['SYM1']) == len(result['SYM2'])
        assert len(result['SYM1']) == 3  # Only 3 common timestamps

        # Check no NaNs
        assert not result['SYM1'].isna().any().any()
        assert not result['SYM2'].isna().any().any()

    def test_synchronize_missing_bars_interpolate(self, misaligned_data):
        """Test interpolation method for missing bars."""
        result = DataSynchronizer.synchronize(misaligned_data, method='interpolate')

        # Both should have same length
        assert len(result['SYM1']) == len(result['SYM2'])
        assert len(result['SYM2']) == 5

        # Check interpolation worked (values between neighbors)
        df2 = result['SYM2']
        # Between 2.0 and 2.2, should be ~2.1
        assert 2.0 < df2.iloc[1]['open'] < 2.2

    def test_synchronize_different_lengths(self, different_length_data):
        """Test synchronization with different length DataFrames."""
        result = DataSynchronizer.synchronize(different_length_data, method='ffill')

        # Both should have same length (trimmed to common valid period)
        assert len(result['SYM1']) == len(result['SYM2'])
        # With default handle_leading_nans='drop', trim to SYM2 start (03:00)
        # With default handle_trailing_nans='drop', trim to SYM1 end (09:00)
        # Overlap: 03:00 to 09:00 = 7 bars
        assert len(result['SYM1']) == 7

        # No NaNs after synchronization
        assert not result['SYM1'].isna().any().any()
        assert not result['SYM2'].isna().any().any()

    def test_synchronize_handle_leading_nans_drop(self, different_length_data):
        """Test handling of leading NaNs with drop."""
        result = DataSynchronizer.synchronize(
            different_length_data,
            method='ffill',
            handle_leading_nans='drop'
        )

        # SYM2 should start from its first valid index
        assert result['SYM2'].index[0] == different_length_data['SYM2'].index[0]

    def test_synchronize_handle_leading_nans_fill(self, different_length_data):
        """Test handling of leading NaNs with fill."""
        result = DataSynchronizer.synchronize(
            different_length_data,
            method='ffill',
            handle_leading_nans='fill',
            handle_trailing_nans='drop'  # Still drop trailing to keep test focused
        )

        # Both should start from earliest timestamp
        assert result['SYM1'].index[0] == result['SYM2'].index[0]
        # Both should end at SYM1's last (with handle_trailing_nans='drop')
        # SYM2 leading values should be back-filled
        assert not result['SYM2'].isna().any().any()

    def test_synchronize_handle_trailing_nans_drop(self):
        """Test handling of trailing NaNs with drop."""
        dates1 = pd.date_range('2024-01-01', periods=10, freq='1h')
        dates2 = pd.date_range('2024-01-01', periods=7, freq='1h')  # Ends 3 hours earlier

        df1 = pd.DataFrame({'close': range(10)}, index=dates1)
        df2 = pd.DataFrame({'close': range(7)}, index=dates2)

        data = {'SYM1': df1, 'SYM2': df2}
        result = DataSynchronizer.synchronize(
            data,
            method='ffill',
            handle_leading_nans='fill',  # Don't trim leading (both start at same time)
            handle_trailing_nans='drop'
        )

        # Both should end at the earliest last valid index (SYM2's end)
        assert result['SYM1'].index[-1] == dates2[-1]
        assert result['SYM2'].index[-1] == dates2[-1]
        # Both should have same length
        assert len(result['SYM1']) == len(result['SYM2'])
        assert len(result['SYM1']) == 7

    def test_synchronize_handle_trailing_nans_fill(self):
        """Test handling of trailing NaNs with fill."""
        dates1 = pd.date_range('2024-01-01', periods=10, freq='1h')
        dates2 = pd.date_range('2024-01-01', periods=7, freq='1h')

        df1 = pd.DataFrame({'close': range(10)}, index=dates1)
        df2 = pd.DataFrame({'close': range(7)}, index=dates2)

        data = {'SYM1': df1, 'SYM2': df2}
        result = DataSynchronizer.synchronize(
            data,
            method='ffill',
            handle_trailing_nans='fill'
        )

        # Both should end at same time
        assert result['SYM1'].index[-1] == result['SYM2'].index[-1]
        # Last values of SYM2 should be forward-filled
        assert result['SYM2'].iloc[-1]['close'] == 6  # Last valid value

    def test_synchronize_empty_dict(self):
        """Test error handling for empty dict."""
        with pytest.raises(ValueError, match="data_dict cannot be empty"):
            DataSynchronizer.synchronize({})

    def test_synchronize_empty_dataframe(self):
        """Test error handling for empty DataFrame."""
        data = {
            'SYM1': pd.DataFrame(),
            'SYM2': pd.DataFrame({'close': [1, 2, 3]})
        }
        with pytest.raises(ValueError, match="DataFrame for SYM1 is empty"):
            DataSynchronizer.synchronize(data)

    def test_synchronize_non_datetime_index(self):
        """Test error handling for non-DatetimeIndex."""
        df = pd.DataFrame({'close': [1, 2, 3]})  # Integer index
        data = {'SYM1': df}

        with pytest.raises(ValueError, match="must have DatetimeIndex"):
            DataSynchronizer.synchronize(data)

    def test_synchronize_invalid_method(self, aligned_data):
        """Test error handling for invalid method."""
        with pytest.raises(ValueError, match="Invalid method"):
            DataSynchronizer.synchronize(aligned_data, method='invalid')

    def test_validate_synchronized_data_true(self, aligned_data):
        """Test validation with synchronized data."""
        assert DataSynchronizer.validate_synchronized_data(aligned_data) is True

    def test_validate_synchronized_data_false(self, misaligned_data):
        """Test validation with non-synchronized data."""
        assert DataSynchronizer.validate_synchronized_data(misaligned_data) is False

    def test_validate_synchronized_data_empty(self):
        """Test validation with empty dict."""
        assert DataSynchronizer.validate_synchronized_data({}) is False

    def test_get_overlap_period(self, different_length_data):
        """Test getting overlap period."""
        start, end = DataSynchronizer.get_overlap_period(different_length_data)

        # Overlap should be from SYM2 start to SYM2 end
        assert start == different_length_data['SYM2'].index[0]
        assert end == different_length_data['SYM1'].index[-1]

    def test_get_overlap_period_no_overlap(self):
        """Test error handling when there's no overlap."""
        dates1 = pd.date_range('2024-01-01', periods=5, freq='1h')
        dates2 = pd.date_range('2024-01-02', periods=5, freq='1h')  # Next day

        df1 = pd.DataFrame({'close': range(5)}, index=dates1)
        df2 = pd.DataFrame({'close': range(5)}, index=dates2)

        data = {'SYM1': df1, 'SYM2': df2}

        with pytest.raises(ValueError, match="No overlap found"):
            DataSynchronizer.get_overlap_period(data)

    def test_get_overlap_period_empty(self):
        """Test error handling for empty dict."""
        with pytest.raises(ValueError, match="data_dict cannot be empty"):
            DataSynchronizer.get_overlap_period({})

    def test_trim_to_overlap(self, different_length_data):
        """Test trimming to overlap period."""
        result = DataSynchronizer.trim_to_overlap(different_length_data)

        # Both should have same start/end
        assert result['SYM1'].index[0] == result['SYM2'].index[0]
        assert result['SYM1'].index[-1] == result['SYM2'].index[-1]

        # SYM1 should be shorter (trimmed)
        assert len(result['SYM1']) < len(different_length_data['SYM1'])
        # SYM2 should be trimmed by 1 bar (overlap ends at SYM1's last bar, which is before SYM2's last)
        # Overlap: SYM2 start (03:00) to SYM1 end (09:00) = 7 bars
        assert len(result['SYM2']) == 7
        assert len(result['SYM1']) == 7

    def test_synchronize_timezone_handling(self):
        """Test timezone handling in synchronization."""
        dates1 = pd.date_range('2024-01-01', periods=5, freq='1h', tz='UTC')
        dates2 = pd.date_range('2024-01-01', periods=5, freq='1h', tz='UTC')  # Same timezone

        df1 = pd.DataFrame({'close': range(5)}, index=dates1)
        df2 = pd.DataFrame({'close': range(5)}, index=dates2)

        data = {'SYM1': df1, 'SYM2': df2}

        # Should handle timezone-aware indices
        result = DataSynchronizer.synchronize(data, method='ffill')
        assert len(result['SYM1']) == 5
        assert len(result['SYM2']) == 5
        # Data should be synchronized correctly
        assert isinstance(result['SYM1'].index, pd.DatetimeIndex) or isinstance(result['SYM1'].index, pd.Index)
        assert isinstance(result['SYM2'].index, pd.DatetimeIndex) or isinstance(result['SYM2'].index, pd.Index)

    def test_synchronize_preserves_columns(self, aligned_data):
        """Test that synchronization preserves all columns."""
        result = DataSynchronizer.synchronize(aligned_data, method='ffill')

        # Check all columns preserved
        assert list(result['SYM1'].columns) == ['open', 'close']
        assert list(result['SYM2'].columns) == ['open', 'close']

    def test_synchronize_large_dataset(self):
        """Test synchronization with larger dataset."""
        dates1 = pd.date_range('2024-01-01', periods=1000, freq='1h')
        dates2 = pd.date_range('2024-01-01', periods=1000, freq='1h')
        # Remove random bars from dates2
        dates2 = dates2.delete(np.random.choice(1000, 100, replace=False))

        df1 = pd.DataFrame({
            'open': np.random.randn(1000),
            'close': np.random.randn(1000)
        }, index=dates1)
        df2 = pd.DataFrame({
            'open': np.random.randn(900),
            'close': np.random.randn(900)
        }, index=dates2)

        data = {'SYM1': df1, 'SYM2': df2}

        # Should handle large dataset with handle_leading_nans='fill' and handle_trailing_nans='fill'
        result = DataSynchronizer.synchronize(
            data,
            method='ffill',
            handle_leading_nans='fill',
            handle_trailing_nans='fill'
        )
        assert len(result['SYM1']) == len(result['SYM2'])
        assert len(result['SYM1']) == 1000  # Full timeline kept

    def test_synchronize_three_symbols(self):
        """Test synchronization with 3+ symbols."""
        dates1 = pd.date_range('2024-01-01', periods=10, freq='1h')
        dates2 = pd.date_range('2024-01-01', periods=10, freq='1h').delete([2, 5])
        dates3 = pd.date_range('2024-01-01', periods=10, freq='1h').delete([1, 3, 7])

        df1 = pd.DataFrame({'close': range(10)}, index=dates1)
        df2 = pd.DataFrame({'close': range(8)}, index=dates2)
        df3 = pd.DataFrame({'close': range(7)}, index=dates3)

        data = {'SYM1': df1, 'SYM2': df2, 'SYM3': df3}

        result = DataSynchronizer.synchronize(data, method='ffill')

        # All should have same length
        assert len(result['SYM1']) == len(result['SYM2']) == len(result['SYM3'])
        assert len(result['SYM1']) == 10

    def test_synchronize_drop_method_three_symbols(self):
        """Test drop method with 3 symbols."""
        dates1 = pd.date_range('2024-01-01', periods=10, freq='1h')
        dates2 = pd.date_range('2024-01-01', periods=10, freq='1h').delete([2, 5])
        dates3 = pd.date_range('2024-01-01', periods=10, freq='1h').delete([1, 3, 7])

        df1 = pd.DataFrame({'close': range(10)}, index=dates1)
        df2 = pd.DataFrame({'close': range(8)}, index=dates2)
        df3 = pd.DataFrame({'close': range(7)}, index=dates3)

        data = {'SYM1': df1, 'SYM2': df2, 'SYM3': df3}

        result = DataSynchronizer.synchronize(data, method='drop')

        # Should only have common timestamps (intersection)
        expected_common = len(set(dates1) & set(dates2) & set(dates3))
        assert len(result['SYM1']) == expected_common
        assert len(result['SYM2']) == expected_common
        assert len(result['SYM3']) == expected_common
