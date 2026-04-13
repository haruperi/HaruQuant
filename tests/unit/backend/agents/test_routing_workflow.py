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


def test_routing_workflow_runner_falls_back_to_default_branch() -> None:
    """Unmatched route should run default_branch instead of raising."""
    default_branch = RoutingWorkflowBranch(
        route_key="default",
        runtime_agent=RouteRuntime("default_fallback"),
        request=ADKRunRequest(
            workflow_id="wf_002",
            correlation_id="corr_002",
            agent_name="research_agent",
            input_payload={},
        ),
    )
    runner = RoutingWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        ),
        default_branch=default_branch,
    )

    result = runner.run(
        route_key="unknown_route_xyz",
        branches=(
            RoutingWorkflowBranch(
                route_key="research",
                runtime_agent=RouteRuntime("research"),
                request=ADKRunRequest(
                    workflow_id="wf_002",
                    correlation_id="corr_002",
                    agent_name="research_agent",
                    input_payload={},
                ),
            ),
        ),
    )

    assert result.output_payload["route"] == "default_fallback"


def test_routing_workflow_without_default_still_raises() -> None:
    """Without default_branch, unmatched route should still raise LookupError."""
    runner = RoutingWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        ),
        default_branch=None,
    )

    with pytest.raises(LookupError, match="workflow route not found"):
        runner.run(
            route_key="missing",
            branches=(
                RoutingWorkflowBranch(
                    route_key="other",
                    runtime_agent=RouteRuntime("other"),
                    request=ADKRunRequest(
                        workflow_id="wf_003",
                        correlation_id="corr_003",
                        agent_name="research_agent",
                        input_payload={},
                    ),
                ),
            ),
        )
