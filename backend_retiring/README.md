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
- `backend_retiring/`
  - the new agentic system slices
  - owns contracts, governance, orchestration, execution control, replay, promotion, and hardening

This migration was intentionally additive. That means:
- existing simulator and MT5-connected trading functionality in `apps/` is still reused
- new live control-plane logic is built in `backend_retiring/`
- legacy capabilities are wrapped behind bounded interfaces such as MCP adapters where needed

## Directory Map

### `backend_retiring/contracts/`

Canonical message contracts and schema-governance helpers.

Use this area when you need:
- the shared envelope
- workflow, proposal, risk, execution, observation, evaluation, incident, override, or replay contracts
- schema version resolution and runtime validation
- deterministic contract serialization

Key idea:
- every important message in the backend should be shaped by a contract from here

### `backend_retiring/db/`

Migration scaffolding, repository layer, and storage-facing records.

Use this area when you need:
- schema migrations
- repository methods for workflows, risk, execution, governance, audit, and replay state
- persistent records and storage mapping

Key idea:
- services should usually talk to repositories, not write ad hoc SQL directly

### `backend_retiring/orchestration/`

Deterministic workflow state machines and workflow skeleton logic.

Use this area when you need:
- workflow, proposal, incident, or kill-switch state transitions
- transition validation
- workflow creation, transition logging, and step recording

Key idea:
- workflow law is encoded here, not in prompts or UI behavior

### `backend_retiring/api/`

Migration-era operator API shell and supervision endpoints.

Use this area when you need:
- operator-facing API routes
- health endpoints
- approval and event stream endpoints
- API composition over backend services

Key idea:
- this is the control-plane HTTP surface, not the broker integration surface

### `backend_retiring/mcp/`

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

### `backend_retiring/agents/`

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

### `backend_retiring/read_models/`

Operator-facing read-side shaping for dashboard and supervision flows.

Use this area when you need:
- dashboard-friendly read projections
- denormalized control-plane views

### `services/`

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
- canonical contracts in [`backend_retiring/contracts`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\contracts)
- schema registry models, seeds, and runtime validation
- database baseline and repositories in [`backend_retiring/db`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\db)
- workflow state machines in [`backend_retiring/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\orchestration\workflow)
- policy and approval baseline in [`services/risk/policy`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\policy) and [`services/execution/approval`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\approval)
- operator API shell in [`backend_retiring/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\api)

Why it matters:
- everything later depends on these contracts, repositories, workflow rules, and policy baselines

## Phase 2: Deterministic Safety Core

Phase 2 implemented the hard safety loop for live mutation.

Implemented here:
- risk assembly, calculators, decisions, validity, and persistence in [`services/risk`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\risk)
- kill-switch state and audit in [`services/risk/safety`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\safety)
- execution readiness validation in [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\execution)
- MT5 MCP boundary in [`backend_retiring/mcp/mt5_mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\mcp\mt5_mcp)
- reconciliation in [`services/execution/reconciliation`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\reconciliation)

Why it matters:
- this is the part that actually blocks unsafe live trading behavior

## Phase 3: Agent Runtime

Phase 3 added the governed agent runtime.

Implemented here:
- runtime foundation, prompt registry, workflow patterns, evaluator infrastructure, and observability in [`backend_retiring/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\agents\runtime)
- core agents and optional sub-agents in [`backend_retiring/agents`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\agents)

Why it matters:
- agents can now operate inside bounded schemas, tools, prompts, and trajectory logging

## Phase 4: Live Control Plane

Phase 4 connected the proposal-to-execution supervision path.

Implemented here:
- proposal transformation and readiness in [`services/strategy/proposals`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\proposals)
- execution assembly, send orchestration, attempt/receipt persistence, and authority-state propagation in [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\execution)
- observation and incident handling in [`services/execution/monitoring`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\monitoring)
- replay, audit export, legal hold, and signing in [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\audit)
- operator approval/event API in [`backend_retiring/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\api)

Why it matters:
- this is the supervised live path and operator-facing control surface

## Phase 5: Portfolio And Promotion

Phase 5 added portfolio analytics and strategy lifecycle governance.

Implemented here:
- portfolio analytics in [`services/risk/portfolio`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\portfolio)
- strategy lifecycle and promotion logic in [`services/strategy/governance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\strategy_gov)
- evidence bundle automation in [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\evidence)

Why it matters:
- strategy promotion is now explicit, evidence-backed, and gated before broader live autonomy

## Phase 6: Migration And Hardening

Phase 6 wrapped legacy capabilities and added production hardening.

Implemented here:
- legacy MCP wrappers in [`backend_retiring/mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\mcp)
- shadow mode in [`services/execution/shadow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\shadow)
- replay validation in [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\audit)
- performance helpers in [`services/execution/performance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\performance)

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
- [`backend_retiring/contracts`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\contracts)
- [`backend_retiring/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\orchestration\workflow)
- [`services/strategy/proposals`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\proposals)
- [`backend_retiring/db/repositories`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\db\repositories)

## 2. Risk Decision Path

Use this path when a proposal needs deterministic evaluation before execution.

Typical flow:
1. assemble a `RiskAssessmentRequest`
2. evaluate exposures, concentrations, margin, drawdown, correlations, and restrictions
3. compose a decision with rationale, constraints, and provenance
4. persist the decision and any constraints
5. enforce freshness and invalidate on material proposal drift

Primary areas:
- [`services/risk`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\risk)

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
- [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\execution)
- [`backend_retiring/mcp/mt5_mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\mcp\mt5_mcp)
- [`services/execution/reconciliation`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\reconciliation)

## 4. Safety And Recovery Path

Use this path when live entry must be blocked or governed recovery must occur.

Typical flow:
1. trigger soft or hard kill switch
2. block new live entry
3. require governed recovery
4. audit the state transitions

Primary areas:
- [`services/risk/safety`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\safety)

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
- [`backend_retiring/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\agents\runtime)
- [`backend_retiring/agents`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\agents)

## 6. Replay And Audit Path

Use this path when you need audit export, replay, legal hold, or evidence integrity.

Typical flow:
1. assemble replay bundles and audit artifacts
2. compute integrity manifests and signatures
3. export reviewable packages
4. block purge when legal hold applies

Primary areas:
- [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\audit)
- [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\evidence)

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
- [`services/strategy/governance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\strategy_gov)
- [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\evidence)

## Where To Use What

## Use `backend_retiring/contracts` when

- defining or validating canonical payloads
- serializing execution-bound messages
- resolving contract versions

Do not use it for:
- business decisions
- DB writes
- workflow side effects

## Use `backend_retiring/db/repositories` when

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

## Use `backend_retiring/mcp` when

- exposing bounded tool access to legacy or broker capabilities
- enforcing role separation and stale-input checks at the boundary

Do not use it for:
- storing business state
- embedding policy logic that belongs in services

## Use `backend_retiring/agents/runtime` when

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

This is why contracts, trajectory logs, replay bundles, receipts, and evidence bundles exist across the backend_retiring.

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
- [`services`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services)

Then:
- pick the correct domain package
- use contracts from `backend_retiring/contracts`
- persist through repositories in `backend_retiring/db/repositories`

## For new workflow or state-machine work

Start in:
- [`backend_retiring/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\orchestration\workflow)

## For new agent work

Start in:
- [`backend_retiring/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\agents\runtime)
- [`backend_retiring/agents`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\agents)

## For new broker or legacy tool boundaries

Start in:
- [`backend_retiring/mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\mcp)

## For operator-facing control plane features

Start in:
- [`backend_retiring/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\api)
- [`backend_retiring/read_models`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\read_models)

## Running And Verifying

## Apply migrations

The backend DB baseline is migration-driven.

Use the migration runner through Python, for example:

```python
from pathlib import Path
from backend_retiring.db import apply_pending_migrations

repo_root = Path(__file__).resolve().parents[1]
database_path = repo_root / "backend_example.sqlite3"
migrations_dir = repo_root / "backend_retiring" / "db" / "migrations"

apply_pending_migrations(database_path, migrations_dir)
```

## Run the operator API

The migration-era operator app lives under [`backend_retiring/api`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\api).

Use this area when booting or extending the control plane. The exact launch surface depends on the app composition used in the repository at runtime.

## Run targeted backend tests

Common targeted slices used during implementation:

```powershell
python -m pytest tests/unit/contracts --no-cov -q
python -m pytest tests/unit/backend_retiring/db tests/unit/backend_retiring/agents tests/unit/backend/services --no-cov -q
python -m pytest tests/integration/backend --no-cov -q
python -m pytest tests/scenario tests/chaos tests/security tests/replay --no-cov -q
```

## Run practical usage examples

Phase-based examples live under [`scripts/examples/agentic_ai`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai):

- [`00_utilities.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai\00_utilities.py)
- [`01_prompting.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai\01_prompting.py)
- [`02_agentic_workflows.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai\02_agentic_workflows.py)
- [`03_building_agents.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai\03_building_agents.py)
- [`04_multi_agent_systems.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai\04_multi_agent_systems.py)
- [`05_agents_systems.py`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai\05_agents_systems.py)

These are the best practical orientation points if you want to see the backend used as a system rather than as isolated modules.

## Suggested Entry Points By Task Type

If you are trying to understand:

- contracts and message families
  - open [`backend_retiring/contracts`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\contracts)
- persistence and schema
  - open [`data/database/migrations`](C:\Users\rharu\Documents\MyApplications\HaruQuant\data\database\migrations) and [`data/database/repositories`](C:\Users\rharu\Documents\MyApplications\HaruQuant\data\database\repositories)
- workflow law
  - open [`backend_retiring/orchestration/workflow`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\orchestration\workflow)
- live safety
  - open [`services/risk`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\risk), [`services/execution`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\execution), and [`services/risk/safety`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\safety)
- agent runtime
  - open [`backend_retiring/agents/runtime`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\agents\runtime)
- broker boundary
  - open [`backend_retiring/mcp/mt5_mcp`](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend_retiring\mcp\mt5_mcp)
- replay and legal hold
  - open [`services/strategy/evidence/audit`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\audit)
- promotion and evidence
  - open [`services/risk/portfolio`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\portfolio), [`services/strategy/governance`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\strategy_gov), and [`services/strategy/evidence`](C:\Users\rharu\Documents\MyApplications\HaruQuant\services\evidence)

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

If you need the quickest practical orientation, start with the Phase examples in [`scripts/examples/agentic_ai`](C:\Users\rharu\Documents\MyApplications\HaruQuant\scripts\examples\agentic_ai), then trace into the service package used by the example you care about.
