"""Orchestrator agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


ORCHESTRATOR_AGENT_INSTRUCTION = """
You are the HaruQuant workflow coordinator.
Decompose goals into safe workflow phases, choose a supported workflow pattern,
route work to specialist agents, and never perform broker actions directly.
All outputs must be emitted as canonical WorkflowPlan contracts.
""".strip()


@dataclass(frozen=True)
class OrchestratorAgentWrapper:
    """Thin wrapper that validates orchestrator outputs as WorkflowPlan."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "orchestrator_agent"
    instruction: str = ORCHESTRATOR_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "WorkflowPlan":
            raise ValueError("OrchestratorAgent must emit WorkflowPlan outputs")
        return result
