from datetime import datetime, timezone

import pandas as pd
import pytest

from apps.utils.datetime_utils import (
    normalize_timestamp,
    normalize_timezone_for_series,
    parse_datetime,
    to_naive_utc,
    to_utc,
)


def test_parse_datetime_from_iso_z():
    dt = parse_datetime("2026-02-17T14:00:00Z")
    assert dt.tzinfo is not None
    assert dt.astimezone(timezone.utc).hour == 14


def test_parse_datetime_from_epoch_milliseconds():
    dt = parse_datetime(1_771_336_800_000)
    assert dt.tzinfo is not None
    assert normalize_timestamp(dt, output="epoch_ms") == 1_771_336_800_000


def test_to_utc_and_to_naive_utc():
    naive = datetime(2026, 2, 17, 10, 0, 0)
    aware_utc = to_utc(naive, assume_tz="UTC")
    naive_utc = to_naive_utc(naive, assume_tz="UTC")

    assert aware_utc.tzinfo is not None
    assert aware_utc.tzinfo == timezone.utc
    assert naive_utc.tzinfo is None
    assert naive_utc.hour == 10


def test_normalize_timestamp_iso_output():
    out = normalize_timestamp("2026-02-17T10:00:00+00:00", output="iso")
    assert out == "2026-02-17T10:00:00Z"


def test_normalize_timezone_for_datetime_index():
    idx = pd.date_range("2026-02-17 10:00:00", periods=2, freq="h")
    out = normalize_timezone_for_series(idx, target_tz="Europe/Athens", make_naive=False)
    assert isinstance(out, pd.DatetimeIndex)
    assert out.tz is not None


def test_normalize_timezone_for_series_make_naive():
    series = pd.Series(pd.date_range("2026-02-17 10:00:00", periods=2, freq="h", tz="UTC"))
    out = normalize_timezone_for_series(series, target_tz="Europe/Athens", make_naive=True)
    assert isinstance(out, pd.Series)
    assert out.dt.tz is None


def test_parse_datetime_invalid_input_raises():
    with pytest.raises(ValueError):
        parse_datetime("")

