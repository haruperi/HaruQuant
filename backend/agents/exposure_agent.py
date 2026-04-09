"""Exposure sub-agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime import ADKRunRequest, ADKRunResult, ADKRunnerService, AgentRuntime, CanonicalOutputValidator


EXPOSURE_AGENT_INSTRUCTION = """
You are the HaruQuant ExposureAgent.
Summarize exposure concentrations and marginal risk contribution for advisory analysis only.
All outputs must be emitted as canonical ObservationEvent contracts.
""".strip()


@dataclass(frozen=True)
class ExposureAgentWrapper:
    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "exposure_agent"
    instruction: str = EXPOSURE_AGENT_INSTRUCTION

    def execute(self, *, runtime_agent: AgentRuntime, request: ADKRunRequest) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "ObservationEvent":
            raise ValueError("ExposureAgent must emit ObservationEvent outputs")
        return result
