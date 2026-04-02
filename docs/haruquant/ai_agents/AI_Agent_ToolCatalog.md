# AI Agentic Orchestration Layer — Tool Catalog

## 1. Purpose

This document defines the initial HaruQuant AI tool catalog.

The catalog is designed so agents can operate through **bounded, typed, auditable tools** rather than freeform internal assumptions.

The tools described here are logical capabilities. They can be implemented by wrapping existing HaruQuant services, APIs, repositories, or engine entry points.

---

## 2. Tool design principles

1. Every tool must have a clear purpose.
2. Every tool must have a typed input and output contract.
3. Every tool must be assigned a permission mode.
4. Every tool call must be auditable.
5. Every tool should map to a real HaruQuant subsystem.

---

## 3. Permission modes

### 3.1 Read-only
Can retrieve, compare, summarize, or export.
Cannot mutate runtime state.

### 3.2 Advisory-write
Can trigger safe, non-live workflows that do not bypass governance.
Examples include report generation, batch refresh, what-if runs, and replay analysis.

### 3.3 Privileged
Can affect live/critical operations.
These must require stronger policies and explicit approval.

---

## 4. Shared tool response contract

Recommended shared response shape:

```json
{
  "ok": true,
  "tool_name": "...",
  "data": {},
  "refs": [],
  "warnings": [],
  "metadata": {
    "duration_ms": 0,
    "correlation_id": "..."
  }
}
```

---

## 5. Edge tools

## 5.1 edge_prepare_dataset
Mode: advisory-write

Purpose:
- prepare a validated, cleaned, enriched Edge dataset

Inputs:
- symbol
- timeframe
- source
- range_by
- start_date / end_date or bar count
- force_rerun

Outputs:
- prepared dataset summary
- validation report
- dataset fingerprint
- reproducibility metadata

Reason:
- all later Edge workflows depend on a common prepared dataset

## 5.2 edge_run_core_metrics
Mode: advisory-write

Purpose:
- run Core Metric profile generation

Outputs:
- run_id
- metric summary
- stored metric refs

Reason:
- needed before seasonality and later scorecard chain

## 5.3 edge_run_seasonality
Mode: advisory-write

Purpose:
- run seasonality analysis using the prepared dataset and prior prerequisites

Outputs:
- seasonality summary
- session opportunity tables
- ranked hours/sessions

Reason:
- agent needs explicit opportunity windows, not only raw charts

## 5.4 edge_run_market_structure
Mode: advisory-write

Purpose:
- run market structure analysis and produce structural verdicts and scores

Outputs:
- market structure run id
- verdict
- confidence
- score groups
- tradeability overlay

Reason:
- this is one of the strongest edge interpretation inputs

## 5.5 edge_run_scorecard
Mode: advisory-write

Purpose:
- produce final Edge scorecard and strategy-fit ranking

Outputs:
- aggregate score
- named score breakdown
- ranked strategy archetypes
- readiness flags

Reason:
- this is the final compact edge interpretation layer

## 5.6 edge_list_snapshots
Mode: read-only

Purpose:
- list saved Edge profile snapshots for a symbol/timeframe or filter set

Outputs:
- snapshot headers
- versions
- timestamps

## 5.7 edge_get_snapshot
Mode: read-only

Purpose:
- load one snapshot with detail rows

Outputs:
- snapshot summary
- metric rows
- score rows
- strategy-fit rows

## 5.8 edge_compare_snapshots
Mode: read-only

Purpose:
- compare two Edge snapshots

Outputs:
- score deltas
- fit deltas
- notable changes
- comparison report refs

Reason:
- allows agents to detect improvement or degradation over time

## 5.9 edge_export_profile_report
Mode: advisory-write

Purpose:
- export JSON / Markdown pair report or comparison report

Outputs:
- artifact refs

---

## 6. Backtest and validation tools

## 6.1 backtest_list_runs
Mode: read-only

Purpose:
- list available backtest runs for a user and filter scope

## 6.2 backtest_get_run
Mode: read-only

Purpose:
- retrieve backtest run details and top summary metrics

## 6.3 backtest_get_trades
Mode: read-only

Purpose:
- retrieve backtest trades for audit or QA review

## 6.4 optimization_get_run
Mode: read-only

Purpose:
- retrieve optimization run summary and ranking state

## 6.5 optimization_get_top_results
Mode: read-only

Purpose:
- inspect the best ranked optimization candidates

## 6.6 validation_get_wfo_summary
Mode: read-only

Purpose:
- fetch walk-forward summary outputs

## 6.7 validation_get_wfm_summary
Mode: read-only

Purpose:
- fetch walk-forward matrix outputs

## 6.8 validation_get_monte_carlo_summary
Mode: read-only

Purpose:
- fetch Monte Carlo summary and stability signals

## 6.9 validation_get_sensitivity_report
Mode: read-only

Purpose:
- fetch parameter sensitivity and stability outputs

## 6.10 validation_get_manifest
Mode: read-only

Purpose:
- retrieve reproducibility metadata and version bindings for a strategy/run

## 6.11 validation_export_review_report
Mode: advisory-write

Purpose:
- export a structured validation/QA report

---

## 7. Risk tools

## 7.1 risk_get_current_state
Mode: read-only

Purpose:
- retrieve current canonical portfolio state or selected stored state

## 7.2 risk_build_snapshot
Mode: advisory-write

Purpose:
- build current descriptive risk snapshot from canonical state

Outputs:
- summary
- metric family rows
- governance and regime context

## 7.3 risk_build_scorecard
Mode: advisory-write

Purpose:
- build a scorecard from a snapshot

Outputs:
- named score rows
- overall score

## 7.4 risk_evaluate_governance
Mode: advisory-write

Purpose:
- evaluate a transition or current state through governance

Outputs:
- decision
- rule results
- warning/breach events

## 7.5 risk_get_recommendations
Mode: advisory-write

Purpose:
- run or fetch current recommendation pipeline output

Outputs:
- ranked recommendation batch
- impact deltas
- feasibility status

## 7.6 risk_run_what_if
Mode: advisory-write

Purpose:
- evaluate hypothetical portfolio changes without mutating baseline state

Outputs:
- before/after deltas
- scenario deltas
- governance deltas

Reason:
- one of the best agent-support tools for decision support

## 7.7 risk_get_scenarios
Mode: read-only

Purpose:
- retrieve scenario rows and worst-case summaries

## 7.8 risk_list_snapshots
Mode: read-only

Purpose:
- list persisted risk snapshots for a run or backtest

## 7.9 risk_get_snapshot
Mode: read-only

Purpose:
- retrieve one stored risk snapshot bundle

## 7.10 risk_export_report
Mode: advisory-write

Purpose:
- export stored risk report artifacts

---

## 8. Simulator and replay tools

## 8.1 sim_list_sessions
Mode: read-only

Purpose:
- list accessible simulator sessions

## 8.2 sim_get_session
Mode: read-only

Purpose:
- load session identity and current metadata

## 8.3 sim_preview_trade
Mode: advisory-write

Purpose:
- preview governance impact of a manual trade without executing it

Reason:
- perfect for trade review agent workflows

## 8.4 sim_run_what_if
Mode: advisory-write

Purpose:
- run simulator what-if analysis on current session state

## 8.5 sim_resume_session
Mode: advisory-write

Purpose:
- resume a paused simulation session

## 8.6 sim_stop_and_save
Mode: privileged

Purpose:
- persist a session into saved backtest/risk artifacts

## 8.7 replay_get_frames
Mode: read-only

Purpose:
- retrieve replay frames for timeline inspection

## 8.8 replay_compare_baseline_vs_hypothetical
Mode: advisory-write

Purpose:
- compare baseline replay state and hypothetical replay state

---

## 9. Live and execution tools

## 9.1 live_get_session_status
Mode: read-only

Purpose:
- retrieve live session health and status

## 9.2 live_get_positions
Mode: read-only

Purpose:
- fetch live positions for oversight

## 9.3 live_get_orders
Mode: read-only

Purpose:
- fetch live orders for oversight

## 9.4 live_get_logs
Mode: read-only

Purpose:
- fetch filtered live session logs

## 9.5 live_get_reconciliation_status
Mode: read-only

Purpose:
- fetch reconciliation and escalation state

## 9.6 live_get_execution_quality
Mode: read-only

Purpose:
- fetch slippage, latency, partial-fill, and execution-quality summaries

## 9.7 live_pause_session
Mode: privileged

Purpose:
- pause live operation under approved workflow

## 9.8 live_stop_session
Mode: privileged

Purpose:
- stop a live session under approved workflow

---

## 10. Reporting and workflow tools

## 10.1 report_generate_markdown
Mode: advisory-write

Purpose:
- generate operator-facing Markdown memo from saved artifacts

## 10.2 report_generate_json
Mode: advisory-write

Purpose:
- generate machine-readable report payloads

## 10.3 workflow_send_notification
Mode: advisory-write

Purpose:
- route message to Slack / Telegram / email / Notion through n8n or internal adapter

## 10.4 workflow_trigger_n8n
Mode: advisory-write

Purpose:
- trigger downstream n8n workflow with structured payload

## 10.5 workflow_create_incident_packet
Mode: advisory-write

Purpose:
- bundle evidence refs and summaries for incident escalation

---

## 11. Policy and approval tools

## 11.1 approval_request_action
Mode: advisory-write

Purpose:
- create an approval request for a privileged action

## 11.2 approval_get_status
Mode: read-only

Purpose:
- check approval status

## 11.3 approval_apply_decision
Mode: privileged

Purpose:
- apply approved or rejected decision outcome to workflow state

---

## 12. Agent-to-tool mapping

### Research Orchestrator
- edge_prepare_dataset
- edge_run_core_metrics
- edge_run_seasonality
- edge_run_market_structure
- edge_run_scorecard
- edge_list_snapshots
- edge_compare_snapshots
- edge_export_profile_report

### Edge Intelligence Agent
- edge_get_snapshot
- edge_compare_snapshots
- edge_export_profile_report

### Strategy QA Agent
- backtest_get_run
- backtest_get_trades
- optimization_get_run
- optimization_get_top_results
- validation_get_wfo_summary
- validation_get_wfm_summary
- validation_get_monte_carlo_summary
- validation_get_sensitivity_report
- validation_get_manifest
- validation_export_review_report

### Risk Supervisor Agent
- risk_get_current_state
- risk_build_snapshot
- risk_build_scorecard
- risk_evaluate_governance
- risk_get_recommendations
- risk_run_what_if
- risk_get_scenarios
- risk_export_report

### Execution Oversight Agent
- live_get_execution_quality
- live_get_logs
- live_get_reconciliation_status
- live_get_session_status

### Incident Investigator Agent
- replay_get_frames
- risk_get_snapshot
- live_get_logs
- workflow_create_incident_packet
- risk_run_what_if

### Portfolio Allocation Agent
- edge_get_snapshot
- validation_get_manifest
- risk_get_current_state
- risk_get_recommendations

### Live Operations Agent
- live_get_session_status
- workflow_send_notification
- workflow_trigger_n8n
- approval_request_action

---

## 13. Initial implementation priority

Recommended first tool groups:

### Priority 1
- Edge tools
- Risk tools
- Reporting tools

### Priority 2
- Backtest/validation tools
- Replay/incident tools

### Priority 3
- Live/execution tools
- Approval tools

This keeps the first release research- and robustness-first rather than autonomy-first.

---

## 14. Success criteria

The tool catalog is successful when:
- agents can perform useful work through structured tools only
- tool permissions are enforced cleanly
- evidence refs are preserved in agent outputs
- read-only analysis and advisory workflows cover the main HaruQuant decision loops
- privileged actions remain clearly separated and approval-gated
