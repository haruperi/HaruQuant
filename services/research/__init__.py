"""Edge research and statistical validation toolkit."""

from __future__ import annotations

_EXPORT_MODULES = {
    "BootstrapConfig": "config",
    "DataConfig": "config",
    "EdgeLabConfig": "config",
    "MeanReversionConfig": "config",
    "PermutationConfig": "config",
    "SessionConfig": "config",
    "MarketStructureConfig": "config",
    "TrendPersistenceConfig": "config",
    "CleaningConfig": "data",
    "DataQualityReportModel": "data",
    "EnrichmentConfig": "data",
    "PreparedDataset": "data",
    "CoreMetricProfile": "core_metrics",
    "MetricRegistry": "core_metrics",
    "build_core_metric_profile": "core_metrics",
    "build_default_registry": "core_metrics",
    "run_eds_mean_reversion": "eds_mean_reversion",
    "run_eds_null_baseline": "eds_null_models",
    "run_eds_session": "eds_session",
    "run_eds_trend_persistence": "eds_trend_persistence",
    "MarketStructureProfile": "market_structure",
    "build_market_structure_profile": "market_structure",
    "build_market_structure_research_profile": "market_structure",
    "atr": "features",
    "bb_width": "features",
    "bollinger_bands": "features",
    "forward_returns": "features",
    "hurst_exponent": "features",
    "log_returns": "features",
    "rolling_percentile_rank": "features",
    "rsi": "features",
    "sma": "features",
    "std": "features",
    "zscore": "features",
    "benjamini_hochberg": "null_models",
    "block_bootstrap_ci": "null_models",
    "permutation_test": "null_models",
    "r_space_null": "null_models",
    "random_entry_null": "null_models",
    "generate_multi_symbol_report": "reporting",
    "print_result_summary": "reporting",
    "result_to_markdown": "reporting",
    "save_json": "reporting",
    "save_markdown": "reporting",
    "EdgeResult": "results_schema",
    "EdgeStats": "results_schema",
    "TradeSample": "results_schema",
}

_DATASET_EXPORTS = {
    "DataSource",
    "OHLCVSchema",
    "load_ohlc",
    "prepare_ohlcvs_dataset",
    "resample_ohlc",
    "tag_sessions",
    "validate_data_quality",
}

_ANALYTICS_EXPORTS = {
    "calmar_ratio": ("services.analytics.ratios", "calmar_ratio"),
    "expectancy": ("services.analytics.ratios", "expectancy"),
    "max_drawdown": ("services.analytics.drawdowns", "max_drawdown"),
    "median_mae_mfe": ("services.analytics.metrics", "median_mae_mfe"),
    "profit_factor": ("services.analytics.ratios", "profit_factor"),
    "sharpe_ratio": ("services.analytics.ratios", "sharpe_ratio"),
    "sortino_ratio": ("services.analytics.ratios", "sortino_ratio"),
    "win_rate": ("services.analytics.metrics", "win_rate_fraction"),
}

__all__ = list(_EXPORT_MODULES) + list(_DATASET_EXPORTS) + list(_ANALYTICS_EXPORTS)


def __getattr__(name: str):
    from importlib import import_module

    if name in _DATASET_EXPORTS:
        module = import_module("services.utils.datasets")
        value = getattr(module, name)
    elif name in _ANALYTICS_EXPORTS:
        module_name, attr = _ANALYTICS_EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attr)
    else:
        module_name = _EXPORT_MODULES.get(name)
        if module_name is None:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        module = import_module(f"{__name__}.{module_name}")
        value = getattr(module, name)

    globals()[name] = value
    return value
