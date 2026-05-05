# Phase 2 Repository Refactor Plan

**Date:** 2026-05-03

**Purpose:** Move HaruQuant from a collection of capable individual agents and services toward a top-down Agentic Trading Firm repository structure without losing existing backtesting, optimization, risk, execution, audit, and UI functionality.

This plan follows `docs/agentic_firm/Implementation_plan.md`, but adapts Phase 2 to the codebase that already exists. The repository is not empty: it already contains a substantial backend under `backend/`, a public `haruquant` package, a Next.js UI under `ui/`, and tests across unit, integration, scenario, replay, security, and acceptance layers.

## Phase 2 Goal

Create the physical homes for the trading firm:

- executive and departmental agents
- governed tools
- deterministic risk and execution gates
- memory and evidence storage
- human-readable reports

The key migration rule is:

```text
Create new firm-facing structure first, then migrate or wrap behavior behind compatibility exports. Do not move working modules directly unless imports, tests, and UI routes are updated in the same slice.
```

## Current Repository Findings

### Existing Strengths To Preserve

The current backend already contains many pieces needed by the Agentic Firm:

| Firm capability | Existing implementation area |
| --- | --- |
| Agent runtime, prompts, tool allowlists, workflow runners | `backend/agents/`, `backend/agents/runtime/`, `backend/agents/chat/` |
| Conversation planner and chat orchestration | `backend/agents/chat/ai_chat/` |
| Deterministic workflows and transitions | `backend/orchestration/workflow/` |
| Typed contracts and schema registry | `backend/contracts/` |
| Read-only chat tools | `backend/tools/read_only/` |
| Risk decisions, exposure, correlation, margin, restrictions | `services/risk/` |
| Larger risk engine and VaR/CVaR/correlation metrics | `services/risk/` |
| Kill switch and safety blocking | `services/risk/safety/` |
| Execution readiness, intents, sends, receipts | `services/execution/` |
| Live trading runtime and MT5 compatibility | `services/execution/live/`, `backend/mcp/mt5_mcp/` |
| Strategy lifecycle, promotion, retirement, evidence | `services/strategy/governance/`, `services/strategy/evidence/` |
| Strategy framework and generated strategies | `services/strategy/`, `backend/data/strategies/` |
| Backtesting/simulation | `services/simulation/`, `backend/api/routes/backtest.py` |
| Optimization and robustness tooling | `services/optimization/`, `backend/mcp/optimization_mcp/` |
| Research and market structure tooling | `services/research/`, `backend/api/routes/edge.py` |
| Portfolio analytics and advisory proposals | `services/risk/portfolio/` |
| Audit, replay, export, legal hold, signing | `services/strategy/evidence/audit/` |
| Operator API | `backend/api/` |
| Frontend | `ui/` |

### Phase 2 Checklist Gap

Only the high-level `backend/agents/` and `backend/tools/` folders already exist. The department folders from the new Agentic Firm plan do not yet exist:

- `backend/agents/ceo/`
- `backend/agents/planner/`
- `backend/agents/research/`
- `backend/agents/strategy_creator/`
- `backend/agents/strategy_reviewer/`
- `backend/agents/codegen/`
- `backend/agents/backtest/`
- `backend/agents/optimization/`
- `backend/agents/robustness/`
- `backend/agents/statistical_validation/`
- `backend/agents/risk_reviewer/`
- `backend/agents/portfolio_manager/`
- `backend/agents/execution/`
- `backend/agents/performance_reporter/`
- `backend/agents/audit/`
- `backend/agents/cost_optimizer/`

The new top-level `memory/` and `reports/` trees also do not exist yet.

### Important Design Adjustment

The implementation plan names files such as `backend/risk/governor.py` and `backend/execution/order_router.py`. The live codebase already has richer deterministic service packages under:

- `services/risk/`
- `services/risk/`
- `services/risk/safety/`
- `services/execution/`
- `services/execution/live/`
- `backend/mcp/mt5_mcp/`

For Phase 2, we should not duplicate that logic into a parallel `backend/risk` and `backend/execution` stack. Instead:

1. Create `backend/risk/` and `backend/execution/` as firm-facing compatibility façades.
2. Re-export or wrap the existing deterministic services.
3. Keep business logic in `backend/services/*` until a later, tested migration proves a better final layout.

This prevents two competing RiskGovernors, two order routers, or two kill switches.

## Target Repository Shape

### Agent Departments

Create department folders under `backend/agents/`:

```text
backend/agents/
  ceo/
  planner/
  research/
  strategy_creator/
  strategy_reviewer/
  codegen/
  backtest/
  optimization/
  robustness/
  statistical_validation/
  risk_reviewer/
  portfolio_manager/
  execution/
  performance_reporter/
  audit/
  cost_optimizer/
```

Each department should initially contain:

- `__init__.py`
- `README.md`
- `agent.py` only when there is already a safe wrapper or adapter to expose

Do not move existing agent files immediately. Start with adapters:

| New firm department | Initial adapter source |
| --- | --- |
| `ceo` | Wrap current `backend/agents/chat/ai_chat/conversation_orchestrator.py` and final response composition |
| `planner` | Wrap `backend/agents/chat/ai_chat/conversation_planner.py`, `agent_router.py`, and `backend/agents/intent_router.py` |
| `research` | Wrap `backend/agents/research_agent.py`, `regime_agent.py`, chat research agents, and `services/research/` |
| `strategy_creator` | Wrap `backend/agents/strategy_creator_agent.py` and strategy design services |
| `strategy_reviewer` | Wrap `backend/agents/chat/strategy_code_review_agent.py` first, then split non-code review later |
| `codegen` | Wrap `services/strategy/design/blueprint_renderer.py` and materializer |
| `backtest` | Wrap `services/simulation/` and `backend/mcp/backtest_mcp/` |
| `optimization` | Wrap `services/optimization/` and `backend/mcp/optimization_mcp/` |
| `robustness` | Wrap Monte Carlo, walk-forward, and robustness paths in `services/optimization/` |
| `statistical_validation` | Wrap `services/analytics/statistical_tests.py` and research validation modules |
| `risk_reviewer` | Wrap risk agents plus `services/risk/` and `services/risk/` read/review surfaces |
| `portfolio_manager` | Wrap `backend/agents/portfolio_agent.py` and `services/risk/portfolio/` |
| `execution` | Wrap `backend/agents/execution_agent.py`, `services/execution/`, and paper/live execution services |
| `performance_reporter` | Wrap analytics, reporting, and `services/execution/performance/` |
| `audit` | Wrap `services/strategy/evidence/audit/`, replay, legal hold, and signing |
| `cost_optimizer` | Wrap `services/execution/cost/` |

### Tool Departments

Create firm-facing tool modules under `backend/tools/`:

```text
backend/tools/
  data_tools.py
  strategy_tools.py
  backtest_tools.py
  analytics_tools.py
  risk_tools.py
  portfolio_tools.py
  execution_tools.py
  reporting_tools.py
  audit_tools.py
```

These should be thin registries or re-export modules at first. Existing `backend/tools/read_only/` remains in place. Tool modules should not call broker or database internals directly when a service or MCP wrapper already exists.

### Risk And Execution Façades

Create:

```text
backend/risk/
  __init__.py
  governor.py
  approvals.py
  kill_switch.py
  correlation.py
  var_engine.py

backend/execution/
  __init__.py
  paper_broker.py
  mt5_bridge.py
  ctrader_bridge.py
  order_router.py
```

Initial mapping:

| New path | Existing source |
| --- | --- |
| `backend/risk/governor.py` | `services/risk/`, `services/risk/limits/`, `services/risk/core/governance_engine.py` |
| `backend/risk/approvals.py` | `services/execution/approval/`, `services/risk/decisions.py` |
| `backend/risk/kill_switch.py` | `services/risk/safety/kill_switch.py` |
| `backend/risk/correlation.py` | `services/risk/correlation.py`, `services/risk/metrics/correlation_risk.py` |
| `backend/risk/var_engine.py` | `services/risk/metrics/var_cvar.py` |
| `backend/execution/paper_broker.py` | `services/execution/shadow/`, `services/simulation/`, paper mode in live/session services |
| `backend/execution/mt5_bridge.py` | `backend/mcp/mt5_mcp/`, `services/execution/live/mt5_compat.py` |
| `backend/execution/ctrader_bridge.py` | placeholder only until cTrader support exists |
| `backend/execution/order_router.py` | `services/execution/send_service.py`, `pre_send.py`, `assembler.py`, `authority.py` |

### Memory And Reports

Create:

```text
memory/
  institutional/
  performance/
  evidence/
  lessons/
  strategies/
    active/
    paper/
    live/
    rejected/
    retired/

reports/
  daily/
  weekly/
  monthly/
  board/
  risk/
  backtests/
  robustness/
  strategy_reviews/
```

Initial rule:

- `backend/data/` remains the application data store.
- `memory/` becomes the long-lived agentic firm memory and evidence-facing filesystem surface.
- `reports/` becomes the human-readable output surface.
- For now, add README/manifest files in each top-level memory/report area and connect writers in later phases.

## Migration Sequence

### Step 1: Add Empty Structure Safely

Create the new folders with `__init__.py` for Python packages and short `README.md` files explaining ownership.

No imports change in this step.

Verification:

```powershell
python -m pytest tests/unit/backend tests/integration/backend --no-cov -q
```

### Step 2: Add Compatibility Adapters

Add thin modules under the new firm paths that import from existing services.

Examples:

```python
# backend/risk/kill_switch.py
from services.risk.safety.kill_switch import *
```

```python
# backend/agents/strategy_creator/agent.py
from backend.agents.strategy_creator_agent import StrategyCreatorAgent
```

Keep adapters intentionally small. Their job is to establish stable firm-facing import paths before changing internal ownership.

Verification:

```powershell
python -m pytest tests/unit/backend/agents tests/unit/backend/services --no-cov -q
python -m pytest tests/integration/backend/test_phase3_agent_runtime_integration.py --no-cov -q
```

### Step 3: Add Tool Aggregators

Create the Phase 2 tool modules as registries that group existing read-only tools, MCP wrappers, and deterministic services by business function.

Do not grant new powers yet. Tool modules should label risk class and approval requirements, but enforcement remains in the existing runtime and policy layer until Phase 5.

Verification:

```powershell
python -m pytest tests/contracts tests/security --no-cov -q
```

### Step 4: Redirect New Code To Firm Paths

Once the adapters exist, all new agentic firm work should import from:

- `backend.agents.<department>`
- `backend.tools.<domain>_tools`
- `backend.risk`
- `backend.execution`

Existing imports from `backend.services.*` stay valid. Do not mass-edit all old imports in one change.

### Step 5: Move Internals Gradually Only When Worth It

After tests pass and the firm paths are stable, individual modules can be moved if they clearly belong in the new department. Each move must include:

- import compatibility shim at old path
- focused tests
- UI/API smoke test if route behavior is affected
- changelog note in the department README

## Non-Loss Guarantees

To avoid losing functionality:

1. Keep `backend/services/*` as the deterministic source of truth during Phase 2.
2. Keep `backend/agents/runtime/*` as the runtime source of truth.
3. Keep `backend/data/strategies/*` strategy storage untouched.
4. Keep existing API routes stable.
5. Keep `haruquant/` public package stable.
6. Add adapters before changing imports.
7. Run targeted backend tests after each structural slice.
8. Avoid creating duplicate live execution paths.
9. Treat cTrader as a placeholder until a real bridge exists.
10. Keep live trading disabled unless the existing governed path explicitly enables it.

## Phase 2 Work Packages

### WP1: Firm Department Skeleton

Create all `backend/agents/<department>/` folders with ownership README files and package initializers.

Deliverable:

- New agent department tree exists.
- Existing agent imports still work.

### WP2: Agent Adapter Layer

Expose existing agent wrappers through the new department paths.

Deliverable:

- `backend.agents.strategy_creator.StrategyCreatorAgent` works.
- `backend.agents.portfolio_manager` points to portfolio advisory agents/services.
- `backend.agents.execution` points to execution planning only, not direct broker mutation.

### WP3: Tool Domain Layer

Create domain tool modules that group existing tools and services.

Deliverable:

- Clear tool homes for data, strategy, backtest, analytics, risk, portfolio, execution, reporting, and audit.
- No new ungoverned tool execution path.

### WP4: Risk And Execution Façades

Create firm-facing `backend/risk` and `backend/execution` modules that wrap existing deterministic services.

Deliverable:

- Phase 2 target paths exist.
- No duplicate RiskGovernor or order router logic.

### WP5: Memory And Report Filesystem

Create `memory/` and `reports/` directories with README/manifest guidance.

Deliverable:

- Future phases have stable write targets.
- No existing database/data behavior changes.

### WP6: Documentation And Checklist Update

Update `docs/agentic_firm/Implementation_plan.md` Phase 2 checklist only after skeletons/adapters are created.

Deliverable:

- Checklist reflects actual completion.
- Any deliberate deviations from the original path are documented.

## Recommended First Implementation Slice

Start with this low-risk slice:

1. Create department folders.
2. Add `__init__.py` files.
3. Add README files explaining each department.
4. Add `backend/risk` and `backend/execution` package folders with façade README files only.
5. Add `memory/` and `reports/` skeletons with README files.
6. Run backend import tests.

Then, in a second slice, add the adapter modules.

## Acceptance Criteria

Phase 2 should be considered complete when:

- Every path in the Phase 2 checklist exists.
- Existing API, strategy, backtest, optimization, risk, execution, audit, and UI behavior still works.
- New firm-facing paths do not duplicate deterministic safety logic.
- New code has an obvious place to live by department.
- Memory and reports have stable filesystem homes.
- The implementation plan checklist is updated with completed items and notes for compatibility façades.

## Test Plan

Minimum test commands after skeleton creation:

```powershell
python -m pytest tests/unit/backend/agents tests/unit/backend/services --no-cov -q
python -m pytest tests/integration/backend/test_phase3_agent_runtime_integration.py --no-cov -q
```

After risk/execution adapters:

```powershell
python -m pytest tests/integration/backend/test_phase2_execution_safety_integration.py --no-cov -q
python -m pytest tests/integration/backend/test_phase4_live_control_plane_integration.py --no-cov -q
python -m pytest tests/security --no-cov -q
```

Before marking Phase 2 complete:

```powershell
python -m pytest tests/unit/backend tests/integration/backend tests/contracts tests/security --no-cov -q
```

## Open Decisions

1. Whether `backend/services/*` remains the permanent deterministic domain layer, with `backend/risk` and `backend/execution` as stable façades.
2. Whether long-lived agent memory should be filesystem-first under `memory/`, database-first under `backend/data/database`, or dual-written through `services/strategy/evidence`.
3. Whether generated reports should be plain Markdown initially, or typed report artifacts with database references from the start.
4. Whether the CEO Agent should be a new top-level orchestrator or an adapter over the current AI chat orchestrator until Phase 6/7.

## Recommendation

Use an additive façade migration for Phase 2.

HaruQuant already has a lot of valuable controlled machinery. The correct move is not to tear it apart; it is to put a firm-shaped command structure over it, expose stable department paths, and then migrate behavior only when the adapters and tests prove the new shape is safe.
