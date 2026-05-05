"""Executable workflow plan orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Callable

from backend.agents.runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    EvaluatorOptimizerStep,
    EvaluatorOptimizerWorkflowRunner,
    OrchestratorWorkerTask,
    OrchestratorWorkerWorkflowRunner,
    ParallelWorkflowRunner,
    ParallelWorkflowTask,
    RoutingWorkflowBranch,
    RoutingWorkflowRunner,
    SequentialWorkflowRunner,
    SequentialWorkflowStep,
    RuntimeTrajectoryLogService,
    WorkflowPatternRegistry,
    build_run_trajectory_log,
)
from haruquant.utils import generate_prefixed_id
from haruquant.utils import logger
from backend.contracts.workflow_plan.model import (
    WorkflowPattern,
    WorkflowPhaseStep,
    WorkflowPlan,
)
from backend.data.database import ResearchAuditRepository, WorkflowRepository
from backend.observability.span_model import Span
from backend.observability.trace_model import Trace

from .persistence import (
    WorkflowStepRecorder,
    WorkflowStepRequest,
    WorkflowTransitionEvent,
    WorkflowTransitionLogger,
)
from .states import WorkflowState
from .transitions import is_allowed_workflow_transition
from .validator import WorkflowStateValidator, WorkflowValidationContext


@dataclass(frozen=True)
class StepExecutionResult:
    """Typed result for one workflow step."""

    step_id: str
    phase: str
    agent_name: str
    final_state: str
    latency_ms: int
    output_payload: dict
    input_ref: str = ""
    output_ref: str = ""
    span_id: str = ""


@dataclass(frozen=True)
class WorkflowExecutionResult:
    """Typed result for a workflow plan execution."""

    workflow_id: str
    correlation_id: str
    final_state: str
    selected_pattern: WorkflowPattern
    steps: tuple[StepExecutionResult, ...]
    failed_steps: tuple[str, ...] = ()
    timed_out_steps: tuple[str, ...] = ()
    synthesized_output: dict | None = None
    trace_id: str | None = None
    spans: tuple[dict, ...] = ()


@dataclass
class WorkflowPlanExecutor:
    """Execute typed WorkflowPlan contracts through registered pattern runners."""

    runner: ADKRunnerService
    workflow_repository: WorkflowRepository
    step_recorder: WorkflowStepRecorder
    transition_logger: WorkflowTransitionLogger
    runtime_agents: dict[str, AgentRuntime]
    trajectory_log_service: RuntimeTrajectoryLogService | None = None
    research_audit_repository: ResearchAuditRepository | None = None
    pattern_registry: WorkflowPatternRegistry | None = None
    evaluator_by_step_id: dict[str, Callable[[ADKRunResult], float]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        logger.debug("WorkflowPlanExecutor initialized", component="orchestration.executor")
        if self.pattern_registry is None:
            registry = WorkflowPatternRegistry()
            registry.register(
                pattern=WorkflowPattern.SEQUENTIAL,
                runner=SequentialWorkflowRunner(self.runner),
            )
            registry.register(
                pattern=WorkflowPattern.ROUTING,
                runner=RoutingWorkflowRunner(self.runner),
            )
            registry.register(
                pattern=WorkflowPattern.PARALLEL,
                runner=ParallelWorkflowRunner(self.runner),
                supports_concurrency=True,
            )
            registry.register(
                pattern=WorkflowPattern.EVALUATOR_OPTIMIZER,
                runner=EvaluatorOptimizerWorkflowRunner(self.runner),
            )
            registry.register(
                pattern=WorkflowPattern.ORCHESTRATOR_WORKERS,
                runner=OrchestratorWorkerWorkflowRunner(self.runner),
                supports_concurrency=True,
            )
            self.pattern_registry = registry

    def execute(self, plan: WorkflowPlan) -> WorkflowExecutionResult:
        """Execute a typed workflow plan and persist step-level observability."""

        workflow = self.workflow_repository.get_workflow(plan.workflow_id)
        if workflow is None:
            logger.error(
                "Workflow not found — cannot execute plan",
                component="orchestration.executor",
                workflow_id=plan.workflow_id,
            )
            raise LookupError(f"workflow not found: {plan.workflow_id}")

        pattern = plan.payload.selected_pattern
        logger.info(
            "Starting workflow plan execution",
            component="orchestration.executor",
            workflow_id=plan.workflow_id,
            pattern=pattern.value,
            correlation_id=plan.correlation_id,
            step_count=len(plan.payload.phase_steps),
        )
        self.pattern_registry.get(pattern)
        trace = Trace(
            trace_id=plan.trace_id or generate_prefixed_id("trace"),
            workflow_id=plan.workflow_id,
            request_id=plan.causation_id,
            agent_name="workflow_plan_executor",
            result_status="RUNNING",
        )
        trace.start()
        raw_results = self._execute_by_pattern(plan, pattern)
        step_results = tuple(
            self._record_step_result(plan=plan, step=step, result=result, trace=trace)
            for step, result in raw_results
        )
        failed_steps = tuple(
            result.step_id for result in step_results if result.final_state != "COMPLETED"
        )
        final_state = "COMPLETED" if not failed_steps else "FAILED"
        final_state = self._complete_workflow(
            workflow_id=plan.workflow_id,
            final_state=final_state,
            step_results=step_results,
        )
        trace.result_status = final_state
        trace.end()

        if failed_steps:
            logger.warning(
                "Workflow completed with failed steps",
                component="orchestration.executor",
                workflow_id=plan.workflow_id,
                final_state=final_state,
                failed_steps=failed_steps,
            )
        else:
            logger.info(
                "Workflow execution completed",
                component="orchestration.executor",
                workflow_id=plan.workflow_id,
                final_state=final_state,
                step_count=len(step_results),
            )

        return WorkflowExecutionResult(
            workflow_id=plan.workflow_id,
            correlation_id=plan.correlation_id,
            final_state=final_state,
            selected_pattern=pattern,
            steps=step_results,
            failed_steps=failed_steps,
            timed_out_steps=tuple(
                result.step_id for result in step_results if result.final_state == "TIMED_OUT"
            ),
            synthesized_output={
                result.step_id: result.output_payload for result in step_results
            },
            trace_id=trace.trace_id,
            spans=tuple(span.to_dict() for span in trace.attributes.get("spans", ())),
        )

    def _execute_by_pattern(
        self,
        plan: WorkflowPlan,
        pattern: WorkflowPattern,
    ) -> tuple[tuple[WorkflowPhaseStep, ADKRunResult], ...]:
        steps = tuple(plan.payload.phase_steps)
        if pattern is WorkflowPattern.SEQUENTIAL:
            runner = self.pattern_registry.get(pattern).runner
            sequential_steps = tuple(
                SequentialWorkflowStep(
                    step_name=step.step_id,
                    runtime_agent=self._agent(step.owner_agent),
                    request=self._request(plan, step),
                    input_contract_type=step.input_contract_type,
                    expected_output_contract_type=step.expected_output_contract_type,
                )
                for step in steps
            )
            results = runner.run(steps=sequential_steps)
            return tuple(zip(steps, results))

        if pattern is WorkflowPattern.ROUTING:
            runner = self.pattern_registry.get(pattern).runner
            route_key = str(plan.payload.phase_steps[0].metadata.get("route_key", ""))
            if not route_key:
                route_key = plan.payload.phase_steps[0].step_id
            branches = tuple(
                RoutingWorkflowBranch(
                    route_key=step.step_id,
                    runtime_agent=self._agent(step.owner_agent),
                    request=self._request(plan, step),
                    input_contract_type=step.input_contract_type,
                    expected_output_contract_type=step.expected_output_contract_type,
                )
                for step in steps
            )
            return ((steps[0], runner.run(route_key=route_key, branches=branches)),)

        if pattern is WorkflowPattern.PARALLEL:
            runner = self.pattern_registry.get(pattern).runner
            tasks = tuple(
                ParallelWorkflowTask(
                    task_name=step.step_id,
                    runtime_agent=self._agent(step.owner_agent),
                    request=self._request(plan, step),
                    input_contract_type=step.input_contract_type,
                    expected_output_contract_type=step.expected_output_contract_type,
                    timeout_seconds=step.timeout_seconds,
                    critical=step.failure_policy.critical,
                )
                for step in steps
            )
            aggregate = runner.run(tasks=tasks)
            return tuple((step, aggregate[step.step_id]) for step in steps)

        if pattern is WorkflowPattern.EVALUATOR_OPTIMIZER:
            if len(steps) != 1:
                raise ValueError("evaluator_optimizer plans require exactly one phase step")
            step = steps[0]
            evaluator = self.evaluator_by_step_id.get(step.step_id)
            if evaluator is None:
                raise ValueError(f"missing evaluator for step: {step.step_id}")
            runner = self.pattern_registry.get(pattern).runner
            result = runner.run(
                generator_step=EvaluatorOptimizerStep(
                    runtime_agent=self._agent(step.owner_agent),
                    request=self._request(plan, step),
                ),
                evaluator=evaluator,
                acceptance_threshold=float(step.metadata.get("acceptance_threshold", 0.8)),
                max_iterations=int(step.metadata.get("max_iterations", 3)),
            )
            self._persist_evaluator_iterations(plan=plan, step=step, result=result)
            return ((step, result.final_result),)

        if pattern is WorkflowPattern.ORCHESTRATOR_WORKERS:
            runner = self.pattern_registry.get(pattern).runner
            tasks = tuple(
                OrchestratorWorkerTask(
                    worker_name=step.step_id,
                    runtime_agent=self._agent(step.owner_agent),
                    request=self._request(plan, step),
                    input_contract_type=step.input_contract_type,
                    expected_output_contract_type=step.expected_output_contract_type,
                    timeout_seconds=step.timeout_seconds,
                    critical=step.failure_policy.critical,
                )
                for step in steps
            )
            group = runner.run(tasks=tasks)
            return tuple((step, group[step.step_id]) for step in steps)

        raise LookupError(f"unsupported workflow pattern: {pattern.value}")

    def _record_step_result(
        self,
        *,
        plan: WorkflowPlan,
        step: WorkflowPhaseStep,
        result: ADKRunResult,
        trace: Trace,
    ) -> StepExecutionResult:
        self._advance_for_phase(plan=plan, step=step, result=result)
        request = self._request(plan, step)
        input_ref = str(step.metadata.get("input_ref", "")) or _artifact_ref(
            plan.workflow_id,
            step.step_id,
            "input",
        )
        output_ref = str(step.metadata.get("output_ref", "")) or _artifact_ref(
            plan.workflow_id,
            step.step_id,
            "output",
        )
        span = Span(
            span_id=generate_prefixed_id("span"),
            trace_id=trace.trace_id,
            name=f"{step.phase}:{step.step_id}",
            attributes={
                "workflow_id": plan.workflow_id,
                "step_id": step.step_id,
                "agent_name": step.owner_agent,
                "input_ref": input_ref,
                "output_ref": output_ref,
            },
        )
        span.start()
        span.end(status=result.final_state)
        trace.attributes.setdefault("spans", []).append(span)
        self.step_recorder.record(
            WorkflowStepRequest(
                step_id=step.step_id,
                workflow_id=plan.workflow_id,
                step_type=step.phase,
                status=result.final_state,
                assigned_agent=step.owner_agent,
                input_contract_type=step.input_contract_type,
                input_ref=input_ref,
                output_contract_type=step.expected_output_contract_type,
                output_ref=output_ref,
                started_at=_utc_now(),
                completed_at=_utc_now(),
                latency_ms=result.latency_ms,
                iteration_no=int(step.metadata.get("iteration_no", 0)),
                metadata_json=json.dumps(
                    {
                        "tool_calls": list(result.tool_calls),
                        "token_usage": result.token_usage,
                        "validation_error": result.validation_error,
                        "repair_attempted": result.repair_attempted,
                        "repair_succeeded": result.repair_succeeded,
                    },
                    sort_keys=True,
                    default=str,
                ),
            )
        )
        if self.trajectory_log_service is not None:
            self.trajectory_log_service.persist(
                build_run_trajectory_log(
                    request=request,
                    result=result,
                    phase=step.phase,
                    iteration_no=int(step.metadata.get("iteration_no", 0)),
                    input_schema=step.input_contract_type or "unknown",
                    output_schema=step.expected_output_contract_type,
                    artifact_ref=output_ref,
                )
            )
        return StepExecutionResult(
            step_id=step.step_id,
            phase=step.phase,
            agent_name=step.owner_agent,
            final_state=result.final_state,
            latency_ms=result.latency_ms,
            output_payload=dict(result.output_payload),
            input_ref=input_ref,
            output_ref=output_ref,
            span_id=span.span_id,
        )

    def _persist_evaluator_iterations(
        self,
        *,
        plan: WorkflowPlan,
        step: WorkflowPhaseStep,
        result: object,
    ) -> None:
        if self.research_audit_repository is None:
            return
        evaluations = tuple(getattr(result, "evaluations", ()))
        scores = tuple(getattr(result, "evaluation_scores", ()))
        for index, evaluation in enumerate(evaluations):
            if hasattr(evaluation, "rubric_name"):
                rubric_name = evaluation.rubric_name
                rubric_scores = evaluation.rubric_scores
                overall_score = evaluation.overall_score
                verdict = evaluation.verdict
            else:
                score = float(scores[index])
                rubric_name = str(step.metadata.get("rubric_name", "score_threshold"))
                rubric_scores = {"overall": score}
                overall_score = score
                threshold = float(step.metadata.get("acceptance_threshold", 0.8))
                verdict = "pass" if score >= threshold else "fail"
            self.research_audit_repository.add_evaluation_report(
                evaluation_id=generate_prefixed_id("eval"),
                workflow_id=plan.workflow_id,
                target_type="workflow_step",
                target_ref=step.step_id,
                rubric_name=str(rubric_name),
                rubric_scores_json=json.dumps(rubric_scores, sort_keys=True),
                overall_score=float(overall_score),
                verdict=str(verdict),
                issues_json="[]",
                improvement_actions_json=json.dumps(
                    ["refine"] if str(verdict) != "pass" else [],
                    sort_keys=True,
                ),
                evaluator_identity="workflow_plan_executor",
                evaluation_model_id=self.runner.config.default_model,
            )

    def _advance_for_phase(
        self,
        *,
        plan: WorkflowPlan,
        step: WorkflowPhaseStep,
        result: ADKRunResult,
    ) -> None:
        workflow = self.workflow_repository.get_workflow(plan.workflow_id)
        if workflow is None:
            raise LookupError(f"workflow not found: {plan.workflow_id}")
        current_state = WorkflowState(workflow.state)
        target_state = _phase_to_state(step.phase)
        if target_state is None or current_state is target_state:
            return
        if not is_allowed_workflow_transition(current_state, target_state):
            logger.warning(
                "Workflow state transition not allowed — skipping",
                component="orchestration.executor",
                workflow_id=plan.workflow_id,
                from_state=current_state.value,
                to_state=target_state.value,
                phase=step.phase,
            )
            return

        WorkflowStateValidator().validate_transition(
            from_state=current_state,
            to_state=target_state,
            context=WorkflowValidationContext(),
        )
        logger.debug(
            "Workflow state transition",
            component="orchestration.executor",
            workflow_id=plan.workflow_id,
            from_state=current_state.value,
            to_state=target_state.value,
            phase=step.phase,
            agent=step.owner_agent,
        )
        self.workflow_repository.update_workflow_state(
            workflow_id=plan.workflow_id,
            expected_version=workflow.version_no,
            state=target_state.value,
            current_step_id=step.step_id,
        )
        self.transition_logger.append(
            WorkflowTransitionEvent(
                workflow_id=plan.workflow_id,
                from_state=current_state,
                to_state=target_state,
                actor_type="agent",
                actor_id=step.owner_agent,
                correlation_id=plan.correlation_id,
                phase_name=step.phase,
                transition_reason=result.final_state,
                causation_id=plan.causation_id,
            )
        )

    def _complete_workflow(
        self,
        *,
        workflow_id: str,
        final_state: str,
        step_results: tuple[StepExecutionResult, ...],
    ) -> str:
        workflow = self.workflow_repository.get_workflow(workflow_id)
        if workflow is None:
            raise LookupError(f"workflow not found: {workflow_id}")
        current_state = WorkflowState(workflow.state)
        target_state = WorkflowState.COMPLETED if final_state == "COMPLETED" else WorkflowState.FAILED
        if not is_allowed_workflow_transition(current_state, target_state):
            target_state = WorkflowState.FAILED
        try:
            WorkflowStateValidator().validate_transition(
                from_state=current_state,
                to_state=target_state,
                context=WorkflowValidationContext(
                    observe_seen=any(step.phase == "observe" for step in step_results),
                    evaluate_seen=any(
                        step.phase in {"evaluate", "verify", "risk"} for step in step_results
                    ),
                ),
            )
        except Exception:
            target_state = WorkflowState.FAILED

        self.workflow_repository.update_workflow_state(
            workflow_id=workflow_id,
            expected_version=workflow.version_no,
            state=target_state.value,
            completed_at=_utc_now(),
            terminal_reason=None
            if target_state is WorkflowState.COMPLETED
            else "workflow_execution_failed",
        )
        return target_state.value

    def _agent(self, agent_name: str) -> AgentRuntime:
        try:
            return self.runtime_agents[agent_name]
        except KeyError as exc:
            logger.error(
                "Runtime agent not registered",
                component="orchestration.executor",
                agent_name=agent_name,
                registered_agents=list(self.runtime_agents.keys()),
            )
            raise LookupError(f"runtime agent not registered: {agent_name}") from exc

    def _request(self, plan: WorkflowPlan, step: WorkflowPhaseStep) -> ADKRunRequest:
        input_payload = dict(step.metadata.get("input_payload", {}))
        if not input_payload:
            input_payload = {
                "contract_type": step.input_contract_type or "WorkflowStepInput",
                "schema_version": plan.schema_version,
                "workflow_id": plan.workflow_id,
                "step_id": step.step_id,
                "goal": step.goal,
            }
        return ADKRunRequest(
            workflow_id=plan.workflow_id,
            correlation_id=plan.correlation_id,
            agent_name=step.owner_agent,
            input_payload=input_payload,
            allowed_tools=tuple(step.allowed_tools),
            metadata={
                "phase": step.phase,
                "step_id": step.step_id,
                "depends_on": list(step.depends_on),
                **dict(step.metadata),
            },
        )


def _phase_to_state(phase: str) -> WorkflowState | None:
    normalized = phase.lower()
    mapping = {
        "reason": WorkflowState.REASONING,
        "research": WorkflowState.REASONING,
        "plan": WorkflowState.PLANNING,
        "planning": WorkflowState.PLANNING,
        "act": WorkflowState.ACTING,
        "execute": WorkflowState.ACTING,
        "observe": WorkflowState.OBSERVING,
        "evaluate": WorkflowState.EVALUATING,
        "verify": WorkflowState.EVALUATING,
        "risk": WorkflowState.EVALUATING,
        "refine": WorkflowState.REFINING,
    }
    return mapping.get(normalized)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _artifact_ref(workflow_id: str, step_id: str, kind: str) -> str:
    return f"artifact://workflow/{workflow_id}/steps/{step_id}/{kind}"
