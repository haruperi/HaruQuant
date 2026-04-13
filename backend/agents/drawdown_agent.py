"""Drawdown sub-agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.drawdown_template import DRAWDOWN_AGENT_INSTRUCTION
from .runtime import ADKRunRequest, ADKRunResult, ADKRunnerService, AgentRuntime, CanonicalOutputValidator


@dataclass(frozen=True)
class DrawdownAgentWrapper:
    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "drawdown_agent"
    instruction: str = DRAWDOWN_AGENT_INSTRUCTION

    def execute(self, *, runtime_agent: AgentRuntime, request: ADKRunRequest) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "ObservationEvent":
            raise ValueError("DrawdownAgent must emit ObservationEvent outputs")
        return result
