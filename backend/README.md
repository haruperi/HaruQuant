# Backend

This directory contains the new agentic backend built from `docs/agentic_ai/implementation_plan.md`.

It is the additive migration target for HaruQuant's decentralized, governed, replayable trading system. The legacy runtime still exists under `apps/`, but new deterministic control-plane, agent-runtime, governance, and audit logic now lives here.

## What This Backend Is

The backend is the new system-of-record and enforcement layer for the agentic architecture.

Its job is to:
- define canonical contracts for every execution-bound message
- persist workflow, risk, execution, governance, and audit state
- enforce deterministic safety and policy gates before any live mutation
- run the agent runtime inside strict tool, schema, and provenance boundaries
- expose operator-facing APIs and read models
- support replay, audit export, legal hold, shadow mode, and hardening flows

Its job is not to:
- replace every legacy implementation in `apps/` immediately
- let agents directly mutate brokers or state stores
- let prompts or model output bypass deterministic validation

The key rule is simple:
- agents may propose, summarize, classify, and plan
- deterministic backend services decide, enforce, persist, and audit

## Relationship To `apps/`

The repository currently has two major backend-era surfaces:

- `apps/`
  - the legacy and still-useful runtime
  - contains existing trading, simulation, MT5, optimization, and related application logic
- `backend/`
  - the new agentic system slices
  - owns contracts, governance, orchestration, execution control, replay, promotion, and hardening

This migration was intentionally additive. That means:
- existing simulator and MT5-connected trading functionality in `apps/` is still reused
- new live control-plane logic is built in `backend/`
- legacy capabilities are wrapped behind bounded interfaces such as MCP adapters where needed

## Directory Map

### `backend/contracts/`

Canonical message contracts and schema-governance helpers.

Use this area when you need:
- the shared envelope
- workflow, proposal, risk, execution, observation, evaluation, incident, override, or replay contracts
- schema version resolution and runtime validation
- deterministic contract serialization

Key idea:
- every important message in the backend should be shaped by a contract from here

### `backend/db/`

Migration scaffolding, repository layer, and storage-facing records.

Use this area when you need:
- schema migrations
- repository methods for workflows, risk, execution, governance, audit, and replay state
- persistent records and storage mapping

Key idea:
- services should usually talk to repositories, not write ad hoc SQL directly

### `backend/orchestration/`

Deterministic workflow state machines and workflow skeleton logic.

Use this area when you need:
- workflow, proposal, incident, or kill-switch state transitions
- transition validation
- workflow creation, transition logging, and step recording

Key idea:
- workflow law is encoded here, not in prompts or UI behavior

### `backend/api/`

Migration-era operator API shell and supervision endpoints.

Use this area when you need:
- operator-facing API routes
- health endpoints
- approval and event stream endpoints
- API composition over backend services

Key idea:
- this is the control-plane HTTP surface, not the broker integration surface

### `backend/mcp/`

Governed tool boundaries over broker and legacy capabilities.

Current MCP packages include:
- `mt5_mcp`
- `backtest_mcp`
- `optimization_mcp`
- `risk_analytics_mcp`
- `sql_mcp`

Use this area when you need:
- tool-style access to broker or legacy functionality
- role-gated mutation paths
- stale-input rejection at the boundary
- normalized tool responses

Key idea:
- side effects should cross a bounded service/tool interface, not arbitrary direct calls

### `backend/agents/`

The agent runtime and agent wrappers.

Use this area when you need:
- runtime execution wrappers
- tool allowlists
- prompt version resolution
- output schema validation
- workflow execution patterns
- trajectory logging and evaluator helpers
- specialized agents and sub-agents

Key idea:
- agents are runtime participants, not system authorities

### `backend/read_models/`

Operator-facing read-side shaping for dashboard and supervision flows.

Use this area when you need:
- dashboard-friendly read projections
- denormalized control-plane views

### `backend/services/`

The main deterministic business-logic layer.

This is where most practical backend logic lives.

Current service domains:
- `approval`
- `audit`
- `evidence`
- `execution`
- `monitoring`
- `performance`
- `policy`
- `portfolio`
- `proposals`
- `reconciliation`
- `risk`
- `safety`
- `shadow`
- `strategy_gov`

Key idea:
- if something is policy-bearing, execution-bearing, or audit-bearing, it usually belongs in `services/`

## What Was Built, Phase By Phase

## Phase 1: Governance And Skeleton

Phase 1 established the backend foundation.

Implemented here:
- canonical contracts in [`backend/contracts`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\contracts)
- schema registry models, seeds, and runtime validation
- database baseline and repositories in [`backend/db`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\db)
- workflow state machines in [`backend/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\orchestration\workflow)
- policy and approval baseline in [`services/risk/policy`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\policy) and [`services/execution/approval`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\approval)
- operator API shell in [`backend/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\api)

Why it matters:
- everything later depends on these contracts, repositories, workflow rules, and policy baselines

## Phase 2: Deterministic Safety Core

Phase 2 implemented the hard safety loop for live mutation.

Implemented here:
- risk assembly, calculators, decisions, validity, and persistence in [`services/risk`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\risk)
- kill-switch state and audit in [`services/risk/safety`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\safety)
- execution readiness validation in [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\execution)
- MT5 MCP boundary in [`backend/mcp/mt5_mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\mcp\mt5_mcp)
- reconciliation in [`services/execution/reconciliation`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\reconciliation)

Why it matters:
- this is the part that actually blocks unsafe live trading behavior

## Phase 3: Agent Runtime

Phase 3 added the governed agent runtime.

Implemented here:
- runtime foundation, prompt registry, workflow patterns, evaluator infrastructure, and observability in [`backend/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\runtime)
- core agents and optional sub-agents in [`backend/agents`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents)

Why it matters:
- agents can now operate inside bounded schemas, tools, prompts, and trajectory logging

## Phase 4: Live Control Plane

Phase 4 connected the proposal-to-execution supervision path.

Implemented here:
- proposal transformation and readiness in [`services/strategy/proposals`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\proposals)
- execution assembly, send orchestration, attempt/receipt persistence, and authority-state propagation in [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\execution)
- observation and incident handling in [`services/execution/monitoring`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\monitoring)
- replay, audit export, legal hold, and signing in [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\audit)
- operator approval/event API in [`backend/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\api)

Why it matters:
- this is the supervised live path and operator-facing control surface

## Phase 5: Portfolio And Promotion

Phase 5 added portfolio analytics and strategy lifecycle governance.

Implemented here:
- portfolio analytics in [`services/risk/portfolio`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\portfolio)
- strategy lifecycle and promotion logic in [`services/strategy/governance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\strategy_gov)
- evidence bundle automation in [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\evidence)

Why it matters:
- strategy promotion is now explicit, evidence-backed, and gated before broader live autonomy

## Phase 6: Migration And Hardening

Phase 6 wrapped legacy capabilities and added production hardening.

Implemented here:
- legacy MCP wrappers in [`backend/mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\mcp)
- shadow mode in [`services/execution/shadow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\shadow)
- replay validation in [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\audit)
- performance helpers in [`services/execution/performance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\performance)

Why it matters:
- this is where the backend moved from “implemented” to “operationally defensible”

## Core Backend Logic Paths

## 1. Workflow And Proposal Path

Use this path when a strategy, operator, or agent starts a new controlled workflow.

Typical flow:
1. create or receive a contract-backed workflow input
2. validate workflow state and allowed transition rules
3. transform hypothesis or upstream evidence into a proposal
4. persist workflow, proposal, and transition records

Primary areas:
- [`backend/contracts`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\contracts)
- [`backend/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\orchestration\workflow)
- [`services/strategy/proposals`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\proposals)
- [`backend/db/repositories`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\db\repositories)

## 2. Risk Decision Path

Use this path when a proposal needs deterministic evaluation before execution.

Typical flow:
1. assemble a `RiskAssessmentRequest`
2. evaluate exposures, concentrations, margin, drawdown, correlations, and restrictions
3. compose a decision with rationale, constraints, and provenance
4. persist the decision and any constraints
5. enforce freshness and invalidate on material proposal drift

Primary areas:
- [`services/risk`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\risk)

## 3. Live Execution Path

Use this path when a proposal is approved for execution.

Typical flow:
1. assemble an `ExecutionIntent`
2. validate readiness using current metadata and risk freshness
3. route send through execution services only
4. cross the broker boundary through MT5 MCP only
5. persist attempt and receipt artifacts
6. reconcile against broker truth before any retry

Primary areas:
- [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\execution)
- [`backend/mcp/mt5_mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\mcp\mt5_mcp)
- [`services/execution/reconciliation`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\reconciliation)

## 4. Safety And Recovery Path

Use this path when live entry must be blocked or governed recovery must occur.

Typical flow:
1. trigger soft or hard kill switch
2. block new live entry
3. require governed recovery
4. audit the state transitions

Primary areas:
- [`services/risk/safety`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\safety)

## 5. Agent Runtime Path

Use this path when an agent should run under schema, prompt, tool, and provenance controls.

Typical flow:
1. resolve prompt version
2. create runtime request/session context
3. apply tool allowlist and redaction
4. execute the agent wrapper
5. validate the output contract
6. persist trajectory and evaluation information

Primary areas:
- [`backend/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\runtime)
- [`backend/agents`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents)

## 6. Replay And Audit Path

Use this path when you need audit export, replay, legal hold, or evidence integrity.

Typical flow:
1. assemble replay bundles and audit artifacts
2. compute integrity manifests and signatures
3. export reviewable packages
4. block purge when legal hold applies

Primary areas:
- [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\audit)
- [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\evidence)

## 7. Strategy Promotion Path

Use this path when a strategy moves through lifecycle gates toward broader live operation.

Typical flow:
1. register strategy metadata
2. validate lifecycle transition
3. assemble and store required evidence bundle
4. validate evidence for the target state
5. resolve approval route
6. persist promotion and update lifecycle state
7. update operating envelope
8. evaluate suspension and retirement when needed

Primary areas:
- [`services/strategy/governance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\strategy_gov)
- [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\evidence)

## Where To Use What

## Use `backend/contracts` when

- defining or validating canonical payloads
- serializing execution-bound messages
- resolving contract versions

Do not use it for:
- business decisions
- DB writes
- workflow side effects

## Use `backend/db/repositories` when

- reading or writing persistent backend state
- implementing services that need DB-backed records

Do not use it for:
- policy logic
- contract validation
- HTTP concerns

## Use `services/risk` when

- evaluating whether a trade can proceed
- deriving deterministic constraints and approvals

Do not use it for:
- direct broker sends
- prompt-driven reasoning

## Use `services/execution` when

- assembling intents
- validating send readiness
- sending to the broker boundary
- persisting attempts and receipts

Do not use it for:
- bypassing MT5 MCP
- ad hoc broker calls from unrelated code

## Use `backend/mcp` when

- exposing bounded tool access to legacy or broker capabilities
- enforcing role separation and stale-input checks at the boundary

Do not use it for:
- storing business state
- embedding policy logic that belongs in services

## Use `backend/agents/runtime` when

- running agents with prompt, tool, memory, and schema controls
- evaluating or logging agent trajectories

Do not use it for:
- deterministic live safety decisions
- direct DB orchestration outside runtime needs

## Use `services/strategy/evidence/audit` and `services/strategy/evidence` when

- building replay bundles
- managing legal hold logic
- exporting or signing audit evidence
- storing lifecycle evidence bundles

## Use `services/risk/portfolio` and `services/strategy/governance` when

- generating portfolio-level advisory changes
- governing strategy lifecycle, promotion, suspension, and retirement

## Design Rationale

## Deterministic Enforcement Beats Agent Discretion

Live safety is not delegated to prompts.

The backend was structured so that:
- agents can generate candidate plans or judgments
- deterministic services decide what is legal, fresh, allowed, and auditable

## Side Effects Must Cross Bounded Interfaces

Broker and legacy integrations are intentionally wrapped.

This makes it easier to:
- apply authorization
- reject stale inputs
- normalize responses
- observe and replay important side effects

## Provenance And Replay Are First-Class

Execution-bound state is expected to be:
- persisted
- reconstructable
- attributable
- exportable under audit and legal hold requirements

This is why contracts, trajectory logs, replay bundles, receipts, and evidence bundles exist across the backend.

## Additive Migration Preserved Momentum

The backend did not replace the whole repo in one cutover.

Instead it:
- reused working simulator and broker-connected code where appropriate
- wrapped legacy capabilities behind new bounded services
- introduced control-plane logic around the edges first

That kept the migration practical while improving safety and governance.

## How To Use The Backend In Practice

## For new deterministic backend logic

Start in:
- [`backend/services`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services)

Then:
- pick the correct domain package
- use contracts from `backend/contracts`
- persist through repositories in `backend/db/repositories`

## For new workflow or state-machine work

Start in:
- [`backend/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\orchestration\workflow)

## For new agent work

Start in:
- [`backend/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\runtime)
- [`backend/agents`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents)

## For new broker or legacy tool boundaries

Start in:
- [`backend/mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\mcp)

## For operator-facing control plane features

Start in:
- [`backend/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\api)
- [`backend/read_models`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\read_models)

## Running And Verifying

## Apply migrations

The backend DB baseline is migration-driven.

Use the migration runner through Python, for example:

```python
from pathlib import Path
from backend.db import apply_pending_migrations

repo_root = Path(__file__).resolve().parents[1]
database_path = repo_root / "backend_example.sqlite3"
migrations_dir = repo_root / "backend" / "db" / "migrations"

apply_pending_migrations(database_path, migrations_dir)
```

## Run the operator API

The migration-era operator app lives under [`backend/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\api).

Use this area when booting or extending the control plane. The exact launch surface depends on the app composition used in the repository at runtime.

## Run targeted backend tests

Common targeted slices used during implementation:

```powershell
python -m pytest tests/unit/contracts --no-cov -q
python -m pytest tests/unit/backend/db tests/unit/backend/services tests/unit/backend/agents --no-cov -q
python -m pytest tests/integration/backend --no-cov -q
python -m pytest tests/scenario tests/chaos tests/security tests/replay --no-cov -q
```

## Run practical usage examples

Phase-based examples live under [`backend/scripts/examples/agentic_ai`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai):

- [`00_utilities.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\00_utilities.py)
- [`01_prompting.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\01_prompting.py)
- [`02_agentic_workflows.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\02_agentic_workflows.py)
- [`03_building_agents.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\03_building_agents.py)
- [`04_multi_agent_systems.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\04_multi_agent_systems.py)
- [`05_agents_systems.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai\05_agents_systems.py)

These are the best practical orientation points if you want to see the backend used as a system rather than as isolated modules.

## Suggested Entry Points By Task Type

If you are trying to understand:

- contracts and message families
  - open [`backend/contracts`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\contracts)
- persistence and schema
  - open [`backend/data/database/migrations`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\data\database\migrations) and [`backend/data/database/repositories`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\data\database\repositories)
- workflow law
  - open [`backend/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\orchestration\workflow)
- live safety
  - open [`services/risk`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\risk), [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\execution), and [`services/risk/safety`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\safety)
- agent runtime
  - open [`backend/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\runtime)
- broker boundary
  - open [`backend/mcp/mt5_mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\mcp\mt5_mcp)
- replay and legal hold
  - open [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\audit)
- promotion and evidence
  - open [`services/risk/portfolio`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\portfolio), [`services/strategy/governance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\strategy_gov), and [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\services\evidence)

## References

Primary planning and evidence documents:

- [`docs/agentic_ai/implementation_plan.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\implementation_plan.md)
- [`docs/agentic_ai/phase1_exit_report.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\phase1_exit_report.md)
- [`docs/agentic_ai/phase2_exit_report.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\phase2_exit_report.md)
- [`docs/agentic_ai/phase3_exit_report.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\phase3_exit_report.md)
- [`docs/agentic_ai/phase4_exit_report.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\phase4_exit_report.md)
- [`docs/agentic_ai/phase5_exit_report.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\phase5_exit_report.md)
- [`docs/agentic_ai/phase6_exit_report.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\phase6_exit_report.md)
- [`docs/agentic_ai/final_production_readiness_report.md`](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\agentic_ai\final_production_readiness_report.md)

If you need the quickest practical orientation, start with the Phase examples in [`backend/scripts/examples/agentic_ai`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\scripts\examples\agentic_ai), then trace into the service package used by the example you care about.
