# HaruQuant Risk Folder Restructure Plan

## Purpose

The current `risk/` folder contains many valuable pieces, but they are mixed across legacy root-level files, production engines, research simulation tools, live execution adapters, policy logic, reporting, scoring, and persistence. The goal is to reorganize it into a production-grade risk management subsystem that is easy to understand, easy to extend, and usable by both research workflows and live trading workflows.

---

## 1. Current State Diagnosis

### Observed folder facts

- Current package contains **142 Python files**.
- Current package has **24 root-level Python files**, which makes the root too noisy.
- There are several overlapping concepts:
  - `risk/governor.py` and `risk/core/governance_engine.py`
  - `risk/policies.py`, `risk/policy/`, and `risk/limits/`
  - root metric utilities such as `var.py`, `cvar.py`, `correlation.py`, `drawdown.py`, `exposure.py`, `margin.py` and package metrics under `risk/metrics/`
  - `risk/live/` contains trading engine code that may belong partly in execution/live integration, not pure risk core
  - `risk/simulation/`, `risk/scenarios/`, and `risk/reports/` are useful but should clearly be research/replay/reporting layers, not core production enforcement

### Main issue

The folder currently mixes four different concerns:

1. **Risk domain model** — account, position, market, portfolio, proposals, decisions.
2. **Risk calculations** — exposure, VaR, CVaR, margin, drawdown, correlation, concentration.
3. **Risk governance and enforcement** — pre-trade checks, policy, limits, kill switch, approvals, audit tokens.
4. **Applications/workflows** — live trading integration, replay, what-if, scenario analysis, reports, dashboards.

The restructure should separate these concerns so every file answers one clear question: _What layer am I in, and who is allowed to import me?_

---

## 2. Recommended Target Architecture

```text
services/risk/
    __init__.py
    README.md
    ARCHITECTURE.md
    WORKFLOWS.md
    POLICY_GUIDE.md
    LIVE_TRADING_GUIDE.md
    RESEARCH_GUIDE.md

    domain/
        __init__.py
        account.py
        market.py
        position.py
        portfolio.py
        symbol.py
        proposal.py
        decision.py
        approval.py
        snapshot.py
        events.py
        exceptions.py

    config/
        __init__.py
        thresholds.py
        policy_profiles.py
        schemas.py
        defaults.py

    calculations/
        __init__.py
        exposure.py
        concentration.py
        correlation.py
        drawdown.py
        margin.py
        position_sizing.py
        var.py
        cvar.py
        volatility.py
        stress.py
        math_utils.py

    metrics/
        __init__.py
        base.py
        registry.py
        account.py
        portfolio.py
        position.py
        symbol.py
        strategy.py
        concentration.py
        correlation.py
        currency_exposure.py
        drawdown.py
        margin.py
        tail_risk.py
        volatility.py
        stress.py

    policy/
        __init__.py
        models.py
        resolver.py
        profiles.py
        compliance.py
        restrictions.py
        limit_events.py
        limit_engine.py
        hard_limits.py
        soft_limits.py
        circuit_breakers.py
        pre_trade.py
        post_trade.py

    governance/
        __init__.py
        risk_governor.py
        governance_engine.py
        approval_tokens.py
        validity.py
        audit.py
        signatures.py
        decision_composer.py
        kill_switch.py

    portfolio/
        __init__.py
        state_builder.py
        snapshot_builder.py
        contributions.py
        impacts.py
        proposals.py
        advisory_enforcement.py

    regimes/
        __init__.py
        models.py
        engine.py
        market.py
        volatility.py
        liquidity.py
        crisis.py
        transitions.py

    scoring/
        __init__.py
        base.py
        registry.py
        normalization.py
        portfolio_health.py
        margin_safety.py
        leverage_safety.py
        concentration_score.py
        diversification_score.py
        stress_fragility.py
        governance_compliance.py
        regime_alignment.py
        overall_quality.py

    optimization/
        __init__.py
        models.py
        marginal_risk.py
        allocation_optimizer.py
        allocation_planner.py
        capital_efficiency.py
        hedge_optimizer.py
        rebalance_suggestions.py

    scenarios/
        __init__.py
        models.py
        registry.py
        evaluator.py

    replay/
        __init__.py
        models.py
        clock.py
        timeline.py
        replay_engine.py
        what_if_engine.py
        cockpit_state.py
        hypothetical_orders.py

    live/
        __init__.py
        adapter.py
        live_risk_service.py
        safety_checks.py
        execution_gate.py
        portfolio_sync.py

    reports/
        __init__.py
        risk_report.py
        scenario_report.py
        replay_report.py
        markdown.py
        json_export.py
        templates.py

    storage/
        __init__.py
        schema.py
        repositories.py
        snapshot_store.py
        scenario_store.py
        decision_store.py

    validators/
        __init__.py
        common.py
        account.py
        market.py
        positions.py
        symbols.py
        limits.py

    workflows/
        __init__.py
        research_risk_workflow.py
        pre_trade_workflow.py
        live_monitoring_workflow.py
        post_trade_workflow.py
        replay_workflow.py
        portfolio_review_workflow.py
```

---

## 3. What Should Be Moved Where

| Current file/folder | Recommended destination | Reason |
|---|---|---|
| `models/*` | `domain/*` | These are core domain objects and should be the foundation layer. |
| `contracts.py` | split into `domain/proposal.py`, `domain/approval.py`, `domain/decision.py` | Current contract file combines too many concepts. |
| `snapshots.py` | `domain/snapshot.py` | Snapshot models belong with domain models. |
| `exceptions.py` | `domain/exceptions.py` | Domain-level exception definitions. |
| `calculators.py` | split into `calculations/math_utils.py`, `calculations/exposure.py`, `calculations/position_sizing.py` | Too generic; should be split by calculation family. |
| `var.py`, `cvar.py` | `calculations/var.py`, `calculations/cvar.py` | Root-level quantitative calculations should move under calculations. |
| `correlation.py` | `calculations/correlation.py` | Keep pure correlation math separate from metric wrappers. |
| `drawdown.py` | `calculations/drawdown.py` | Pure drawdown calculation. |
| `exposure.py` | `calculations/exposure.py` or split with `calculations/concentration.py` | Exposure and concentration are calculation primitives. |
| `margin.py` | `calculations/margin.py` | Pure margin impact calculations. |
| `position_sizing.py` | `calculations/position_sizing.py` | Position sizing is calculation logic, not governance. |
| `thresholds.py` | `config/thresholds.py` | Threshold loading/validation is config. |
| `policies.py` | deprecate or split into `policy/pre_trade.py`, `policy/limit_engine.py`, `governance/risk_governor.py` | Current file duplicates policy and governance concerns. |
| `policy/*` | keep under `policy/` | Policy models, compliance, resolver, and profiles belong together. |
| `limits/*` | merge into `policy/*` | Limits are part of policy enforcement, not a separate top-level concept. |
| `restrictions.py` | `policy/restrictions.py` | Session, spread, operating mode, and compliance restrictions are policy checks. |
| `governor.py` | `governance/risk_governor.py` | Main deterministic enforcement gateway. |
| `approval_tokens.py` | `governance/approval_tokens.py` | Approval token lifecycle belongs to governance. |
| `audit.py` | `governance/audit.py` | Decision audit belongs to governance. |
| `signatures.py` | `governance/signatures.py` | Signing is part of governance provenance. |
| `validity.py` | `governance/validity.py` | Decision expiry and invalidation belongs to governance. |
| `decisions.py` | `governance/decision_composer.py` | Decision composition/provenance belongs to governance. |
| `safety/kill_switch.py` | `governance/kill_switch.py` | Kill switch is a governance primitive. |
| `safety/audit.py` | `governance/kill_switch_audit.py` or merge into `governance/audit.py` | Avoid separate audit concepts. |
| `core/portfolio_state_engine.py` | `portfolio/state_builder.py` | State assembly is portfolio layer. |
| `core/risk_snapshot_engine.py` | `portfolio/snapshot_builder.py` or `metrics/snapshot_engine.py` | Builds risk snapshot from portfolio state. |
| `core/governance_engine.py` | `governance/governance_engine.py` | Governance orchestration. |
| `core/portfolio_risk_engine.py` | split into `calculations/*` and `portfolio/risk_engine.py` | It combines math and state access; split if possible. |
| `core/recommendation_engine.py` | `optimization/recommendation_engine.py` | Recommendation logic belongs with optimization/advisory. |
| `core/risk_scorecard_engine.py` | `scoring/scorecard_engine.py` | Scorecard orchestration belongs to scoring. |
| `core/timeline_reconstructor.py` | `replay/timeline.py` | Timeline reconstruction is replay/research. |
| `simulation/*` | rename to `replay/*` | “Replay” is clearer than generic simulation for risk playback. |
| `scenarios/*` | keep under `scenarios/` | Scenario stress testing is a separate research + governance support layer. |
| `live/engine.py` | move most logic outside risk, keep only `live/live_risk_service.py` and `live/execution_gate.py` | Risk should gate execution, not become the live trading engine. |
| `live/portfolio_manager.py` | `live/portfolio_sync.py` or move to execution service | MT5 account/position synchronization is adapter logic. |
| `live/safety_checks.py` | `live/safety_checks.py` and/or `policy/pre_trade.py` | Keep broker/platform checks near live adapter, but policy check logic should be reusable. |
| `reports/*` | keep under `reports/` | Reporting is an application layer. |
| `storage/*` | keep under `storage/` | Persistence layer is well separated already. |
| `validators/*` | keep under `validators/` | Input validation is well separated. |

---

## 4. Files to Treat as Canonical vs Legacy

### Canonical foundation

Keep and build around these concepts:

- Domain models from `models/`
- `metrics/` registry approach
- `scoring/` registry approach
- `policy/` resolver/compliance models
- `limits/` policy engine logic, but merge it into `policy/`
- `governor.py` approval-token/audit flow
- `simulation/` replay/what-if features, renamed to `replay/`
- `scenarios/` stress testing
- `storage/` repositories and stores

### Legacy or compatibility layer

These should be treated carefully:

- Root-level `policies.py`: useful but overlaps with `policy/` and `limits/`.
- Root-level `calculators.py`: useful but too broad.
- Root-level `var.py`, `cvar.py`, `drawdown.py`, `margin.py`, `exposure.py`, `correlation.py`: useful but should move under `calculations/`.
- `live/engine.py`: likely too large for the risk package. It should become an execution-level engine that imports risk, not the other way around.
- `live/portfolio_manager.py`: likely belongs in execution/live or broker integration, with risk consuming its normalized snapshot.

---

## 5. Production-Grade Risk System Boundary

The risk system should expose a small public API. Other HaruQuant services should not import random internal files.

### Public API

```python
from services.risk import (
    RiskGovernor,
    RiskAssessmentRequest,
    RiskDecision,
    PortfolioStateBuilder,
    RiskSnapshotBuilder,
    RiskReportBuilder,
)
```

### Production request flow

```text
Strategy Signal
    ↓
Trade Proposal
    ↓
Portfolio State Builder
    ↓
Market/Account/Position Validation
    ↓
Risk Snapshot Builder
    ↓
Policy Resolver
    ↓
Pre-Trade Limit Engine
    ↓
Risk Governor
    ↓
Decision: APPROVED / REDUCED / REJECTED / BLOCKED
    ↓
Approval Token if approved
    ↓
Execution Gate validates token before broker order
    ↓
Post-Trade Checks + Audit + Storage
```

### Production rule

No order should reach the broker unless it has a valid, unexpired approval token from the `RiskGovernor`.

---

## 6. Recommended Workflows

## Workflow A — Research Risk Review

Purpose: evaluate a strategy, portfolio, or candidate allocation before live deployment.

```text
Backtest results / candidate portfolio
    ↓
Build PortfolioState
    ↓
Compute metrics
    ↓
Run scenarios and stress tests
    ↓
Build scorecard
    ↓
Generate recommendations
    ↓
Export markdown/json report
```

Outputs:

- Risk snapshot
- Scorecard
- Scenario report
- Portfolio recommendations
- Research approval memo

Core modules:

- `portfolio/state_builder.py`
- `metrics/`
- `scoring/`
- `scenarios/`
- `optimization/`
- `reports/`

---

## Workflow B — Pre-Trade Live Risk Gate

Purpose: decide whether a proposed live trade can be executed.

```text
Signal / execution proposal
    ↓
Create RiskProposal
    ↓
Assemble latest account, position, market, symbol state
    ↓
Validate inputs
    ↓
Calculate proposed trade risk
    ↓
Apply hard limits
    ↓
Apply soft limits
    ↓
Apply session/spread/broker restrictions
    ↓
Apply kill switch state
    ↓
Approve, reduce, reject, or block
    ↓
Issue approval token only if allowed
```

Outputs:

- `RiskDecision`
- approval token if approved
- rejection reasons if blocked/rejected
- audit record

Core modules:

- `domain/proposal.py`
- `portfolio/state_builder.py`
- `policy/pre_trade.py`
- `policy/limit_engine.py`
- `governance/risk_governor.py`
- `governance/approval_tokens.py`
- `governance/audit.py`

---

## Workflow C — Execution Gate

Purpose: protect the broker bridge from unsafe orders.

```text
Execution service receives order request
    ↓
Check approval token exists
    ↓
Validate token signature
    ↓
Validate expiry
    ↓
Validate proposal fingerprint has not materially changed
    ↓
Validate approved size >= requested execution size
    ↓
Allow or deny broker order
```

Outputs:

- execution allowed / denied
- token validation audit

Core modules:

- `governance/approval_tokens.py`
- `governance/validity.py`
- `live/execution_gate.py`

---

## Workflow D — Live Monitoring

Purpose: continuously monitor portfolio health while positions are open.

```text
Timer / market tick / account update
    ↓
Sync account, positions, prices, spreads
    ↓
Build current PortfolioState
    ↓
Build RiskSnapshot
    ↓
Check post-trade limits and circuit breakers
    ↓
Update kill-switch state if needed
    ↓
Generate alerts/recommendations
    ↓
Persist snapshot
```

Outputs:

- current risk snapshot
- limit events
- alerts
- recommendations
- kill-switch state transitions

Core modules:

- `live/portfolio_sync.py`
- `portfolio/state_builder.py`
- `metrics/`
- `policy/post_trade.py`
- `governance/kill_switch.py`
- `storage/snapshot_store.py`

---

## Workflow E — Replay / What-If Risk Analysis

Purpose: replay historical states and test alternative risk actions.

```text
Historical timeline
    ↓
Replay portfolio states frame by frame
    ↓
Compute risk snapshot and scorecard per frame
    ↓
Apply hypothetical resize/hedge/derisk actions
    ↓
Compare before vs after
    ↓
Export replay report
```

Outputs:

- replay run
- replay frames
- cockpit state payloads
- what-if comparison
- replay report

Core modules:

- `replay/timeline.py`
- `replay/replay_engine.py`
- `replay/what_if_engine.py`
- `replay/hypothetical_orders.py`
- `reports/replay_report.py`

---

## Workflow F — Portfolio Review / Risk Committee

Purpose: generate an institutional risk review for the CEO Agent, Portfolio Department, or Board.

```text
Current portfolio snapshot
    ↓
Metrics + scoring + regimes + scenarios
    ↓
Recommendation engine
    ↓
Policy compliance summary
    ↓
Markdown risk memo
    ↓
Decision: keep, reduce, hedge, pause, escalate
```

Outputs:

- risk committee memo
- portfolio health score
- top breaches/warnings
- action recommendations
- escalation decision

Core modules:

- `metrics/`
- `scoring/`
- `regimes/`
- `scenarios/`
- `optimization/`
- `reports/risk_report.py`

---

## 7. Clean Import Rules

To prevent future bloat, use strict layering.

```text
domain        imports nothing from risk except domain-level exceptions
config        may import domain exceptions only
calculations  may import domain models and config, but no governance/live/reports
metrics       may import domain + calculations
policy        may import domain + metrics + calculations + config
governance    may import domain + policy + calculations + config + storage
portfolio     may import domain + validators + calculations
regimes       may import domain + calculations
scoring       may import metrics + domain
optimization  may import metrics + scoring + portfolio
scenarios     may import domain + metrics + calculations
replay        may import portfolio + metrics + scoring + optimization
live          may import governance + portfolio + domain, but should not own strategy execution
reports       may import outputs from metrics/scoring/scenarios/replay/governance
storage       may import domain objects only
workflows     may orchestrate all layers
```

Forbidden imports:

- `calculations` must not import `governance`, `live`, `reports`, or `storage`.
- `domain` must not import anything above it.
- `metrics` must not call broker APIs.
- `risk` should not import execution engines except inside `live/adapter.py`.
- Broker-specific MT5/cTrader logic should stay in adapters, not core risk math.

---

## 8. Migration Plan

### Phase 1 — Freeze and map

- Freeze current `risk/` folder.
- Add tests around current externally used APIs.
- Identify imports from outside `services.risk`.
- Decide which symbols must remain backward compatible.

### Phase 2 — Create new structure

- Create new folders:
  - `domain/`
  - `config/`
  - `calculations/`
  - `governance/`
  - `replay/`
  - `workflows/`
- Add compatibility imports in old paths temporarily.

### Phase 3 — Move pure models and calculations

- Move `models/*` to `domain/*`.
- Move root calculations to `calculations/*`.
- Split `contracts.py` into proposal, decision, approval, memo models.
- Keep old imports working through deprecation wrappers.

### Phase 4 — Merge policy and limits

- Move `limits/*` into `policy/*`.
- Keep `policy/limit_engine.py` as the canonical limit engine.
- Deprecate root `policies.py` after moving its useful logic.

### Phase 5 — Governance cleanup

- Move `governor.py`, tokens, audit, signatures, validity, decisions into `governance/`.
- Make `RiskGovernor` the only production pre-trade decision entry point.
- Add `ExecutionGate` to validate approval tokens before broker orders.

### Phase 6 — Live adapter cleanup

- Reduce `risk/live/` to risk-facing adapters and gates only.
- Move full multi-strategy engine behavior back to execution/live if needed.
- Keep risk responsible for “approve or block,” not for owning all trading orchestration.

### Phase 7 — Research workflow cleanup

- Rename `simulation/` to `replay/`.
- Keep `scenarios/` separate.
- Add workflows for replay, scenario analysis, and risk reports.

### Phase 8 — Documentation and tests

- Add module-level README files.
- Add workflow docs.
- Add regression tests for:
  - risk proposal normalization
  - pre-trade gate
  - hard-limit rejection
  - soft-limit warning
  - approval token validation
  - kill switch block
  - live execution gate
  - replay what-if comparison
  - scenario report generation

---

## 9. Minimum Production API

```python
class RiskGovernor:
    def evaluate_trade(self, request: RiskAssessmentRequest) -> RiskDecision:
        ...

class ExecutionGate:
    def validate_order(self, order_request: BrokerOrderRequest, approval_token: str) -> GateDecision:
        ...

class PortfolioStateBuilder:
    def build(self, account, positions, market, symbols) -> PortfolioState:
        ...

class RiskSnapshotBuilder:
    def build(self, state: PortfolioState) -> RiskSnapshot:
        ...

class RiskReportBuilder:
    def build_current_report(self, state: PortfolioState) -> RiskReport:
        ...
```

---

## 10. Recommended Documentation Set

### `README.md`

Simple orientation:

- What the risk module does
- Public entry points
- Folder map
- Example usage

### `ARCHITECTURE.md`

Detailed design:

- Layered architecture
- Import rules
- Core data models
- State flow
- Decision flow
- Persistence and audit flow

### `WORKFLOWS.md`

Operational workflows:

- Research risk review
- Pre-trade gate
- Execution gate
- Live monitoring
- Post-trade review
- Replay/what-if
- Portfolio committee review

### `POLICY_GUIDE.md`

Policy authoring guide:

- Hard limits
- Soft limits
- Circuit breakers
- Compliance profiles
- Regime restrictions
- Override rules
- Escalation rules

### `LIVE_TRADING_GUIDE.md`

Live usage guide:

- How execution service calls risk
- How approval tokens work
- How kill switch works
- How broker state is synchronized
- How failures are handled fail-closed

### `RESEARCH_GUIDE.md`

Research usage guide:

- How to analyze a backtest
- How to build risk scorecards
- How to run stress scenarios
- How to run replay/what-if analysis
- How to compare strategies or portfolios

---

## 11. Final Recommended Mental Model

The clean system should be understood like this:

```text
Domain = What things are
Calculations = How risk numbers are computed
Metrics = How calculations become standardized rows/snapshots
Policy = What is allowed
Governance = Who decides and signs approval
Portfolio = How state is assembled and projected
Scoring = How risk quality is graded
Optimization = What actions are recommended
Scenarios = What happens under stress
Replay = What would have happened historically
Live = How production trading asks risk for permission
Reports = How humans and agents understand the result
Storage = How decisions and snapshots are preserved
Workflows = How all of the above are composed
```

This keeps HaruQuant risk management usable for both research and live trading without mixing the two layers.
