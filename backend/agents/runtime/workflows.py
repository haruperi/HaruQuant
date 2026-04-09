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
