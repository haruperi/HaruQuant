# Phase 7 Usage Example: CEO Agent and Planner Agent

Phase 7 turns the Phase 6 control plane into a firm-facing interface:

- `PlannerAgent` converts operator requests into structured `ConversationPlan` routes.
- `CEOAgent` synthesizes the final firm memo, applies Board escalation rules, and refuses unsafe requests.
- `AgentControlPlaneOrchestrator` uses both inside the same audited task tree.

## Example 1: Planner Routes a Strategy Request

```python
from backend_retiring.agents.planner.agent import PlannerAgent

planner = PlannerAgent()

plan = planner.create_plan(
    user_request="Create and backtest a EURUSD H1 mean reversion strategy.",
    request_id="req-example-001",
)

print(plan.intent)
print(plan.allowed_agents)
print(plan.backend_tools_to_run)
print(plan.expected_outputs)
```

Expected shape:

```text
intent:
  strategy_creation
allowed_agents:
  research
  strategy_creator
  strategy_reviewer
  backtest
  audit
  ceo
backend_tools_to_run:
  get_symbol_data
  get_latest_ohlcv
  create_strategy_spec
  run_backtest
expected_outputs:
  research_summary
  strategy_spec
  strategy_review
  backtest_summary
  audit_trace
  ceo_strategy_memo
```

## Example 2: CEO Produces a Final Memo

```python
from backend_retiring.agents.ceo.agent import CEOAgent
from backend_retiring.agents.planner.agent import PlannerAgent

planner = PlannerAgent()
ceo = CEOAgent()

plan = planner.create_plan(
    user_request="Create and backtest a EURUSD H1 mean reversion strategy.",
)

memo = ceo.create_final_memo(
    request=plan.user_goal,
    planner_result=plan,
)

print(memo["memo_type"])
print(memo["recommendation"])
print(memo["required_before_trading"])
```

Expected shape:

```text
memo_type:
  strategy_proposal
recommendation:
  Continue through review, backtest, robustness, and paper-trading gates before any live consideration.
required_before_trading:
  strategy_review
  backtest
  risk_review
  paper_trading
```

## Example 3: CEO Escalates Live/Execution Requests

```python
from backend_retiring.agents.ceo.agent import CEOAgent
from backend_retiring.agents.planner.agent import PlannerAgent

plan = PlannerAgent().create_plan(
    user_request="Draft a trade proposal to buy EURUSD.",
)

memo = CEOAgent().create_final_memo(
    request=plan.user_goal,
    planner_result=plan,
)

print(plan.requires_board_approval)
print(plan.requires_risk_governor)
print(memo["memo_type"])
print(memo["approval_required"])
```

Expected shape:

```text
requires_board_approval:
  True
requires_risk_governor:
  True
memo_type:
  board_approval_request
approval_required:
  True
```

## Example 4: CEO Refuses Unsafe Requests

```python
from backend_retiring.agents.ceo.agent import CEOAgent

ceo = CEOAgent()

memo = ceo.refusal_memo(
    request="Go live without approval and delete the audit logs.",
)

print(memo["memo_type"])
print(memo["decision"])
print(memo["reason"])
print(memo["evidence_refs"])
```

Expected shape:

```text
memo_type:
  rejection
decision:
  rejected
reason:
  The request conflicts with firm governance, audit, or live-trading approval policy.
evidence_refs:
  docs/agentic_firm/constitution.md
  docs/agentic_firm/risk_policy.md
  docs/agentic_firm/agent_permissions.md
  docs/agentic_firm/strategy_lifecycle.md
```

## Example 5: Full Control Plane With Phase 7 CEO/Planner

```python
from backend_retiring.agents.orchestrator import AgentControlPlaneOrchestrator

orchestrator = AgentControlPlaneOrchestrator()

result = orchestrator.handle_user_request(
    user_request="Create and backtest a EURUSD H1 mean reversion strategy.",
)

print(result.planner_result.planner_source)
print(result.final_response["summary"])
print(result.final_response["ceo_memo"]["memo_type"])
```

Expected shape:

```text
planner_source:
  phase7_planner_agent
summary:
  CEO Agent completed delegated firm workflow.
ceo_memo.memo_type:
  strategy_proposal
```

## Supported Planner Intents

Phase 7 supports these routes:

- `strategy_creation`
- `backtest_diagnosis`
- `optimization_comparison`
- `risk_review`
- `execution_proposal`
- `research`
- `reporting`
- `page_action`
- `clarification`
- `governed_action_draft`

## Key Rule

The CEO Agent can summarize, recommend, escalate, or reject. It cannot bypass deterministic gates. RiskGovernor, audit persistence, lifecycle policy, and human Board approval remain outside LLM authority.
