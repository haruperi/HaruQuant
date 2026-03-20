# HaruQuant Risk Engine

Portfolio-first risk infrastructure for the Python trading stack.

This package is no longer just a trade gate. It is now a layered risk system that covers:

- canonical portfolio state construction
- portfolio risk math and governance
- descriptive risk snapshots
- regime detection
- explainable scorecards
- recommendation and optimization helpers
- replay and what-if analysis
- storage of normalized risk artifacts
- snapshot-first reporting
- integration and acceptance test coverage

The authoritative broader architecture notes live in [docs/haruquant/architecture.md](C:/Users/rharu/Documents/MyApplications/HaruQuant/docs/haruquant/architecture.md).

## What This Package Owns

At a high level, `apps/risk` answers four different questions:

1. What does the current portfolio look like in a normalized, validated form?
2. How risky is it right now?
3. Is a proposed change allowed?
4. What should we do next, and how do we replay, store, and report that state?

That work is split into layers instead of being hidden inside one large runtime object.

## Current Architecture

### 1. Canonical State Layer

Files:

- `apps/risk/models/`
- `apps/risk/validators/`
- [`apps/risk/core/portfolio_state_engine.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/core/portfolio_state_engine.py)

Purpose:

- normalize raw account, position, symbol, market, and limit inputs
- validate that the portfolio has the minimum data needed for risk math
- produce one shared `PortfolioState` contract used by later layers

Core models:

- `AccountState`
- `PositionState`
- `SymbolState`
- `MarketState`
- `PortfolioState`

Key point:

- later risk layers should consume canonical state instead of rebuilding assumptions from raw MT5 payloads

### 2. Portfolio Risk Math Layer

Files:

- [`apps/risk/core/portfolio_risk_engine.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/core/portfolio_risk_engine.py)
- [`apps/risk/metrics/math.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/metrics/math.py)

Purpose:

- own the shared portfolio math used by governance, snapshots, and optimization
- bridge raw MT5/simulator data access when callers are still working from runtime positions rather than canonical state

Main responsibilities:

- returns alignment
- covariance estimation
- portfolio VaR / ES
- risk contributions
- cluster metrics
- notional exposure math
- margin estimation
- RC rebalance proposal math

### 3. Governance and Limits Layer

Files:

- [`apps/risk/core/governance_engine.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/core/governance_engine.py)
- `apps/risk/limits/`

Purpose:

- own hard portfolio gating and policy evaluation
- produce explainable warnings, breaches, overrides, and governance state

Main responsibilities:

- pre-trade checks
- post-trade checks
- hard limit evaluation
- soft warning evaluation
- circuit breaker handling
- regime-aware effective policy tightening

Important current boundary:

- `GovernanceEngine` is the public decision entry point
- `PolicyEngine` owns policy evaluation
- `PortfolioRiskEngine` owns the underlying math

### 4. Metric Snapshot Layer

Files:

- `apps/risk/metrics/`
- [`apps/risk/core/risk_snapshot_engine.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/core/risk_snapshot_engine.py)

Purpose:

- produce one normalized current-state `RiskSnapshot`
- describe the portfolio in a persistable row-based format

Metric families currently implemented:

- account risk
- position risk
- symbol risk
- currency exposure
- strategy risk
- portfolio risk
- margin risk
- concentration
- volatility risk
- correlation risk
- drawdown risk
- tail risk
- stress risk

Snapshot output now also carries:

- governance state and policy events
- regime summary

### 5. Regime Layer

Files:

- `apps/risk/regimes/`

Purpose:

- classify portfolio-relevant market state
- provide normalized regime output for snapshots, governance, and downstream explanation

Main components:

- `RegimeEngine`
- `RiskRegimeDetector`
- `CrisisRegimeDetector`
- `MarketRegimeDetector`
- `VolatilityRegimeDetector`
- `LiquidityRegimeDetector`
- transition helpers in `regime_transition.py`

Important note:

- the old `apps/risk/regime.py` module has been retired
- the legacy `NORMAL` / `STRESS` detector logic was absorbed into the new regime package

### 6. Scoring Layer

Files:

- `apps/risk/scoring/`
- [`apps/risk/core/risk_scorecard_engine.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/core/risk_scorecard_engine.py)

Purpose:

- turn descriptive risk snapshots into explainable 0-100 score rows
- keep scores separate from metrics

Current score families:

- portfolio health
- concentration
- diversification
- leverage safety
- margin safety
- stress fragility
- regime alignment
- governance compliance
- overall risk quality

Each score row is expected to be:

- explainable
- confidence tagged
- based on snapshot outputs rather than recalculating core math

### 7. Recommendation and Optimization Layer

Files:

- `apps/risk/optimization/`
- [`apps/risk/core/recommendation_engine.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/core/recommendation_engine.py)

Purpose:

- evaluate candidate actions using the existing state, snapshot, scorecard, and governance layers
- rank useful portfolio changes without introducing a second risk engine

Main components:

- `AllocationPlanner`
- `MarginalRiskEvaluator`
- `RebalanceSuggestionEngine`
- `CapitalEfficiencyRanker`
- `AllocationOptimizer`
- `HedgeOptimizer`
- `RecommendationEngine`

Important note:

- the old `apps/risk/allocator.py` module has been retired
- soft allocation planning now lives in `apps/risk/optimization/allocation_planner.py`

### 8. Replay and What-If Layer

Files:

- [`apps/risk/core/timeline_reconstructor.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/core/timeline_reconstructor.py)
- `apps/risk/simulation/`

Purpose:

- replay deterministic simulator frames through the risk stack
- compare baseline and hypothetical states without mutating the baseline

Main components:

- `TimelineReconstructor`
- `ReplayClock`
- `ReplayEngine`
- `WhatIfEngine`
- hypothetical action helpers
- cockpit payload builders

This layer intentionally reuses:

- the existing trading simulator in `apps/trading`
- `PortfolioStateEngine`
- `RiskSnapshotEngine`
- `RiskScorecardEngine`
- `RecommendationEngine`

### 9. Storage Layer

Files:

- `apps/risk/storage/`
- [`apps/sqlite/risk_storage.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/sqlite/risk_storage.py)

Purpose:

- persist normalized risk artifacts using the shared SQLite infrastructure

Stored artifact types:

- risk runs
- risk snapshots
- metric rows
- score rows
- policy events
- recommendations
- replay frame summaries
- scenarios

Design boundary:

- the risk package uses the existing SQLite manager
- it does not introduce a second persistence system

### 10. Reporting Layer

Files:

- `apps/risk/reports/`

Purpose:

- generate machine-readable and Markdown risk reports from stored artifacts
- avoid rerunning live engines during reporting

Main components:

- `risk_report_builder.py`
- `scenario_report_builder.py`
- `replay_report_builder.py`
- `markdown_report.py`
- `json_export.py`
- `summary_templates.py`

Design boundary:

- reporting is snapshot-first
- reports are built from stored bundles, not fresh runtime recomputation

### 11. Test Coverage Layer

Relevant paths:

- `tests/unit/apps/risk/`
- `tests/integration/apps/risk/`
- `tests/acceptance/apps/risk/`
- [`tests/fixtures/risk_portfolios.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/tests/fixtures/risk_portfolios.py)

Purpose:

- cover the stack from local math and policy behavior up through replay, storage, reporting, and acceptance outcomes

## Current Control Flow

The current intended flow is:

```text
Raw account/positions/symbols/market data
-> PortfolioStateEngine
-> PortfolioState
-> RiskSnapshotEngine
-> RiskSnapshot
-> RiskScorecardEngine
-> RiskScorecard
-> RecommendationEngine / GovernanceEngine / ReplayEngine / Storage / Reports
```

Trade-entry sizing sits beside that flow:

```text
Signal
-> PositionSizer
-> candidate lots
-> GovernanceEngine
-> execution or rejection
```

## Public Components

The main exported package entry points in [`apps/risk/__init__.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/__init__.py) are:

- `PositionSizer`
- `PortfolioStateEngine`
- `PortfolioRiskEngine`
- `GovernanceEngine`
- `RiskSnapshotEngine`
- `RiskScorecardEngine`
- `RecommendationEngine`
- `AllocationPlanner`
- `RegimeEngine`
- `RiskRegimeDetector`
- replay and what-if helpers
- reporting builders and exporters

## PositionSizer Boundary

[`apps/risk/position_sizing.py`](C:/Users/rharu/Documents/MyApplications/HaruQuant/apps/risk/position_sizing.py) remains an active and distinct component.

It is not replaced by the portfolio layers above.

It still owns:

- per-trade lot sizing
- fixed-lot sizing
- milestone sizing
- fixed-risk sizing
- Kelly sizing
- volatility sizing
- fixed-fractional sizing
- trade-level size validation

Use it when the question is:

- "How large should this trade be?"

Do not confuse that with:

- `AllocationPlanner`: "How should portfolio risk budget be distributed?"
- `GovernanceEngine`: "Is this transition allowed?"
- `RecommendationEngine`: "What change should improve the portfolio?"

## Retired Python Modules

These Python modules have been retired from the current architecture:

- `apps/risk/governor.py`
- `apps/risk/risk_limits.py`
- `apps/risk/regime.py`
- `apps/risk/allocator.py`

Their responsibilities were absorbed into:

- `apps/risk/core/governance_engine.py`
- `apps/risk/limits/`
- `apps/risk/regimes/`
- `apps/risk/optimization/allocation_planner.py`

If you see example or integration code still referring to the retired files, that code is stale.

## Examples

The current example set lives under [`examples/risk`](C:/Users/rharu/Documents/MyApplications/HaruQuant/examples/risk).

Phase-oriented examples:

1. `09_portfolio_state_foundation.py`
2. `10_core_risk_metric_snapshot.py`
3. `11_governance_limits_engine.py`
4. `12_structural_fragility_analytics.py`
5. `13_drawdown_tail_and_stress.py`
6. `14_regime_engine.py`
7. `15_scorecard_engine.py`
8. `16_recommendation_engine.py`
9. `17_replay_and_what_if.py`
10. `18_storage_and_snapshot_store.py`
11. `19_reporting_layer.py`

Older practical examples that still run:

- `01_position_sizing.py`
- `02_regime_detection.py`
- `03_risk_allocation.py`
- `04_risk_governor.py`
- `05_full_scenarios.py`
- `06_simple_single_strategy.py`
- `07_multi_strategy_portfolio.py`
- `08_integrate_existing_system.py`
- `demo.py`

Run examples from the repo root, for example:

```bash
python examples/risk/09_portfolio_state_foundation.py
python examples/risk/15_scorecard_engine.py
python examples/risk/19_reporting_layer.py
```

## Focused Test Commands

Examples of focused local commands used during development:

```bash
pytest --no-cov tests/unit/apps/risk/test_portfolio_state_engine.py
pytest --no-cov tests/unit/apps/risk/test_risk_snapshot_engine.py
pytest --no-cov tests/unit/apps/risk/test_policy_engine.py
pytest --no-cov tests/unit/apps/risk/test_regime_engine.py
pytest --no-cov tests/unit/apps/risk/test_risk_scorecard_engine.py
pytest --no-cov tests/unit/apps/risk/test_recommendation_engine.py
pytest --no-cov tests/unit/apps/risk/test_replay_engine.py
pytest --no-cov tests/unit/apps/risk/test_risk_storage.py
pytest --no-cov tests/unit/apps/risk/test_risk_reporting.py
pytest --no-cov tests/integration/apps/risk/test_risk_pipeline_integration.py
pytest --no-cov tests/integration/apps/risk/test_risk_replay_reporting_integration.py
pytest --no-cov tests/acceptance/apps/risk/test_risk_acceptance.py
```

Note:

- some environments in this repo have Windows-specific `pytest` temp cleanup issues
- when that happens, direct Python execution of focused tests may still be used for local verification

## Integration Notes

When integrating this package into trading code:

- use `PositionSizer` for trade-level sizing
- use `PortfolioStateEngine` when you want canonical normalized state
- use `GovernanceEngine` for approval/rejection and compliance checks
- use `RiskSnapshotEngine` for descriptive current-state analytics
- use `RiskScorecardEngine` when you need explainable scores
- use `RecommendationEngine` when you need ranked actions
- use replay/storage/report layers instead of building parallel tooling around the same artifacts

## Documentation Boundary

This README is the package-level overview.

For broader app architecture, cross-module boundaries, and implementation-history notes, use:

- [docs/haruquant/architecture.md](C:/Users/rharu/Documents/MyApplications/HaruQuant/docs/haruquant/architecture.md)

For runnable usage references, use:

- [examples/risk](C:/Users/rharu/Documents/MyApplications/HaruQuant/examples/risk)
