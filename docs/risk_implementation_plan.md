# Implementation Plan
## HaruQuant Risk Intelligence Engine

## 1. Objective
This implementation plan defines the phased roadmap for building the HaruQuant Risk Intelligence Engine as a comprehensive portfolio-risk, governance, and simulation-ready subsystem.

The subsystem will deliver:
- portfolio-wide risk analytics
- explainable governance and limit checks
- scenario and stress testing
- marginal-risk and allocation recommendations
- replay-ready risk snapshots for simulator UI
- Markdown and JSON reporting

---

## 2. Delivery Strategy
The subsystem should be built in layered phases:
1. contracts and architecture
2. canonical portfolio-state foundation
3. core risk metrics
4. governance and limit engine
5. volatility, correlation, and stress analytics
6. scoring and recommendation intelligence
7. replay/simulator support
8. reporting, testing, and calibration

This order ensures the simulator is powered by real backend intelligence instead of UI-only placeholders.

---

## 3. Scope Summary
### In Scope
- account, position, symbol, currency, strategy, and portfolio risk analytics
- margin and leverage analytics
- volatility and correlation risk analytics
- drawdown, VaR/CVaR, and stress analysis
- policy, limits, and governance engine
- recommendation and allocation support
- historical replay snapshot generation
- simulator-compatible outputs

### Out of Scope for Initial Release
- direct live broker execution from simulator
- full real-time streaming risk recomputation at ultra-high frequency
- advanced ML optimization without explainability
- exchange/clearing-level counterparty exposure modeling

---

## 4. Repository Placement
Recommended module path:

```text
apps/risk/
```

Recommended docs path:

```text
docs/risk/
```

---

## 5. Phase Plan

## Phase 0 — Design Freeze and Project Setup
### Goal
Define subsystem contracts, architecture, naming, and standards before implementation.

### Tasks
- create subsystem package structure
- create documentation pack
- define canonical portfolio-state contract
- define risk snapshot contract
- define policy configuration contract
- define scenario configuration contract
- define score and metric versioning rules
- define logging and audit standards
- define simulator integration boundary

### Deliverables
- `Risk_SRS.md`
- `Risk_Design.md`
- `Risk_MetricCatalog.md`
- `Risk_ScorecardSpec.md`
- `Risk_ImplementationPlan.md`
- initial package skeleton

### Exit Criteria
- contracts are internally consistent
- no major ambiguity remains in model boundaries
- simulator/backend interface is clearly defined

---

## Phase 1 — Canonical State Foundation
### Goal
Build the canonical input, validation, and portfolio-state layers.

### Tasks
#### 1. Input contracts
- define account state model
- define position state model
- define pending order model
- define symbol specs model
- define market slice model
- define policy config model

#### 2. Validation
- validate account values
- validate position completeness
- validate symbol specs
- validate synchronized market coverage across active symbols
- validate policy and limit config

#### 3. Portfolio state engine
- normalize raw inputs into canonical portfolio state
- compute derived exposure primitives
- support point-in-time and historical-state construction
- attach validation summary and metadata

### Deliverables
- `models/account_models.py`
- `models/position_models.py`
- `models/portfolio_models.py`
- `validators/*`
- `core/portfolio_state_engine.py`

### Exit Criteria
- a portfolio can be loaded into a canonical validated state object
- point-in-time state can be reconstructed deterministically

---

## Phase 2 — Core Risk Metric MVP
### Goal
Deliver the first usable portfolio risk snapshot.

### Metric Families
- account state
- position risk
- symbol risk
- currency exposure
- strategy exposure
- portfolio risk
- margin and leverage

### Tasks
- create metric interface and registry
- implement position risk metrics
- implement symbol risk metrics
- implement currency exposure metrics
- implement strategy group metrics
- implement portfolio exposure and heat metrics
- implement margin and leverage metrics
- persist normalized metric rows

### Deliverables
- `metrics/position_risk.py`
- `metrics/symbol_risk.py`
- `metrics/currency_exposure.py`
- `metrics/portfolio_risk.py`
- `metrics/margin_risk.py`
- `metrics/concentration.py`
- metric registry

### Exit Criteria
- one portfolio snapshot can produce a useful top-level risk report
- metrics are unit tested and persistable

---

## Phase 3 — Governance and Limits Engine
### Goal
Make the subsystem capable of enforcing risk policy and exposing governance state.

### Tasks
- define limit models and policy contracts
- implement pre-trade checks
- implement post-trade checks
- implement hard limits
- implement soft limits
- implement override recording model
- implement circuit-breaker rules
- implement risk-budget utilization tracking
- store policy events and breach records

### Deliverables
- `limits/pre_trade_checks.py`
- `limits/post_trade_checks.py`
- `limits/hard_limits.py`
- `limits/soft_limits.py`
- `limits/circuit_breakers.py`
- `limits/policy_engine.py`

### Exit Criteria
- snapshot output includes compliance state
- breaches and warnings are explainable and persisted

---

## Phase 4 — Volatility, Correlation, and Concentration Analytics
### Goal
Measure structural fragility beyond static exposure.

### Tasks
#### Volatility
- implement symbol volatility state metrics
- implement volatility-adjusted exposure
- implement volatility shock loss estimates

#### Correlation
- implement rolling pairwise correlations
- implement intra-portfolio correlation summary
- implement redundancy metrics
- implement cluster exposure analysis

#### Concentration
- implement hidden overlap scoring
- implement effective independent bets
- implement diversification ratio

### Deliverables
- `metrics/volatility_risk.py`
- `metrics/correlation_risk.py`
- enhanced `metrics/concentration.py`
- clustering support structures

### Exit Criteria
- risk engine can identify correlated clusters and fragility to vol/correlation changes

---

## Phase 5 — Drawdown, Tail Risk, and Stress Testing
### Goal
Make the engine capable of serious downside analysis.

### Tasks
#### Drawdown
- implement current, historical, and projected drawdown metrics
- implement drawdown velocity and time-under-water metrics

#### Tail metrics
- implement VaR and CVaR framework
- support configurable methods and windows

#### Stress scenarios
- implement volatility shock scenario
- implement spread blowout scenario
- implement gap risk scenario
- implement correlation spike scenario
- implement liquidity crunch scenario
- define scenario registry and configuration model

### Deliverables
- `metrics/drawdown_risk.py`
- `metrics/var_cvar.py`
- `metrics/stress_risk.py`
- `scenarios/*`

### Exit Criteria
- engine can produce scenario losses and stressed portfolio summaries
- scenario assumptions are explicit and versioned

---

## Phase 6 — Regime Engine
### Goal
Make portfolio risk analysis state-aware.

### Tasks
- define market regime logic
- define volatility regime logic
- define liquidity regime logic
- define crisis regime logic
- implement regime labels and confidence
- link regime state to policy throttle hooks
- compute regime-alignment inputs for scoring and recommendation layers

### Deliverables
- `regimes/market_regime.py`
- `regimes/volatility_regime.py`
- `regimes/liquidity_regime.py`
- `regimes/crisis_regime.py`
- `regimes/regime_transition.py`

### Exit Criteria
- snapshot output includes regime labels and regime-conditioned warnings
- policies can react to regimes in a documented way

---

## Phase 7 — Scorecard Engine
### Goal
Turn raw risk analytics into explainable score outputs.

### Tasks
- implement score normalization helpers
- implement Portfolio Health Score
- implement Concentration Score
- implement Diversification Score
- implement Leverage Safety Score
- implement Margin Safety Score
- implement Volatility Resilience Score
- implement Correlation Resilience Score
- implement Stress Resilience Score
- implement Regime Alignment Score
- implement Liquidity Safety Score
- implement Governance Compliance Score
- implement Allocation Efficiency Score
- implement Recovery Resilience Score
- implement Overall Risk Quality Score
- add score explanation and confidence models

### Deliverables
- `scoring/portfolio_health.py`
- `scoring/concentration_score.py`
- `scoring/diversification_score.py`
- `scoring/stress_fragility.py` or resilience equivalent
- `scoring/regime_alignment.py`
- score registry

### Exit Criteria
- reports and dashboards include a full scorecard with rationale and confidence

---

## Phase 8 — Recommendation and Optimization Engine
### Goal
Enable action-oriented decision support.

### Tasks
- implement marginal risk engine
- implement add/remove/resize evaluation
- implement hedge candidate evaluation
- implement rebalance suggestion logic
- implement capital-efficiency ranking
- implement action recommendation scoring
- integrate governance feasibility checks into recommendations

### Deliverables
- `optimization/marginal_risk.py`
- `optimization/allocation_optimizer.py`
- `optimization/hedge_optimizer.py`
- `optimization/rebalance_suggestions.py`
- `optimization/capital_efficiency.py`
- recommendation output models

### Exit Criteria
- engine can rank candidate actions by risk-aware usefulness
- outputs are simulator-ready and explainable

---

## Phase 9 — Replay and Simulator Backend Support
### Goal
Provide replay-ready risk state reconstruction for the UI cockpit.

### Tasks
- build historical timeline reconstructor
- build per-bar portfolio state engine
- build replay frame model
- add checkpointing strategy for long replay windows
- implement hypothetical action injection into replay timeline
- implement what-if engine
- create cockpit state payloads for UI

### Deliverables
- `core/timeline_reconstructor.py`
- `simulation/replay_engine.py`
- `simulation/simulation_clock.py`
- `simulation/hypothetical_orders.py`
- `simulation/what_if_engine.py`
- `simulation/cockpit_state.py`

### Exit Criteria
- historical replay can reconstruct evolving risk state bar-by-bar
- what-if actions can be evaluated during replay
- simulator payloads are stable and sufficient for UI rendering

---

## Phase 10 — Storage and Snapshot Infrastructure
### Goal
Persist risk intelligence and replay artifacts in a structured and versioned way.

### Tasks
- define SQL schema for runs, snapshots, metrics, scores, policy events, scenarios, recommendations, replay frames
- implement repository layer
- implement Parquet exporters for wide or timeline-heavy data
- implement snapshot builder
- implement scenario artifact storage
- implement retrieval APIs for reports and simulator

### Deliverables
- `storage/schema.py`
- `storage/repositories.py`
- `storage/snapshot_store.py`
- `storage/scenario_store.py`

### Exit Criteria
- all major outputs are persistable and queryable
- replay and reports can retrieve historical artifacts consistently

---

## Phase 11 — Reporting Layer
### Goal
Generate complete human-readable and machine-readable risk reports.

### Tasks
- build portfolio risk report builder
- build scenario/stress report builder
- build markdown renderer
- build JSON exporter
- build dashboard summary payloads
- build replay summary payloads
- build recommendation summary templates

### Deliverables
- `reports/risk_report_builder.py`
- `reports/markdown_report.py`
- `reports/json_export.py`
- `reports/summary_templates.py`

### Exit Criteria
- one command can generate a full current risk report
- one command can generate a scenario/stress report
- simulator can consume replay summary payloads

---

## Phase 12 — Testing and Acceptance
### Goal
Make the subsystem trustworthy for serious portfolio use.

### Test Categories
#### Unit tests
- position risk formulas
- margin formulas
- currency decomposition
- correlation calculations
- VaR/CVaR methods
- score formulas
- policy rules
- scenario calculations

#### Integration tests
- validated inputs to complete risk snapshot
- complete risk snapshot to report
- replay reconstruction consistency
- policy engine integration with recommendations

#### Acceptance tests
- low-risk balanced portfolio
- concentrated single-currency portfolio
- high-leverage fragile portfolio
- high-correlation clustered portfolio
- margin-stressed portfolio
- volatility expansion stress case
- correlation spike stress case
- replay with hypothetical action insertion

#### Audit tests
- score explanation consistency
- breach audit trail completeness
- snapshot reproducibility
- replay checkpoint integrity

### Deliverables
- `tests/unit/`
- `tests/integration/`
- `tests/acceptance/`
- fixtures and synthetic portfolios

### Exit Criteria
- core risk and simulator backend pass acceptance criteria
- outputs are stable enough for portfolio decision use

---

## 6. Work Breakdown Structure (To-Do List)

## 6.1 Setup
- [ ] Create `apps/risk/`
- [ ] Create package skeleton
- [ ] Create docs folder
- [ ] Add logger imports and config
- [ ] Add README

## 6.2 Models and State
- [ ] Define account models
- [ ] Define position and order models
- [ ] Define portfolio state model
- [ ] Define risk snapshot model
- [ ] Define scenario models
- [ ] Define policy models
- [ ] Define recommendation models

## 6.3 Validation and Core State
- [ ] Implement validators
- [ ] Implement market synchronization checks
- [ ] Implement portfolio state engine
- [ ] Implement state snapshot builder
- [ ] Implement timeline reconstructor foundation

## 6.4 Metrics
- [ ] Implement metric interface
- [ ] Implement metric registry
- [ ] Implement account metrics
- [ ] Implement position risk metrics
- [ ] Implement symbol risk metrics
- [ ] Implement currency exposure metrics
- [ ] Implement strategy group metrics
- [ ] Implement portfolio risk metrics
- [ ] Implement margin/leverage metrics
- [ ] Implement volatility risk metrics
- [ ] Implement correlation risk metrics
- [ ] Implement drawdown metrics
- [ ] Implement VaR/CVaR metrics
- [ ] Implement liquidity metrics
- [ ] Implement stress metrics
- [ ] Implement regime risk metrics

## 6.5 Governance and Scenarios
- [ ] Implement pre-trade checks
- [ ] Implement post-trade checks
- [ ] Implement hard and soft limits
- [ ] Implement override logging
- [ ] Implement circuit breakers
- [ ] Implement scenario registry
- [ ] Implement core stress scenarios

## 6.6 Scores and Recommendations
- [ ] Implement score normalization helpers
- [ ] Implement full scorecard modules
- [ ] Implement confidence model
- [ ] Implement marginal risk engine
- [ ] Implement allocation suggestions
- [ ] Implement hedge suggestions
- [ ] Implement action ranking

## 6.7 Replay and Simulator Backend
- [ ] Implement replay engine
- [ ] Implement simulation clock
- [ ] Implement hypothetical orders
- [ ] Implement what-if engine
- [ ] Implement cockpit state payloads
- [ ] Implement replay checkpoints

## 6.8 Storage and Reports
- [ ] Design SQL schema
- [ ] Implement repositories
- [ ] Implement Parquet/timeline storage
- [ ] Implement JSON exporters
- [ ] Implement Markdown reports
- [ ] Implement scenario and replay report builders

## 6.9 Testing
- [ ] Create synthetic portfolio fixtures
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Add acceptance tests
- [ ] Add audit tests

---

## 7. Suggested Sprint Sequence

### Sprint 1
- Phase 0
- package setup
- canonical models and validators

### Sprint 2
- portfolio state engine
- core position/symbol/portfolio metrics
- current risk snapshot report stub

### Sprint 3
- governance and limits engine
- margin/leverage analytics
- initial dashboard summary payload

### Sprint 4
- volatility/correlation/concentration analytics
- early scorecard MVP

### Sprint 5
- drawdown, VaR/CVaR, and stress scenarios
- scenario reports

### Sprint 6
- regime engine
- recommendations and optimization MVP

### Sprint 7
- replay engine foundation
- historical risk snapshots
- simulator cockpit payloads

### Sprint 8
- what-if engine
- checkpoint optimization
- full acceptance tests

---

## 8. Milestones

### Milestone 1 — Canonical Risk Snapshot
A validated portfolio can be turned into a structured current-state risk snapshot.

### Milestone 2 — Governance-Aware Risk Engine
Limits, warnings, breaches, and policy compliance are fully integrated.

### Milestone 3 — Structural Fragility Engine
Volatility, correlation, concentration, drawdown, and stress analysis are available.

### Milestone 4 — Decision Support Engine
Recommendations and allocation/hedge suggestions are available.

### Milestone 5 — Simulator-Ready Backend
Replay frames, what-if actions, and cockpit payloads support a UI risk simulator.

---

## 9. Risks and Mitigations

### Risk: Inconsistent position or account data
Mitigation:
- strict validation and canonical model conversion
- explicit warning/fatal separation

### Risk: Correlation and scenario assumptions becoming misleading
Mitigation:
- version methods and assumptions
- expose configuration in reports and UI

### Risk: Replay reconstruction becoming too slow
Mitigation:
- checkpoint replay state
- separate heavy scenario calculations from baseline replay
- cache deterministic intermediate state

### Risk: Recommendations becoming black-box
Mitigation:
- persist inputs, weights, penalties, and rationale
- keep optimization constrained and explainable

### Risk: Governance logic spreading across modules
Mitigation:
- centralize policy engine and limit registries
- keep breach event schema consistent

---

## 10. Immediate Next Actions
1. Create repository skeleton under `apps/risk/`
2. Define canonical models for account, positions, portfolio state, and snapshots
3. Implement validation and portfolio state engine
4. Implement MVP metric registry and core snapshot metrics
5. Draft policy config and storage schema

---

## 11. Definition of Done
The Risk Intelligence Engine is complete for initial release when:
- a portfolio can be processed into a full risk snapshot
- governance, stress, and score outputs are available
- recommendations are explainable and persisted
- replay-ready frames can be generated for historical windows
- reports are available in JSON and Markdown
- acceptance tests pass
- documentation remains aligned with implementation

