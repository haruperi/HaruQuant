"""
Edge Lab: Symbol-specific edge discovery and statistical validation toolkit.

This module provides a comprehensive framework for discovering trading edges
and validating them statistically before turning them into production strategies.

Edge Discovery Strategies (EDS):
- EDS-0: Null Models / Baseline (establish what "no edge" looks like)
- EDS-1: Mean Reversion Detector (compression + z-score fade)
- EDS-2: Trend Persistence Detector (high-ATR breakout follow-through)
- EDS-3: Session Edge Detector (time-of-day alpha)

Statistical Tools:
- Block bootstrap confidence intervals (autocorrelation-aware)
- Permutation / randomization tests
- Multiple hypothesis correction (Benjamini-Hochberg FDR)
- Null model distributions
"""

from .config import (
    BootstrapConfig,
    DataConfig,
    EdgeLabConfig,
    MeanReversionConfig,
    PermutationConfig,
    SessionConfig,
    MarketStructureConfig,
    TrendPersistenceConfig,
)
from .datasets import (
    DataSource,
    OHLCVSchema,
    load_ohlc,
    prepare_ohlcvs_dataset,
    resample_ohlc,
    tag_sessions,
    validate_data_quality,
)
from .data import (
    CleaningConfig,
    DataQualityReportModel,
    EnrichmentConfig,
    PreparedDataset,
)
from .core_metrics import (
    CoreMetricProfile,
    MetricRegistry,
    build_core_metric_profile,
    build_default_registry,
)
from .eds_mean_reversion import run_eds_mean_reversion
from .eds_null_models import run_eds_null_baseline
from .eds_session import run_eds_session
from .eds_trend_persistence import run_eds_trend_persistence
from .market_structure import (
    MarketStructureProfile,
    build_market_structure_profile,
    build_market_structure_research_profile,
)
from .features import (
    atr,
    bb_width,
    bollinger_bands,
    forward_returns,
    hurst_exponent,
    log_returns,
    rolling_percentile_rank,
    rsi,
    sma,
    std,
    zscore,
)
from apps.finance.drawdowns import max_drawdown
from apps.finance.metrics import median_mae_mfe, win_rate_fraction as win_rate
from apps.finance.ratios import (
    calmar_ratio,
    expectancy,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
)
from .null_models import (
    benjamini_hochberg,
    block_bootstrap_ci,
    permutation_test,
    r_space_null,
    random_entry_null,
)
from .reporting import (
    generate_multi_symbol_report,
    print_result_summary,
    result_to_markdown,
    save_json,
    save_markdown,
)
from .results_schema import EdgeResult, EdgeStats, TradeSample

__all__ = [
    # Config
    "BootstrapConfig",
    "DataConfig",
    "EdgeLabConfig",
    "MeanReversionConfig",
    "PermutationConfig",
    "SessionConfig",
    "MarketStructureConfig",
    "TrendPersistenceConfig",
    # Datasets
    "DataSource",
    "OHLCVSchema",
    "load_ohlc",
    "prepare_ohlcvs_dataset",
    "resample_ohlc",
    "tag_sessions",
    "validate_data_quality",
    "CleaningConfig",
    "EnrichmentConfig",
    "DataQualityReportModel",
    "PreparedDataset",
    "CoreMetricProfile",
    "MetricRegistry",
    "build_core_metric_profile",
    "build_default_registry",
    # EDS Runners
    "run_eds_mean_reversion",
    "run_eds_trend_persistence",
    "run_eds_null_baseline",
    "run_eds_session",
    "MarketStructureProfile",
    "build_market_structure_profile",
    "build_market_structure_research_profile",
    # Features
    "atr",
    "bb_width",
    "bollinger_bands",
    "forward_returns",
    "hurst_exponent",
    "log_returns",
    "rolling_percentile_rank",
    "rsi",
    "sma",
    "std",
    "zscore",
    # Metrics
    "expectancy",
    "median_mae_mfe",
    "profit_factor",
    "sharpe_ratio",
    "win_rate",
    "max_drawdown",
    "sortino_ratio",
    "calmar_ratio",
    # Null Models
    "benjamini_hochberg",
    "block_bootstrap_ci",
    "permutation_test",
    "random_entry_null",
    "r_space_null",
    # Reporting
    "generate_multi_symbol_report",
    "print_result_summary",
    "result_to_markdown",
    "save_json",
    "save_markdown",
    # Results
    "EdgeResult",
    "EdgeStats",
    "TradeSample",
]
