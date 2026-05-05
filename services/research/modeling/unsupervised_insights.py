"""Unsupervised investment-data insight helpers.

These helpers turn raw PCA and K-Means outputs into strategy-facing artifacts:
data summaries, factor interpretation, cluster outperformance, and signal
adaptation. They intentionally remain deterministic and side-effect free so
workflow stages can persist the returned payloads as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import pandas as pd

from services.research.modeling.unsupervised import (
    ClusterModelResult,
    PcaModelResult,
    attach_cluster_labels,
    cluster_feature_space,
    run_pca,
)


@dataclass(frozen=True)
class InvestmentDataSummary:
    """Compact EDA summary for investment or feature data."""

    row_count: int
    column_count: int
    start: Any
    end: Any
    numeric_columns: tuple[str, ...]
    missing_by_column: dict[str, int]
    duplicate_index_count: int
    numeric_stats: dict[str, dict[str, float]]
    return_stats: dict[str, float]
    correlation_matrix: dict[str, dict[str, float]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "start": self.start,
            "end": self.end,
            "numeric_columns": list(self.numeric_columns),
            "missing_by_column": self.missing_by_column,
            "duplicate_index_count": self.duplicate_index_count,
            "numeric_stats": self.numeric_stats,
            "return_stats": self.return_stats,
            "correlation_matrix": self.correlation_matrix,
        }


@dataclass(frozen=True)
class PcaRiskFactor:
    """Top loading that explains a PCA component with semantic interpretation."""

    component: str
    feature: str
    loading: float
    abs_loading: float
    direction: str
    explained_variance_ratio: float
    interpretation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "feature": self.feature,
            "loading": self.loading,
            "abs_loading": self.abs_loading,
            "direction": self.direction,
            "explained_variance_ratio": self.explained_variance_ratio,
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True)
class ClusterOutperformance:
    """Forward-return performance of one unsupervised cluster with regime naming."""

    cluster_label: int
    observations: int
    mean_forward_return: float
    hit_rate: float
    outperformance_vs_overall: float
    regime_name: str = "UNKNOWN"
    characteristics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_label": self.cluster_label,
            "observations": self.observations,
            "mean_forward_return": self.mean_forward_return,
            "hit_rate": self.hit_rate,
            "outperformance_vs_overall": self.outperformance_vs_overall,
            "regime_name": self.regime_name,
            "characteristics": list(self.characteristics),
        }


@dataclass(frozen=True)
class SignalAdaptationResult:
    """Result of filtering strategy signals by cluster outperformance."""

    adapted_signals: pd.DataFrame
    allowed_clusters: tuple[int, ...]
    blocked_clusters: tuple[int, ...]
    original_signal_count: int
    adapted_signal_count: int

    def to_metadata(self) -> dict[str, Any]:
        return {
            "allowed_clusters": list(self.allowed_clusters),
            "blocked_clusters": list(self.blocked_clusters),
            "original_signal_count": self.original_signal_count,
            "adapted_signal_count": self.adapted_signal_count,
        }


@dataclass(frozen=True)
class UnsupervisedInsightReport:
    """End-to-end unsupervised report for a trading workflow stage."""

    data_summary: InvestmentDataSummary
    pca: PcaModelResult
    clusters: ClusterModelResult
    labeled_data: pd.DataFrame
    risk_factors: tuple[PcaRiskFactor, ...]
    cluster_outperformance: tuple[ClusterOutperformance, ...]
    signal_adaptation: SignalAdaptationResult | None

    def to_metadata(self) -> dict[str, Any]:
        return {
            "data_summary": self.data_summary.to_dict(),
            "pca": self.pca.to_metadata(),
            "clusters": self.clusters.to_metadata(),
            "risk_factors": [factor.to_dict() for factor in self.risk_factors],
            "cluster_outperformance": [
                cluster.to_dict() for cluster in self.cluster_outperformance
            ],
            "signal_adaptation": (
                self.signal_adaptation.to_metadata()
                if self.signal_adaptation is not None
                else None
            ),
        }


def summarize_investment_data(
    data: pd.DataFrame,
    *,
    price_column: str = "close",
) -> InvestmentDataSummary:
    """Explore investment data and return key descriptive statistics."""
    if data.empty:
        raise ValueError("data must contain at least one row")

    numeric = data.select_dtypes(include="number")
    missing_by_column = {str(column): int(data[column].isna().sum()) for column in data.columns}
    numeric_stats: dict[str, dict[str, float]] = {}

    for column in numeric.columns:
        series = pd.to_numeric(numeric[column], errors="coerce")
        numeric_stats[str(column)] = {
            "mean": _finite_float(series.mean()),
            "std": _finite_float(series.std(ddof=0)),
            "min": _finite_float(series.min()),
            "max": _finite_float(series.max()),
            "skew": _finite_float(series.skew()),
            "kurtosis": _finite_float(series.kurtosis()),
        }

    return_stats: dict[str, float] = {}
    if price_column in data.columns:
        returns = pd.to_numeric(data[price_column], errors="coerce").pct_change().dropna()
        if not returns.empty:
            return_stats = {
                "mean": _finite_float(returns.mean()),
                "std": _finite_float(returns.std(ddof=0)),
                "min": _finite_float(returns.min()),
                "max": _finite_float(returns.max()),
                "skew": _finite_float(returns.skew()),
                "kurtosis": _finite_float(returns.kurtosis()),
                "cumulative_return": _finite_float((1.0 + returns).prod() - 1.0),
            }

    correlation_matrix: dict[str, dict[str, float]] = {}
    if len(numeric.columns) > 1:
        corr = numeric.corr().fillna(0.0)
        for col in corr.columns:
            correlation_matrix[str(col)] = {
                str(other): float(val) for other, val in corr[col].items()
            }

    return InvestmentDataSummary(
        row_count=int(len(data)),
        column_count=int(len(data.columns)),
        start=data.index[0],
        end=data.index[-1],
        numeric_columns=tuple(str(column) for column in numeric.columns),
        missing_by_column=missing_by_column,
        duplicate_index_count=int(data.index.duplicated().sum()),
        numeric_stats=numeric_stats,
        return_stats=return_stats,
        correlation_matrix=correlation_matrix,
    )


def identify_pca_risk_factors(
    pca_result: PcaModelResult,
    *,
    top_n_per_component: int = 3,
) -> tuple[PcaRiskFactor, ...]:
    """Extract the largest PCA loadings as interpretable risk factors."""
    if top_n_per_component <= 0:
        raise ValueError("top_n_per_component must be positive")

    factors: list[PcaRiskFactor] = []
    for component_index, component in enumerate(pca_result.loadings.columns):
        explained = pca_result.explained_variance_ratio[component_index]
        top_loadings = (
            pca_result.loadings[component]
            .dropna()
            .abs()
            .sort_values(ascending=False)
            .head(top_n_per_component)
            .index
        )
        for feature in top_loadings:
            loading = float(pca_result.loadings.loc[feature, component])
            factors.append(
                PcaRiskFactor(
                    component=str(component),
                    feature=str(feature),
                    loading=loading,
                    abs_loading=abs(loading),
                    direction="positive" if loading >= 0 else "negative",
                    explained_variance_ratio=float(explained),
                    interpretation=_interpret_pca_loading(str(feature), loading),
                )
            )

    return tuple(factors)


def _interpret_pca_loading(feature: str, loading: float) -> str:
    """Heuristic mapping of feature loadings to trading intuition."""
    f = feature.lower()
    direction = "Positive" if loading >= 0 else "Negative"
    if "volatility" in f or "range" in f:
        return f"{direction} Volatility Factor"
    if "momentum" in f or "return" in f:
        return f"{direction} Trend/Momentum Factor"
    if "ema_spread" in f:
        return f"{direction} Trend Strength/Bias Factor"
    return f"{direction} {feature} Loading"


def compute_forward_returns(
    data: pd.DataFrame,
    *,
    price_column: str = "close",
    horizon: int = 1,
    output_column: str = "forward_return",
) -> pd.Series:
    """Compute horizon-aligned forward returns from a price column."""
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if price_column not in data.columns:
        raise ValueError(f"missing price column: {price_column}")

    prices = pd.to_numeric(data[price_column], errors="coerce")
    forward = prices.shift(-horizon) / prices - 1.0
    return forward.rename(output_column)


def analyze_cluster_outperformance(
    data: pd.DataFrame,
    labels: pd.Series,
    *,
    price_column: str = "close",
    forward_returns: pd.Series | None = None,
    horizon: int = 1,
    feature_columns: Sequence[str] = (),
) -> tuple[ClusterOutperformance, ...]:
    """Score each cluster by future returns and assign semantic regime names."""
    returns = (
        forward_returns.rename("forward_return")
        if forward_returns is not None
        else compute_forward_returns(data, price_column=price_column, horizon=horizon)
    )
    frame = pd.DataFrame(
        {
            "cluster_label": labels.reindex(data.index),
            "forward_return": returns.reindex(data.index),
        }
    )
    # Add features for characteristic analysis
    for col in feature_columns:
        if col in data.columns:
            frame[col] = data[col]

    frame = frame.dropna(subset=["cluster_label", "forward_return"])
    if frame.empty:
        return tuple()

    overall_mean = float(frame["forward_return"].mean())
    feature_means = frame[list(feature_columns)].mean() if feature_columns else pd.Series()

    results: list[ClusterOutperformance] = []
    for label, group in frame.groupby("cluster_label", sort=True):
        cluster_return = float(group["forward_return"].mean())
        
        characteristics: list[str] = []
        if not feature_means.empty:
            group_means = group[list(feature_columns)].mean()
            for col in feature_columns:
                diff = group_means[col] - feature_means[col]
                std = frame[col].std()
                if abs(diff) > 0.5 * std: # Significant deviation
                    adj = "High" if diff > 0 else "Low"
                    characteristics.append(f"{adj} {col.replace('_', ' ').title()}")
        
        regime_name = _name_regime(characteristics, cluster_return > overall_mean)

        results.append(
            ClusterOutperformance(
                cluster_label=int(label),
                observations=int(len(group)),
                mean_forward_return=cluster_return,
                hit_rate=float((group["forward_return"] > 0).mean()),
                outperformance_vs_overall=cluster_return - overall_mean,
                regime_name=regime_name,
                characteristics=tuple(characteristics),
            )
        )
    return tuple(results)


def _name_regime(characteristics: list[str], is_outperforming: bool) -> str:
    """Heuristic mapping of cluster characteristics to semantic regime names."""
    chars_lower = [c.lower() for c in characteristics]
    
    is_high_vol = any("high rolling volatility" in c or "high range pct" in c for c in chars_lower)
    is_low_vol = any("low rolling volatility" in c or "low range pct" in c for c in chars_lower)
    is_high_mom = any("high momentum" in c or "high return_1" in c for c in chars_lower)
    is_low_mom = any("low momentum" in c or "low return_1" in c for c in chars_lower)

    if is_high_vol and is_high_mom:
        return "Explosive Trending"
    if is_low_vol and is_high_mom:
        return "Stable Accumulation"
    if is_high_vol and not is_high_mom:
        return "Volatile Mean-Reverting"
    if is_low_vol and not is_high_mom:
        return "Quiet Consolidation"
    if is_high_mom:
        return "Strong Trend"
    if is_low_mom:
        return "Weak/Bearish"
    
    return "Outperforming" if is_outperforming else "Underperforming"


def adapt_signals_by_cluster(
    signal_frame: pd.DataFrame,
    cluster_outperformance: Sequence[ClusterOutperformance],
    *,
    label_column: str = "cluster_label",
    signal_column: str = "entry_signal",
    min_observations: int = 1,
) -> SignalAdaptationResult:
    """Suppress strategy entries in clusters with weak forward returns."""
    if label_column not in signal_frame.columns:
        raise ValueError(f"missing label column: {label_column}")
    if signal_column not in signal_frame.columns:
        raise ValueError(f"missing signal column: {signal_column}")

    allowed_clusters = tuple(
        sorted(
            cluster.cluster_label
            for cluster in cluster_outperformance
            if cluster.observations >= min_observations
            and cluster.outperformance_vs_overall > 0
        )
    )
    all_clusters = tuple(sorted(cluster.cluster_label for cluster in cluster_outperformance))
    blocked_clusters = tuple(cluster for cluster in all_clusters if cluster not in allowed_clusters)

    adapted = signal_frame.copy()
    original_signal_count = int((pd.to_numeric(adapted[signal_column], errors="coerce") != 0).sum())
    blocked_mask = ~adapted[label_column].isin(allowed_clusters)
    adapted.loc[blocked_mask, signal_column] = 0
    adapted_signal_count = int((pd.to_numeric(adapted[signal_column], errors="coerce") != 0).sum())
    adapted.attrs["signal_adaptation"] = {
        "rule": "allow positive outperformance clusters only",
        "min_observations": min_observations,
        "allowed_clusters": list(allowed_clusters),
        "blocked_clusters": list(blocked_clusters),
    }

    return SignalAdaptationResult(
        adapted_signals=adapted,
        allowed_clusters=allowed_clusters,
        blocked_clusters=blocked_clusters,
        original_signal_count=original_signal_count,
        adapted_signal_count=adapted_signal_count,
    )


def build_unsupervised_insight_report(
    data: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    price_column: str = "close",
    n_components: int = 2,
    n_clusters: int = 3,
    random_state: int = 42,
    forward_return_horizon: int = 1,
    label_column: str = "cluster_label",
    signal_frame: pd.DataFrame | None = None,
    signal_column: str = "entry_signal",
    scale_features: bool = True,
) -> UnsupervisedInsightReport:
    """Build a complete unsupervised insight report for trading workflows."""
    data_summary = summarize_investment_data(data, price_column=price_column)
    pca = run_pca(
        data,
        feature_columns=feature_columns,
        n_components=n_components,
        scale=scale_features,
    )
    clusters = cluster_feature_space(
        data,
        feature_columns=feature_columns,
        n_clusters=n_clusters,
        random_state=random_state,
        label_name=label_column,
        scale=scale_features,
    )
    labeled_data = attach_cluster_labels(data, clusters, column_name=label_column)
    risk_factors = identify_pca_risk_factors(pca)
    cluster_outperformance = analyze_cluster_outperformance(
        labeled_data,
        clusters.labels,
        price_column=price_column,
        horizon=forward_return_horizon,
        feature_columns=feature_columns,
    )

    signal_adaptation = None
    if signal_frame is not None:
        signals = signal_frame.copy()
        if label_column not in signals.columns:
            signals[label_column] = clusters.labels.reindex(signals.index).astype("Int64")
        signal_adaptation = adapt_signals_by_cluster(
            signals,
            cluster_outperformance,
            label_column=label_column,
            signal_column=signal_column,
        )

    return UnsupervisedInsightReport(
        data_summary=data_summary,
        pca=pca,
        clusters=clusters,
        labeled_data=labeled_data,
        risk_factors=risk_factors,
        cluster_outperformance=cluster_outperformance,
        signal_adaptation=signal_adaptation,
    )


def _finite_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)
