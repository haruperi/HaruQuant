# Edge Lab

Edge Lab is HaruQuant's pair-intelligence and symbol-research subsystem.

Its job is to answer, before strategy design:

1. What kind of market character does this symbol have?
2. Is that character stable, tradeable, and strong enough to matter?
3. Which strategy styles fit it best?

The subsystem is now dataset-first, progressive, snapshot-aware, and automation-ready.

## Progressive Flow

The main Edge Lab flow is intentionally sequential:

1. `Data`
   - load one OHLCVS dataset
   - validate, clean, enrich, and cache it for the current session
2. `Core Metric`
   - build a descriptive, cost-aware profile from the prepared dataset
3. `Seasonality`
   - map hourly, session, weekday, and monthly behavior
4. `Market Structure`
   - classify trend, reversion, chop, breakout quality, regime behavior, and deeper structure
5. `Scorecard`
   - convert the earlier outputs into decision-support scores and strategy-fit guidance

Later tabs depend on prior outputs rather than rebuilding everything independently.

## Main Capability Areas

- shared OHLCVS preparation pipeline
- EDS studies:
  - `EDS-0` null / baseline
  - `EDS-1` mean reversion
  - `EDS-2` trend persistence
  - `EDS-3` session edge
- `Core Metric` descriptive profile
- `Seasonality` time-based opportunity mapping
- `Market Structure` unified trend / reversion / range / chop engine
- `Scorecard` explainable decision-support layer
- snapshot storage, report export, pair comparison
- automation, batch execution, scheduled refresh
- validation, calibration, stability, robustness, and acceptance testing

## Dataset Pipeline

Canonical preparation entrypoint:

- `apps/edge/datasets.py -> prepare_ohlcvs_dataset(...)`

Supporting modules:

- `apps/edge/data/validation.py`
- `apps/edge/data/cleaning.py`
- `apps/edge/data/enrichment.py`
- `apps/edge/data/models.py`

Prepared datasets include:

- canonical OHLCVS schema
- OHLC logical validation
- continuity and duplicate checks
- spread and volume validation
- missing-bar handling
- pip / point metadata
- body / wick / range features
- returns and log returns
- session and calendar enrichment

Session classification now uses dataset index time as-is, with fixed windows:

- `sydney` `00:00-06:59`
- `tokyo` `02:00-08:59`
- `london` `10:00-16:59`
- `ny` `15:00-21:59`

Overlaps and gaps are derived automatically and stored in the prepared dataset.

## Core Metric

Core Metric builds the first descriptive profile on top of the prepared dataset.

Location:

- `apps/edge/core_metrics/`

Current families:

- returns
- ROC
- candles
- ranges
- volatility
- spread
- volume / activity

Persistence:

- `edge_core_metric_runs`
- `edge_core_metric_values`

## EDS Studies

### EDS-0

Purpose:

- establish null / no-edge baselines

### EDS-1 Mean Reversion

Purpose:

- test whether stretched / compressed states revert

### EDS-2 Trend Persistence

Purpose:

- test whether breakout-style states continue

### EDS-3 Session Edge

Purpose:

- test time-window-specific behavior

These studies remain useful directly, but they also feed the wider Market Structure and Scorecard layers.

## Seasonality

Main entrypoint:

- `apps/edge/seasonality.py -> run_seasonality(...)`

Seasonality now covers:

- hourly movement metrics
- hourly spread metrics
- hourly volatility metrics
- session movement summaries
- session high / low formation rates
- weekday and monthly statistics
- ranked opportunity windows
- low-opportunity windows
- chart-ready heatmap and calendar models

The UI now exposes both:

- graphical heatmaps / charts for fast reading
- summary tables for auditability

## Market Structure

Main entrypoint:

- `apps/edge/market_structure.py -> build_market_structure_profile(...)`

This is the main behavior engine. It classifies:

- `TREND_BIASED`
- `REVERSION_BIASED`
- `MIXED`

### What It Measures

Trend-side structure:

- swing detection
- `HH` / `HL` / `LH` / `LL` structure
- chains and legs
- pullback quality
- continuation after pullback

Range / reversion / chop:

- range-state detection
- range duration and height
- breakout follow-through
- false-break frequency
- reentry probability
- half-life of reversion
- z-score / band reentry
- choppiness / whipsaw

Phase 6 deep-dive metrics:

- distribution metrics
- breakout and retracement analysis
- excursion studies
- stop/target suitability proxies

Phase 7 regime outputs:

- trend regime
- volatility regime
- liquidity regime
- transition matrix
- regime share and duration
- regime-conditioned metrics
- regime-aware score inputs

### Research Layers Around Market Structure

Supporting modules:

- `apps/edge/market_structure_validation.py`
- `apps/edge/market_structure_calibration.py`
- `apps/edge/market_structure_metric_calibration.py`
- `apps/edge/market_structure_profiles.py`
- `apps/edge/market_structure_profile_calibration.py`
- `apps/edge/market_structure_stability.py`
- `apps/edge/market_structure_robustness.py`
- `apps/edge/market_structure_strategy_fit.py`

These provide:

- forward validation
- top-level threshold calibration
- lower-level metric-band calibration
- symbol/timeframe profile calibration
- regime stability
- parameter robustness
- strategy-fit mapping

Persistence:

- `edge_market_structure_runs`
- `edge_market_structure_values`
- `edge_market_structure_scores`
- `edge_market_structure_swings`
- `edge_market_structure_legs`
- `edge_market_structure_evaluations`

## Scorecard

There are now two scorecard layers:

1. frontend progressive scorecard
   - `ui/src/lib/edge-lab-scorecard.ts`
2. backend automation scorecard
   - `apps/edge/scorecard.py`

The scorecard converts upstream analytics into named, explainable scores such as:

- Trendability
- Noise
- Cost Efficiency
- Mean Reversion
- Breakout Quality
- Session Opportunity
- Stability
- Tradability

It also adds:

- per-score confidence labels
- ranked strategy-fit outputs
- warnings and anti-fit conditions
- final opportunity label

The backend scorecard now also exposes:

- `score_spec_version`
- `research_ready`
- `readiness_label`
- `readiness_reasons`

## Strategy-Fit Engine

The final scorecard stage ranks strategy archetypes such as:

- Trend Breakout
- Trend Pullback Continuation
- Mean Reversion Fade
- Range Reversion
- Session Breakout
- Intraday Scalping
- Swing Trend Following
- Volatility Expansion

Each archetype includes:

- fit score
- rationale
- warnings
- anti-fit conditions
- explicit inputs used

## Snapshot Storage

Edge Lab now persists versioned pair-profile snapshots through:

- `apps/edge/profile_snapshot.py`
- `apps/sqlite/edge_discovery.py`
- `apps/sqlite/schema.py`

Snapshot tables:

- `edge_profile_snapshots`
- `edge_profile_snapshot_metrics`
- `edge_profile_snapshot_scores`
- `edge_profile_snapshot_strategy_fit`
- `edge_profile_snapshot_artifacts`

Snapshots preserve:

- dataset metadata
- Core Metric summary
- Seasonality summary
- Market Structure summary
- Scorecard rows
- strategy-fit rankings
- automation metadata
- report / artifact refs

Important reproducibility fields now preserved with snapshots:

- `model_version`
- `baseline_id`
- `dataset_fingerprint`
- `config_fingerprint`
- `score_spec_version`

## Reporting

Main reporting module:

- `apps/edge/profile_reporting.py`

Current outputs:

- profile summary builder
- dashboard summary builder
- JSON pair report
- Markdown pair report
- Markdown pair comparison report

Reports are snapshot-based, so they stay aligned with the stored version/spec instead of re-running analysis on export.

## Automation

Automation entrypoints live in:

- `apps/api/routes/edge.py`

Current automation endpoints:

- `POST /api/edge-lab/automation/run`
- `POST /api/edge-lab/automation/batch`
- `POST /api/edge-lab/automation/refresh`

The automation path runs:

1. dataset preparation
2. Core Metric
3. Seasonality
4. Market Structure
5. backend Scorecard
6. optional snapshot persistence

Current automation features:

- single-symbol runner
- batch runner
- scheduled refresh hook
- rerun metadata
- partial recomputation by family
- cache reuse of matching snapshots

Dependency policy:

- `scorecard -> market_structure -> seasonality -> core_metric`

Automation metadata now includes:

- trigger type
- run reason
- requested families
- recomputed vs reused families
- cache / dependency policy
- partial-snapshot flag
- per-stage timings

Per-stage timings currently cover:

- dataset prepare
- cache lookup
- Core Metric
- Seasonality
- Market Structure
- backend Scorecard
- snapshot persistence
- total runtime

Scheduler integration exists in:

- `apps/utils/scheduler.py`

and can run universe refreshes when `EDGE_LAB_BATCH_SYMBOLS` is configured.

## Non-UI Examples

The current progressive Edge Lab workflow also has non-UI example scripts under:

- `examples/edge/01_prepare_dataset.py`
- `examples/edge/02_core_metric.py`
- `examples/edge/03_seasonality.py`
- `examples/edge/04_market_structure.py`
- `examples/edge/05_scorecard_snapshot.py`
- `examples/edge/06_automation_run.py`

These examples use real MT5 data and mirror the main progressive flow:

1. prepare one dataset
2. build Core Metric
3. run Seasonality
4. run Market Structure
5. build/export Scorecard + snapshot
6. exercise the backend automation runner

Shared helper code for the examples lives in:

- `examples/edge/_workflow_common.py`

The examples are intentionally simple and are useful for:

- quick manual verification outside the UI
- MT5-backed smoke testing
- showing the progressive Edge Lab flow in script form

## UI Integration

Relevant frontend areas:

- `ui/src/contexts/edge-lab-data-context.tsx`
- `ui/src/components/edge-lab/`
- `ui/src/lib/api/edge.ts`
- `ui/src/lib/edge-lab-dashboard.ts`

Main pages:

- `/edge-lab`
- `/edge-lab/core-metric`
- `/edge-lab/seasonality`
- `/edge-lab/market-structure`
- `/edge-lab/scorecard`
- `/edge-lab/automation`
- `/edge-lab/discovery`

The UI now supports:

- progressive prerequisite gating
- shared prepared dataset reuse
- Market Structure research panels
- Scorecard snapshot save/export/compare
- automation execution page
- shared dashboard/view-model builders

## Testing

Edge Lab now has dedicated coverage for:

- unit tests under `tests/unit/apps/edge`
- integration tests under `tests/integration/apps/edge`
- acceptance tests under `tests/acceptance/apps/edge`
- synthetic fixtures under `tests/fixtures/edge_lab_scenarios.py`

Acceptance scenarios include:

- trending
- ranging / mixed
- noisy
- spread-heavy
- missing-data
- short-history
- DST/session-boundary

The integration/audit layer verifies:

- completed automation runs
- cache reuse
- partial recompute metadata
- reproducibility
- snapshot comparison
- report consistency

## Public Module Surface

```text
apps/edge/
|-- __init__.py
|-- config.py
|-- datasets.py
|-- results_schema.py
|-- scorecard.py
|-- profile_snapshot.py
|-- profile_reporting.py
|-- seasonality.py
|-- market_structure.py
|-- market_structure_validation.py
|-- market_structure_calibration.py
|-- market_structure_metric_calibration.py
|-- market_structure_profiles.py
|-- market_structure_profile_calibration.py
|-- market_structure_stability.py
|-- market_structure_robustness.py
|-- market_structure_strategy_fit.py
|-- core_metrics/
|-- data/
|-- eds_null_models.py
|-- eds_mean_reversion.py
|-- eds_trend_persistence.py
|-- eds_session.py
`-- README.md
```

## Philosophy

Edge Lab is not the final execution strategy layer.

It is the upstream research layer that helps decide:

- what kind of symbol behavior exists
- whether that behavior is stable and trustworthy
- whether it is efficient enough to trade
- which strategy archetypes fit it best
- how that profile compares across runs, versions, and symbols

## Related Documentation

Detailed architecture notes are maintained in:

- `docs/haruquant/architecture.md`
