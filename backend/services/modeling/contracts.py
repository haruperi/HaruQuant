"""Contracts for reusable unsupervised research services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from backend.services.modeling.unsupervised_insights import UnsupervisedInsightReport


@dataclass(frozen=True)
class UnsupervisedResearchConfig:
    """Stable configuration contract for unsupervised analysis."""

    feature_set: str = "market_regime_core"
    fast_period: int = 20
    slow_period: int = 50
    volatility_window: int = 20
    momentum_window: int = 5
    min_feature_periods: int = 3
    include_ema_spread: bool = True
    n_components: int = 2
    n_clusters: int = 3
    random_state: int = 42
    forward_return_horizon: int = 1
    label_column: str = "cluster_label"
    price_column: str = "close"
    signal_column: str = "entry_signal"
    min_rows: int = 25
    min_cluster_observations: int = 3
    scale_features: bool = True
    enable_signal_adaptation: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_set": self.feature_set,
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "volatility_window": self.volatility_window,
            "momentum_window": self.momentum_window,
            "min_feature_periods": self.min_feature_periods,
            "include_ema_spread": self.include_ema_spread,
            "n_components": self.n_components,
            "n_clusters": self.n_clusters,
            "random_state": self.random_state,
            "forward_return_horizon": self.forward_return_horizon,
            "label_column": self.label_column,
            "price_column": self.price_column,
            "signal_column": self.signal_column,
            "min_rows": self.min_rows,
            "min_cluster_observations": self.min_cluster_observations,
            "scale_features": self.scale_features,
            "enable_signal_adaptation": self.enable_signal_adaptation,
        }


@dataclass(frozen=True)
class UnsupervisedResearchRequest:
    """Input contract for reusable unsupervised analysis."""

    data: pd.DataFrame
    signal_frame: pd.DataFrame | None = None
    config: UnsupervisedResearchConfig = field(default_factory=UnsupervisedResearchConfig)


@dataclass(frozen=True)
class UnsupervisedResearchResult:
    """Stable output contract for reusable unsupervised analysis."""

    status: str
    config: UnsupervisedResearchConfig
    report: UnsupervisedInsightReport | None = None
    feature_frame: pd.DataFrame | None = None
    feature_columns: tuple[str, ...] = ()
    feature_metadata: dict[str, Any] = field(default_factory=dict)
    strategy_context: dict[str, Any] = field(default_factory=dict)
    risk_context: dict[str, Any] = field(default_factory=dict)
    guardrails: tuple[str, ...] = ()
    reason: str | None = None

    def to_metadata(self) -> dict[str, Any]:
        payload = {
            "status": self.status,
            "config": self.config.to_dict(),
            "feature_columns": list(self.feature_columns),
            "feature_metadata": self.feature_metadata,
            "strategy_context": self.strategy_context,
            "risk_context": self.risk_context,
            "guardrails": list(self.guardrails),
            "reason": self.reason,
        }
        if self.report is not None:
            payload["report"] = self.report.to_metadata()
        return payload


__all__ = [
    "UnsupervisedResearchConfig",
    "UnsupervisedResearchRequest",
    "UnsupervisedResearchResult",
]
