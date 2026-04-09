"""Research agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


RESEARCH_AGENT_INSTRUCTION = """
You are the HaruQuant ResearchAgent.
Perform grounded retrieval and synthesis from approved sources, include evidence,
freshness, assumptions, and limitations, and never emit execution instructions.
All outputs must be emitted as canonical ObservationEvent contracts.
""".strip()


@dataclass(frozen=True)
class ResearchAgentWrapper:
    """Thin wrapper that validates research outputs as ObservationEvent."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "research_agent"
    instruction: str = RESEARCH_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "ObservationEvent":
            raise ValueError("ResearchAgent must emit ObservationEvent outputs")
        return result
