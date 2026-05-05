from __future__ import annotations

import pandas as pd

from haruquant.research import (
    UnsupervisedResearchConfig,
    UnsupervisedResearchService,
)
from haruquant.strategy import StrategyAdapter
from haruquant.strategy import BaseStrategy


def _market_frame(rows: int = 96) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=rows, freq="h", tz="UTC")
    closes = []
    for idx in range(rows):
        drift = 0.0007 * idx if idx < rows // 2 else -0.0009 * (idx - rows // 2)
        closes.append(1.10 + drift + (0.0004 if idx % 11 == 0 else 0.0))
    close_series = pd.Series(closes, index=index)
    return pd.DataFrame(
        {
            "open": close_series.values,
            "high": (close_series + 0.0012).values,
            "low": (close_series - 0.0012).values,
            "close": close_series.values,
            "volume": [100 + idx for idx in range(rows)],
            "ema_20": close_series.ewm(span=20, adjust=False).mean().values,
            "ema_50": close_series.ewm(span=50, adjust=False).mean().values,
            "entry_signal": [1 if idx % 5 == 0 else 0 for idx in range(rows)],
            "exit_signal": [1 if idx % 19 == 0 else 0 for idx in range(rows)],
            "price": close_series.values,
        },
        index=index,
    )


class _DummyStrategy(BaseStrategy):
    def on_init(self) -> None:
        return None

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return data


def test_unsupervised_research_service_builds_contexts_and_report() -> None:
    service = UnsupervisedResearchService()
    frame = _market_frame()
    config = UnsupervisedResearchConfig(enable_signal_adaptation=True)

    result = service.analyze_frame(frame, signal_frame=frame, config=config)

    assert result.status == "COMPLETED"
    assert result.report is not None
    assert result.feature_columns
    assert result.feature_metadata["name"] == "market_regime_core"
    assert "exclude_forward_returns_from_feature_space" in result.guardrails
    assert "cluster_count" in result.strategy_context
    assert "regime_name" in result.risk_context
    assert result.to_metadata()["report"]["pca"]["model"] == "pca"


def test_unsupervised_research_service_skips_small_samples() -> None:
    service = UnsupervisedResearchService()
    frame = _market_frame(rows=6)
    config = UnsupervisedResearchConfig(min_rows=20)

    result = service.analyze_frame(frame, config=config)

    assert result.status == "SKIPPED"
    assert result.report is None
    assert "insufficient rows" in (result.reason or "")


def test_strategy_adapter_includes_unsupervised_metadata_in_signal_intent() -> None:
    strategy = _DummyStrategy({"symbol": "EURUSD", "strategy_id": "dummy"})
    strategy.on_init()
    adapter = StrategyAdapter(strategy)
    data = pd.DataFrame(
        {
            "entry_signal": [0, 1],
            "exit_signal": [0, 0],
            "price": [1.10, 1.11],
            "cluster_label": [0, 2],
        },
        index=pd.date_range("2025-01-01", periods=2, freq="h", tz="UTC"),
    )
    data.attrs["cluster_metadata"] = {"model": "kmeans", "n_clusters": 3}
    data.attrs["signal_adaptation"] = {"allowed_clusters": [2]}

    intent = adapter.build_signal_intent(data, 1)

    assert intent is not None
    assert intent["action"] == "BUY"
    assert intent["features"]["cluster_label"] == 2
    assert intent["metadata"]["cluster_metadata"]["model"] == "kmeans"
    assert intent["metadata"]["signal_adaptation"]["allowed_clusters"] == [2]
