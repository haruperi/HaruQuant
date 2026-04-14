"""Tests for CSVDataSource."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import pytest

from backend.services.market_data.data_getters import CSVDataSource, clear_data_cache


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    """Create a sample OHLCV CSV file."""
    data = (
        "date,open,high,low,close,volume\n"
        "2025-01-02 09:00,1.1000,1.1010,1.0990,1.1005,100\n"
        "2025-01-02 09:01,1.1005,1.1015,1.0995,1.1010,120\n"
        "2025-01-02 09:02,1.1010,1.1020,1.1000,1.1015,110\n"
        "2025-01-02 09:03,1.1015,1.1025,1.1005,1.1020,130\n"
        "2025-01-02 09:04,1.1020,1.1030,1.1010,1.1025,140\n"
        "2025-01-02 09:05,1.1025,1.1035,1.1015,1.1030,150\n"
        "2025-01-02 09:06,1.1030,1.1040,1.1020,1.1035,160\n"
        "2025-01-02 09:07,1.1035,1.1045,1.1025,1.1040,170\n"
        "2025-01-02 09:08,1.1040,1.1050,1.1030,1.1045,180\n"
        "2025-01-02 09:09,1.1045,1.1055,1.1035,1.1050,190\n"
    )
    filepath = tmp_path / "eurusd_h1.csv"
    filepath.write_text(data)
    return filepath


@pytest.fixture()
def csv_with_timestamp(tmp_path: Path) -> Path:
    """Create CSV using 'timestamp' column name instead of 'date'."""
    data = (
        "timestamp,open,high,low,close,volume,spread\n"
        "2025-03-01 00:00,1.2000,1.2020,1.1990,1.2010,500,1.5\n"
        "2025-03-01 01:00,1.2010,1.2030,1.2000,1.2020,520,1.6\n"
        "2025-03-01 02:00,1.2020,1.2040,1.2010,1.2030,540,1.7\n"
        "2025-03-01 03:00,1.2030,1.2050,1.2020,1.2040,560,1.8\n"
        "2025-03-01 04:00,1.2040,1.2060,1.2030,1.2050,580,1.9\n"
    )
    filepath = tmp_path / "gbpusd_h1.csv"
    filepath.write_text(data)
    return filepath


@pytest.fixture()
def csv_uppercase(tmp_path: Path) -> Path:
    """Create CSV with uppercase column names."""
    data = (
        "Date,Open,High,Low,Close,Volume\n"
        "2025-06-01,1.3000,1.3020,1.2990,1.3010,300\n"
        "2025-06-02,1.3010,1.3030,1.3000,1.3020,310\n"
        "2025-06-03,1.3020,1.3040,1.3010,1.3030,320\n"
    )
    filepath = tmp_path / "usdjpy.csv"
    filepath.write_text(data)
    return filepath


@pytest.fixture()
def csv_no_date_col(tmp_path: Path) -> Path:
    """Create CSV without a recognizable date column."""
    data = (
        "open,high,low,close,volume\n"
        "1.4000,1.4020,1.3990,1.4010,200\n"
        "1.4010,1.4030,1.4000,1.4020,210\n"
    )
    filepath = tmp_path / "no_date.csv"
    filepath.write_text(data)
    return filepath


@pytest.fixture()
def csv_empty(tmp_path: Path) -> Path:
    """Create an empty CSV file."""
    filepath = tmp_path / "empty.csv"
    filepath.write_text("date,open,high,low,close,volume\n")
    return filepath


@pytest.fixture()
def csv_mixed_case(tmp_path: Path) -> Path:
    """Create CSV with mixed-case column names and tick_volume."""
    data = (
        "Date,OPEN,HIGH,LOW,CLOSE,Tick_Volume\n"
        "2025-07-01,1.5000,1.5020,1.4990,1.5010,400\n"
        "2025-07-02,1.5010,1.5030,1.5000,1.5020,410\n"
        "2025-07-03,1.5020,1.5040,1.5010,1.5030,420\n"
        "2025-07-04,1.5030,1.5050,1.5020,1.5040,430\n"
    )
    filepath = tmp_path / "mixed.csv"
    filepath.write_text(data)
    return filepath


class TestCSVDataSourceInit:
    """Test CSVDataSource initialization."""

    def test_init_with_string_path(self, sample_csv: Path) -> None:
        source = CSVDataSource(str(sample_csv))
        assert source._filepath == sample_csv

    def test_init_with_path_object(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        assert source._filepath == sample_csv

    def test_init_with_custom_date_column(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv, date_column="date")
        assert source._date_column == "date"

    def test_init_with_cache_disabled(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv, cache=False)
        assert source._cache is False

    def test_init_with_read_csv_kwargs(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv, sep=",", skiprows=0)
        assert source._read_csv_kwargs["sep"] == ","


class TestCSVDataSourceFetch:
    """Test CSVDataSource.fetch_data behavior."""

    def test_fetch_full_range(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        df = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=10)
        assert df is not None
        assert len(df) == 10
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_fetch_partial_range(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        df = source.fetch_data("EURUSD", "H1", start_pos=2, end_pos=7)
        assert df is not None
        assert len(df) == 5
        assert df.index[0] == pd.Timestamp("2025-01-02 09:02")

    def test_fetch_with_timestamp_column(self, csv_with_timestamp: Path) -> None:
        source = CSVDataSource(csv_with_timestamp)
        df = source.fetch_data("GBPUSD", "H1", start_pos=0, end_pos=5)
        assert df is not None
        assert len(df) == 5
        assert "spread" in df.columns

    def test_fetch_with_uppercase_columns(self, csv_uppercase: Path) -> None:
        source = CSVDataSource(csv_uppercase)
        df = source.fetch_data("USDJPY", "D1", start_pos=0, end_pos=3)
        assert df is not None
        assert len(df) == 3
        assert "close" in df.columns

    def test_fetch_with_mixed_case_columns(self, csv_mixed_case: Path) -> None:
        source = CSVDataSource(csv_mixed_case)
        df = source.fetch_data("EURJPY", "D1", start_pos=0, end_pos=4)
        assert df is not None
        assert len(df) == 4
        assert "close" in df.columns
        assert "volume" in df.columns

    def test_fetch_invalid_start_pos(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        result = source.fetch_data("EURUSD", "H1", start_pos=-1, end_pos=5)
        assert result is None

    def test_fetch_end_beyond_length(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        result = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=999)
        assert result is None

    def test_fetch_start_greater_than_end(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        result = source.fetch_data("EURUSD", "H1", start_pos=5, end_pos=3)
        assert result is None

    def test_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.csv"
        source = CSVDataSource(missing)
        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=10)

    def test_empty_csv(self, csv_empty: Path) -> None:
        source = CSVDataSource(csv_empty)
        with pytest.raises(ValueError, match="CSV file is empty"):
            source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=10)

    def test_no_date_column(self, csv_no_date_col: Path) -> None:
        source = CSVDataSource(csv_no_date_col)
        with pytest.raises(ValueError, match="No date/time column detected"):
            source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=10)

    def test_explicit_date_column(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv, date_column="date")
        df = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=3)
        assert df is not None
        assert len(df) == 3

    def test_ohlcv_columns_present(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        df = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=10)
        assert df is not None
        for col in ("open", "high", "low", "close", "volume"):
            assert col in df.columns

    def test_numeric_columns(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        df = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=10)
        assert df is not None
        assert df["close"].dtype in (float, "float64")
        assert df["volume"].dtype in (float, "float64", int, "int64")

    def test_index_is_sorted(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv)
        df = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=10)
        assert df is not None
        assert df.index.is_monotonic_increasing


class TestCSVDataSourceCaching:
    """Test CSVDataSource caching behavior."""

    def test_caching_returns_copy(self, sample_csv: Path) -> None:
        source = CSVDataSource(sample_csv, cache=True)
        df1 = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=5)
        df2 = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=5)
        assert df1 is not df2  # different objects

    def test_cache_clear(self, sample_csv: Path) -> None:
        clear_data_cache()
        source = CSVDataSource(sample_csv, cache=True)
        source._loaded = None  # reset instance cache
        df = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=5)
        assert df is not None


class TestCSVDataSourceIntegration:
    """Test CSVDataSource integration with prepare_ohlcvs_dataset."""

    def test_prepare_ohlcvs_dataset(self, sample_csv: Path) -> None:
        """Wire CSVDataSource through the full research pipeline."""
        from backend.services.research.datasets import (
            prepare_ohlcvs_dataset,
        )

        # Need enough bars for validation to pass (need at least some bars)
        # Create a larger CSV for this test
        rows = []
        for i in range(200):
            hour = 9 + i // 60
            minute = i % 60
            base = 1.1000 + i * 0.0005
            rows.append(
                f"2025-01-02 {hour:02d}:{minute:02d},"
                f"{base:.4f},{base+0.0010:.4f},{base-0.0010:.4f},{base+0.0005:.4f},{100+i}"
            )
        large_csv = sample_csv.parent / "eurusd_large.csv"
        header = "date,open,high,low,close,volume\n"
        large_csv.write_text(header + "\n".join(rows))

        source = CSVDataSource(large_csv)
        dataset = prepare_ohlcvs_dataset(
            source=source,
            symbol="EURUSD",
            timeframe="M1",
            start_pos=0,
            end_pos=200,
        )

        assert dataset.data is not None
        assert len(dataset.data) > 0
        assert dataset.report.is_valid
        assert "close" in dataset.data.columns or "Close" in dataset.data.columns
