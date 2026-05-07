# HaruQuant Risk Department

## Goal

Create a production-grade Risk Department for HaruQuant that protects the trading firm from unacceptable losses, excessive concentration, correlated exposure, margin stress, cost deterioration, broker anomalies, and unauthorized execution.

The Risk Department is responsible for deterministic risk control, risk review, portfolio risk monitoring, approval-token generation, kill-switch coordination, and explainable risk memos.

The most important rule is:

```text
No order can execute without deterministic RiskGovernor approval.
```

The RiskGovernor is not a normal LLM agent. It is a deterministic policy-as-code service. LLM reasoning may be used by supporting risk-review agents to explain, summarize, classify, or recommend, but the final risk approval/rejection decision must always come from deterministic code.

---

## Dependency

Simulation Department complete.

Required upstream evidence:

```text
Research Department
-> Strategy Creation Department
-> Simulation Department
-> Risk Department
```

Required inputs from previous departments:

- Strategy specification
- Strategy code hash
- Backtest result package
- Backtest diagnosis report
- Optimization comparison result
- Robustness result
- Statistical validation result
- Current portfolio state
- Current market state
- Current broker/account state
- Current risk configuration

---

## Agent Template Compliance

Every Risk Department agent or service must follow the HaruQuant Agent Template.

Standard execution pattern:

```text
Validate Input
-> Gather Evidence / Context
-> Optional LLM Reasoning
-> Deterministic Policy Decision
-> Structured Output
-> Audit Log
-> Evaluation Test
```

Risk-specific interpretation:

```text
LLM output = explanation or proposal
Deterministic policy = final risk decision
```

RiskGovernor must be stricter than normal agents:

```text
No optional LLM decision layer.
No free-form approval.
No silent fallback to approval.
Missing critical evidence = reject or needs_more_context.
Policy errors = fail closed.
```

---

## Standard Risk Department Folder Structure

```text
services/
  risk/
    __init__.py
    governor.py
    contracts.py
    policies.py
    thresholds.py
    calculators.py
    exposure.py
    var.py
    cvar.py
    correlation.py
    margin.py
    drawdown.py
    approval_tokens.py
    signatures.py
    exceptions.py
    audit.py
    tests/
      test_governor.py
      test_thresholds.py
      test_exposure.py
      test_var.py
      test_cvar.py
      test_correlation.py
      test_margin.py
      test_drawdown.py
      test_approval_tokens.py
      test_fail_closed.py

agents/
  risk/
    risk_reviewer_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

    portfolio_risk_monitor_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

    risk_limit_auditor_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

    risk_approval_auditor_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

config/
  risk_thresholds.yaml
  risk_policy_profiles.yaml
  risk_symbols.yaml
  correlation_clusters.yaml
```

---

## 1. Risk Department Orchestrator

## Purpose

Coordinate all Risk Department services and agents while keeping RiskGovernor as the only authority for approval/rejection.

The orchestrator receives risk-related requests, gathers required context, calls RiskGovernor when approval is required, calls explanatory agents when a human-readable memo is needed, and routes results to the CEO Agent, Planner Agent, Portfolio Department, Simulation Department, or Audit Department.

## Checklist

* [x] Create `agents/risk/risk_orchestrator_agent` or equivalent orchestration service.
* [x] Receive risk review requests from Planner Agent.
* [x] Receive trade approval requests from Portfolio / Execution Planner.
* [x] Receive strategy promotion requests from Strategy/Simulation Departments.
* [x] Validate request type.
* [x] Validate request source.
* [x] Validate permission profile.
* [x] Load current portfolio state.
* [x] Load current account state.
* [x] Load current market state.
* [x] Load strategy evidence package.
* [x] Load simulation evidence package.
* [x] Load current risk configuration.
* [x] Route execution approval requests to RiskGovernor.
* [x] Route explanatory memo requests to Risk Reviewer Agent.
* [x] Route portfolio monitoring requests to Portfolio Risk Monitor Agent.
* [x] Route config review requests to Risk Limit Auditor Agent.
* [x] Route approval-token audit requests to Risk Approval Auditor Agent.
* [x] Merge outputs into a department-level response.
* [x] Save department-level audit record.
* [x] Return structured output to Planner and CEO Agent.

## Deterministic Policy Rules

* [x] Reject requests with missing request ID.
* [x] Reject approval requests that do not include a proposal ID.
* [x] Reject execution approval requests that bypass RiskGovernor.
* [x] Reject requests with stale portfolio/account data.
* [x] Reject requests with invalid risk config hash.
* [x] Reject requests from unapproved workflow sources.
* [x] Escalate critical risk findings to Kill Switch Service.
* [x] Never allow an LLM memo to override RiskGovernor output.

## Allowed Actions

* [x] `route_to_risk_governor`
* [x] `route_to_risk_reviewer`
* [x] `route_to_portfolio_risk_monitor`
* [x] `route_to_risk_limit_auditor`
* [x] `route_to_risk_approval_auditor`
* [x] `summarize_risk_department_result`
* [x] `request_more_context`

## Blocked Actions

* [x] `approve_trade_directly`
* [x] `execute_trade`
* [x] `modify_open_position`
* [x] `override_risk_governor`
* [x] `change_risk_thresholds_without_approval`

## Output Artifacts

* [x] Risk department response.
* [x] Risk routing decision.
* [x] Risk evidence list.
* [x] RiskGovernor decision reference.
* [x] Human-readable risk memo, if requested.
* [x] Audit trail.

## Tests Required

* [x] Valid trade approval routing.
* [x] Invalid request rejection.
* [x] Missing portfolio state rejection.
* [x] Stale risk config rejection.
* [x] LLM override attempt blocked.
* [x] Critical risk routes to kill-switch escalation.

---

## 2. RiskGovernor Deterministic Service

## Purpose

Create the non-LLM hard gate for all risk approvals.

The RiskGovernor is a deterministic service that approves, modifies, rejects, or blocks proposals based on policy-as-code. It must not depend on LLM reasoning. It must fail closed.

## Required Path

```text
services/risk/governor.py
```

## Checklist

* [x] Create `services/risk/governor.py`.
* [x] Create `services/risk/contracts.py`.
* [x] Create `services/risk/policies.py`.
* [x] Create `services/risk/calculators.py`.
* [x] Create `services/risk/approval_tokens.py`.
* [x] Load `config/risk_thresholds.yaml`.
* [x] Load `config/risk_policy_profiles.yaml`.
* [x] Load `config/correlation_clusters.yaml`.
* [x] Validate risk config schema.
* [x] Validate risk config hash.
* [x] Validate proposal schema.
* [x] Validate proposal source.
* [x] Validate strategy lifecycle state.
* [x] Validate strategy approval status.
* [x] Validate account state freshness.
* [x] Validate market state freshness.
* [x] Validate portfolio state freshness.
* [x] Calculate proposed trade risk.
* [x] Calculate proposed trade R-value.
* [x] Calculate stop-loss distance.
* [x] Calculate notional exposure.
* [x] Calculate pip/tick value.
* [x] Calculate open portfolio exposure.
* [x] Calculate symbol exposure.
* [x] Calculate strategy exposure.
* [x] Calculate currency-cluster exposure.
* [x] Calculate correlated exposure.
* [x] Calculate sector/asset-class exposure where applicable.
* [x] Calculate long/short net exposure.
* [x] Calculate gross exposure.
* [x] Calculate leverage usage.
* [x] Calculate margin impact.
* [x] Calculate free-margin impact.
* [x] Calculate margin-level impact.
* [x] Calculate liquidation proximity where applicable.
* [x] Calculate VaR impact.
* [x] Calculate CVaR impact.
* [x] Calculate correlation impact.
* [x] Calculate portfolio volatility impact.
* [x] Calculate risk contribution impact.
* [x] Calculate drawdown state.
* [x] Calculate daily loss state.
* [x] Calculate weekly loss state.
* [x] Calculate monthly loss state.
* [x] Calculate strategy drawdown state.
* [x] Calculate symbol drawdown state.
* [x] Calculate current spread state.
* [x] Calculate slippage expectation.
* [x] Calculate commission impact.
* [x] Calculate swap/rollover risk.
* [x] Calculate news-event risk.
* [x] Calculate broker anomaly state.
* [x] Calculate open-order conflict risk.
* [x] Calculate duplicate signal risk.
* [x] Calculate cooldown/lockout state.
* [x] Approve, reduce, reject, or block proposal.
* [x] Return deterministic decision.
* [x] Return signed approval token only when approved or size-reduced.
* [x] Save audit record.
* [x] Fail closed on missing critical evidence.
* [x] Fail closed on policy engine errors.

## Deterministic Policy Rules

* [x] Reject if proposal has no stop-loss and strategy requires fixed risk.
* [x] Reject if proposed risk exceeds max risk per trade.
* [x] Reject if daily loss limit is reached.
* [x] Reject if weekly loss limit is reached.
* [x] Reject if monthly loss limit is reached.
* [x] Reject if portfolio drawdown exceeds policy.
* [x] Reject if strategy drawdown exceeds policy.
* [x] Reject if symbol drawdown exceeds policy.
* [x] Reject if max open positions would be exceeded.
* [x] Reject if max live strategies would be exceeded.
* [x] Reject if max symbol concentration would be exceeded.
* [x] Reject if max currency-cluster exposure would be exceeded.
* [x] Reject if max correlated exposure would be exceeded.
* [x] Reject if total margin usage would exceed policy.
* [x] Reject if margin level would fall below policy.
* [x] Reject if free margin would fall below policy.
* [x] Reject if spread exceeds policy.
* [x] Reject if slippage estimate exceeds policy.
* [x] Reject if commission/cost destroys expected edge.
* [x] Reject if swap cost violates strategy assumptions.
* [x] Reject if high-impact news block is active.
* [x] Reject if broker anomaly block is active.
* [x] Reject if kill switch is active.
* [x] Reject if proposal conflicts with open order policy.
* [x] Reject if strategy lifecycle state is not approved for live/paper execution.
* [x] Reduce size if proposal is valid but exceeds preferred risk target while still within hard limits.
* [x] Approve only if every hard rule passes.
* [x] Emit explicit rejection reasons.
* [x] Emit approved size, not requested size, when size is reduced.
* [x] Never use LLM analysis to approve or reject.

## Risk Rules

* [x] Max risk per trade.
* [x] Max daily loss.
* [x] Max weekly loss.
* [x] Max monthly loss.
* [x] Max portfolio drawdown.
* [x] Max strategy drawdown.
* [x] Max symbol drawdown.
* [x] Max symbol concentration.
* [x] Max currency-cluster exposure.
* [x] Max correlated exposure.
* [x] Max total exposure.
* [x] Max gross exposure.
* [x] Max net exposure.
* [x] Max leverage.
* [x] Max total margin usage.
* [x] Minimum free margin.
* [x] Minimum margin level.
* [x] Max open positions.
* [x] Max pending orders.
* [x] Max live strategies.
* [x] Max trades per day.
* [x] Max trades per strategy per day.
* [x] Max consecutive losses.
* [x] Max strategy cooldown violation.
* [x] Max spread.
* [x] Max slippage.
* [x] Max commission burden.
* [x] Max swap burden.
* [x] News block.
* [x] Rollover block.
* [x] Weekend/market-close block.
* [x] Broker anomaly block.
* [x] Data anomaly block.
* [x] Kill-switch block.

## Approval Token Requirements

* [x] Add `approval_id`.
* [x] Add `proposal_id`.
* [x] Add `strategy_id`.
* [x] Add `strategy_version`.
* [x] Add `symbol`.
* [x] Add `side`.
* [x] Add requested size.
* [x] Add approved size.
* [x] Add max allowed price deviation.
* [x] Add expiration time.
* [x] Add valid execution venue/broker.
* [x] Add valid account ID.
* [x] Add valid order type.
* [x] Add risk metrics snapshot.
* [x] Add portfolio state hash.
* [x] Add market state hash.
* [x] Add config version hash.
* [x] Add policy version.
* [x] Add signature/hash.
* [x] Add audit record reference.
* [x] Make token single-use.
* [x] Reject expired token.
* [x] Reject replayed token.
* [x] Reject token if proposal changes.
* [x] Reject token if market/account state is too stale.

## Output Artifacts

* [x] `risk_decision.json`.
* [x] `approval_token.json`, only when approved or reduced.
* [x] `risk_metrics_snapshot.json`.
* [x] `risk_rejection_reasons.json`.
* [x] `audit.json`.

## Tests Required

* [x] Normal approval case.
* [x] Size-reduction case.
* [x] Max risk rejection.
* [x] Daily loss rejection.
* [x] Drawdown rejection.
* [x] Margin rejection.
* [x] Correlation rejection.
* [x] Symbol concentration rejection.
* [x] Spread rejection.
* [x] News block rejection.
* [x] Broker anomaly rejection.
* [x] Kill-switch rejection.
* [x] Missing stop-loss rejection.
* [x] Missing critical evidence fail-closed case.
* [x] Invalid config hash rejection.
* [x] Expired token rejection.
* [x] Token replay rejection.
* [x] LLM cannot approve risk.

## Done Definition

No order can execute without RiskGovernor approval.

---

## 3. Portfolio Risk Monitor Agent

## Purpose

Continuously evaluate portfolio-level risk and detect unacceptable exposure, concentration, correlation, drawdown, or margin stress.

This agent may use LLM reasoning to summarize and explain portfolio conditions, but deterministic policy must produce final risk status and escalation level.

## Required Folder

```text
agents/risk/portfolio_risk_monitor_agent/
```

## Checklist

* [x] Create `agents/risk/portfolio_risk_monitor_agent`.
* [x] Read open positions.
* [x] Read pending orders.
* [x] Read account equity and balance.
* [x] Read margin, free margin, and margin level.
* [x] Read current strategy allocations.
* [x] Read symbol exposure.
* [x] Read currency exposure.
* [x] Read strategy exposure.
* [x] Read correlation clusters.
* [x] Read current drawdown state.
* [x] Read current daily/weekly/monthly loss state.
* [x] Read current VaR/CVaR estimate.
* [x] Read current volatility regime.
* [x] Read current spread and liquidity state.
* [x] Detect overconcentration.
* [x] Detect correlated exposure clusters.
* [x] Detect hidden duplicate exposure.
* [x] Detect strategy crowding.
* [x] Detect excessive margin usage.
* [x] Detect drawdown escalation.
* [x] Detect loss-limit proximity.
* [x] Detect high-risk market regime.
* [x] Detect exposure drift from intended allocation.
* [x] Detect risk budget exhaustion.
* [x] Output portfolio risk status.
* [x] Output risk escalation level.
* [x] Save portfolio risk snapshot.

## Evidence Required

* [x] Current positions.
* [x] Pending orders.
* [x] Account state.
* [x] Portfolio exposure map.
* [x] Correlation matrix or cluster map.
* [x] Risk thresholds.
* [x] Market state.
* [x] Drawdown state.
* [x] VaR/CVaR estimate.

## LLM Responsibilities

* [x] Explain portfolio risk in plain language.
* [x] Summarize exposure concentration.
* [x] Explain correlation concerns.
* [x] Explain drawdown concerns.
* [x] Suggest review topics.

## Deterministic Policy Rules

* [x] Set status `normal` if all monitored risk metrics are within policy.
* [x] Set status `watch` if any metric is within warning distance of a hard limit.
* [x] Set status `reduce_risk` if soft limits are breached.
* [x] Set status `block_new_trades` if hard limits are breached.
* [x] Set status `kill_switch_recommended` if critical limits are breached.
* [x] Never allow LLM text to downgrade risk status.
* [x] Missing account state means `needs_more_context` or `block_new_trades`.

## Allowed Actions

* [x] `summarize_portfolio_risk`
* [x] `flag_concentration_risk`
* [x] `flag_correlation_risk`
* [x] `flag_margin_risk`
* [x] `flag_drawdown_risk`
* [x] `recommend_risk_reduction_review`
* [x] `recommend_block_new_trades`
* [x] `recommend_kill_switch_escalation`

## Blocked Actions

* [x] `execute_trade`
* [x] `close_position_directly`
* [x] `approve_trade`
* [x] `override_risk_governor`
* [x] `change_risk_thresholds`

## Output Artifacts

* [x] Portfolio risk report.
* [x] Exposure map.
* [x] Correlation cluster report.
* [x] Loss-limit proximity report.
* [x] Margin stress report.
* [x] Risk escalation recommendation.
* [x] Audit metadata.

## Tests Required

* [x] Normal portfolio case.
* [x] High concentration case.
* [x] High correlation case.
* [x] Margin stress case.
* [x] Drawdown breach case.
* [x] Missing account state case.
* [x] LLM downgrade attempt blocked.

---

## 4. Risk Reviewer Agent

## Purpose

Add LLM-assisted risk explanation on top of deterministic RiskGovernor, Simulation Department, and portfolio outputs.

The Risk Reviewer explains risk decisions, summarizes evidence, identifies failure modes, and recommends reduce/hold/pause/promote actions. It does not approve trades. It does not override RiskGovernor.

## Required Folder

```text
agents/risk/risk_reviewer_agent/
```

## Checklist

* [x] Create `agents/risk/risk_reviewer_agent`.
* [x] Read strategy specification.
* [x] Read strategy code hash.
* [x] Read strategy lifecycle state.
* [x] Read research evidence.
* [x] Read backtest result package.
* [x] Read backtest diagnosis report.
* [x] Read optimization comparison result.
* [x] Read robustness result.
* [x] Read statistical validation result.
* [x] Read paper/live performance where available.
* [x] Read portfolio exposure.
* [x] Read RiskGovernor output.
* [x] Read RiskGovernor rejection reasons.
* [x] Read approval token metadata if available.
* [x] Explain key risks.
* [x] Explain rejection reasons.
* [x] Explain size-reduction reasons.
* [x] Explain portfolio impact.
* [x] Explain correlation concerns.
* [x] Explain drawdown concerns.
* [x] Explain cost concerns.
* [x] Explain robustness concerns.
* [x] Explain statistical evidence concerns.
* [x] Explain deployment readiness.
* [x] Recommend reduce, hold, pause, promote, retest, or reject.
* [x] Produce risk memo.
* [x] Save memo to evidence memory.

## Evidence Required

* [x] Strategy spec.
* [x] Simulation evidence package.
* [x] Robustness scorecard.
* [x] Statistical validation rating.
* [x] Portfolio exposure snapshot.
* [x] RiskGovernor decision.
* [x] Risk config version.
* [x] Current market/account context when relevant.

## LLM Responsibilities

* [x] Summarize risk evidence.
* [x] Explain technical risk in plain language.
* [x] Identify plausible failure modes.
* [x] Explain why RiskGovernor rejected or reduced size.
* [x] Draft risk memo.
* [x] Recommend human review topics.

## Deterministic Policy Rules

* [x] If RiskGovernor rejects, final recommendation cannot be `promote`.
* [x] If robustness failed, final recommendation cannot be `promote_to_live`.
* [x] If statistical evidence is weak, final recommendation must be `retest`, `paper_only`, or `reject`.
* [x] If portfolio risk is critical, final recommendation must be `pause` or `block_new_trades`.
* [x] If evidence package is incomplete, status must be `needs_more_context`.
* [x] If strategy code hash does not match tested code hash, status must be `rejected`.
* [x] LLM cannot override deterministic risk status.

## Risk Memo Format

* [x] Strategy summary.
* [x] Evidence reviewed.
* [x] Current lifecycle state.
* [x] Key risk metrics.
* [x] RiskGovernor decision.
* [x] Rejection or reduction reasons.
* [x] Portfolio impact.
* [x] Correlation concerns.
* [x] Drawdown concerns.
* [x] Cost concerns.
* [x] Robustness concerns.
* [x] Statistical evidence concerns.
* [x] Failure modes.
* [x] Recommendation.
* [x] Required Board action, if any.
* [x] Required next tests, if any.
* [x] Evidence references.
* [x] Audit metadata.

## Allowed Actions

* [x] `explain_risk_decision`
* [x] `produce_risk_memo`
* [x] `recommend_reduce`
* [x] `recommend_hold`
* [x] `recommend_pause`
* [x] `recommend_retest`
* [x] `recommend_promote_for_review`

## Blocked Actions

* [x] `approve_trade`
* [x] `execute_trade`
* [x] `override_risk_governor`
* [x] `modify_position_size_directly`
* [x] `change_risk_thresholds`

## Output Artifacts

* [x] `risk_memo.md`.
* [x] `risk_summary.json`.
* [x] `risk_recommendation.json`.
* [x] `evidence_refs.json`.
* [x] `audit.json`.

## Tests Required

* [x] Approved RiskGovernor output explanation.
* [x] Rejected RiskGovernor output explanation.
* [x] Robustness failure blocks promote.
* [x] Weak statistical evidence blocks live deployment.
* [x] Code hash mismatch rejection.
* [x] Missing evidence needs more context.
* [x] LLM override attempt blocked.

## Done Definition

Risk decisions become understandable, auditable, and explainable.

---

## 5. Risk Limit Auditor Agent

## Purpose

Review risk configuration files and confirm that the configured limits are valid, internally consistent, versioned, and aligned with the current trading environment.

This agent does not decide trade approvals. It checks the quality and safety of risk configuration.

## Required Folder

```text
agents/risk/risk_limit_auditor_agent/
```

## Checklist

* [x] Create `agents/risk/risk_limit_auditor_agent`.
* [x] Read `config/risk_thresholds.yaml`.
* [x] Read `config/risk_policy_profiles.yaml`.
* [x] Read `config/correlation_clusters.yaml`.
* [x] Validate config schema.
* [x] Validate config hash.
* [x] Validate version fields.
* [x] Validate threshold units.
* [x] Validate threshold ranges.
* [x] Validate hard limit vs soft limit consistency.
* [x] Validate strategy-specific overrides.
* [x] Validate symbol-specific overrides.
* [x] Validate account-specific overrides.
* [x] Validate correlation cluster definitions.
* [x] Validate margin policy.
* [x] Validate drawdown policy.
* [x] Validate cost policy.
* [x] Validate news/rollover block policy.
* [x] Validate kill-switch trigger policy.
* [x] Detect missing limits.
* [x] Detect contradictory limits.
* [x] Detect dangerously permissive limits.
* [x] Detect stale config versions.
* [x] Output risk config audit report.

## Evidence Required

* [x] Risk thresholds file.
* [x] Risk profile file.
* [x] Symbol risk metadata.
* [x] Correlation cluster config.
* [x] Current account/broker constraints.
* [x] Current strategy universe.

## LLM Responsibilities

* [x] Explain policy risks.
* [x] Summarize risky configuration choices.
* [x] Draft improvement recommendations.

## Deterministic Policy Rules

* [x] Reject config if required thresholds are missing.
* [x] Reject config if hard limits are weaker than soft limits.
* [x] Reject config if risk-per-trade limit is invalid.
* [x] Reject config if drawdown limits are invalid.
* [x] Reject config if margin limits are invalid.
* [x] Reject config if config hash does not match approved version.
* [x] Mark config as `needs_review` if thresholds are valid but unusually permissive.
* [x] Mark config as `approved_for_use` only if all required checks pass.

## Allowed Actions

* [x] `audit_risk_config`
* [x] `flag_invalid_thresholds`
* [x] `flag_missing_limits`
* [x] `recommend_policy_review`

## Blocked Actions

* [x] `approve_trade`
* [x] `execute_trade`
* [x] `change_config_directly`
* [x] `override_risk_governor`

## Output Artifacts

* [x] Risk config audit report.
* [x] Config validation result.
* [x] Config hash record.
* [x] Required fixes list.
* [x] Audit metadata.

## Tests Required

* [x] Valid config passes.
* [x] Missing threshold fails.
* [x] Invalid units fail.
* [x] Contradictory hard/soft limits fail.
* [x] Dangerous permissive config needs review.
* [x] Invalid config hash fails.

---

## 6. Risk Approval Auditor Agent

## Purpose

Audit approval tokens and confirm that execution requests match valid, unexpired, single-use RiskGovernor approvals.

This agent helps the Portfolio Department verify that execution is authorized.

## Required Folder

```text
agents/risk/risk_approval_auditor_agent/
```

## Checklist

* [x] Create `agents/risk/risk_approval_auditor_agent`.
* [x] Read approval token.
* [x] Validate token schema.
* [x] Validate approval ID.
* [x] Validate proposal ID.
* [x] Validate strategy ID.
* [x] Validate symbol.
* [x] Validate side.
* [x] Validate approved size.
* [x] Validate expiration time.
* [x] Validate signature/hash.
* [x] Validate config version hash.
* [x] Validate policy version.
* [x] Validate market/account state freshness.
* [x] Validate token is unused.
* [x] Validate execution request matches approved token.
* [x] Reject token replay.
* [x] Reject expired token.
* [x] Reject modified proposal.
* [x] Reject unapproved size increase.
* [x] Reject wrong symbol/side/account/broker.
* [x] Output token audit result.
* [x] Save token usage audit.

## Evidence Required

* [x] Approval token.
* [x] Original risk proposal.
* [x] Execution request.
* [x] RiskGovernor audit record.
* [x] Token usage store.
* [x] Current market/account state.

## LLM Responsibilities

* [x] None required for approval validation.
* [x] Optional: explain token rejection reasons in human-readable form.

## Deterministic Policy Rules

* [x] Reject if token is missing.
* [x] Reject if token schema is invalid.
* [x] Reject if token expired.
* [x] Reject if token already used.
* [x] Reject if signature/hash is invalid.
* [x] Reject if execution request differs from approval token.
* [x] Reject if execution size exceeds approved size.
* [x] Reject if symbol/side/account/broker differs.
* [x] Reject if market/account state is too stale.
* [x] Accept only if every token validation check passes.

## Allowed Actions

* [x] `validate_approval_token`
* [x] `mark_token_used`
* [x] `reject_invalid_token`
* [x] `explain_token_result`

## Blocked Actions

* [x] `approve_trade_without_token`
* [x] `execute_trade`
* [x] `change_approved_size`
* [x] `extend_token_expiry_without_risk_governor`

## Output Artifacts

* [x] Token validation result.
* [x] Token usage audit.
* [x] Execution authorization status.
* [x] Rejection reasons.
* [x] Audit metadata.

## Tests Required

* [x] Valid token accepted.
* [x] Expired token rejected.
* [x] Replay token rejected.
* [x] Wrong symbol rejected.
* [x] Wrong size rejected.
* [x] Wrong account rejected.
* [x] Invalid signature rejected.
* [x] Modified proposal rejected.

---

## 7. Drawdown Control Service

## Purpose

Track portfolio, strategy, symbol, and session drawdowns and enforce deterministic drawdown-based lockouts.

This may be a pure service under `risk/` rather than an LLM-capable agent.

## Required Path

```text
risk/drawdown.py
```

## Checklist

* [x] Create `risk/drawdown.py`.
* [x] Track account equity peak.
* [x] Track portfolio drawdown.
* [x] Track strategy drawdown.
* [x] Track symbol drawdown.
* [x] Track daily drawdown.
* [x] Track weekly drawdown.
* [x] Track monthly drawdown.
* [x] Track rolling-window drawdown.
* [x] Track consecutive loss count.
* [x] Track loss streak by strategy.
* [x] Track loss streak by symbol.
* [x] Detect soft drawdown warning.
* [x] Detect hard drawdown breach.
* [x] Trigger strategy cooldown.
* [x] Trigger symbol cooldown.
* [x] Trigger portfolio new-trade block.
* [x] Trigger kill-switch recommendation.
* [x] Save drawdown state snapshot.

## Deterministic Policy Rules

* [x] Warn when drawdown exceeds soft threshold.
* [x] Block strategy when strategy drawdown exceeds hard threshold.
* [x] Block symbol when symbol drawdown exceeds hard threshold.
* [x] Block new trades when portfolio drawdown exceeds hard threshold.
* [x] Recommend kill switch when critical drawdown threshold is breached.
* [x] Reset daily state only after configured daily reset time.
* [x] Do not reset strategy drawdown without lifecycle approval.

## Output Artifacts

* [x] Drawdown state snapshot.
* [x] Drawdown breach report.
* [x] Cooldown state.
* [x] Audit metadata.

## Tests Required

* [x] Normal drawdown case.
* [x] Soft warning case.
* [x] Hard strategy breach case.
* [x] Hard portfolio breach case.
* [x] Daily reset behavior.
* [x] Consecutive loss lockout.

---

## 8. VaR and CVaR Risk Service

## Purpose

Compute historical and Monte Carlo VaR/CVaR for the open portfolio and proposed trades.

This service supports RiskGovernor and Portfolio Risk Monitor.

## Required Path

```text
services/risk/var.py
services/risk/cvar.py
```

## Checklist

* [x] Create `services/risk/var.py`.
* [x] Create `services/risk/cvar.py`.
* [x] Read open positions.
* [x] Read symbol returns.
* [x] Read rolling volatility.
* [x] Read rolling correlations.
* [x] Calculate position nominal values.
* [x] Calculate portfolio weights.
* [x] Build covariance matrix.
* [x] Calculate portfolio standard deviation.
* [x] Calculate historical VaR.
* [x] Calculate historical CVaR.
* [x] Calculate Monte Carlo VaR.
* [x] Calculate Monte Carlo CVaR.
* [x] Calculate incremental VaR for proposed trade.
* [x] Calculate incremental CVaR for proposed trade.
* [x] Calculate marginal risk contribution.
* [x] Calculate component risk contribution.
* [x] Flag VaR threshold breach.
* [x] Flag CVaR threshold breach.
* [x] Save VaR/CVaR snapshot.

## Deterministic Policy Rules

* [x] Reject VaR calculation if required return data is missing.
* [x] Reject calculation if covariance matrix is invalid.
* [x] Use conservative fallback if Monte Carlo fails.
* [x] Treat stale correlation data as high risk.
* [x] Block proposed trade if incremental VaR exceeds policy.
* [x] Block proposed trade if incremental CVaR exceeds policy.

## Output Artifacts

* [x] VaR snapshot.
* [x] CVaR snapshot.
* [x] Incremental risk report.
* [x] Risk contribution report.
* [x] Audit metadata.

## Tests Required

* [x] Historical VaR calculation.
* [x] Monte Carlo VaR calculation.
* [x] CVaR calculation.
* [x] Incremental VaR test.
* [x] Missing returns rejection.
* [x] Invalid covariance rejection.
* [x] Stale data high-risk flag.

---

## 9. Correlation and Concentration Risk Service

## Purpose

Control duplicate exposure and correlation clusters, especially for FX baskets and USD-linked symbols.

## Required Path

```text
services/risk/correlation.py
services/risk/exposure.py
```

## Checklist

* [x] Create `services/risk/correlation.py`.
* [x] Create `services/risk/exposure.py`.
* [x] Read open positions.
* [x] Read pending orders.
* [x] Read symbol metadata.
* [x] Read currency metadata.
* [x] Read correlation matrix.
* [x] Read correlation cluster config.
* [x] Calculate symbol exposure.
* [x] Calculate currency exposure.
* [x] Calculate strategy exposure.
* [x] Calculate account exposure.
* [x] Calculate cluster exposure.
* [x] Calculate correlated exposure.
* [x] Calculate net and gross exposure.
* [x] Calculate synthetic exposure.
* [x] Detect duplicate USD exposure.
* [x] Detect duplicate JPY/CHF safe-haven exposure.
* [x] Detect commodity-currency clustering.
* [x] Detect multi-strategy crowding.
* [x] Detect same-symbol overconcentration.
* [x] Detect same-direction portfolio crowding.
* [x] Calculate proposed trade exposure impact.
* [x] Save exposure snapshot.

## Deterministic Policy Rules

* [x] Reject if symbol exposure exceeds threshold.
* [x] Reject if currency-cluster exposure exceeds threshold.
* [x] Reject if correlated exposure exceeds threshold.
* [x] Reject if proposed trade increases exposure in an already stressed cluster.
* [x] Reject if correlation data is stale and exposure is already high.
* [x] Size-reduce if exposure is acceptable only at smaller volume.

## Output Artifacts

* [x] Exposure snapshot.
* [x] Correlation cluster report.
* [x] Concentration risk report.
* [x] Proposed trade exposure impact.
* [x] Audit metadata.

## Tests Required

* [x] Single-symbol concentration breach.
* [x] Currency-cluster breach.
* [x] Correlated exposure breach.
* [x] Duplicate USD exposure detection.
* [x] Size reduction based on exposure.
* [x] Stale correlation data high-risk case.

---

## 10. Margin and Broker Risk Service

## Purpose

Ensure proposed and open trades do not create unsafe margin usage or broker-execution risk.

## Required Path

```text
services/risk/margin.py
services/risk/broker_risk.py
```

## Checklist

* [x] Create `services/risk/margin.py`.
* [x] Create `services/risk/broker_risk.py`.
* [x] Read account balance.
* [x] Read account equity.
* [x] Read used margin.
* [x] Read free margin.
* [x] Read margin level.
* [x] Read broker leverage rules.
* [x] Read symbol margin requirements.
* [x] Read contract size.
* [x] Read current spread.
* [x] Read current slippage estimate.
* [x] Read broker execution state.
* [x] Calculate required margin for proposal.
* [x] Calculate post-trade used margin.
* [x] Calculate post-trade free margin.
* [x] Calculate post-trade margin level.
* [x] Calculate liquidation/stopping-out proximity.
* [x] Detect broker disconnection.
* [x] Detect abnormal spread.
* [x] Detect abnormal slippage.
* [x] Detect stale price feed.
* [x] Detect rejected-order spike.
* [x] Detect execution latency anomaly.
* [x] Output broker and margin risk status.

## Deterministic Policy Rules

* [x] Reject if margin requirement cannot be calculated.
* [x] Reject if post-trade margin level is below threshold.
* [x] Reject if post-trade free margin is below threshold.
* [x] Reject if broker connection is unhealthy.
* [x] Reject if price feed is stale.
* [x] Reject if spread exceeds policy.
* [x] Reject if slippage exceeds policy.
* [x] Reject if broker anomaly block is active.
* [x] Size-reduce if margin is acceptable only at smaller volume.

## Output Artifacts

* [x] Margin impact report.
* [x] Broker risk report.
* [x] Execution-safety status.
* [x] Audit metadata.

## Tests Required

* [x] Normal margin case.
* [x] Low free-margin rejection.
* [x] Low margin-level rejection.
* [x] Broker disconnect rejection.
* [x] Stale price rejection.
* [x] Spread anomaly rejection.
* [x] Slippage anomaly rejection.

---

## 11. Risk Configuration Schemas

## Purpose

Define the standard risk configuration files and required fields.

## `config/risk_thresholds.yaml`

Required fields:

* [x] `config_version`.
* [x] `config_hash`.
* [x] `approved_by`.
* [x] `approved_at`.
* [x] `account_profile`.
* [x] `max_risk_per_trade_pct`.
* [x] `max_daily_loss_pct`.
* [x] `max_weekly_loss_pct`.
* [x] `max_monthly_loss_pct`.
* [x] `max_portfolio_drawdown_pct`.
* [x] `max_strategy_drawdown_pct`.
* [x] `max_symbol_drawdown_pct`.
* [x] `max_symbol_exposure_pct`.
* [x] `max_currency_cluster_exposure_pct`.
* [x] `max_correlated_exposure_pct`.
* [x] `max_total_margin_usage_pct`.
* [x] `min_free_margin_pct`.
* [x] `min_margin_level_pct`.
* [x] `max_open_positions`.
* [x] `max_pending_orders`.
* [x] `max_live_strategies`.
* [x] `max_trades_per_day`.
* [x] `max_consecutive_losses`.
* [x] `max_spread_pips_by_symbol`.
* [x] `max_slippage_pips_by_symbol`.
* [x] `news_block_minutes_before`.
* [x] `news_block_minutes_after`.
* [x] `rollover_block_minutes_before`.
* [x] `rollover_block_minutes_after`.
* [x] `approval_token_ttl_seconds`.
* [x] `kill_switch_thresholds`.

## `config/risk_policy_profiles.yaml`

Required profiles:

* [x] `research_only`.
* [x] `backtest_only`.
* [x] `paper_trading`.
* [x] `small_live`.
* [x] `standard_live`.
* [x] `restricted_mode`.
* [x] `emergency_mode`.

## `config/correlation_clusters.yaml`

Required fields:

* [x] `cluster_id`.
* [x] `cluster_name`.
* [x] `symbols`.
* [x] `currencies`.
* [x] `max_cluster_exposure_pct`.
* [x] `correlation_threshold`.
* [x] `notes`.

---

## 12. Risk Proposal Schema

## Purpose

Define the standard proposal format that any strategy, execution planner, or portfolio service must submit to RiskGovernor.

Required fields:

* [x] `proposal_id`.
* [x] `proposal_type`.
* [x] `source_department`.
* [x] `source_agent`.
* [x] `strategy_id`.
* [x] `strategy_name`.
* [x] `strategy_version`.
* [x] `strategy_code_hash`.
* [x] `strategy_lifecycle_state`.
* [x] `symbol`.
* [x] `asset_class`.
* [x] `timeframe`.
* [x] `side`.
* [x] `order_type`.
* [x] `requested_volume`.
* [x] `requested_price`.
* [x] `stop_loss`.
* [x] `take_profit`.
* [x] `expected_entry_time`.
* [x] `expected_holding_period`.
* [x] `setup_id`.
* [x] `group_id`.
* [x] `risk_model`.
* [x] `strategy_risk_controls`.
* [x] `evidence_refs`.
* [x] `context_revision`.
* [x] `created_at`.

---

## 13. Risk Decision Schema

## Purpose

Define the standard deterministic RiskGovernor output.

Required fields:

* [x] `decision_id`.
* [x] `proposal_id`.
* [x] `status`:
  * [x] `approved`
  * [x] `approved_with_reduced_size`
  * [x] `rejected`
  * [x] `blocked`
  * [x] `needs_more_context`
  * [x] `error_fail_closed`
* [x] `requested_volume`.
* [x] `approved_volume`.
* [x] `risk_level`.
* [x] `risk_metrics_snapshot`.
* [x] `rules_checked`.
* [x] `rules_passed`.
* [x] `rules_failed`.
* [x] `rejection_reasons`.
* [x] `warnings`.
* [x] `required_actions`.
* [x] `approval_token_ref`.
* [x] `config_version_hash`.
* [x] `policy_version`.
* [x] `created_at`.
* [x] `expires_at`.
* [x] `audit_ref`.

---

## 14. Risk Approval Token Schema

## Purpose

Define the signed token required before execution can happen.

Required fields:

* [x] `approval_id`.
* [x] `decision_id`.
* [x] `proposal_id`.
* [x] `strategy_id`.
* [x] `strategy_code_hash`.
* [x] `symbol`.
* [x] `side`.
* [x] `order_type`.
* [x] `requested_volume`.
* [x] `approved_volume`.
* [x] `max_price_deviation`.
* [x] `account_id`.
* [x] `broker_id`.
* [x] `valid_from`.
* [x] `expires_at`.
* [x] `single_use`.
* [x] `used_at`.
* [x] `risk_metrics_snapshot`.
* [x] `portfolio_state_hash`.
* [x] `market_state_hash`.
* [x] `config_version_hash`.
* [x] `policy_version`.
* [x] `signature`.
* [x] `audit_ref`.

---

## 15. Risk Memo Schema

## Purpose

Define the standard output produced by the Risk Reviewer Agent.

Required fields:

* [x] `memo_id`.
* [x] `strategy_id`.
* [x] `strategy_name`.
* [x] `strategy_lifecycle_state`.
* [x] `risk_governor_decision_ref`.
* [x] `evidence_reviewed`.
* [x] `risk_summary`.
* [x] `key_risk_metrics`.
* [x] `portfolio_impact`.
* [x] `correlation_concerns`.
* [x] `drawdown_concerns`.
* [x] `cost_concerns`.
* [x] `margin_concerns`.
* [x] `robustness_concerns`.
* [x] `statistical_concerns`.
* [x] `failure_modes`.
* [x] `recommendation`.
* [x] `required_board_action`.
* [x] `required_next_steps`.
* [x] `confidence`.
* [x] `evidence_refs`.
* [x] `audit`.

---

## 16. Risk Scoring System

## Purpose

Create a consistent scoring layer for risk review and reporting. This does not replace hard risk rules. It supports ranking, explanations, and portfolio review.

Recommended scores:

* [x] `trade_risk_score`.
* [x] `portfolio_impact_score`.
* [x] `margin_stress_score`.
* [x] `drawdown_pressure_score`.
* [x] `correlation_risk_score`.
* [x] `concentration_risk_score`.
* [x] `cost_risk_score`.
* [x] `execution_risk_score`.
* [x] `news_risk_score`.
* [x] `broker_risk_score`.
* [x] `strategy_evidence_score`.
* [x] `overall_risk_score`.

Suggested formula:

```text
overall_risk_score =
    0.15 * trade_risk_score
  + 0.15 * portfolio_impact_score
  + 0.10 * margin_stress_score
  + 0.10 * drawdown_pressure_score
  + 0.15 * correlation_risk_score
  + 0.10 * concentration_risk_score
  + 0.10 * cost_risk_score
  + 0.10 * execution_risk_score
  + 0.05 * news_risk_score
```

Risk scoring rules:

* [x] Scoring supports explanation only.
* [x] Hard rule breaches override scores.
* [x] A low score cannot approve a proposal that fails a hard limit.
* [x] Missing critical evidence increases risk score.
* [x] LLM cannot directly set score values unless validated by deterministic code.

---

## 17. Risk-to-Execution Handoff Contract

## Purpose

Define the only valid way for the Portfolio Department to receive approval to execute.

Required handoff fields:

* [x] `handoff_id`.
* [x] `proposal_id`.
* [x] `risk_decision_id`.
* [x] `approval_token`.
* [x] `approved_order_details`.
* [x] `approved_volume`.
* [x] `approved_symbol`.
* [x] `approved_side`.
* [x] `approved_order_type`.
* [x] `max_price_deviation`.
* [x] `expiration_time`.
* [x] `required_pre_execution_checks`.
* [x] `blocked_actions`.
* [x] `audit_ref`.

Execution rules:

* [x] Portfolio Execution Bridge must validate approval token before sending order.
* [x] Portfolio Execution Bridge must reject expired token.
* [x] Portfolio Execution Bridge must reject replayed token.
* [x] Portfolio Execution Bridge must reject modified order details.
* [x] Portfolio Execution Bridge must reject size above approved volume.
* [x] Portfolio Execution Bridge must reject if kill switch is active.
* [x] Portfolio Execution Bridge must write execution result back to audit.

---

## 18. Risk-to-Simulation Handoff Contract

## Purpose

Feed risk findings back into Simulation Department for future testing and strategy improvement.

Required fields:

* [x] `strategy_id`.
* [x] `risk_rejection_reasons`.
* [x] `risk_reviewer_memo_ref`.
* [x] `required_additional_tests`.
* [x] `cost_sensitivity_required`.
* [x] `spread_stress_required`.
* [x] `slippage_stress_required`.
* [x] `correlation_stress_required`.
* [x] `drawdown_stress_required`.
* [x] `position_size_sensitivity_required`.
* [x] `recommended_parameter_constraints`.

---

## 19. Risk-to-Strategy Handoff Contract

## Purpose

Feed risk concerns back into Strategy Creation Department so strategy specs and code can be improved.

Required fields:

* [x] `strategy_id`.
* [x] `strategy_version`.
* [x] `risk_concerns`.
* [x] `required_spec_changes`.
* [x] `required_position_sizing_changes`.
* [x] `required_stop_loss_changes`.
* [x] `required_exposure_controls`.
* [x] `required_session_filters`.
* [x] `required_news_filters`.
* [x] `required_cost_assumption_changes`.
* [x] `required_stateful_strategy_limits`.
* [x] `retest_required`.

---

## 20. Standard Permissions Model

## Department-Level Permissions

Risk Department permissions:

```python
RISK_DEPARTMENT_PERMISSIONS = {
    "can_read_strategy_evidence": True,
    "can_read_backtest_results": True,
    "can_read_robustness_results": True,
    "can_read_statistical_validation": True,
    "can_read_portfolio": True,
    "can_read_account_state": True,
    "can_read_market_state": True,
    "can_read_risk_config": True,
    "can_create_approval_token": True,      # RiskGovernor only
    "can_approve_risk": True,              # RiskGovernor only
    "can_execute_trade": False,
    "can_modify_position": False,
    "can_override_execution": False,
    "can_modify_risk_config": False,
}
```

Agent-specific permissions:

| Component | Can Approve Risk? | Can Create Approval Token? | Can Explain Risk? | Can Execute Trades? | Can Modify Config? |
|---|---:|---:|---:|---:|---:|
| RiskGovernor | Yes | Yes | Limited | No | No |
| Portfolio Risk Monitor Agent | No | No | Yes | No | No |
| Risk Reviewer Agent | No | No | Yes | No | No |
| Risk Limit Auditor Agent | No | No | Yes | No | No |
| Risk Approval Auditor Agent | No | No | Limited | No | No |
| Drawdown Control Service | No | No | No | No | No |
| VaR/CVaR Service | No | No | No | No | No |
| Correlation/Exposure Service | No | No | No | No | No |
| Margin/Broker Risk Service | No | No | No | No | No |

---

## 21. Standard Audit Requirements

Every Risk Department output must include:

* [x] `request_id`.
* [x] `component_name`.
* [x] `component_type`.
* [x] `start_time`.
* [x] `end_time`.
* [x] `input_validation_status`.
* [x] `proposal_id`.
* [x] `strategy_id`.
* [x] `strategy_code_hash`.
* [x] `risk_config_hash`.
* [x] `policy_version`.
* [x] `tools_called`.
* [x] `evidence_refs`.
* [x] `rules_checked`.
* [x] `rules_failed`.
* [x] `decision`.
* [x] `risk_level`.
* [x] `approved_volume`.
* [x] `approval_token_ref`.
* [x] `blocked_actions`.
* [x] `fallback_used`.
* [x] `error_if_any`.
* [x] `signature/hash`.

Audit rules:

* [x] Audit must be machine-readable.
* [x] Audit must not contain secrets.
* [x] RiskGovernor audit must be immutable.
* [x] Approval-token audit must record single-use state.
* [x] Rejections must include explicit reasons.
* [x] Fail-closed errors must be clearly marked.

---

## 22. Standard Test Requirements

Every Risk Department agent must include:

```text
test_contracts.py
test_deterministic_policy.py
test_service.py
test_agent_smoke.py
```

RiskGovernor and pure risk services must include direct service-level tests:

```text
test_governor.py
test_thresholds.py
test_exposure.py
test_var.py
test_cvar.py
test_correlation.py
test_margin.py
test_drawdown.py
test_approval_tokens.py
test_fail_closed.py
```

Required risk test categories:

* [x] Normal case.
* [x] Missing evidence case.
* [x] Invalid schema case.
* [x] Invalid config hash case.
* [x] Soft limit warning case.
* [x] Hard limit rejection case.
* [x] Critical limit kill-switch case.
* [x] Size-reduction case.
* [x] LLM override attempt case.
* [x] Token expiration case.
* [x] Token replay case.
* [x] Stale market state case.
* [x] Stale account state case.
* [x] Broker anomaly case.
* [x] Fail-closed error case.

---

## 23. Recommended Build Order

Build in this order:

```text
1. Risk shared contracts
2. Risk config schemas
3. Risk threshold loader and config hash validator
4. Exposure service
5. Margin service
6. Drawdown service
7. Correlation service
8. VaR/CVaR service
9. Approval token service
10. RiskGovernor deterministic service
11. Risk Approval Auditor Agent
12. Portfolio Risk Monitor Agent
13. Risk Reviewer Agent
14. Risk Limit Auditor Agent
15. Risk Department Orchestrator
16. Portfolio Department handoff integration
17. CEO/Planner routing integration
18. Full audit and fail-closed tests
```

---

## 24. Department Done Definition

The Risk Department is complete only when:

```text
1. RiskGovernor exists as a deterministic non-LLM service.
2. Risk thresholds are loaded from versioned config.
3. Risk config hash is validated.
4. Proposed trades are evaluated against hard risk limits.
5. Portfolio exposure is calculated.
6. Symbol exposure is calculated.
7. Currency-cluster exposure is calculated.
8. Margin impact is calculated.
9. VaR/CVaR impact is calculated.
10. Correlation impact is calculated.
11. Drawdown and loss-limit state are calculated.
12. RiskGovernor can approve, reduce, reject, block, or fail closed.
13. Signed approval tokens are generated only after approval.
14. Execution cannot proceed without a valid token.
15. Expired/replayed/modified tokens are rejected.
16. Risk Reviewer can explain decisions without overriding them.
17. Portfolio Risk Monitor can detect escalating portfolio risk.
18. Risk Limit Auditor can validate risk configs.
19. All outputs include audit metadata.
20. All components have deterministic tests.
21. LLM output cannot override deterministic risk policy.
22. Critical errors fail closed.
```

---

## 25. Final Architecture Rule

```text
RiskGovernor is not an opinion agent.
RiskGovernor is the hard deterministic risk gate.
Risk Reviewer explains.
Portfolio Risk Monitor observes.
Risk Limit Auditor checks policy quality.
Risk Approval Auditor verifies execution authorization.
Portfolio Execution Bridge obeys only valid RiskGovernor approval tokens.
```





