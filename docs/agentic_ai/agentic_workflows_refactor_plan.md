# Agentic Workflows Refactor Plan

## Purpose

This plan records the work required to move HaruQuant from agentic workflow scaffolding to an executable, observable, testable agentic workflow runtime.

The target standard is the course module expectation for **Agentic Workflows**:

- explicit workflow modeling
- prompt chaining
- routing
- true parallelization
- evaluator-optimizer loops
- orchestrator-worker delegation
- traceable execution
- reliable failure handling
- maintainable, extensible workflow definitions
- tested workflow paths

## Current Assessment

Overall readiness before this refactor was **Partial**.

## Implementation Status

Status: **Implemented as a first production runtime slice**

Completed in this pass:

- canonical migration directory helper and active test migration-path cleanup
- typed `WorkflowPlan` pattern enum and typed `WorkflowPhaseStep`
- real concurrent `ParallelWorkflowRunner`
- structured aggregate results for parallel and orchestrator-worker patterns
- worker output conflict detection
- `WorkflowPatternRegistry`
- structured `RouteDecisionService`
- `WorkflowPlanExecutor`
- `WorkflowRuntimeService` for create-and-execute wiring
- automatic workflow step recording from plan execution
- artifact references for step inputs and outputs
- trace/span IDs on workflow execution results
- optional trajectory log persistence from executor
- evaluator-optimizer iteration persistence to `core_evaluation_reports`
- operator trajectory read model for workflow steps, trajectory logs, and evaluation reports
- focused unit, integration, db, and scenario tests for the workflow runtime

Completion ledger:

| Plan item | Status |
| --- | --- |
| 1. Fix Migration Path Drift | Complete |
| 2. Tighten `WorkflowPlan` | Complete |
| 3. Fix Misleading Parallel Workflow Behavior | Complete |
| 4. Add `WorkflowPlanExecutor` | Complete |
| 5. Add `WorkflowPatternRegistry` | Complete |
| 6. Add Typed Execution Results | Complete |
| 7. Introduce `RouteDecisionService` | Complete |
| 8. Make Routing Policy-Aware | Complete |
| 9. Instrument All Pattern Runners | Complete |
| 10. Add Trace And Span Hierarchy | Complete |
| 11. Add Execution Trajectory Read Model | Complete |
| 12. Prompt Chaining | Complete |
| 13. Parallelization | Complete |
| 14. Evaluator-Optimizer | Complete |
| 15. Orchestrator-Workers | Complete |
| 16. Routing Workflow Runner | Complete |
| 17. Add Failure Policy Model | Complete |
| 18. Integrate MCP Wrapper Failure States | Complete through runtime result/failure propagation |
| 19. Add Timeout Enforcement To Executor | Complete |
| 20. Add Focused Unit Tests | Complete |
| 21. Add Scenario Tests | Complete |
| 22. Add Replay And Observability Tests | Complete for the new runtime trajectory/read-model path |

Remaining follow-up outside this workflow refactor:

- unrelated LLM runtime tests still need separate cleanup around provider registry isolation and mocked OpenAI client behavior
- archived documentation may still describe historical paths or pre-refactor architecture as archive material

The codebase has strong foundations:

- agent catalog and workflow catalog in `docs/haruquant/agents/Catalog.md` and `docs/haruquant/workflows/Catalog.md`
- workflow pattern runner scaffolds in `backend/agents/runtime/workflows.py`
- runtime enforcement in `backend/agents/runtime/runner.py`
- canonical output validation in `backend/agents/runtime/output_validation.py`
- explicit workflow FSMs in `backend/orchestration/workflow`
- MCP retry, circuit-breaker, and rate-limit wrappers in `backend/mcp/wrappers`
- trajectory log models in `backend/agents/runtime/observability.py`

The main gap is that these pieces are not yet integrated into a full executable workflow engine. Several patterns exist as testable scaffolds but are not production-grade orchestration paths.

## Phase 1: Stabilize The Foundation

### 1. Fix Migration Path Drift

Replace stale `backend/db/migrations` references with the real migration location:

```text
backend/data/database/migrations
```

Primary targets:

- `backend/api/dependencies.py`
- tests under `tests/unit`
- tests under `tests/integration`
- tests under `tests/scenario`
- tests under `tests/chaos`
- tests under `tests/replay`
- stale documentation references in `backend/README.md`

Add a shared helper such as:

```python
backend.data.database.default_migrations_dir()
```

Acceptance criteria:

- workflow DB tests no longer fail with `no such table: core_workflows`
- app startup dependency setup uses the correct migration path
- tests do not hardcode divergent migration locations

### 2. Tighten `WorkflowPlan`

Replace loose workflow plan fields in `backend/contracts/workflow_plan/model.py`.

Current weak points:

- `selected_pattern: str`
- `phase_steps: list[dict[str, Any]]`

Target model:

- `selected_pattern` should be an enum:
  - `sequential`
  - `routing`
  - `parallel`
  - `evaluator_optimizer`
  - `orchestrator_workers`
- `phase_steps` should be a typed list of `WorkflowPhaseStep`

Suggested `WorkflowPhaseStep` fields:

- `step_id`
- `phase`
- `owner_agent`
- `input_contract_type`
- `expected_output_contract_type`
- `depends_on`
- `allowed_tools`
- `timeout_seconds`
- `failure_policy`
- `metadata`

Acceptance criteria:

- unknown workflow patterns fail validation
- missing owners fail validation
- invalid dependencies fail validation
- invalid or empty expected output contracts fail validation
- examples and schema tests are updated

### 3. Fix Misleading Parallel Workflow Behavior

`ParallelWorkflowRunner` in `backend/agents/runtime/workflows.py` currently loops sequentially.

Preferred fix:

- implement real bounded concurrency using async execution or an executor
- include per-task timeout
- include cancellation behavior
- return a structured aggregate result

Fallback fix:

- rename the current class to avoid claiming true parallel behavior

Acceptance criteria:

- tests prove independent tasks overlap in time
- partial failures are represented explicitly
- successful task outputs are preserved when non-critical peers fail

## Phase 2: Build The Missing Execution Core

### 4. Add `WorkflowPlanExecutor`

Create:

```text
backend/orchestration/workflow/executor.py
```

Responsibilities:

- accept a validated `WorkflowPlan`
- validate policy, tool, and agent constraints
- select the correct workflow pattern runner
- execute plan steps
- persist workflow transitions
- persist workflow step records
- persist trajectory logs
- produce a typed workflow execution result

Existing components to integrate:

- `WorkflowStateValidator`
- `WorkflowTransitionLogger`
- `WorkflowStepRecorder`
- `ADKRunnerService`
- `RuntimeTrajectoryLogService`
- workflow pattern runners from `backend/agents/runtime/workflows.py`

Acceptance criteria:

- one integration test executes `WorkflowIntent -> WorkflowPlan -> worker steps -> final artifact`
- workflow state transitions are validated during execution
- workflow steps are recorded automatically
- invalid plan execution fails closed

### 5. Add `WorkflowPatternRegistry`

Create:

```text
backend/agents/runtime/pattern_registry.py
```

Responsibilities:

- map workflow pattern enum values to runner implementations
- allow new workflow patterns to be registered without editing executor control flow
- centralize pattern capability metadata

Acceptance criteria:

- executor uses the registry instead of hardcoded pattern conditionals
- a test can register a dummy pattern without modifying executor code

### 6. Add Typed Execution Results

Introduce typed result models:

- `StepExecutionResult`
- `WorkflowExecutionResult`
- `ParallelAggregateResult`
- `WorkerGroupResult`
- `RouteDecision`

Avoid returning raw `dict[str, ADKRunResult]` at orchestration boundaries.

Acceptance criteria:

- success, validation failure, timeout, tool-policy violation, route failure, and partial worker failure are distinct states
- all result types include workflow ID, correlation ID, step ID, final state, latency, and artifact references

## Phase 3: Make Routing Real And Inspectable

### 7. Introduce `RouteDecisionService`

Current routing is split across:

- `backend/api/router.py`
- `backend/agents/intent_router.py`
- `RoutingWorkflowRunner` in `backend/agents/runtime/workflows.py`

Create a shared route decision abstraction with:

- `intent`
- `confidence`
- `matched_rules`
- `fallback_route`
- `ambiguity_reason`
- `required_policy_checks`
- `selected_handler`

Keep path-prefix routing as one classifier, not the whole routing architecture.

Acceptance criteria:

- known route test passes
- unknown route test passes
- ambiguous route test passes
- missing handler test passes
- fallback route test passes
- route decisions are logged and inspectable

### 8. Make Routing Policy-Aware

Route decisions should consider:

- operating mode
- workflow type
- allowed tools
- risk class
- side-effecting capability restrictions
- approval requirements

Acceptance criteria:

- research workflows cannot route to execution tools
- live execution cannot bypass risk governance
- low-confidence or ambiguous routing escalates or falls back according to policy

## Phase 4: Make Observability Automatic

### 9. Instrument All Pattern Runners

Every workflow step should automatically emit:

- workflow transition
- workflow step record
- trajectory log
- latency
- final state
- validation status
- repair status
- tool calls
- token usage
- prompt hash
- prompt version

Do this in the executor or a runner middleware, not manually in tests.

Acceptance criteria:

- executing any pattern leaves complete rows in workflow transitions, workflow steps, and trajectory logs
- observability does not depend on hand-written test setup

### 10. Add Trace And Span Hierarchy

Use:

- `backend/observability/trace_model.py`
- `backend/observability/span_model.py`

Runtime hierarchy:

- parent span: workflow
- child spans:
  - route
  - plan
  - each worker step
  - tool call
  - evaluation
  - synthesis

Acceptance criteria:

- a workflow replay can reconstruct step order, timings, agent names, input refs, output refs, and failures

### 11. Add Execution Trajectory Read Model

Extend the operator read model or add a new read model for:

- current workflow state
- phase list
- step status
- assigned agent
- input/output refs
- failures
- retries
- evaluation scores
- final artifact

Acceptance criteria:

- operator-facing UI/API can inspect one workflow from request to completion

## Phase 5: Strengthen Each Pattern

### 12. Prompt Chaining

Replace raw `metadata["prior_steps"]` dictionaries with typed artifact references.

Required behavior:

- validate every intermediate output
- persist every intermediate output
- pass deliberate context forward
- fail closed on invalid intermediate outputs

Acceptance criteria:

- chained workflow blocks on invalid intermediate output
- blocked step is recorded with reason and validation error

### 13. Parallelization

Add:

- bounded concurrency
- fan-in synthesis
- `fail_fast` policy
- `continue_on_error` policy
- `quorum` policy
- critical vs non-critical tasks

Acceptance criteria:

- one failed non-critical worker does not erase successful worker outputs
- one failed critical worker blocks synthesis
- timeouts cancel or mark affected workers according to policy

### 14. Evaluator-Optimizer

Enhance:

- persist every iteration as an `EvaluationReport`
- make rubrics part of workflow declarations
- add typed critique/refinement artifacts
- add regression detection

Stop reasons:

- `accepted`
- `max_iterations`
- `regression_detected`
- `policy_blocked`
- `validation_failed`

Acceptance criteria:

- tests prove generate -> critique -> improve behavior
- every iteration is replayable
- optimizer stops when output quality regresses repeatedly

### 15. Orchestrator-Workers

Required upgrades:

- convert orchestrator-generated `WorkflowPlan.phase_steps` into executable worker tasks
- validate dependencies before dispatch
- execute workers by selected pattern
- add final synthesis phase
- handle worker disagreement
- handle partial failure

Acceptance criteria:

- orchestrator emits a plan
- executor dispatches workers from that plan
- final synthesis references all worker outputs
- conflicting worker outputs are escalated or resolved according to policy

### 16. Routing Workflow Runner

Upgrade:

- add fallback branch support
- add route confidence thresholds
- add route decision logging
- return structured route failure instead of raw `LookupError`

Acceptance criteria:

- unknown route produces fallback or escalation result
- low-confidence route does not silently dispatch

## Phase 6: Reliability And Fault Tolerance

### 17. Add Failure Policy Model

Define workflow-level and step-level failure policy fields:

- retry count
- retryable states
- timeout
- fallback agent
- compensation action
- escalation condition
- criticality

Acceptance criteria:

- tests cover tool failure
- tests cover timeout
- tests cover validation failure
- tests cover policy block
- tests cover missing data

### 18. Integrate MCP Wrapper Failure States

Map MCP wrapper failures into workflow states:

- retry exhaustion
- circuit breaker open
- rate limit exceeded
- downstream timeout

Relevant modules:

- `backend/mcp/wrappers/base_wrapper.py`
- `backend/mcp/wrappers/retry_policy.py`
- `backend/mcp/wrappers/circuit_breaker.py`
- `backend/mcp/wrappers/rate_limiter.py`

Acceptance criteria:

- downstream tool outage produces an explicit workflow state such as `FAILED`, `TIMED_OUT`, `BLOCKED_BY_POLICY`, or `RECONCILING`
- failure reason is visible in workflow steps and trajectory logs

### 19. Add Timeout Enforcement To Executor

Use:

- `backend/services/monitoring/workflow_timeout.py`

Step timeout should be enforced during execution, not only through external monitoring.

Acceptance criteria:

- timed-out step stops or degrades execution according to policy
- timed-out workflow records `TIMED_OUT`
- timeout reason is persisted

## Phase 7: Testing Upgrade

### 20. Add Focused Unit Tests

Add tests for:

- `WorkflowPlanExecutor`
- `WorkflowPatternRegistry`
- typed `WorkflowPlan`
- `RouteDecisionService`
- real parallel execution
- fan-in aggregation
- evaluator persistence
- orchestrator-worker synthesis

### 21. Add Scenario Tests

Add or strengthen scenario tests for:

- research-only workflow cannot execute trades
- paper execution workflow follows Reason -> Plan -> Act -> Observe -> Evaluate
- live workflow requires risk and approval gates
- parallel portfolio analysis aggregates exposure, correlation, and drawdown workers
- evaluator-optimizer improves a low-score strategy report
- worker partial failure escalates or degrades according to policy

### 22. Add Replay And Observability Tests

Every material workflow should be reconstructable from:

- workflow transitions
- workflow steps
- trajectory logs
- artifact refs
- prompt versions
- policy versions

Acceptance criteria:

- replay completeness fails when any material step lacks input ref, output ref, latency, final state, or agent name
- replay can reconstruct a workflow from initial request to final result

## Suggested Implementation Order

1. Fix migration path drift.
2. Tighten `WorkflowPlan`.
3. Implement real parallel execution or rename the current runner.
4. Add `WorkflowPlanExecutor`.
5. Add automatic step and trajectory logging.
6. Add `RouteDecisionService`.
7. Execute orchestrator plans through worker dispatch.
8. Persist evaluator-optimizer iterations.
9. Add failure policies and timeout enforcement.
10. Add end-to-end scenario and replay tests.

## Priority Table

| Issue | Severity | Effort | Impact | Recommended Action |
|---|---:|---:|---:|---|
| Pattern runners not wired into production workflow execution | High | High | High | Build `WorkflowPlanExecutor` and route workflow creation through it |
| `ParallelWorkflowRunner` is sequential | High | Medium | High | Implement bounded async or executor concurrency with timeout and aggregation |
| `WorkflowPlan` is too loosely typed | High | Medium | High | Replace `dict[str, Any]` phase steps with typed step models and pattern enum |
| Orchestrator-worker lacks plan execution and synthesis | High | High | High | Convert orchestrator `WorkflowPlan` into executable worker graph and synthesize outputs |
| Observability is manual, not automatic | High | Medium | High | Emit step records, transitions, spans, and trajectory logs inside runners |
| Migration path mismatch breaks workflow persistence tests | High | Low | High | Standardize on `backend/data/database/migrations` everywhere |
| Routing is prefix-based and low-context | Medium | Medium | Medium | Add typed `RouteDecision` with confidence, matched rules, and fallback policy |
| Evaluator outputs are not persisted by default | Medium | Medium | Medium | Store each critique/refinement iteration as `EvaluationReport` and trajectory log |
| Failure handling is inconsistent across pattern runners | Medium | Medium | High | Add per-step and per-pattern `FailurePolicy` |
| Agent wrappers are thin validators | Medium | Medium | Medium | Bind agents to declared capabilities, expected tools, and output contracts |
| Tests mostly cover happy paths | Medium | Medium | High | Add tests for partial worker failure, invalid intermediate output, route ambiguity, timeout, retry, and fan-in conflicts |

## Definition Of Done

This refactor is complete when:

- workflow plans are typed and executable
- workflow execution uses a central executor
- all five agentic workflow patterns are production-grade
- every material step is observable and replayable
- routing is structured, policy-aware, and inspectable
- evaluator-optimizer loops persist critique and refinement evidence
- parallel workflows actually execute concurrently
- orchestrator-workers run from orchestrator-generated plans
- failure handling is explicit and tested
- scenario tests prove safe behavior across research, paper, and live workflow modes
