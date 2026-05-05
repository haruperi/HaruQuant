"""Reusable unsupervised research service for strategy and optimization flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from services.research.modeling.contracts import (
    UnsupervisedResearchConfig,
    UnsupervisedResearchRequest,
    UnsupervisedResearchResult,
)
from services.research.modeling.feature_sets import build_market_regime_feature_frame
from services.research.modeling.unsupervised_insights import (
    UnsupervisedInsightReport,
    build_unsupervised_insight_report,
)


@dataclass(frozen=True)
class UnsupervisedResearchService:
    """Single service boundary for unsupervised analysis workflows."""

    def analyze(
        self,
        request: UnsupervisedResearchRequest,
    ) -> UnsupervisedResearchResult:
        config = request.config
        feature_set = build_market_regime_feature_frame(
            request.data,
            fast_period=config.fast_period,
            slow_period=config.slow_period,
            volatility_window=config.volatility_window,
            momentum_window=config.momentum_window,
            min_periods=config.min_feature_periods,
            include_ema_spread=config.include_ema_spread,
            price_column=config.price_column,
        )
        feature_frame = feature_set.frame
        feature_columns = feature_set.feature_columns
        min_rows = max(config.min_rows, config.n_components, config.n_clusters)
        if len(feature_frame) < min_rows or len(feature_columns) < config.n_components:
            return UnsupervisedResearchResult(
                status="SKIPPED",
                config=config,
                feature_frame=feature_frame,
                feature_columns=feature_columns,
                feature_metadata=feature_set.to_metadata(),
                guardrails=self._build_guardrails(config),
                reason="insufficient rows or feature columns for PCA/K-Means",
            )

        aligned_signals = None
        if config.enable_signal_adaptation and request.signal_frame is not None:
            aligned_signals = request.signal_frame.reindex(feature_frame.index).copy()

        report = build_unsupervised_insight_report(
            feature_frame,
            feature_columns=feature_columns,
            price_column=config.price_column,
            n_components=config.n_components,
            n_clusters=config.n_clusters,
            random_state=config.random_state,
            forward_return_horizon=config.forward_return_horizon,
            label_column=config.label_column,
            signal_frame=aligned_signals,
            signal_column=config.signal_column,
            scale_features=config.scale_features,
        )
        strategy_context = self._build_strategy_context(report, config)
        risk_context = self._build_risk_context(report, config)
        return UnsupervisedResearchResult(
            status="COMPLETED",
            config=config,
            report=report,
            feature_frame=feature_frame,
            feature_columns=feature_columns,
            feature_metadata=feature_set.to_metadata(),
            strategy_context=strategy_context,
            risk_context=risk_context,
            guardrails=self._build_guardrails(config),
        )

    def analyze_frame(
        self,
        data: pd.DataFrame,
        *,
        signal_frame: pd.DataFrame | None = None,
        config: UnsupervisedResearchConfig | None = None,
    ) -> UnsupervisedResearchResult:
        return self.analyze(
            UnsupervisedResearchRequest(
                data=data,
                signal_frame=signal_frame,
                config=config or UnsupervisedResearchConfig(),
            )
        )

    @staticmethod
    def _build_guardrails(config: UnsupervisedResearchConfig) -> tuple[str, ...]:
        return (
            "standardize_features_before_pca_and_clustering" if config.scale_features else "raw_features_without_standardization",
            "exclude_forward_returns_from_feature_space",
            "avoid_raw_price_as_direct_cluster_feature",
            "require_minimum_sample_size_before_training",
            "keep_signal_adaptation_advisory_not_autonomous_execution",
        )

    @staticmethod
    def _build_strategy_context(
        report: UnsupervisedInsightReport,
        config: UnsupervisedResearchConfig,
    ) -> dict[str, Any]:
        adaptation = report.signal_adaptation
        return {
            "label_column": config.label_column,
            "cluster_count": report.clusters.n_clusters,
            "allowed_clusters": list(adaptation.allowed_clusters) if adaptation is not None else [],
            "blocked_clusters": list(adaptation.blocked_clusters) if adaptation is not None else [],
            "adaptation_enabled": adaptation is not None,
            "adaptation_rule": "positive_outperformance_clusters_only" if adaptation is not None else "none",
        }

    @staticmethod
    def _build_risk_context(
        report: UnsupervisedInsightReport,
        config: UnsupervisedResearchConfig,
    ) -> dict[str, Any]:
        outperformance = list(report.cluster_outperformance)
        top_cluster = max(outperformance, key=lambda item: item.outperformance_vs_overall, default=None)
        weakest_cluster = min(outperformance, key=lambda item: item.outperformance_vs_overall, default=None)
        top_factor = report.risk_factors[0] if report.risk_factors else None
        regime_name = "FAVORABLE" if top_cluster and top_cluster.outperformance_vs_overall > 0 else "NEUTRAL"
        confidence = float(report.pca.explained_variance_ratio[0]) if report.pca.explained_variance_ratio else 0.0
        payload = {
            "regime_name": regime_name,
            "regime_confidence": confidence,
            "unsupervised_label_column": config.label_column,
            "top_outperforming_cluster": (
                {
                    "cluster_label": top_cluster.cluster_label,
                    "outperformance_vs_overall": top_cluster.outperformance_vs_overall,
                    "observations": top_cluster.observations,
                }
                if top_cluster is not None
                else None
            ),
            "weakest_cluster": (
                {
                    "cluster_label": weakest_cluster.cluster_label,
                    "outperformance_vs_overall": weakest_cluster.outperformance_vs_overall,
                    "observations": weakest_cluster.observations,
                }
                if weakest_cluster is not None
                else None
            ),
            "top_pca_factor": (
                {
                    "component": top_factor.component,
                    "feature": top_factor.feature,
                    "loading": top_factor.loading,
                    "explained_variance_ratio": top_factor.explained_variance_ratio,
                }
                if top_factor is not None
                else None
            ),
        }
        return payload


__all__ = [
    "UnsupervisedResearchService",
]
