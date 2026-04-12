# HaruQuant Risk Engine

Portfolio-first risk infrastructure for the Python trading stack.

This package owns:
- canonical portfolio state construction
- portfolio risk math and governance
- descriptive risk snapshots
- regime detection
- explainable scorecards
- recommendations, replay, what-if analysis, and storage/reporting helpers

Broader cross-app architecture notes live in [docs/haruquant/architecture.md](../../docs/haruquant/architecture.md).

## Core Layers

### Canonical State

Main paths:
- `apps/risk/models/`
- `apps/risk/validators/`
- `apps/risk/core/portfolio_state_engine.py`

Purpose:
- normalize raw account, position, symbol, market, and limit inputs
- validate that the portfolio has enough data for downstream risk math
- produce one shared `PortfolioState` contract for the rest of the stack

### Portfolio Risk Math

Main paths:
- `apps/risk/core/portfolio_risk_engine.py`
- `apps/risk/metrics/math.py`

Purpose:
- portfolio VaR / ES
- covariance and correlation handling
- margin and exposure math
- risk contribution calculations

### Governance and Limits

Main paths:
- `apps/risk/core/governance_engine.py`
- `apps/risk/limits/`

Purpose:
- pre-trade and post-trade checks
- warnings and breaches
- explainable approval/rejection outcomes

Important boundary:
- canonical `PortfolioState` is the preferred governance input path

### Snapshots, Regimes, Scores, Recommendations

Main paths:
- `apps/risk/core/risk_snapshot_engine.py`
- `apps/risk/regimes/`
- `apps/risk/core/risk_scorecard_engine.py`
- `apps/risk/core/recommendation_engine.py`

Purpose:
- build descriptive snapshots
- classify market/risk regimes
- turn snapshots into explainable scores
- rank candidate portfolio actions

### Replay, Storage, Reporting

Main paths:
- `apps/risk/core/timeline_reconstructor.py`
- `apps/risk/simulation/`
- `apps/risk/storage/`
- `apps/risk/reports/`

Purpose:
- deterministic replay and what-if evaluation
- persistence of normalized risk artifacts
- snapshot-first reporting

## Current Control Flow

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

Main package entry points are exported through `apps/risk/__init__.py`, including:
- `PositionSizer`
- `PortfolioStateEngine`
- `PortfolioRiskEngine`
- `GovernanceEngine`
- `RiskSnapshotEngine`
- `RiskScorecardEngine`
- `RecommendationEngine`
- `AllocationPlanner`
- `RegimeEngine`
- replay and reporting helpers

## Retired Modules

These older Python modules are no longer part of the current architecture:
- `apps/risk/governor.py`
- `apps/risk/risk_limits.py`
- `apps/risk/regime.py`
- `apps/risk/allocator.py`

If examples or integration code still reference them, that code is stale.

## Examples

The current example set lives under [backend/scripts/examples/risk](../../backend/scripts/examples/risk).

Fixture-based deterministic example:
- `13_fixture_portfolio_state_demo.py`

Live-broker dependent manual demos:
- `01_portfolio_state_foundation.py`
- `02_core_risk_metric_snapshot.py`
- `03_governance_limits_engine.py`
- `04_structural_fragility_analytics.py`
- `05_drawdown_tail_and_stress.py`
- `06_regime_engine.py`
- `07_scorecard_engine.py`
- `08_recommendation_engine.py`
- `09_replay_and_what_if.py`
- `10_storage_and_snapshot_store.py`
- `11_reporting_layer.py`

Workflow demo:
- `12_comprehensive_workflows.py`

Run examples from the repo root, for example:

```bash
python backend/scripts/examples/risk/13_fixture_portfolio_state_demo.py
python backend/scripts/examples/risk/01_portfolio_state_foundation.py
python backend/scripts/examples/risk/07_scorecard_engine.py
```

## Focused Test Commands

Examples of focused local commands:

```bash
pytest --no-cov tests/unit/apps/risk/test_portfolio_state_engine.py
pytest --no-cov tests/unit/apps/risk/test_risk_snapshot_engine.py
pytest --no-cov tests/unit/apps/risk/test_policy_engine.py
pytest --no-cov tests/unit/apps/risk/test_regime_engine.py
pytest --no-cov tests/unit/apps/risk/test_risk_scorecard_engine.py
pytest --no-cov tests/unit/apps/risk/test_recommendation_engine.py
pytest --no-cov tests/unit/apps/risk/test_risk_storage.py
```

## Integration Notes

When integrating this package into trading code:
- use `PositionSizer` for trade-level sizing
- use `PortfolioStateEngine` for canonical normalized state
- use `GovernanceEngine` for approval/rejection and compliance checks
- use `RiskSnapshotEngine` for descriptive current-state analytics
- use `RiskScorecardEngine` for explainable scores
- use `RecommendationEngine` for ranked actions

This README is the package-level overview. For broader app architecture and implementation boundaries, use [docs/haruquant/architecture.md](../../docs/haruquant/architecture.md).
