"""Agent-runtime workflow pattern runners."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Optional, Union

from .runner import ADKRunRequest, ADKRunResult, ADKRunnerService, AgentRuntime
from .output_validation import CanonicalOutputValidator, ContractValidationError
from .evaluator import (
    EvaluatorRubric,
    TrajectoryEvaluation,
    TrajectoryEvaluationService,
    generate_refinement_recommendations,
)


@dataclass(frozen=True)
class SequentialWorkflowStep:
    """One ordered step in a sequential workflow pattern."""

    step_name: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest
    input_contract_type: str | None = None
    expected_output_contract_type: str | None = None
    validate_before_next: bool = True


class SequentialWorkflowRunner:
    """Execute workflow steps strictly in declaration order.

    Builds a context_chain where each step's output becomes available
    to subsequent steps via request.metadata["prior_steps"].
    """

    def __init__(
        self,
        runner: ADKRunnerService,
        output_validator: CanonicalOutputValidator | None = None,
    ) -> None:
        self._runner = runner
        self._output_validator = output_validator

    def run(
        self,
        *,
        steps: tuple[SequentialWorkflowStep, ...],
    ) -> tuple[ADKRunResult, ...]:
        results: list[ADKRunResult] = []
        context_chain: Dict[str, Any] = {}
        for step in steps:
            # Inject prior step results as context
            augmented_request = replace(step.request, metadata={
                **step.request.metadata,
                "prior_steps": dict(context_chain),
            })
            result = self._runner.run(
                agent=step.runtime_agent,
                request=augmented_request,
            )
            if step.validate_before_next and not self._step_output_is_valid(step, result):
                results.append(result)
                break
            context_chain[step.step_name] = {
                "output": result.output_payload,
                "state": result.final_state,
            }
            results.append(result)
        return tuple(results)

    def _step_output_is_valid(
        self,
        step: SequentialWorkflowStep,
        result: ADKRunResult,
    ) -> bool:
        if result.final_state != "COMPLETED":
            return False
        if step.expected_output_contract_type is not None:
            if result.output_payload.get("contract_type") != step.expected_output_contract_type:
                return False
        if self._output_validator is None:
            return True
        try:
            self._output_validator.validate(result.output_payload)
        except ContractValidationError:
            return False
        return True


@dataclass(frozen=True)
class RoutingWorkflowBranch:
    """One named branch in a routing workflow pattern."""

    route_key: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest
    input_contract_type: str | None = None
    expected_output_contract_type: str | None = None


class RoutingWorkflowRunner:
    """Execute the one branch selected by a route key."""

    def __init__(self, runner: ADKRunnerService) -> None:
        self._runner = runner

    def run(
        self,
        *,
        route_key: str,
        branches: tuple[RoutingWorkflowBranch, ...],
    ) -> ADKRunResult:
        for branch in branches:
            if branch.route_key == route_key:
                return self._runner.run(
                    agent=branch.runtime_agent,
                    request=branch.request,
                )
        raise LookupError(f"workflow route not found: {route_key}")


@dataclass(frozen=True)
class ParallelWorkflowTask:
    """One task in a fan-out parallel workflow pattern."""

    task_name: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest
    input_contract_type: str | None = None
    expected_output_contract_type: str | None = None
    timeout_seconds: float | None = None
    critical: bool = True


@dataclass(frozen=True)
class ParallelAggregateResult(Mapping[str, ADKRunResult]):
    """Fan-in result for a parallel workflow run."""

    results: dict[str, ADKRunResult]
    timed_out_tasks: tuple[str, ...] = ()
    failed_tasks: tuple[str, ...] = ()

    def __getitem__(self, key: str) -> ADKRunResult:
        return self.results[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    @property
    def successful_tasks(self) -> tuple[str, ...]:
        return tuple(
            task_name
            for task_name, result in self.results.items()
            if result.final_state == "COMPLETED"
        )


class ParallelWorkflowRunner:
    """Execute independent tasks and return a keyed fan-in result map.

    Each task receives peer_tasks metadata containing the names of all
    other parallel tasks, so results can reference each other's outputs.
    """

    def __init__(self, runner: ADKRunnerService) -> None:
        self._runner = runner

    def run(
        self,
        *,
        tasks: tuple[ParallelWorkflowTask, ...],
    ) -> ParallelAggregateResult:
        results: dict[str, ADKRunResult] = {}
        peer_task_names = tuple(t.task_name for t in tasks)
        if not tasks:
            return ParallelAggregateResult(results={})

        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {}
            for task in tasks:
                augmented_request = replace(
                    task.request,
                    metadata={
                        **task.request.metadata,
                        "peer_tasks": tuple(
                            name for name in peer_task_names if name != task.task_name
                        ),
                    },
                )
                futures[
                    executor.submit(
                        self._runner.run,
                        agent=task.runtime_agent,
                        request=augmented_request,
                    )
                ] = (task, augmented_request)

            max_timeout = _max_timeout_seconds(tasks)
            done, not_done = wait(futures.keys(), timeout=max_timeout)

            failed_tasks: list[str] = []
            for future in done:
                task, augmented_request = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - defensive runtime guard
                    failed_tasks.append(task.task_name)
                    result = _synthetic_result(
                        runner=self._runner,
                        request=augmented_request,
                        final_state="FAILED",
                        error=str(exc),
                    )
                if result.final_state != "COMPLETED":
                    failed_tasks.append(task.task_name)
                results[task.task_name] = result

            timed_out_tasks: list[str] = []
            for future in not_done:
                task, augmented_request = futures[future]
                future.cancel()
                timed_out_tasks.append(task.task_name)
                results[task.task_name] = _synthetic_result(
                    runner=self._runner,
                    request=augmented_request,
                    final_state="TIMED_OUT",
                    error="parallel task timed out",
                )

        return ParallelAggregateResult(
            results=results,
            timed_out_tasks=tuple(timed_out_tasks),
            failed_tasks=tuple(dict.fromkeys(failed_tasks)),
        )


def _max_timeout_seconds(tasks: tuple[ParallelWorkflowTask, ...]) -> float | None:
    timeouts = tuple(task.timeout_seconds for task in tasks if task.timeout_seconds)
    return max(timeouts) if timeouts else None


def _synthetic_result(
    *,
    runner: ADKRunnerService,
    request: ADKRunRequest,
    final_state: str,
    error: str,
) -> ADKRunResult:
    model = request.model or runner.config.default_model
    return ADKRunResult(
        runner_name=runner.config.runner_name,
        runtime_version=runner.config.runtime_version,
        agent_name=request.agent_name,
        workflow_id=request.workflow_id,
        correlation_id=request.correlation_id,
        session_id=request.session_id,
        model=model,
        prompt_version_id=request.prompt_version_id,
        prompt_hash=None,
        latency_ms=0,
        output_payload={
            "error": error,
            "contract_type": request.input_payload.get("contract_type", "unknown"),
            "schema_version": request.input_payload.get("schema_version", "1.0.0"),
        },
        final_state=final_state,
        tool_calls=(),
        token_usage=None,
    )


@dataclass(frozen=True)
class EvaluatorOptimizerStep:
    """One candidate generation step in an evaluator-optimizer pattern."""

    runtime_agent: AgentRuntime
    request: ADKRunRequest


@dataclass(frozen=True)
class EvaluatorOptimizerResult:
    """Result bundle for evaluator-optimizer workflows."""

    final_result: ADKRunResult
    evaluation_scores: tuple[float, ...]
    iterations: int
    terminated_by: str
    evaluations: tuple[Union[float, TrajectoryEvaluation], ...] = ()


class EvaluatorOptimizerWorkflowRunner:
    """Run generation/evaluation loops until accepted or max iterations hit.

    Supports two evaluator modes:
    1. Simple float evaluator: evaluator(result) → float (backward compatible)
    2. Rubric-based evaluator: evaluator(result) → TrajectoryEvaluation

    When a rubric is provided, the generator receives specific refinement
    feedback based on which criteria failed (improvement_actions and
    focus_areas derived from the actual evaluation findings).
    """

    def __init__(
        self,
        runner: ADKRunnerService,
        rubric: Optional[EvaluatorRubric] = None,
    ) -> None:
        self._runner = runner
        self._rubric = rubric
        self._eval_service = TrajectoryEvaluationService() if rubric else None

    def run(
        self,
        *,
        generator_step: EvaluatorOptimizerStep,
        evaluator: Callable[[ADKRunResult], Union[float, TrajectoryEvaluation]],
        acceptance_threshold: float,
        max_iterations: int,
    ) -> EvaluatorOptimizerResult:
        scores: list[float] = []
        evaluations: list[Union[float, TrajectoryEvaluation]] = []
        final_result: ADKRunResult | None = None
        terminated_by = "max_iterations"

        if max_iterations <= 0:
            raise ValueError("max_iterations must be at least 1")

        current_request = generator_step.request
        for iteration in range(max_iterations):
            final_result = self._runner.run(
                agent=generator_step.runtime_agent,
                request=current_request,
            )
            eval_result = evaluator(final_result)
            evaluations.append(eval_result)

            # Extract score from either float or TrajectoryEvaluation
            if isinstance(eval_result, TrajectoryEvaluation):
                score = eval_result.overall_score
            else:
                score = float(eval_result)
            scores.append(score)

            if score >= acceptance_threshold:
                terminated_by = "accepted"
                break

            # Build refinement context for next iteration using actual findings
            if iteration + 1 < max_iterations:
                refinement = self._build_refinement_context(
                    eval_result=eval_result,
                    iteration=iteration,
                    score=score,
                )
                current_request = replace(current_request, metadata={
                    **current_request.metadata,
                    **refinement,
                })

        return EvaluatorOptimizerResult(
            final_result=final_result,
            evaluation_scores=tuple(scores),
            iterations=len(scores),
            terminated_by=terminated_by,
            evaluations=tuple(evaluations),
        )

    def _build_refinement_context(
        self,
        eval_result: Union[float, TrajectoryEvaluation],
        iteration: int,
        score: float,
    ) -> Dict[str, Any]:
        """Build refinement metadata based on actual evaluation findings."""
        if isinstance(eval_result, TrajectoryEvaluation):
            # Rubric-based: generate specific recommendations from criteria
            recommendations = generate_refinement_recommendations(
                evaluation=eval_result,
                unsupported_assertions=None,
            )
            return {
                "refinement_iteration": iteration + 1,
                "previous_score": score,
                "previous_verdict": eval_result.verdict,
                "improvement_actions": recommendations.improvement_actions,
                "focus_areas": recommendations.focus_areas,
            }
        else:
            # Simple float: generic improvement guidance
            return {
                "refinement_iteration": iteration + 1,
                "previous_score": score,
                "improvement_actions": [
                    f"Improve output quality (current score {score:.2f} "
                    f"below threshold)"
                ],
                "focus_areas": ["output_quality"],
            }


@dataclass(frozen=True)
class OrchestratorWorkerTask:
    """One worker task emitted by an orchestrator-worker plan."""

    worker_name: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest
    input_contract_type: str | None = None
    expected_output_contract_type: str | None = None
    timeout_seconds: float | None = None
    critical: bool = True


@dataclass(frozen=True)
class WorkerGroupResult(Mapping[str, ADKRunResult]):
    """Fan-in result for orchestrator-worker dispatch."""

    results: dict[str, ADKRunResult]
    timed_out_workers: tuple[str, ...] = ()
    failed_workers: tuple[str, ...] = ()
    synthesized_output: dict[str, Any] | None = None
    conflicts: tuple[str, ...] = ()

    def __getitem__(self, key: str) -> ADKRunResult:
        return self.results[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)


class OrchestratorWorkerWorkflowRunner:
    """Run an orchestrator plan by dispatching its declared worker tasks."""

    def __init__(self, runner: ADKRunnerService) -> None:
        self._runner = runner

    def run(
        self,
        *,
        tasks: tuple[OrchestratorWorkerTask, ...],
    ) -> WorkerGroupResult:
        parallel_tasks = tuple(
            ParallelWorkflowTask(
                task_name=task.worker_name,
                runtime_agent=task.runtime_agent,
                request=task.request,
                input_contract_type=task.input_contract_type,
                expected_output_contract_type=task.expected_output_contract_type,
                timeout_seconds=task.timeout_seconds,
                critical=task.critical,
            )
            for task in tasks
        )
        aggregate = ParallelWorkflowRunner(self._runner).run(tasks=parallel_tasks)
        synthesized = {
            worker_name: result.output_payload
            for worker_name, result in aggregate.results.items()
            if result.final_state == "COMPLETED"
        }
        conflicts = _detect_worker_conflicts(synthesized)
        return WorkerGroupResult(
            results=aggregate.results,
            timed_out_workers=aggregate.timed_out_tasks,
            failed_workers=aggregate.failed_tasks,
            synthesized_output=synthesized,
            conflicts=conflicts,
        )


def _detect_worker_conflicts(worker_outputs: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    seen: dict[str, Any] = {}
    conflicts: list[str] = []
    for worker_name, payload in worker_outputs.items():
        for key, value in payload.items():
            if key in {"contract_type", "schema_version"}:
                continue
            if key in seen and seen[key] != value:
                conflicts.append(f"{key}:{worker_name}")
            else:
                seen[key] = value
    return tuple(conflicts)


@dataclass(frozen=True)
class RefineLoopGuardDecision:
    """Guard outcome for refinement loop iteration control."""

    allowed: bool
    reason_codes: tuple[str, ...]


def enforce_refine_loop_limit(
    *,
    iteration_count: int,
    max_iterations: int,
) -> RefineLoopGuardDecision:
    """Fail closed once refinement exceeds the configured bound."""

    if iteration_count < max_iterations:
        return RefineLoopGuardDecision(allowed=True, reason_codes=())
    return RefineLoopGuardDecision(
        allowed=False,
        reason_codes=("refine_loop_iteration_limit_reached",),
    )
