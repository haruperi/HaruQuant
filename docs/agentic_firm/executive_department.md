# HaruQuant Agentic AI System — Executive Department

## Goal

Create the executive control layer for HaruQuant: one main user-facing interface through the **CEO Agent**, supported by a deterministic **Planner Agent**, governance policies, Board escalation, evidence-based decisioning, and safe delegation to specialist departments.

The Executive Department is responsible for coordinating the full agentic trading firm. It does not directly execute trades, approve risk, mutate live configuration, or bypass department-level deterministic policies. It receives user requests, plans the workflow, delegates to specialist agents, synthesizes evidence, applies governance rules, and returns a clear final memo to the user.

All Executive Department agents must follow the HaruQuant agent template:

```text
Validate Input
-> Gather Evidence / Context
-> Optional LLM Reasoning
-> Deterministic Policy Decision
-> Structured Output
-> Audit Log
-> Evaluation Test
```

The LLM may reason, summarize, classify, rank, or draft, but final workflow decisions must be controlled by deterministic code.

---

## 1. Department Scope

### 1.1 Primary Responsibilities

* [ ] Provide one main user-facing interface through the CEO Agent.
* [ ] Interpret user requests into structured firm tasks.
* [ ] Route work through the Planner Agent.
* [ ] Delegate to specialist departments.
* [ ] Require evidence for conclusions.
* [ ] Enforce Board escalation rules.
* [ ] Enforce refusal and safety rules.
* [ ] Enforce risk-policy references.
* [ ] Preserve auditability across all workflows.
* [ ] Produce final user-facing memos.
* [ ] Keep specialist agents isolated from direct chat access.
* [ ] Ensure chat requests enter through `services/ceo_gateway.py`.
* [ ] Ensure Planner decides which specialist evidence is required.
* [ ] Ensure CEO Agent owns final user-facing synthesis.

### 1.2 Non-Goals

* [ ] Do not execute trades.
* [ ] Do not approve risk.
* [ ] Do not bypass RiskGovernor.
* [ ] Do not directly mutate broker, account, or execution state.
* [ ] Do not let users casually trigger live trading actions.
* [ ] Do not expose specialist agents directly to the chat UI.
* [ ] Do not turn raw LLM output into final workflow decisions.
* [ ] Do not invent evidence, backtests, metrics, or approvals.
* [ ] Do not silently ignore missing evidence.

---

## 2. Standard Executive Department Folder Structure

```text
agents/
  executive/
    __init__.py

    ceo_agent/
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

    planner_agent/
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

    board_governance_agent/
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

    evidence_synthesis_agent/
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

    governance_auditor_agent/
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

    shared/
      executive_contracts.py
      routing.py
      response_templates.py
      escalation_rules.py
      workflow_states.py
      evidence_requirements.py
      permission_profiles.py
      audit.py

services/
  ceo_gateway.py

policies/
  firm_constitution.yaml
  executive_policy.yaml
  board_escalation_policy.yaml
  refusal_policy.yaml
  tool_policy.py
```

---

## 3. Executive Department Agents and Services

Recommended build order:

```text
1. Shared executive contracts
2. Planner Agent
3. CEO Agent
4. Evidence Synthesis Agent
5. Board Governance Agent
6. Governance Auditor Agent
7. CEO Gateway integration
8. End-to-end workflow tests
```

---

# 4. CEO Agent

## 4.1 Purpose

The **CEO Agent** is the main user-facing executive interface for HaruQuant. It receives the final structured plan and specialist outputs, synthesizes the evidence, applies executive governance, and returns the final memo to the user.

The CEO Agent is not a trading execution agent. It is a reasoning and synthesis layer sitting above specialist departments.

## 4.2 Required Files

* [ ] Create `agents/executive/ceo_agent/__init__.py`.
* [ ] Create `agents/executive/ceo_agent/agent.py`.
* [ ] Create `agents/executive/ceo_agent/contracts.py`.
* [ ] Create `agents/executive/ceo_agent/prompts.py`.
* [ ] Create `agents/executive/ceo_agent/deterministic_policy.py`.
* [ ] Create `agents/executive/ceo_agent/tools.py`.
* [ ] Create `agents/executive/ceo_agent/service.py`.
* [ ] Create `agents/executive/ceo_agent/evaluator.py`.
* [ ] Create `agents/executive/ceo_agent/README.md`.
* [ ] Create `agents/executive/ceo_agent/tests/test_contracts.py`.
* [ ] Create `agents/executive/ceo_agent/tests/test_deterministic_policy.py`.
* [ ] Create `agents/executive/ceo_agent/tests/test_service.py`.
* [ ] Create `agents/executive/ceo_agent/tests/test_agent_smoke.py`.

## 4.3 Responsibilities

* [ ] Receive structured request from `services/ceo_gateway.py`.
* [ ] Read Planner Agent output.
* [ ] Read specialist agent outputs.
* [ ] Read evidence references.
* [ ] Read firm constitution reference.
* [ ] Read risk policy reference.
* [ ] Read workflow state.
* [ ] Read Board escalation requirements.
* [ ] Validate that the requested task is allowed.
* [ ] Validate that required specialist evidence exists.
* [ ] Validate that high-risk actions are not being executed directly.
* [ ] Synthesize final executive memo.
* [ ] Explain what was done.
* [ ] Explain what was blocked.
* [ ] Explain what evidence was used.
* [ ] Explain what remains uncertain.
* [ ] Explain required next actions.
* [ ] Escalate to Board when required.
* [ ] Refuse unsafe or unsupported requests.
* [ ] Save final memo metadata to audit trail.

## 4.4 Inputs

| Field | Type | Required | Description |
|---|---|---:|---|
| `request_id` | str | Yes | Unique request identifier |
| `user_id` | str | Yes | User identifier |
| `task` | str | Yes | User request |
| `planner_output` | PlannerOutput | Yes | Structured workflow plan |
| `specialist_outputs` | list[AgentResponse] | No | Outputs from delegated agents |
| `context` | AgentContext | Yes | Session, portfolio, market, strategy, and risk context |
| `constraints` | dict | No | User, workflow, risk, or system constraints |

## 4.5 Tools

The CEO Agent should use read-only tools only.

* [ ] `read_firm_constitution`.
* [ ] `read_risk_policy_summary`.
* [ ] `read_board_escalation_policy`.
* [ ] `read_specialist_outputs`.
* [ ] `read_evidence_refs`.
* [ ] `read_workflow_state`.
* [ ] `read_strategy_lifecycle_state`.
* [ ] `read_portfolio_summary`.
* [ ] `read_audit_summary`.

## 4.6 Forbidden Tools

* [ ] No broker execution tools.
* [ ] No order router tools.
* [ ] No direct MT5/cTrader tools.
* [ ] No write access to risk thresholds.
* [ ] No direct modification of strategy lifecycle state.
* [ ] No direct database mutation unless explicitly allowed by a governed workflow.

## 4.7 LLM Responsibilities

The optional LLM may:

* [ ] Summarize specialist evidence.
* [ ] Explain reasoning in plain language.
* [ ] Draft investment/research/risk/reporting memos.
* [ ] Identify contradictions between specialist outputs.
* [ ] Highlight missing evidence.
* [ ] Propose next steps.
* [ ] Format responses for the user.

The optional LLM must not:

* [ ] Approve trades.
* [ ] Execute trades.
* [ ] Override RiskGovernor.
* [ ] Invent missing specialist results.
* [ ] Claim Board approval exists unless provided as evidence.
* [ ] Convert a rejected proposal into an approved one.

## 4.8 Deterministic Policy Rules

* [ ] If Planner output is missing, return `needs_more_context`.
* [ ] If task type is unsupported, return `rejected` or `clarification_required`.
* [ ] If specialist evidence is required but missing, block final recommendation.
* [ ] If RiskGovernor rejected an action, CEO response must preserve the rejection.
* [ ] If Board approval is required but absent, CEO response must request Board approval.
* [ ] If user asks for live execution without governed workflow approval, block the request.
* [ ] If user asks to bypass risk, refuse.
* [ ] If evidence references are missing, mark confidence as low.
* [ ] If specialist outputs conflict, require reconciliation or human review.
* [ ] If task is informational, allow response with cited evidence.
* [ ] If task is a governed action draft, return draft only and require approval.
* [ ] Final response type must match Planner task type.

## 4.9 Allowed Actions

* [ ] `synthesize_final_memo`.
* [ ] `summarize_specialist_outputs`.
* [ ] `request_clarification`.
* [ ] `draft_board_approval_request`.
* [ ] `explain_risk_rejection`.
* [ ] `explain_missing_evidence`.
* [ ] `recommend_next_workflow_step`.
* [ ] `prepare_governed_action_draft`.

## 4.10 Blocked Actions

* [ ] `execute_trade`.
* [ ] `approve_risk`.
* [ ] `override_risk_governor`.
* [ ] `modify_risk_thresholds`.
* [ ] `promote_strategy_without_board_approval`.
* [ ] `enable_live_mode`.
* [ ] `disable_kill_switch`.
* [ ] `directly_call_execution_bridge`.

## 4.11 Output Artifacts

* [ ] `executive_memo`.
* [ ] `decision_summary`.
* [ ] `evidence_summary`.
* [ ] `missing_evidence`.
* [ ] `blocked_actions`.
* [ ] `board_escalation_request`.
* [ ] `recommended_next_steps`.
* [ ] `audit_metadata`.

## 4.12 Tests Required

* [ ] Normal research memo case.
* [ ] Strategy creation memo case.
* [ ] Backtest diagnosis memo case.
* [ ] Risk rejection case.
* [ ] Missing evidence case.
* [ ] Board approval required case.
* [ ] Unsafe live execution request case.
* [ ] LLM tries to override deterministic block.
* [ ] Specialist output conflict case.
* [ ] Audit metadata completeness case.

---

# 5. Planner Agent

## 5.1 Purpose

The **Planner Agent** converts user requests into structured workflow plans. It determines intent, required context, required specialist agents, missing inputs, permission level, risk level, artifact expectations, and whether Board approval or governed action handling is required.

The Planner Agent must be deterministic at the final routing layer. The LLM may propose a plan, but `deterministic_policy.py` validates and finalizes the plan.

## 5.2 Required Files

* [ ] Create `agents/executive/planner_agent/__init__.py`.
* [ ] Create `agents/executive/planner_agent/agent.py`.
* [ ] Create `agents/executive/planner_agent/contracts.py`.
* [ ] Create `agents/executive/planner_agent/prompts.py`.
* [ ] Create `agents/executive/planner_agent/deterministic_policy.py`.
* [ ] Create `agents/executive/planner_agent/tools.py`.
* [ ] Create `agents/executive/planner_agent/service.py`.
* [ ] Create `agents/executive/planner_agent/evaluator.py`.
* [ ] Create `agents/executive/planner_agent/README.md`.
* [ ] Create `agents/executive/planner_agent/tests/test_contracts.py`.
* [ ] Create `agents/executive/planner_agent/tests/test_deterministic_policy.py`.
* [ ] Create `agents/executive/planner_agent/tests/test_service.py`.
* [ ] Create `agents/executive/planner_agent/tests/test_agent_smoke.py`.

## 5.3 Responsibilities

* [ ] Parse user request.
* [ ] Detect primary intent.
* [ ] Detect secondary intents.
* [ ] Detect missing inputs.
* [ ] Detect required context.
* [ ] Detect required evidence.
* [ ] Detect required specialist departments.
* [ ] Detect required specialist agents.
* [ ] Detect required backend tools.
* [ ] Detect required attached tools.
* [ ] Detect whether the task expects an artifact.
* [ ] Detect whether the task requires page action.
* [ ] Detect whether the task requires governed action handling.
* [ ] Detect whether the task requires Board approval.
* [ ] Detect whether the task is unsafe or forbidden.
* [ ] Classify risk level.
* [ ] Produce structured planner output.
* [ ] Block direct execution requests.
* [ ] Route final user-facing synthesis back to CEO Agent.

## 5.4 Supported Intent Types

* [ ] `research`.
* [ ] `strategy_creation`.
* [ ] `strategy_codegen`.
* [ ] `strategy_review`.
* [ ] `backtest`.
* [ ] `backtest_diagnosis`.
* [ ] `optimization_comparison`.
* [ ] `robustness_review`.
* [ ] `statistical_validation`.
* [ ] `risk_review`.
* [ ] `portfolio_review`.
* [ ] `allocation_review`.
* [ ] `paper_trading_review`.
* [ ] `execution_proposal`.
* [ ] `execution_readiness`.
* [ ] `incident_review`.
* [ ] `reporting`.
* [ ] `audit_review`.
* [ ] `cost_review`.
* [ ] `page_action`.
* [ ] `clarification`.
* [ ] `governed_action_draft`.
* [ ] `general_question`.
* [ ] `unsupported`.

## 5.5 Planner Output Fields

* [ ] `plan_id`.
* [ ] `request_id`.
* [ ] `user_intent`.
* [ ] `secondary_intents`.
* [ ] `missing_inputs`.
* [ ] `context_needed`.
* [ ] `evidence_needed`.
* [ ] `departments_to_run`.
* [ ] `agents_to_run`.
* [ ] `backend_tools_to_run`.
* [ ] `attached_tools`.
* [ ] `page_actions_to_plan`.
* [ ] `artifact_expected`.
* [ ] `artifact_type`.
* [ ] `risk_level`.
* [ ] `permission_profile`.
* [ ] `governed_action_required`.
* [ ] `board_approval_required`.
* [ ] `human_confirmation_required`.
* [ ] `blocked_actions`.
* [ ] `allowed_actions`.
* [ ] `execution_order`.
* [ ] `fallback_plan`.
* [ ] `planner_confidence`.
* [ ] `reasons`.

## 5.6 Intent Routing Rules

### Research

* [ ] Route to Research Department when the user asks for market context, strategy ideas, news, macro, sentiment, seasonality, or technical analysis.
* [ ] Required agents may include Market Intelligence, Technical Analyst, Strategy Scout, News/Sentiment, Macro, Cross-Asset, Seasonality, Strategy Hypothesis, and Research Validation.

### Strategy Creation

* [ ] Route to Strategy Creation Department when the user asks to create, formalize, code, review, or revise a strategy.
* [ ] Required agents may include Strategy Creator, Strategy Codegen, Strategy Reviewer, Spec Validator, Spec Storage, and Strategy Evidence Curator.

### Simulation

* [ ] Route to Simulation Department when the user asks to backtest, analyze results, optimize parameters, run robustness tests, or validate statistics.
* [ ] Required agents may include Backtest, Backtest Analyst, Optimization, Optimization Comparator, Robustness, Statistical Validation, and Simulation Evidence Curator.

### Risk

* [ ] Route to Risk Department when the user asks about risk review, risk approval, portfolio exposure, drawdown, VaR/CVaR, margin, or correlation risk.
* [ ] Required services may include RiskGovernor, Risk Reviewer, Portfolio Risk Monitor, Drawdown Control, VaR/CVaR, Correlation/Concentration, and Margin/Broker Risk.

### Portfolio

* [ ] Route to Portfolio Department when the user asks about strategy lifecycle, allocation, paper trading, live readiness, execution health, incident review, performance reporting, audit, or cost.
* [ ] Required agents/services may include Portfolio Manager, Allocation Optimizer, Strategy Lifecycle, Paper Execution, Live Execution, Execution Readiness, Kill Switch, Incident, Performance Reporter, Audit, and Cost Optimizer.

## 5.7 Deterministic Policy Rules

* [ ] If the request includes live execution, mark `governed_action_required = true`.
* [ ] If the request includes live execution, require RiskGovernor and Order Router evidence.
* [ ] If the request asks to bypass risk, reject.
* [ ] If the request asks to modify risk thresholds, require Board approval.
* [ ] If the request asks to promote a strategy to live, require Portfolio, Risk, Simulation, and Board evidence.
* [ ] If the request is missing symbol/timeframe for strategy creation, request clarification unless defaults are explicitly allowed.
* [ ] If the request asks to generate strategy code, require a validated StrategySpec.
* [ ] If the request asks to backtest code, require strategy code hash, data window, cost assumptions, and execution mode.
* [ ] If the request asks for risk review, require evidence from strategy, simulation, portfolio, and risk services.
* [ ] If the request asks for reporting, gather relevant existing evidence instead of running unrelated agents.
* [ ] If the request asks for unsafe action, route to refusal template.
* [ ] If intent confidence is low, return clarification plan.

## 5.8 Allowed Actions

* [ ] `create_structured_plan`.
* [ ] `request_clarification`.
* [ ] `select_specialist_agents`.
* [ ] `select_backend_tools`.
* [ ] `prepare_governed_action_draft`.
* [ ] `mark_board_approval_required`.
* [ ] `block_unsafe_request`.

## 5.9 Blocked Actions

* [ ] `execute_trade`.
* [ ] `approve_risk`.
* [ ] `modify_strategy_lifecycle_state`.
* [ ] `modify_risk_thresholds`.
* [ ] `call_broker_bridge_directly`.
* [ ] `override_specialist_rejection`.

## 5.10 Tests Required

* [ ] Strategy creation routing.
* [ ] Backtest diagnosis routing.
* [ ] Optimization comparison routing.
* [ ] Risk review routing.
* [ ] Research routing.
* [ ] Reporting routing.
* [ ] Page action routing.
* [ ] Governed action routing.
* [ ] Clarification routing.
* [ ] Unsafe request rejection.
* [ ] Missing input detection.
* [ ] Board approval detection.
* [ ] LLM routing proposal cannot bypass deterministic policy.

---

# 6. Board Governance Agent

## 6.1 Purpose

The **Board Governance Agent** determines whether a proposed workflow or decision requires explicit human/Board approval before execution, promotion, deployment, or configuration change.

This agent may use optional LLM reasoning to explain governance requirements, but the final approval requirement must come from deterministic policy.

## 6.2 Required Files

* [ ] Create `agents/executive/board_governance_agent/__init__.py`.
* [ ] Create `agents/executive/board_governance_agent/agent.py`.
* [ ] Create `agents/executive/board_governance_agent/contracts.py`.
* [ ] Create `agents/executive/board_governance_agent/prompts.py`.
* [ ] Create `agents/executive/board_governance_agent/deterministic_policy.py`.
* [ ] Create `agents/executive/board_governance_agent/tools.py`.
* [ ] Create `agents/executive/board_governance_agent/service.py`.
* [ ] Create `agents/executive/board_governance_agent/evaluator.py`.
* [ ] Create `agents/executive/board_governance_agent/README.md`.
* [ ] Create `agents/executive/board_governance_agent/tests/`.

## 6.3 Responsibilities

* [ ] Read Board escalation policy.
* [ ] Read firm constitution.
* [ ] Read risk policy.
* [ ] Read proposed workflow plan.
* [ ] Read specialist outputs.
* [ ] Read RiskGovernor output when relevant.
* [ ] Detect whether Board approval is required.
* [ ] Detect whether human confirmation is required.
* [ ] Detect whether request must be refused.
* [ ] Draft Board approval request.
* [ ] Track approval status.
* [ ] Track approval expiration.
* [ ] Track approval scope.
* [ ] Track approval conditions.

## 6.4 Board Approval Required For

* [ ] Enabling live trading.
* [ ] Promoting a strategy to live.
* [ ] Increasing live allocation above current approved limit.
* [ ] Changing risk thresholds.
* [ ] Disabling or weakening RiskGovernor rules.
* [ ] Disabling or weakening kill switch rules.
* [ ] Resuming live trading after a critical incident.
* [ ] Changing execution bridge permissions.
* [ ] Adding a new broker/exchange integration.
* [ ] Approving capital allocation changes.
* [ ] Retiring a live strategy if it affects portfolio exposure materially.
* [ ] Deploying a strategy with weak or incomplete evidence.

## 6.5 Deterministic Policy Rules

* [ ] If action touches live capital, Board approval is required unless already approved within scope.
* [ ] If action modifies risk policy, Board approval is required.
* [ ] If action modifies execution permissions, Board approval is required.
* [ ] If action follows critical incident, Board approval is required before resume.
* [ ] If approval is expired, require new approval.
* [ ] If approval scope does not match requested action, require new approval.
* [ ] If evidence package is incomplete, block Board approval request as incomplete.
* [ ] If action is forbidden by firm constitution, reject instead of escalating.

## 6.6 Output Artifacts

* [ ] `board_escalation_decision`.
* [ ] `board_approval_request`.
* [ ] `approval_scope`.
* [ ] `approval_conditions`.
* [ ] `approval_expiration`.
* [ ] `missing_evidence`.
* [ ] `rejection_reason`.

## 6.7 Tests Required

* [ ] Live promotion requires Board approval.
* [ ] Risk threshold change requires Board approval.
* [ ] Expired approval is rejected.
* [ ] Mismatched approval scope is rejected.
* [ ] Forbidden action is rejected.
* [ ] Incomplete evidence blocks approval request.

---

# 7. Evidence Synthesis Agent

## 7.1 Purpose

The **Evidence Synthesis Agent** merges outputs from specialist agents into a structured evidence package for the CEO Agent. It prevents the CEO Agent from relying on scattered, inconsistent, missing, or low-quality evidence.

## 7.2 Required Files

* [ ] Create `agents/executive/evidence_synthesis_agent/__init__.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/agent.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/contracts.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/prompts.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/deterministic_policy.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/tools.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/service.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/evaluator.py`.
* [ ] Create `agents/executive/evidence_synthesis_agent/README.md`.
* [ ] Create `agents/executive/evidence_synthesis_agent/tests/`.

## 7.3 Responsibilities

* [ ] Read all specialist outputs.
* [ ] Normalize evidence into common structure.
* [ ] Deduplicate evidence references.
* [ ] Identify missing evidence.
* [ ] Identify contradictory evidence.
* [ ] Identify stale evidence.
* [ ] Identify low-confidence evidence.
* [ ] Separate facts from recommendations.
* [ ] Separate deterministic decisions from LLM suggestions.
* [ ] Build final evidence package for CEO Agent.
* [ ] Preserve source links and artifact references.
* [ ] Preserve audit metadata.

## 7.4 Evidence Package Fields

* [ ] `evidence_package_id`.
* [ ] `request_id`.
* [ ] `workflow_id`.
* [ ] `specialist_outputs`.
* [ ] `evidence_refs`.
* [ ] `facts`.
* [ ] `recommendations`.
* [ ] `deterministic_decisions`.
* [ ] `llm_observations`.
* [ ] `missing_evidence`.
* [ ] `contradictions`.
* [ ] `stale_evidence`.
* [ ] `confidence_summary`.
* [ ] `risk_summary`.
* [ ] `audit_refs`.

## 7.5 Deterministic Policy Rules

* [ ] If required evidence is missing, mark package incomplete.
* [ ] If evidence references are missing, mark package low confidence.
* [ ] If deterministic decisions conflict, escalate to CEO and Board if critical.
* [ ] If LLM recommendation conflicts with deterministic decision, preserve deterministic decision.
* [ ] If evidence is stale beyond policy, require refresh.
* [ ] If evidence package contains unsafe action proposal, mark as governed action.

## 7.6 Tests Required

* [ ] Complete evidence package case.
* [ ] Missing evidence case.
* [ ] Contradictory specialist output case.
* [ ] Stale evidence case.
* [ ] LLM suggestion conflicts with deterministic policy case.
* [ ] Audit references retained case.

---

# 8. Governance Auditor Agent

## 8.1 Purpose

The **Governance Auditor Agent** verifies that executive workflows obey the firm constitution, planner routing rules, Board escalation policy, tool permission policy, and evidence requirements.

## 8.2 Required Files

* [ ] Create `agents/executive/governance_auditor_agent/__init__.py`.
* [ ] Create `agents/executive/governance_auditor_agent/agent.py`.
* [ ] Create `agents/executive/governance_auditor_agent/contracts.py`.
* [ ] Create `agents/executive/governance_auditor_agent/prompts.py`.
* [ ] Create `agents/executive/governance_auditor_agent/deterministic_policy.py`.
* [ ] Create `agents/executive/governance_auditor_agent/tools.py`.
* [ ] Create `agents/executive/governance_auditor_agent/service.py`.
* [ ] Create `agents/executive/governance_auditor_agent/evaluator.py`.
* [ ] Create `agents/executive/governance_auditor_agent/README.md`.
* [ ] Create `agents/executive/governance_auditor_agent/tests/`.

## 8.3 Responsibilities

* [ ] Check every executive workflow has a Planner output.
* [ ] Check every CEO final memo references evidence.
* [ ] Check governed actions are not executed directly.
* [ ] Check Board approval is requested where required.
* [ ] Check unsafe requests are refused.
* [ ] Check planner-selected agents match task type.
* [ ] Check specialist outputs are not bypassed.
* [ ] Check RiskGovernor decisions are preserved.
* [ ] Check audit metadata exists.
* [ ] Check permission profile is valid.
* [ ] Check no hidden mutation happened during read-only workflows.
* [ ] Generate governance audit report.

## 8.4 Audit Severity

* [ ] `info`.
* [ ] `warning`.
* [ ] `major`.
* [ ] `critical`.

## 8.5 Critical Failures

* [ ] CEO response claims approval without approval evidence.
* [ ] Planner routes live execution without governed action.
* [ ] Board approval required but skipped.
* [ ] RiskGovernor rejection is overridden.
* [ ] Execution bridge called directly from Executive Department.
* [ ] Missing audit trail for governed workflow.
* [ ] Hidden tool call modifies risk/execution configuration.

## 8.6 Deterministic Policy Rules

* [ ] If critical failure is detected, mark workflow invalid.
* [ ] If live-related critical failure is detected, recommend live trading lockout.
* [ ] If missing evidence is detected, mark memo incomplete.
* [ ] If Board approval is skipped, block workflow.
* [ ] If RiskGovernor rejection is overridden, block workflow and create critical audit finding.

## 8.7 Tests Required

* [ ] Valid executive workflow case.
* [ ] Missing Planner output case.
* [ ] Missing evidence case.
* [ ] Board approval skipped case.
* [ ] RiskGovernor override attempt case.
* [ ] Direct execution bridge call case.
* [ ] Missing audit metadata case.

---

# 9. Shared Executive Contracts

## 9.1 Planner Output Contract

* [ ] Create `PlannerOutput` Pydantic model.
* [ ] Add `plan_id`.
* [ ] Add `request_id`.
* [ ] Add `user_intent`.
* [ ] Add `secondary_intents`.
* [ ] Add `missing_inputs`.
* [ ] Add `context_needed`.
* [ ] Add `evidence_needed`.
* [ ] Add `departments_to_run`.
* [ ] Add `agents_to_run`.
* [ ] Add `backend_tools_to_run`.
* [ ] Add `attached_tools`.
* [ ] Add `page_actions_to_plan`.
* [ ] Add `artifact_expected`.
* [ ] Add `artifact_type`.
* [ ] Add `risk_level`.
* [ ] Add `permission_profile`.
* [ ] Add `governed_action_required`.
* [ ] Add `board_approval_required`.
* [ ] Add `human_confirmation_required`.
* [ ] Add `allowed_actions`.
* [ ] Add `blocked_actions`.
* [ ] Add `execution_order`.
* [ ] Add `fallback_plan`.
* [ ] Add `confidence`.
* [ ] Add `reasons`.

## 9.2 Executive Memo Contract

* [ ] Create `ExecutiveMemo` Pydantic model.
* [ ] Add `memo_id`.
* [ ] Add `request_id`.
* [ ] Add `memo_type`.
* [ ] Add `summary`.
* [ ] Add `decision`.
* [ ] Add `evidence_reviewed`.
* [ ] Add `key_findings`.
* [ ] Add `risks`.
* [ ] Add `blocked_actions`.
* [ ] Add `recommended_next_steps`.
* [ ] Add `board_action_required`.
* [ ] Add `confidence`.
* [ ] Add `limitations`.
* [ ] Add `audit_refs`.

## 9.3 Board Approval Request Contract

* [ ] Create `BoardApprovalRequest` Pydantic model.
* [ ] Add `approval_request_id`.
* [ ] Add `request_id`.
* [ ] Add `workflow_id`.
* [ ] Add `decision_type`.
* [ ] Add `action_requested`.
* [ ] Add `evidence_package_id`.
* [ ] Add `risk_summary`.
* [ ] Add `expected_impact`.
* [ ] Add `approval_scope`.
* [ ] Add `approval_conditions`.
* [ ] Add `expiration_time`.
* [ ] Add `required_human`.
* [ ] Add `status`.

## 9.4 Evidence Package Contract

* [ ] Create `ExecutiveEvidencePackage` Pydantic model.
* [ ] Add `evidence_package_id`.
* [ ] Add `request_id`.
* [ ] Add `workflow_id`.
* [ ] Add `specialist_outputs`.
* [ ] Add `evidence_refs`.
* [ ] Add `deterministic_decisions`.
* [ ] Add `llm_observations`.
* [ ] Add `facts`.
* [ ] Add `recommendations`.
* [ ] Add `missing_evidence`.
* [ ] Add `contradictions`.
* [ ] Add `stale_evidence`.
* [ ] Add `confidence_summary`.
* [ ] Add `audit_refs`.

---

# 10. CEO Response Templates

## 10.1 Research Memo Template

* [ ] Add `research_question`.
* [ ] Add `market_context`.
* [ ] Add `evidence_reviewed`.
* [ ] Add `key_findings`.
* [ ] Add `candidate_ideas`.
* [ ] Add `risks`.
* [ ] Add `confidence`.
* [ ] Add `recommended_next_steps`.
* [ ] Add `blocked_actions`.

## 10.2 Strategy Proposal Template

* [ ] Add `strategy_name`.
* [ ] Add `strategy_type`.
* [ ] Add `symbol`.
* [ ] Add `timeframe`.
* [ ] Add `market_assumption`.
* [ ] Add `entry_logic_summary`.
* [ ] Add `exit_logic_summary`.
* [ ] Add `position_management_summary`.
* [ ] Add `risk_assumptions`.
* [ ] Add `test_plan`.
* [ ] Add `implementation_status`.
* [ ] Add `review_status`.
* [ ] Add `next_steps`.

## 10.3 Backtest Report Template

* [ ] Add `strategy_id`.
* [ ] Add `backtest_run_id`.
* [ ] Add `data_window`.
* [ ] Add `cost_assumptions`.
* [ ] Add `execution_mode`.
* [ ] Add `summary_metrics`.
* [ ] Add `equity_curve_summary`.
* [ ] Add `drawdown_summary`.
* [ ] Add `trade_distribution_summary`.
* [ ] Add `long_short_summary`.
* [ ] Add `diagnosis`.
* [ ] Add `acceptance_status`.
* [ ] Add `recommended_next_steps`.

## 10.4 Risk Memo Template

* [ ] Add `strategy_summary`.
* [ ] Add `evidence_reviewed`.
* [ ] Add `RiskGovernor_result`.
* [ ] Add `key_risk_metrics`.
* [ ] Add `portfolio_impact`.
* [ ] Add `correlation_concerns`.
* [ ] Add `drawdown_concerns`.
* [ ] Add `cost_concerns`.
* [ ] Add `failure_modes`.
* [ ] Add `recommendation`.
* [ ] Add `required_board_action`.

## 10.5 Portfolio Review Template

* [ ] Add `portfolio_summary`.
* [ ] Add `active_strategies`.
* [ ] Add `paper_strategies`.
* [ ] Add `promotion_candidates`.
* [ ] Add `demotion_candidates`.
* [ ] Add `retirement_candidates`.
* [ ] Add `allocation_recommendations`.
* [ ] Add `RiskGovernor_constraints`.
* [ ] Add `Board_actions_required`.

## 10.6 Board Approval Request Template

* [ ] Add `action_requested`.
* [ ] Add `why_action_is_needed`.
* [ ] Add `evidence_package`.
* [ ] Add `risk_summary`.
* [ ] Add `expected_benefit`.
* [ ] Add `worst_case_risk`.
* [ ] Add `approval_scope`.
* [ ] Add `approval_conditions`.
* [ ] Add `expiration`.
* [ ] Add `human_decision_required`.

## 10.7 Rejection Template

* [ ] Add `request_summary`.
* [ ] Add `rejection_reason`.
* [ ] Add `policy_or_evidence_basis`.
* [ ] Add `safe_alternative`.
* [ ] Add `next_possible_action`.

## 10.8 Blocked-by-Risk Template

* [ ] Add `proposal_summary`.
* [ ] Add `RiskGovernor_decision`.
* [ ] Add `blocked_actions`.
* [ ] Add `risk_metrics_snapshot`.
* [ ] Add `specific_reasons`.
* [ ] Add `possible_safe_modifications`.
* [ ] Add `required_next_review`.

---

# 11. Executive Permission Model

## 11.1 CEO Agent Permissions

```python
CEO_AGENT_PERMISSIONS = {
    "can_read_specialist_outputs": True,
    "can_read_firm_constitution": True,
    "can_read_risk_policy": True,
    "can_read_board_policy": True,
    "can_synthesize_final_memo": True,
    "can_draft_board_request": True,
    "can_execute_trade": False,
    "can_approve_risk": False,
    "can_modify_risk_thresholds": False,
    "can_modify_live_mode": False,
    "can_call_broker_bridge": False,
}
```

## 11.2 Planner Agent Permissions

```python
PLANNER_AGENT_PERMISSIONS = {
    "can_classify_intent": True,
    "can_select_specialist_agents": True,
    "can_select_read_only_tools": True,
    "can_mark_governed_action_required": True,
    "can_mark_board_approval_required": True,
    "can_execute_trade": False,
    "can_approve_risk": False,
    "can_call_broker_bridge": False,
    "can_modify_database": False,
}
```

## 11.3 Board Governance Agent Permissions

```python
BOARD_GOVERNANCE_AGENT_PERMISSIONS = {
    "can_read_board_policy": True,
    "can_evaluate_approval_requirement": True,
    "can_draft_approval_request": True,
    "can_record_approval_status": True,
    "can_execute_trade": False,
    "can_approve_risk": False,
    "can_override_risk_governor": False,
}
```

---

# 12. Executive Audit Requirements

Every Executive Department response must include:

* [ ] `request_id`.
* [ ] `workflow_id`.
* [ ] `agent_name`.
* [ ] `planner_output_id`.
* [ ] `evidence_package_id`.
* [ ] `specialist_agents_called`.
* [ ] `tools_called`.
* [ ] `permission_profile`.
* [ ] `risk_level`.
* [ ] `governed_action_required`.
* [ ] `board_approval_required`.
* [ ] `board_approval_id` if available.
* [ ] `blocked_actions`.
* [ ] `allowed_actions`.
* [ ] `prompt_version`.
* [ ] `policy_version`.
* [ ] `model_provider`.
* [ ] `model_name`.
* [ ] `fallback_used`.
* [ ] `context_revision`.
* [ ] `evidence_refs`.
* [ ] `created_at`.

---

# 13. Executive Workflow States

* [ ] `received`.
* [ ] `planning`.
* [ ] `clarification_required`.
* [ ] `delegating`.
* [ ] `waiting_for_specialist_outputs`.
* [ ] `evidence_synthesis`.
* [ ] `governance_review`.
* [ ] `board_approval_required`.
* [ ] `blocked_by_policy`.
* [ ] `blocked_by_risk`.
* [ ] `memo_drafting`.
* [ ] `completed`.
* [ ] `failed`.

---

# 14. Executive Department Handoff Contracts

## 14.1 Research Handoff

* [ ] Send research questions to Research Department.
* [ ] Receive research report package.
* [ ] Receive validated hypotheses.
* [ ] Receive evidence references.
* [ ] CEO synthesizes research memo.

## 14.2 Strategy Creation Handoff

* [ ] Send strategy request or approved hypothesis.
* [ ] Receive StrategySpec.
* [ ] Receive generated code package if requested.
* [ ] Receive reviewer report.
* [ ] CEO synthesizes strategy proposal memo.

## 14.3 Simulation Handoff

* [ ] Send strategy code hash, spec, period, costs, and execution mode.
* [ ] Receive immutable backtest package.
* [ ] Receive diagnosis.
* [ ] Receive optimization/robustness/statistical validation outputs.
* [ ] CEO synthesizes simulation memo.

## 14.4 Risk Handoff

* [ ] Send strategy evidence and portfolio context.
* [ ] Receive RiskGovernor output.
* [ ] Receive risk reviewer memo.
* [ ] CEO preserves deterministic risk decision.
* [ ] CEO explains risk decision to user.

## 14.5 Portfolio Handoff

* [ ] Send strategy lifecycle review request.
* [ ] Receive allocation recommendations.
* [ ] Receive paper/live performance evidence.
* [ ] Receive Board approval requirement.
* [ ] CEO synthesizes portfolio decision memo.

## 14.6 Execution Handoff

* [ ] Executive Department may only draft execution proposals.
* [ ] Execution requires governed workflow.
* [ ] Execution requires RiskGovernor approval token.
* [ ] Execution requires live mode enabled.
* [ ] Execution requires Order Router validation.
* [ ] Execution requires audit logging available.
* [ ] CEO may report status but must not directly execute.

---

# 15. Refusal and Safety Rules

The Executive Department must refuse or block:

* [ ] Requests to bypass RiskGovernor.
* [ ] Requests to bypass Board approval.
* [ ] Requests to execute live trades without approved workflow.
* [ ] Requests to disable kill switch without Board approval.
* [ ] Requests to hide failed trades, failed backtests, or audit logs.
* [ ] Requests to fabricate evidence or performance.
* [ ] Requests to ignore costs, slippage, spread, or drawdown.
* [ ] Requests to promote a strategy without validation.
* [ ] Requests to modify risk limits without governed approval.
* [ ] Requests to use unapproved external tools for trading-critical decisions.

---

# 16. Evaluation Requirements

## 16.1 CEO Agent Evaluation

* [ ] Response contains valid `AgentResponse` envelope.
* [ ] Response includes final memo artifact.
* [ ] Response includes evidence references.
* [ ] Response preserves specialist deterministic decisions.
* [ ] Response preserves RiskGovernor rejection.
* [ ] Response marks Board approval when required.
* [ ] Response does not execute or approve trades.
* [ ] Response handles missing evidence safely.
* [ ] Response includes audit metadata.

## 16.2 Planner Agent Evaluation

* [ ] Planner output validates against schema.
* [ ] Planner detects correct intent.
* [ ] Planner detects missing inputs.
* [ ] Planner detects governed actions.
* [ ] Planner detects Board approval requirement.
* [ ] Planner rejects unsafe requests.
* [ ] Planner selects correct specialist agents.
* [ ] Planner avoids direct broker/execution calls.
* [ ] Planner includes audit metadata.

## 16.3 Board Governance Evaluation

* [ ] Board approval requirement is detected correctly.
* [ ] Approval scope is enforced.
* [ ] Expired approvals are rejected.
* [ ] Forbidden actions are rejected instead of escalated.
* [ ] Missing evidence blocks approval request.

## 16.4 Governance Auditor Evaluation

* [ ] Valid workflow passes.
* [ ] Missing Planner output fails.
* [ ] Missing evidence fails.
* [ ] Risk override attempt fails.
* [ ] Direct execution attempt fails.
* [ ] Missing audit trail fails.

---

# 17. Definition of Done

The Executive Department is complete only when:

* [ ] CEO Agent exists as a standard HaruQuant agent service.
* [ ] Planner Agent exists as a standard HaruQuant agent service.
* [ ] Board Governance Agent exists as a standard HaruQuant agent service.
* [ ] Evidence Synthesis Agent exists as a standard HaruQuant agent service.
* [ ] Governance Auditor Agent exists as a standard HaruQuant agent service.
* [ ] Every agent has `agent.py`, `contracts.py`, `prompts.py`, `deterministic_policy.py`, `tools.py`, `service.py`, `evaluator.py`, `README.md`, and tests.
* [ ] Chat requests enter through `services/ceo_gateway.py`.
* [ ] Planner produces structured planner output.
* [ ] Specialist agents are never called directly by the chat UI.
* [ ] CEO Agent produces final user-facing memos.
* [ ] CEO Agent preserves deterministic specialist decisions.
* [ ] RiskGovernor decisions cannot be overridden.
* [ ] Board approval is required for governed actions.
* [ ] Evidence references are required for conclusions.
* [ ] Unsafe requests are refused.
* [ ] Audit metadata is produced for every executive workflow.
* [ ] Tests cover normal, missing-evidence, governed-action, Board-approval, unsafe-request, and risk-rejection cases.

---

# 18. Final Architecture Rule

```text
The CEO Agent is the user-facing executive synthesizer.
The Planner Agent is the deterministic workflow router.
Specialist agents produce evidence.
RiskGovernor controls risk approval.
Board Governance controls human approval.
Execution services execute only approved orders.
CEOChatGateway is the only chat entrypoint.
```

The Executive Department must make HaruQuant feel like one coherent trading firm instead of a collection of unrelated agents.
