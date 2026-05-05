"""Unsupervised modeling helpers for AI trading workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class PcaModelResult:
    """PCA output plus metadata needed for evidence and downstream workflows."""

    components: pd.DataFrame
    loadings: pd.DataFrame
    explained_variance_ratio: tuple[float, ...]
    feature_columns: tuple[str, ...]
    n_components: int
    scaled: bool

    def to_metadata(self) -> dict[str, Any]:
        """Return compact serializable metadata for reports/evidence."""
        return {
            "model": "pca",
            "n_components": self.n_components,
            "feature_columns": list(self.feature_columns),
            "explained_variance_ratio": list(self.explained_variance_ratio),
            "scaled": self.scaled,
        }


@dataclass(frozen=True)
class ClusterModelResult:
    """K-Means output plus metadata needed for regime/factor labeling."""

    labels: pd.Series
    centroids: pd.DataFrame
    inertia: float
    feature_columns: tuple[str, ...]
    n_clusters: int
    random_state: int
    scaled: bool

    def to_metadata(self) -> dict[str, Any]:
        """Return compact serializable metadata for reports/evidence."""
        return {
            "model": "kmeans",
            "n_clusters": self.n_clusters,
            "feature_columns": list(self.feature_columns),
            "inertia": self.inertia,
            "random_state": self.random_state,
            "scaled": self.scaled,
        }


def run_pca(
    data: pd.DataFrame,
    *,
    feature_columns: Sequence[str] | None = None,
    n_components: int = 2,
    scale: bool = True,
    component_prefix: str = "pc",
) -> PcaModelResult:
    """Run PCA on numeric feature columns and return component scores/loadings."""
    features, columns = _prepare_feature_matrix(data, feature_columns)
    if n_components <= 0:
        raise ValueError("n_components must be positive")
    if n_components > min(len(columns), len(features)):
        raise ValueError("n_components cannot exceed feature or row count")

    matrix = _scale_features(features) if scale else features.to_numpy(dtype=float)
    model = PCA(n_components=n_components)
    values = model.fit_transform(matrix)
    component_columns = [f"{component_prefix}_{idx + 1}" for idx in range(n_components)]
    components = pd.DataFrame(values, index=data.index, columns=component_columns)
    loadings = pd.DataFrame(
        model.components_.T,
        index=columns,
        columns=component_columns,
    )
    return PcaModelResult(
        components=components,
        loadings=loadings,
        explained_variance_ratio=tuple(float(v) for v in model.explained_variance_ratio_),
        feature_columns=tuple(columns),
        n_components=n_components,
        scaled=scale,
    )


def cluster_feature_space(
    data: pd.DataFrame,
    *,
    feature_columns: Sequence[str] | None = None,
    n_clusters: int = 3,
    random_state: int = 42,
    scale: bool = True,
    label_name: str = "cluster_label",
) -> ClusterModelResult:
    """Cluster numeric feature rows with deterministic K-Means labels."""
    features, columns = _prepare_feature_matrix(data, feature_columns)
    if n_clusters <= 1:
        raise ValueError("n_clusters must be greater than 1")
    if n_clusters > len(features):
        raise ValueError("n_clusters cannot exceed row count")

    matrix = _scale_features(features) if scale else features.to_numpy(dtype=float)
    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = model.fit_predict(matrix)
    centroids = pd.DataFrame(model.cluster_centers_, columns=columns)

    return ClusterModelResult(
        labels=pd.Series(labels.astype(int), index=data.index, name=label_name),
        centroids=centroids,
        inertia=float(model.inertia_),
        feature_columns=tuple(columns),
        n_clusters=n_clusters,
        random_state=random_state,
        scaled=scale,
    )


def attach_cluster_labels(
    data: pd.DataFrame,
    result: ClusterModelResult,
    *,
    column_name: str | None = None,
) -> pd.DataFrame:
    """Attach cluster labels to a feature frame without mutating the input."""
    output = data.copy()
    name = column_name or result.labels.name or "cluster_label"
    output[name] = result.labels.reindex(data.index).astype("Int64")
    output.attrs["cluster_metadata"] = result.to_metadata()
    return output


def _prepare_feature_matrix(
    data: pd.DataFrame,
    feature_columns: Sequence[str] | None,
) -> tuple[pd.DataFrame, list[str]]:
    if data.empty:
        raise ValueError("data must contain at least one row")

    if feature_columns is None:
        columns = list(data.select_dtypes(include=[np.number]).columns)
    else:
        columns = [str(column) for column in feature_columns]

    if not columns:
        raise ValueError("at least one numeric feature column is required")
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"missing feature columns: {missing}")

    features = data.loc[:, columns].apply(pd.to_numeric, errors="coerce")
    if not features.notna().to_numpy().any():
        raise ValueError("feature matrix contains no numeric values")
    features = features.fillna(features.mean(numeric_only=True)).fillna(0.0)
    return features, columns


def _scale_features(features: pd.DataFrame) -> np.ndarray:
    scaler = StandardScaler()
    return scaler.fit_transform(features.to_numpy(dtype=float))
