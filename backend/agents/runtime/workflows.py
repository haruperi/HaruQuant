"""Agent-runtime workflow pattern runners."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Optional

from .runner import ADKRunRequest, ADKRunResult, ADKRunnerService, AgentRuntime


@dataclass(frozen=True)
class SequentialWorkflowStep:
    """One ordered step in a sequential workflow pattern."""

    step_name: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest


class SequentialWorkflowRunner:
    """Execute workflow steps strictly in declaration order.

    Builds a context_chain where each step's output becomes available
    to subsequent steps via request.metadata["prior_steps"].
    """

    def __init__(self, runner: ADKRunnerService) -> None:
        self._runner = runner

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
            context_chain[step.step_name] = {
                "output": result.output_payload,
                "state": result.final_state,
            }
            results.append(result)
        return tuple(results)


@dataclass(frozen=True)
class RoutingWorkflowBranch:
    """One named branch in a routing workflow pattern."""

    route_key: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest


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
    ) -> dict[str, ADKRunResult]:
        results: dict[str, ADKRunResult] = {}
        peer_task_names = tuple(t.task_name for t in tasks)
        for task in tasks:
            augmented_request = replace(task.request, metadata={
                **task.request.metadata,
                "peer_tasks": peer_task_names,
            })
            results[task.task_name] = self._runner.run(
                agent=task.runtime_agent,
                request=augmented_request,
            )
        return results


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


class EvaluatorOptimizerWorkflowRunner:
    """Run generation/evaluation loops until accepted or max iterations hit.

    On each iteration, the generator receives refinement feedback
    (previous score, improvement actions, focus areas) to guide
    improved outputs.
    """

    def __init__(self, runner: ADKRunnerService) -> None:
        self._runner = runner

    def run(
        self,
        *,
        generator_step: EvaluatorOptimizerStep,
        evaluator: Callable[[ADKRunResult], float],
        acceptance_threshold: float,
        max_iterations: int,
    ) -> EvaluatorOptimizerResult:
        scores: list[float] = []
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
            score = evaluator(final_result)
            scores.append(score)
            if score >= acceptance_threshold:
                terminated_by = "accepted"
                break

            # Build refinement context for next iteration
            if iteration + 1 < max_iterations:
                current_request = replace(current_request, metadata={
                    **current_request.metadata,
                    "refinement_iteration": iteration + 1,
                    "previous_score": score,
                    "improvement_actions": ["Improve output quality to meet acceptance threshold"],
                    "focus_areas": ["output_quality"],
                })

        return EvaluatorOptimizerResult(
            final_result=final_result,
            evaluation_scores=tuple(scores),
            iterations=len(scores),
            terminated_by=terminated_by,
        )


@dataclass(frozen=True)
class OrchestratorWorkerTask:
    """One worker task emitted by an orchestrator-worker plan."""

    worker_name: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest


class OrchestratorWorkerWorkflowRunner:
    """Run an orchestrator plan by dispatching its declared worker tasks."""

    def __init__(self, runner: ADKRunnerService) -> None:
        self._runner = runner

    def run(
        self,
        *,
        tasks: tuple[OrchestratorWorkerTask, ...],
    ) -> dict[str, ADKRunResult]:
        results: dict[str, ADKRunResult] = {}
        for task in tasks:
            results[task.worker_name] = self._runner.run(
                agent=task.runtime_agent,
                request=task.request,
            )
        return results


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
