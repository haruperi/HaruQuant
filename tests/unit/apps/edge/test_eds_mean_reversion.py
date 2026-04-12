from __future__ import annotations

import pandas as pd

from backend.services.research import eds_mean_reversion as mr_module
from backend.services.research.config import BootstrapConfig, MeanReversionConfig, PermutationConfig


def _sample_df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=40, freq="h")
    close = [1.1000 + (0.00005 if i % 2 == 0 else -0.00005) for i in range(40)]
    open_prices = [close[0]] + close[:-1]
    high = [price + 0.0002 for price in close]
    low = [price - 0.0002 for price in close]
    return pd.DataFrame(
        {
            "Open": open_prices,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": [100] * len(close),
            "Spread": [10] * len(close),
        },
        index=idx,
    )


def test_eds_mean_reversion_persists_buy_trades(monkeypatch):
    def fake_zscore(series: pd.Series, window: int) -> pd.Series:
        values = [0.0] * len(series)
        values[24] = -2.5
        values[25] = -1.8
        values[26] = 0.2
        return pd.Series(values, index=series.index, dtype=float)

    def fake_bbw(series: pd.Series, n: int, k: float) -> pd.Series:
        return pd.Series([0.05] * len(series), index=series.index, dtype=float)

    def fake_rank(series: pd.Series, window: int) -> pd.Series:
        return pd.Series([0.1] * len(series), index=series.index, dtype=float)

    def fake_adr(df: pd.DataFrame, n: int, high_col: str = "High", low_col: str = "Low") -> pd.Series:
        return pd.Series([0.0020] * len(df), index=df.index, dtype=float)

    monkeypatch.setattr(mr_module, "zscore", fake_zscore)
    monkeypatch.setattr(mr_module, "bb_width", fake_bbw)
    monkeypatch.setattr(mr_module, "rolling_percentile_rank", fake_rank)
    monkeypatch.setattr(mr_module, "adr", fake_adr)

    result = mr_module.run_eds_mean_reversion(
        _sample_df(),
        symbol="EURUSD",
        timeframe="H1",
        cfg=MeanReversionConfig(
            sma_n=5,
            z_entry=1.0,
            bbw_n=5,
            bbw_k=2.0,
            compression_window=10,
            compression_q=0.8,
            atr_n=5,
            max_hold_bars=6,
            k_stop_atr=1.0,
        ),
        boot=BootstrapConfig(n_boot=25, block_size=5),
        perm=PermutationConfig(n_perm=25),
    )

    assert result.stats.n_trades > 0
    assert any(trade.side == "BUY" for trade in result.trades)
