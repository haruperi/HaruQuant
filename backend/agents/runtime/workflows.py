"""Agent-runtime workflow pattern runners."""

from __future__ import annotations

from dataclasses import dataclass

from .runner import ADKRunRequest, ADKRunResult, ADKRunnerService, AgentRuntime


@dataclass(frozen=True)
class SequentialWorkflowStep:
    """One ordered step in a sequential workflow pattern."""

    step_name: str
    runtime_agent: AgentRuntime
    request: ADKRunRequest


class SequentialWorkflowRunner:
    """Execute workflow steps strictly in declaration order."""

    def __init__(self, runner: ADKRunnerService) -> None:
        self._runner = runner

    def run(
        self,
        *,
        steps: tuple[SequentialWorkflowStep, ...],
    ) -> tuple[ADKRunResult, ...]:
        results: list[ADKRunResult] = []
        for step in steps:
            results.append(
                self._runner.run(
                    agent=step.runtime_agent,
                    request=step.request,
                )
            )
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
