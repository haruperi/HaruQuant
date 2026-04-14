from __future__ import annotations

import pandas as pd

from backend.services.modeling.unsupervised import run_pca
from backend.services.modeling.unsupervised_insights import (
    adapt_signals_by_cluster,
    analyze_cluster_outperformance,
    build_unsupervised_insight_report,
    identify_pca_risk_factors,
    summarize_investment_data,
)


def _investment_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=8, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "close": [100.0, 101.0, 102.0, 103.0, 99.0, 98.0, 97.0, 96.0],
            "return_1": [0.00, 0.01, 0.01, 0.01, -0.04, -0.01, -0.01, -0.01],
            "volatility": [0.01, 0.01, 0.012, 0.011, 0.05, 0.045, 0.04, 0.038],
            "momentum": [0.00, 0.01, 0.02, 0.03, -0.01, -0.02, -0.03, -0.04],
        },
        index=index,
    )


def test_summarize_investment_data_explores_core_statistics() -> None:
    frame = _investment_frame()

    summary = summarize_investment_data(frame)

    assert summary.row_count == 8
    assert summary.column_count == 4
    assert summary.numeric_columns == ("close", "return_1", "volatility", "momentum")
    assert summary.missing_by_column["close"] == 0
    assert summary.duplicate_index_count == 0
    assert summary.numeric_stats["close"]["min"] == 96.0
    assert summary.return_stats["cumulative_return"] < 0


def test_identify_pca_risk_factors_reports_dominant_loadings() -> None:
    frame = _investment_frame()
    pca = run_pca(
        frame,
        feature_columns=["return_1", "volatility", "momentum"],
        n_components=2,
    )

    factors = identify_pca_risk_factors(pca, top_n_per_component=1)

    assert len(factors) == 2
    assert factors[0].component == "pc_1"
    assert factors[0].feature in {"return_1", "volatility", "momentum"}
    assert factors[0].abs_loading > 0
    assert factors[0].direction in {"positive", "negative"}


def test_analyze_cluster_outperformance_scores_regimes() -> None:
    frame = _investment_frame()
    labels = pd.Series([0, 0, 0, 0, 1, 1, 1, 1], index=frame.index)

    performance = analyze_cluster_outperformance(frame, labels)
    by_cluster = {item.cluster_label: item for item in performance}

    assert by_cluster[0].observations == 4
    assert by_cluster[0].mean_forward_return > by_cluster[1].mean_forward_return
    assert by_cluster[0].outperformance_vs_overall > 0
    assert by_cluster[1].outperformance_vs_overall < 0


def test_adapt_signals_by_cluster_blocks_underperforming_regimes() -> None:
    frame = pd.DataFrame(
        {
            "cluster_label": [0, 0, 1, 1],
            "entry_signal": [1, -1, 1, -1],
        }
    )
    performance = analyze_cluster_outperformance(
        _investment_frame(),
        pd.Series([0, 0, 0, 0, 1, 1, 1, 1], index=_investment_frame().index),
    )

    result = adapt_signals_by_cluster(frame, performance)

    assert result.allowed_clusters == (0,)
    assert result.blocked_clusters == (1,)
    assert result.original_signal_count == 4
    assert result.adapted_signal_count == 2
    assert result.adapted_signals.loc[2, "entry_signal"] == 0
    assert result.adapted_signals.attrs["signal_adaptation"]["allowed_clusters"] == [0]


def test_build_unsupervised_insight_report_covers_stats_factors_and_adaptation() -> None:
    frame = _investment_frame()
    signals = pd.DataFrame({"entry_signal": [1] * len(frame)}, index=frame.index)

    report = build_unsupervised_insight_report(
        frame,
        feature_columns=["return_1", "volatility", "momentum"],
        n_components=2,
        n_clusters=2,
        random_state=7,
        signal_frame=signals,
    )

    metadata = report.to_metadata()

    assert "cluster_label" in report.labeled_data.columns
    assert len(report.risk_factors) >= 2
    assert len(report.cluster_outperformance) == 2
    assert report.signal_adaptation is not None
    assert report.signal_adaptation.adapted_signal_count <= len(frame)
    assert metadata["pca"]["model"] == "pca"
    assert metadata["clusters"]["model"] == "kmeans"
