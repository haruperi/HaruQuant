from __future__ import annotations

import pytest

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    RoutingWorkflowBranch,
    RoutingWorkflowRunner,
)


class RouteRuntime:
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(output_payload={"route": self.name})


def test_routing_workflow_runner_executes_selected_route() -> None:
    runner = RoutingWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    result = runner.run(
        route_key="research",
        branches=(
            RoutingWorkflowBranch(
                route_key="strategy",
                runtime_agent=RouteRuntime("strategy"),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="strategy_agent",
                    input_payload={},
                ),
            ),
            RoutingWorkflowBranch(
                route_key="research",
                runtime_agent=RouteRuntime("research"),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="research_agent",
                    input_payload={},
                ),
            ),
        ),
    )

    assert result.output_payload["route"] == "research"


def test_routing_workflow_runner_rejects_unknown_route() -> None:
    runner = RoutingWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    with pytest.raises(LookupError, match="workflow route not found"):
        runner.run(route_key="missing", branches=())
