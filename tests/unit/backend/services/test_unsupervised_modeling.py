from __future__ import annotations

import pandas as pd

from backend.services.modeling.unsupervised import (
    attach_cluster_labels,
    cluster_feature_space,
    run_pca,
)


def _feature_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=8, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "return_1": [-0.04, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.04],
            "volatility": [0.04, 0.035, 0.03, 0.025, 0.02, 0.018, 0.015, 0.012],
            "momentum": [-0.05, -0.04, -0.03, -0.02, 0.02, 0.03, 0.04, 0.05],
            "symbol": ["EURUSD"] * 8,
        },
        index=index,
    )


def test_run_pca_returns_components_loadings_and_metadata() -> None:
    frame = _feature_frame()

    result = run_pca(
        frame,
        feature_columns=["return_1", "volatility", "momentum"],
        n_components=2,
    )

    assert list(result.components.columns) == ["pc_1", "pc_2"]
    assert result.components.index.equals(frame.index)
    assert list(result.loadings.index) == ["return_1", "volatility", "momentum"]
    assert result.n_components == 2
    assert len(result.explained_variance_ratio) == 2
    assert result.to_metadata()["model"] == "pca"


def test_cluster_feature_space_is_deterministic_with_fixed_seed() -> None:
    frame = _feature_frame()

    first = cluster_feature_space(
        frame,
        feature_columns=["return_1", "volatility", "momentum"],
        n_clusters=2,
        random_state=7,
    )
    second = cluster_feature_space(
        frame,
        feature_columns=["return_1", "volatility", "momentum"],
        n_clusters=2,
        random_state=7,
    )

    assert first.labels.tolist() == second.labels.tolist()
    assert first.n_clusters == 2
    assert first.centroids.shape == (2, 3)
    assert first.to_metadata()["random_state"] == 7


def test_attach_cluster_labels_preserves_input_and_adds_metadata() -> None:
    frame = _feature_frame()
    result = cluster_feature_space(
        frame,
        feature_columns=["return_1", "volatility", "momentum"],
        n_clusters=2,
        random_state=42,
        label_name="regime_label",
    )

    labeled = attach_cluster_labels(frame, result)

    assert "regime_label" not in frame.columns
    assert "regime_label" in labeled.columns
    assert labeled["regime_label"].isna().sum() == 0
    assert labeled.attrs["cluster_metadata"]["model"] == "kmeans"


def test_unsupervised_modeling_rejects_missing_feature_columns() -> None:
    frame = _feature_frame()

    try:
        run_pca(frame, feature_columns=["missing"], n_components=1)
    except ValueError as exc:
        assert "missing feature columns" in str(exc)
    else:
        raise AssertionError("missing feature column should fail")


def test_unsupervised_modeling_rejects_too_many_clusters() -> None:
    frame = _feature_frame()

    try:
        cluster_feature_space(frame, feature_columns=["return_1"], n_clusters=99)
    except ValueError as exc:
        assert "n_clusters" in str(exc)
    else:
        raise AssertionError("too many clusters should fail")
