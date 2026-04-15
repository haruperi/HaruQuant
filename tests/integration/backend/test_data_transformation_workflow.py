from __future__ import annotations

import pandas as pd

from backend.orchestration.workflow.steps_data_transformation import (
    WorkflowContext,
    step_run_unsupervised_research,
)


def _signaled_frame(rows: int = 80) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=rows, freq="h", tz="UTC")
    closes = []
    for idx in range(rows):
        regime_offset = -0.002 * idx if idx >= rows // 2 else 0.003 * idx
        closes.append(1.10 + regime_offset + (0.0005 if idx % 9 == 0 else 0.0))

    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [close + 0.001 for close in closes],
            "low": [close - 0.001 for close in closes],
            "close": closes,
            "volume": [100 + idx for idx in range(rows)],
            "ema_20": pd.Series(closes, index=index).ewm(span=20, adjust=False).mean(),
            "ema_50": pd.Series(closes, index=index).ewm(span=50, adjust=False).mean(),
            "entry_signal": [1 if idx % 4 == 0 else 0 for idx in range(rows)],
            "exit_signal": [1 if idx % 13 == 0 else 0 for idx in range(rows)],
            "price": closes,
        },
        index=index,
    )
    return frame


def test_unsupervised_research_step_returns_serializable_metadata() -> None:
    ctx = WorkflowContext(signaled=_signaled_frame())

    result = step_run_unsupervised_research(ctx, n_components=2, n_clusters=3)

    assert result["status"] == "COMPLETED"
    assert result["rows_analyzed"] > 0
    assert result["pca"]["model"] == "pca"
    assert result["clusters"]["model"] == "kmeans"
    assert result["clusters"]["n_clusters"] == 3
    assert result["risk_factors"]
    assert result["cluster_outperformance"]
    assert "unsupervised_report" in ctx
    assert "labeled_feature_frame" in ctx


def test_unsupervised_research_step_builds_non_expansive_signal_filter() -> None:
    ctx = WorkflowContext(signaled=_signaled_frame())

    result = step_run_unsupervised_research(ctx, n_components=2, n_clusters=3)

    adaptation = result["signal_adaptation"]
    assert adaptation is not None
    assert adaptation["adapted_signal_count"] <= adaptation["original_signal_count"]
    assert "adapted_signaled" in ctx


def test_unsupervised_research_step_skips_when_sample_is_too_small() -> None:
    ctx = WorkflowContext(signaled=_signaled_frame(rows=5))

    result = step_run_unsupervised_research(ctx, n_components=2, n_clusters=3)

    assert result["status"] == "SKIPPED"
    assert "insufficient rows" in result["reason"]
