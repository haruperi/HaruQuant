# HaruQuant Live Trading Activation and Operating Cycle

**Purpose:** Define the controlled workflow for moving a strategy from research/simulation/paper trading into micro-live or limited-live deployment, and define the daily, weekly, and monthly operating cycle for running HaruQuant as an agentic trading firm.

**Document type:** Governed Workflow Specification

**Applies to:** CEO Agent, internal Planner, Research Department, Strategy Creation Department, Simulation Department, Risk Department, Portfolio Department, UI Integration, Board Room, Order Router, Kill Switch, Audit, Cost, Paper Trading, and Live Execution.

---

## 1. Goal

Allow controlled live deployment only after:

- Research evidence exists.
- Strategy specification is complete.
- Strategy code is reviewed.
- Backtests are reproducible.
- Robustness testing is passed.
- Statistical validation is acceptable.
- Paper trading performance is sufficient.
- Risk review is complete.
- Portfolio review is complete.
- Broker readiness is verified.
- Kill switch is healthy.
- Audit logging is healthy.
- Board approval is granted.
- Live configuration is updated through a governed path.

A strategy must never go live because of agent enthusiasm, promising backtest metrics, or a single attractive report. Live trading requires a complete evidence chain, deterministic risk checks, and human approval.

---

## 2. Core Governance Rules

### 2.1 CEO-first workflow rule

- [ ] Live activation requests must originate through the CEO workflow.
- [ ] The UI must not directly activate live trading.
- [ ] Specialist agents may provide evidence only.
- [ ] Internal Planner may route work, but only inside CEO.
- [ ] CEO prepares the final activation memo.
- [ ] Board Room displays the approval package.
- [ ] Final activation requires human approval.

### 2.2 RiskGovernor-first execution rule

- [ ] No live order can execute without RiskGovernor approval.
- [ ] No live order can execute without a valid approval token.
- [ ] No live strategy can generate executable orders unless live mode is enabled.
- [ ] No strategy can bypass Order Router.
- [ ] No agent can bypass RiskGovernor.
- [ ] No UI action can bypass server-side governed checks.
- [ ] No LLM output can approve live trading.
- [ ] RiskGovernor must fail closed.

### 2.3 Evidence-chain rule

Every live activation request must link to:

- [ ] Research report.
- [ ] Strategy specification.
- [ ] Strategy code version.
- [ ] Strategy review.
- [ ] Backtest result package.
- [ ] Backtest diagnosis.
- [ ] Optimization comparison if optimization was used.
- [ ] Robustness report.
- [ ] Statistical validation report.
- [ ] Paper trading report.
- [ ] Risk memo.
- [ ] Portfolio memo.
- [ ] Broker readiness report.
- [ ] Audit preflight report.
- [ ] Cost impact report if relevant.

### 2.4 Activation-stage rule

Live deployment must be staged:

```text
research
→ spec
→ code_reviewed
→ backtested
→ robustness_tested
→ statistically_validated
→ admitted_to_paper
→ paper_trading
→ micro_live_candidate
→ micro_live
→ limited_live_candidate
→ limited_live
→ full_live_candidate
→ full_live
```

Recommended default:

```text
No strategy jumps directly from paper to full live.
```

---

## 3. Live Activation Request Schema

### 3.1 Purpose

The `LiveActivationRequest` is the governed package used to request micro-live, limited-live, or full-live activation.

### 3.2 Checklist

- [ ] Create `LiveActivationRequest` schema.
- [ ] Add `request_id`.
- [ ] Add `created_at`.
- [ ] Add `created_by`.
- [ ] Add `requested_stage`.
- [ ] Add `strategy_id`.
- [ ] Add `strategy_name`.
- [ ] Add `strategy_version`.
- [ ] Add `strategy_spec_id`.
- [ ] Add `strategy_spec_version`.
- [ ] Add `strategy_code_hash`.
- [ ] Add `strategy_code_version`.
- [ ] Add `strategy_family`.
- [ ] Add `strategy_type`.
- [ ] Add `symbol`.
- [ ] Add `timeframe`.
- [ ] Add `approved_symbols`.
- [ ] Add `approved_timeframes`.
- [ ] Add `broker_account_id`.
- [ ] Add `broker_name`.
- [ ] Add `execution_bridge`.
- [ ] Add `requested_allocation`.
- [ ] Add `requested_max_risk_per_trade`.
- [ ] Add `requested_max_daily_loss`.
- [ ] Add `requested_max_drawdown`.
- [ ] Add `requested_max_open_positions`.
- [ ] Add `requested_max_margin_usage`.
- [ ] Add `requested_max_symbol_exposure`.
- [ ] Add `requested_max_correlated_exposure`.
- [ ] Add `allowed_sessions`.
- [ ] Add `blocked_sessions`.
- [ ] Add `news_blackout_rules`.
- [ ] Add `spread_limit`.
- [ ] Add `slippage_limit`.
- [ ] Add `kill_switch_status`.
- [ ] Add `broker_readiness_status`.
- [ ] Add `audit_readiness_status`.
- [ ] Add `risk_governor_status`.
- [ ] Add `portfolio_status`.
- [ ] Add `cost_status`.
- [ ] Add `approval_expiration`.
- [ ] Add `evidence_pack_id`.
- [ ] Add `risk_memo_id`.
- [ ] Add `portfolio_memo_id`.
- [ ] Add `ceo_memo_id`.
- [ ] Add `board_approval_id`.
- [ ] Add `status`.
- [ ] Add `rejection_reason`.
- [ ] Add `audit_refs`.

### 3.3 Recommended schema example

```yaml
request_id: lar_2026_000001
created_at: "2026-05-07T00:00:00Z"
created_by: ceo_agent
requested_stage: micro_live
strategy:
  strategy_id: strat_eurusd_h1_mean_reversion
  strategy_name: EURUSD_H1_MeanReversion
  strategy_version: "1.0.0"
  strategy_spec_id: spec_2026_000019
  strategy_spec_version: "1.0"
  strategy_code_hash: sha256:...
  strategy_code_version: code_2026_000044
  strategy_family: mean_reversion
  strategy_type: simple
market_scope:
  symbols:
    - EURUSD
  timeframes:
    - H1
  allowed_sessions:
    - london
    - new_york
  blocked_sessions:
    - rollover
requested_limits:
  allocation: 1000.0
  max_risk_per_trade: 0.0025
  max_daily_loss: 0.005
  max_strategy_drawdown: 0.03
  max_open_positions: 1
  max_margin_usage: 0.10
  spread_limit_pips: 2.0
  slippage_limit_pips: 1.5
evidence:
  research_report_id: rr_...
  strategy_review_id: sr_...
  backtest_run_id: bt_...
  robustness_report_id: rb_...
  statistical_validation_id: sv_...
  paper_report_id: pp_...
  risk_memo_id: rm_...
  portfolio_memo_id: pm_...
preflight:
  kill_switch_status: healthy
  broker_readiness_status: healthy
  audit_readiness_status: healthy
  risk_governor_status: healthy
approval:
  board_approval_id: null
  approval_expiration: "2026-06-07T00:00:00Z"
status: pending_board_approval
```

---

## 4. Live Activation Evidence Pack

### 4.1 Purpose

The evidence pack is the immutable bundle reviewed before live activation.

### 4.2 Checklist

- [ ] Create `LiveActivationEvidencePack` schema.
- [ ] Include strategy summary.
- [ ] Include research evidence.
- [ ] Include strategy specification.
- [ ] Include strategy code review.
- [ ] Include no-lookahead confirmation.
- [ ] Include backtest evidence.
- [ ] Include backtest reproducibility status.
- [ ] Include robustness evidence.
- [ ] Include statistical validation evidence.
- [ ] Include paper trading evidence.
- [ ] Include risk memo.
- [ ] Include portfolio memo.
- [ ] Include execution readiness report.
- [ ] Include broker readiness report.
- [ ] Include audit preflight report.
- [ ] Include cost impact.
- [ ] Include known failure modes.
- [ ] Include expected worst-case behavior.
- [ ] Include recommended activation stage.
- [ ] Include recommended limits.
- [ ] Include rejection criteria.
- [ ] Include rollback criteria.
- [ ] Include monitoring checklist.
- [ ] Include evidence completeness score.
- [ ] Include evidence quality rating.

### 4.3 Evidence quality gates

- [ ] Reject if research evidence is missing.
- [ ] Reject if strategy spec is missing.
- [ ] Reject if strategy code hash is missing.
- [ ] Reject if code review failed.
- [ ] Reject if no-lookahead test failed.
- [ ] Reject if backtest is not reproducible.
- [ ] Reject if robustness failed.
- [ ] Reject if statistical validation is weak.
- [ ] Reject if paper trading evidence is missing.
- [ ] Reject if paper trading duration is too short.
- [ ] Reject if paper trading trade count is too low.
- [ ] Reject if paper drawdown exceeded limit.
- [ ] Reject if paper execution anomalies exist.
- [ ] Reject if RiskGovernor blocked the activation.
- [ ] Reject if portfolio memo rejects the allocation.
- [ ] Reject if broker readiness failed.
- [ ] Reject if kill switch is unhealthy.
- [ ] Reject if audit logging is unavailable.

---

## 5. Live Activation Gatekeeper Service

### 5.1 Purpose

The Live Activation Gatekeeper is a deterministic service that validates whether a strategy is eligible to be presented to the Board for activation.

It is not an LLM agent.

### 5.2 Recommended folder

```text
services/
  live_activation/
    __init__.py
    contracts.py
    gatekeeper.py
    evidence_pack.py
    live_config_writer.py
    approval_policy.py
    preflight.py
    audit.py
    README.md
    tests/
      test_contracts.py
      test_gatekeeper.py
      test_evidence_pack.py
      test_preflight.py
      test_live_config_writer.py
      test_approval_policy.py
```

### 5.3 Checklist

- [ ] Create `services/live_activation/gatekeeper.py`.
- [ ] Load live activation request.
- [ ] Validate request schema.
- [ ] Validate strategy lifecycle state.
- [ ] Validate strategy version.
- [ ] Validate strategy code hash.
- [ ] Validate evidence pack.
- [ ] Validate backtest status.
- [ ] Validate robustness status.
- [ ] Validate statistical validation status.
- [ ] Validate paper trading status.
- [ ] Validate risk memo.
- [ ] Validate portfolio memo.
- [ ] Validate broker readiness.
- [ ] Validate kill switch status.
- [ ] Validate audit logger status.
- [ ] Validate RiskGovernor status.
- [ ] Validate requested allocation.
- [ ] Validate requested symbols.
- [ ] Validate requested broker account.
- [ ] Validate requested risk limits.
- [ ] Validate approval expiration.
- [ ] Produce gatekeeper decision.
- [ ] Return allowed/blocked activation stages.
- [ ] Return deterministic rejection reasons.
- [ ] Write audit record.

### 5.4 Gatekeeper decision statuses

```text
eligible_for_board_review
blocked_missing_evidence
blocked_by_risk
blocked_by_portfolio
blocked_by_broker_readiness
blocked_by_audit
blocked_by_kill_switch
blocked_by_lifecycle_state
blocked_by_policy
error
```

---

## 6. Board Approval UI

### 6.1 Goal

Allow the user to approve or reject live activation from a complete evidence package.

### 6.2 Checklist

- [ ] Show full evidence pack.
- [ ] Show CEO activation memo.
- [ ] Show strategy summary.
- [ ] Show strategy lifecycle state.
- [ ] Show strategy version and code hash.
- [ ] Show requested activation stage.
- [ ] Show requested allocation.
- [ ] Show max risk per trade.
- [ ] Show max daily loss.
- [ ] Show max strategy drawdown.
- [ ] Show max margin usage.
- [ ] Show approved symbols.
- [ ] Show approved broker account.
- [ ] Show risk limits.
- [ ] Show expected worst-case behavior.
- [ ] Show promotion reason.
- [ ] Show known failure modes.
- [ ] Show rollback criteria.
- [ ] Show RiskGovernor status.
- [ ] Show Portfolio Manager recommendation.
- [ ] Show broker readiness.
- [ ] Show kill-switch status.
- [ ] Show audit readiness.
- [ ] Show approval expiration.
- [ ] Show rejection option.
- [ ] Show approve micro-live only.
- [ ] Show approve limited-live only.
- [ ] Show approve full-live only if policy allows.
- [ ] Show request clarification from CEO action.
- [ ] Store approval in audit log.
- [ ] Store rejection in audit log.
- [ ] Require rejection reason when rejecting.
- [ ] Require confirmation phrase for live activation.
- [ ] Disable approval if gatekeeper blocks request.
- [ ] Disable approval if RiskGovernor blocks request.
- [ ] Disable approval if audit status is unhealthy.
- [ ] Disable approval if kill switch is triggered.
- [ ] Disable approval if broker readiness failed.

### 6.3 Approval buttons

Recommended controls:

```text
Reject
Request More Evidence
Approve Micro-Live
Approve Limited-Live
Approve Full-Live
```

Default policy:

```text
Approve Full-Live should be disabled unless the strategy already passed micro-live and limited-live stages.
```

### 6.4 Board approval audit fields

- [ ] `approval_id`
- [ ] `request_id`
- [ ] `approved_by`
- [ ] `approved_at`
- [ ] `approval_type`
- [ ] `approved_stage`
- [ ] `approved_allocation`
- [ ] `approved_symbols`
- [ ] `approved_broker_account`
- [ ] `approved_risk_limits`
- [ ] `approval_expiration`
- [ ] `evidence_pack_hash`
- [ ] `live_config_hash_before`
- [ ] `live_config_hash_after`
- [ ] `rejection_reason`
- [ ] `confirmation_text`
- [ ] `audit_signature`

---

## 7. Live Config

### 7.1 Goal

Create a governed live-trading configuration that cannot be edited casually.

### 7.2 Checklist

- [ ] Create `config/live_trading.yaml`.
- [ ] Add global live mode.
- [ ] Add global paper mode.
- [ ] Add environment.
- [ ] Add approved broker accounts.
- [ ] Add approved symbols.
- [ ] Add allowed execution bridges.
- [ ] Add per-strategy live mode.
- [ ] Add per-strategy paper mode.
- [ ] Add per-strategy activation stage.
- [ ] Add per-strategy allocation.
- [ ] Add per-strategy max risk per trade.
- [ ] Add per-strategy max daily loss.
- [ ] Add per-strategy max drawdown.
- [ ] Add per-strategy max margin usage.
- [ ] Add per-strategy max open positions.
- [ ] Add per-strategy approved symbols.
- [ ] Add per-strategy approved timeframes.
- [ ] Add per-strategy approved broker account.
- [ ] Add per-strategy allowed sessions.
- [ ] Add per-strategy news blackout rules.
- [ ] Add per-strategy spread limit.
- [ ] Add per-strategy slippage limit.
- [ ] Add approval ID.
- [ ] Add approval expiration.
- [ ] Add config version.
- [ ] Add config hash.
- [ ] Add last modified timestamp.
- [ ] Add last modified by.
- [ ] Add audit reference.
- [ ] Block edits except through approved admin path.
- [ ] Reject config if hash does not match.
- [ ] Reject config if approval expired.
- [ ] Reject config if strategy version mismatches.
- [ ] Reject config if strategy code hash mismatches.
- [ ] Reject config if broker account mismatches.

### 7.3 Example

```yaml
global:
  environment: production
  live_mode_enabled: false
  paper_mode_enabled: true
  live_mode_requires_board_approval: true
  config_version: "live_trading_v1"
  config_hash: sha256:...
  last_modified_at: "2026-05-07T00:00:00Z"
  last_modified_by: board_approval_workflow

broker_accounts:
  approved:
    - account_id: mt5_primary_micro
      broker: mt5
      mode: micro_live

strategies:
  strat_eurusd_h1_mean_reversion:
    strategy_version: "1.0.0"
    strategy_code_hash: sha256:...
    activation_stage: micro_live
    live_enabled: true
    paper_enabled: true
    allocation: 1000.0
    max_risk_per_trade: 0.0025
    max_daily_loss: 0.005
    max_strategy_drawdown: 0.03
    max_open_positions: 1
    max_margin_usage: 0.10
    approved_symbols:
      - EURUSD
    approved_timeframes:
      - H1
    approved_broker_account: mt5_primary_micro
    allowed_sessions:
      - london
      - new_york
    blocked_sessions:
      - rollover
    spread_limit_pips: 2.0
    slippage_limit_pips: 1.5
    approval_id: approval_2026_000001
    approval_expiration: "2026-06-07T00:00:00Z"
    audit_ref: audit_2026_000001
```

---

## 8. Live Config Writer Service

### 8.1 Purpose

The Live Config Writer is the only service allowed to modify `config/live_trading.yaml`.

It must be deterministic and audit-heavy.

### 8.2 Checklist

- [ ] Create `services/live_activation/live_config_writer.py`.
- [ ] Validate Board approval.
- [ ] Validate approval is not expired.
- [ ] Validate approval matches strategy.
- [ ] Validate approval matches strategy version.
- [ ] Validate approval matches code hash.
- [ ] Validate approval matches requested allocation.
- [ ] Validate approval matches broker account.
- [ ] Validate approval matches approved symbols.
- [ ] Validate current config hash.
- [ ] Create proposed config diff.
- [ ] Validate config diff against policy.
- [ ] Write new config atomically.
- [ ] Generate new config hash.
- [ ] Save config snapshot.
- [ ] Save audit record.
- [ ] Reject manual/unapproved changes.
- [ ] Fail closed on mismatch.
- [ ] Roll back if write fails.
- [ ] Notify CEO workflow.
- [ ] Notify RiskGovernor.
- [ ] Notify Order Router.
- [ ] Notify Audit Agent.

### 8.3 Config write statuses

```text
success
rejected_no_approval
rejected_expired_approval
rejected_hash_mismatch
rejected_strategy_mismatch
rejected_broker_mismatch
rejected_policy_violation
write_failed
rolled_back
```

---

## 9. Execution Preflight

### 9.1 Goal

Before live activation becomes effective, the system must verify that execution infrastructure is safe.

### 9.2 Checklist

- [ ] Validate broker connection.
- [ ] Validate broker heartbeat.
- [ ] Validate account info.
- [ ] Validate account ID matches approval.
- [ ] Validate account currency.
- [ ] Validate account leverage.
- [ ] Validate margin mode.
- [ ] Validate symbol metadata.
- [ ] Validate pip value.
- [ ] Validate tick size.
- [ ] Validate tick value.
- [ ] Validate min lot.
- [ ] Validate max lot.
- [ ] Validate lot step.
- [ ] Validate stop distance.
- [ ] Validate freeze level.
- [ ] Validate trading session.
- [ ] Validate spread.
- [ ] Validate latest tick recency.
- [ ] Validate order router health.
- [ ] Validate RiskGovernor health.
- [ ] Validate kill switch health.
- [ ] Validate audit logger health.
- [ ] Validate execution bridge permissions.
- [ ] Validate live config hash.
- [ ] Validate strategy lifecycle state.
- [ ] Validate strategy live status.
- [ ] Generate execution readiness report.
- [ ] Block activation if any critical check fails.

### 9.3 Preflight statuses

```text
ready
ready_with_warnings
blocked_broker
blocked_symbol_metadata
blocked_spread
blocked_risk_governor
blocked_kill_switch
blocked_audit
blocked_config
blocked_policy
```

---

## 10. Micro-Live Stage

### 10.1 Goal

Allow a strategy to trade with very small exposure to validate live execution behavior.

### 10.2 Checklist

- [ ] Require Board approval.
- [ ] Require live config entry.
- [ ] Require micro-live allocation cap.
- [ ] Require stricter risk per trade.
- [ ] Require stricter daily loss limit.
- [ ] Require stricter max open positions.
- [ ] Require stricter spread/slippage limits.
- [ ] Require execution anomaly monitoring.
- [ ] Require daily review.
- [ ] Require minimum live days before promotion.
- [ ] Require minimum live trade count before promotion.
- [ ] Require no critical audit findings.
- [ ] Require no RiskGovernor violations.
- [ ] Require no kill-switch incidents.
- [ ] Require broker execution quality within tolerance.
- [ ] Require live performance within expected paper/backtest confidence interval.
- [ ] Auto-pause if live losses breach micro-live threshold.
- [ ] Auto-pause if repeated execution anomalies occur.
- [ ] Auto-pause if strategy behavior deviates materially from expected behavior.

### 10.3 Micro-live promotion criteria

- [ ] Minimum live duration met.
- [ ] Minimum live trade count met.
- [ ] Drawdown within limit.
- [ ] Slippage within expected range.
- [ ] Spread within expected range.
- [ ] No abnormal order rejection pattern.
- [ ] No audit-critical findings.
- [ ] No kill-switch triggers.
- [ ] No unauthorized lifecycle changes.
- [ ] Performance not materially worse than paper expectation.
- [ ] Risk memo supports promotion.
- [ ] Portfolio memo supports promotion.
- [ ] CEO memo recommends promotion.
- [ ] Board approves promotion.

---

## 11. Limited-Live Stage

### 11.1 Goal

Increase allocation only after micro-live behavior is proven.

### 11.2 Checklist

- [ ] Require completed micro-live stage.
- [ ] Require micro-live report.
- [ ] Require updated risk memo.
- [ ] Require updated portfolio memo.
- [ ] Require updated execution quality report.
- [ ] Require updated audit report.
- [ ] Require Board approval.
- [ ] Require live config update.
- [ ] Increase allocation gradually.
- [ ] Maintain per-strategy risk cap.
- [ ] Maintain daily loss limit.
- [ ] Monitor correlation impact.
- [ ] Monitor portfolio drawdown impact.
- [ ] Monitor cost/slippage impact.
- [ ] Monitor strategy drift.
- [ ] Auto-pause on policy breach.
- [ ] Require periodic review.

### 11.2 Limited-live promotion criteria

- [ ] Minimum limited-live duration met.
- [ ] Minimum limited-live trade count met.
- [ ] Performance remains within expected range.
- [ ] Drawdown remains within limit.
- [ ] Execution quality remains acceptable.
- [ ] Portfolio diversification remains acceptable.
- [ ] RiskGovernor blocks remain explainable.
- [ ] No critical audit findings.
- [ ] CEO recommends further promotion.
- [ ] Board approves further promotion.

---

## 12. Full-Live Stage

### 12.1 Goal

Allow normal live allocation only for strategies that have passed all prior stages.

### 12.2 Checklist

- [ ] Require completed limited-live stage.
- [ ] Require full evidence refresh.
- [ ] Require updated simulation comparison.
- [ ] Require updated robustness review if market regime changed.
- [ ] Require updated risk memo.
- [ ] Require updated portfolio memo.
- [ ] Require updated Board approval.
- [ ] Require production live config.
- [ ] Require ongoing risk monitoring.
- [ ] Require ongoing audit monitoring.
- [ ] Require ongoing cost monitoring.
- [ ] Require monthly review.
- [ ] Auto-pause if strategy violates live policy.
- [ ] Auto-pause if performance deteriorates beyond threshold.
- [ ] Auto-pause if market regime invalidates edge.
- [ ] Auto-pause if broker/execution quality deteriorates.
- [ ] Auto-pause if RiskGovernor becomes unavailable.
- [ ] Auto-pause if audit logger becomes unavailable.

---

## 13. Live Activation Rejection Rules

The system must reject or block live activation if:

- [ ] Strategy is not code-reviewed.
- [ ] Strategy lifecycle state is not eligible.
- [ ] Strategy version is not pinned.
- [ ] Strategy code hash is missing.
- [ ] Strategy code hash changed after review.
- [ ] Strategy spec hash changed after review.
- [ ] Backtest package is missing.
- [ ] Backtest is not reproducible.
- [ ] Backtest acceptance rules failed.
- [ ] Robustness tests failed.
- [ ] Statistical validation is weak.
- [ ] Paper trading minimum duration not met.
- [ ] Paper trading minimum trade count not met.
- [ ] Paper trading drawdown exceeded limit.
- [ ] Paper trading execution anomalies exist.
- [ ] Risk memo rejects activation.
- [ ] Portfolio memo rejects allocation.
- [ ] Requested allocation exceeds approved limit.
- [ ] Requested risk per trade exceeds policy.
- [ ] Requested symbol is not approved.
- [ ] Requested broker account is not approved.
- [ ] Kill switch is triggered.
- [ ] Broker readiness failed.
- [ ] Audit logging is unavailable.
- [ ] RiskGovernor is unavailable.
- [ ] Cost or compute limits block workflow completion.
- [ ] Board approval is missing.
- [ ] Board approval expired.
- [ ] Live config hash mismatch is detected.
- [ ] Manual config edit is detected.

---

## 14. Live Activation Output Artifacts

The workflow must produce:

```text
live_activation_request.yaml
live_activation_evidence_pack.json
ceo_activation_memo.md
risk_activation_memo.md
portfolio_activation_memo.md
execution_readiness_report.json
audit_preflight_report.json
board_approval_record.json
live_config_diff.yaml
live_config_snapshot.yaml
live_activation_audit.json
```

Recommended path:

```text
live_activation/
  requests/
    <request_id>/
      live_activation_request.yaml
      evidence_pack.json
      ceo_activation_memo.md
      risk_activation_memo.md
      portfolio_activation_memo.md
      execution_readiness_report.json
      audit_preflight_report.json
      board_approval_record.json
      live_config_diff.yaml
      live_config_snapshot.yaml
      audit.json
```

---

## 15. Full Operating Cycle

### 15.1 Goal

Run HaruQuant as a repeatable autonomous research-and-trading operating system.

### 15.2 Operating-cycle principle

The firm should continuously cycle through:

```text
Observe
→ Research
→ Specify
→ Code
→ Review
→ Simulate
→ Diagnose
→ Optimize
→ Robustness Test
→ Statistically Validate
→ Risk Review
→ Portfolio Review
→ Paper Trade
→ Live Activation Review
→ Execute
→ Monitor
→ Report
→ Audit
→ Improve
```

The CEO Agent owns user-facing summaries and Board requests. Specialist agents/services produce structured evidence.

---

## 16. Daily Cycle

### 16.1 Goal

Monitor the current market, active strategies, execution, risk, performance, and incidents.

### 16.2 Checklist

- [ ] Market Intelligence Agent scans active symbols.
- [ ] Technical Analyst Agent updates symbol context.
- [ ] News and Sentiment Agent checks high-impact event risk.
- [ ] Macro/Fundamental Agent refreshes relevant macro context where needed.
- [ ] Cross-Asset Agent updates correlation and exposure context.
- [ ] Seasonality Agent updates current session/calendar context.
- [ ] Strategy signals are checked.
- [ ] Paper strategies generate paper trade proposals where allowed.
- [ ] Live strategies generate live trade proposals where allowed.
- [ ] RiskGovernor checks proposals.
- [ ] Order Router rejects or routes approved proposals.
- [ ] Paper Execution Agent runs where allowed.
- [ ] Live Execution Agent runs where allowed.
- [ ] Kill Switch Service monitors safety state.
- [ ] Portfolio Risk Monitor checks exposure and drawdown.
- [ ] Performance Reporter writes daily report.
- [ ] Audit Agent writes daily audit.
- [ ] Cost Optimizer records daily cost.
- [ ] CEO summarizes daily state.
- [ ] CEO lists blocked actions.
- [ ] CEO lists required user decisions.
- [ ] CEO escalates critical issues to Board Room.

### 16.3 Daily report must include

- [ ] Daily P&L.
- [ ] Open exposure.
- [ ] Current drawdown.
- [ ] Daily loss usage.
- [ ] VaR/CVaR.
- [ ] Strategy health.
- [ ] Paper strategy performance.
- [ ] Live strategy performance.
- [ ] Rejected trades.
- [ ] RiskGovernor blocks.
- [ ] Execution anomalies.
- [ ] Kill-switch status.
- [ ] Audit status.
- [ ] Cost usage.
- [ ] Market regime summary.
- [ ] News/event risk summary.
- [ ] Required actions.
- [ ] CEO recommendation.

### 16.4 Daily automatic blocks

- [ ] Block new live orders if daily loss limit breached.
- [ ] Block new live orders if kill switch triggered.
- [ ] Block new live orders if audit logger unavailable.
- [ ] Block new live orders if RiskGovernor unavailable.
- [ ] Block new live orders if broker heartbeat failed.
- [ ] Block strategy if repeated execution anomalies occur.
- [ ] Block strategy if spread/slippage exceeds policy.
- [ ] Block strategy if live config hash mismatch detected.
- [ ] Block strategy if approval expired.

---

## 17. Weekly Cycle

### 17.1 Goal

Generate new ideas, validate candidates, rank strategies, and prepare Board decisions.

### 17.2 Checklist

- [ ] Research Department proposes new ideas.
- [ ] Strategy Creator creates or updates specs.
- [ ] Strategy Codegen Agent generates code for approved specs.
- [ ] Strategy Reviewer Agent reviews generated strategies.
- [ ] Backtest Agent runs tests.
- [ ] Backtest Analyst diagnoses strategy behavior.
- [ ] Optimization Agent runs approved parameter sweeps.
- [ ] Optimization Comparator recommends robust regions.
- [ ] Robustness Agent validates candidates.
- [ ] Statistical Validation Agent rates evidence quality.
- [ ] Risk Reviewer produces risk memos for candidates.
- [ ] Portfolio Manager ranks strategy candidates.
- [ ] Paper strategies are reviewed.
- [ ] Micro-live strategies are reviewed.
- [ ] Live strategies are reviewed.
- [ ] Cost Optimizer reviews weekly cost.
- [ ] Audit Agent creates weekly compliance summary.
- [ ] CEO creates Board report.
- [ ] Board approves/rejects requested actions.

### 17.3 Weekly Board report must include

- [ ] Portfolio performance.
- [ ] Live strategy performance.
- [ ] Paper strategy performance.
- [ ] Micro-live strategy performance.
- [ ] New research ideas.
- [ ] New strategy specs.
- [ ] Generated code reviews.
- [ ] Backtest summaries.
- [ ] Robustness summaries.
- [ ] Statistical validation summaries.
- [ ] Risk events.
- [ ] Audit findings.
- [ ] Cost usage.
- [ ] Promotion candidates.
- [ ] Demotion candidates.
- [ ] Pause candidates.
- [ ] Retirement candidates.
- [ ] Allocation-change requests.
- [ ] Live activation requests.
- [ ] Required Board decisions.

### 17.4 Weekly decision types

- [ ] Approve new research direction.
- [ ] Approve strategy specification.
- [ ] Approve strategy coding.
- [ ] Approve backtesting campaign.
- [ ] Admit strategy to paper trading.
- [ ] Reject strategy.
- [ ] Promote strategy to micro-live candidate.
- [ ] Promote strategy to limited-live candidate.
- [ ] Increase allocation.
- [ ] Decrease allocation.
- [ ] Pause strategy.
- [ ] Retire strategy.
- [ ] Request more evidence.
- [ ] Change risk policy through governed workflow.
- [ ] Change cost budget through governed workflow.

---

## 18. Monthly Cycle

### 18.1 Goal

Review firm-level health, strategy lifecycle, risk policy, allocation, cost efficiency, and audit incidents.

### 18.2 Checklist

- [ ] Review all live strategies.
- [ ] Review all micro-live strategies.
- [ ] Review all limited-live strategies.
- [ ] Review all paper strategies.
- [ ] Review all rejected strategies for learning.
- [ ] Review strategy lifecycle table.
- [ ] Review strategy family concentration.
- [ ] Review symbol concentration.
- [ ] Review currency-cluster concentration.
- [ ] Review correlation clusters.
- [ ] Review portfolio-level drawdown.
- [ ] Review VaR/CVaR behavior.
- [ ] Review RiskGovernor blocks.
- [ ] Review execution quality.
- [ ] Review broker reliability.
- [ ] Review spread/slippage drift.
- [ ] Review live-vs-paper performance gap.
- [ ] Review backtest-vs-live performance gap.
- [ ] Promote strong paper strategies.
- [ ] Promote strong micro-live strategies.
- [ ] Reduce weak live strategies.
- [ ] Pause suspicious strategies.
- [ ] Retire failed strategies.
- [ ] Rebalance allocations.
- [ ] Review risk policy.
- [ ] Review kill-switch thresholds.
- [ ] Review live activation policy.
- [ ] Review cost efficiency.
- [ ] Review model routing policy.
- [ ] Review audit incidents.
- [ ] Review infrastructure health.
- [ ] CEO produces monthly firm review.
- [ ] Board approves major changes.

### 18.3 Monthly firm review must include

- [ ] Executive summary.
- [ ] Firm-level performance.
- [ ] Portfolio allocation.
- [ ] Risk state.
- [ ] Strategy lifecycle changes.
- [ ] Research pipeline.
- [ ] Simulation pipeline.
- [ ] Paper trading pipeline.
- [ ] Live trading performance.
- [ ] Incidents.
- [ ] Audit findings.
- [ ] Cost report.
- [ ] Infrastructure report.
- [ ] Policy review.
- [ ] Decisions required.

---

## 19. Quarterly Cycle

### 19.1 Goal

Review long-term strategic direction, risk regime, portfolio construction, infrastructure, and agent performance.

### 19.2 Checklist

- [ ] Review annualized performance.
- [ ] Review rolling drawdown.
- [ ] Review risk-adjusted returns.
- [ ] Review strategy-family diversification.
- [ ] Review symbol and currency exposure.
- [ ] Review live-trading scalability.
- [ ] Review broker quality.
- [ ] Review execution quality.
- [ ] Review risk model calibration.
- [ ] Review VaR/CVaR calibration.
- [ ] Review correlation model stability.
- [ ] Review strategy retirement policy.
- [ ] Review robustness test thresholds.
- [ ] Review statistical validation thresholds.
- [ ] Review paper-to-live promotion policy.
- [ ] Review Board approval policy.
- [ ] Review audit policy.
- [ ] Review model routing and cost policy.
- [ ] Review agent evaluator performance.
- [ ] Review prompt and policy version drift.
- [ ] Review documentation completeness.
- [ ] Update strategic roadmap.

---

## 20. Operating Cycle Orchestrator

### 20.1 Purpose

The Operating Cycle Orchestrator schedules and coordinates daily, weekly, monthly, and quarterly workflows.

This may be implemented as a deterministic service with CEO-facing summaries, not as an independent user-facing agent.

### 20.2 Recommended folder

```text
services/
  operating_cycle/
    __init__.py
    contracts.py
    scheduler.py
    daily_cycle.py
    weekly_cycle.py
    monthly_cycle.py
    quarterly_cycle.py
    cycle_policy.py
    audit.py
    README.md
    tests/
      test_contracts.py
      test_daily_cycle.py
      test_weekly_cycle.py
      test_monthly_cycle.py
      test_cycle_policy.py
```

### 20.3 Checklist

- [ ] Create `services/operating_cycle`.
- [ ] Define cycle schedules.
- [ ] Define daily cycle workflow.
- [ ] Define weekly cycle workflow.
- [ ] Define monthly cycle workflow.
- [ ] Define quarterly cycle workflow.
- [ ] Define cycle input contracts.
- [ ] Define cycle output contracts.
- [ ] Define required reports.
- [ ] Define required evidence.
- [ ] Define required checks.
- [ ] Define escalation rules.
- [ ] Define skip rules.
- [ ] Define failure rules.
- [ ] Define retry rules for safe read-only tasks.
- [ ] Define no-retry rules for governed writes.
- [ ] Define cost budgets.
- [ ] Define audit records.
- [ ] Save cycle run history.
- [ ] Expose cycle status to UI.
- [ ] Send cycle summary to CEO.

### 20.4 Cycle statuses

```text
scheduled
running
completed
completed_with_warnings
blocked
failed
cancelled
```

---

## 21. Operating Cycle Report Schemas

### 21.1 DailyCycleReport

- [ ] `report_id`
- [ ] `date`
- [ ] `created_at`
- [ ] `market_summary`
- [ ] `strategy_signal_summary`
- [ ] `paper_execution_summary`
- [ ] `live_execution_summary`
- [ ] `risk_summary`
- [ ] `portfolio_summary`
- [ ] `performance_summary`
- [ ] `audit_summary`
- [ ] `cost_summary`
- [ ] `incidents`
- [ ] `blocked_actions`
- [ ] `required_user_actions`
- [ ] `ceo_summary`
- [ ] `evidence_refs`
- [ ] `audit_refs`

### 21.2 WeeklyBoardReport

- [ ] `report_id`
- [ ] `week_start`
- [ ] `week_end`
- [ ] `created_at`
- [ ] `portfolio_performance`
- [ ] `research_pipeline`
- [ ] `strategy_pipeline`
- [ ] `simulation_pipeline`
- [ ] `paper_pipeline`
- [ ] `live_pipeline`
- [ ] `risk_events`
- [ ] `audit_events`
- [ ] `cost_summary`
- [ ] `approval_queue`
- [ ] `recommended_decisions`
- [ ] `evidence_refs`
- [ ] `audit_refs`

### 21.3 MonthlyFirmReview

- [ ] `report_id`
- [ ] `month`
- [ ] `created_at`
- [ ] `firm_performance`
- [ ] `portfolio_composition`
- [ ] `risk_review`
- [ ] `strategy_lifecycle_review`
- [ ] `research_review`
- [ ] `simulation_review`
- [ ] `paper_review`
- [ ] `live_review`
- [ ] `incident_review`
- [ ] `audit_review`
- [ ] `cost_review`
- [ ] `policy_review`
- [ ] `roadmap_recommendations`
- [ ] `board_decisions_required`
- [ ] `evidence_refs`
- [ ] `audit_refs`

---

## 22. UI Requirements

### 22.1 `/board-room`

- [ ] Show live activation requests.
- [ ] Show evidence pack.
- [ ] Show CEO activation memo.
- [ ] Show RiskGovernor status.
- [ ] Show Portfolio Manager recommendation.
- [ ] Show broker readiness.
- [ ] Show kill-switch status.
- [ ] Show audit readiness.
- [ ] Show approve/reject/request-more-evidence controls.
- [ ] Show live config diff before approval.
- [ ] Show approval expiration.
- [ ] Show activation history.
- [ ] Show rejected activation requests.

### 22.2 `/execution`

- [ ] Show live config status.
- [ ] Show active live strategies.
- [ ] Show active micro-live strategies.
- [ ] Show active limited-live strategies.
- [ ] Show broker readiness.
- [ ] Show bridge health.
- [ ] Show order router health.
- [ ] Show kill-switch status.
- [ ] Show RiskGovernor health.
- [ ] Show audit logger health.
- [ ] Show live order blocks.
- [ ] Show execution anomalies.

### 22.3 `/portfolio`

- [ ] Show lifecycle state for every strategy.
- [ ] Show paper-to-live candidates.
- [ ] Show micro-live candidates.
- [ ] Show limited-live candidates.
- [ ] Show allocation recommendations.
- [ ] Show promotion/demotion recommendations.
- [ ] Show monthly lifecycle review.

### 22.4 `/ai-ceo`

- [ ] Allow user to ask CEO for live activation readiness.
- [ ] Allow user to ask CEO to prepare a live activation request.
- [ ] Allow CEO to request missing evidence.
- [ ] Show Planner-selected departments.
- [ ] Show final activation memo.
- [ ] Link to Board Room approval card.

### 22.5 `/audit`

- [ ] Show live activation audit records.
- [ ] Show live config changes.
- [ ] Show approval token usage.
- [ ] Show unauthorized config edit attempts.
- [ ] Show activation-stage violations.
- [ ] Show critical audit failures.

---

## 23. Testing Requirements

### 23.1 Live activation tests

- [ ] Test valid micro-live activation request.
- [ ] Test request rejected when research evidence missing.
- [ ] Test request rejected when backtest missing.
- [ ] Test request rejected when robustness failed.
- [ ] Test request rejected when statistical validation weak.
- [ ] Test request rejected when paper duration too short.
- [ ] Test request rejected when paper trade count too low.
- [ ] Test request rejected when RiskGovernor blocks.
- [ ] Test request rejected when portfolio memo rejects.
- [ ] Test request rejected when broker readiness failed.
- [ ] Test request rejected when kill switch triggered.
- [ ] Test request rejected when audit logger unavailable.
- [ ] Test request rejected when Board approval missing.
- [ ] Test request rejected when approval expired.
- [ ] Test request rejected when strategy code hash changed.
- [ ] Test request rejected when live config hash mismatch.
- [ ] Test Live Config Writer atomic update.
- [ ] Test config rollback on write failure.
- [ ] Test approval audit record written.
- [ ] Test UI approval disabled when gatekeeper blocks.

### 23.2 Operating cycle tests

- [ ] Test daily cycle creates daily report.
- [ ] Test daily cycle blocks live orders when RiskGovernor unavailable.
- [ ] Test daily cycle escalates kill-switch incident.
- [ ] Test weekly cycle creates Board report.
- [ ] Test weekly cycle includes approval queue.
- [ ] Test monthly cycle creates firm review.
- [ ] Test monthly cycle identifies promotion candidates.
- [ ] Test monthly cycle identifies retirement candidates.
- [ ] Test cycle fails safely when audit logging unavailable.
- [ ] Test cycle respects cost budget.
- [ ] Test governed writes are not retried automatically.
- [ ] Test read-only task retry behavior.

---

## 24. Audit Requirements

### 24.1 Live activation audit

Every activation workflow must audit:

- [ ] Request creation.
- [ ] Evidence pack creation.
- [ ] Gatekeeper decision.
- [ ] Risk memo.
- [ ] Portfolio memo.
- [ ] CEO memo.
- [ ] Board approval or rejection.
- [ ] Live config diff.
- [ ] Live config write.
- [ ] Config hash before and after.
- [ ] Execution preflight.
- [ ] Activation status.
- [ ] Any blocked reason.
- [ ] Any exception.
- [ ] Any rollback.
- [ ] User confirmation text.
- [ ] Approval expiration.

### 24.2 Operating cycle audit

Every cycle must audit:

- [ ] Cycle ID.
- [ ] Cycle type.
- [ ] Start time.
- [ ] End time.
- [ ] Tasks run.
- [ ] Tasks skipped.
- [ ] Tasks failed.
- [ ] Reports produced.
- [ ] Decisions requested.
- [ ] Escalations created.
- [ ] Cost incurred.
- [ ] Evidence refs.
- [ ] Audit refs.
- [ ] Critical warnings.

---

## 25. Security and Permission Requirements

- [ ] Only authorized Board approver can approve live activation.
- [ ] Only governed workflow can write live config.
- [ ] Only Order Router can submit live order requests to execution bridge.
- [ ] Only Execution Bridge can call broker order endpoints.
- [ ] Only RiskGovernor can approve risk.
- [ ] Only Kill Switch can block globally.
- [ ] UI cannot override live config.
- [ ] UI cannot create approval tokens.
- [ ] UI cannot bypass evidence requirements.
- [ ] UI cannot directly call broker bridge.
- [ ] Manual config edits must be detected.
- [ ] Config hash mismatch must block live trading.
- [ ] Approval expiration must block live trading.
- [ ] Critical audit failure must disable live trading.

---

## 26. Build Order

Build in this order:

```text
1. LiveActivationRequest contract
2. LiveActivationEvidencePack contract
3. Live Activation Gatekeeper service
4. Execution Preflight service
5. Board approval record contract
6. Live Config Writer service
7. config/live_trading.yaml
8. Live activation audit records
9. Board Room approval UI
10. Execution readiness UI
11. Operating Cycle contracts
12. Daily cycle service
13. Weekly cycle service
14. Monthly cycle service
15. Quarterly cycle service
16. CEO operating-cycle summaries
17. UI cycle dashboards
18. E2E live activation safety tests
19. E2E operating cycle tests
20. Production dry run with live mode disabled
```

---

## 27. Definition of Done

### 27.1 Live activation done definition

Live trading activation is complete only when:

```text
1. LiveActivationRequest schema exists.
2. Evidence pack schema exists.
3. Gatekeeper validates all evidence and policy requirements.
4. Board approval UI shows the full evidence pack.
5. RiskGovernor can block activation.
6. Portfolio Manager can block activation.
7. Broker readiness can block activation.
8. Kill switch can block activation.
9. Audit logger health can block activation.
10. Board approval is required.
11. Approval expiration is enforced.
12. Live config can only be modified by Live Config Writer.
13. Live config hash is validated.
14. Unauthorized config changes block live trading.
15. Micro-live, limited-live, and full-live stages are distinct.
16. Live execution still requires per-order RiskGovernor approval tokens.
17. All activation actions produce audit records.
18. E2E tests prove unsafe activation is blocked.
```

### 27.2 Operating cycle done definition

The full operating cycle is complete only when:

```text
1. Daily cycle produces market, risk, execution, performance, audit, cost, and CEO summaries.
2. Weekly cycle produces Board reports and approval queues.
3. Monthly cycle reviews all strategy lifecycle states and portfolio allocations.
4. Quarterly cycle reviews policy, infrastructure, and strategic direction.
5. CEO summarizes each cycle for the user.
6. Required Board decisions appear in the Board Room.
7. Critical incidents escalate automatically.
8. Risk blocks, kill-switch events, and audit failures are visible in UI.
9. Reports link to evidence and audit references.
10. HaruQuant operates as a repeatable research-and-trading firm.
```

---

## 28. Final Rule

```text
Live trading is not a feature toggle.
It is a governed lifecycle transition.

A strategy goes live only when evidence, risk, portfolio, execution readiness, audit, and Board approval all agree.
Even after activation, every order still requires deterministic RiskGovernor approval.
```
