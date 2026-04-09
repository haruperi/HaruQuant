from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
)


class FakeRuntimeAgent:
    def __init__(self) -> None:
        self.last_context = None

    def run(self, *, request, context):  # noqa: ANN001
        self.last_context = context
        return AgentExecutionResult(
            output_payload={
                "echo": request.input_payload,
                "agent": request.agent_name,
            },
            tool_calls=({"tool_name": "research.lookup", "latency_ms": 12},),
            token_usage={"prompt": 10, "completion": 6},
        )


def test_adk_runner_service_initializes_and_uses_default_model() -> None:
    service = ADKRunnerService(
        ADKRunnerConfig(
            runner_name="agent-runtime",
            default_model="gemini-2.5-flash",
        )
    )
    agent = FakeRuntimeAgent()

    result = service.run(
        agent=agent,
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="orchestrator_agent",
            session_id="sess_001",
            input_payload={"goal": "review eurusd"},
            allowed_tools=("market.snapshot",),
            prompt_version_id="prompt_001",
        ),
    )

    assert service.config.runner_name == "agent-runtime"
    assert result.model == "gemini-2.5-flash"
    assert result.prompt_version_id == "prompt_001"
    assert result.prompt_hash is None
    assert result.workflow_id == "wf_001"
    assert result.output_payload["agent"] == "orchestrator_agent"
    assert agent.last_context.allowed_tools == ("market.snapshot",)
    assert agent.last_context.prompt_version_id == "prompt_001"


def test_adk_runner_service_allows_request_model_override() -> None:
    service = ADKRunnerService(
        ADKRunnerConfig(
            runner_name="agent-runtime",
            default_model="gemini-2.5-flash",
        )
    )
    agent = FakeRuntimeAgent()

    result = service.run(
        agent=agent,
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="research_agent",
            input_payload={"query": "macro drivers"},
            model="gemini-2.5-pro",
        ),
    )

    assert result.model == "gemini-2.5-pro"
    assert result.prompt_version_id is None
    assert result.session_id is None
    assert result.tool_calls[0]["tool_name"] == "research.lookup"
