"""Modeling services for AI trading workflows."""

from backend.services.modeling.contracts import (
    UnsupervisedResearchConfig,
    UnsupervisedResearchRequest,
    UnsupervisedResearchResult,
)
from backend.services.modeling.feature_sets import (
    FeatureSetFrame,
    build_market_regime_feature_frame,
)
from backend.services.modeling.service import UnsupervisedResearchService
from backend.services.modeling.unsupervised import (
    ClusterModelResult,
    PcaModelResult,
    attach_cluster_labels,
    cluster_feature_space,
    run_pca,
)
from backend.services.modeling.unsupervised_insights import (
    ClusterOutperformance,
    InvestmentDataSummary,
    PcaRiskFactor,
    SignalAdaptationResult,
    UnsupervisedInsightReport,
    adapt_signals_by_cluster,
    analyze_cluster_outperformance,
    build_unsupervised_insight_report,
    compute_forward_returns,
    identify_pca_risk_factors,
    summarize_investment_data,
)

__all__ = [
    "ClusterModelResult",
    "ClusterOutperformance",
    "InvestmentDataSummary",
    "PcaModelResult",
    "PcaRiskFactor",
    "SignalAdaptationResult",
    "FeatureSetFrame",
    "UnsupervisedResearchConfig",
    "UnsupervisedResearchRequest",
    "UnsupervisedResearchResult",
    "UnsupervisedResearchService",
    "UnsupervisedInsightReport",
    "attach_cluster_labels",
    "adapt_signals_by_cluster",
    "analyze_cluster_outperformance",
    "build_unsupervised_insight_report",
    "build_market_regime_feature_frame",
    "cluster_feature_space",
    "compute_forward_returns",
    "identify_pca_risk_factors",
    "run_pca",
    "summarize_investment_data",
]
