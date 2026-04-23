from __future__ import annotations

from datetime import datetime
import sys
import types

import pandas as pd
import pytest

from haruquant.data import DataCache, YFData


@pytest.fixture(autouse=True)
def isolated_data_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("HQT_DATA_CACHE_PATH", str(tmp_path / "market_data_cache.lmdb"))
    DataCache.clear()
    yield
    DataCache.clear()


def _build_price_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=3, freq="D")
    return pd.DataFrame(
        {
            "Open": [1.0, 2.0, 3.0],
            "High": [1.1, 2.1, 3.1],
            "Low": [0.9, 1.9, 2.9],
            "Close": [1.05, 2.05, 3.05],
            "Volume": [100, 200, 300],
        },
        index=index,
    )


def test_data_cache_key_is_stable_for_equivalent_payloads():
    first = DataCache.make_key(
        "YFData",
        {
            "symbol": "BTC-USD",
            "timeframe": "1d",
            "start": datetime(2024, 1, 1),
            "end": datetime(2024, 1, 10),
            "kwargs": {"auto_adjust": True, "threads": False},
        },
    )
    second = DataCache.make_key(
        "YFData",
        {
            "kwargs": {"threads": False, "auto_adjust": True},
            "end": datetime(2024, 1, 10),
            "timeframe": "1d",
            "symbol": "BTC-USD",
            "start": datetime(2024, 1, 1),
        },
    )
    different = DataCache.make_key(
        "YFData",
        {
            "symbol": "ETH-USD",
            "timeframe": "1d",
            "start": datetime(2024, 1, 1),
            "end": datetime(2024, 1, 10),
        },
    )

    assert first == second
    assert first != different


def test_yf_download_uses_disk_cache(monkeypatch):
    calls = {"count": 0}
    frame = _build_price_frame()

    def fake_download(**kwargs):
        calls["count"] += 1
        return frame.copy()

    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        types.SimpleNamespace(download=fake_download),
    )

    first = YFData.download("BTC-USD", start="2024-01-01", interval="1d", cache=True)
    second = YFData.download("BTC-USD", start="2024-01-01", interval="1d", cache=True)

    assert calls["count"] == 1
    assert list(first.df.columns) == ["open", "high", "low", "close", "volume"]
    pd.testing.assert_frame_equal(first.df, second.df)


def test_yf_download_bypasses_cache_when_disabled(monkeypatch):
    calls = {"count": 0}
    frame = _build_price_frame()

    def fake_download(**kwargs):
        calls["count"] += 1
        return frame.copy()

    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        types.SimpleNamespace(download=fake_download),
    )

    YFData.download("BTC-USD", start="2024-01-01", interval="1d", cache=False)
    YFData.download("BTC-USD", start="2024-01-01", interval="1d", cache=False)

    assert calls["count"] == 2


def test_yf_download_cache_separates_different_params(monkeypatch):
    calls = {"count": 0}
    frame = _build_price_frame()

    def fake_download(**kwargs):
        calls["count"] += 1
        return frame.copy()

    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        types.SimpleNamespace(download=fake_download),
    )

    YFData.download("BTC-USD", start="2024-01-01", interval="1d", cache=True)
    YFData.download("BTC-USD", start="2024-01-02", interval="1d", cache=True)

    assert calls["count"] == 2
