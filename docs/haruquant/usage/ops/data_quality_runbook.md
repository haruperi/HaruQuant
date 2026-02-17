# Data Quality Runbook (IP-10)

## Scope

This runbook covers detection and remediation flagging for:
- missing intervals
- duplicate timestamps
- out-of-order timestamps
- price sanity issues
- spikes/anomalies
- zero-volume bars
- spread widening / negative spread anomalies

Implementation module:
- `apps/utils/data_validator.py`

## Quick Start

```python
import pandas as pd
from apps.utils.data_validator import DataValidator

df = pd.read_parquet("your_market_data.parquet")
validator = DataValidator()

results = validator.validate(
    df,
    checks=[
        "monotonic_timestamps",
        "normalized_schema",
        "price_sanity",
        "gaps",
        "spikes",
        "missing_timestamps",
        "zero_volume",
        "duplicates",
        "spread",
    ],
    expected_frequency="1h",
)
```

## What To Read First

- `results["summary"]["is_valid"]`
- `results["summary"]["quality_score"]`
- `results["summary"]["remediation"]`

`results["summary"]["remediation"]` includes:
- `severity_counts`
- `actions`
- `needs_immediate_action`

## Remediation Mapping

Each issue in `results["issues_found"]` is annotated with:
- `severity`: `critical|high|medium|low`
- `remediation_action`
- `remediation_required`

Typical actions:
- `normalize_schema`
- `sort_by_timestamp`
- `deduplicate_timestamps_keep_first`
- `backfill_or_drop_missing_intervals`
- `review_or_filter_outliers`
- `flag_or_drop_zero_volume_bars`
- `drop_invalid_ohlc_rows`
- `drop_negative_spread_rows`
- `flag_wide_spread_regime`

## Export Report

```python
validator.export_report(
    "artifacts/evidence/data_quality/latest_report.json",
    results=results,
    format="json",
)
```
