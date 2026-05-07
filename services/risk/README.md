# Risk Service

The risk service is the safety and portfolio-risk subsystem for HaruQuant. It normalizes account, position, symbol, market, and proposal state; computes risk; applies policy; issues governed approvals; and supports research replay, scenarios, reports, and live execution gates.

## Public Entry Points

```python
from services.risk import (
    PortfolioStateBuilder,
    RiskAssessmentRequest,
    RiskDecision,
    RiskGovernor,
    RiskReportBuilder,
    RiskSnapshotBuilder,
)
```

## Folder Map

- `domain/`: account, market, position, portfolio, proposal, decision, approval, snapshot, and exceptions.
- `config/`: thresholds and configuration defaults.
- `calculations/`: pure exposure, VaR, CVaR, drawdown, margin, sizing, and correlation calculations.
- `metrics/`: standardized metric rows and registry-backed metric evaluation.
- `policy/`: policy resolution, compliance, and reusable policy checks.
- `governance/`: governor, approval tokens, signatures, validity, audit, and kill switch controls.
- `portfolio/`: portfolio state and snapshot assembly plus advisory portfolio projections.
- `scoring/`: registry-backed risk scorecards.
- `optimization/`: allocation, hedging, marginal risk, and rebalance recommendations.
- `scenarios/`: stress scenario models, registry, and evaluation.
- `replay/`: historical replay and what-if analysis.
- `live/`: risk-facing live adapters and execution gates.
- `reports/`: markdown, JSON, scenario, replay, and current risk reports.
- `storage/`: repositories and snapshot/scenario persistence.
- `validators/`: account, market, position, symbol, and limit validators.
- `workflows/`: orchestration entry points for research, pre-trade, live monitoring, and replay workflows.

The package root is intentionally kept clean: public imports go through `services.risk`, and implementations live in the layer folders above.


# Risk Architecture

The risk service is layered so production enforcement does not depend on research or live trading orchestration.

## Layers

```text
domain -> config -> calculations -> metrics -> policy -> governance
                       |             |           |
                       v             v           v
                  portfolio      scoring      live
                       |             |
                       v             v
                 scenarios       optimization
                       |             |
                       v             v
                     replay ------ reports
```

## Import Rules

- `domain` is the foundation and should not import higher risk layers.
- `calculations` contains pure math and should not import `governance`, `live`, `reports`, or `storage`.
- `metrics` may use `domain` and `calculations`.
- `policy` may use `domain`, `metrics`, `calculations`, and `config`.
- `governance` decides, signs, audits, and validates approvals.
- `live` asks risk for permission; it should not own strategy execution.
- `reports`, `replay`, and `scenarios` are application/research layers.

## Production Boundary

No broker order should be sent unless a `RiskGovernor` approval created a valid, unexpired approval token, and an execution gate validates that token against the requested order.


# Live Trading Guide

Live trading must call risk before sending an order to the broker.

1. Normalize the proposal and latest account, position, symbol, and market state.
2. Build a portfolio state and current risk snapshot.
3. Ask `RiskGovernor` for a decision.
4. Send orders only when the decision includes a valid approval token.
5. Validate the token again at the execution gate.
6. Fail closed on missing state, expired tokens, changed proposal details, or active kill switch state.

Broker-specific logic belongs in live adapters or execution services, not in core calculations.


# Policy Guide

Risk policy answers one question: what is allowed right now?

Use hard limits for non-negotiable blocks, soft limits for warnings or size reductions, circuit breakers for fail-closed state transitions, and compliance profiles for account, strategy, symbol, session, spread, and operating-mode restrictions.

Policy checks should be reusable by both pre-trade and post-trade workflows. Governance owns the final decision and approval token; policy only reports allowed actions, warnings, breaches, and required reductions.


# Research Guide

Research workflows can use risk without touching live execution.

Use `portfolio/` to assemble portfolio state, `metrics/` for standardized risk rows, `scoring/` for scorecards, `scenarios/` for stress testing, `optimization/` for recommendations, `replay/` for historical playback and what-if analysis, and `reports/` for markdown or JSON outputs.

Research code may orchestrate many layers, but calculation and domain modules should stay reusable by production workflows.



# Risk Workflows

## Pre-Trade Gate

```text
Proposal -> PortfolioStateBuilder -> RiskSnapshotBuilder -> policy checks -> RiskGovernor -> approval token or rejection
```

Use this for live or paper execution requests. The decision must fail closed when required context or configuration is invalid.

## Execution Gate

```text
Order request -> approval token validation -> proposal fingerprint check -> approved size check -> allow or deny broker order
```

The execution service should treat the risk token as mandatory.

## Live Monitoring

```text
Account/position/market sync -> current portfolio state -> risk snapshot -> post-trade checks -> alerts, storage, kill switch updates
```

## Research Review

```text
Backtest or candidate portfolio -> metrics -> scoring -> scenarios -> recommendations -> markdown/json report
```

## Replay / What-If

```text
Historical timeline -> replay frames -> risk snapshots -> hypothetical actions -> comparison report
```

## Portfolio Committee Review

```text
Current portfolio -> metrics + scorecard + regimes + scenarios -> recommendations -> risk memo
```


